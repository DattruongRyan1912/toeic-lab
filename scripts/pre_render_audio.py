#!/usr/bin/env python3
"""
Pre-render high quality Azure Neural MP3 audio files for TOEIC Flashcards dataset.
Generates:
1. docs/audio/words/{word}.mp3
2. docs/audio/sentences/{id}_{word}.mp3
"""

import asyncio
from pathlib import Path
import re
import edge_tts

FLASHCARDS = [
    {"id": 1, "word": "postpone", "sentence": "The board of directors decided to postpone the annual shareholder meeting until next Friday."},
    {"id": 2, "word": "conduct", "sentence": "The internal auditing committee will conduct a comprehensive inspection of financial records."},
    {"id": 3, "word": "comply", "sentence": "All manufacturing plants must strictly comply with environmental and workplace safety regulations."},
    {"id": 4, "word": "eligible", "sentence": "Full-time software engineers are eligible for tuition reimbursement after six months of service."},
    {"id": 5, "word": "reimburse", "sentence": "Please submit your travel receipts so that the finance department can reimburse your business expenses."},
    {"id": 6, "word": "unanimously", "sentence": "The shareholders unanimously approved the proposed merger with the technology firm."},
    {"id": 7, "word": "comprehensive", "sentence": "The warranty provided with this server rack provides comprehensive coverage for hardware defects."},
    {"id": 8, "word": "tentative", "sentence": "The project timeline shared yesterday is only tentative and subject to change based on client feedback."},
    {"id": 9, "word": "facilitate", "sentence": "The engineering department introduced a new ticketing system to facilitate cross-team collaboration."},
    {"id": 10, "word": "allocate", "sentence": "The management agreed to allocate additional budget funds to upgrade cloud infrastructure."},
    {"id": 11, "word": "expire", "sentence": "Your subscription to the enterprise cloud platform will expire at the end of this billing cycle."},
    {"id": 12, "word": "exceptional", "sentence": "The hiring manager noted that Mr. Tran is an exceptional candidate with strong distributed systems expertise."},
    {"id": 13, "word": "anticipate", "sentence": "The logistics provider does not anticipate any delivery delays despite the adverse weather conditions."},
    {"id": 14, "word": "implement", "sentence": "The security division will implement stricter authentication protocols across all production databases."},
    {"id": 15, "word": "itinerary", "sentence": "Please review the detailed flight itinerary sent by the travel agency before departing for Tokyo."},
    {"id": 16, "word": "mandatory", "sentence": "Attendance at tomorrow morning's orientation session is mandatory for all newly hired software engineers."},
    {"id": 17, "word": "prompt", "sentence": "Thank you for your prompt response to our customer inquiry regarding service availability."},
    {"id": 18, "word": "substantially", "sentence": "Quarterly net revenues increased substantially following the launch of the new subscription model."},
    {"id": 19, "word": "accommodate", "sentence": "The conference venue is fully equipped to accommodate up to 500 attendees with specialized accessibility needs."},
    {"id": 20, "word": "confidential", "sentence": "All employee compensation records and personnel files must remain strictly confidential."}
]

DEFAULT_VOICE = "en-US-JennyNeural"

BASE_DIR = Path(__file__).resolve().parent.parent
WORDS_DIR = BASE_DIR / "docs" / "audio" / "words"
SENTENCES_DIR = BASE_DIR / "docs" / "audio" / "sentences"

WORDS_DIR.mkdir(parents=True, exist_ok=True)
SENTENCES_DIR.mkdir(parents=True, exist_ok=True)

async def render_audio(text: str, output_path: Path, voice: str = DEFAULT_VOICE):
    clean = re.sub(r'<[^>]+>', '', text).strip()
    if output_path.exists() and output_path.stat().st_size > 0:
        print(f"  [SKIPPED] {output_path.name} already exists.")
        return
    print(f"  [RENDERING] {output_path.name} (voice: {voice})...")
    comm = edge_tts.Communicate(clean, voice)
    await comm.save(str(output_path))
    print(f"  ✓ Saved {output_path.name} ({output_path.stat().st_size // 1024} KB)")

async def main():
    print(f"=== Starting Studio Audio Pre-rendering (Voice: {DEFAULT_VOICE}) ===")
    
    # 1. Render all single words
    print("\n--- Phase 1: Rendering Word Audio ---")
    for item in FLASHCARDS:
        word = item["word"]
        target = WORDS_DIR / f"{word}.mp3"
        await render_audio(word, target)
        
    # 2. Render all full sentences
    print("\n--- Phase 2: Rendering Sentence Audio ---")
    for item in FLASHCARDS:
        card_id = item["id"]
        word = item["word"]
        sentence = item["sentence"]
        target = SENTENCES_DIR / f"{card_id}_{word}.mp3"
        await render_audio(sentence, target)
        
    print("\n=== Audio pre-rendering completed successfully! ===")
    print(f"Words: {len(list(WORDS_DIR.glob('*.mp3')))} files")
    print(f"Sentences: {len(list(SENTENCES_DIR.glob('*.mp3')))} files")

if __name__ == "__main__":
    asyncio.run(main())
