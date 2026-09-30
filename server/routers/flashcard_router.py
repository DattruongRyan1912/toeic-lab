import json
import re
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from server.database import get_db
from server.models import Flashcard, UserCardSRS
from server.schemas import (
    FlashcardRead, FlashcardCreate, UserCardSRSRead, SRSReviewRequest,
    AIFillVocabRequest, AIFillVocabResponse
)
from server.services.srs_service import calculate_sm2_review
from server.services.ai_agent_service import query_llm

router = APIRouter(prefix="/api/flashcards", tags=["Flashcards & SRS"])

@router.get("", response_model=List[FlashcardRead])
def list_flashcards(
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(100),
    db: Session = Depends(get_db)
):
    query = db.query(Flashcard)
    if category and category != "all":
        query = query.filter(Flashcard.category == category)
    if search:
        s = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Flashcard.word.ilike(s),
                Flashcard.meaning.ilike(s),
                Flashcard.collocations.ilike(s),
                Flashcard.paraphrase_pair.ilike(s)
            )
        )
    return query.order_by(Flashcard.id.asc()).limit(limit).all()

@router.get("/summary")
def get_vocab_summary(user_id: int = 1, db: Session = Depends(get_db)):
    total_cards = db.query(Flashcard).count()
    mastered_cards = db.query(UserCardSRS).filter(
        UserCardSRS.user_id == user_id,
        UserCardSRS.state == "mastered"
    ).count()
    now = datetime.utcnow()
    due_cards = db.query(UserCardSRS).filter(
        UserCardSRS.user_id == user_id,
        UserCardSRS.next_review_at <= now
    ).count()
    
    # Categories breakdown
    categories_dict: Dict[str, int] = {}
    cards = db.query(Flashcard.category).all()
    for (cat,) in cards:
        categories_dict[cat] = categories_dict.get(cat, 0) + 1

    return {
        "total_cards": total_cards,
        "mastered_cards": mastered_cards,
        "due_cards": due_cards,
        "learning_cards": max(0, total_cards - mastered_cards),
        "categories": categories_dict
    }

@router.post("", response_model=FlashcardRead, status_code=status.HTTP_201_CREATED)
def create_flashcard(
    payload: FlashcardCreate,
    user_id: int = 1,
    db: Session = Depends(get_db)
):
    clean_word = payload.word.strip().lower()
    existing = db.query(Flashcard).filter(Flashcard.word == clean_word).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Từ vựng '{clean_word}' đã tồn tại trong Sổ tay!"
        )

    card = Flashcard(
        category=payload.category.strip(),
        word=clean_word,
        ipa=payload.ipa.strip() if payload.ipa else None,
        word_type=payload.word_type.strip() if payload.word_type else None,
        meaning=payload.meaning.strip(),
        collocations=payload.collocations.strip() if payload.collocations else None,
        paraphrase_pair=payload.paraphrase_pair.strip() if payload.paraphrase_pair else None,
        example_sentence=payload.example_sentence.strip(),
        audio_word_url=f"audio/words/{clean_word}.mp3"
    )
    db.add(card)
    db.commit()
    db.refresh(card)

    # Automatically add to UserCardSRS with state 'new'
    srs = UserCardSRS(
        user_id=user_id,
        card_id=card.id,
        state="new",
        next_review_at=datetime.utcnow()
    )
    db.add(srs)
    db.commit()

    return card

