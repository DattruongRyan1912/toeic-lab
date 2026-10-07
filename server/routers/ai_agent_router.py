import json
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from server import config
from server.database import get_db
from server.deps import current_user_id, is_test_mode, require_learner_user_id
from server.models import AIMessage
from server.schemas import (
    AIActionRead,
    AIChatRequest,
    AIChatResponse,
    AIMessageRead,
    AIStatus,
    AIToolExecuteRequest,
    AIToolInfo,
    VoiceCoachStartRequest,
    VoiceCoachStartResponse,
    VoiceCoachTurnRequest,
    VoiceCoachTurnResponse,
    VocabPronounceRequest,
    VocabPronounceResponse,
)
from server.services import activity, agent_tools, insights, learner_context, voice_coach_service
from server.services import ai_agent_service as agent
from server.utils import rate_limit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai", tags=["AI Mentor Copilot"])


@router.get("/status", response_model=AIStatus)
def ai_status():
    return agent.provider_status()


@router.get("/tools", response_model=List[AIToolInfo])
def list_tools():
    """What the mentor can read and change (shown in Settings → AI)."""
    return agent_tools.catalog()


@router.get("/history", response_model=List[AIMessageRead])
def chat_history(
    limit: int = Query(50, ge=1, le=500),
    user_id: int = Depends(require_learner_user_id),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(AIMessage)
        .filter(AIMessage.user_id == user_id, AIMessage.role.in_(("user", "assistant")))
        .order_by(AIMessage.id.desc())
        .limit(limit)
        .all()
    )
    result = []
    for row in reversed(rows):
        try:
            actions = json.loads(row.tool_calls_json) if row.tool_calls_json else []
        except ValueError:
            actions = []
        result.append({"id": row.id, "role": row.role, "content": row.content, "created_at": row.created_at, "actions": actions or []})
    return result


@router.delete("/history")
def clear_history(user_id: int = Depends(require_learner_user_id), db: Session = Depends(get_db)):
    deleted = db.query(AIMessage).filter(AIMessage.user_id == user_id).delete()
    db.commit()
    return {"status": "cleared", "deleted": deleted}


@router.get("/actions", response_model=List[AIActionRead])
def list_actions(
    limit: int = Query(50, ge=1, le=200),
    user_id: int = Depends(require_learner_user_id),
    db: Session = Depends(get_db),
):
    """Audit trail of every data change made through agent tools (AI mentor or one-click suggestions)."""
    return agent_tools.recent_actions(db, user_id, limit)


@router.post("/actions/{action_id}/undo")
def undo_action(action_id: int, user_id: int = Depends(require_learner_user_id), db: Session = Depends(get_db)):
    try:
        return agent_tools.undo_action(db, user_id, action_id)
    except agent_tools.ToolError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/actions/execute")
def execute_tool(payload: AIToolExecuteRequest, user_id: int = Depends(require_learner_user_id), db: Session = Depends(get_db)):
    """Run one tool directly (one-click coach suggestions). Same validation, audit and undo as the AI."""
    if payload.tool not in agent_tools.REGISTRY:
        raise HTTPException(status_code=404, detail=f"Công cụ không tồn tại: {payload.tool}")
    ctx = agent_tools.ToolContext(db=db, user_id=user_id, source=payload.source)
    result = agent_tools.execute(ctx, payload.tool, payload.args)
    if result["status"] == "error":
        raise HTTPException(status_code=422, detail=result["message"])
    return result


