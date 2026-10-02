"""Flashcard writes shared by the REST router and the AI mentor tool."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from server.models import Flashcard, SRSReviewLog, UserCardSRS
from server.utils.timeutil import utcnow


def _clean(value, max_len: Optional[int] = None) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text[:max_len] if max_len else text


def normalize_ipa(value) -> Optional[str]:
    """Store IPA without surrounding slashes ("/pəʊstˈpəʊn/" -> "pəʊstˈpəʊn"); the UI adds them."""
    text = _clean(value, 100)
    if not text:
        return None
    return text.strip("/[] ").strip() or None


def find_card(db: Session, word: str) -> Optional[Flashcard]:
    return db.query(Flashcard).filter(func.lower(Flashcard.word) == word.strip().lower()).first()


def create_card(db: Session, user_id: int, data: dict) -> tuple:
    """Returns (card, created). An existing word is returned untouched with created=False."""
    word = (_clean(data.get("word"), 100) or "").lower()
    meaning = _clean(data.get("meaning"))
    if not word or not meaning:
        raise ValueError("Cần có từ vựng và nghĩa tiếng Việt")
    existing = find_card(db, word)
    if existing is not None:
        return existing, False

    card = Flashcard(
        category=_clean(data.get("category"), 100) or "General Business",
        word=word,
        ipa=normalize_ipa(data.get("ipa")),
        word_type=_clean(data.get("word_type"), 50),
        meaning=meaning,
        collocations=_clean(data.get("collocations")),
        paraphrase_pair=_clean(data.get("paraphrase_pair")),
        example_sentence=_clean(data.get("example_sentence")) or "Example sentence pending.",
        example_translation=_clean(data.get("example_translation")),
    )
    db.add(card)
    db.flush()
    db.add(UserCardSRS(user_id=user_id, card_id=card.id, state="new", next_review_at=utcnow()))
    db.commit()
    db.refresh(card)
    return card, True


def delete_card(db: Session, card: Flashcard) -> None:
    db.query(UserCardSRS).filter_by(card_id=card.id).delete()
    db.query(SRSReviewLog).filter_by(card_id=card.id).delete()
    db.delete(card)
    db.commit()
