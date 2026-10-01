import json

import httpx

from server import config
from server.services import ai_agent_service


def use_mock_transport(monkeypatch, handler):
    monkeypatch.setattr(ai_agent_service, "_http_client", lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler)))


def test_offline_mentor_is_grounded_and_has_no_side_effects(client, seeded):
    assert client.get("/api/ai/status").json()["offline"] is True

    data = client.post("/api/ai/chat", json={"message": "Tôi làm sai câu này, giải thích giúp", "question_id": seeded[108]}).json()
    assert data["provider"] == "offline"
    assert "(D)" in data["reply"] and "Bẫy Vị Trí Trạng Từ" in data["reply"] and "Bài 01" in data["reply"]
    assert data["actions_taken"] == []
    assert client.get("/api/error-logs").json() == []  # no more hard-coded auto logging

    legacy = client.post("/api/ai/chat", json={"message": "?", "question_id": "ETS2024_01_108"}).json()
    assert "(D)" in legacy["reply"]
    word = client.post("/api/ai/chat", json={"message": "postpone nghĩa là gì?"}).json()
    assert "nghĩa postpone" in word["reply"]

    history = client.get("/api/ai/history").json()
    assert [m["role"] for m in history] == ["user", "assistant"] * 3
    assert client.delete("/api/ai/history").json()["deleted"] == 6


def test_gemini_function_calling_uses_question_bank_facts(client, seeded, monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "test-key")
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        requests.append(body)
        assert request.headers["x-goog-api-key"] == "test-key" and "key=" not in str(request.url)
        if len(requests) == 1:
            system = body["systemInstruction"]["parts"][0]["text"]
            assert "Đáp án đúng: D" in system and "DỮ LIỆU HỌC VIÊN" in system
            names = [decl["name"] for decl in body["tools"][0]["functionDeclarations"]]
            assert {"log_error_question", "create_practice_questions", "update_learner_profile", "replan_week"} <= set(names)
            assert all("parameters" not in d or d["parameters"]["properties"] for d in body["tools"][0]["functionDeclarations"])
            call = {
                "id": "call-1",
                "name": "log_error_question",
                "args": {"error_type": "GRAMMAR", "root_cause": "Nhầm tính từ với trạng từ", "user_choice": "(B) unanimous", "correct_choice": "A"},
            }
            return httpx.Response(200, json={"candidates": [{"content": {"role": "model", "parts": [{"functionCall": call}]}}]})
        function_response = body["contents"][-1]["parts"][0]["functionResponse"]
        assert function_response["id"] == "call-1" and function_response["response"]["result"]["status"] == "success"
        assert body["contents"][-2]["parts"][0]["functionCall"]["name"] == "log_error_question"
        return httpx.Response(200, json={"candidates": [{"content": {"role": "model", "parts": [{"text": "Đã lưu câu 108."}]}}]})

    use_mock_transport(monkeypatch, handler)
    data = client.post("/api/ai/chat", json={"message": "Tôi chọn B và sai, lưu vào sổ lỗi", "question_id": seeded[108]}).json()
    assert (data["provider"], data["reply"]) == ("gemini", "Đã lưu câu 108.")
    assert data["actions_taken"][0]["tool"] == "log_error_question"

    [log] = client.get("/api/error-logs").json()
    # The model claimed "A"; the question bank says "D" and wins.
    assert (log["correct_choice"], log["user_choice"], log["question_no"], log["source"]) == ("D", "B", 108, "ai_mentor")
    assert log["topic"] == "Bẫy Vị Trí Trạng Từ" and log["lesson_number"] == 1
    assert client.get("/api/dashboard/stats").json()["learning_gaps"][0]["lesson_number"] == 1
    assert client.get("/api/ai/history").json()[-1]["actions"][0]["status"] == "success"


def test_openai_compatible_tool_loop_dedupes_flashcards(client, seeded, monkeypatch):
    monkeypatch.setattr(config, "DEEPSEEK_API_KEY", "ds-key")

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert request.url.path.endswith("/chat/completions") and body["model"] == config.DEEPSEEK_MODEL
        assert request.headers["authorization"] == "Bearer ds-key"
        if body["messages"][-1]["role"] != "tool":
            arguments = json.dumps({"word": "Postpone", "meaning": "hoãn", "example_sentence": "x"})
            message = {
                "role": "assistant",
                "content": None,
                "tool_calls": [{"id": "t1", "type": "function", "function": {"name": "create_flashcard", "arguments": arguments}}],
            }
            return httpx.Response(200, json={"choices": [{"message": message}]})
        result = json.loads(body["messages"][-1]["content"])
        return httpx.Response(200, json={"choices": [{"message": {"role": "assistant", "content": f"Kết quả: {result['status']}"}}]})

    use_mock_transport(monkeypatch, handler)
    data = client.post("/api/ai/chat", json={"message": "Lưu từ postpone vào sổ tay"}).json()
    assert (data["provider"], data["reply"]) == ("deepseek", "Kết quả: exists")
    assert client.get("/api/flashcards/summary").json()["total_cards"] == 5


