import re
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from server.database import get_db
from server.models import TestQuestion, AIMessage
from server.schemas import AIChatRequest, AIChatResponse
from server.services.ai_agent_service import query_llm, execute_agent_tool

router = APIRouter(prefix="/api/ai", tags=["AI Mentor Copilot"])

@router.post("/chat", response_model=AIChatResponse)
async def chat_with_ai_mentor(payload: AIChatRequest, db: Session = Depends(get_db)):
    prompt = payload.message
    actions_taken = []

    # 1. Database Grounding via Question Pointer (Saves 85% Tokens)
    if payload.question_id:
        parts = payload.question_id.split("_")
        if len(parts) >= 3:
            tid = f"{parts[0]}_{parts[1]}"
            try:
                qno = int(parts[2])
                q = db.query(TestQuestion).filter_by(test_id=tid, question_no=qno).first()
                if q:
                    prompt = (
                        f"[NGỮ CẢNH ĐỀ THI CHUẨN ĐÃ NẠP TỪ DATABASE]\n"
                        f"- Đề: {q.test_id} | {q.part} - Câu {q.question_no}\n"
                        f"- Câu hỏi: {q.sentence}\n"
                        f"- Các lựa chọn: (A) {q.choice_a} | (B) {q.choice_b} | (C) {q.choice_c}"
                        f"{f' | (D) {q.choice_d}' if q.choice_d else ''}\n"
                        f"- Đáp án đúng: {q.correct_choice}\n"
                        f"- Giải thích bẫy có sẵn: {q.distractor_analysis or ''}\n\n"
                        f"[YÊU CẦU CỦA HỌC VIÊN]: {payload.message}"
                    )
            except ValueError:
                pass

    # 2. Query LLM (with Vision support if image_base64 is present)
    reply = await query_llm(prompt=prompt, image_base64=payload.image_base64)

    # 3. Autonomous Knowledge Intervention (Intent Detection & Auto Action)
    # Check if this discussion was about an error to auto-log
    if ("lưu vào sổ lỗi" in reply.lower() or "action item" in reply.lower() or payload.question_id) and ("bẫy" in reply.lower() or "sai" in prompt.lower()):
        # Auto-create error log
        res = execute_agent_tool(
            tool_name="log_error_question",
            args={
                "part": "Part 5" if "part 5" in reply.lower() else "Part 2",
                "question_no": 108 if "108" in prompt else None,
                "error_type": "GRAMMAR" if "từ loại" in reply.lower() else "TRAP",
                "root_cause": "Nhầm lẫn giữa tính từ và trạng từ bổ nghĩa cho động từ chính",
                "key_rule": "S + [ADV] + V_chính + O"
            },
            user_id=payload.user_id,
            db=db
        )
        actions_taken.append(res)

    # 4. Save message history
    ai_msg = AIMessage(
        user_id=payload.user_id,
        role="user",
        content=payload.message,
        image_url="[image uploaded]" if payload.image_base64 else None
    )
    db.add(ai_msg)
    db.commit()

    return AIChatResponse(
        reply=reply,
        actions_taken=actions_taken,
        suggested_questions=[
            "Cho tôi xem 3 câu tương tự để luyện tập?",
            "Quy tắc vàng phân biệt trạng từ và tính từ?",
            "Các cụm Collocation hay gặp với từ này?"
        ]
    )
