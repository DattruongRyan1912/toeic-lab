import asyncio
import httpx

async def test_apis():
    base_url = "http://127.0.0.1:8000"
    async with httpx.AsyncClient(base_url=base_url, timeout=10.0) as client:
        # 1. Health check
        res = await client.get("/health")
        print("1. Health:", res.status_code, res.json())

        # 2. Dashboard stats
        res = await client.get("/api/dashboard/stats")
        print("2. Dashboard Stats:", res.status_code, res.json())

        # 3. Roadmaps
        res = await client.get("/api/roadmaps")
        roadmap = res.json()
        print("3. Roadmap:", res.status_code, f"Title: {roadmap.get('title')}")
        if roadmap.get("sprint_tasks"):
            print("   First task:", roadmap["sprint_tasks"][0]["task_title"])

        # 4. Flashcards Due
        res = await client.get("/api/flashcards/due")
        cards = res.json()
        print("4. Flashcards Due:", res.status_code, f"Found {len(cards)} due cards")
        if cards:
            card_id = cards[0]["id"]
            # Test SM-2 review
            review_res = await client.post(f"/api/flashcards/{card_id}/review", json={"rating": 4})
            print("   Review Card 1 (Good):", review_res.status_code, review_res.json())

        # 5. Error Logs
        res = await client.get("/api/error-logs")
        errors = res.json()
        print("5. Error Logs:", res.status_code, f"Found {len(errors)} error logs")

        # 6. Add new error log
        new_err = {
            "test_id": "ETS 2024 Test 02",
            "part": "Part 5",
            "question_no": 105,
            "error_type": "GRAMMAR",
            "user_choice": "A",
            "correct_choice": "C",
            "root_cause": "Nhầm lẫn giữa tính từ đuôi -ive và danh từ",
            "key_rule_or_paraphrase": "representative là danh từ đếm được (người đại diện)"
        }
        res = await client.post("/api/error-logs", json=new_err)
        print("6. Created Error Log:", res.status_code, res.json())

        # 7. Knowledge Lessons
        res = await client.get("/api/knowledge/lessons")
        lessons = res.json()
        print("7. Lessons:", res.status_code, f"Found {len(lessons)} lessons")

        # 8. Reminders
        res = await client.get("/api/reminders")
        reminders = res.json()
        print("8. Reminders:", res.status_code, f"Found {len(reminders)} reminders")

        # 9. AI Chat (Question Pointer)
        chat_payload = {
            "message": "Tôi vừa làm sai câu này: đề ETS 2024 Test 01 Part 5 câu 108, tôi chọn B nhưng đáp án là D vì thiếu trạng từ. Hãy ghi nhận câu này vào sổ lỗi giúp tôi.",
            "question_pointer": {
                "test_name": "ETS 2024 Test 01",
                "part": 5,
                "question_num": 108
            }
        }
        res = await client.post("/api/ai/chat", json=chat_payload)
        ai_resp = res.json()
        print("9. AI Chat Response:")
        print("   Status:", res.status_code)
        print("   Reply length:", len(ai_resp.get("reply", "")))
        print("   Executed actions:", ai_resp.get("executed_actions"))

        # Verify error log was auto-created by AI Agent
        err_res = await client.get("/api/error-logs")
        print("10. Error Logs after AI Tool Call:", len(err_res.json()), "logs in DB")

if __name__ == "__main__":
    asyncio.run(test_apis())
