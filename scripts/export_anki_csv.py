#!/usr/bin/env python3
"""
Export TOEIC Vocab data to standard CSV/TSV format.
Hỗ trợ import trực tiếp vào AnkiWeb, Quizlet, hoặc Google Sheets.
"""

import csv
import os
from generate_anki_deck import VOCAB_DATA

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_file = os.path.join(base_dir, "decks", "TOEIC_Sprint1_Core_Vocab.csv")
    with open(csv_file, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Front_Sentence", "Domain", "Word", "IPA", "WordType", "Meaning", "Collocations", "Paraphrase", "Full_Sentence"])
        for row in VOCAB_DATA:
            writer.writerow(list(row))
    print(f"🎉 Đã xuất thêm file CSV: {csv_file}")

if __name__ == "__main__":
    main()
