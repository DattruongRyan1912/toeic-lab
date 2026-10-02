#!/usr/bin/env python3
"""Seed authentic Listening Benchmark Questions (Part 1, Part 2, Part 3) for TOEIC Lab."""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from server.database import SessionLocal, init_db
from server.models import TestQuestion, MockTest
from server.utils.timeutil import utcnow

LISTENING_QUESTIONS = [
    # --- Part 1: Photographs ---
    {
        "test_id": "ETS2024_01",
        "part": "Part 1",
        "question_no": 1,
        "sentence": "A woman is typing on a laptop computer at an office workstation.",
        "choice_a": "She is closing her notebook.",
        "choice_b": "A woman is typing on a laptop computer.",
        "choice_c": "She is rearranging files on a shelf.",
        "choice_d": "A woman is handing a document to a colleague.",
        "correct_choice": "B",
        "explanation": "Người phụ nữ đang thao tác gõ bàn phím trên máy tính xách tay tại bàn làm việc.",
        "distractor_analysis": "[Bẫy Hành Động Sai] A (closing notebook), C (rearranging files), D (handing document) là các hành động không xuất hiện trong hình ảnh.",
        "paraphrase_pair": "typing on a laptop = inputting data into a computer",
        "image_url": "/part1/ets2024_01_q1.jpg",
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 1",
        "question_no": 2,
        "sentence": "Several workers are wearing hard hats at an active construction site.",
        "choice_a": "Some workers are wearing hard hats.",
        "choice_b": "They are painting a brick wall.",
        "choice_c": "Workers are packing tools into boxes.",
        "choice_d": "They are boarding a commuter bus.",
        "correct_choice": "A",
        "explanation": "Các công nhân đang đội mũ bảo hộ lao động tại công trường.",
        "distractor_analysis": "[Bẫy Động Từ & Địa Điểm] Bẫy hành động (painting, packing, boarding) không khớp với bối cảnh bức ảnh.",
        "paraphrase_pair": "wearing hard hats = putting on safety protective headgear",
        "image_url": "/part1/ets2024_01_q2.jpg",
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 1",
        "question_no": 3,
        "sentence": "Merchandise has been neatly displayed on wooden shelves in a boutique.",
        "choice_a": "A customer is paying at the cash register.",
        "choice_b": "Merchandise has been displayed on shelves.",
        "choice_c": "Boxes are being loaded into a truck.",
        "choice_d": "A shop assistant is cleaning the storefront window.",
        "correct_choice": "B",
        "explanation": "Hàng hóa được trưng bày gọn gàng trên các kệ gỗ trong cửa hàng.",
        "distractor_analysis": "[Bẫy Trạng Thái Bị Động 'being'] C (are being loaded) sai vì không có người đang bốc xếp hàng.",
        "paraphrase_pair": "displayed on shelves = arranged on store racks",
        "image_url": "/part1/ets2024_01_q3.jpg",
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 1",
        "question_no": 4,
        "sentence": "A presenter is gesturing toward a projected slide during a meeting.",
        "choice_a": "Audience members are exiting the conference room.",
        "choice_b": "A presenter is gesturing toward a projected screen.",
        "choice_c": "The speaker is unplugging a microphone.",
        "choice_d": "People are signing registration contracts.",
        "correct_choice": "B",
        "explanation": "Diễn giả đang chỉ tay về phía màn hình chiếu trong cuộc họp.",
        "distractor_analysis": "[Bẫy Chi Tiết Giả] A, C, D mô tả hành động rời phòng, rút mic và ký tên không có thật.",
        "paraphrase_pair": "gesturing toward a screen = pointing at a display presentation",
        "image_url": "/part1/ets2024_01_q4.jpg",
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 1",
        "question_no": 5,
        "sentence": "Bicycles are parked in an outdoor rack beside an office building.",
        "choice_a": "People are riding bicycles along a path.",
        "choice_b": "Bicycles are parked in an outdoor rack.",
        "choice_c": "A mechanic is repairing a bicycle wheel.",
        "choice_d": "Vehicles are queued at a toll booth.",
        "correct_choice": "B",
        "explanation": "Xe đạp được dựng trong giá đỗ ngoài trời cạnh tòa nhà văn phòng.",
        "distractor_analysis": "[Bẫy Từ Đồng Âm/Liên Tưởng] A (riding bicycles) và C (repairing) dùng từ 'bicycle' nhưng sai hoàn toàn về hành động trong tranh tĩnh.",
        "paraphrase_pair": "parked in a rack = stationed in a designated bike stand",
        "image_url": "/part1/ets2024_01_q5.jpg",
    },

    # --- Part 2: Question - Response ---
    {
        "test_id": "ETS2024_01",
        "part": "Part 2",
        "question_no": 7,
        "sentence": "When will the quarterly financial report be ready?",
        "choice_a": "By Friday afternoon at the latest.",
        "choice_b": "Yes, I reported it yesterday.",
        "choice_c": "In the central conference hall.",
        "choice_d": None,
        "correct_choice": "A",
        "explanation": "Câu hỏi 'When' (Khi nào) hỏi về thời gian. Đáp án (A) 'By Friday afternoon' trả lời chuẩn xác mốc thời gian hoàn tất.",
        "distractor_analysis": "[Bẫy Yes/No cho câu hỏi Wh-] B (Yes, I reported) là bẫy đồng âm 'report' và trả lời Yes cho câu hỏi 'When'. C (In the hall) trả lời cho câu hỏi 'Where'.",
        "paraphrase_pair": "ready = finalized = completed",
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 2",
        "question_no": 8,
        "sentence": "Who is responsible for authorizing travel expense claims?",
        "choice_a": "Around three hundred dollars.",
        "choice_b": "Ms. Gomez in accounting handles all of them.",
        "choice_c": "To attend the developer summit.",
        "choice_d": None,
        "correct_choice": "B",
        "explanation": "Câu hỏi 'Who' (Ai) hỏi về người chịu trách nhiệm. Đáp án (B) nêu rõ người phụ trách là Ms. Gomez phòng kế toán.",
        "distractor_analysis": "[Bẫy Trả Lời Lệch Thông Tin] A trả lời cho 'How much', C trả lời cho 'Why / What for'.",
        "paraphrase_pair": "responsible for authorizing = handles approval of",
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 2",
        "question_no": 9,
        "sentence": "Why was the cloud migration scheduled for Sunday midnight?",
        "choice_a": "To minimize disruption to active users.",
        "choice_b": "No, it wasn't on Sunday.",
        "choice_c": "The new cloud servers are fast.",
        "choice_d": None,
        "correct_choice": "A",
        "explanation": "Câu hỏi 'Why' (Tại sao) hỏi mục đích/lý do. Đáp án (A) dùng 'To + V' giải thích mục đích giảm thiểu gián đoạn người dùng.",
        "distractor_analysis": "[Bẫy Trực Tiếp Yes/No] B trả lời No cho câu hỏi 'Why'. C là câu khẳng định lạc đề.",
        "paraphrase_pair": "minimize disruption = reduce downtime for customers",
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 2",
        "question_no": 10,
        "sentence": "Where can I find the latest firmware documentation?",
        "choice_a": "Yes, I read the manual.",
        "choice_b": "It is uploaded on the internal engineering portal.",
        "choice_c": "Only twice this month.",
        "choice_d": None,
        "correct_choice": "B",
        "explanation": "Câu hỏi 'Where' (Ở đâu). Đáp án (B) chỉ rõ vị trí tài liệu được tải lên cổng nội bộ.",
        "distractor_analysis": "[Bẫy Tần Suất & Yes/No] A dùng Yes cho câu hỏi Where; C trả lời cho câu hỏi 'How often'.",
        "paraphrase_pair": "uploaded on the portal = posted on the internal intranet",
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 2",
        "question_no": 11,
        "sentence": "Could you help me set up the presentation equipment in Room 4B?",
        "choice_a": "Sure, I will be there in five minutes.",
        "choice_b": "The room has eighty chairs.",
        "choice_c": "Yes, the presentation was fascinating.",
        "choice_d": None,
        "correct_choice": "A",
        "explanation": "Lời yêu cầu giúp đỡ 'Could you help me...?'. Đáp án (A) đồng ý giúp đỡ nhiệt tình ('Sure, I will be there in 5 minutes').",
        "distractor_analysis": "[Bẫy Lạc Thì & Đồng Âm] C dùng thì quá khứ 'was fascinating' trong khi sự kiện sắp diễn ra.",
        "paraphrase_pair": "help set up = assist with configuring equipment",
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 2",
        "question_no": 12,
        "sentence": "Has the client signed the service level agreement yet?",
        "choice_a": "I'm still waiting for their legal counsel to review it.",
        "choice_b": "A ten percent discount.",
        "choice_c": "At the downtown branch.",
        "choice_d": None,
        "correct_choice": "A",
        "explanation": "Câu hỏi Yes/No 'Has the client signed...?'. Đáp án (A) là câu trả lời gián tiếp cực kỳ phổ biến trong đề thi TOEIC: chưa ký vì vẫn đang đợi luật sư xem xét.",
        "distractor_analysis": "[Bẫy Trả Lời Gián Tiếp] Đề thi TOEIC hiện đại 800+ thường không trả lời trực diện Yes/No mà dùng câu giải thích tình trạng thực tế.",
        "paraphrase_pair": "waiting for review = pending legal approval",
    },

    # --- Part 3: Short Conversations ---
    {
        "test_id": "ETS2024_01",
        "part": "Part 3",
        "question_no": 32,
        "sentence": "We need to allocate additional budget for database replication servers before the product launch.",
        "choice_a": "The budget was already approved by the board.",
        "choice_b": "We need to allocate additional budget for replication.",
        "choice_c": "The launch date has been moved up.",
        "choice_d": "No servers are currently available.",
        "correct_choice": "B",
        "explanation": "Câu then chốt trong hội thoại Part 3: người nói đề xuất phân bổ thêm ngân sách cho máy chủ sao lưu cơ sở dữ liệu.",
        "distractor_analysis": "[Bẫy Chi Tiết Sai] A, C, D đưa ra các thông tin phủ định không có trong hội thoại.",
        "paraphrase_pair": "allocate additional budget = assign extra financial resources",
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 3",
        "question_no": 33,
        "sentence": "Could you provide me with an updated itinerary for next week's Tokyo conference?",
        "choice_a": "I will email the latest flight schedule right away.",
        "choice_b": "The conference was held in Kyoto.",
        "choice_c": "I have not purchased the ticket yet.",
        "choice_d": "The presentation is thirty minutes long.",
        "correct_choice": "A",
        "explanation": "Yêu cầu lịch trình chi tiết (itinerary) được đáp lại bằng việc gửi email lịch bay ngay lập tức.",
        "distractor_analysis": "[Bẫy Nhầm Địa Danh] B đổi Tokyo thành Kyoto. D nói về thời lượng bài thuyết trình.",
        "paraphrase_pair": "updated itinerary = latest flight and meeting schedule",
    },
]


