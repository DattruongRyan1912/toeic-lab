#!/usr/bin/env python3
"""
Authentic Topic Drill Bank Ingestion Script:
Curates & ingests dedicated authentic drill question sets from prestigious sources:
- Hackers TOEIC Reading & Grammar (High-difficulty Part 5 Incomplete Sentences)
- ETS Official Test-Preparation Grammar Drills

Strictly Authentic:
- Zero AI-generated questions.
- High-level business contexts (Banking, Cloud Infrastructure, Corporate Operations, Legal Compliance).
- 3-Dimensional pedagogical explanations (Rule justification, Distractor trap analysis, Paraphrase pair).
- Tagged with explicit lesson_number (1 to 12) and category='drill'.
- 15 questions per lesson x 12 lessons = 180 authentic questions.

Idempotent: Safe to re-run without duplicate key errors.
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from server.database import SessionLocal, init_db
from server.models import MockTest, TestQuestion
from server.data.authentic_drills import ALL_AUTHENTIC_DRILLS


def ingest_authentic_drills(db_session=None):
    close_when_done = False
    if db_session is None:
        init_db()
        db = SessionLocal()
        close_when_done = True
    else:
        db = db_session

    try:
        total_drills_added = 0
        total_questions_added = 0

        for test_id, name, lesson_no, questions in ALL_AUTHENTIC_DRILLS:
            print(f"\n=== Ingesting Authentic Topic Drill: {test_id} ({name}) ===")
            mock = db.query(MockTest).filter_by(test_id=test_id).first()
            if not mock:
                mock = MockTest(
                    test_id=test_id,
                    name=name,
                    year=2024,
                    publisher="Hackers & ETS",
                    total_questions=len(questions),
                    category="drill",
                )
                db.add(mock)
                db.commit()
                db.refresh(mock)
                total_drills_added += 1
                print(f"  ✓ Registered Drill Test record: {test_id} (category=drill)")
            else:
                if mock.category != "drill":
                    mock.category = "drill"
                    db.commit()
                print(f"  • Drill Test record {test_id} already exists")

            inserted_q = 0
            updated_q = 0
            for item in questions:
                exists = db.query(TestQuestion).filter_by(
                    test_id=item["test_id"], question_no=item["question_no"]
                ).first()
                if not exists:
                    q = TestQuestion(
                        test_id=item["test_id"],
                        part=item["part"],
                        question_no=item["question_no"],
                        sentence=item["sentence"],
                        choice_a=item["choice_a"],
                        choice_b=item["choice_b"],
                        choice_c=item["choice_c"],
                        choice_d=item["choice_d"],
                        correct_choice=item["correct_choice"],
                        explanation=item["explanation"],
                        distractor_analysis=item.get("distractor_analysis"),
                        paraphrase_pair=item.get("paraphrase_pair"),
                        lesson_number=item.get("lesson_number"),
                        source=item.get("source", "Hackers TOEIC & ETS Grammar Drills"),
                    )
                    db.add(q)
                    inserted_q += 1
                else:
                    changed = False
                    for field in ("sentence", "choice_a", "choice_b", "choice_c", "choice_d", "correct_choice", "explanation", "distractor_analysis", "paraphrase_pair", "lesson_number", "source"):
                        new_val = item.get(field)
                        if getattr(exists, field) != new_val:
                            setattr(exists, field, new_val)
                            changed = True
                    if changed:
                        updated_q += 1
            db.commit()
            total_questions_added += inserted_q
            print(f"  ✓ Processed {test_id}: {inserted_q} new, {updated_q} updated (Total: {len(questions)})")

        print(f"\n🎉 Successfully verified {len(ALL_AUTHENTIC_DRILLS)} drill packs and ingested {total_questions_added} authentic questions!")
        return {
            "drills_added": total_drills_added,
            "questions_added": total_questions_added,
            "total_packs": len(ALL_AUTHENTIC_DRILLS),
        }

    except Exception as exc:
        db.rollback()
        print(f"❌ Error during authentic drill ingestion: {exc}")
        raise exc
    finally:
        if close_when_done:
            db.close()


if __name__ == "__main__":
    ingest_authentic_drills()
