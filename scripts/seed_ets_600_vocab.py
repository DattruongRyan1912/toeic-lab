"""Seed the complete Authoritative ETS 600 Words Master Corpus into the database.
Sources:
- Barron's 600 Essential Words for the TOEIC (Dr. Lin Lougheed)
- Hacker TOEIC Vocabulary 30 Days (David Cho)
- ETS TOEIC Official Test Banks (2020-2024)
"""
import sys
from pathlib import Path
from collections import Counter
from sqlalchemy import func

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from server.database import SessionLocal, init_db
from server.models import Flashcard, User, UserCardSRS
from server.utils.timeutil import utcnow

from scripts.corpus.ets_vocab_pack1 import PACK_1
from scripts.corpus.ets_vocab_pack2 import PACK_2
from scripts.corpus.ets_vocab_pack3 import PACK_3
from scripts.corpus.ets_vocab_pack4 import PACK_4
from scripts.corpus.ets_vocab_pack5 import PACK_5
from scripts.corpus.ets_vocab_pack6 import PACK_6
from scripts.corpus.ets_vocab_pack7 import PACK_7
from scripts.corpus.ets_vocab_pack8 import PACK_8
from scripts.corpus.ets_vocab_pack9 import PACK_9
from scripts.corpus.ets_vocab_pack10 import PACK_10
from scripts.corpus.ets_vocab_pack11 import PACK_11
from scripts.corpus.ets_vocab_pack12 import PACK_12
from scripts.corpus.ets_vocab_pack13 import PACK_13
from scripts.corpus.ets_vocab_pack14 import PACK_14
from scripts.corpus.ets_vocab_pack15 import PACK_15
from scripts.corpus.ets_vocab_pack_it import PACK_IT
from scripts.corpus.barrons_50_lessons import BARRONS_CANON


def seed_corpus():
    init_db()
    db = SessionLocal()

    all_packs = [
        PACK_1, PACK_2, PACK_3, PACK_4, PACK_5, PACK_6, PACK_7, PACK_8,
        PACK_9, PACK_10, PACK_11, PACK_12, PACK_13, PACK_14, PACK_15,
        PACK_IT, BARRONS_CANON
    ]

    # Deduplicate within corpus entries
    corpus_dict = {}
    for pack in all_packs:
        for item in pack:
            lemma = item["word"].lower().strip()
            if lemma not in corpus_dict:
                corpus_dict[lemma] = item

    print(f"📦 Aggregated authoritative corpus: {len(corpus_dict)} distinct words.")

    user = db.query(User).filter_by(id=1).first()
    if not user:
        user = User(id=1, username="learner", target_score=850, daily_goal_minutes=60)
        db.add(user)
        db.commit()
        db.refresh(user)

    added_count = 0
    updated_count = 0
    category_counts = Counter()

    for lemma, data in corpus_dict.items():
        existing = db.query(Flashcard).filter(func.lower(Flashcard.word) == lemma).first()
        
        category = data.get("category", "General Business")
        word = data["word"].strip()
        ipa = data.get("ipa", "")
        word_type = data.get("word_type", "noun")
        meaning = data["meaning"].strip()
        collocations = data.get("collocations", "")
        paraphrase_pair = data.get("paraphrase_pair", "")
        example_sentence = data.get("example_sentence", "")
        audio_word = f"/api/tts?text={word}&voice=en-US-JennyNeural"
        audio_sentence = f"/api/tts?text={example_sentence}&voice=en-US-JennyNeural"

        if existing:
            # Enrich missing fields if any
            if not existing.collocations and collocations:
                existing.collocations = collocations
            if not existing.paraphrase_pair and paraphrase_pair:
                existing.paraphrase_pair = paraphrase_pair
            if not existing.ipa and ipa:
                existing.ipa = ipa
            updated_count += 1
            card_id = existing.id
            category_counts[existing.category] += 1
        else:
            new_card = Flashcard(
                category=category,
                word=word,
                ipa=ipa,
                word_type=word_type,
                meaning=meaning,
                collocations=collocations,
                paraphrase_pair=paraphrase_pair,
                example_sentence=example_sentence,
                audio_word_url=audio_word,
                audio_sentence_url=audio_sentence,
            )
            db.add(new_card)
            db.flush()
            card_id = new_card.id
            added_count += 1
            category_counts[category] += 1

        # Ensure UserCardSRS link
        srs = db.query(UserCardSRS).filter_by(user_id=user.id, card_id=card_id).first()
        if not srs:
            srs = UserCardSRS(
                user_id=user.id,
                card_id=card_id,
                state="new",
                interval_days=1,
                ease_factor=2.5,
                repetition_count=0,
                next_review_at=utcnow(),
            )
            db.add(srs)

    db.commit()

    total_cards = db.query(Flashcard).count()
    total_srs = db.query(UserCardSRS).filter_by(user_id=user.id).count()

    print("\n✅ Seed completed successfully!")
    print(f"  • Newly added cards: {added_count}")
    print(f"  • Enriched existing cards: {updated_count}")
    print(f"  • Total flashcards in database: {total_cards}")
    print(f"  • Total cards in user SRS queue: {total_srs}")
    print("\n📊 Breakdown by 14 ETS Business Domains:")
    for cat, cnt in sorted(category_counts.items(), key=lambda x: -x[1]):
        print(f"  - {cat}: {cnt} từ")

    db.close()


if __name__ == "__main__":
    seed_corpus()
