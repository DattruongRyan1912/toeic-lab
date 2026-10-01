from datetime import timedelta

from server.utils.timeutil import utcnow


def calculate_sm2_review(
    current_repetition: int,
    current_ease: float,
    current_interval: int,
    rating: int,  # 1: Again, 2: Hard, 3: Good, 4: Easy
):
    """SuperMemo-2 (SM-2) spaced repetition.

    Returns (new_repetition, new_ease, new_interval, new_state, next_review_at) where
    next_review_at is naive UTC like every stored timestamp.
    """
    now = utcnow()
    current_repetition = current_repetition or 0
    current_ease = current_ease or 2.5
    current_interval = current_interval or 1

    # 1. Rating = 1: Again (forgot)
    if rating == 1:
        new_ease = max(1.3, current_ease - 0.2)
        return 0, round(new_ease, 2), 1, "learning", now + timedelta(days=1)

    # 2. Rating >= 2 (remembered)
    if current_repetition == 0:
        new_interval = 1 if rating <= 2 else 2
    elif current_repetition == 1:
        new_interval = 3 if rating <= 2 else 6
    else:
        bonus = 1.3 if rating == 4 else 1.0
        new_interval = max(current_interval + 1, round(current_interval * current_ease * bonus))

    new_repetition = current_repetition + 1

    # EF' = EF + (0.1 - (4 - rating) * (0.08 + (4 - rating) * 0.02))
    ease_delta = 0.1 - (4 - rating) * (0.08 + (4 - rating) * 0.02)
    new_ease = max(1.3, min(3.0, current_ease + ease_delta))

    new_state = "mastered" if new_repetition >= 4 or new_interval >= 21 else "review"
    return new_repetition, round(new_ease, 2), new_interval, new_state, now + timedelta(days=new_interval)