@router.post("/chat", response_model=AIChatResponse, dependencies=[Depends(rate_limit.limit_ai)])
async def chat_with_ai_mentor(
    payload: AIChatRequest,
    user_id: int = Depends(require_learner_user_id),
    db: Session = Depends(get_db),
):
    # payload.user_id is a test/CLI convenience only; real requests always act on the token owner.
    target_user_id = (payload.user_id or user_id) if user_id == config.DEFAULT_USER_ID and is_test_mode() else user_id
    insights.get_or_create_user(db, target_user_id)
    question = agent.resolve_question(db, payload.question_id)
    titles = insights.lesson_titles(db)
    status = agent.provider_status()
    context_text, dashboard = learner_context.build(db, target_user_id, ai_online=not status["offline"])
    history = agent.load_history(db, target_user_id, config.AI_HISTORY_TURNS) if payload.include_history else []

    actions: list = []
    executor = agent.make_tool_executor(db, target_user_id, question, sink=actions)
    system_prompt = agent.build_system_prompt(
        context_text, agent.question_context(question, titles) if question else None, payload.page_context
    )
    provider, model = "offline", None
    try:
        result = await agent.run_agent(
            system_prompt=system_prompt,
            history=history,
            message=payload.message,
            image_base64=payload.image_base64,
            tool_executor=executor,
        )
        reply, provider, model = result.reply, result.provider, result.model
    except agent.LLMError as exc:
        reason = "chưa cấu hình GEMINI_API_KEY / DEEPSEEK_API_KEY / OPENAI_API_KEY" if status["offline"] else str(exc)
        if not status["offline"]:
            logger.warning("AI provider failed, using offline mentor: %s", exc)
        reply = agent.offline_reply(db, payload.message, question, dashboard, reason, executor=executor, user_id=target_user_id)
        if actions and not any(a.get("writes") for a in actions):
            actions = []  # offline read-only lookups are not "actions"

    db.add(
        AIMessage(
            user_id=target_user_id,
            role="user",
            content=payload.message,
            image_url="[image uploaded]" if payload.image_base64 else None,
        )
    )
    db.add(
        AIMessage(
            user_id=target_user_id,
            role="assistant",
            content=reply,
            tool_calls_json=json.dumps(actions, ensure_ascii=False, default=str) if actions else None,
        )
    )
    activity.track(db, target_user_id, "mentor", activity.MENTOR_QUESTION_SECONDS, items=1)
    db.commit()

    return AIChatResponse(
        reply=reply,
        actions_taken=actions,
        suggested_questions=agent.suggested_questions(question, payload.page_context, titles),
        provider=provider,
        model=model,
    )


@router.post("/voice-coach/start", response_model=VoiceCoachStartResponse, dependencies=[Depends(rate_limit.limit_ai)])
def voice_coach_start(
    payload: VoiceCoachStartRequest,
    user_id: int = Depends(require_learner_user_id),
):
    """Bắt đầu phiên đàm thoại giọng nói 1-1 theo kịch bản."""
    return voice_coach_service.start_voice_session(
        scenario=payload.scenario,
        accent=payload.accent or "en-US-JennyNeural",
    )


@router.post("/voice-coach/turn", response_model=VoiceCoachTurnResponse, dependencies=[Depends(rate_limit.limit_ai)])
async def voice_coach_turn(
    payload: VoiceCoachTurnRequest,
    user_id: int = Depends(require_learner_user_id),
    db: Session = Depends(get_db),
):
    """Xử lý một lượt phát biểu của học viên (qua text hoặc audio trực tiếp), đối đáp và chấm điểm."""
    insights.get_or_create_user(db, user_id)
    activity.track(db, user_id, "mentor", activity.MENTOR_QUESTION_SECONDS, items=1)
    db.commit()

    return await voice_coach_service.process_voice_turn(
        scenario=payload.scenario,
        user_transcript=payload.user_transcript,
        audio_base64=payload.audio_base64,
        history=payload.history,
        accent=payload.accent or "en-US-JennyNeural",
    )


@router.post("/pronounce-vocab", response_model=VocabPronounceResponse, dependencies=[Depends(rate_limit.limit_ai)])
async def pronounce_vocab(
    payload: VocabPronounceRequest,
    user_id: int = Depends(require_learner_user_id),
    db: Session = Depends(get_db),
):
    """Lắng nghe đoạn thu âm giọng đọc và đánh giá chi tiết độ chính xác khi phát âm từ vựng."""
    insights.get_or_create_user(db, user_id)
    activity.track(db, user_id, "vocab", 15, items=1)
    db.commit()

    return await voice_coach_service.evaluate_vocab_pronunciation(
        word=payload.word,
        expected_ipa=payload.expected_ipa,
        audio_base64=payload.audio_base64,
        user_transcript=payload.user_transcript,
    )
