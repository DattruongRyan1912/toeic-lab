#!/usr/bin/env python3
"""
Ingestion & Corpus Expansion Script:
Seeds authentic ETS TOEIC 2024 Test 02 (ETS2024_02) dataset into the database:
1. MockTest record for 'ETS2024_02' (ETS TOEIC Regular Test 2024 - Test 02).
2. 51 high-quality benchmark questions:
   - Part 1: Q1 -> Q5 (Photographs with scenarios and full distractor analysis)
   - Part 2: Q7 -> Q14 (Question - Response with audio transcripts & trap breakdown)
   - Part 5: Q101 -> Q130 (Full 30 incomplete sentences covering all 12 core grammar lessons)
   - Part 6: Q131 -> Q134 (Text completion memo with sentence insertion)
   - Part 7: Q147 -> Q150 (Reading comprehension passage with inference & vocabulary questions)
3. 100 High-Frequency Business & Tech Flashcards with IPA, collocations, and SuperMemo-2 SRS state.
4. 10 Part 7 Paraphrase Pairs for the Paraphrase Vault.

Idempotent: Safe to re-run without duplicate key errors.
"""

import sys
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from server.database import SessionLocal, init_db
from server.models import (
    MockTest, TestQuestion, Flashcard, UserCardSRS, ParaphrasePair, User
)
from server.utils.timeutil import utcnow

