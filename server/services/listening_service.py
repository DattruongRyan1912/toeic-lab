"""Listening service: Dictation diffing, connected speech detection, and exercise management."""

from __future__ import annotations

import difflib
import re
from typing import List, Optional
from sqlalchemy.orm import Session

from server.models import TestQuestion
from server.services import activity, practice_service

_CLEAN_RE = re.compile(r"[^\w\s']")
_APOSTROPHES = str.maketrans({"\u2019": "'", "\u2018": "'", "`": "'"})  # iOS/macOS keyboards type curly quotes
_CHOICE_LABEL_RE = re.compile(r"\(\s*[A-Da-d]\s*\)")  # "(A)" labels in Part 1/2 transcripts are not spoken words
_WORD_SPLIT_RE = re.compile(r"[\s\-\u2013\u2014/]+")  # "work-order" and "work order" are the same words

# Contraction -> spoken full forms. Both sides are reduced to the contraction so "It's" == "It is".
_CONTRACTIONS = {
    "can't": ("can not",), "won't": ("will not",), "don't": ("do not",), "doesn't": ("does not",), "didn't": ("did not",),
    "isn't": ("is not",), "aren't": ("are not",), "wasn't": ("was not",), "weren't": ("were not",),
    "haven't": ("have not",), "hasn't": ("has not",), "hadn't": ("had not",),
    "wouldn't": ("would not",), "shouldn't": ("should not",), "couldn't": ("could not",),
    "it's": ("it is", "it has"), "he's": ("he is", "he has"), "she's": ("she is", "she has"), "that's": ("that is",),
    "there's": ("there is",), "what's": ("what is",), "who's": ("who is",), "where's": ("where is",), "here's": ("here is",),
    "let's": ("let us",), "i'm": ("i am",),
    **{f"{p}'re": (f"{p} are",) for p in ("you", "we", "they")},
    **{f"{p}'ve": (f"{p} have",) for p in ("i", "you", "we", "they")},
    **{f"{p}'ll": (f"{p} will",) for p in ("i", "you", "he", "she", "it", "we", "they")},
    **{f"{p}'d": (f"{p} would", f"{p} had") for p in ("i", "you", "he", "she", "we", "they")},
}
_EXPANSIONS = {tuple(full.split()): short for short, fulls in _CONTRACTIONS.items() for full in fulls}
_NUMBER_WORDS = {
    word: str(value)
    for value, word in enumerate(
        "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen "
        "sixteen seventeen eighteen nineteen twenty".split()
    )
}
_NUMBER_WORDS.update({"thirty": "30", "forty": "40", "fifty": "50", "sixty": "60", "seventy": "70", "eighty": "80", "ninety": "90"})
_ORDINALS = dict(zip("first second third fourth fifth sixth seventh eighth ninth tenth".split(),
                     "1st 2nd 3rd 4th 5th 6th 7th 8th 9th 10th".split()))
_ALIASES = {"cannot": "can't", **_NUMBER_WORDS, **_ORDINALS}

# Key phonetics keywords for TOEIC connected speech
_FLAP_T = {"water", "meeting", "better", "waiting", "city", "computer", "shuttle", "quarter", "party", "hospital"}
_ELISION = {"last night", "next day", "most common", "first time", "hold on", "left turn", "stand by"}


def normalize_token(token: str) -> str:
    cleaned = _CLEAN_RE.sub("", token.translate(_APOSTROPHES).lower()).strip("'")
    return _ALIASES.get(cleaned, cleaned)


def word_units(text: str) -> list:
    """(display, canonical) units: curly quotes, choice labels, hyphens, numbers and contractions normalised."""
    text = _CHOICE_LABEL_RE.sub(" ", text.translate(_APOSTROPHES))
    units = [(word, normalize_token(word)) for word in _WORD_SPLIT_RE.split(text) if word]
    units = [unit for unit in units if unit[1]]
    merged, i = [], 0
    while i < len(units):
        pair = (units[i][1], units[i + 1][1]) if i + 1 < len(units) else None
        if pair in _EXPANSIONS:
            merged.append((f"{units[i][0]} {units[i + 1][0]}", _EXPANSIONS[pair]))
            i += 2
        else:
            merged.append(units[i])
            i += 1
    return merged


def dictation_target(question) -> str:
    """What the learner hears in the clip: Part 2 audio is the question followed by the three responses."""
    if question.part == "Part 2":
        responses = " ".join(f"({key}) {text}" for key, text in (("A", question.choice_a), ("B", question.choice_b), ("C", question.choice_c)) if text)
        return f"{question.sentence} {responses}".strip()
    return question.sentence or ""


def detect_phonetic_cues(text: str) -> List[str]:
    cues = []
    lowered = text.lower()
    
    # Flap-T detection
    for word in _FLAP_T:
        if word in lowered:
            cues.append(f"Biến âm Flap-T trong '{word}': âm /t/ kẹp giữa 2 nguyên âm phát âm thành /d/ nhẹ trong giọng Mỹ.")
            break

    # Linking sounds (Consonant to Vowel)
    words = [w.strip() for w in text.split() if w.strip()]
    for i in range(len(words) - 1):
        w1, w2 = normalize_token(words[i]), normalize_token(words[i + 1])
        if w1 and w2 and w1[-1] not in "aeiou" and w2[0] in "aeiou" and len(w1) > 1:
            cues.append(f"Nối âm (Consonant-to-Vowel): '{words[i]} {words[i+1]}' nối phụ âm cuối sang nguyên âm đầu.")
            break

    # Elision (t/d drop)
    for phrase in _ELISION:
        if phrase in lowered:
            cues.append(f"Nuốt âm (Elision): Trong cụm '{phrase}', phụ âm cuối /t/ hoặc /d/ thường bị nuốt khi đứng trước phụ âm.")
            break

    if not cues:
        cues.append("Nhịp điệu trọng âm: chú ý nhấn mạnh vào danh từ, động từ chính và giảm nhẹ các trợ động từ/giới từ.")
    return cues