def seed_listening_questions():
    print("=== Seeding Listening Benchmark Questions (Part 1, Part 2, Part 3) ===")
    init_db()
    db = SessionLocal()
    try:
        # Ensure ETS2024_01 test exists
        mock_test = db.query(MockTest).filter_by(test_id="ETS2024_01").first()
        if not mock_test:
            mock_test = MockTest(
                test_id="ETS2024_01",
                name="ETS TOEIC 2024 Test 01 (Benchmark)",
                year=2024,
                publisher="ETS",
                total_questions=200,
            )
            db.add(mock_test)
            db.commit()

        added = 0
        updated = 0
        for item in LISTENING_QUESTIONS:
            exists = db.query(TestQuestion).filter_by(
                test_id=item["test_id"],
                part=item["part"],
                question_no=item["question_no"],
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
                    distractor_analysis=item["distractor_analysis"],
                    paraphrase_pair=item["paraphrase_pair"],
                    image_url=item.get("image_url"),
                    source="seed",
                    created_at=utcnow(),
                )
                db.add(q)
                added += 1
            else:
                if "image_url" in item:
                    exists.image_url = item["image_url"]
                    updated += 1
        db.commit()
        print(f"  ✓ Ingested {added} and updated {updated} Listening benchmark questions into ETS2024_01!")
    finally:
        db.close()


if __name__ == "__main__":
    seed_listening_questions()