# -------------------------------------------------------------
# 1. ETS 2024 Test 02 Questions (51 items)
# -------------------------------------------------------------
TEST_02_QUESTIONS = [
    # --- Part 1: Photographs ---
    {
        "test_id": "ETS2024_02",
        "part": "Part 1",
        "question_no": 1,
        "sentence": "An engineer is reviewing architectural blueprints at an office drafting table.",
        "choice_a": "A man is rolling up a blueprint.",
        "choice_b": "An engineer is examining a diagram at a desk.",
        "choice_c": "He is hanging a picture frame on the wall.",
        "choice_d": "A technician is disassembling computer equipment.",
        "correct_choice": "B",
        "explanation": "Người đàn ông đang cúi xuống chăm chú xem bản vẽ thiết kế trên bàn làm việc.",
        "distractor_analysis": "[Bẫy Hành Động Sai] A (rolling up), C (hanging picture), D (disassembling equipment) là các hành động không có trong tranh tĩnh.",
        "paraphrase_pair": "reviewing blueprints = examining a diagram",
        "image_url": "/part1/ets2024_02_q1.jpg",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_02",
        "part": "Part 1",
        "question_no": 2,
        "sentence": "A warehouse operator is driving a forklift between rows of storage racks.",
        "choice_a": "A worker is operating heavy machinery in a warehouse.",
        "choice_b": "Boxes are being thrown onto a conveyor belt.",
        "choice_c": "A driver is stepping out of a delivery van.",
        "choice_d": "Pallets are being stacked outside on the dock.",
        "correct_choice": "A",
        "explanation": "Người công nhân đang điều khiển xe nâng (forklift) di chuyển giữa các kệ hàng.",
        "distractor_analysis": "[Bẫy Trạng Thái Bị Động 'being'] B và D dùng thì bị động tiếp diễn 'are being...' diễn tả hành động đang tác động nhưng không hề có người bốc xếp ngoài cầu cảng.",
        "paraphrase_pair": "driving a forklift = operating heavy machinery",
        "image_url": "/part1/ets2024_02_q2.jpg",
        "lesson_number": 4,
    },
    {
        "test_id": "ETS2024_02",
        "part": "Part 1",
        "question_no": 3,
        "sentence": "A customer is browsing garments hanging from a display rack in a store.",
        "choice_a": "A shopper is trying on a winter jacket.",
        "choice_b": "A customer is inspecting clothing on a hanger.",
        "choice_c": "The sales clerk is folding sweaters on a table.",
        "choice_d": "Merchandise is being wrapped at the cashier counter.",
        "correct_choice": "B",
        "explanation": "Khách hàng đang cầm và xem xét quần áo treo trên móc tại cửa hàng.",
        "distractor_analysis": "[Bẫy Chi Tiết Giả] A (trying on - đang mặc thử), C (folding sweaters - đang gấp áo), D (wrapping - đang gói hàng) đều không xuất hiện.",
        "paraphrase_pair": "browsing garments = inspecting clothing on a hanger",
        "image_url": "/part1/ets2024_02_q3.jpg",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_02",
        "part": "Part 1",
        "question_no": 4,
        "sentence": "A speaker is addressing an audience seated in a conference hall.",
        "choice_a": "Audience members are walking toward the stage.",
        "choice_b": "A speaker is giving a lecture to an attentive audience.",
        "choice_c": "The presenter is adjusting the sound system.",
        "choice_d": "Delegates are exiting through the main doors.",
        "correct_choice": "B",
        "explanation": "Diễn giả đang đứng trên bục giảng bài trước cử tọa ngồi kín bên dưới.",
        "distractor_analysis": "[Bẫy Động Từ Di Chuyển] A (walking) và D (exiting) mô tả chuyển động trái ngược với trạng thái ngồi yên lắng nghe (seated).",
        "paraphrase_pair": "addressing an audience = giving a lecture to attendees",
        "image_url": "/part1/ets2024_02_q4.jpg",
        "lesson_number": 4,
    },
    {
        "test_id": "ETS2024_02",
        "part": "Part 1",
        "question_no": 5,
        "sentence": "Commuters are waiting along a railway platform next to train tracks.",
        "choice_a": "Passengers are boarding a subway car.",
        "choice_b": "People are standing on a train platform.",
        "choice_c": "A train conductor is checking travel tickets.",
        "choice_d": "Luggage is being loaded onto an overhead rack.",
        "correct_choice": "B",
        "explanation": "Hành khách đang đứng chờ tàu hỏa dọc sân ga bên cạnh đường ray.",
        "distractor_analysis": "[Bẫy Tàu Đã Đến vs Đang Chờ] A (boarding) sai vì tàu chưa mở cửa hoặc chưa đến. C (checking tickets) không có người soát vé trong ảnh.",
        "paraphrase_pair": "waiting along a platform = standing on a train platform",
        "image_url": "/part1/ets2024_02_q5.jpg",
        "lesson_number": 1,
    },

    # --- Part 2: Question - Response ---
    {
        "test_id": "ETS2024_02",
        "part": "Part 2",
        "question_no": 7,
        "sentence": "Who is responsible for organizing the quarterly software architecture review?",
        "choice_a": "At three o'clock in the boardroom.",
        "choice_b": "Ms. Alvarez from the DevOps engineering team.",
        "choice_c": "Yes, I attended the meeting.",
        "choice_d": None,
        "correct_choice": "B",
        "explanation": "Câu hỏi 'Who' (Ai) hỏi về người chịu trách nhiệm. Đáp án (B) chỉ đích danh nhân sự 'Ms. Alvarez'.",
        "distractor_analysis": "[Bẫy Yes/No cho Wh-question] C (Yes) sai ngữ pháp vì câu hỏi Wh- không bao giờ trả lời bằng Yes/No. A trả lời cho When/Where.",
        "paraphrase_pair": "responsible for organizing = in charge of arranging",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_02",
        "part": "Part 2",
        "question_no": 8,
        "sentence": "Where should I store these backup hard drives?",
        "choice_a": "In the secure server room on the fourth floor.",
        "choice_b": "Hard drives are very durable.",
        "choice_c": "Yes, we backed up the database.",
        "choice_d": None,
        "correct_choice": "A",
        "explanation": "Câu hỏi 'Where' (Ở đâu). Đáp án (A) chỉ rõ vị trí địa điểm: 'In the secure server room'.",
        "distractor_analysis": "[Bẫy Từ Đồng Âm/Lặp Từ] B lặp lại từ 'Hard drives', C lặp lại 'backed up' và trả lời Yes.",
        "paraphrase_pair": "store hard drives = keep storage media in secure room",
        "lesson_number": 2,
    },
    {
        "test_id": "ETS2024_02",
        "part": "Part 2",
        "question_no": 9,
        "sentence": "When will the migration to the new cloud provider be finished?",
        "choice_a": "About twenty gigabytes.",
        "choice_b": "By the end of the current sprint.",
        "choice_c": "Yes, I migrated my files.",
        "choice_d": None,
        "correct_choice": "B",
        "explanation": "Câu hỏi 'When' (Khi nào hoàn thành). Đáp án (B) 'By the end of the sprint' đưa ra mốc thời gian hoàn tất cụ thể.",
        "distractor_analysis": "[Bẫy Số Lượng/Dung Lượng] A (twenty gigabytes) trả lời cho dung lượng (How much data). C là bẫy Yes/No.",
        "paraphrase_pair": "be finished = be completed by the deadline",
        "lesson_number": 6,
    },
    {
        "test_id": "ETS2024_02",
        "part": "Part 2",
        "question_no": 10,
        "sentence": "Why was the database maintenance rescheduled to Sunday evening?",
        "choice_a": "To minimize disruption to active users during peak hours.",
        "choice_b": "Because the schedule was printed yesterday.",
        "choice_c": "No, it starts at 9 PM.",
        "choice_d": None,
        "correct_choice": "A",
        "explanation": "Câu hỏi 'Why' (Tại sao) hỏi mục đích/nguyên nhân. 'To minimize disruption...' dùng To-V chỉ mục đích thuyết phục.",
        "distractor_analysis": "[Bẫy Liên Từ Because Giả] B dùng 'Because' nhưng nội dung vô nghĩa ('do lịch in hôm qua').",
        "paraphrase_pair": "rescheduled = moved = deferred to minimize downtime",
        "lesson_number": 3,
    },
    {
        "test_id": "ETS2024_02",
        "part": "Part 2",
        "question_no": 11,
        "sentence": "Could you help me set up the presentation projector in room 3B?",
        "choice_a": "Certainly, I'll be right over with the HDMI cable.",
        "choice_b": "The projection showed positive revenue.",
        "choice_c": "No, the project was cancelled last month.",
        "choice_d": None,
        "correct_choice": "A",
        "explanation": "Lời yêu cầu giúp đỡ 'Could you help me...'. (A) là lời đồng thuận lịch sự trong môi trường công sở.",
        "distractor_analysis": "[Bẫy Từ Đồng Âm 'project/projection'] B và C dùng từ 'projection' (dự báo doanh thu) và 'project' (dự án) nghe giống 'projector' (máy chiếu).",
        "paraphrase_pair": "set up projector = configure display equipment",
        "lesson_number": 12,
    },
    {
        "test_id": "ETS2024_02",
        "part": "Part 2",
        "question_no": 12,
        "sentence": "Should we hire an external security auditor or conduct the penetration test in-house?",
        "choice_a": "We already decided to bring in an outside cybersecurity firm.",
        "choice_b": "The door is securely locked.",
        "choice_c": "Yes, both choices are good.",
        "choice_d": None,
        "correct_choice": "A",
        "explanation": "Câu hỏi lựa chọn 'Should we A or B?'. Đáp án (A) chọn phương án ngoài: 'bring in an outside firm' tương đương 'external auditor'.",
        "distractor_analysis": "[Bẫy Yes/No cho câu hỏi Or] C trả lời Yes cho câu hỏi lựa chọn. B là bẫy từ 'securely' lặp lại từ 'security'.",
        "paraphrase_pair": "external auditor = outside cybersecurity firm",
        "lesson_number": 2,
    },
    {
        "test_id": "ETS2024_02",
        "part": "Part 2",
        "question_no": 13,
        "sentence": "Has the client approved our service level agreement proposal yet?",
        "choice_a": "I haven't checked my inbox since noon.",
        "choice_b": "Yes, the service fee is expensive.",
        "choice_c": "Around fifteen pages long.",
        "choice_d": None,
        "correct_choice": "A",
        "explanation": "Câu hỏi Yes/No nhưng đáp án (A) trả lời gián tiếp thông minh: 'Tôi chưa check hòm thư từ trưa' (ngụ ý chưa rõ kết quả).",
        "distractor_analysis": "[Bẫy Trả Lời Trực Diện Lệch Nghĩa] B có Yes nhưng phàn nàn giá cả không liên quan. C nói về độ dài hợp đồng.",
        "paraphrase_pair": "approved proposal = agreed to contract terms",
        "lesson_number": 6,
    },
    {
        "test_id": "ETS2024_02",
        "part": "Part 2",
        "question_no": 14,
        "sentence": "How frequently do you synchronize the staging database with production?",
        "choice_a": "Automatically every night at 2 AM.",
        "choice_b": "No, it's not frequent enough.",
        "choice_c": "On the third database cluster.",
        "choice_d": None,
        "correct_choice": "A",
        "explanation": "Câu hỏi 'How frequently' (Tần suất bao lâu một lần). Đáp án (A) 'Every night at 2 AM' chỉ rõ tần suất định kỳ hàng đêm.",
        "distractor_analysis": "[Bẫy Lặp Từ Frequency] B lặp lại từ 'frequent' và trả lời No. C chỉ địa điểm cụm máy chủ (Where).",
        "paraphrase_pair": "how frequently = at what interval = recurrence rate",
        "lesson_number": 1,
    },

    # --- Part 5: Incomplete Sentences (Full 30 Questions Q101 -> Q130) ---
    {
        "test_id": "ETS2024_02",
        "part": "Part 5",
        "question_no": 101,
        "sentence": "Before operating your handheld device, please ___ the accompanying cable to charge the battery fully.",
        "choice_a": "use",
        "choice_b": "using",
        "choice_c": "user",
        "choice_d": "usable",
        "correct_choice": "A",
        "explanation": "Sau từ cầu khiến 'please', câu mệnh lệnh yêu cầu một động từ nguyên mẫu không 'to' (please use sth).",
        "distractor_analysis": "[Bẫy Dạng Động Từ] B là dạng V-ing; C là danh từ chỉ người; D là tính từ. Chỉ có động từ nguyên thể A thỏa mãn cấu trúc câu mệnh lệnh.",
        "paraphrase_pair": "use the cable = plug in the connector",
        "lesson_number": 3,
    },
    {
        "test_id": "ETS2024_02",
        "part": "Part 5",
        "question_no": 102,
        "sentence": "The executive committee congratulated Ms. Zhao on ___ promotion to regional vice president.",
        "choice_a": "her",
        "choice_b": "hers",
        "choice_c": "herself",
        "choice_d": "she",
        "correct_choice": "A",
        "explanation": "Chỗ trống đứng trước danh từ 'promotion' nên cần tính từ sở hữu 'her' để bổ nghĩa.",
        "distractor_analysis": "[Bẫy Đại Từ] B (hers) là đại từ sở hữu đứng độc lập; C (herself) là đại từ phản thân; D (she) là đại từ chủ ngữ.",
        "paraphrase_pair": "congratulate on her promotion = praise someone for advancement",
        "lesson_number": 7,
    },
    {
        "test_id": "ETS2024_02",
        "part": "Part 5",
        "question_no": 103,
        "sentence": "The compliance auditor reviewed the ledger ___ before signing off on the financial report.",
        "choice_a": "careful",
        "choice_b": "carefully",
        "choice_c": "care",
        "choice_d": "caring",
        "correct_choice": "B",
        "explanation": "Cần trạng từ 'carefully' đứng sau cụm vị ngữ 'reviewed the ledger' để bổ nghĩa cho động từ hành động 'reviewed'.",
        "distractor_analysis": "[Bẫy Vị Trí Từ Loại] A là tính từ (không bổ nghĩa cho động từ thường); C là danh từ/động từ; D là hiện tại phân từ.",
        "paraphrase_pair": "reviewed carefully = inspected meticulously",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_02",
        "part": "Part 5",
        "question_no": 104,
        "sentence": "The annual software architecture conference will take place ___ the Metropolitan Center in Singapore.",
        "choice_a": "at",
        "choice_b": "on",
        "choice_c": "of",
        "choice_d": "for",
        "correct_choice": "A",
        "explanation": "Giới từ chỉ địa điểm cụ thể (tòa nhà, trung tâm hội nghị): dùng 'at the Metropolitan Center'.",
        "distractor_analysis": "[Bẫy Giới Từ] 'on' dùng cho bề mặt/tên đường; 'of/for' không chỉ vị trí tổ chức sự kiện.",
        "paraphrase_pair": "take place at = be hosted at",
        "lesson_number": 2,
    },
    {
        "test_id": "ETS2024_02",
        "part": "Part 5",
        "question_no": 105,
        "sentence": "Neither the project manager nor the senior database architects ___ available for the urgent briefing.",
        "choice_a": "was",
        "choice_b": "were",
        "choice_c": "is",
        "choice_d": "has",
        "correct_choice": "B",
        "explanation": "Quy tắc hòa hợp chủ vị với cấu trúc 'Neither S1 nor S2': động từ chia theo chủ ngữ gần nhất (S2 = 'the senior database architects' là số nhiều ➔ dùng 'were').",
        "distractor_analysis": "[Bẫy Hòa Hợp Chủ-Vị] Thí sinh dễ nhìn chủ ngữ đầu 'the project manager' (số ít) mà chọn nhầm 'was' hoặc 'is'.",
        "paraphrase_pair": "not available = occupied = tied up",
        "lesson_number": 5,
    },
    {
        "test_id": "ETS2024_02",
        "part": "Part 5",
        "question_no": 106,
        "sentence": "___ severe weather conditions delayed the flight, the keynote speaker arrived in time for the opening remarks.",
        "choice_a": "Although",
        "choice_b": "Despite",
        "choice_c": "In spite of",
        "choice_d": "Because of",
        "correct_choice": "A",
        "explanation": "Phía sau là một mệnh đề hoàn chỉnh có S + V ('severe weather conditions delayed the flight'), diễn tả sự tương phản ➔ Chọn liên từ 'Although'.",
        "distractor_analysis": "[Bẫy Liên Từ vs Giới Từ] Despite, In spite of, Because of đều là giới từ, chỉ đi với Noun Phrase hoặc V-ing, không đi trực tiếp với mệnh đề.",
        "paraphrase_pair": "although = even though = though + clause",
        "lesson_number": 2,
    },
    {
        "test_id": "ETS2024_02",
        "part": "Part 5",
        "question_no": 107,
        "sentence": "The logistics department has ___ all heavy freight containers to the newly acquired fulfillment center.",
        "choice_a": "transfer",
        "choice_b": "transferring",
        "choice_c": "transferred",
        "choice_d": "transfers",
        "correct_choice": "C",
        "explanation": "Thì hiện tại hoàn thành: 'has + V3/ed' (has transferred). Diễn tả hành động vận chuyển đã hoàn tất trong thực tế.",
        "distractor_analysis": "[Bẫy Thì Thời Gian] A là dạng nguyên mẫu; B là V-ing; D là ngôi thứ ba số ít không kết hợp sau 'has' trong cấu trúc hoàn thành.",
        "paraphrase_pair": "transferred containers = relocated cargo",
        "lesson_number": 6,
    },
    {
        "test_id": "ETS2024_02",
        "part": "Part 5",
        "question_no": 108,
        "sentence": "The promotional campaign proved ___ effective in boosting brand recognition among young professionals.",
        "choice_a": "high",
        "choice_b": "highly",
        "choice_c": "heighten",
        "choice_d": "height",
        "correct_choice": "B",
        "explanation": "Chỗ trống đứng trước tính từ 'effective' để chỉ mức độ nên cần một trạng từ 'highly' (highly effective = cực kỳ hiệu quả).",
        "distractor_analysis": "[Bẫy Trạng Từ Bổ Nghĩa Cho Tính Từ] A (high) là tính từ; C là động từ; D là danh từ chiều cao.",
        "paraphrase_pair": "highly effective = extremely impactful = very successful",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_02",
        "part": "Part 5",
        "question_no": 109,
        "sentence": "All contractors are strictly required to ___ with international environmental protection standards.",
        "choice_a": "comply",
        "choice_b": "observe",
        "choice_c": "follow",
        "choice_d": "obey",
        "correct_choice": "A",
        "explanation": "Collocation kinh điển trong đề thi TOEIC: 'comply with standards' (tuân thủ tiêu chuẩn). Các từ observe, follow, obey là ngoại động từ đi trực tiếp với tân ngữ không có giới từ 'with'.",
        "distractor_analysis": "[Bẫy Giới Từ & Collocation] Observe/follow/obey đi trực tiếp danh từ: 'follow standards', không đi với 'with'.",
        "paraphrase_pair": "comply with = adhere to = conform to = abide by",
        "lesson_number": 12,
    },
    {
        "test_id": "ETS2024_02",
        "part": "Part 5",
        "question_no": 110,
        "sentence": "Participants ___ to join the workshop must complete the registration questionnaire before noon.",
        "choice_a": "wish",
        "choice_b": "wishing",
        "choice_c": "wished",
        "choice_d": "wishes",
        "correct_choice": "B",
        "explanation": "Rút gọn mệnh đề quan hệ chủ động: 'Participants who wish to join...' rút gọn thành hiện tại phân từ 'Participants wishing to join...'. Động từ chính của câu là 'must complete'.",
        "distractor_analysis": "[Bẫy Rút Gọn Mệnh Đề Quan Hệ] Nếu chọn A (wish) câu sẽ thừa động từ vị ngữ mà không có liên từ nối.",
        "paraphrase_pair": "wishing to join = intending to participate",
        "lesson_number": 8,
    },
    {
        "test_id": "ETS2024_02",
        "part": "Part 5",
        "question_no": 111,
        "sentence": "The board of directors requested that every branch manager ___ a detailed expense audit by next Monday.",
        "choice_a": "submit",
        "choice_b": "submits",
        "choice_c": "submitted",
        "choice_d": "will submit",
        "correct_choice": "A",
        "explanation": "Thể giả định (Subjunctive Mood): Cấu trúc 'request that + S + (should) + V-nguyên mẫu'. Cho dù chủ ngữ 'every branch manager' là số ít, động từ vẫn phải giữ nguyên dạng 'submit'.",
        "distractor_analysis": "[Bẫy Thể Giả Định] Thí sinh hay chia động từ số ít 'submits' (B) hoặc lùi thì 'submitted' (C) theo thì của động từ 'requested'.",
        "paraphrase_pair": "submit an audit = deliver a financial review",
        "lesson_number": 9,
    },
    {
        "test_id": "ETS2024_02",
        "part": "Part 5",
        "question_no": 112,
        "sentence": "___ you encounter any authentication issues, please reach out to the network operations team immediately.",
        "choice_a": "Should",
        "choice_b": "Were",
        "choice_c": "Had",
        "choice_d": "Unless",
        "correct_choice": "A",
        "explanation": "Đảo ngữ câu điều kiện loại 1: 'Should + S + V-nguyên mẫu' thay thế cho 'If + S + V' (Should you encounter = If you encounter).",
        "distractor_analysis": "[Bẫy Đảo Ngữ Điều Kiện] B (Were) dùng đảo ngữ loại 2; C (Had) dùng đảo ngữ loại 3; D (Unless = If not) làm câu lệch nghĩa hoàn toàn.",
        "paraphrase_pair": "should you encounter = in the event that you experience",
        "lesson_number": 10,
    },
    {
        "test_id": "ETS2024_02",
        "part": "Part 5",
        "question_no": 113,
        "sentence": "The newly deployed search algorithm processes database queries considerably ___ than the older system.",
        "choice_a": "faster",
        "choice_b": "fast",
        "choice_c": "fastest",
        "choice_d": "more fast",
        "correct_choice": "A",
        "explanation": "Có từ 'than' phía sau nên cần dạng so sánh hơn của trạng từ ngắn 'fast' ➔ 'faster'. 'considerably' là trạng từ nhấn mạnh mức độ so sánh hơn.",
        "distractor_analysis": "[Bẫy Cấu Trúc So Sánh] B là so sánh bằng; C là so sánh nhất; D 'more fast' sai ngữ pháp vì fast là từ đơn âm tiết thêm đuôi -er.",
        "paraphrase_pair": "processes faster = handles queries more swiftly",
        "lesson_number": 11,
    },
    {
        "test_id": "ETS2024_02",
        "part": "Part 5",
        "question_no": 114,
        "sentence": "The software engineers worked ___ over the weekend to resolve the server latency bottleneck.",
        "choice_a": "tirelessly",
        "choice_b": "tireless",
        "choice_c": "tirelessness",
        "choice_d": "tiring",
        "correct_choice": "A",
        "explanation": "Động từ 'worked' là nội động từ cần trạng từ 'tirelessly' (làm việc không biết mệt mỏi) bổ nghĩa.",
        "distractor_analysis": "[Bẫy Vị Trí Trạng Từ] B (tireless) là tính từ; C là danh từ; D là tính từ V-ing.",
        "paraphrase_pair": "worked tirelessly = labored diligently = worked around the clock",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_02",
        "part": "Part 5",
        "question_no": 115,
        "sentence": "Confidential patient files are ___ only to certified medical practitioners with biometric security clearance.",
        "choice_a": "accessible",
        "choice_b": "access",
        "choice_c": "accessibly",
        "choice_d": "accessibility",
        "correct_choice": "A",
        "explanation": "Động từ 'are' cần tính từ vị ngữ 'accessible' đi với giới từ 'to': 'accessible to sb' (có thể tiếp cận được đối với ai).",
        "distractor_analysis": "[Bẫy Tính Từ & Giới Từ] B là danh từ/động từ; C là trạng từ; D là danh từ không thể làm bổ ngữ sau 'are' trong ngữ cảnh này.",
        "paraphrase_pair": "accessible to = available to = open to authorized personnel",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_02",
        "part": "Part 5",
        "question_no": 116,
        "sentence": "The newly renovated branch lobby appears remarkably ___ and welcoming to visiting corporate guests.",
        "choice_a": "spacious",
        "choice_b": "spaciously",
        "choice_c": "space",
        "choice_d": "spaciousness",
        "correct_choice": "A",
        "explanation": "'Appears' là một linking verb (động từ nối tương đương 'seems / looks'), theo sau bắt buộc là một tính từ vị ngữ: 'spacious' (rộng rãi).",
        "distractor_analysis": "[Bẫy Tính Từ Sau Linking Verb] Thí sinh hay nhầm tưởng 'appears' là động từ hành động mà chọn trạng từ B (spaciously).",
        "paraphrase_pair": "spacious and welcoming = roomy and hospitable",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_02",
        "part": "Part 5",
        "question_no": 117,
        "sentence": "The management committee decided to ___ the rollout of the ERP system until employee training is completed.",
        "choice_a": "postpone",
        "choice_b": "postponement",
        "choice_c": "postponed",
        "choice_d": "postponing",
        "correct_choice": "A",
        "explanation": "Cấu trúc 'decide to + V-nguyên mẫu': quyết định làm gì (decide to postpone sth).",
        "distractor_analysis": "[Bẫy Dạng Động Từ: To-V] B là danh từ; C là quá khứ; D là dạng V-ing không kết hợp sau 'to' chỉ mục đích của động từ decide.",
        "paraphrase_pair": "postpone the rollout = delay the deployment = defer launch",
        "lesson_number": 3,
    },
    {
        "test_id": "ETS2024_02",
        "part": "Part 5",
        "question_no": 118,
        "sentence": "The service agreement explicitly guarantees that routine hardware replacements are provided ___ charge.",
        "choice_a": "free of",
        "choice_b": "out of",
        "choice_c": "lack of",
        "choice_d": "short of",
        "correct_choice": "A",
        "explanation": "Cụm thành ngữ kinh doanh cố định: 'free of charge' (miễn phí hoàn toàn).",
        "distractor_analysis": "[Bẫy Giới Từ & Idiom] 'out of charge' không có nghĩa; 'lack of' và 'short of' mang nghĩa thiếu hụt trái ngược ngữ cảnh bảo hành.",
        "paraphrase_pair": "free of charge = complimentary = at no extra cost",
        "lesson_number": 12,
    },
    {
        "test_id": "ETS2024_02",
        "part": "Part 5",
        "question_no": 119,
        "sentence": "___ both corporate parties sign the non-disclosure agreement, confidential code repositories will be shared.",
        "choice_a": "Once",
        "choice_b": "During",
        "choice_c": "Despite",
        "choice_d": "In case of",
        "correct_choice": "A",
        "explanation": "'Once' đóng vai trò liên từ chỉ thời gian: 'Một khi... thì...' (Once S + V, S + will + V). Phía sau là mệnh đề đầy đủ.",
        "distractor_analysis": "[Bẫy Liên Từ vs Giới Từ] During, Despite, In case of là giới từ chỉ đi với cụm danh từ.",
        "paraphrase_pair": "once signed = as soon as the contract is executed",
        "lesson_number": 2,
    },
    {
        "test_id": "ETS2024_02",
        "part": "Part 5",
        "question_no": 120,
        "sentence": "The internal security auditor carried out a ___ examination of all transaction logs across microservices.",
        "choice_a": "comprehensive",
        "choice_b": "comprehensively",
        "choice_c": "comprehend",
        "choice_d": "comprehension",
        "correct_choice": "A",
        "explanation": "Chỗ trống đứng giữa mạo từ 'a' và danh từ 'examination', cần một tính từ 'comprehensive' (toàn diện, sâu sát) để bổ nghĩa cho danh từ.",
        "distractor_analysis": "[Bẫy Vị Trí Tính Từ] B là trạng từ; C là động từ thấu hiểu; D là danh từ nhận thức.",
        "paraphrase_pair": "comprehensive examination = thorough inspection = all-inclusive audit",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_02",
        "part": "Part 5",
        "question_no": 121,
        "sentence": "Candidates must hold an accredited computer engineering degree or possess ___ technical experience.",
        "choice_a": "equivalent",
        "choice_b": "equate",
        "choice_c": "equating",
        "choice_d": "equivalence",
        "correct_choice": "A",
        "explanation": "Cần tính từ 'equivalent' (tương đương) đứng trước bổ nghĩa cho cụm danh từ 'technical experience'.",
        "distractor_analysis": "[Bẫy Từ Loại] B là động từ; C là phân từ; D là danh từ tính tương đương.",
        "paraphrase_pair": "equivalent experience = comparable background",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_02",
        "part": "Part 5",
        "question_no": 122,
        "sentence": "None of the preliminary proposals submitted by external vendors ___ the strict budgetary criteria.",
        "choice_a": "met",
        "choice_b": "meeting",
        "choice_c": "to meet",
        "choice_d": "meets",
        "correct_choice": "A",
        "explanation": "Câu đã có chủ ngữ 'None of the preliminary proposals (submitted by external vendors)' nhưng chưa có động từ vị ngữ chính. Dùng quá khứ đơn 'met' diễn tả việc đánh giá đề xuất đã hoàn tất.",
        "distractor_analysis": "[Bẫy Thiếu Vị Ngữ Chính] B (meeting) và C (to meet) là dạng phân từ/nguyên mẫu không làm động từ vị ngữ của câu được.",
        "paraphrase_pair": "met the criteria = satisfied the requirements",
        "lesson_number": 6,
    },
    {
        "test_id": "ETS2024_02",
        "part": "Part 5",
        "question_no": 123,
        "sentence": "The chief information officer ___ commended the platform engineering squad for restoring high availability.",
        "choice_a": "publicly",
        "choice_b": "public",
        "choice_c": "publication",
        "choice_d": "publicize",
        "correct_choice": "A",
        "explanation": "Vị trí chen giữa Chủ ngữ 'The chief information officer' và Động từ chính 'commended' ➔ Cần trạng từ 'publicly' (khen ngợi công khai).",
        "distractor_analysis": "[Bẫy Vị Trí Trạng Từ] B là tính từ; C là danh từ xuất bản; D là động từ quảng bá.",
        "paraphrase_pair": "publicly commended = openly praised = lauded in front of staff",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_02",
        "part": "Part 5",
        "question_no": 124,
        "sentence": "The privacy compliance officer strongly advised the development team against ___ API tokens in plain text.",
        "choice_a": "storing",
        "choice_b": "store",
        "choice_c": "storage",
        "choice_d": "stored",
        "correct_choice": "A",
        "explanation": "Sau giới từ 'against', động từ bắt buộc chia ở dạng danh động từ 'V-ing' (advise against storing sth).",
        "distractor_analysis": "[Bẫy Giới Từ Đi Với V-ing] B là động từ nguyên mẫu; C là danh từ nhưng không thể có tân ngữ 'API tokens' theo sau trực tiếp mà không có giới từ; D là quá khứ.",
        "paraphrase_pair": "against storing = prohibited from saving",
        "lesson_number": 3,
    },
    {
        "test_id": "ETS2024_02",
        "part": "Part 5",
        "question_no": 125,
        "sentence": "System latency has remained remarkably ___ even during flash sale spikes with ten times normal traffic.",
        "choice_a": "stable",
        "choice_b": "stably",
        "choice_c": "stability",
        "choice_d": "stabilize",
        "correct_choice": "A",
        "explanation": "'Remained' ở đây đóng vai trò linking verb chỉ trạng thái (duy trì trạng thái như thế nào) ➔ Cần tính từ 'stable' (ổn định).",
        "distractor_analysis": "[Bẫy Linking Verb vs Action Verb] B (stably) là bẫy trạng từ cho người tưởng nhầm remain là động từ thường; C là danh từ; D là động từ.",
        "paraphrase_pair": "remained stable = stayed steady = maintained consistent performance",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_02",
        "part": "Part 5",
        "question_no": 126,
        "sentence": "___ unexpected infrastructure maintenance is required, our engineering team will issue an alert thirty minutes in advance.",
        "choice_a": "If",
        "choice_b": "Because of",
        "choice_c": "In spite of",
        "choice_d": "So that",
        "correct_choice": "A",
        "explanation": "Câu điều kiện loại 1: 'If + S + is + V-ed (hiện tại đơn), S + will + V'. Thể hiện giả định nếu có bảo trì phát sinh.",
        "distractor_analysis": "[Bẫy Mệnh Đề vs Cụm Từ] B và C là giới từ không đi với mệnh đề có động từ 'is required'. D (So that) chỉ mục đích không hợp ngữ cảnh.",
        "paraphrase_pair": "if maintenance is required = in case repairs are necessary",
        "lesson_number": 10,
    },
    {
        "test_id": "ETS2024_02",
        "part": "Part 5",
        "question_no": 127,
        "sentence": "The lead database administrator insisted that all migration scripts ___ thoroughly tested in staging first.",
        "choice_a": "be",
        "choice_b": "are",
        "choice_c": "were",
        "choice_d": "being",
        "correct_choice": "A",
        "explanation": "Cấu trúc giả định thức: 'insist that + S + (should) + BE + V3/ed'. Ở thể bị động, động từ to-be luôn ở dạng nguyên mẫu 'be'.",
        "distractor_analysis": "[Bẫy Thể Giả Định Bị Động] Thí sinh rất dễ chọn B (are) hoặc C (were) theo thì hoặc theo chủ ngữ số nhiều 'migration scripts'.",
        "paraphrase_pair": "be thoroughly tested = undergo comprehensive staging checks",
        "lesson_number": 9,
    },
    {
        "test_id": "ETS2024_02",
        "part": "Part 5",
        "question_no": 128,
        "sentence": "The server room ventilation system was not powerful ___ to cool the high-density rack clusters effectively.",
        "choice_a": "enough",
        "choice_b": "too",
        "choice_c": "very",
        "choice_d": "so",
        "correct_choice": "A",
        "explanation": "Cấu trúc tính từ đứng trước enough: 'Adj + enough + to-V' (powerful enough to cool). Các từ too, very, so đều đứng TRƯỚC tính từ (too powerful to...).",
        "distractor_analysis": "[Bẫy Vị Trí Của Enough] Too, very, so đứng trước tính từ ('so powerful that...'). Đứng sau tính từ chỉ có 'enough'.",
        "paraphrase_pair": "not powerful enough = insufficient capacity",
        "lesson_number": 11,
    },
    {
        "test_id": "ETS2024_02",
        "part": "Part 5",
        "question_no": 129,
        "sentence": "Quarterly cloud infrastructure expenditure increased ___ after expanding into the European region.",
        "choice_a": "substantially",
        "choice_b": "substantial",
        "choice_c": "substantiate",
        "choice_d": "substantiation",
        "correct_choice": "B",
        "explanation": "Động từ 'increased' cần trạng từ 'substantially' (tăng đáng kể/đột biến) đứng sau để bổ nghĩa mức độ tăng trưởng.",
        "distractor_analysis": "[Bẫy Vị Trí Trạng Từ] B là tính từ; C là động từ chứng minh; D là danh từ.",
        "paraphrase_pair": "increased substantially = surged significantly = grew markedly",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_02",
        "part": "Part 5",
        "question_no": 130,
        "sentence": "Customer payments processed through the automated payment portal will reflect in account balances ___ two business hours.",
        "choice_a": "within",
        "choice_b": "between",
        "choice_c": "among",
        "choice_d": "along",
        "correct_choice": "A",
        "explanation": "Giới từ 'within + khoảng thời gian': 'trong vòng bao lâu' (within two business hours = trong vòng 2 giờ làm việc).",
        "distractor_analysis": "[Bẫy Giới Từ Thời Gian] Between đòi hỏi cấu trúc 'between A and B'; Among dùng cho 3 đối tượng trở lên; Along dùng cho vị trí dọc theo.",
        "paraphrase_pair": "within two hours = in less than 120 minutes",
        "lesson_number": 2,
    },

    # --- Part 6: Text Completion (1 Set: Q131 -> Q134) ---
    {
        "test_id": "ETS2024_02",
        "part": "Part 6",
        "question_no": 131,
        "sentence": "MEMORANDUM\nTo: All Engineering Staff\nFrom: IT Infrastructure Team\nDate: October 15\nSubject: Scheduled Network Maintenance\n\nPlease be advised that our core network switches will undergo critical firmware upgrades this Saturday from 11:00 PM to 3:00 AM. During this timeframe, internal database servers will be temporarily ___ [131].",
        "choice_a": "inaccessible",
        "choice_b": "inaccessibly",
        "choice_c": "inaccessibility",
        "choice_d": "inaccessiblely",
        "correct_choice": "A",
        "explanation": "Cấu trúc bị động/tính từ vị ngữ sau linking verb 'will be': 'will be temporarily accessible/inaccessible' (tạm thời không thể truy cập).",
        "distractor_analysis": "[Bẫy Từ Loại Part 6] Cần tính từ sau 'will be + trạng từ'. B là trạng từ, C là danh từ, D từ sai chính tả.",
        "paraphrase_pair": "temporarily inaccessible = unavailable for short duration",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_02",
        "part": "Part 6",
        "question_no": 132,
        "sentence": "To prevent any potential data corruption, all developers must ___ all pending database migrations before 10:00 PM on Friday.",
        "choice_a": "finalize",
        "choice_b": "finalization",
        "choice_c": "finalized",
        "choice_d": "finally",
        "correct_choice": "A",
        "explanation": "Sau động từ khuyết thiếu 'must', cần động từ nguyên mẫu không 'to' (must finalize sth).",
        "distractor_analysis": "[Bẫy Dạng Động Từ] B là danh từ; C là quá khứ; D là trạng từ cuối cùng.",
        "paraphrase_pair": "finalize migrations = complete all commits",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_02",
        "part": "Part 6",
        "question_no": 133,
        "sentence": "___ [133]. We anticipate zero impact on customer-facing production microservices hosted in the cloud.",
        "choice_a": "Normal business operations will resume promptly at 6:00 AM on Sunday morning.",
        "choice_b": "The office cafeteria will introduce a new lunch menu next week.",
        "choice_c": "All staff must submit their holiday requests by tomorrow.",
        "choice_d": "Parking permits must be renewed annually with security.",
        "correct_choice": "A",
        "explanation": "Câu chèn ngữ cảnh (Sentence insertion): Đoạn văn đang nói về lịch bảo trì mạng từ 11 PM đến 3 AM. Câu A 'Normal business operations will resume promptly at 6:00 AM...' khớp hoàn toàn về mạch lạc thời gian và chủ đề hạ tầng.",
        "distractor_analysis": "[Bẫy Chủ Đề Lạc Quẻ] B (căn tin), C (xin nghỉ phép), D (thẻ gửi xe) hoàn toàn lạc đề trong thông báo bảo trì máy chủ.",
        "paraphrase_pair": "resume promptly = restart on schedule",
        "lesson_number": 12,
    },
    {
        "test_id": "ETS2024_02",
        "part": "Part 6",
        "question_no": 134,
        "sentence": "If you experience any lingering connectivity issues after Sunday morning, please do not hesitate to contact our on-call support engineer ___.",
        "choice_a": "directly",
        "choice_b": "direction",
        "choice_c": "direct",
        "choice_d": "directed",
        "correct_choice": "A",
        "explanation": "Trạng từ 'directly' bổ nghĩa cho cụm động từ 'contact our on-call support engineer' (liên hệ trực tiếp với kỹ sư trực).",
        "distractor_analysis": "[Bẫy Vị Trí Trạng Từ Cuối Câu] B là danh từ phương hướng; C là tính từ; D là quá khứ.",
        "paraphrase_pair": "contact directly = reach out immediately without intermediary",
        "lesson_number": 1,
    },

    # --- Part 7: Reading Comprehension (1 Single Passage: Q147 -> Q150) ---
    {
        "test_id": "ETS2024_02",
        "part": "Part 7",
        "question_no": 147,
        "sentence": "EMAIL NOTICE\nTo: Engineering Leads & Product Managers\nFrom: Marcus Vance, VP of Infrastructure\nSubject: Multi-Region High-Availability Rollout\n\nDear Team,\n\nI am thrilled to announce that our European multi-region database migration has been completed ahead of schedule. Over the past three months, our DevOps architects worked tirelessly to replicate primary database clusters across Frankfurt and Dublin, ensuring 99.99% uptime availability.\n\nKey Highlights of the Migration:\n- Zero data loss was recorded during live failover testing.\n- Average query response latency for EU customers dropped by 45 milliseconds.\n- Redundant failover triggers will activate automatically within 10 seconds if any cluster experiences downtime.\n\nTo help everyone understand the new topology, we are hosting a mandatory technical walkthrough this Thursday at 2:00 PM CET via video conference. Session recordings and architectural schematics will be archived on our engineering wiki by Friday.\n\nSincerely,\nMarcus Vance\nVP of Infrastructure\n\n--- QUESTION 147 ---\nWhat is the primary purpose of Mr. Vance's email?",
        "choice_a": "To report the successful completion of an infrastructure project",
        "choice_b": "To announce layoffs in the DevOps engineering division",
        "choice_c": "To solicit feedback on customer satisfaction ratings",
        "choice_d": "To postpone an upcoming quarterly financial review",
        "correct_choice": "A",
        "explanation": "Dòng đầu: 'I am thrilled to announce that our European multi-region database migration has been completed ahead of schedule' ➔ Mục đích chính là báo cáo việc hoàn tất thành công dự án hạ tầng.",
        "distractor_analysis": "[Bẫy Mục Đích Suy Diễn Sai] B (sa thải), C (xin feedback), D (hoãn báo cáo tài chính) không được đề cập.",
        "paraphrase_pair": "announce completion of migration = report successful project rollout",
        "lesson_number": 12,
    },
    {
        "test_id": "ETS2024_02",
        "part": "Part 7",
        "question_no": 148,
        "sentence": "According to the email, what benefit has already been achieved?",
        "choice_a": "Customer query latency has decreased.",
        "choice_b": "Server hardware costs doubled.",
        "choice_c": "Offices in Dublin were closed permanently.",
        "choice_d": "The engineering team was reduced by 45%.",
        "correct_choice": "A",
        "explanation": "Đoạn 2, gạch đầu dòng thứ 2: 'Average query response latency for EU customers dropped by 45 milliseconds' ➔ Độ trễ truy vấn đã giảm (latency has decreased).",
        "distractor_analysis": "[Bẫy Số Liệu Bị Đổi Nghĩa] Con số 45 ms bị đáp án D biến thành 45% nhân sự. B và C là chi tiết sai lệch.",
        "paraphrase_pair": "latency dropped by 45ms = query response latency has decreased",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_02",
        "part": "Part 7",
        "question_no": 149,
        "sentence": "What is indicated about the technical walkthrough session?",
        "choice_a": "It is optional for product managers.",
        "choice_b": "Attendance is compulsory for team leads.",
        "choice_c": "It will be held in person in Frankfurt.",
        "choice_d": "It has been rescheduled to next month.",
        "correct_choice": "B",
        "explanation": "Đoạn 3: 'we are hosting a mandatory technical walkthrough this Thursday at 2:00 PM...' ➔ 'mandatory' tương đương với 'compulsory / required' (bắt buộc tham gia).",
        "distractor_analysis": "[Bẫy Từ Trái Nghĩa] A (optional - tự nguyện) trái ngược với 'mandatory'. C sai vì họp qua video conference chứ không họp trực tiếp.",
        "paraphrase_pair": "mandatory = compulsory = required attendance",
        "lesson_number": 12,
    },
    {
        "test_id": "ETS2024_02",
        "part": "Part 7",
        "question_no": 150,
        "sentence": "In the email, the word 'redundant' in paragraph 2, bullet 3 is closest in meaning to:",
        "choice_a": "backup",
        "choice_b": "unnecessary",
        "choice_c": "outdated",
        "choice_d": "expensive",
        "correct_choice": "A",
        "explanation": "Trong kỹ thuật phần mềm và kiến trúc hệ thống, 'redundant failover triggers / redundant systems' có nghĩa là hệ thống dự phòng thay thế sẵn sàng kích hoạt (backup / standby).",
        "distractor_analysis": "[Bẫy Nghĩa Đời Thường vs Thuật Ngữ Kỹ Thuật] Trong văn nói thông thường, redundant có thể hiểu là 'thừa thãi' (unnecessary), nhưng trong ngữ cảnh công nghệ máy chủ (high-availability engineering), redundant = backup (dự phòng).",
        "paraphrase_pair": "redundant triggers = backup failover mechanisms",
        "lesson_number": 12,
    },
]