def diff_transcription(learner_text: str, target_transcript: str) -> dict:
    """Compare learner transcription against the reference target.

    Accuracy is an F1 score over words: missing words and extra words both cost points, so typing more than
    was said (or padding the answer) cannot reach 100%.
    """
    clean_target = target_transcript.strip()
    clean_learner = learner_text.strip()
    target = word_units(clean_target)
    learner = word_units(clean_learner)
    # ETS clips start with "Number seven." -- not part of the transcript, so it is not counted as extra.
    if len(learner) >= 2 and learner[0][1] == "number" and learner[1][1].isdigit() and (not target or target[0][1] != "number"):
        learner = learner[2:]

    matcher = difflib.SequenceMatcher(None, [u[1] for u in target], [u[1] for u in learner], autojunk=False)
    diff_tokens = []
    correct_count = 0
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for offset in range(i2 - i1):
                diff_tokens.append({"word": target[i1 + offset][0], "status": "correct", "learner_word": learner[j1 + offset][0]})
                correct_count += 1
        elif tag == "replace":
            for offset in range(i2 - i1):
                given = learner[j1 + offset][0] if j1 + offset < j2 else ""
                diff_tokens.append({"word": target[i1 + offset][0], "status": "misspelled" if given else "missing", "learner_word": given})
            for idx in range(j1 + (i2 - i1), j2):
                diff_tokens.append({"word": "", "status": "extra", "learner_word": learner[idx][0]})
        elif tag == "delete":
            for idx in range(i1, i2):
                diff_tokens.append({"word": target[idx][0], "status": "missing", "learner_word": ""})
        elif tag == "insert":
            for idx in range(j1, j2):
                diff_tokens.append({"word": "", "status": "extra", "learner_word": learner[idx][0]})

    denominator = len(target) + len(learner)
    accuracy = round(2 * correct_count / denominator * 100, 1) if denominator else 0.0
    return {
        "accuracy": accuracy,
        "is_perfect": accuracy >= 95.0,
        "correct_words": correct_count,
        "total_words": len(target),
        "tokens": diff_tokens,
        "target_transcript": clean_target,
        "learner_text": clean_learner,
        "phonetic_cues": detect_phonetic_cues(clean_target),
    }


def list_exercises(
    db: Session,
    part: Optional[str] = None,
    difficulty: Optional[str] = None,
    limit: int = 30,
) -> list:
    """Retrieve listening exercises from test questions and benchmark items."""
    query = db.query(TestQuestion)
    if part:
        query = query.filter(TestQuestion.part == part)
    else:
        query = query.filter(TestQuestion.part.in_(["Part 1", "Part 2", "Part 3", "Part 4"]))
        
    questions = query.order_by(TestQuestion.test_id.asc(), TestQuestion.question_no.asc()).limit(limit * 2).all()
    
    items = []
    for q in questions:
        diff = practice_service.classify_difficulty(q)
        if difficulty and diff != difficulty:
            continue
        
        # Audio accent distribution based on question index
        accents = ["US", "UK", "AU", "CA"]
        accent = accents[(q.question_no or 0) % 4]
        
        # Construct audio URL (using cached edge-tts synthesized with corresponding native accent voice)
        voice_map = {
            "US": "en-US-JennyNeural",
            "UK": "en-GB-RyanNeural",
            "AU": "en-AU-NatashaNeural",
            "CA": "en-CA-ClaraNeural",
        }
        voice = voice_map.get(accent, "en-US-JennyNeural")
        
        items.append({
            "id": q.id,
            "test_id": q.test_id,
            "part": q.part,
            "question_no": q.question_no,
            "sentence": q.sentence,
            "target_transcript": dictation_target(q),
            "explanation": q.explanation,
            "distractor_analysis": q.distractor_analysis,
            "paraphrase_pair": q.paraphrase_pair,
            "accent": accent,
            "voice": voice,
            "difficulty": diff,
            "phonetic_cues": detect_phonetic_cues(q.sentence),
            "choice_a": q.choice_a,
            "choice_b": q.choice_b,
            "choice_c": q.choice_c,
            "choice_d": q.choice_d,
            "correct_choice": q.correct_choice,
            "image_url": q.image_url,
            "audio_url": q.audio_url,
        })
        if len(items) >= limit:
            break
            
    return items


def track_listening_activity(db: Session, user_id: Optional[int], seconds: int) -> dict:
    """Record listening practice time and update activity minutes (guests: user_id None, nothing stored)."""
    safe_seconds = max(1, min(int(seconds), 7200))
    if user_id is None:
        return {"status": "ignored", "seconds": safe_seconds, "session_id": None}
    entry = activity.track(db, user_id, "listening", safe_seconds)
    db.commit()
    return {
        "status": "tracked",
        "seconds": safe_seconds,
        "session_id": entry.id if entry else None,
    }
