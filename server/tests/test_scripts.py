import csv

from server import models
from scripts import export_anki_csv, seed_database
from scripts.vocab_rows import BLANK, card_row


def test_seed_if_empty_detection(db):
    assert seed_database.database_is_empty() is True
    db.add(models.MockTest(test_id="T1", name="Test"))
    db.commit()
    assert seed_database.database_is_empty() is False


def test_anki_export_reads_the_learner_vocab(seeded, db, tmp_path):
    db.add(models.Flashcard(category="IT", word="deploy", meaning="triển khai", example_sentence="We deployed the <new> build."))
    db.commit()
    out = tmp_path / "deck.csv"
    assert export_anki_csv.main(["--out", str(out)]) == 0

    rows = list(csv.reader(out.open(encoding="utf-8")))
    assert rows[0] == export_anki_csv.HEADER and len(rows) == 1 + 6  # 5 seeded cards + the one added above
    deploy = next(row for row in rows if row[2] == "deploy")
    assert deploy[0] == f"We {BLANK} the &lt;new&gt; build."
    assert "<b style='color:#0284c7'>deployed</b>" in deploy[8]


def test_card_row_falls_back_when_word_is_absent():
    card = models.Flashcard(category="HR", word="eligible", meaning="đủ điều kiện", example_sentence="Staff qualify for bonuses.")
    assert card_row(card)[0] == f"Staff qualify for bonuses. ({BLANK})"