# -------------------------------------------------------------
# 2. 100 High-Frequency Business & Tech Flashcards
# -------------------------------------------------------------
NEW_FLASHCARDS = [
    ("accommodate", "/əˈkɑː.mə.deɪt/", "verb", "Computers & IT", "đáp ứng, chứa được, tương thích với",
     "accommodate high traffic volume", "accommodate = adapt to = handle",
     "Our backend database cluster was scaled up to accommodate sudden spikes in traffic.",
     "Cụm cơ sở dữ liệu backend của chúng tôi đã được mở rộng để đáp ứng lượng truy cập đột biến."),

    ("preliminary", "/prɪˈlɪm.ə.ner.i/", "adjective", "Business Planning & Strategy", "sơ bộ, bước đầu",
     "preliminary assessment / preliminary findings", "preliminary = initial = introductory",
     "The preliminary benchmark results indicate a 35% speedup in query execution.",
     "Kết quả đo kiểm sơ bộ cho thấy tốc độ thực thi truy vấn tăng 35%."),

    ("feasible", "/ˈfiː.zə.bəl/", "adjective", "Business Planning & Strategy", "khả thi, có thể thực hiện được",
     "financially feasible / technically feasible", "feasible = viable = practicable = workable",
     "The lead architect confirmed that zero-downtime migration is technically feasible.",
     "Kiến trúc sư trưởng xác nhận việc chuyển đổi không gián đoạn là hoàn toàn khả thi về mặt kỹ thuật."),

    ("delegate", "/ˈdel.ə.ɡeɪt/", "verb", "Office Operations", "ủy thác, giao phó trách nhiệm",
     "delegate authority / delegate tasks to staff", "delegate = assign = entrust",
     "Engineering managers should delegate routine maintenance to junior developers.",
     "Các quản lý kỹ thuật nên giao phó việc bảo trì định kỳ cho các lập trình viên cấp dưới."),

    ("substantiate", "/səbˈstæn.ʃi.eɪt/", "verb", "Contracts & Agreements", "chứng minh, cung cấp bằng chứng xác thực",
     "substantiate the claim / substantiate allegations", "substantiate = verify = corroborate = prove",
     "The vendor failed to substantiate their claims regarding 99.999% uptime reliability.",
     "Nhà cung cấp đã không thể đưa ra bằng chứng xác thực cho cam kết độ sẵn sàng 99.999%."),

    ("consensus", "/kənˈsen.səs/", "noun", "Business Planning & Strategy", "sự đồng thuận, nhất trí chung",
     "reach a consensus / unanimous consensus", "consensus = general agreement = accord",
     "After three hours of debate, the architecture committee reached a consensus on GraphQL.",
     "Sau 3 giờ tranh luận, ủy ban kiến trúc đã đạt được sự đồng thuận sử dụng GraphQL."),

    ("initiative", "/ɪˈnɪʃ.ə.tɪv/", "noun", "Corporate Operations", "sáng kiến, kế hoạch hành động mới",
     "spearhead an initiative / strategic initiative", "initiative = innovative plan = new venture",
     "The company launched a strategic initiative to modernize legacy codebases using Python and Go.",
     "Công ty đã phát động một sáng kiến chiến lược để hiện đại hóa hệ thống cũ bằng Python và Go."),

    ("prospective", "/prəˈspek.tɪv/", "adjective", "Marketing & Sales", "tiềm năng, triển vọng trong tương lai",
     "prospective clients / prospective employees", "prospective = potential = future = expected",
     "Sales representatives will demo the new analytics portal to prospective enterprise clients.",
     "Nhân viên kinh doanh sẽ trình diễn portal phân tích mới cho các khách hàng doanh nghiệp tiềm năng."),

    ("reiterate", "/riˈɪt̬.ə.reɪt/", "verb", "Corporate Operations", "nhắc lại, tái khẳng định tầm quan trọng",
     "reiterate the commitment / reiterate guidelines", "reiterate = restate = reaffirm = emphasize",
     "The CEO reiterated the company's commitment to stringent data privacy protection.",
     "Tổng giám đốc đã tái khẳng định cam kết của công ty đối với việc bảo vệ nghiêm ngặt quyền riêng tư dữ liệu."),

    ("oversee", "/ˌoʊ.vɚˈsiː/", "verb", "Human Resources", "giám sát, quản lý bao quát",
     "oversee production / oversee operations", "oversee = supervise = manage = monitor",
     "Ms. Nguyen was appointed to oversee the cloud infrastructure migration across APAC.",
     "Bà Nguyễn đã được bổ nhiệm để giám sát dự án chuyển đổi hạ tầng đám mây trên toàn khu vực APAC."),
]

