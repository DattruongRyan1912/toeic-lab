"""Curriculum mapping: question trap tags -> RCA error type + syntax lesson.

Every question's `distractor_analysis` starts with a tag such as "[Bẫy Vị Trí Trạng Từ]".
This module turns that tag into:
  * an RCA code (VOCAB / GRAMMAR / PHONETICS / TRAP / TIME) for the error log, and
  * the syntax lesson (Bài 01-12) that fixes it,
which links mock tests, the error log, learning gaps and lessons together.
Pure functions only (no DB access) so models and services can both use it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

ERROR_TYPES = ("VOCAB", "GRAMMAR", "PHONETICS", "TRAP", "TIME")
LISTENING_PARTS = {"Part 1", "Part 2", "Part 3", "Part 4"}

_TAG_RE = re.compile(r"^\s*\[([^\]]{2,120})\]")
_TENSE_RE = re.compile(r"(?<!\w)thì(?!\w)")


@dataclass(frozen=True)
class TrapClass:
    error_type: str
    lesson_number: Optional[int]


# First match wins, so specific rules come before generic ones
# (e.g. "Từ Loại Trong So Sánh" belongs to comparisons, not word forms).
_RULES = (
    (("nối âm", "nuốt âm", "phát âm", "biến âm", "trọng âm", "accent"), "PHONETICS", None),
    (("similar sound", "đồng âm"), "TRAP", None),
    (("thông tin lệch", "suy diễn", "phủ định", "ngụ ý"), "TRAP", None),
    (("so sánh",), "GRAMMAR", 11),
    (("đảo ngữ", "điều kiện"), "GRAMMAR", 10),
    (("giả định", "cầu khiến"), "GRAMMAR", 9),
    (("quan hệ", "rút gọn", "hai động từ", "phân từ"), "GRAMMAR", 8),
    (("đại từ", "sở hữu"), "GRAMMAR", 7),
    (("__tense__",), "GRAMMAR", 6),
    (("hòa hợp", "chủ-vị", "chủ vị"), "GRAMMAR", 5),
    (("bị động",), "GRAMMAR", 4),
    (("dạng động từ", "mục đích", "to-v", "v-ing"), "GRAMMAR", 3),
    (
        ("giới từ đi kèm", "đi với giới từ", "cụm giới từ", "collocation", "từ vựng", "trái nghĩa", "đồng nghĩa"),
        "VOCAB",
        12,
    ),
    (("liên từ", "giới từ"), "GRAMMAR", 2),
    (("từ loại", "vị trí", "linking", "trạng từ", "tính từ", "danh từ"), "GRAMMAR", 1),
)


def extract_trap_tag(distractor_analysis: Optional[str]) -> Optional[str]:
    """"[Bẫy Từ Loại] A là tính từ..." -> "Bẫy Từ Loại"."""
    if not distractor_analysis:
        return None
    match = _TAG_RE.match(distractor_analysis)
    return match.group(1).strip() if match else None


def _default_error_type(part: Optional[str]) -> str:
    if part in ("Part 5", "Part 6"):
        return "GRAMMAR"
    return "TRAP"


def classify_trap(tag: Optional[str], part: Optional[str] = None) -> TrapClass:
    if not tag:
        return TrapClass(_default_error_type(part), None)
    lowered = tag.lower()
    for keywords, error_type, lesson in _RULES:
        for keyword in keywords:
            hit = bool(_TENSE_RE.search(lowered)) if keyword == "__tense__" else keyword in lowered
            if hit:
                return TrapClass(error_type, lesson)
    return TrapClass(_default_error_type(part), None)


def classify_question(question) -> dict:
    """Works with a TestQuestion ORM object (or anything with the same attributes).

    An explicit `lesson_number` on the question wins over the trap tag. Lessons 01-12 are Part 5/6
    grammar topics, so listening questions (Part 1-4) never map to one.
    """
    tag = extract_trap_tag(getattr(question, "distractor_analysis", None))
    part = getattr(question, "part", None)
    if part in LISTENING_PARTS:
        return {"trap_tag": tag, "error_type": classify_trap(tag, part).error_type, "lesson_number": None}
    trap = classify_trap(tag, part)
    explicit = getattr(question, "lesson_number", None)
    if explicit:
        error_type = trap.error_type if tag else ("VOCAB" if explicit == 12 else _default_error_type(part))
        return {"trap_tag": tag, "error_type": error_type, "lesson_number": int(explicit)}
    return {"trap_tag": tag, "error_type": trap.error_type, "lesson_number": trap.lesson_number}


def normalize_part(value) -> Optional[str]:
    """Accept "Part 5", "part5", "5" -> "Part 5"."""
    if value is None:
        return None
    match = re.search(r"([1-7])", str(value))
    return f"Part {match.group(1)}" if match else None


LESSON_REF_RE = re.compile(r"Bài\s*0?(\d{1,2})", re.IGNORECASE)


def lesson_numbers_in(text: Optional[str]) -> list:
    """Lesson numbers referenced in free text, e.g. roadmap task titles ("Bài 02 ... & Bài 03 ...")."""
    if not text:
        return []
    return [int(n) for n in LESSON_REF_RE.findall(text) if 1 <= int(n) <= 12]
