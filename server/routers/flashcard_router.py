from collections import Counter
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from server.database import get_db
from server.config import DEFAULT_USER_ID
from server.deps import current_user_id, optional_learner_id, require_admin, require_learner_user_id
from server.models import Flashcard, SRSReviewLog, User, UserCardSRS
from server.schemas import (
    AIFillVocabRequest,
    AIFillVocabResponse,
    FlashcardCreate,
    FlashcardRead,
    FlashcardSummary,
    SRSReviewRequest,
    TranslateSentenceRequest,
    TranslateSentenceResponse,
    UserCardSRSRead,
)
from server.services import activity, ai_agent_service, ai_usage, insights, vocab_service
from server.services.srs_service import calculate_sm2_review
from server.utils.timeutil import utcnow

router = APIRouter(prefix="/api/flashcards", tags=["Flashcards & SRS"])

AI_FILL_PROMPT = """Phân tích từ vựng tiếng Anh sau cho người luyện TOEIC 800-900+.
Từ vựng: "{word}"
Ngữ cảnh đề thi (nếu có): "{context}"

Trả về DUY NHẤT một object JSON hợp lệ (không markdown, không văn bản khác) với các khóa:
{{
  "word": "{word_lower}",
  "ipa": "phiên âm IPA chuẩn, không kèm dấu /",
  "word_type": "verb | noun | adjective | adverb",
  "category": "General Business | Finance & Banking | Personnel & HR | Contracts & Agreements | Marketing & Sales | Office Operations | Travel & Hospitality",
  "meaning": "nghĩa tiếng Việt ngắn gọn, sát ngữ cảnh thương mại",
  "collocations": "2-3 collocation TOEIC, ngăn cách bằng dấu phẩy",
  "paraphrase_pair": "cặp đồng nghĩa hay gặp, ví dụ: postpone = delay = put off",
  "example_sentence": "1 câu ví dụ chuẩn đề TOEIC có chứa từ này",
  "example_translation": "dịch nghĩa tiếng Việt tự nhiên, chính xác của câu ví dụ trên"
}}"""


TRANSLATION_UNAVAILABLE = "Bản dịch tự động tạm thời chưa khả dụng."


async def translate_sentence_to_vi(sentence: str, keyword: Optional[str] = None) -> Optional[str]:
    """Dịch câu ví dụ tiếng Anh sang tiếng Việt tự nhiên theo chuẩn đề thi TOEIC. None khi AI không dịch được."""
    if ai_agent_service.resolve_provider() is not None:
        prompt = (
            "Dịch câu ví dụ tiếng Anh luyện thi TOEIC sau sang tiếng Việt tự nhiên, chính xác, sát ngữ cảnh thương mại.\n"
            f"Câu gốc: \"{sentence}\"\n"
        )
        if keyword:
            prompt += f"Từ vựng trọng tâm cần lưu ý: \"{keyword}\"\n"
        prompt += (
            "Chỉ trả về DUY NHẤT một chuỗi câu tiếng Việt hoàn chỉnh, không kèm giải thích, không kèm ngoặc kép hay markdown."
        )
        try:
            res = await ai_agent_service.complete_text(prompt)
            clean = res.strip().strip('"').strip("'")
            if clean.startswith("{") and "translation" in clean:
                parsed = ai_agent_service.extract_json_object(clean)
                if parsed and parsed.get("translation"):
                    clean = str(parsed["translation"]).strip()
            if clean:
                return clean
        except Exception:
            pass
    return None


@router.get("", response_model=List[FlashcardRead])
def list_flashcards(
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None, max_length=100),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    query = db.query(Flashcard)
    if category and category != "all":
        query = query.filter(Flashcard.category == category)
    if search and search.strip():
        pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Flashcard.word.ilike(pattern),
                Flashcard.meaning.ilike(pattern),
                Flashcard.collocations.ilike(pattern),
                Flashcard.paraphrase_pair.ilike(pattern),
            )
        )
    return query.order_by(Flashcard.id.desc()).limit(limit).all()