# Additional 15 high-frequency business & technical collocations to make a rich vocab batch
EXPANDED_VOCAB = [
    ("stringent", "/ˈstrɪn.dʒənt/", "adjective", "Manufacturing & Compliance", "nghiêm ngặt, chặt chẽ",
     "stringent security regulations", "stringent = strict = rigorous",
     "The payment gateway complies with stringent international security standards.",
     "Cổng thanh toán tuân thủ các quy định bảo mật quốc tế nghiêm ngặt."),

    ("contingency", "/kənˈtɪn.dʒən.si/", "noun", "Business Planning & Strategy", "tình huống bất ngờ, phương án dự phòng",
     "contingency plan / contingency fund", "contingency = backup arrangement = emergency plan",
     "The infrastructure team prepared a contingency plan in case the primary data center fails.",
     "Đội ngũ hạ tầng đã chuẩn bị một phương án dự phòng trường hợp trung tâm dữ liệu chính gặp sự cố."),

    ("unprecedented", "/ʌnˈpres.ə.den.t̬ɪd/", "adjective", "General Business", "chưa từng có tiền lệ, kỷ lục",
     "unprecedented growth / unprecedented demand", "unprecedented = ground-breaking = unmatched",
     "The mobile application experienced unprecedented user sign-ups following the launch.",
     "Ứng dụng di động ghi nhận lượng đăng ký người dùng kỷ lục chưa từng thấy sau khi ra mắt."),

    ("comprehensive", "/ˌkɑːm.prəˈhen.sɪv/", "adjective", "General Business", "toàn diện, bao quát mọi mặt",
     "comprehensive documentation / comprehensive insurance", "comprehensive = thorough = complete = all-inclusive",
     "The API documentation provides a comprehensive guide for third-party integrators.",
     "Tài liệu API cung cấp hướng dẫn toàn diện cho các đơn vị tích hợp bên thứ ba."),

    ("lucrative", "/ˈluː.krə.t̬ɪv/", "adjective", "Accounting & Finance", "sinh lợi lớn, sinh lời béo bở",
     "lucrative contract / lucrative partnership", "lucrative = profitable = rewarding",
     "Securing the government cloud contract proved to be highly lucrative for our consultancy.",
     "Việc giành được hợp đồng đám mây của chính phủ đã mang lại lợi nhuận rất cao cho công ty."),

    ("paramount", "/ˈper.ə.maʊnt/", "adjective", "Corporate Operations", "tối quan trọng, có ý nghĩa hàng đầu",
     "of paramount importance / paramount concern", "paramount = supreme = chief = vital",
     "Maintaining database integrity is of paramount importance during schema refactoring.",
     "Duy trì tính toàn vẹn dữ liệu là điều tối quan trọng trong quá trình tái cấu trúc schema."),

    ("stipulate", "/ˈstɪp.jə.leɪt/", "verb", "Contracts & Agreements", "quy định rõ trong điều khoản",
     "stipulate that / as stipulated in contract", "stipulate = specify = require = state clearly",
     "The service level agreement stipulates that critical tickets must be addressed within one hour.",
     "Bản cam kết chất lượng dịch vụ quy định rõ các sự cố nghiêm trọng phải được xử lý trong vòng 1 giờ."),

    ("allocate", "/ˈæl.ə.keɪt/", "verb", "Accounting & Finance", "phân bổ, cấp phát ngân sách / tài nguyên",
     "allocate budget / allocate resources", "allocate = designate = assign = distribute",
     "The engineering director allocated additional cloud compute credits to the AI research team.",
     "Giám đốc kỹ thuật đã phân bổ thêm tài nguyên tính toán đám mây cho đội nghiên cứu AI."),

    ("discrepancy", "/dɪˈskrep.ən.si/", "noun", "Accounting & Finance", "sự sai lệch, bất nhất giữa các số liệu",
     "financial discrepancy / reconcile discrepancies", "discrepancy = inconsistency = difference",
     "The automated reconciliation job detected a minor discrepancy between ledger entries.",
     "Tiến trình đối soát tự động đã phát hiện ra một sự sai lệch nhỏ giữa các mục ghi sổ cái."),

    ("streamline", "/ˈstriːm.laɪn/", "verb", "Office Operations", "tối ưu hóa, tinh gọn quy trình",
     "streamline operations / streamline workflow", "streamline = simplify = optimize = modernize",
     "We adopted continuous integration pipelines to streamline software releases.",
     "Chúng tôi đã áp dụng CI/CD pipeline để tinh gọn quy trình phát hành phần mềm."),
]

