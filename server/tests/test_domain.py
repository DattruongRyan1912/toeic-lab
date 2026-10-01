import pytest

from server.services import curriculum, scoring
from server.services.srs_service import calculate_sm2_review


# --------------------------------------------------------------------------- scoring
@pytest.mark.parametrize(
    "raw, listening, reading",
    [(0, 5, 5), (50, 240, 205), (75, 390, 360), (85, 450, 425), (90, 480, 460), (97, 495, 495), (100, 495, 495)],
)
def test_curve_reference_points(raw, listening, reading):
    assert scoring.listening_scaled(raw) == listening
    assert scoring.reading_scaled(raw) == reading


def test_curve_is_monotonic_and_multiple_of_five():
    for fn in (scoring.listening_scaled, scoring.reading_scaled):
        values = [fn(raw) for raw in range(0, 101)]
        assert all(value % 5 == 0 and 5 <= value <= 495 for value in values)
        assert values == sorted(values)


@pytest.mark.parametrize("total, code", [(990, "C1"), (945, "C1"), (944, "B2"), (785, "B2"), (784, "B1"), (550, "B1"), (225, "A2"), (224, "A1")])
def test_cefr_bands(total, code):
    assert scoring.cefr_for(total)[0] == code


def test_suggested_gain_reaches_target():
    result = scoring.convert(70, 70, 800)
    assert result.target_gap > 0
    reached = scoring.listening_scaled(70 + result.suggested_gain_listening) + scoring.reading_scaled(70 + result.suggested_gain_reading)
    assert reached >= 800
    assert scoring.convert(99, 99, 800).suggested_gain_listening == 0


def test_cli_and_api_share_the_same_curve(capsys):
    from scripts import score_calculator

    result = score_calculator.diagnose_performance(78, 72, 800)
    assert result.as_dict() == scoring.convert(78, 72, 800).as_dict()
    assert "410/495" in capsys.readouterr().out


# --------------------------------------------------------------------------- curriculum
@pytest.mark.parametrize(
    "tag, error_type, lesson",
    [
        ("Bẫy Từ Loại", "GRAMMAR", 1),
        ("Bẫy Vị Trí Trạng Từ", "GRAMMAR", 1),
        ("Bẫy Tính Từ Sau Linking Verb", "GRAMMAR", 1),
        ("Bẫy Liên Từ vs Giới Từ", "GRAMMAR", 2),
        ("Bẫy Dạng Động Từ Sau Giới Từ", "GRAMMAR", 3),
        ("Bẫy Thể Bị Động", "GRAMMAR", 4),
        ("Bẫy Hòa Hợp Chủ-Vị", "GRAMMAR", 5),
        ("Bẫy Thì Tương Lai", "GRAMMAR", 6),
        ("Bẫy Đại Từ Phản Thân", "GRAMMAR", 7),
        ("Bẫy Đại Từ Quan Hệ Số Ít vs Số Nhiều", "GRAMMAR", 8),
        ("Bẫy Thể Giả Định", "GRAMMAR", 9),
        ("Bẫy Đảo Ngữ Câu Điều Kiện", "GRAMMAR", 10),
        ("Bẫy Từ Loại Trong So Sánh", "GRAMMAR", 11),
        ("Bẫy Tính Từ Đi Với Giới Từ", "VOCAB", 12),
        ("Bẫy Collocation", "VOCAB", 12),
        ("Bẫy Similar Sound", "TRAP", None),
        ("Bẫy Thông Tin Lệch", "TRAP", None),
    ],
)
def test_trap_tags_map_to_rca_and_lesson(tag, error_type, lesson):
    assert curriculum.classify_trap(tag, "Part 5") == curriculum.TrapClass(error_type, lesson)


def test_tag_extraction_and_part_normalization():
    assert curriculum.extract_trap_tag("[Bẫy Từ Loại] A là tính từ") == "Bẫy Từ Loại"
    assert curriculum.extract_trap_tag("không có tag") is None
    assert curriculum.normalize_part("part5") == "Part 5"
    assert curriculum.normalize_part("9") is None
    assert curriculum.lesson_numbers_in("Bài 02 (Liên từ) & Bài 03 (To-V)") == [2, 3]


# --------------------------------------------------------------------------- SM-2
def test_sm2_progression_and_reset():
    rep, ease, interval, state, _ = calculate_sm2_review(0, 2.5, 1, 3)
    assert (rep, interval, state) == (1, 2, "review")
    rep, ease, interval, state, _ = calculate_sm2_review(rep, ease, interval, 3)
    assert (rep, interval) == (2, 6)
    rep, ease, interval, state, next_review = calculate_sm2_review(rep, ease, interval, 1)
    assert (rep, interval, state) == (0, 1, "learning")
    assert next_review.tzinfo is None  # naive UTC, same convention as the DB
