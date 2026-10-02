"""Batch translate example sentences for all flashcards in the database using AI.
Saves results directly into flashcards.example_translation.
Safe, idempotent, incremental (only processes cards where example_translation is empty).
"""
import asyncio
import json
import re
import sys
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
load_dotenv(ROOT_DIR / ".env")

from server.database import SessionLocal, init_db
from server.models import Flashcard
from server.services import ai_agent_service

BATCH_SIZE = 25


def extract_json_array(text: str) -> list:
    """Robustly extract a JSON array from raw model text."""
    text = text.strip()
    match = re.search(r"\[\s*\{.*\}\s*\]", text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            if isinstance(data, list):
                return data
        except Exception:
            pass
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []


async def translate_batch(batch_items: list[dict]) -> dict[int, str]:
    """Sends a batch of items to AI and returns {card_id: translation}."""
    prompt = f"""Bạn là chuyên gia biên dịch tài liệu luyện thi TOEIC 800-900+. 
Dịch các câu ví dụ tiếng Anh thương mại sau sang tiếng Việt chuẩn xác, tự nhiên, sát ngữ cảnh công sở, làm nổi bật nghĩa của từ vựng TOEIC.

Danh sách câu:
{json.dumps(batch_items, ensure_ascii=False, indent=2)}

Trả về DUY NHẤT một mảng JSON các object theo đúng định dạng:
[
  {{"id": 123, "translation": "câu dịch tiếng Việt hoàn chỉnh"}},
  ...
]
Không viết giải thích, không markdown bên ngoài mảng JSON."""

    try:
        raw = await ai_agent_service.complete_text(prompt)
        items = extract_json_array(raw)
        result = {}
        for it in items:
            cid = it.get("id")
            trans = it.get("translation")
            if cid is not None and trans:
                result[int(cid)] = str(trans).strip()
        return result
    except Exception as exc:
        print(f"    ⚠️ Lỗi khi gọi AI cho batch: {exc}")
        return {}


async def main():
    init_db()
    db = SessionLocal()

    untranslated = (
        db.query(Flashcard)
        .filter(
            (Flashcard.example_translation == None) | (Flashcard.example_translation == "")  # noqa: E711
        )
        .order_by(Flashcard.id)
        .all()
    )

    total_untranslated = len(untranslated)
    print(f"🔍 Tìm thấy {total_untranslated} từ vựng chưa có bản dịch câu ví dụ.")
    if total_untranslated == 0:
        print("✅ Tất cả câu ví dụ đã được dịch đầy đủ!")
        return

    provider = ai_agent_service.resolve_provider()
    print(f"🤖 Đang sử dụng AI Provider: {provider}")

    success_count = 0
    for i in range(0, total_untranslated, BATCH_SIZE):
        chunk = untranslated[i : i + BATCH_SIZE]
        batch_items = [
            {"id": card.id, "word": card.word, "sentence": card.example_sentence}
            for card in chunk
            if card.example_sentence and card.example_sentence != "Example sentence pending."
        ]

        if not batch_items:
            continue

        print(f"  → Đang dịch batch {i // BATCH_SIZE + 1}/{(total_untranslated + BATCH_SIZE - 1) // BATCH_SIZE} ({len(batch_items)} câu)...", end="", flush=True)
        translations = await translate_batch(batch_items)

        batch_saved = 0
        for card in chunk:
            if card.id in translations:
                card.example_translation = translations[card.id]
                batch_saved += 1
                success_count += 1

        db.commit()
        print(f" ✓ Đã lưu {batch_saved}/{len(batch_items)} câu dịch.")
        await asyncio.sleep(0.5)

    print(f"\n🎉 Hoàn thành! Đã cập nhật thành công {success_count}/{total_untranslated} bản dịch câu ví dụ.")


if __name__ == "__main__":
    asyncio.run(main())
