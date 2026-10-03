#!/usr/bin/env python3
"""Migrate existing learner data from default user 1 to a new authenticated account."""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from sqlalchemy import text
from server.database import SessionLocal
from server.models import Flashcard, Roadmap, SprintTask, User, UserCardSRS
from server.services import insights, planner
from server.utils.security import hash_password


def migrate_to_personal_account(
    target_username: str = "ryantruong",
    target_email: str = "dattruong19122003@gmail.com",
    raw_password: str = "Ryan@2026",
    display_name: str = "Ryan Truong",
):
    db = SessionLocal()
    try:
        # 1. Check if user 1 exists
        user1 = db.query(User).filter_by(id=1).first()
        if not user1:
            print("User 1 does not exist, nothing to migrate.")
            return

        # 2. Check if target user already exists
        target_user = (
            db.query(User)
            .filter((User.username == target_username) | (User.email == target_email))
            .first()
        )

        if not target_user:
            print(f"Creating new user: {target_username} ({target_email})...")
            target_user = User(
                username=target_username,
                email=target_email,
                hashed_password=hash_password(raw_password),
                display_name=display_name or user1.display_name or "Ryan Truong",
                headline=user1.headline or "Backend Engineer",
                target_score=user1.target_score or 800,
                daily_goal_minutes=user1.daily_goal_minutes or 60,
                created_at=user1.created_at,
                exam_date=user1.exam_date,
                baseline_listening=user1.baseline_listening,
                baseline_reading=user1.baseline_reading,
                study_days=user1.study_days,
                new_cards_per_day=user1.new_cards_per_day,
                explanation_style=user1.explanation_style or "detailed",
                focus_parts=user1.focus_parts,
                learning_goal_note=user1.learning_goal_note,
                auto_adjust=user1.auto_adjust,
                onboarded_at=user1.onboarded_at,
                plan_generated_on=user1.plan_generated_on,
                is_active=True,
                role="admin",
            )
            db.add(target_user)
            db.commit()
            db.refresh(target_user)
            print(f"  ✓ Created target user with ID = {target_user.id}")
        else:
            print(f"  ✓ Target user already exists with ID = {target_user.id}")
            target_user.hashed_password = hash_password(raw_password)
            db.commit()

        new_user_id = target_user.id

        # 3. Move all data from user_id = 1 to target_user.id
        tables = [
            "roadmaps",
            "user_flashcard_srs",
            "srs_review_logs",
            "error_logs",
            "ai_learning_gaps",
            "question_attempts",
            "user_test_submissions",
            "study_sessions",
            "study_reminders",
            "lesson_progress",
            "lesson_notes",
            "learner_memories",
            "study_plan_items",
            "ai_messages",
            "ai_action_logs",
        ]

        for t in tables:
            res = db.execute(
                text(f"UPDATE {t} SET user_id = :new_id WHERE user_id = 1"),
                {"new_id": new_user_id},
            )
            if res.rowcount > 0:
                print(f"  ✓ Moved {res.rowcount} rows in '{t}' -> user {new_user_id}")

        # 4. Reset User 1 to clean demo/guest account
        user1.username = "guest"
        user1.email = "guest@toeiclab.dev"
        user1.display_name = "Khách trải nghiệm"
        user1.headline = "Guest Learner"
        user1.hashed_password = hash_password("Guest@2026")
        user1.role = "guest"
        db.commit()

        # Provision fresh default data for user 1 (guest) so guest mode continues to work smoothly
        insights.ensure_srs_records(db, 1)
        r = db.query(Roadmap).filter_by(user_id=1).first()
        if not r:
            r = Roadmap(
                user_id=1,
                title="Lộ trình mẫu TOEIC 800+ (Khách)",
                total_weeks=24,
                current_week=1,
            )
            db.add(r)
            db.commit()
            db.refresh(r)
            from server.routers.auth_router import DEFAULT_SPRINT_TASKS

            for phase, week, cat, title, done in DEFAULT_SPRINT_TASKS:
                db.add(
                    SprintTask(
                        roadmap_id=r.id,
                        phase=phase,
                        week_number=week,
                        category=cat,
                        title=title,
                        is_completed=done,
                    )
                )
            db.commit()

        print("\n=== MIGRATION COMPLETED SUCCESSFULLY ===")
        print(f"Personal Account: {target_username}")
        print(f"Email: {target_email}")
        print(f"Password: {raw_password}")
        print(f"User ID: {new_user_id}")
    finally:
        db.close()


if __name__ == "__main__":
    migrate_to_personal_account()
