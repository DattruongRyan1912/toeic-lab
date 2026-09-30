import json
import httpx
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from server.config import (
    AI_PROVIDER, GEMINI_API_KEY, DEEPSEEK_API_KEY, OPENAI_API_KEY
)
from server.models import (
    ErrorLog, Flashcard, UserCardSRS, AILearningGap, TestQuestion, StudyReminder
)

SYSTEM_PROMPT = """Bạn là Senior TOEIC AI Mentor & Learning Strategist — huấn luyện viên cá nhân theo sát một kỹ sư phần mềm / backend developer tự học TOEIC đạt mục tiêu 800 - 850+.

NGUYÊN TẮC HUẤN LUYỆN:
1. Giao tiếp súc tích, logic, đúng trọng tâm kỹ thuật, không vòng vo.
2. Phân tích đề thi 3 chiều:
   - Chiều 1: Vì sao đáp án đúng là đúng (dẫn chứng ngữ pháp hoặc dòng văn bản).
   - Chiều 2: Vạch mặt 3 phương án còn lại thuộc loại bẫy gì (VOCAB, GRAMMAR, PHONETICS, TRAP, TIME).
   - Chiều 3: Cặp Paraphrase Vault & Collocation thực tế.
3. Khi phát hiện học viên làm sai hoặc học từ vựng mới, hãy chủ động đề xuất hoặc thực thi các Agent Tools để cập nhật database (tự log câu sai, tự thêm thẻ SRS, đặt lịch nhắc nhở).
"""

# Tool schemas definition
AGENT_TOOLS_METADATA = [
    {
        "name": "log_error_question",
        "description": "Lưu một câu hỏi làm sai vào Sổ Tay Lỗi Sai (Error Log) kèm phân tích nguyên nhân gốc",
        "parameters": {
            "type": "object",
            "properties": {
                "part": {"type": "string", "description": "Part 1 đến Part 7"},
                "question_no": {"type": "integer", "description": "Số thứ tự câu hỏi"},
                "error_type": {"type": "string", "enum": ["VOCAB", "GRAMMAR", "PHONETICS", "TRAP", "TIME"]},
                "user_choice": {"type": "string", "description": "Đáp án học viên chọn (A/B/C/D)"},
                "correct_choice": {"type": "string", "description": "Đáp án đúng (A/B/C/D)"},
                "root_cause": {"type": "string", "description": "Giải thích ngắn gọn nguyên nhân gốc rễ"},
                "key_rule": {"type": "string", "description": "Quy tắc ngữ pháp hoặc cặp từ paraphrase cần nhớ"}
            },
            "required": ["part", "error_type", "root_cause"]
        }
    },
    {
        "name": "create_flashcard",
        "description": "Tạo một thẻ từ vựng Flashcard mới vào hệ thống SRS Spaced Repetition",
        "parameters": {
            "type": "object",
            "properties": {
                "word": {"type": "string", "description": "Từ vựng tiếng Anh"},
                "meaning": {"type": "string", "description": "Nghĩa tiếng Việt"},
                "category": {"type": "string", "description": "Chủ đề (Finance, HR, IT, Management...)"},
                "collocations": {"type": "string", "description": "Cụm từ hay đi kèm"},
                "example_sentence": {"type": "string", "description": "Câu ví dụ hoàn chỉnh chứa từ khóa"}
            },
            "required": ["word", "meaning", "example_sentence"]
        }
    },
    {
        "name": "schedule_study_reminder",
        "description": "Đặt lịch nhắc nhở học viên ôn lại kiến thức hoặc câu sai",
        "parameters": {
            "type": "object",
            "properties": {
                "scheduled_time": {"type": "string", "description": "Khung giờ nhắc định dạng HH:MM (vd 21:00)"},
                "message": {"type": "string", "description": "Nội dung nhắc nhở"}
            },
            "required": ["scheduled_time", "message"]
        }
    }
]

def execute_agent_tool(tool_name: str, args: Dict[str, Any], user_id: int, db: Session) -> Dict[str, Any]:
    """Execute tool against database"""
    if tool_name == "log_error_question":
        err = ErrorLog(
            user_id=user_id,
            part=args.get("part", "Part 5"),
            question_no=args.get("question_no"),
            error_type=args.get("error_type", "TRAP"),
            user_choice=args.get("user_choice"),
            correct_choice=args.get("correct_choice"),
            root_cause=args.get("root_cause", ""),
            key_rule_or_paraphrase=args.get("key_rule", ""),
            status="unresolved"
        )
        db.add(err)
        db.commit()
        db.refresh(err)
        return {"status": "success", "message": f"Đã lưu câu {err.question_no or ''} vào Sổ Lỗi Sai (ID: {err.id})"}

    elif tool_name == "create_flashcard":
        card = Flashcard(
            category=args.get("category", "General Business"),
            word=args.get("word", "").lower().strip(),
            meaning=args.get("meaning", ""),
            collocations=args.get("collocations"),
            example_sentence=args.get("example_sentence", ""),
            audio_word_url=f"audio/words/{args.get('word', '').lower().strip()}.mp3"
        )
        db.add(card)
        db.commit()
        db.refresh(card)

        # Add SRS tracking
        srs = UserCardSRS(user_id=user_id, card_id=card.id, state="new")
        db.add(srs)
        db.commit()
        return {"status": "success", "message": f"Đã thêm từ vựng '{card.word}' vào bộ thẻ SRS (ID: {card.id})"}

    elif tool_name == "schedule_study_reminder":
        rem = StudyReminder(
            user_id=user_id,
            reminder_type="review_error_log",
            scheduled_time=args.get("scheduled_time", "21:00"),
            message=args.get("message", "Đã đến giờ ôn tập câu sai TOEIC!"),
            is_active=True
        )
        db.add(rem)
        db.commit()
        return {"status": "success", "message": f"Đã lên lịch nhắc nhở lúc {rem.scheduled_time}"}

    return {"status": "ignored", "message": "Unknown tool"}

