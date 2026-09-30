from datetime import datetime, timedelta, timezone

def calculate_sm2_review(
    current_repetition: int,
    current_ease: float,
    current_interval: int,
    rating: int  # 1: Again, 2: Hard, 3: Good, 4: Easy
):
    """
    SuperMemo-2 (SM-2) Spaced Repetition Algorithm.
    Returns: (new_repetition, new_ease, new_interval, new_state, next_review_at)
    """
    now = datetime.now(timezone.utc)

    # 1. Rating = 1: Again (Forgot)
    if rating == 1:
        new_repetition = 0
        new_interval = 1
        new_ease = max(1.3, current_ease - 0.2)
        new_state = "learning"
        next_review_at = now + timedelta(days=1)
        return new_repetition, round(new_ease, 2), new_interval, new_state, next_review_at

    # 2. Rating >= 2 (Remembered)
    if current_repetition == 0:
        new_interval = 1 if rating <= 2 else 2
    elif current_repetition == 1:
        new_interval = 3 if rating <= 2 else 6
    else:
        # Scale interval with ease factor
        bonus = 1.3 if rating == 4 else 1.0
        new_interval = max(current_interval + 1, round(current_interval * current_ease * bonus))

    new_repetition = current_repetition + 1

    # Update ease factor based on performance
    # Formula: EF' = EF + (0.1 - (4 - rating) * (0.08 + (4 - rating) * 0.02))
    ease_delta = 0.1 - (4 - rating) * (0.08 + (4 - rating) * 0.02)
    new_ease = max(1.3, min(3.0, current_ease + ease_delta))

    # Determine state
    if new_repetition >= 4 or new_interval >= 21:
        new_state = "mastered"
    else:
        new_state = "review"

    next_review_at = now + timedelta(days=new_interval)
    return new_repetition, round(new_ease, 2), new_interval, new_state, next_review_at
