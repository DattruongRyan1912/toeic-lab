"""Single source of truth for TOEIC raw -> scaled conversion.

Used by the API (/api/tests/calculate-score, quiz submissions) and by the CLI
(scripts/score_calculator.py) so the same raw score always yields the same result.
The curve is an approximation of published ETS equating tables; real tests vary by form.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Optional

MAX_RAW = 100
MIN_SECTION = 5
MAX_SECTION = 495

LISTENING_PARTS = ("Part 1", "Part 2", "Part 3", "Part 4")
READING_PARTS = ("Part 5", "Part 6", "Part 7")

# (minimum total, code, label, description) — ETS TOEIC L&R to CEFR mapping.
CEFR_BANDS = (
    (945, "C1", "C1 - Advanced Professional", "Làm việc quốc tế thành thạo, gần tương đương người bản xứ."),
    (785, "B2", "B2 - Working Proficiency", "Đủ điều kiện làm việc trong tập đoàn đa quốc gia và môi trường kỹ thuật quốc tế."),
    (550, "B1", "B1 - Independent User", "Giao tiếp công việc căn bản, cần bổ sung từ vựng chuyên ngành."),
    (225, "A2", "A2 - Elementary", "Giao tiếp đơn giản, phản xạ nghe còn chậm."),
    (0, "A1", "A1 - Beginner", "Cần xây lại nền tảng ngữ pháp, phát âm và từ vựng cốt lõi."),
)


def _clamp_raw(raw: int) -> int:
    return max(0, min(MAX_RAW, int(raw)))


def _round5(value: float) -> int:
    return int(max(MIN_SECTION, min(MAX_SECTION, round(value / 5) * 5)))


def listening_scaled(raw: int) -> int:
    raw = _clamp_raw(raw)
    if raw <= 0:
        value = 5
    elif raw >= 96:
        value = 495
    elif raw >= 93:
        value = 490
    elif raw >= 90:
        value = 480
    elif raw >= 85:
        value = 450 + (raw - 85) * 6
    elif raw >= 75:
        value = 390 + (raw - 75) * 6
    elif raw >= 65:
        value = 330 + (raw - 65) * 6
    elif raw >= 50:
        value = 240 + (raw - 50) * 6
    elif raw >= 35:
        value = 150 + (raw - 35) * 6
    elif raw >= 20:
        value = 75 + (raw - 20) * 5
    else:
        value = max(5, raw * 4)
    return _round5(value)


def reading_scaled(raw: int) -> int:
    raw = _clamp_raw(raw)
    if raw <= 0:
        value = 5
    elif raw >= 97:
        value = 495
    elif raw >= 94:
        value = 485
    elif raw >= 90:
        value = 460
    elif raw >= 85:
        value = 425 + (raw - 85) * 7
    elif raw >= 75:
        value = 360 + (raw - 75) * 6.5
    elif raw >= 65:
        value = 295 + (raw - 65) * 6.5
    elif raw >= 50:
        value = 205 + (raw - 50) * 6
    elif raw >= 35:
        value = 125 + (raw - 35) * 5.3
    elif raw >= 20:
        value = 65 + (raw - 20) * 4
    else:
        value = max(5, raw * 3.25)
    return _round5(value)


def cefr_for(total: int) -> tuple:
    """Return (code, label, description) for a total scaled score."""
    for minimum, code, label, description in CEFR_BANDS:
        if total >= minimum:
            return code, label, description
    return CEFR_BANDS[-1][1:]


def section_for_part(part: Optional[str]) -> Optional[str]:
    if part in LISTENING_PARTS:
        return "listening"
    if part in READING_PARTS:
        return "reading"
    return None


MIN_SECTION_SAMPLE = 20  # fewer answers than this say too little about a 100-question section


def estimate_section_scaled(section: str, correct: int, total: int) -> Optional[int]:
    """Extrapolate a partial practice set (e.g. 30 Part 5 questions) to a 0-100 raw section score.

    None when the set is too small: 6/6 on Part 1 or 15/15 on a drill must not read as a 495.
    """
    if total < MIN_SECTION_SAMPLE:
        return None
    raw = round(correct / total * MAX_RAW)
    return listening_scaled(raw) if section == "listening" else reading_scaled(raw)


def plan_gain(l_raw: int, r_raw: int, target: int) -> tuple:
    """Fewest extra correct answers (listening, reading) needed to reach `target`."""
    l_raw, r_raw = _clamp_raw(l_raw), _clamp_raw(r_raw)
    add_l = add_r = 0
    while listening_scaled(l_raw + add_l) + reading_scaled(r_raw + add_r) < target:
        can_l, can_r = l_raw + add_l < MAX_RAW, r_raw + add_r < MAX_RAW
        if not (can_l or can_r):
            break
        gain_l = listening_scaled(l_raw + add_l + 1) - listening_scaled(l_raw + add_l) if can_l else -1
        gain_r = reading_scaled(r_raw + add_r + 1) - reading_scaled(r_raw + add_r) if can_r else -1
        if gain_l >= gain_r:  # ties favour Listening: the fastest section to lift for most learners
            add_l += 1
        else:
            add_r += 1
    return add_l, add_r


def recommendations(l_raw: int, r_raw: int) -> list:
    tips = []
    if l_raw < 70:
        tips.append("Listening: tập trung Part 1 & 2, luyện Dictation để bắt âm nối/nuốt âm.")
    elif l_raw < 85:
        tips.append("Listening: nâng Part 3 & 4 bằng kỹ thuật đọc trước 3 câu hỏi và Shadowing 1.0x.")
    else:
        tips.append("Listening: duy trì với audio tốc độ 1.15x, xử lý bẫy ngụ ý và giọng Anh/Úc.")
    if r_raw < 65:
        tips.append("Reading: củng cố 12 chuyên đề cú pháp Part 5, giữ Part 5 dưới 15 phút.")
    elif r_raw < 80:
        tips.append("Reading: tối ưu 3-Pass Scanning cho Part 7 đoạn đơn, Part 5 dưới 12 phút.")
    else:
        tips.append("Reading: luyện liên kết chéo Double/Triple Passages và Paraphrase Vault.")
    return tips


@dataclass
class ScoreBreakdown:
    raw_listening: int
    raw_reading: int
    scaled_listening: int
    scaled_reading: int
    total_score: int
    cefr_code: str
    cefr_level: str
    cefr_description: str
    target_score: int
    target_gap: int
    suggested_gain_listening: int
    suggested_gain_reading: int
    recommendations: list = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)


def convert(l_raw: int, r_raw: int, target: int = 800) -> ScoreBreakdown:
    l_raw, r_raw = _clamp_raw(l_raw), _clamp_raw(r_raw)
    scaled_l, scaled_r = listening_scaled(l_raw), reading_scaled(r_raw)
    total = scaled_l + scaled_r
    code, label, description = cefr_for(total)
    gain_l, gain_r = plan_gain(l_raw, r_raw, target)
    return ScoreBreakdown(
        raw_listening=l_raw,
        raw_reading=r_raw,
        scaled_listening=scaled_l,
        scaled_reading=scaled_r,
        total_score=total,
        cefr_code=code,
        cefr_level=label,
        cefr_description=description,
        target_score=target,
        target_gap=max(0, target - total),
        suggested_gain_listening=gain_l,
        suggested_gain_reading=gain_r,
        recommendations=recommendations(l_raw, r_raw),
    )