@router.get("/summary", response_model=FlashcardSummary)
def get_vocab_summary(user_id: int = Depends(current_user_id), db: Session = Depends(get_db)):
    insights.ensure_srs_records(db, user_id)
    counts = insights.srs_counts(db, user_id)
    categories = Counter(category for (category,) in db.query(Flashcard.category))
    cat_stats = insights.category_stats(db, user_id)
    return {
        "total_cards": db.query(Flashcard).count(),
        "mastered_cards": counts["mastered"],
        "due_cards": counts["session_size"],
        "review_due": counts["review_due"],
        "new_available": counts["new_available"],
        "new_cards": counts["new_total"],
        "learning_cards": counts["learning"],
        "reviewed_today": counts["reviewed_today"],
        "new_cards_per_day": counts["new_cards_per_day"],
        "categories": dict(categories),
        "category_stats": cat_stats,
    }


@router.post("", response_model=FlashcardRead, status_code=status.HTTP_201_CREATED)
def create_flashcard(payload: FlashcardCreate, user_id: int = Depends(require_learner_user_id), db: Session = Depends(get_db)):
    try:
        card, created = vocab_service.create_card(db, user_id, payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    if not created:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Từ vựng '{card.word}' đã có trong Sổ tay!")
    return card


@router.delete("/{card_id}")
def delete_flashcard(card_id: int, _admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Cards are shared by every learner, so only admins may delete them."""
    card = db.get(Flashcard, card_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy từ vựng!")
    word = card.word
    vocab_service.delete_card(db, card)
    return {"status": "success", "message": f"Đã xóa từ '{word}' khỏi Sổ tay!"}


@router.post("/ai-fill", response_model=AIFillVocabResponse, dependencies=[Depends(ai_usage.guard("ai_fill"))])
async def ai_fill_vocab(payload: AIFillVocabRequest, db: Session = Depends(get_db)):
    word = payload.word.strip()
    existing = vocab_service.find_card(db, word)
    if existing is not None:
        raise HTTPException(status_code=409, detail=f"Từ '{existing.word}' đã có trong Sổ tay (#{existing.id}).")
    if ai_agent_service.resolve_provider() is None:
        raise HTTPException(
            status_code=503,
            detail="AI chưa được cấu hình (thiếu GEMINI_API_KEY / DEEPSEEK_API_KEY / OPENAI_API_KEY) — hãy nhập thủ công.",
        )
    prompt = AI_FILL_PROMPT.format(word=word, word_lower=word.lower(), context=(payload.context or "").strip())
    try:
        raw = await ai_agent_service.complete_text(prompt)
    except ai_agent_service.LLMError as exc:
        raise HTTPException(status_code=502, detail=f"AI không phản hồi: {exc}")
    parsed = ai_agent_service.extract_json_object(raw)
    if not parsed or not parsed.get("meaning"):
        raise HTTPException(status_code=502, detail="AI trả về dữ liệu không hợp lệ, hãy thử lại.")

    def text(key: str) -> str:
        value = parsed.get(key)
        return str(value).strip() if value is not None else ""

    return AIFillVocabResponse(
        word=text("word") or word.lower(),
        ipa=vocab_service.normalize_ipa(text("ipa")) or "",
        word_type=text("word_type"),
        category=text("category") or "General Business",
        meaning=text("meaning"),
        collocations=text("collocations"),
        paraphrase_pair=text("paraphrase_pair"),
        example_sentence=text("example_sentence"),
        example_translation=text("example_translation") or None,
    )


@router.post("/translate-sentence", response_model=TranslateSentenceResponse, dependencies=[Depends(ai_usage.guard("translate"))])
async def translate_sentence_endpoint(payload: TranslateSentenceRequest):
    sentence = payload.sentence.strip()
    if not sentence:
        raise HTTPException(status_code=400, detail="Câu không được để trống.")
    trans = await translate_sentence_to_vi(sentence) or TRANSLATION_UNAVAILABLE
    return TranslateSentenceResponse(sentence=sentence, translation=trans)


@router.post("/{card_id}/translate-example", response_model=FlashcardRead, dependencies=[Depends(ai_usage.guard("translate"))])
async def translate_flashcard_example(
    card_id: int,
    learner_id: Optional[int] = Depends(optional_learner_id),
    db: Session = Depends(get_db),
):
    """Translate a card's example. Signed-in learners save it on the shared card; guests only see it."""
    card = db.get(Flashcard, card_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy từ vựng!")

    if card.example_translation:
        return card

    if not card.example_sentence or card.example_sentence.strip() in ("", "Example sentence pending."):
        raise HTTPException(status_code=400, detail="Thẻ này chưa có câu ví dụ để dịch.")

    trans = await translate_sentence_to_vi(vocab_service.plain_sentence(card.example_sentence, card.word), keyword=card.word)
    if trans is None:  # never store a failure message on a card shared by every learner
        raise HTTPException(status_code=503, detail="AI chưa dịch được câu này, vui lòng thử lại sau.")
    if learner_id is None:  # guests are read-only: answer without writing to the shared card
        return FlashcardRead.model_validate(card).model_copy(update={"example_translation": trans})
    card.example_translation = trans
    db.commit()
    db.refresh(card)
    return card


@router.get("/due", response_model=List[UserCardSRSRead])
def get_due_srs_cards(
    category: Optional[str] = Query(None, description="Lọc theo chủ đề từ vựng"),
    mode: str = Query("srs", description="'srs': chuẩn SM-2, 'all'/'cram': luyện tập toàn bộ chủ đề, 'new': từ mới"),
    limit: int = Query(30, ge=1, le=200),
    user_id: int = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    """Only cards that are actually due, or cards in a chosen category / study mode."""
    insights.ensure_srs_records(db, user_id)
    return insights.due_queue(db, user_id, limit=limit, category=category, mode=mode)


@router.post("/{card_id}/review", response_model=UserCardSRSRead)
def submit_srs_review(
    card_id: int,
    payload: SRSReviewRequest,
    learner_id: Optional[int] = Depends(optional_learner_id),
    db: Session = Depends(get_db),
):
    """Apply an SM-2 review. Guests and early (cram) reviews of cards that are not due leave the schedule alone."""
    if db.get(Flashcard, card_id) is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy từ vựng!")
    user_id = learner_id or DEFAULT_USER_ID
    srs = db.query(UserCardSRS).filter_by(user_id=user_id, card_id=card_id).first()
    if learner_id is None:
        if srs is None:
            raise HTTPException(status_code=401, detail="Vui lòng đăng nhập để lưu tiến độ ôn từ vựng")
        return srs  # guests practise on the demo deck without changing it
    if srs is None:
        srs = UserCardSRS(user_id=user_id, card_id=card_id, state="new", next_review_at=utcnow())
        db.add(srs)
        db.flush()

    prev_state = srs.state or "new"
    if prev_state != "new" and srs.next_review_at and srs.next_review_at >= insights.srs_due_before():
        # Reviewing ahead of schedule ("Luyện toàn bộ"/cram): count the study time only. Applying SM-2
        # here would push intervals out (or reset them) from reviews that were not due.
        activity.track(db, user_id, "srs", activity.card_seconds(payload.duration_ms), items=1, correct=int(payload.rating >= 3))
        db.commit()
        return srs

    repetition, ease, interval, state, next_review = calculate_sm2_review(
        current_repetition=srs.repetition_count,
        current_ease=srs.ease_factor,
        current_interval=srs.interval_days,
        rating=payload.rating,
    )
    now = utcnow()
    srs.repetition_count = repetition
    srs.ease_factor = ease
    srs.interval_days = interval
    srs.state = state
    srs.next_review_at = next_review
    srs.last_reviewed_at = now
    db.add(
        SRSReviewLog(
            user_id=user_id,
            card_id=card_id,
            rating=payload.rating,
            prev_state=prev_state,
            new_state=state,
            interval_days=interval,
            duration_ms=payload.duration_ms,
            reviewed_at=now,
        )
    )
    activity.track(db, user_id, "srs", activity.card_seconds(payload.duration_ms), items=1, correct=int(payload.rating >= 3), at=now)
    db.commit()
    db.refresh(srs)
    return srs