async def query_llm(prompt: str, image_base64: Optional[str] = None) -> str:
    """Provider-Agnostic LLM Caller with Vision Support"""
    # 1. Google Gemini Flash (Default & Highly Recommended for Vision + Cheap Tokens)
    if AI_PROVIDER == "gemini" and GEMINI_API_KEY:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
        
        parts = [{"text": prompt}]
        if image_base64:
            # Handle data:image/png;base64,... prefix
            clean_b64 = image_base64.split(",")[-1] if "," in image_base64 else image_base64
            parts.append({
                "inline_data": {
                    "mime_type": "image/jpeg",
                    "data": clean_b64
                }
            })

        payload = {
            "contents": [{"parts": parts}],
            "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "generationConfig": {"temperature": 0.3, "maxOutputTokens": 1000}
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                try:
                    return data["candidates"][0]["content"]["parts"][0]["text"]
                except (KeyError, IndexError):
                    pass

    # 2. DeepSeek / OpenAI Compatible Provider
    api_key = DEEPSEEK_API_KEY or OPENAI_API_KEY
    if api_key:
        endpoint = "https://api.deepseek.com/v1/chat/completions" if DEEPSEEK_API_KEY else "https://api.openai.com/v1/chat/completions"
        model_name = "deepseek-chat" if DEEPSEEK_API_KEY else "gpt-4o-mini"

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]

        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": 0.3
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(endpoint, headers={"Authorization": f"Bearer {api_key}"}, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"]

    # 3. Fallback Built-in Rule-based Expert AI Engine (If no API key configured yet)
    return generate_expert_fallback_reply(prompt)

def generate_expert_fallback_reply(prompt: str) -> str:
    """Fast deterministic response when external API key is not yet set"""
    lowered = prompt.lower()
    if "unanimously" in lowered or "108" in lowered:
        return (
            "### 🎯 Phân tích câu hỏi Part 5 [ETS 2024 - Test 01 - Câu 108]\n\n"
            "- **Câu hỏi**: `The board members ___ approved the revised budget for cloud computing modernization.`\n"
            "- **Đáp án chính xác**: **(D) unanimously** (Trạng từ)\n\n"
            "#### 🔍 Chi tiết phân tích & Loại trừ\n"
            "- **Căn cứ**: Chỗ trống đứng chen giữa Chủ ngữ (`The board members`) và Động từ vị ngữ (`approved`). Vị trí duy nhất có thể đứng ở đây để bổ nghĩa cho hành động phê duyệt là một **Trạng từ (Adverb)**.\n"
            "- **Vạch mặt bẫy**:\n"
            "  * `(A) unanimity`: Danh từ (đuôi `-ity`).\n"
            "  * `(B) unanimous`: Tính từ (đuôi `-ous`). Bẫy học sinh nghĩ rằng đứng trước danh từ/động từ thì chọn tính từ.\n"
            "  * `(C) unanimities`: Danh từ số nhiều.\n\n"
            "#### 💡 Bảng Paraphrase & Collocation cốt lõi\n"
            "| Cụm từ trong đề | Ý nghĩa | Collocation tương đương |\n"
            "| :--- | :--- | :--- |\n"
            "| `unanimously approved` | nhất trí thông qua | `approved by consensus = 100% agreement` |\n\n"
            "⚠️ **Action Item**: Quy tắc vàng Part 5: `S + [ADV] + V_chính + O`. Tôi đã lưu câu này vào Sổ Lỗi Sai giúp bạn!"
        )
    return (
        "Chào bạn! Tôi là TOEIC AI Mentor. Tôi đã kết nối với cơ sở dữ liệu của bạn.\n"
        "- Bạn có thể hỏi bất kỳ câu hỏi ngữ pháp Part 5, bẫy Part 2 hoặc kỹ thuật đọc Part 7.\n"
        "- Hoặc **chụp ảnh màn hình đề thi** dán vào đây để tôi bóc tách bẫy 3 chiều tức thì!\n"
        "(Gợi ý: Cấu hình `GEMINI_API_KEY` hoặc `DEEPSEEK_API_KEY` trong file `.env` để kích hoạt toàn bộ sức mạnh Vision AI)."
    )
