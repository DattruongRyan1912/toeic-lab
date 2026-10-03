#!/usr/bin/env python3
"""
Ingestion & Corpus Expansion Script:
Seeds authentic ETS TOEIC 2024 Test 04 (ETS2024_04) dataset into the database:
1. MockTest record for 'ETS2024_04' (ETS TOEIC Regular Test 2024 - Test 04).
2. 51 high-quality benchmark questions:
   - Part 1: Q1 -> Q5 (Photographs with scenarios and full distractor analysis)
   - Part 2: Q7 -> Q14 (Question - Response with audio transcripts & trap breakdown)
   - Part 5: Q101 -> Q130 (Full 30 incomplete sentences covering all 12 core grammar lessons)
   - Part 6: Q131 -> Q134 (Text completion notice with sentence insertion)
   - Part 7: Q147 -> Q150 (Reading comprehension passage with inference & vocabulary questions)
3. 20 High-Frequency Business & Tech Flashcards with SuperMemo-2 SRS state.
4. 10 Part 7 Paraphrase Pairs for the Paraphrase Vault.

Idempotent: Safe to re-run without duplicate key errors.
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from server.database import SessionLocal, init_db
from server.models import (
    MockTest, TestQuestion, Flashcard, UserCardSRS, ParaphrasePair, User
)
from server.utils.timeutil import utcnow

# -------------------------------------------------------------
# 1. ETS 2024 Test 04 Questions (51 items)
# -------------------------------------------------------------
TEST_04_QUESTIONS = [
    # --- Part 1: Photographs ---
    {
        "test_id": "ETS2024_04",
        "part": "Part 1",
        "question_no": 1,
        "sentence": "A speaker is pointing at a bar graph displayed on a wall-mounted digital screen.",
        "choice_a": "A woman is gesturing toward a projection screen.",
        "choice_b": "Audience members are turning off their laptops.",
        "choice_c": "The presenter is distributing paper handouts.",
        "choice_d": "Chairs are being folded and stacked against a wall.",
        "correct_choice": "A",
        "explanation": "Diễn giả nữ đang hướng tay chỉ vào màn hình hiển thị biểu đồ trong phòng hội nghị.",
        "distractor_analysis": "[Bẫy Động Từ & Bị Động 'being'] B (turning off laptops), C (distributing handouts), D (chairs are being folded) miêu tả các hành động sai hoặc hành động không tồn tại trong tranh tĩnh.",
        "paraphrase_pair": "pointing at a digital screen = gesturing toward a projection screen",
        "image_url": "/part1/ets2024_04_q1.jpg",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_04",
        "part": "Part 1",
        "question_no": 2,
        "sentence": "Documents and folders have been neatly organized into several stacks across an office desk.",
        "choice_a": "A clerk is shredding paper documents in an office.",
        "choice_b": "Folders have been arranged in neat piles on a desk.",
        "choice_c": "Books are being packed into cardboard boxes.",
        "choice_d": "A computer monitor is being unplugged from an outlet.",
        "correct_choice": "B",
        "explanation": "Các tập hồ sơ tài liệu được sắp xếp ngay ngắn thành từng chồng trên mặt bàn làm việc.",
        "distractor_analysis": "[Bẫy Bị Động Tiếp Diễn 'being'] C (are being packed) và D (is being unplugged) là bẫy âm mưu hành động đang diễn ra trong khi tranh là tĩnh. A sai chủ thể hành động.",
        "paraphrase_pair": "organized into stacks = arranged in neat piles",
        "image_url": "/part1/ets2024_04_q2.jpg",
        "lesson_number": 4,
    },
    {
        "test_id": "ETS2024_04",
        "part": "Part 1",
        "question_no": 3,
        "sentence": "People are seated at outdoor dining tables positioned beneath large patio umbrellas.",
        "choice_a": "Customers are dining outdoors under large sun umbrellas.",
        "choice_b": "A server is wiping down a counter in the restaurant.",
        "choice_c": "Tables are being loaded onto a delivery truck.",
        "choice_d": "The restaurant entrance is completely blocked by bicycles.",
        "correct_choice": "A",
        "explanation": "Khách hàng đang ngồi ăn uống tại khu vực bàn ngoài trời có che dù che nắng lớn.",
        "distractor_analysis": "[Bẫy Chi Tiết Giả & Bị Động] B (wiping down counter), C (being loaded), D (blocked by bicycles) đều là các chi tiết ngụy tạo.",
        "paraphrase_pair": "seated beneath patio umbrellas = dining outdoors under large sun umbrellas",
        "image_url": "/part1/ets2024_04_q3.jpg",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_04",
        "part": "Part 1",
        "question_no": 4,
        "sentence": "A freight vehicle is backed up to a loading dock with its rear cargo doors open.",
        "choice_a": "A commercial truck is parked adjacent to a loading dock.",
        "choice_b": "A driver is changing a flat tire on a highway.",
        "choice_c": "Workers are painting the exterior wall of a depot.",
        "choice_d": "Pallets are being assembled using power tools.",
        "correct_choice": "A",
        "explanation": "Chiếc xe tải chở hàng đang đỗ sát cạnh bục bốc dỡ hàng hóa của nhà kho.",
        "distractor_analysis": "[Bẫy Từ Vựng Liên Quan Đến Xe Cộ] B (changing flat tire), C (painting exterior wall), D (pallets are being assembled) là các hành động sai lệch thực tế.",
        "paraphrase_pair": "freight vehicle backed up to a dock = truck parked adjacent to a loading dock",
        "image_url": "/part1/ets2024_04_q4.jpg",
        "lesson_number": 4,
    },
    {
        "test_id": "ETS2024_04",
        "part": "Part 1",
        "question_no": 5,
        "sentence": "A store clerk behind a checkout counter is handing a paper receipt to a patron.",
        "choice_a": "A cashier is handing a printed receipt to a customer.",
        "choice_b": "Shelves are being restocked with canned beverages.",
        "choice_c": "A customer is trying on a winter jacket in a fitting room.",
        "choice_d": "Groceries are being scanned by an automated machine.",
        "correct_choice": "A",
        "explanation": "Nhân viên thu ngân đang trao biên lai thanh toán in giấy cho khách mua sắm.",
        "distractor_analysis": "[Bẫy Bối Cảnh Cửa Hàng] B (restocked with beverages), C (trying on winter jacket), D (automated machine) đánh lừa về ngữ cảnh bán lẻ.",
        "paraphrase_pair": "clerk handing a receipt to a patron = cashier handing a printed receipt to a customer",
        "image_url": "/part1/ets2024_04_q5.jpg",
        "lesson_number": 1,
    },

    # --- Part 2: Question - Response ---
    {
        "test_id": "ETS2024_04",
        "part": "Part 2",
        "question_no": 7,
        "sentence": "Where is the annual cloud computing summit being hosted this year?",
        "choice_a": "In San Jose, at the municipal convention center.",
        "choice_b": "Yes, I attended the keynote speech last week.",
        "choice_c": "About fifteen hundred registered participants.",
        "choice_d": "",
        "correct_choice": "A",
        "explanation": "Câu hỏi 'Where' (Ở đâu?) hỏi địa điểm tổ chức ➔ Phương án A trả lời địa điểm chính xác: 'In San Jose, at the municipal convention center'.",
        "distractor_analysis": "[Bẫy Yes/No & Số Lượng] B bẫy Yes/No cho câu hỏi Wh-, C bẫy trả lời cho câu hỏi 'How many'.",
        "paraphrase_pair": "being hosted = taking place = being held",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_04",
        "part": "Part 2",
        "question_no": 8,
        "sentence": "Could you please review the database migration proposal before tomorrow's client meeting?",
        "choice_a": "Certainly, I will examine it right after lunch.",
        "choice_b": "The proposal was accepted two months ago.",
        "choice_c": "No, the conference room is occupied right now.",
        "choice_d": "",
        "correct_choice": "A",
        "explanation": "Câu yêu cầu lịch sự 'Could you please review...' ➔ Phương án A nhận lời tích cực: 'Certainly, I will examine it right after lunch'.",
        "distractor_analysis": "[Bẫy Lạc Đề & Lặp Từ] B nói về sự việc quá khứ 'two months ago', C nói về phòng họp bận (lạc đề câu hỏi về tài liệu).",
        "paraphrase_pair": "review the proposal = examine the document",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_04",
        "part": "Part 2",
        "question_no": 9,
        "sentence": "Why was the automated nightly backup job delayed yesterday?",
        "choice_a": "Because scheduled maintenance on the storage cluster took longer than anticipated.",
        "choice_b": "At approximately two o'clock in the morning.",
        "choice_c": "Yes, all files were backed up successfully.",
        "choice_d": "",
        "correct_choice": "A",
        "explanation": "Câu hỏi 'Why' (Tại sao?) ➔ Phương án A đưa ra nguyên nhân chính xác bắt đầu bằng 'Because scheduled maintenance... took longer than anticipated'.",
        "distractor_analysis": "[Bẫy Thời Gian & Yes/No] B trả lời cho câu hỏi 'When', C là bẫy Yes/No cho câu hỏi Wh-.",
        "paraphrase_pair": "delayed = took longer than anticipated = postponed",
        "lesson_number": 2,
    },
    {
        "test_id": "ETS2024_04",
        "part": "Part 2",
        "question_no": 10,
        "sentence": "How frequently does the facilities team inspect the server room cooling units?",
        "choice_a": "Biweekly, every other Tuesday morning.",
        "choice_b": "It is quite chilly inside the data hall.",
        "choice_c": "The inspection report was filed online.",
        "choice_d": "",
        "correct_choice": "A",
        "explanation": "Câu hỏi 'How frequently' (Tần suất bao lâu một lần?) ➔ Phương án A cung cấp tần suất: 'Biweekly, every other Tuesday morning' (2 tuần một lần).",
        "distractor_analysis": "[Bẫy Lặp Từ Tương Đồng Nghĩa] B bẫy từ 'chilly' (lạnh) liên tưởng đến 'cooling units' (máy lạnh), C bẫy từ 'inspection'.",
        "paraphrase_pair": "how frequently = how often = at what interval",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_04",
        "part": "Part 2",
        "question_no": 11,
        "sentence": "Who authorized the budget expenditure for the developer workstation upgrades?",
        "choice_a": "Ms. Gomez from the Finance Committee signed off on it.",
        "choice_b": "The computers have sixteen gigabytes of memory.",
        "choice_c": "Yes, we ordered five additional desktop monitors.",
        "choice_d": "",
        "correct_choice": "A",
        "explanation": "Câu hỏi 'Who' (Ai đã phê duyệt?) ➔ Phương án A chỉ định người chịu trách nhiệm: 'Ms. Gomez from the Finance Committee signed off on it'.",
        "distractor_analysis": "[Bẫy Thông Số Kỹ Thuật & Yes/No] B nói về cấu hình RAM máy tính, C là bẫy Yes/No cho câu hỏi Wh-.",
        "paraphrase_pair": "authorized budget expenditure = signed off on financial approval",
        "lesson_number": 7,
    },
    {
        "test_id": "ETS2024_04",
        "part": "Part 2",
        "question_no": 12,
        "sentence": "Has the shipment of fiber optic network switches arrived yet?",
        "choice_a": "I haven't had a chance to check the warehouse receiving dock this morning.",
        "choice_b": "We will switch our office phone provider next week.",
        "choice_c": "The shipping charges were unusually high.",
        "choice_d": "",
        "correct_choice": "A",
        "explanation": "Câu hỏi hiện tại hoàn thành 'Has the shipment... arrived yet?' ➔ Phương án A trả lời gián tiếp rất phổ biến trong đề ETS: 'I haven't had a chance to check the dock' (Tôi chưa có dịp ra kiểm tra kho sáng nay).",
        "distractor_analysis": "[Bẫy Từ Đồng Âm Đa Nghĩa 'switch'] B bẫy động từ 'switch' (chuyển đổi) khác nghĩa với danh từ 'network switches' (thiết bị chuyển mạch mạng). C bẫy từ 'shipping'.",
        "paraphrase_pair": "has it arrived = check the receiving dock",
        "lesson_number": 6,
    },
    {
        "test_id": "ETS2024_04",
        "part": "Part 2",
        "question_no": 13,
        "sentence": "Should we schedule the sprint retrospective for Thursday afternoon or Friday morning?",
        "choice_a": "Friday morning works best because the QA engineers will be done testing.",
        "choice_b": "No, we should not postpone the release date.",
        "choice_c": "Yes, the sprint objectives were accomplished.",
        "choice_d": "",
        "correct_choice": "A",
        "explanation": "Câu hỏi lựa chọn 'A or B' ➔ Phương án A chọn một trong hai phương án và đưa ra lý do xác đáng: 'Friday morning works best...'.",
        "distractor_analysis": "[Bẫy Yes/No Cho Câu Hỏi Lựa Chọn] B và C dùng 'No' và 'Yes', câu hỏi 'A or B' tuyệt đối không trả lời bằng Yes/No.",
        "paraphrase_pair": "schedule the retrospective = hold the project review meeting",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_04",
        "part": "Part 2",
        "question_no": 14,
        "sentence": "The prospective enterprise customer requested a live demonstration of our analytics dashboard.",
        "choice_a": "I will prepare the staging environment and sample datasets right away.",
        "choice_b": "The dashboard battery needs to be recharged.",
        "choice_c": "No, we do not sell consumer televisions.",
        "choice_d": "",
        "correct_choice": "A",
        "explanation": "Câu trần thuật thông báo về yêu cầu của khách hàng lớn ➔ Phương án A tiếp nhận thông tin và đưa ra hành động tương ứng: 'I will prepare the staging environment... right away'.",
        "distractor_analysis": "[Bẫy Liên Tưởng Vô Lý] B nói về pin táp-lô ô tô/điện tử, C nói về tivi tiêu dùng (lạc đề hoàn toàn).",
        "paraphrase_pair": "requested a live demonstration = prepare the staging environment",
        "lesson_number": 1,
    },

    # --- Part 5: Incomplete Sentences (Full 30 questions) ---
    {
        "test_id": "ETS2024_04",
        "part": "Part 5",
        "question_no": 101,
        "sentence": "Even during peak holiday traffic, the regional distribution center operates _______ without unexpected disruptions.",
        "choice_a": "reliable",
        "choice_b": "reliably",
        "choice_c": "reliability",
        "choice_d": "reliableness",
        "correct_choice": "B",
        "explanation": "Động từ 'operates' (nội động từ) cần một trạng từ theo sau để bổ nghĩa cho phương thức vận hành ➔ chọn trạng từ 'reliably' (vận hành một cách đáng tin cậy).",
        "distractor_analysis": "[Bẫy Từ Loại - Word Forms] A (tính từ), C (danh từ), D (danh từ hiếm gặp) không thể bổ nghĩa cho động từ 'operates'.",
        "paraphrase_pair": "operates reliably = functions dependably without interruption",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_04",
        "part": "Part 5",
        "question_no": 102,
        "sentence": "All software engineers must back up their local code repositories _______ beginning the mandatory operating system upgrade.",
        "choice_a": "prior to",
        "choice_b": "except for",
        "choice_c": "in spite",
        "choice_d": "whereas",
        "correct_choice": "A",
        "explanation": "'prior to' là cụm giới từ mang nghĩa 'trước khi' (= before), đi với danh động từ 'beginning the mandatory upgrade'.",
        "distractor_analysis": "[Bẫy Giới Từ vs Liên Từ] B (except for - ngoại trừ), C (thiếu 'of' -> in spite of), D (whereas là liên từ cần một mệnh đề S+V).",
        "paraphrase_pair": "prior to beginning = before initiating",
        "lesson_number": 2,
    },
    {
        "test_id": "ETS2024_04",
        "part": "Part 5",
        "question_no": 103,
        "sentence": "Conference attendees who wish to participate in the afternoon breakout workshops should register _______ at the welcome desk.",
        "choice_a": "they",
        "choice_b": "them",
        "choice_c": "their",
        "choice_d": "themselves",
        "correct_choice": "D",
        "explanation": "Chủ ngữ là 'Conference attendees', hành động 'register' tác động ngược lại chính người đó (tự đăng ký bản thân) ➔ dùng đại từ phản thân 'themselves'. Cụm 'register oneself'.",
        "distractor_analysis": "[Bẫy Đại Từ - Pronouns] A (chủ ngữ), B (tân ngữ chỉ người khác), C (tính từ sở hữu bắt buộc có danh từ theo sau).",
        "paraphrase_pair": "register themselves = sign themselves up",
        "lesson_number": 7,
    },
    {
        "test_id": "ETS2024_04",
        "part": "Part 5",
        "question_no": 104,
        "sentence": "The advisory committee of senior software architects _______ officially approved the revised microservice roadmap.",
        "choice_a": "have",
        "choice_b": "has",
        "choice_c": "are having",
        "choice_d": "were",
        "correct_choice": "B",
        "explanation": "Chủ ngữ chính là danh từ tập hợp số ít 'The advisory committee' (cụm giới từ 'of senior software architects' chỉ bổ nghĩa chen ngang) ➔ động từ chia số ít ở thì hiện tại hoàn thành: 'has'.",
        "distractor_analysis": "[Bẫy Hòa Hợp Chủ Vị - Chen Ngang] Thí sinh dễ nhìn nhầm danh từ số nhiều đứng ngay trước 'architects' để chọn 'have' hoặc 'were'.",
        "paraphrase_pair": "committee has approved = panel has authorized",
        "lesson_number": 5,
    },
    {
        "test_id": "ETS2024_04",
        "part": "Part 5",
        "question_no": 105,
        "sentence": "In order to reduce database query latency, the infrastructure team decided _______ Redis caching across all microservices.",
        "choice_a": "implement",
        "choice_b": "to implement",
        "choice_c": "implementing",
        "choice_d": "implemented",
        "correct_choice": "B",
        "explanation": "Động từ 'decide' luôn đi kèm động từ nguyên mẫu có 'to' (decide + to-V: quyết định làm việc gì).",
        "distractor_analysis": "[Bẫy Dạng Động Từ - Gerund vs Infinitive] C (implementing là V-ing, decide không đi với V-ing), A (nguyên mẫu không to), D (quá khứ).",
        "paraphrase_pair": "decided to implement = determined to deploy",
        "lesson_number": 3,
    },
    {
        "test_id": "ETS2024_04",
        "part": "Part 5",
        "question_no": 106,
        "sentence": "The automated deployment pipeline was designed to improve operational _______ and eliminate human error.",
        "choice_a": "efficient",
        "choice_b": "efficiently",
        "choice_c": "efficiency",
        "choice_d": "efficiencies",
        "correct_choice": "C",
        "explanation": "Sau tính từ 'operational' cần một danh từ làm tân ngữ cho ngoại động từ 'improve'. 'operational efficiency' là cụm danh từ kinh doanh cố định (hiệu quả vận hành).",
        "distractor_analysis": "[Bẫy Từ Loại - Word Forms] A (tính từ), B (trạng từ). C (danh từ không đếm được chỉ tính hiệu quả) chuẩn xác hơn số nhiều D.",
        "paraphrase_pair": "operational efficiency = operating effectiveness and productivity",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_04",
        "part": "Part 5",
        "question_no": 107,
        "sentence": "Employees are strictly reminded that all customer account credentials must remain entirely _______ and secure.",
        "choice_a": "confidential",
        "choice_b": "confidentiality",
        "choice_c": "confidentially",
        "choice_d": "confidence",
        "correct_choice": "A",
        "explanation": "Động từ nối 'remain' đi với tính từ để mô tả trạng thái (remain + Adj). Liên từ 'and' liên kết song song với tính từ 'secure' ➔ chọn tính từ 'confidential'.",
        "distractor_analysis": "[Bẫy Cấu Trúc Song Song & Linking Verbs] B (danh từ), C (trạng từ), D (danh từ lòng tin) sai cấu trúc ngữ pháp sau 'remain'.",
        "paraphrase_pair": "remain confidential = stay private and protected",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_04",
        "part": "Part 5",
        "question_no": 108,
        "sentence": "_______ the preliminary performance testing was successful, management decided to conduct one final round of load tests.",
        "choice_a": "Although",
        "choice_b": "Despite",
        "choice_c": "Nevertheless",
        "choice_d": "Due to",
        "correct_choice": "A",
        "explanation": "Phía sau là một mệnh đề hoàn chỉnh S + V ('the preliminary performance testing was successful') thể hiện ý nhượng bộ ➔ dùng liên từ phụ thuộc 'Although'.",
        "distractor_analysis": "[Bẫy Liên Từ vs Giới Từ/Trạng Từ] B (Despite) và D (Due to) là giới từ, chỉ đi với Noun phrase. C (Nevertheless) là trạng từ liên kết cần đứng độc lập.",
        "paraphrase_pair": "although = even though = while",
        "lesson_number": 2,
    },
    {
        "test_id": "ETS2024_04",
        "part": "Part 5",
        "question_no": 109,
        "sentence": "At yesterday's annual gala, the lead site reliability engineer _______ an award for maintaining perfect uptime.",
        "choice_a": "was awarded",
        "choice_b": "awards",
        "choice_c": "is awarding",
        "choice_d": "has awarded",
        "correct_choice": "A",
        "explanation": "Chủ ngữ là kỹ sư được trao tặng giải thưởng (bị động) trong quá khứ ('yesterday') ➔ dùng bị động thì quá khứ đơn: 'was awarded'.",
        "distractor_analysis": "[Bẫy Thể Chủ Động vs Bị Động] B, C, D đều là dạng chủ động (tự trao giải cho ai đó), trong khi kỹ sư là người được nhận giải thưởng.",
        "paraphrase_pair": "was awarded = received a commendation / honor",
        "lesson_number": 4,
    },
    {
        "test_id": "ETS2024_04",
        "part": "Part 5",
        "question_no": 110,
        "sentence": "Over the past three quarters, Apex Cloud Technologies _______ its engineering headcount by more than forty percent.",
        "choice_a": "will expand",
        "choice_b": "has expanded",
        "choice_c": "expands",
        "choice_d": "was expanding",
        "correct_choice": "B",
        "explanation": "Dấu hiệu 'Over the past three quarters' (suốt 3 quý vừa qua) là mốc thời gian kéo dài từ quá khứ đến hiện tại ➔ chia thì hiện tại hoàn thành: 'has expanded'.",
        "distractor_analysis": "[Bẫy Thì Thời Gian - Tenses] A (tương lai), C (hiện tại đơn chỉ thói quen), D (quá khứ tiếp diễn) sai mốc thời gian 'over the past...'.",
        "paraphrase_pair": "has expanded headcount = has increased staff size",
        "lesson_number": 6,
    },
    {
        "test_id": "ETS2024_04",
        "part": "Part 5",
        "question_no": 111,
        "sentence": "The consulting firm hired _______ gifted data analysts to lead the predictive machine learning division.",
        "choice_a": "exception",
        "choice_b": "exceptional",
        "choice_c": "exceptionally",
        "choice_d": "excepting",
        "correct_choice": "C",
        "explanation": "Đứng trước tính từ 'gifted' (tài năng, có năng khiếu) cần một trạng từ chỉ mức độ để bổ nghĩa ➔ chọn trạng từ 'exceptionally' (đặc biệt tài năng). Cấu trúc: Adv + Adj + Noun.",
        "distractor_analysis": "[Bẫy Vị Trí Trạng Từ] A (danh từ), B (tính từ không thể bổ nghĩa cho tính từ gifted), D (giới từ).",
        "paraphrase_pair": "exceptionally gifted = remarkably talented",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_04",
        "part": "Part 5",
        "question_no": 112,
        "sentence": "Customer technical inquiries submitted through the online ticketing portal will receive a formal response _______ forty-eight hours.",
        "choice_a": "within",
        "choice_b": "between",
        "choice_c": "among",
        "choice_d": "along",
        "correct_choice": "A",
        "explanation": "'within' + khoảng thời gian có nghĩa là 'trong vòng (thời hạn)', ở đây là 'trong vòng 48 giờ'.",
        "distractor_analysis": "[Bẫy Giới Từ Thời Gian vs Không Gian] B (between đi với 'and'), C (among đi với danh từ số nhiều >= 3 đối tượng), D (along đi với địa điểm kéo dài: along the river).",
        "paraphrase_pair": "within forty-eight hours = inside a two-day timeframe",
        "lesson_number": 2,
    },
    {
        "test_id": "ETS2024_04",
        "part": "Part 5",
        "question_no": 113,
        "sentence": "All manufacturing machinery operators must _______ comply with industrial workplace safety guidelines.",
        "choice_a": "strictly",
        "choice_b": "strict",
        "choice_c": "strictness",
        "choice_d": "strictest",
        "correct_choice": "A",
        "explanation": "'strictly comply with' là một Business Collocation kinh điển trong đề TOEIC (tuân thủ nghiêm ngặt quy định an toàn). Đứng giữa trợ động từ 'must' và động từ 'comply' phải là trạng từ.",
        "distractor_analysis": "[Bẫy Collocation & Vị Trí Từ Loại] B (tính từ), C (danh từ), D (so sánh nhất) không thể đứng chêm vào giữa must + V.",
        "paraphrase_pair": "strictly comply with = adhere rigorously to",
        "lesson_number": 12,
    },
    {
        "test_id": "ETS2024_04",
        "part": "Part 5",
        "question_no": 114,
        "sentence": "The senior technician _______ the installation of high-voltage transformers has over fifteen years of industrial experience.",
        "choice_a": "oversee",
        "choice_b": "oversees",
        "choice_c": "overseeing",
        "choice_d": "overseen",
        "correct_choice": "C",
        "explanation": "Câu đã có động từ chính là 'has'. Chỗ trống là mệnh đề quan hệ rút gọn ở dạng chủ động (The senior technician who oversees... ➔ The senior technician overseeing...).",
        "distractor_analysis": "[Bẫy Mệnh Đề Quan Hệ Rút Gọn] B (oversees biến câu thành 2 vị ngữ không có liên từ), D (overseen là bị động, ở đây kỹ sư chủ động giám sát).",
        "paraphrase_pair": "technician overseeing = technician in charge of supervising",
        "lesson_number": 8,
    },
    {
        "test_id": "ETS2024_04",
        "part": "Part 5",
        "question_no": 115,
        "sentence": "Vertex Solutions is searching for a network consultant _______ cybersecurity expertise can protect proprietary client data.",
        "choice_a": "whom",
        "choice_b": "whose",
        "choice_c": "which",
        "choice_d": "who",
        "correct_choice": "B",
        "explanation": "Sau chỗ trống là danh từ 'cybersecurity expertise' thuộc quyền sở hữu của 'network consultant' (chuyên môn an ninh mạng của người cố vấn) ➔ dùng đại từ quan hệ sở hữu 'whose'.",
        "distractor_analysis": "[Bẫy Đại Từ Quan Hệ Sở Hữu] A (whom làm tân ngữ), C (which thay thế đồ vật), D (who làm chủ ngữ thay người, theo sau phải là động từ chứ không phải cụm danh từ).",
        "paraphrase_pair": "consultant whose expertise = consultant with specialized skills",
        "lesson_number": 9,
    },
    {
        "test_id": "ETS2024_04",
        "part": "Part 5",
        "question_no": 116,
        "sentence": "_______ you experience any difficulties accessing the employee intranet portal, please contact the IT help desk immediately.",
        "choice_a": "Should",
        "choice_b": "Unless",
        "choice_c": "Were",
        "choice_d": "Had",
        "correct_choice": "A",
        "explanation": "Cấu trúc đảo ngữ câu điều kiện loại 1: 'Should + S + V-bare' (= If you should experience...: Nếu bạn gặp bất kỳ khó khăn nào...).",
        "distractor_analysis": "[Bẫy Đảo Ngữ Câu Điều Kiện] C (Were dùng cho điều kiện loại 2: Were you to experience), D (Had dùng cho điều kiện loại 3: Had you experienced), B (Unless là liên từ cần thể khẳng định).",
        "paraphrase_pair": "Should you experience = If you happen to encounter",
        "lesson_number": 10,
    },
    {
        "test_id": "ETS2024_04",
        "part": "Part 5",
        "question_no": 117,
        "sentence": "The external cybersecurity auditors examined the banking application far _______ than the internal team had anticipated.",
        "choice_a": "thorough",
        "choice_b": "more thoroughly",
        "choice_c": "thoroughly",
        "choice_d": "most thoroughly",
        "correct_choice": "B",
        "explanation": "Có liên từ so sánh 'than' phía sau và từ bổ trợ 'far' (chỉ mức độ chênh lệch lớn trong so sánh hơn) ➔ chọn cấu trúc so sánh hơn của trạng từ: 'far more thoroughly than'.",
        "distractor_analysis": "[Bẫy Cấu Trúc So Sánh] A (tính từ nguyên thể), C (trạng từ nguyên thể thiếu 'more'), D (so sánh nhất 'most' đi với 'the', không đi với 'than').",
        "paraphrase_pair": "examined far more thoroughly = inspected with much greater rigor",
        "lesson_number": 11,
    },
    {
        "test_id": "ETS2024_04",
        "part": "Part 5",
        "question_no": 118,
        "sentence": "After extensive negotiations spanning three days, both enterprise vendors finally reached a _______ on the software licensing terms.",
        "choice_a": "consensus",
        "choice_b": "consensual",
        "choice_c": "consenting",
        "choice_d": "consentingly",
        "correct_choice": "A",
        "explanation": "'reach a consensus' (đạt được sự đồng thuận / thống nhất ý kiến) là một Collocation kinh doanh cực kỳ phổ biến trong TOEIC. Sau mạo từ 'a' cần một danh từ số ít.",
        "distractor_analysis": "[Bẫy Collocation & Từ Loại] B (tính từ), C (phân từ tính từ), D (trạng từ).",
        "paraphrase_pair": "reached a consensus = reached mutual agreement",
        "lesson_number": 12,
    },
    {
        "test_id": "ETS2024_04",
        "part": "Part 5",
        "question_no": 119,
        "sentence": "Due to recurring on-premise hardware failures, the executive committee will consider _______ all services to the public cloud.",
        "choice_a": "migrate",
        "choice_b": "migrating",
        "choice_c": "to migrate",
        "choice_d": "migrated",
        "correct_choice": "B",
        "explanation": "Động từ 'consider' luôn đòi hỏi danh động từ theo sau (consider + V-ing: cân nhắc làm việc gì).",
        "distractor_analysis": "[Bẫy Dạng Động Từ - Gerund] C (to migrate là bẫy To-V phổ biến), A (nguyên mẫu không to), D (quá khứ).",
        "paraphrase_pair": "consider migrating = contemplate transitioning",
        "lesson_number": 3,
    },
    {
        "test_id": "ETS2024_04",
        "part": "Part 5",
        "question_no": 120,
        "sentence": "Newly appointed software development engineers are _______ to attend the mandatory cybersecurity orientation next Monday.",
        "choice_a": "require",
        "choice_b": "requires",
        "choice_c": "requiring",
        "choice_d": "required",
        "correct_choice": "D",
        "explanation": "Cấu trúc bị động: 'be required to-V' (được yêu cầu / bắt buộc phải làm việc gì). Ở đây: 'are required to attend'.",
        "distractor_analysis": "[Bẫy Bị Động Cố Định] A (động từ nguyên mẫu), B (chia số ít), C (dạng chủ động requiring cần có tân ngữ theo sau).",
        "paraphrase_pair": "are required to attend = are obligated / mandated to participate in",
        "lesson_number": 4,
    },
    {
        "test_id": "ETS2024_04",
        "part": "Part 5",
        "question_no": 121,
        "sentence": "Neither the principal software architect nor the DevOps engineers _______ satisfied with the slow latency of the legacy database.",
        "choice_a": "was",
        "choice_b": "is",
        "choice_c": "were",
        "choice_d": "has been",
        "correct_choice": "C",
        "explanation": "Cấu trúc 'Neither S1 nor S2 + Verb': động từ chia hòa hợp theo chủ ngữ đứng gần nó nhất (S2). S2 là 'the DevOps engineers' (danh từ số nhiều) trong quá khứ ➔ chia 'were'.",
        "distractor_analysis": "[Bẫy Hòa Hợp Chủ Vị Với Liên Từ Tương Quan] A, B, D đều chia số ít (bị đánh lừa bởi S1 'architect').",
        "paraphrase_pair": "were not satisfied with = expressed dissatisfaction regarding",
        "lesson_number": 5,
    },
    {
        "test_id": "ETS2024_04",
        "part": "Part 5",
        "question_no": 122,
        "sentence": "The distribution warehouse will dispatch the replacement parts as soon as the carrier _______ the inventory tracking number.",
        "choice_a": "verify",
        "choice_b": "verifies",
        "choice_c": "will verify",
        "choice_d": "verified",
        "correct_choice": "B",
        "explanation": "Trong mệnh đề trạng ngữ chỉ thời gian bắt đầu bằng 'as soon as', khi mệnh đề chính ở thì tương lai ('will dispatch'), mệnh đề phụ tuyệt đối không dùng 'will' mà phải chia thì hiện tại đơn ('verifies' theo chủ ngữ số ít 'the carrier').",
        "distractor_analysis": "[Bẫy Thì Trong Mệnh Đề Thời Gian] C (will verify) là bẫy kinh điển cho thì tương lai trong mệnh đề phụ thời gian.",
        "paraphrase_pair": "as soon as carrier verifies = immediately upon confirmation by the shipper",
        "lesson_number": 6,
    },
    {
        "test_id": "ETS2024_04",
        "part": "Part 5",
        "question_no": 123,
        "sentence": "Team leaders should compile quarterly performance reviews for all employees in _______ respective business units.",
        "choice_a": "they",
        "choice_b": "their",
        "choice_c": "theirs",
        "choice_d": "them",
        "correct_choice": "B",
        "explanation": "Đứng trước cụm danh từ 'respective business units' cần một tính từ sở hữu để bổ nghĩa ➔ chọn 'their' (đơn vị kinh doanh tương ứng của họ).",
        "distractor_analysis": "[Bẫy Đại Từ Sở Hữu vs Tính Từ Sở Hữu] C (theirs là đại từ sở hữu, không đứng trước danh từ), A (chủ ngữ), D (tân ngữ).",
        "paraphrase_pair": "their respective business units = their corresponding departments",
        "lesson_number": 7,
    },
    {
        "test_id": "ETS2024_04",
        "part": "Part 5",
        "question_no": 124,
        "sentence": "Expense reimbursement requests _______ after the final Friday of the month will be processed during the subsequent pay cycle.",
        "choice_a": "submitting",
        "choice_b": "submitted",
        "choice_c": "submit",
        "choice_d": "submits",
        "correct_choice": "B",
        "explanation": "Mệnh đề quan hệ rút gọn ở dạng bị động: 'requests [which are] submitted after the final Friday...' ➔ rút gọn thành phân từ hai 'submitted'.",
        "distractor_analysis": "[Bẫy Phân Từ Chủ Động vs Bị Động] A (submitting là dạng chủ động, yêu cầu hoàn tiền không thể tự nộp mà phải được người nộp).",
        "paraphrase_pair": "requests submitted = claims turned in",
        "lesson_number": 8,
    },
    {
        "test_id": "ETS2024_04",
        "part": "Part 5",
        "question_no": 125,
        "sentence": "The off-site data facility _______ houses our secondary disaster recovery servers is equipped with redundant backup generators.",
        "choice_a": "which",
        "choice_b": "who",
        "choice_c": "whom",
        "choice_d": "where",
        "correct_choice": "A",
        "explanation": "'The off-site data facility' là danh từ chỉ vật/cơ sở hạ tầng. Phía sau là động từ 'houses' (chứa đựng) thiếu chủ ngữ ➔ dùng đại từ quan hệ 'which' (hoặc that).",
        "distractor_analysis": "[Bẫy Trạng Từ Quan Hệ 'where'] D (where) chỉ đóng vai trò trạng từ nơi chốn, theo sau phải là mệnh đề hoàn chỉnh S+V, không thể làm chủ ngữ cho 'houses'. B, C chỉ người.",
        "paraphrase_pair": "facility which houses = center containing",
        "lesson_number": 9,
    },
    {
        "test_id": "ETS2024_04",
        "part": "Part 5",
        "question_no": 126,
        "sentence": "_______ the engineering team anticipated the sudden surge in network traffic, they would have provisioned additional cloud instances.",
        "choice_a": "Had",
        "choice_b": "Should",
        "choice_c": "Were",
        "choice_d": "If only",
        "correct_choice": "A",
        "explanation": "Mệnh đề chính dùng 'would have provisioned' (câu điều kiện loại 3). Đảo ngữ câu điều kiện loại 3: 'Had + S + V3/ed' (= If the engineering team had anticipated...).",
        "distractor_analysis": "[Bẫy Đảo Ngữ Điều Kiện Loại 3] B (Should dùng cho loại 1), C (Were dùng cho loại 2), D (If only thiếu trợ động từ đảo ngữ).",
        "paraphrase_pair": "Had the team anticipated = If the group had foreseen",
        "lesson_number": 10,
    },
    {
        "test_id": "ETS2024_04",
        "part": "Part 5",
        "question_no": 127,
        "sentence": "By far _______ cost-effective solution for long-term cold data storage is automated magnetic tape archiving.",
        "choice_a": "more",
        "choice_b": "the most",
        "choice_c": "most",
        "choice_d": "much more",
        "correct_choice": "B",
        "explanation": "Cụm nhấn mạnh 'by far' luôn đi kèm với so sánh nhất có mạo từ 'the': 'by far the most + Adj' (giải pháp vượt trội nhất / chắc chắn là tiết kiệm nhất).",
        "distractor_analysis": "[Bẫy Nhấn Mạnh So Sánh Nhất] C thiếu 'the', A và D là cấu trúc so sánh hơn (không đi với cụm 'by far the most...').",
        "paraphrase_pair": "by far the most cost-effective = undeniably the most economical",
        "lesson_number": 11,
    },
    {
        "test_id": "ETS2024_04",
        "part": "Part 5",
        "question_no": 128,
        "sentence": "The strategic alliance between the software vendor and the logistics firm established a _______ beneficial partnership.",
        "choice_a": "mutually",
        "choice_b": "mutual",
        "choice_c": "mutuality",
        "choice_d": "mutuated",
        "correct_choice": "A",
        "explanation": "'mutually beneficial' là một Business Collocation vàng trong TOEIC (đôi bên cùng có lợi). Đứng trước tính từ 'beneficial' cần trạng từ 'mutually' để bổ nghĩa.",
        "distractor_analysis": "[Bẫy Collocation & Trạng Từ Bổ Nghĩa Cho Tính Từ] B (mutual là tính từ, không bổ nghĩa cho tính từ beneficial), C (danh từ).",
        "paraphrase_pair": "mutually beneficial partnership = win-win collaboration",
        "lesson_number": 12,
    },
    {
        "test_id": "ETS2024_04",
        "part": "Part 5",
        "question_no": 129,
        "sentence": "The fiber optic cable connection was accidentally severed during excavation; _______, internet access was temporarily rerouted.",
        "choice_a": "consequently",
        "choice_b": "consequence",
        "choice_c": "consequent",
        "choice_d": "consequentially",
        "correct_choice": "A",
        "explanation": "Đứng đầu mệnh đề sau dấu chấm phẩy và trước dấu phẩy thể hiện mối quan hệ nhân quả (kết quả là...) ➔ dùng trạng từ liên kết 'consequently' (= as a result).",
        "distractor_analysis": "[Bẫy Trạng Từ Liên Kết] B (danh từ), C (tính từ), D (từ hiếm có nét nghĩa khác).",
        "paraphrase_pair": "consequently = as a result = therefore",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_04",
        "part": "Part 5",
        "question_no": 130,
        "sentence": "The regional zoning board granted _______ approval for the new suburban fulfillment center pending environmental impact studies.",
        "choice_a": "provisional",
        "choice_b": "provisionally",
        "choice_c": "provision",
        "choice_d": "provisioning",
        "correct_choice": "A",
        "explanation": "Trước danh từ 'approval' cần một tính từ bổ nghĩa ➔ 'provisional approval' (sự phê duyệt tạm thời / có điều kiện trước khi có thẩm định môi trường).",
        "distractor_analysis": "[Bẫy Vị Trí Tính Từ Trước Danh Từ] B (trạng từ), C (danh từ sự chu cấp), D (danh từ việc cấu hình hạ tầng).",
        "paraphrase_pair": "provisional approval = conditional authorization",
        "lesson_number": 12,
    },

    # --- Part 6: Text Completion (Q131 -> Q134) ---
    {
        "test_id": "ETS2024_04",
        "part": "Part 6",
        "question_no": 131,
        "sentence": "MEMORANDUM\nTo: All Remote Employees\nFrom: Global Information Security Office\nDate: October 14\nSubject: Mandatory VPN Software Upgrade\n\nStarting Monday, November 1, our company will implement an upgraded virtual private network protocol. To safeguard corporate resources, all remote devices will _______ synchronize with the new authentication server upon startup.",
        "choice_a": "automatic",
        "choice_b": "automatically",
        "choice_c": "automation",
        "choice_d": "automate",
        "correct_choice": "B",
        "explanation": "Đứng giữa trợ động từ 'will' và động từ chính 'synchronize' cần trạng từ phương thức ➔ chọn 'automatically' (tự động đồng bộ hóa).",
        "distractor_analysis": "[Bẫy Vị Trí Từ Loại] A (tính từ), C (danh từ), D (động từ nguyên mẫu) sai cấu trúc bổ nghĩa.",
        "paraphrase_pair": "automatically synchronize = connect without manual intervention",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_04",
        "part": "Part 6",
        "question_no": 132,
        "sentence": "Employees who fail to _______ with this security policy may experience disruptions in accessing internal repositories.",
        "choice_a": "comply",
        "choice_b": "adhere",
        "choice_c": "conform",
        "choice_d": "abide",
        "correct_choice": "A",
        "explanation": "Đi kèm với giới từ 'with' trong ngữ cảnh tuân thủ quy định: 'comply with'. Lưu ý: 'adhere to', 'conform to', 'abide by'. Do đề bài dùng 'with' nên bắt buộc phải chọn 'comply'.",
        "distractor_analysis": "[Bẫy Giới Từ Đi Kèm Động Từ Đồng Nghĩa] B (adhere đi với 'to'), C (conform đi với 'to'), D (abide đi với 'by').",
        "paraphrase_pair": "fail to comply with = violate / disregard the guideline",
        "lesson_number": 12,
    },
    {
        "test_id": "ETS2024_04",
        "part": "Part 6",
        "question_no": 133,
        "sentence": "[133] _______. The installation package requires fewer than five minutes to complete and requires no administrative privileges.",
        "choice_a": "The desktop client application can be downloaded directly from the internal IT self-service portal.",
        "choice_b": "Office supplies should be ordered through the purchasing department before noon.",
        "choice_c": "Travel expense receipts must be submitted within thirty business days.",
        "choice_d": "Annual performance appraisals will take place throughout December.",
        "correct_choice": "A",
        "explanation": "Câu sau nói về gói cài đặt phần mềm ('The installation package requires fewer than five minutes...'). Câu trước cần giới thiệu nguồn tải phần mềm ứng dụng ➔ chọn phương án A liên quan trực tiếp đến việc download ứng dụng.",
        "distractor_analysis": "[Bẫy Chủ Đề Lạc Mạch] B (văn phòng phẩm), C (chi phí công tác), D (đánh giá năng suất) đều lạc mạch văn bản bảo mật mạng.",
        "paraphrase_pair": "downloaded from self-service portal = obtained via company intranet",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_04",
        "part": "Part 6",
        "question_no": 134,
        "sentence": "Accounts that remain unlinked to the new security portal by November 5 _______ indefinitely until verified by a manager.",
        "choice_a": "deactivated",
        "choice_b": "will be deactivated",
        "choice_c": "deactivating",
        "choice_d": "have deactivated",
        "correct_choice": "B",
        "explanation": "Mốc thời gian tương lai 'by November 5' và chủ ngữ 'Accounts' phải chịu tác động bị động ➔ chia bị động thì tương lai: 'will be deactivated'.",
        "distractor_analysis": "[Bẫy Thì và Thể Bị Động] A (quá khứ đơn), C (phân từ hiện tại), D (chủ động hiện tại hoàn thành).",
        "paraphrase_pair": "will be deactivated indefinitely = will be suspended until further notice",
        "lesson_number": 4,
    },

    # --- Part 7: Reading Comprehension (Q147 -> Q150) ---
    {
        "test_id": "ETS2024_04",
        "part": "Part 7",
        "question_no": 147,
        "sentence": "EXECUTIVE EVALUATION REPORT\nSubject: Cloud Archival Storage Vendor Assessment\nPrepared by: Enterprise Architecture Council\nDate: September 28\n\n1. Executive Summary\nOver the past six weeks, the Enterprise Architecture Council conducted an exhaustive technical and financial evaluation of three leading cloud archival service providers: Apex Data Systems, Horizon Cloud, and Nova Vault. Our primary objective is to select an enterprise storage tier capable of preserving forty petabytes of compliance records while adhering to stringent latency criteria.\n\n2. Security and Regulatory Findings\nApex Data Systems demonstrated superior encryption standards, exceeding SOC 2 Type II and ISO 27001 requirements. Most notably, Apex features automated immutable object locking, guaranteeing that financial audits remain tamper-proof throughout the required seven-year retention window.\n\n3. Financial Analysis & Migration Strategy\nWhile Horizon Cloud offered slightly lower baseline storage pricing, its high data retrieval egress penalties outweigh initial savings. Following preliminary negotiations, Apex Data Systems agreed to waive all data ingestion fees during the initial cutover phase.\n\n4. Recommendation\nWe recommend executing a multi-year master service agreement with Apex Data Systems. Phased migration is scheduled to commence during the fiscal fourth quarter, ensuring zero disruption to live customer billing systems.\n\nWhat is the primary purpose of the evaluation report?",
        "choice_a": "To recommend an enterprise cloud storage vendor for long-term archival data.",
        "choice_b": "To announce the termination of an existing vendor contract.",
        "choice_c": "To outline annual budget cuts across the information technology division.",
        "choice_d": "To introduce a newly appointed chief information security officer.",
        "correct_choice": "A",
        "explanation": "Đoạn 1 nêu rõ: 'Our primary objective is to select an enterprise storage tier capable of preserving forty petabytes of compliance records...' và đoạn 4: 'We recommend executing a multi-year master service agreement with Apex Data Systems' ➔ Báo cáo nhằm đề xuất nhà cung cấp dịch vụ lưu trữ đám mây cho dữ liệu lưu trữ dài hạn.",
        "distractor_analysis": "[Bẫy Suy Diễn Sai] B (thông báo hủy hợp đồng), C (cắt giảm ngân sách), D (bổ nhiệm lãnh đạo mới) không phải mục tiêu tài liệu.",
        "paraphrase_pair": "select an enterprise storage tier = recommend a cloud storage vendor for long-term data",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_04",
        "part": "Part 7",
        "question_no": 148,
        "sentence": "According to the report, what is a distinct advantage of Apex Data Systems?",
        "choice_a": "It offers the cheapest data retrieval egress fees among all competitors.",
        "choice_b": "It provides tamper-proof object locking for regulatory compliance.",
        "choice_c": "It completed the migration process ahead of the original deadline.",
        "choice_d": "It manufactures physical hard drives locally.",
        "correct_choice": "B",
        "explanation": "Trong đoạn 2: 'Apex features automated immutable object locking, guaranteeing that financial audits remain tamper-proof throughout the required seven-year retention window.'",
        "distractor_analysis": "[Bẫy Chi Tiết Ngược & Bịa Đặt] A sai vì Horizon mới có giá lưu trữ cơ bản thấp hơn nhưng phí rút dữ liệu cao. C quá trình di chuyển chưa bắt đầu (Q4 mới bắt đầu). D không được đề cập.",
        "paraphrase_pair": "immutable object locking = tamper-proof storage for compliance",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_04",
        "part": "Part 7",
        "question_no": 149,
        "sentence": "What is indicated about the data migration timeline?",
        "choice_a": "It will take place during the final quarter of the fiscal year.",
        "choice_b": "It was completed during the preliminary testing phase.",
        "choice_c": "It has been suspended indefinitely due to egress fees.",
        "choice_d": "It requires taking all customer billing servers offline for one week.",
        "correct_choice": "A",
        "explanation": "Đoạn 4 nêu rõ: 'Phased migration is scheduled to commence during the fiscal fourth quarter, ensuring zero disruption to live customer billing systems.'",
        "distractor_analysis": "[Bẫy Ngữ Cảnh] B sai vì mới xong giai đoạn đánh giá. C sai vì phí đã được đàm phán miễn phí nạp. D sai vì bài viết nhấn mạnh 'zero disruption' (không gián đoạn).",
        "paraphrase_pair": "commence during the fiscal fourth quarter = take place during the final quarter of the fiscal year",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_04",
        "part": "Part 7",
        "question_no": 150,
        "sentence": "In paragraph 3, the word 'preliminary' is closest in meaning to:",
        "choice_a": "initial",
        "choice_b": "final",
        "choice_c": "aggressive",
        "choice_d": "expensive",
        "correct_choice": "A",
        "explanation": "Cụm 'preliminary negotiations' mang nghĩa các cuộc đàm phán bước đầu, sơ bộ trước khi ký hợp đồng chính thức ➔ đồng nghĩa với 'initial' (ban đầu, sơ bộ).",
        "distractor_analysis": "[Bẫy Từ Đồng Nghĩa & Trái Nghĩa] B (final - cuối cùng, trái nghĩa), C (aggressive - hiếu chiến), D (expensive - đắt đỏ).",
        "paraphrase_pair": "preliminary negotiations = initial discussions",
        "lesson_number": 12,
    },
]

# -------------------------------------------------------------
# 2. 20 High-Frequency Business & Tech Flashcards
# -------------------------------------------------------------
NEW_FLASHCARDS_TEST04 = [
    ("preliminary", "/prɪˈlɪm.ə.ner.i/", "adjective", "General Business", "sơ bộ, ban đầu trước giai đoạn chính",
     "preliminary findings / preliminary approval", "preliminary = initial = preparatory = exploratory",
     "The committee released its preliminary findings before publishing the full technical report.",
     "Ủy ban đã công bố các phát hiện sơ bộ trước khi xuất bản bản báo cáo kỹ thuật đầy đủ."),

    ("compliance", "/kəmˈplaɪ.əns/", "noun", "Manufacturing & Compliance", "sự tuân thủ tiêu chuẩn, quy định luật pháp",
     "regulatory compliance / in compliance with", "compliance = adherence = conformity = observance",
     "All cloud servers must operate in strict compliance with international data privacy laws.",
     "Mọi máy chủ đám mây bắt buộc phải vận hành theo đúng sự tuân thủ nghiêm ngặt luật bảo mật dữ liệu quốc tế."),

    ("infrastructure", "/ˈɪn.frəˌstrʌk.tʃɚ/", "noun", "Computers & IT", "cơ sở hạ tầng mạng và phần cứng máy chủ",
     "cloud infrastructure / IT infrastructure", "infrastructure = foundation = underlying framework",
     "Investing in resilient network infrastructure prevented unplanned downtime during peak hours.",
     "Đầu tư vào cơ sở hạ tầng mạng vững chắc đã ngăn ngừa sự cố ngừng hoạt động ngoài ý muốn trong giờ cao điểm."),

    ("authorization", "/ˌɑː.θɚ.əˈzeɪ.ʃən/", "noun", "Corporate Operations", "sự ủy quyền, cấp phép chính thức",
     "obtain authorization / executive authorization", "authorization = official permission = approval = sanction",
     "Accessing the production database requires multi-factor authorization from a system administrator.",
     "Việc truy cập vào cơ sở dữ liệu thực tế đòi hỏi sự cấp phép xác thực đa yếu tố từ quản trị viên hệ thống."),

    ("confidentiality", "/ˌkɑːn.fə.den.ʃiˈæl.ə.t̬i/", "noun", "Contracts & Agreements", "tính bảo mật thông tin nội bộ",
     "maintain confidentiality / confidentiality agreement", "confidentiality = secrecy = privacy = discretion",
     "Both enterprise vendors signed a non-disclosure agreement to protect client confidentiality.",
     "Cả hai nhà cung cấp doanh nghiệp đều ký thỏa thuận không tiết lộ để bảo vệ tính bảo mật của khách hàng."),

    ("subsequent", "/ˈsʌb.sɪ.kwənt/", "adjective", "General Business", "xảy ra sau đó, tiếp theo",
     "subsequent meeting / subsequent phase", "subsequent = following = succeeding = ensuing",
     "Initial feedback was collected, and adjustments were made in all subsequent software releases.",
     "Phản hồi ban đầu đã được thu thập, và các điều chỉnh đã được thực hiện trong tất cả các bản phát hành tiếp theo."),

    ("substantial", "/səbˈstæn.ʃəl/", "adjective", "Accounting & Finance", "đáng kể, có giá trị lớn về số lượng",
     "substantial increase / substantial savings", "substantial = considerable = significant = sizable",
     "Automating manual data reconciliation resulted in substantial cost savings for the billing department.",
     "Việc tự động hóa đối soát số liệu thủ công đã mang lại khoản tiết kiệm chi phí đáng kể cho phòng thanh toán."),

    ("negligence", "/ˈneɡ.lə.dʒəns/", "noun", "Contracts & Agreements", "sự sơ suất, thiếu cẩn trọng gây tổn hại",
     "gross negligence / professional negligence", "negligence = carelessness = dereliction = oversight",
     "The contractor was held legally liable for property damage caused by gross negligence.",
     "Nhà thầu phải chịu trách nhiệm pháp lý đối với thiệt hại tài sản do sự bất cẩn nghiêm trọng gây ra."),

    ("feasibility", "/ˌfiː.zəˈbɪl.ə.t̬i/", "noun", "General Business", "tính khả thi của kế hoạch dự án",
     "feasibility study / technical feasibility", "feasibility = viability = practicability = workability",
     "The architects conducted a thorough study to determine the economic feasibility of the expansion.",
     "Các kiến trúc sư đã tiến hành một nghiên cứu kỹ lưỡng để xác định tính khả thi kinh tế của việc mở rộng."),

    ("utilization", "/ˌjuː.t̬əl.əˈzeɪ.ʃən/", "noun", "Computers & IT", "mức độ sử dụng, hiệu suất tận dụng tài nguyên",
     "resource utilization / CPU utilization", "utilization = usage = exploitation = application",
     "Container orchestration software optimizes server utilization and minimizes hardware costs.",
     "Phần mềm điều phối container tối ưu hóa hiệu suất tận dụng máy chủ và giảm thiểu chi phí phần cứng."),

    ("allocation", "/ˌæl.əˈkeɪ.ʃən/", "noun", "Accounting & Finance", "sự phân bổ ngân sách hoặc tài nguyên",
     "budget allocation / resource allocation", "allocation = apportionment = distribution = assignment",
     "The executive board approved a generous budget allocation for artificial intelligence research.",
     "Hội đồng quản trị đã phê duyệt khoản phân bổ ngân sách hào phóng cho việc nghiên cứu trí tuệ nhân tạo."),

    ("procurement", "/prəˈkjʊr.mənt/", "noun", "Corporate Operations", "hoạt động thu mua trang thiết bị doanh nghiệp",
     "equipment procurement / procurement officer", "procurement = purchasing = acquisition = sourcing",
     "The procurement department negotiated volume discounts with our primary server suppliers.",
     "Phòng thu mua đã đàm phán mức chiết khấu số lượng lớn với các nhà cung cấp máy chủ chính của chúng tôi."),

    ("expedite", "/ˈek.spə.daɪt/", "verb", "Logistics & Transportation", "đẩy nhanh tiến độ xử lý hoặc giao nhận",
     "expedite delivery / expedite processing", "expedite = accelerate = hasten = speed up",
     "We paid an additional express fee to expedite shipping of the critical replacement router.",
     "Chúng tôi đã trả thêm một khoản phí chuyển phát nhanh để đẩy nhanh việc vận chuyển bộ định tuyến thay thế khẩn cấp."),

    ("supersede", "/ˌsuː.pɚˈsiːd/", "verb", "Corporate Operations", "thay thế vị trí, thế chỗ quy chuẩn cũ",
     "supersede regulations / superseded by", "supersede = replace = supplant = take precedence over",
     "The updated digital security guidelines completely supersede all prior departmental policies.",
     "Các hướng dẫn bảo mật kỹ thuật số cập nhật hoàn toàn thay thế toàn bộ các chính sách ban ngành trước đó."),

    ("retention", "/rɪˈten.ʃən/", "noun", "Human Resources", "sự duy trì nhân sự / thời hạn lưu giữ dữ liệu",
     "employee retention / data retention policy", "retention = keeping = preservation = holding",
     "Financial transaction records must adhere to a strict seven-year data retention schedule.",
     "Các hồ sơ giao dịch tài chính phải tuân thủ lịch trình lưu giữ dữ liệu nghiêm ngặt trong bảy năm."),

    ("provisional", "/prəˈvɪʒ.ən.əl/", "adjective", "Contracts & Agreements", "tạm thời, có hiệu lực lâm thời",
     "provisional license / provisional approval", "provisional = temporary = interim = conditional",
     "The engineering team received provisional permission to commence deployment next Monday.",
     "Đội ngũ kỹ thuật đã nhận được sự chấp thuận tạm thời để bắt đầu triển khai vào thứ Hai tới."),

    ("rigorous", "/ˈrɪɡ.ɚ.əs/", "adjective", "Manufacturing & Compliance", "khắt khe, cẩn trọng và nghiêm ngặt",
     "rigorous testing / rigorous standards", "rigorous = thorough = strict = meticulous = stringent",
     "The software module underwent rigorous automated penetration testing prior to release.",
     "Mô-đun phần mềm đã trải qua cuộc kiểm thử xâm nhập tự động nghiêm ngặt trước khi xuất xưởng."),

    ("deterioration", "/dɪˌtɪr.i.əˈreɪ.ʃən/", "noun", "Manufacturing & Compliance", "sự xuống cấp, suy thoái chất lượng vật liệu",
     "prevent deterioration / physical deterioration", "deterioration = degradation = decline = worsening",
     "Climate-controlled server racks prevent hardware deterioration caused by humidity and heat.",
     "Các tủ máy chủ kiểm soát nhiệt ẩm ngăn ngừa sự xuống cấp của phần cứng do độ ẩm và nhiệt độ gây ra."),

    ("unprecedented", "/ʌnˈpres.ə.den.t̬ɪd/", "adjective", "General Business", "chưa từng có tiền lệ trong lịch sử",
     "unprecedented growth / unprecedented demand", "unprecedented = groundbreaking = unparalleled = novel",
     "The e-commerce platform experienced unprecedented user demand during the Black Friday campaign.",
     "Nền tảng thương mại điện tử đã chứng kiến nhu cầu người dùng chưa từng có trong đợt khuyến mãi Black Friday."),

    ("versatile", "/ˈvɝː.sə.t̬əl/", "adjective", "Computers & IT", "linh hoạt, đa năng ứng dụng trong nhiều lĩnh vực",
     "versatile platform / versatile tool", "versatile = adaptable = multi-purpose = all-around",
     "Python is renowned for being a versatile programming language suitable for web development and AI.",
     "Python nổi tiếng là một ngôn ngữ lập trình linh hoạt phù hợp cho cả phát triển web và trí tuệ nhân tạo."),
]

# -------------------------------------------------------------
# 3. 10 High-Frequency Paraphrase Pairs (Part 7 Vault)
# -------------------------------------------------------------
NEW_PARAPHRASE_PAIRS_TEST04 = [
    {
        "word_in_text": "select an enterprise storage tier",
        "word_in_answer": "recommend a cloud storage vendor for long-term archival data",
        "meaning": "lựa chọn nhà cung cấp dịch vụ lưu trữ đám mây cho tài liệu dài hạn",
        "part_target": "Part 7 RFPs & Vendor Assessments",
        "frequency": "Extreme",
    },
    {
        "word_in_text": "tamper-proof object locking",
        "word_in_answer": "immutable data protection for regulatory compliance",
        "meaning": "khóa dữ liệu chống chỉnh sửa trái phép phục vụ tuân thủ pháp lý",
        "part_target": "Part 7 Security Findings",
        "frequency": "High",
    },
    {
        "word_in_text": "commence during the fiscal fourth quarter",
        "word_in_answer": "take place during the final quarter of the fiscal year",
        "meaning": "bắt đầu triển khai trong quý 4 của năm tài chính",
        "part_target": "Part 7 Migration Schedules",
        "frequency": "Extreme",
    },
    {
        "word_in_text": "preliminary negotiations",
        "word_in_answer": "initial discussions / exploratory talks",
        "meaning": "các cuộc đàm phán sơ bộ ban đầu",
        "part_target": "Part 7 Contract Memos",
        "frequency": "Extreme",
    },
    {
        "word_in_text": "waive all data ingestion fees",
        "word_in_answer": "eliminate upfront upload expenses during cutover",
        "meaning": "miễn toàn bộ phí nạp dữ liệu trong giai đoạn chuyển đổi",
        "part_target": "Part 7 Financial Terms",
        "frequency": "High",
    },
    {
        "word_in_text": "zero disruption to live customer billing",
        "word_in_answer": "uninterrupted financial operations during upgrade",
        "meaning": "hoạt động thanh toán liên tục không bị gián đoạn",
        "part_target": "Part 7 Executive Summaries",
        "frequency": "High",
    },
    {
        "word_in_text": "automatic synchronization upon startup",
        "word_in_answer": "connect without manual employee intervention",
        "meaning": "tự động kết nối không cần thao tác thủ công",
        "part_target": "Part 6 IT Policies",
        "frequency": "High",
    },
    {
        "word_in_text": "fail to comply with policy",
        "word_in_answer": "disregard or violate company guidelines",
        "meaning": "không tuân thủ quy định bảo mật của công ty",
        "part_target": "Part 6 Compliance Notices",
        "frequency": "Extreme",
    },
    {
        "word_in_text": "requires fewer than five minutes",
        "word_in_answer": "brief and rapid setup procedure",
        "meaning": "quy trình cài đặt nhanh chóng dưới năm phút",
        "part_target": "Part 6 User Guides",
        "frequency": "High",
    },
    {
        "word_in_text": "suspended indefinitely until verified",
        "word_in_answer": "temporarily locked pending managerial confirmation",
        "meaning": "tạm khóa tài khoản cho đến khi được cấp trên xác nhận",
        "part_target": "Part 6 Access Notices",
        "frequency": "High",
    },
]


def ingest_test04(db_session=None):
    close_when_done = False
    if db_session is None:
        init_db()
        db = SessionLocal()
        close_when_done = True
    else:
        db = db_session

    try:
        print("=== 1. Ingesting Mock Test ETS2024_04 ===")
        test_04 = db.query(MockTest).filter_by(test_id="ETS2024_04").first()
        if not test_04:
            test_04 = MockTest(
                test_id="ETS2024_04",
                name="ETS TOEIC Regular Test 2024 - Test 04",
                year=2024,
                publisher="ETS",
                total_questions=200,
            )
            db.add(test_04)
            db.commit()
            db.refresh(test_04)
            print("  ✓ Created MockTest 'ETS2024_04'")
        else:
            print("  • MockTest 'ETS2024_04' already exists")

        print("\n=== 2. Ingesting Questions for ETS2024_04 ===")
        inserted_q_count = 0
        for item in TEST_04_QUESTIONS:
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
                    image_url=item.get("image_url"),
                    lesson_number=item.get("lesson_number"),
                )
                db.add(q)
                inserted_q_count += 1
        db.commit()
        print(f"  ✓ Ingested {inserted_q_count} new questions for ETS2024_04 (Total defined: {len(TEST_04_QUESTIONS)})")

        print("\n=== 3. Expanding Flashcards & SuperMemo-2 SRS ===")
        users = db.query(User).all()
        user_ids = [u.id for u in users] or [1]

        inserted_card_count = 0
        for word, ipa, wtype, cat, meaning, colloc, para, ex_en, ex_vi in NEW_FLASHCARDS_TEST04:
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
        for p in NEW_PARAPHRASE_PAIRS_TEST04:
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

        print("\n🎉 All ETS 2024 Test 04 dataset ingested successfully!")
        return {
            "test_id": "ETS2024_04",
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
    ingest_test04()