def test_provider_failure_falls_back_to_offline_mentor(client, seeded, monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "test-key")
    use_mock_transport(monkeypatch, lambda request: httpx.Response(500, json={"error": "boom"}))
    data = client.post("/api/ai/chat", json={"message": "Hôm nay tôi nên học gì?"}).json()
    assert data["provider"] == "offline" and "HTTP 500" in data["reply"] and "Kế hoạch hôm nay" in data["reply"]
    overview = client.post("/api/ai/chat", json={"message": "Xin chào"}).json()
    assert "Tình hình học" in overview["reply"] and "Điểm dự đoán" in overview["reply"]
    assert client.get("/api/ai/status").json()["provider"] == "gemini"


def test_ai_fill_parses_json_and_normalizes_ipa(client, seeded, monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "test-key")
    payload = {"word": "leverage", "ipa": "/ˈlevərɪdʒ/", "word_type": "verb", "category": "General Business",
               "meaning": "tận dụng", "collocations": "leverage data", "paraphrase_pair": "leverage = utilize",
               "example_sentence": "We leverage cloud tools."}
    reply = "```json\n" + json.dumps(payload, ensure_ascii=False) + "\n```"
    use_mock_transport(
        monkeypatch,
        lambda request: httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": reply}]}}]}),
    )
    data = client.post("/api/flashcards/ai-fill", json={"word": "leverage"}).json()
    assert data["meaning"] == "tận dụng" and data["ipa"] == "ˈlevərɪdʒ"


def test_voice_coach_start_and_turn(client, seeded):
    # Test start
    start_res = client.post("/api/ai/voice-coach/start", json={"scenario": "tech_interview"}).json()
    assert start_res["scenario"] == "tech_interview"
    assert "backend engineering" in start_res["ai_opening_statement"]
    assert "/api/tts?" in start_res["audio_url"]

    # Test turn (offline mode fallback)
    turn_res = client.post(
        "/api/ai/voice-coach/turn",
        json={
            "scenario": "tech_interview",
            "user_transcript": "I have two years of experience building Python and FastAPI microservices.",
        },
    ).json()
    assert "spoken_reply" in turn_res and len(turn_res["spoken_reply"]) > 0
    assert "/api/tts?" in turn_res["audio_url"]
    assert "feedback" in turn_res
    assert turn_res["feedback"]["grammar_score"] >= 80
    assert "paraphrase_suggestion" in turn_res["feedback"]


def test_tts_rate_handling_and_voice_coach_audio(client):
    start_res = client.post("/api/ai/voice-coach/start", json={"scenario": "tech_interview"}).json()
    audio_url = start_res["audio_url"]
    assert "rate=%2B0%25" in audio_url

    # All rate variants (0%, +0%, %2B0%25, -10%) must succeed with 200 audio/mpeg
    for rate_param in ["0%", "+0%", "%2B0%25", "-10%"]:
        res = client.get(f"/api/tts?text=Hello+Toeic&voice=en-US-JennyNeural&rate={rate_param}")
        assert res.status_code == 200
        assert res.headers["content-type"] == "audio/mpeg"


def test_vocab_pronunciation_assessment(client, seeded):
    # Test vocabulary pronunciation assessment in offline mode
    fake_audio_base64 = "data:audio/webm;base64,GkXfo59ChoEBQveBAULygQ8UA8G7UxEkEVO"
    res = client.post(
        "/api/ai/pronounce-vocab",
        json={
            "word": "accommodate",
            "expected_ipa": "/əˈkɑːmədeɪt/",
            "audio_base64": fake_audio_base64,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["word"] == "accommodate"
    assert data["score"] >= 75
    assert data["is_accurate"] is True
    assert "vowels" in data["feedback"]
    assert "consonants" in data["feedback"]
    assert "stress" in data["feedback"]


def test_voice_coach_audio_turn_multimodal(client, seeded):
    fake_audio_base64 = "data:audio/webm;base64,GkXfo59ChoEBQveBAULygQ8UA8G7UxEkEVO"
    res = client.post(
        "/api/ai/voice-coach/turn",
        json={
            "scenario": "business_office",
            "audio_base64": fake_audio_base64,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert "spoken_reply" in data and len(data["spoken_reply"]) > 0
    assert "user_transcript" in data
    assert "audio_url" in data
    assert "acoustic_notes" in data["feedback"]


