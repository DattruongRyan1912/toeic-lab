#!/usr/bin/env python3
"""
Export the vocab notebook (app database, including words added in the web app or by the AI mentor)
to CSV for AnkiWeb / Quizlet / Google Sheets. Use --static for the curated 20-word list.
"""

import argparse
import csv
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from scripts.vocab_rows import rows_from_db  # noqa: E402

HEADER = ["Front_Sentence", "Domain", "Word", "IPA", "WordType", "Meaning", "Collocations", "Paraphrase", "Full_Sentence"]
DEFAULT_OUT = ROOT_DIR / "decks" / "TOEIC_Sprint1_Core_Vocab.csv"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Xuất Sổ tay từ vựng ra CSV (Anki / Quizlet)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Đường dẫn file CSV")
    parser.add_argument("--static", action="store_true", help="Dùng 20 từ mẫu trong generate_anki_deck.py thay vì database")
    args = parser.parse_args(argv)

    if args.static:
        from scripts.generate_anki_deck import VOCAB_DATA

        rows = [tuple(row) for row in VOCAB_DATA]
    else:
        rows = rows_from_db()
    if not rows:
        print("❌ Database chưa có flashcard nào — chạy `make seed` trước.")
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(HEADER)
        writer.writerows(rows)
    print(f"🎉 Đã xuất {len(rows)} thẻ ra {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
