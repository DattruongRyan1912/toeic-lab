"""Learner flashcards (app database) as Anki rows — shared by export_anki_csv.py and generate_anki_deck.py.

Row layout = fields of the Anki model in generate_anki_deck.py:
Sentence_Front, Domain_Category, Target_Word, IPA, Word_Type, Vietnamese_Meaning, Collocations,
Paraphrase_Equivalence, Full_Sentence_Back. Anki renders fields as HTML, so learner text is escaped.
"""
from __future__ import annotations

import html
import re
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

BLANK = "<span class='blank'>______</span>"
HIGHLIGHT = "<b style='color:#0284c7'>{}</b>"


def _esc(value) -> str:
    return html.escape(value or "", quote=False)


def _find_word(sentence: str, word: str):
    stems = [word]
    if len(word) > 4 and word[-1] in "ey":
        stems.append(word[:-1])  # postpone -> postponed, comply -> complied
    for stem in stems:
        match = re.search(rf"\b{re.escape(stem)}\w*", sentence, re.IGNORECASE)
        if match:
            return match
    return None


def card_row(card) -> tuple:
    sentence = _esc(card.example_sentence)
    word = (card.word or "").strip()
    match = _find_word(sentence, _esc(word))
    if match:
        front = sentence[: match.start()] + BLANK + sentence[match.end():]
        back = sentence[: match.start()] + HIGHLIGHT.format(match.group(0)) + sentence[match.end():]
    else:
        front, back = f"{sentence} ({BLANK})", sentence
    if getattr(card, "example_translation", None):
        back += f"<br><span style='color:#64748b;font-size:0.85em;font-style:italic;'>Dịch: {_esc(card.example_translation)}</span>"
    return (
        front,
        _esc(card.category),
        _esc(word),
        _esc(card.ipa),
        _esc(card.word_type),
        _esc(card.meaning),
        _esc(card.collocations),
        _esc(card.paraphrase_pair),
        back,
    )


def rows_from_db() -> list:
    from server.database import SessionLocal, init_db
    from server.models import Flashcard

    init_db()
    with SessionLocal() as db:
        return [card_row(card) for card in db.query(Flashcard).order_by(Flashcard.id.asc())]