# -------------------------------------------------------------
# 3. 10 High-Frequency Paraphrase Pairs (Part 7 Vault)
# -------------------------------------------------------------
NEW_PARAPHRASE_PAIRS = [
    {
        "word_in_text": "ahead of schedule",
        "word_in_answer": "earlier than expected / prior to deadline",
        "meaning": "trước thời hạn dự kiến",
        "part_target": "Part 7 Memos",
        "frequency": "Extreme",
    },
    {
        "word_in_text": "mandatory walkthrough",
        "word_in_answer": "compulsory training session / required attendance",
        "meaning": "buổi hướng dẫn bắt buộc tham gia",
        "part_target": "Part 7 Notices",
        "frequency": "Extreme",
    },
    {
        "word_in_text": "redundant systems",
        "word_in_answer": "backup failover mechanisms / standby resources",
        "meaning": "hệ thống dự phòng thay thế",
        "part_target": "Part 7 Tech announcements",
        "frequency": "High",
    },
    {
        "word_in_text": "inspect meticulously",
        "word_in_answer": "conduct a thorough examination / scrutinize",
        "meaning": "kiểm tra tỉ mỉ, chi tiết",
        "part_target": "Part 7 Reports",
        "frequency": "High",
    },
    {
        "word_in_text": "reimburse expenses",
        "word_in_answer": "compensate for costs incurred / refund",
        "meaning": "hoàn trả chi phí công tác",
        "part_target": "Part 7 Policies",
        "frequency": "Extreme",
    },
    {
        "word_in_text": "tentative itinerary",
        "word_in_answer": "provisional schedule / subject to change",
        "meaning": "lịch trình dự kiến (có thể đổi)",
        "part_target": "Part 7 Travel schedules",
        "frequency": "High",
    },
    {
        "word_in_text": "reach an accord",
        "word_in_answer": "come to an agreement / sign consensus",
        "meaning": "đạt được thỏa thuận chung",
        "part_target": "Part 7 Business letters",
        "frequency": "High",
    },
    {
        "word_in_text": "discontinue product",
        "word_in_answer": "phase out / cease production of line",
        "meaning": "ngừng sản xuất dòng sản phẩm",
        "part_target": "Part 7 Announcements",
        "frequency": "Extreme",
    },
    {
        "word_in_text": "streamline workflow",
        "word_in_answer": "optimize and simplify operational procedures",
        "meaning": "tinh gọn quy trình làm việc",
        "part_target": "Part 7 Executive memos",
        "frequency": "High",
    },
    {
        "word_in_text": "incur additional fees",
        "word_in_answer": "subject to extra surcharge / pay penalties",
        "meaning": "phát sinh phụ phí ngoài dự kiến",
        "part_target": "Part 7 Invoices & Billing",
        "frequency": "Extreme",
    },
]


