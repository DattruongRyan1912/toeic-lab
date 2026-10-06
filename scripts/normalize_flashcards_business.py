#!/usr/bin/env python3
"""
Normalize flashcard example sentences from IT-tailored back to standard TOEIC business English.
Ensures 100% authentic business scenarios (office management, client meetings, facility operations).
"""
import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from server.database import SessionLocal, init_db
from server.models import Flashcard

IT_REPLACEMENTS = [
    ('server rack maintenance fees', 'office equipment maintenance fees'),
    ('server rack', 'office copier'),
    ('server racks', 'office copiers'),
    ('production databases', 'corporate records'),
    ('production database', 'corporate database'),
    ('production servers', 'headquarters facilities'),
    ('production server', 'company network'),
    ('cloud servers', 'digital archives'),
    ('cloud server', 'digital archive'),
    ('young software developers and tech startups', 'young entrepreneurs and retail clients'),
    ('software developers', 'marketing executives'),
    ('software developer', 'corporate employee'),
    ('developer turnover', 'employee turnover'),
    ('developers with', 'staff members with'),
    ('developers', 'specialists'),
    ('backend engineers', 'technical specialists'),
    ('backend engineer', 'operations manager'),
    ('software engineers', 'department specialists'),
    ('software engineer', 'project specialist'),
    ('software architecture review', 'quarterly operations review'),
    ('API documentation', 'product documentation'),
    ('database replication', 'inventory synchronization'),
    ('database migration', 'facility relocation'),
]

POLISH_MAP = [
    ('project specialisting', 'business operations'),
    ('operations managering', 'operations management'),
    ('marketing executives association', 'retail merchants association'),
    ('specialists must use secure SSH keys to access staging server instances', 'employees must use security badges to access restricted facility areas'),
    ('Climate-controlled office copiers', 'Climate-controlled warehouse facilities'),
    ('corporate database access requires two-factor hardware authentication', 'corporate financial records require authorized supervisor approval'),
    ('leaving default credentials unchanged exposes corporate records to automated intrusion', 'leaving file cabinets unlocked violates company data privacy protocols'),
    ('developers were advised that version two of the API will be deprecated', 'franchise owners were advised that legacy catalog prices will expire'),
    ('accessing the corporate database requires multi-factor authorization', 'accessing confidential client records requires official authorization'),
]


def normalize():
    init_db()
    db = SessionLocal()
    try:
        cards = db.query(Flashcard).all()
        updated_count = 0
        for card in cards:
            if not card.example_sentence:
                continue
            original = card.example_sentence
            sent = original
            # 1. Clean HTML blank spans and replace with the target word
            if "<span" in sent or "blank" in sent:
                sent = re.sub(r"<span class=['\"]blank['\"]>______\s*</span>", card.word, sent, flags=re.IGNORECASE)
                sent = re.sub(r"<span[^>]*>.*?</span>", card.word, sent, flags=re.IGNORECASE)
                sent = re.sub(r"<[^>]+>", "", sent)

            for old_term, new_term in IT_REPLACEMENTS:
                if old_term in sent.lower():
                    pattern = re.compile(re.escape(old_term), re.IGNORECASE)
                    sent = pattern.sub(new_term, sent)

            for old_phrase, new_phrase in POLISH_MAP:
                if old_phrase.lower() in sent.lower():
                    pattern = re.compile(re.escape(old_phrase), re.IGNORECASE)
                    sent = pattern.sub(new_phrase, sent)

            if sent != original:
                card.example_sentence = sent
                updated_count += 1

        db.commit()
        print(f"✓ Successfully normalized {updated_count} flashcards to standard business English.")
    except Exception as e:
        db.rollback()
        print(f"Error during flashcard normalization: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    normalize()
