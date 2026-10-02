"""Listening service: Dictation diffing, connected speech detection, and exercise management."""

from __future__ import annotations

import difflib
import re
from typing import List, Optional
from sqlalchemy.orm import Session

from server.models import TestQuestion
from server.services import activity, practice_service

_CLEAN_RE = re.compile(r"[^\w\s']")
_CONTRACTIONS = {
    "can't": "cannot",
    "won't": "will not",
    "don't": "do not",
    "doesn't": "does not",
    "didn't": "did not",
    "it's": "it is",
    "that's": "that is",
    "there's": "there is",
    "i'm": "i am",
    "you're": "you are",
    "they're": "they are",
    "we're": "we are",
    "i've": "i have",
    "you've": "you have",
    "we've": "we have",
    "they've": "they have",
}

# Key phonetics keywords for TOEIC connected speech
_FLAP_T = {"water", "meeting", "better", "waiting", "city", "computer", "shuttle", "quarter", "party", "hospital"}
_ELISION = {"last night", "next day", "most common", "first time", "hold on", "left turn", "stand by"}


def normalize_token(token: str) -> str:
    cleaned = _CLEAN_RE.sub("", token.lower()).strip()
    return _CONTRACTIONS.get(cleaned, cleaned)


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
    
    Returns token-by-token diff with accuracy score and phonetic analysis.
    """
    clean_target = target_transcript.strip()
    clean_learner = learner_text.strip()
    
    target_tokens = [w for w in clean_target.split() if w]
    learner_tokens = [w for w in clean_learner.split() if w]
    
    norm_target = [normalize_token(w) for w in target_tokens]
    norm_learner = [normalize_token(w) for w in learner_tokens]
    
    matcher = difflib.SequenceMatcher(None, norm_target, norm_learner)
    diff_tokens = []
    correct_count = 0
    
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for idx in range(i1, i2):
                diff_tokens.append({
                    "word": target_tokens[idx],
                    "status": "correct",
                    "learner_word": learner_tokens[j1 + (idx - i1)],
                })
                correct_count += 1
        elif tag == "replace":
            for idx in range(i1, i2):
                corr = target_tokens[idx]
                given = learner_tokens[j1 + (idx - i1)] if (j1 + (idx - i1)) < j2 else ""
                diff_tokens.append({
                    "word": corr,
                    "status": "misspelled" if given else "missing",
                    "learner_word": given,
                })
            # Any remaining learner tokens in replacement
            if (j2 - j1) > (i2 - i1):
                for l_idx in range(j1 + (i2 - i1), j2):
                    diff_tokens.append({
                        "word": "",
                        "status": "extra",
                        "learner_word": learner_tokens[l_idx],
                    })
        elif tag == "delete":
            for idx in range(i1, i2):
                diff_tokens.append({
                    "word": target_tokens[idx],
                    "status": "missing",
                    "learner_word": "",
                })
        elif tag == "insert":
            for idx in range(j1, j2):
                diff_tokens.append({
                    "word": "",
                    "status": "extra",
                    "learner_word": learner_tokens[idx],
                })
                
    total_target = len(target_tokens)
    accuracy = round((correct_count / max(1, total_target)) * 100, 1)
    
    return {
        "accuracy": accuracy,
        "is_perfect": accuracy >= 95.0,
        "correct_words": correct_count,
        "total_words": total_target,
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
            "target_transcript": q.sentence,
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
        })
        if len(items) >= limit:
            break
            
    return items


def track_listening_activity(db: Session, user_id: int, seconds: int) -> dict:
    """Record listening practice time and update activity minutes."""
    safe_seconds = max(1, min(int(seconds), 7200))
    entry = activity.track(db, user_id, "listening", safe_seconds)
    return {
        "status": "tracked",
        "seconds": safe_seconds,
        "session_id": entry.id if entry else None,
    }