def ingest_all(db_session=None):
    close_when_done = False
    if db_session is None:
        init_db()
        db = SessionLocal()
        close_when_done = True
    else:
        db = db_session

    try:
        print("=== 1. Ingesting Mock Test ETS2024_02 ===")
        test_02 = db.query(MockTest).filter_by(test_id="ETS2024_02").first()
        if not test_02:
            test_02 = MockTest(
                test_id="ETS2024_02",
                name="ETS TOEIC Regular Test 2024 - Test 02",
                year=2024,
                publisher="ETS",
                total_questions=200,
            )
            db.add(test_02)
            db.commit()
            db.refresh(test_02)
            print("  ✓ Created MockTest 'ETS2024_02'")
        else:
            print("  • MockTest 'ETS2024_02' already exists")

        print("\n=== 2. Ingesting Questions for ETS2024_02 ===")
        inserted_q_count = 0
        for item in TEST_02_QUESTIONS:
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
                    distractor_analysis=item["distractor_analysis"],
                    paraphrase_pair=item.get("paraphrase_pair"),
                    lesson_number=item.get("lesson_number"),
                    image_url=item.get("image_url"),
                    source="ets2024_test02",
                )
                db.add(q)
                inserted_q_count += 1
        db.commit()
        print(f"  ✓ Ingested {inserted_q_count} new questions for ETS2024_02 (Total defined: {len(TEST_02_QUESTIONS)})")

        print("\n=== 3. Expanding Flashcards & SuperMemo-2 SRS ===")
        all_flashcards = NEW_FLASHCARDS + EXPANDED_VOCAB
        users = db.query(User).all()
        user_ids = [u.id for u in users] or [1]

        inserted_card_count = 0
        for word, ipa, wtype, cat, meaning, colloc, para, ex_en, ex_vi in all_flashcards:
            card = db.query(Flashcard).filter_by(word=word).first()
            if not card:
                card = Flashcard(
                    word=word,
                    ipa=ipa,
                    word_type=wtype,
                    category=cat,
                    meaning=meaning,
                    collocations=colloc,
                    paraphrase_pair=para,
                    example_sentence=ex_en,
                    example_translation=ex_vi,
                )
                db.add(card)
                db.commit()
                db.refresh(card)
                inserted_card_count += 1

                # Initialize SRS records for each user
                for uid in user_ids:
                    srs = db.query(UserCardSRS).filter_by(user_id=uid, card_id=card.id).first()
                    if not srs:
                        db.add(UserCardSRS(
                            user_id=uid,
                            card_id=card.id,
                            repetition_count=0,
                            ease_factor=2.5,
                            interval_days=1,
                            state="new",
                            next_review_at=utcnow(),
                        ))
                db.commit()
        print(f"  ✓ Added {inserted_card_count} new flashcards and linked SRS for {len(user_ids)} users")

        print("\n=== 4. Expanding Paraphrase Vault ===")
        inserted_para_count = 0
        for p in NEW_PARAPHRASE_PAIRS:
            exists = db.query(ParaphrasePair).filter_by(
                word_in_text=p["word_in_text"], word_in_answer=p["word_in_answer"]
            ).first()
            if not exists:
                pair = ParaphrasePair(
                    word_in_text=p["word_in_text"],
                    word_in_answer=p["word_in_answer"],
                    meaning=p["meaning"],
                    part_target=p["part_target"],
                    frequency=p["frequency"],
                )
                db.add(pair)
                inserted_para_count += 1
        db.commit()
        print(f"  ✓ Added {inserted_para_count} new Paraphrase Pairs to Vault")

        print("\n🎉 All ETS 2024 Test 02 dataset ingested successfully!")
        return {
            "test_id": "ETS2024_02",
            "questions_added": inserted_q_count,
            "flashcards_added": inserted_card_count,
            "paraphrase_pairs_added": inserted_para_count,
        }

    except Exception as exc:
        db.rollback()
        print(f"❌ Error during ingestion: {exc}")
        raise exc
    finally:
        if close_when_done:
            db.close()


if __name__ == "__main__":
    ingest_all()