@router.delete("/{card_id}")
def delete_flashcard(card_id: int, db: Session = Depends(get_db)):
    card = db.query(Flashcard).filter_by(id=card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Không tìm thấy từ vựng!")
    
    # Delete related SRS
    db.query(UserCardSRS).filter_by(card_id=card_id).delete()
    db.delete(card)
    db.commit()
    return {"status": "success", "message": f"Đã xóa từ '{card.word}' khỏi Sổ tay!"}

@router.post("/ai-fill", response_model=AIFillVocabResponse)
async def ai_fill_vocab(payload: AIFillVocabRequest):
    word = payload.word.strip()
    context = (payload.context or "").strip()

    prompt = f"""Bạn là Senior TOEIC AI Mentor & Lexicographer. Hãy phân tích từ vựng tiếng Anh sau để học viên tự học đạt 800 - 900+ điểm TOEIC:
Từ vựng: "{word}"
Ngữ cảnh đề thi (nếu có): "{context}"

Hãy trả về DUY NHẤT một chuỗi JSON hợp lệ (không kèm bất kỳ văn bản nào khác, không kèm markdown code fences ```json), theo đúng cấu trúc sau:
{{
  "word": "{word.lower()}",
  "ipa": "/phiên âm quốc tế IPA chuẩn/",
  "word_type": "[v] hoặc [n] hoặc [adj] hoặc [adv]",
  "category": "General Business hoặc Finance & Banking hoặc Personnel & HR hoặc Contracts & Agreements hoặc Marketing & Sales hoặc Office Operations hoặc Travel & Hospitality",
  "meaning": "nghĩa tiếng Việt ngắn gọn, sát ngữ cảnh thương mại TOEIC",
  "collocations": "2-3 cụm từ TOEIC ăn điểm đi kèm, ngăn cách bằng dấu phẩy",
  "paraphrase_pair": "cặp từ đồng nghĩa trong bài thi TOEIC (vd: postpone = delay = put off)",
  "example_sentence": "1 câu ví dụ tiếng Anh chuẩn đề thi TOEIC, thay thế từ vựng bằng '______' để học viên tự điền"
}}
"""
    try:
        raw_reply = await query_llm(prompt)
        # Clean markdown code fences if model returned them
        clean_json_str = raw_reply.strip()
        if clean_json_str.startswith("```"):
            clean_json_str = re.sub(r"^```(?:json)?\s*", "", clean_json_str)
            clean_json_str = re.sub(r"\s*```$", "", clean_json_str)
        
        parsed = json.loads(clean_json_str)
        return AIFillVocabResponse(
            word=parsed.get("word", word.lower()),
            ipa=parsed.get("ipa", f"/{word.lower()}/"),
            word_type=parsed.get("word_type", "[n]"),
            category=parsed.get("category", "General Business"),
            meaning=parsed.get("meaning", "Từ vựng kinh doanh"),
            collocations=parsed.get("collocations", f"apply {word}"),
            paraphrase_pair=parsed.get("paraphrase_pair", f"{word} = essential term"),
            example_sentence=parsed.get("example_sentence", f"The manager requested a ______ before the meeting.")
        )
    except Exception:
        # Fallback dictionary for common TOEIC keywords
        return AIFillVocabResponse(
            word=word.lower(),
            ipa=f"/{word.lower()}/",
            word_type="[n/v]",
            category="General Business",
            meaning="Từ vựng cần ghi nhớ trong đề thi TOEIC",
            collocations=f"{word.lower()} procedure, effective {word.lower()}",
            paraphrase_pair=f"{word.lower()} = key business term",
            example_sentence=f"All employees must understand the ______ outlined in the company handbook."
        )

@router.get("/due", response_model=List[UserCardSRSRead])
def get_due_srs_cards(
    user_id: int = 1,
    limit: int = Query(30),
    db: Session = Depends(get_db)
):
    now = datetime.utcnow()
    due_records = db.query(UserCardSRS).filter(
        UserCardSRS.user_id == user_id,
        UserCardSRS.next_review_at <= now
    ).order_by(UserCardSRS.next_review_at.asc()).limit(limit).all()

    if not due_records:
        due_records = db.query(UserCardSRS).filter(
            UserCardSRS.user_id == user_id
        ).order_by(UserCardSRS.last_reviewed_at.asc().nullsfirst()).limit(limit).all()

    return due_records

@router.post("/{card_id}/review", response_model=UserCardSRSRead)
def submit_srs_review(
    card_id: int,
    payload: SRSReviewRequest,
    user_id: int = 1,
    db: Session = Depends(get_db)
):
    srs = db.query(UserCardSRS).filter_by(user_id=user_id, card_id=card_id).first()
    if not srs:
        srs = UserCardSRS(user_id=user_id, card_id=card_id)
        db.add(srs)
        db.commit()
        db.refresh(srs)

    rep, ease, interval, state, next_date = calculate_sm2_review(
        current_repetition=srs.repetition_count,
        current_ease=srs.ease_factor,
        current_interval=srs.interval_days,
        rating=payload.rating
    )

    srs.repetition_count = rep
    srs.ease_factor = ease
    srs.interval_days = interval
    srs.state = state
    srs.next_review_at = next_date.replace(tzinfo=None)
    srs.last_reviewed_at = datetime.utcnow()

    db.commit()
    db.refresh(srs)
    return srs
