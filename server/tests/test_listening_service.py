import pytest
from server.services import listening_service


def test_phonetic_cues_detection():
    # Flap-T detection
    cues_water = listening_service.detect_phonetic_cues("The water in the bottle is cold.")
    assert any("Flap-T" in c for c in cues_water)

    # Consonant to vowel linking
    cues_link = listening_service.detect_phonetic_cues("Please check out of the room.")
    assert any("Nối âm" in c for c in cues_link)

    # Elision
    cues_elision = listening_service.detect_phonetic_cues("He was here last night.")
    assert any("Nuốt âm" in c for c in cues_elision)


def test_diff_transcription():
    # Exact match
    res_exact = listening_service.diff_transcription(
        learner_text="They're discussing the project schedule.",
        target_transcript="They're discussing the project schedule."
    )
    assert res_exact["accuracy"] == 100.0
    assert all(t["status"] == "correct" for t in res_exact["tokens"])

    # Typos and omissions
    res_diff = listening_service.diff_transcription(
        learner_text="The repo will be finish tomorow",
        target_transcript="The report will be finished tomorrow."
    )
    assert res_diff["accuracy"] < 100.0
    assert any(t["status"] in ("misspelled", "missing") for t in res_diff["tokens"])


def test_listening_api_endpoints(client, seeded):
    # Check exercises list
    resp = client.get("/api/listening/exercises")
    assert resp.status_code == 200
    exercises = resp.json()
    assert isinstance(exercises, list)
    assert len(exercises) > 0

    first_id = exercises[0]["id"]

    # Check dictation diff API
    check_payload = {
        "question_id": first_id,
        "learner_text": "They are working on the project."
    }
    resp_check = client.post("/api/listening/check-dictation", json=check_payload)
    assert resp_check.status_code == 200
    data = resp_check.json()
    assert "accuracy" in data
    assert "tokens" in data
    assert "phonetic_cues" in data

    # Check activity tracking
    track_payload = {
        "mode": "dictation",
        "seconds": 45,
        "items": 1
    }
    resp_track = client.post("/api/listening/track", json=track_payload)
    assert resp_track.status_code == 200
    assert resp_track.json()["status"] == "tracked"


def test_evaluate_shadowing_api(client, seeded):
    # Good pronunciation attempt
    payload = {
        "target_sentence": "A woman is typing on a laptop computer at an office workstation.",
        "user_transcript": "a woman is typing on a laptop computer at an office workstation",
        "phonetic_cues": ["Biến âm Flap-T trong 'computer'"],
        "accent": "US",
    }
    resp = client.post("/api/listening/evaluate-shadowing", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "overall_score" in data
    assert "accuracy_score" in data
    assert "fluency_score" in data
    assert data["overall_score"] >= 70
    assert data["is_passing"] is True
    assert isinstance(data["words"], list)
    assert len(data["words"]) > 0
    assert isinstance(data["coaching_tips"], list)
    assert len(data["coaching_tips"]) > 0

    # Incomplete / flawed attempt
    payload_bad = {
        "target_sentence": "A woman is typing on a laptop computer at an office workstation.",
        "user_transcript": "a woman is typing laptop",
    }
    resp_bad = client.post("/api/listening/evaluate-shadowing", json=payload_bad)
    assert resp_bad.status_code == 200
    data_bad = resp_bad.json()
    assert data_bad["overall_score"] < data["overall_score"]
    assert any(w["status"] in ("needs_work", "missed") for w in data_bad["words"])

    # Missing transcript (browser without STT / guidance mode fallback)
    payload_empty = {
        "target_sentence": "A woman is typing on a laptop computer at an office workstation.",
        "user_transcript": None,
    }
    resp_empty = client.post("/api/listening/evaluate-shadowing", json=payload_empty)
    assert resp_empty.status_code == 200
    data_empty = resp_empty.json()
    assert data_empty["overall_score"] >= 70
    assert data_empty["is_passing"] is True
    assert data_empty.get("is_guidance_fallback") is True


def test_evaluate_shadowing_with_audio_mock(client, monkeypatch):
    from server.services import ai_agent_service, voice_coach_service

    # Mock audio provider to return Gemini
    provider = ai_agent_service.ProviderInfo(
        name="gemini",
        model="gemini-3.5-flash",
        api_key="mock-key",
        base_url="https://generativelanguage.googleapis.com/v1beta",
        vision=True,
    )
    monkeypatch.setattr(ai_agent_service, "resolve_audio_provider", lambda: provider)

    mock_gemini_reply = """```json
    {
      "overall_score": 92,
      "accuracy_score": 95,
      "fluency_score": 90,
      "recognized_transcript": "We must postpone the meeting.",
      "verdict": "Xuất sắc (Native-like)",
      "words": [
        {"word": "We", "status": "perfect", "note": "Rõ ràng"},
        {"word": "must", "status": "perfect", "note": "Nuốt âm /t/ tốt"},
        {"word": "postpone", "status": "perfect", "note": "Trọng âm âm 2 chuẩn"},
        {"word": "the", "status": "perfect", "note": "Tự nhiên"},
        {"word": "meeting", "status": "perfect", "note": "Âm đuôi chuẩn"}
      ],
      "connected_speech_feedback": "Nối âm rất mượt mà.",
      "coaching_tips": ["Tiếp tục phát huy!"]
    }
    ```"""

    async def fake_complete_with_audio(prompt, audio_base64, system_prompt=None):
        return mock_gemini_reply

    monkeypatch.setattr(ai_agent_service, "complete_with_audio", fake_complete_with_audio)

    payload = {
        "target_sentence": "We must postpone the meeting.",
        "audio_base64": "data:audio/webm;codecs=opus;base64,AAAA",
    }
    resp = client.post("/api/listening/evaluate-shadowing", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["overall_score"] == 92
    assert data["provider"] == "gemini"
    assert data["model"] == "gemini-3.5-flash"
    assert data["analysis_mode"] == "audio_multimodal"
    assert data["recognized_transcript"] == "We must postpone the meeting."
    assert len(data["words"]) == 5

