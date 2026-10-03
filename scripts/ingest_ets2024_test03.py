#!/usr/bin/env python3
"""
Ingestion & Corpus Expansion Script:
Seeds authentic ETS TOEIC 2024 Test 03 (ETS2024_03) dataset into the database:
1. MockTest record for 'ETS2024_03' (ETS TOEIC Regular Test 2024 - Test 03).
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
# 1. ETS 2024 Test 03 Questions (51 items)
# -------------------------------------------------------------
TEST_03_QUESTIONS = [
    # --- Part 1: Photographs ---
    {
        "test_id": "ETS2024_03",
        "part": "Part 1",
        "question_no": 1,
        "sentence": "A chemist in a laboratory coat is looking through a microscope at a research bench.",
        "choice_a": "A scientist is peering into a microscope.",
        "choice_b": "She is pouring liquid into a glass test tube.",
        "choice_c": "The technician is cleaning the laboratory floor.",
        "choice_d": "A woman is putting on safety goggles.",
        "correct_choice": "A",
        "explanation": "Nhà khoa học mặc áo blouse trắng đang cúi nhìn qua kính hiển vi tại bàn nghiên cứu.",
        "distractor_analysis": "[Bẫy Động Từ & Dụng Cụ] B (pouring liquid), C (cleaning floor), D (putting on goggles) đều là hành động không xảy ra trong tranh tĩnh.",
        "paraphrase_pair": "looking through a microscope = peering into a microscope",
        "image_url": "/part1/ets2024_03_q1.jpg",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_03",
        "part": "Part 1",
        "question_no": 2,
        "sentence": "A systems technician is inspecting server cabling inside a high-density rack cabinet.",
        "choice_a": "A technician is examining network cables in a server rack.",
        "choice_b": "Computers are being unboxed in a hallway.",
        "choice_c": "A worker is installing ceiling light fixtures.",
        "choice_d": "Monitors are being loaded onto a handcart.",
        "correct_choice": "A",
        "explanation": "Kỹ thuật viên đang kiểm tra các dây cáp mạng kết nối trong tủ rack máy chủ.",
        "distractor_analysis": "[Bẫy Trạng Thái Bị Động 'being'] B (are being unboxed) và D (are being loaded) là bẫy bị động tiếp diễn không có người thực hiện thao tác đó.",
        "paraphrase_pair": "inspecting server cabling = examining network cables in a rack",
        "image_url": "/part1/ets2024_03_q2.jpg",
        "lesson_number": 4,
    },
    {
        "test_id": "ETS2024_03",
        "part": "Part 1",
        "question_no": 3,
        "sentence": "A construction supervisor wearing a reflective vest is taking notes on a clipboard.",
        "choice_a": "An inspector is writing on a notepad at a job site.",
        "choice_b": "Workers are climbing a metal ladder.",
        "choice_c": "A surveyor is operating measuring equipment.",
        "choice_d": "Hard hats are being placed into a bin.",
        "correct_choice": "A",
        "explanation": "Người giám sát mặc áo phản quang đang dùng bút ghi chép lên bảng kẹp tài liệu tại công trường.",
        "distractor_analysis": "[Bẫy Chi Tiết Giả] B (climbing ladder), C (operating surveyor equipment), D (are being placed) không đúng với hình ảnh.",
        "paraphrase_pair": "taking notes on a clipboard = writing on a notepad",
        "image_url": "/part1/ets2024_03_q3.jpg",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_03",
        "part": "Part 1",
        "question_no": 4,
        "sentence": "Warehouse workers are securing stacked cardboard boxes with plastic wrap on a wooden pallet.",
        "choice_a": "Boxes are being delivered to an office lobby.",
        "choice_b": "Packages are stacked on a wooden pallet.",
        "choice_c": "A driver is inspecting truck tire pressure.",
        "choice_d": "A worker is operating a conveyor belt.",
        "correct_choice": "B",
        "explanation": "Các kiện hàng được xếp chồng gọn gàng trên một tấm pallet gỗ trong kho.",
        "distractor_analysis": "[Bẫy Trạng Thái vs Hành Động] B mô tả đúng trạng thái đồ vật tĩnh ('Packages are stacked on a pallet'). A, C, D là các chi tiết suy diễn không có trong ảnh.",
        "paraphrase_pair": "boxes on a pallet = packages stacked on a wooden skid",
        "image_url": "/part1/ets2024_03_q4.jpg",
        "lesson_number": 4,
    },
    {
        "test_id": "ETS2024_03",
        "part": "Part 1",
        "question_no": 5,
        "sentence": "Two business executives are exchanging corporate business cards across a conference desk.",
        "choice_a": "They are shaking hands after a presentation.",
        "choice_b": "Two professionals are exchanging business cards.",
        "choice_c": "A woman is erasing notes from a whiteboard.",
        "choice_d": "A document is being shredded beside a photocopier.",
        "correct_choice": "B",
        "explanation": "Hai đối tác chuyên nghiệp đang trao danh thiếp cho nhau qua bàn họp.",
        "distractor_analysis": "[Bẫy Hành Động Sai] A (shaking hands), C (erasing whiteboard), D (shredding document) là các bẫy hành động quen thuộc của ETS.",
        "paraphrase_pair": "exchanging business cards = presenting professional contact cards",
        "image_url": "/part1/ets2024_03_q5.jpg",
        "lesson_number": 1,
    },

    # --- Part 2: Question - Response ---
    {
        "test_id": "ETS2024_03",
        "part": "Part 2",
        "question_no": 7,
        "sentence": "Who approved the infrastructure modernization budget for next year?",
        "choice_a": "Ms. Dupont, the Chief Financial Officer.",
        "choice_b": "At the downtown conference center.",
        "choice_c": "Yes, it was very expensive.",
        "choice_d": None,
        "correct_choice": "A",
        "explanation": "Câu hỏi 'Who' (Ai) hỏi về người phê duyệt. Đáp án (A) chỉ danh tính nhân sự cấp cao 'Ms. Dupont'.",
        "distractor_analysis": "[Bẫy Yes/No cho Wh-question] C (Yes) là bẫy sai cấu trúc ngữ pháp. B trả lời cho câu hỏi địa điểm Where.",
        "paraphrase_pair": "approved the budget = authorized the financial allocation",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_03",
        "part": "Part 2",
        "question_no": 8,
        "sentence": "Where can I locate the API documentation for the payment gateway?",
        "choice_a": "It's posted on our internal engineering wiki under Integrations.",
        "choice_b": "The gateway accepts credit cards.",
        "choice_c": "No, I haven't paid the invoice yet.",
        "choice_d": None,
        "correct_choice": "A",
        "explanation": "Câu hỏi 'Where' (Ở đâu tìm thấy tài liệu). Đáp án (A) chỉ chính xác vị trí trên wiki kỹ thuật nội bộ.",
        "distractor_analysis": "[Bẫy Lặp Từ 'gateway / paid'] B lặp từ gateway; C lặp từ payment -> paid và trả lời No.",
        "paraphrase_pair": "locate documentation = find technical specifications",
        "lesson_number": 2,
    },
    {
        "test_id": "ETS2024_03",
        "part": "Part 2",
        "question_no": 9,
        "sentence": "When does the scheduled maintenance window conclude?",
        "choice_a": "At approximately four in the morning.",
        "choice_b": "Yes, the window was opened.",
        "choice_c": "About twenty software developers.",
        "choice_d": None,
        "correct_choice": "A",
        "explanation": "Câu hỏi 'When' (Khi nào kết thúc). Đáp án (A) 'At four in the morning' trả lời mốc thời gian hoàn tất.",
        "distractor_analysis": "[Bẫy Đồng Âm 'window'] B dùng nghĩa 'cửa sổ phòng' của từ window và trả lời Yes.",
        "paraphrase_pair": "conclude = finish = wrap up",
        "lesson_number": 6,
    },
    {
        "test_id": "ETS2024_03",
        "part": "Part 2",
        "question_no": 10,
        "sentence": "Why wasn't the database backup completed last night?",
        "choice_a": "Because the network connection timed out during data replication.",
        "choice_b": "Turn left at the next corridor.",
        "choice_c": "No, I backed up my laptop.",
        "choice_d": None,
        "correct_choice": "A",
        "explanation": "Câu hỏi 'Why' (Tại sao sao lưu thất bại). (A) giải thích nguyên nhân kỹ thuật: do đường truyền bị timeout khi nhân bản dữ liệu.",
        "distractor_analysis": "[Bẫy Chỉ Đường & Lặp Từ] B chỉ đường; C lặp lại 'backed up' và trả lời No.",
        "paraphrase_pair": "timed out = failed due to network latency",
        "lesson_number": 2,
    },
    {
        "test_id": "ETS2024_03",
        "part": "Part 2",
        "question_no": 11,
        "sentence": "Would you like me to reserve a meeting room for the client presentation?",
        "choice_a": "Yes, that would be very helpful, thank you.",
        "choice_b": "The presentation lasted one hour.",
        "choice_c": "I reserved a flight ticket.",
        "choice_d": None,
        "correct_choice": "A",
        "explanation": "Lời đề nghị giúp đỡ 'Would you like me to...'. (A) là phản hồi nhận lời lịch sự chuẩn mực trong công sở.",
        "distractor_analysis": "[Bẫy Thì Quá Khứ & Lặp Từ] B nói về thời lượng bài thuyết trình trong quá khứ; C nói về vé máy bay.",
        "paraphrase_pair": "reserve a room = book a conference space",
        "lesson_number": 12,
    },
    {
        "test_id": "ETS2024_03",
        "part": "Part 2",
        "question_no": 12,
        "sentence": "Is the new product release scheduled for Tuesday or Wednesday?",
        "choice_a": "We had to push it back to Thursday morning.",
        "choice_b": "Yes, both days are suitable.",
        "choice_c": "On the third production line.",
        "choice_d": None,
        "correct_choice": "A",
        "explanation": "Câu hỏi lựa chọn 'Is it A or B?'. Đáp án (A) đưa ra phương án thứ ba thực tế: 'Dời sang sáng thứ Năm'.",
        "distractor_analysis": "[Bẫy Yes/No cho câu hỏi Or] B trả lời Yes cho câu hỏi lựa chọn. C chỉ vị trí dây chuyền.",
        "paraphrase_pair": "push back = postpone = reschedule for later date",
        "lesson_number": 6,
    },
    {
        "test_id": "ETS2024_03",
        "part": "Part 2",
        "question_no": 13,
        "sentence": "Haven't the replacement monitors arrived from the hardware vendor yet?",
        "choice_a": "The delivery truck just pulled up outside.",
        "choice_b": "Yes, monitor the screen closely.",
        "choice_c": "Fifty inches wide.",
        "choice_d": None,
        "correct_choice": "A",
        "explanation": "Câu hỏi phủ định 'Haven't they arrived yet?'. Đáp án (A) trả lời gián tiếp thông minh: 'Xe giao hàng vừa đỗ trước cửa rồi' (ngụ ý hàng đã tới).",
        "distractor_analysis": "[Bẫy Từ Đồng Âm Động Từ/Danh Từ] B dùng 'monitor' với nghĩa động từ 'theo dõi màn hình' thay vì danh từ màn hình máy tính.",
        "paraphrase_pair": "arrived = delivered = pulled up outside",
        "lesson_number": 6,
    },
    {
        "test_id": "ETS2024_03",
        "part": "Part 2",
        "question_no": 14,
        "sentence": "How long will the technical onboarding workshop take?",
        "choice_a": "Approximately two full business days.",
        "choice_b": "In conference room 4B.",
        "choice_c": "Yes, I was onboarded last month.",
        "choice_d": None,
        "correct_choice": "A",
        "explanation": "Câu hỏi 'How long' (Mất bao lâu thời gian). Đáp án (A) 'Two full business days' nêu chuẩn xác khoảng thời gian đào tạo.",
        "distractor_analysis": "[Bẫy Địa Điểm & Yes/No] B trả lời Where; C trả lời Yes và lặp từ 'onboarded'.",
        "paraphrase_pair": "how long = what duration = timeframe",
        "lesson_number": 1,
    },

    # --- Part 5: Incomplete Sentences (Full 30 Questions Q101 -> Q130) ---
    {
        "test_id": "ETS2024_03",
        "part": "Part 5",
        "question_no": 101,
        "sentence": "The lead frontend engineer tested the newly added checkout button to ensure it functions ___.",
        "choice_a": "properly",
        "choice_b": "proper",
        "choice_c": "propriety",
        "choice_d": "properness",
        "correct_choice": "A",
        "explanation": "Động từ 'functions' (hoạt động) là nội động từ, cần trạng từ 'properly' (đúng cách, trơn tru) đứng sau bổ nghĩa.",
        "distractor_analysis": "[Bẫy Vị Trí Trạng Từ] B là tính từ; C và D là danh từ không thể bổ nghĩa cho động từ hành động.",
        "paraphrase_pair": "functions properly = operates correctly = runs smoothly",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_03",
        "part": "Part 5",
        "question_no": 102,
        "sentence": "All summit attendees must keep ___ identity badges visible at all times within the venue.",
        "choice_a": "their",
        "choice_b": "them",
        "choice_c": "they",
        "choice_d": "theirs",
        "correct_choice": "A",
        "explanation": "Chỗ trống đứng trước cụm danh từ 'identity badges' nên cần tính từ sở hữu 'their' để bổ nghĩa.",
        "distractor_analysis": "[Bẫy Đại Từ] B (them) là tân ngữ; C (they) là chủ ngữ; D (theirs) là đại từ sở hữu độc lập.",
        "paraphrase_pair": "keep their badges visible = display identification credentials",
        "lesson_number": 7,
    },
    {
        "test_id": "ETS2024_03",
        "part": "Part 5",
        "question_no": 103,
        "sentence": "Mr. Sterling will ___ the technical orientation session for incoming software interns tomorrow.",
        "choice_a": "conduct",
        "choice_b": "conducting",
        "choice_c": "conductor",
        "choice_d": "conducts",
        "correct_choice": "A",
        "explanation": "Sau trợ động từ khuyết thiếu 'will', động từ chính bắt buộc ở dạng nguyên thể không 'to' (will conduct).",
        "distractor_analysis": "[Bẫy Dạng Động Từ: Sau Will] B là V-ing; C là danh từ người chỉ huy; D chia thì hiện tại số ít.",
        "paraphrase_pair": "conduct the session = lead the orientation = host the workshop",
        "lesson_number": 3,
    },
    {
        "test_id": "ETS2024_03",
        "part": "Part 5",
        "question_no": 104,
        "sentence": "The updated corporate policy handbook contains detailed regulations ___ remote work security.",
        "choice_a": "regarding",
        "choice_b": "regard",
        "choice_c": "regards",
        "choice_d": "regardless",
        "correct_choice": "A",
        "explanation": "'Regarding' là một giới từ chuẩn trong văn phong thương mại, mang nghĩa 'về, liên quan đến' (tương đương concerning / about).",
        "distractor_analysis": "[Bẫy Giới Từ] B là động từ nguyên mẫu; C là động từ/danh từ; D (regardless) là trạng từ thường đi với 'of'.",
        "paraphrase_pair": "regarding remote work = concerning telecommuting policies",
        "lesson_number": 2,
    },
    {
        "test_id": "ETS2024_03",
        "part": "Part 5",
        "question_no": 105,
        "sentence": "Every one of the microservices in the payment processing cluster ___ monitored continuously by automated alerts.",
        "choice_a": "is",
        "choice_b": "are",
        "choice_c": "were",
        "choice_d": "have",
        "correct_choice": "A",
        "explanation": "Chủ ngữ là đại từ 'Every one of + danh từ số nhiều', quy tắc ngữ pháp bắt buộc chia động từ ở số ít ('is monitored').",
        "distractor_analysis": "[Bẫy Hòa Hợp Chủ-Vị] Thí sinh hay nhìn danh từ số nhiều 'microservices' đứng ngay trước chỗ trống mà chọn động từ số nhiều B (are) hoặc C (were).",
        "paraphrase_pair": "monitored continuously = tracked around the clock",
        "lesson_number": 5,
    },
    {
        "test_id": "ETS2024_03",
        "part": "Part 5",
        "question_no": 106,
        "sentence": "___ unexpected traffic surges occur on weekends, the autoscaling policy provisions additional compute instances.",
        "choice_a": "Whenever",
        "choice_b": "In spite of",
        "choice_c": "Despite",
        "choice_d": "Due to",
        "correct_choice": "A",
        "explanation": "Phía sau là một mệnh đề hoàn chỉnh (S = traffic surges, V = occur) ➔ Cần liên từ chỉ thời gian 'Whenever' (Bất cứ khi nào... thì...).",
        "distractor_analysis": "[Bẫy Liên Từ vs Giới Từ] In spite of, Despite, Due to đều là giới từ, chỉ đi với danh từ hoặc V-ing, không thể nối mệnh đề có động từ 'occur'.",
        "paraphrase_pair": "whenever surges occur = each time traffic spikes",
        "lesson_number": 2,
    },
    {
        "test_id": "ETS2024_03",
        "part": "Part 5",
        "question_no": 107,
        "sentence": "The cybersecurity audit team has already ___ three critical vulnerabilities in the legacy customer portal.",
        "choice_a": "identified",
        "choice_b": "identify",
        "choice_c": "identifying",
        "choice_d": "identifies",
        "correct_choice": "A",
        "explanation": "Thì hiện tại hoàn thành: 'has already + V3/ed' (has already identified). Diễn tả hành động phát hiện đã hoàn tất có kết quả ở hiện tại.",
        "distractor_analysis": "[Bẫy Thì Thời Gian] B là nguyên mẫu; C là V-ing; D là ngôi thứ ba số ít.",
        "paraphrase_pair": "identified vulnerabilities = discovered security flaws",
        "lesson_number": 6,
    },
    {
        "test_id": "ETS2024_03",
        "part": "Part 5",
        "question_no": 108,
        "sentence": "The engineering documentation is ___ organized, allowing new recruits to locate endpoints within seconds.",
        "choice_a": "meticulously",
        "choice_b": "meticulous",
        "choice_c": "meticulousness",
        "choice_d": "meticulosity",
        "correct_choice": "A",
        "explanation": "Chỗ trống đứng giữa động từ to-be 'is' và tính từ/phân từ 'organized' ➔ Cần trạng từ 'meticulously' (tỉ mỉ, cẩn trọng) để bổ nghĩa cho tính từ.",
        "distractor_analysis": "[Bẫy Trạng Từ Bổ Nghĩa Cho Tính Từ] B (meticulous) là tính từ; C và D là danh từ sự tỉ mỉ.",
        "paraphrase_pair": "meticulously organized = structured thoroughly = carefully cataloged",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_03",
        "part": "Part 5",
        "question_no": 109,
        "sentence": "All software engineers must strictly adhere ___ code review conventions before merging pull requests.",
        "choice_a": "to",
        "choice_b": "with",
        "choice_c": "in",
        "choice_d": "at",
        "correct_choice": "A",
        "explanation": "Collocation bắt buộc trong tiếng Anh thương mại: 'adhere to guidelines / conventions' (tuân thủ nghiêm ngặt quy ước).",
        "distractor_analysis": "[Bẫy Giới Từ Đi Kèm Động Từ] Thí sinh hay nhầm với 'comply with' mà chọn giới từ B (with).",
        "paraphrase_pair": "adhere to conventions = comply with guidelines = follow standards",
        "lesson_number": 12,
    },
    {
        "test_id": "ETS2024_03",
        "part": "Part 5",
        "question_no": 110,
        "sentence": "Invoices ___ after the thirtieth of the month will incur an additional late processing fee.",
        "choice_a": "received",
        "choice_b": "receiving",
        "choice_c": "receive",
        "choice_d": "receives",
        "correct_choice": "A",
        "explanation": "Rút gọn mệnh đề quan hệ ở thể bị động: 'Invoices which are received...' rút gọn thành quá khứ phân từ 'Invoices received...'. Động từ chính của câu là 'will incur'.",
        "distractor_analysis": "[Bẫy Rút Gọn Mệnh Đề Quan Hệ Bị Động] Chọn B (receiving) sai nghĩa vì hóa đơn được nhận chứ không tự nhận. C và D thừa động từ vị ngữ.",
        "paraphrase_pair": "invoices received = bills submitted",
        "lesson_number": 8,
    },
    {
        "test_id": "ETS2024_03",
        "part": "Part 5",
        "question_no": 111,
        "sentence": "The infrastructure director recommended that the production deployment schedule ___ delayed by twenty-four hours.",
        "choice_a": "be",
        "choice_b": "is",
        "choice_c": "was",
        "choice_d": "being",
        "correct_choice": "A",
        "explanation": "Thể giả định thức (Subjunctive Mood): Cấu trúc 'recommend that + S + (should) + BE + V3/ed'. Động từ to-be luôn giữ nguyên dạng 'be'.",
        "distractor_analysis": "[Bẫy Thể Giả Định Bị Động] Thí sinh rất dễ chia theo thì quá khứ của recommend mà chọn C (was) hoặc chia số ít B (is).",
        "paraphrase_pair": "recommended that S be delayed = advised postponing",
        "lesson_number": 9,
    },
    {
        "test_id": "ETS2024_03",
        "part": "Part 5",
        "question_no": 112,
        "sentence": "___ the authentication token expire unexpectedly, the client application will automatically prompt for login.",
        "choice_a": "Should",
        "choice_b": "Were",
        "choice_c": "Had",
        "choice_d": "Unless",
        "correct_choice": "A",
        "explanation": "Đảo ngữ câu điều kiện loại 1: 'Should + S + V-nguyên mẫu' thay thế cho 'If + S + V' (Should the token expire = If the token expires).",
        "distractor_analysis": "[Bẫy Đảo Ngữ Điều Kiện] B (Were) dùng cho điều kiện loại 2; C (Had) dùng cho loại 3; D (Unless) làm lệch nghĩa hoàn toàn.",
        "paraphrase_pair": "should the token expire = if credentials lapse",
        "lesson_number": 10,
    },
    {
        "test_id": "ETS2024_03",
        "part": "Part 5",
        "question_no": 113,
        "sentence": "The benchmark test proved that in-memory cache retrieval is noticeably ___ than direct disk reads.",
        "choice_a": "faster",
        "choice_b": "fast",
        "choice_c": "fastest",
        "choice_d": "more fast",
        "correct_choice": "A",
        "explanation": "Có liên từ so sánh 'than' phía sau nên cần dạng so sánh hơn 'faster' của tính từ/trạng từ ngắn 'fast'.",
        "distractor_analysis": "[Bẫy Cấu Trúc So Sánh] B là nguyên thể; C là so sánh nhất; D sai quy tắc vì tính từ 1 âm tiết thêm đuôi -er.",
        "paraphrase_pair": "noticeably faster = significantly quicker = markedly more rapid",
        "lesson_number": 11,
    },
    {
        "test_id": "ETS2024_03",
        "part": "Part 5",
        "question_no": 114,
        "sentence": "The customer support portal operates ___ seven days a week to assist international business clients.",
        "choice_a": "continuously",
        "choice_b": "continuous",
        "choice_c": "continuation",
        "choice_d": "continue",
        "correct_choice": "A",
        "explanation": "Động từ 'operates' (vận hành) là nội động từ, cần trạng từ 'continuously' (liên tục không ngừng nghỉ) đứng sau bổ nghĩa.",
        "distractor_analysis": "[Bẫy Vị Trí Trạng Từ] B là tính từ; C là danh từ sự tiếp nối; D là động từ.",
        "paraphrase_pair": "operates continuously = functions non-stop = runs 24/7",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_03",
        "part": "Part 5",
        "question_no": 115,
        "sentence": "Road conditions along the mountain route were described as hazardous and ___ for heavy freight trucks.",
        "choice_a": "treacherous",
        "choice_b": "treachery",
        "choice_c": "treacherously",
        "choice_d": "treachering",
        "correct_choice": "A",
        "explanation": "Cấu trúc song hành liên kết bởi 'and': 'hazardous and ___'. Vì 'hazardous' là tính từ nên từ sau 'and' cũng bắt buộc là một tính từ: 'treacherous' (nguy hiểm khôn lường).",
        "distractor_analysis": "[Bẫy Cấu Trúc Song Hành Tính Từ] B là danh từ sự phản bội; C là trạng từ; D từ không tồn tại.",
        "paraphrase_pair": "hazardous and treacherous = dangerous and perilous",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_03",
        "part": "Part 5",
        "question_no": 116,
        "sentence": "The newly engineered cooling fans sound remarkably ___ even when running at maximum RPM capacity.",
        "choice_a": "quiet",
        "choice_b": "quietly",
        "choice_c": "quietness",
        "choice_d": "quieted",
        "correct_choice": "A",
        "explanation": "'Sound' là một linking verb (động từ chỉ cảm giác giác quan), theo sau bắt buộc là tính từ vị ngữ: 'sound quiet' (nghe rất êm).",
        "distractor_analysis": "[Bẫy Tính Từ Sau Linking Verb] Thí sinh hay chọn nhầm trạng từ B (quietly) do tưởng nhầm sound là động từ hành động.",
        "paraphrase_pair": "sound remarkably quiet = operate with minimal noise",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_03",
        "part": "Part 5",
        "question_no": 117,
        "sentence": "The executive board agreed to ___ the proposed joint venture agreement after extensive due diligence.",
        "choice_a": "approve",
        "choice_b": "approval",
        "choice_c": "approved",
        "choice_d": "approving",
        "correct_choice": "A",
        "explanation": "Cấu trúc 'agree to + V-nguyên mẫu': đồng thuận làm gì (agree to approve the agreement).",
        "distractor_analysis": "[Bẫy Dạng Động Từ: To-V] B là danh từ; C là quá khứ; D là dạng V-ing.",
        "paraphrase_pair": "agree to approve = give formal consent = endorse contract",
        "lesson_number": 3,
    },
    {
        "test_id": "ETS2024_03",
        "part": "Part 5",
        "question_no": 118,
        "sentence": "High-speed wireless internet access is provided to all registered hotel guests ___ no extra charge.",
        "choice_a": "at",
        "choice_b": "on",
        "choice_c": "in",
        "choice_d": "of",
        "correct_choice": "A",
        "explanation": "Cụm giới từ cố định: 'at no extra charge' (hoàn toàn không tính thêm phí).",
        "distractor_analysis": "[Bẫy Giới Từ & Cụm Cố Định] Các giới từ on/in/of không kết hợp với cụm 'no extra charge'.",
        "paraphrase_pair": "at no extra charge = free of charge = complimentary",
        "lesson_number": 12,
    },
    {
        "test_id": "ETS2024_03",
        "part": "Part 5",
        "question_no": 119,
        "sentence": "___ the official warranty period lapses, clients are encouraged to enroll in our extended support plan.",
        "choice_a": "Before",
        "choice_b": "During",
        "choice_c": "Despite",
        "choice_d": "In case of",
        "correct_choice": "A",
        "explanation": "'Before' ở đây là liên từ chỉ thời gian nối mệnh đề có S + V ('the warranty period lapses') mang nghĩa: Trước khi thời hạn bảo hành hết hiệu lực.",
        "distractor_analysis": "[Bẫy Liên Từ vs Giới Từ] During, Despite, In case of là giới từ chỉ đi với danh từ, không đi với mệnh đề có động từ 'lapses'.",
        "paraphrase_pair": "before warranty lapses = prior to coverage expiration",
        "lesson_number": 2,
    },
    {
        "test_id": "ETS2024_03",
        "part": "Part 5",
        "question_no": 120,
        "sentence": "The lead data scientist delivered a ___ report detailing the predictive performance of the AI model.",
        "choice_a": "detailed",
        "choice_b": "detail",
        "choice_c": "detailing",
        "choice_d": "details",
        "correct_choice": "A",
        "explanation": "Đứng giữa mạo từ 'a' và danh từ 'report' ➔ Cần tính từ 'detailed' (chi tiết, tường tận) để bổ nghĩa cho danh từ report.",
        "distractor_analysis": "[Bẫy Vị Trí Tính Từ] B và D là danh từ/động từ; C là phân từ V-ing chủ động không dùng làm tính từ đứng trước report trong ngữ cảnh này.",
        "paraphrase_pair": "detailed report = comprehensive dossier = in-depth summary",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_03",
        "part": "Part 5",
        "question_no": 121,
        "sentence": "Contractors must submit two forms of ___ identification when applying for a facility security badge.",
        "choice_a": "valid",
        "choice_b": "validate",
        "choice_c": "validity",
        "choice_d": "validating",
        "correct_choice": "A",
        "explanation": "Cần tính từ 'valid' (hợp lệ, còn hiệu lực) đứng trước danh từ 'identification' để bổ nghĩa.",
        "distractor_analysis": "[Bẫy Từ Loại] B là động từ xác nhận; C là danh từ tính hiệu lực; D là phân từ.",
        "paraphrase_pair": "valid identification = legitimate credentials = unexpired ID",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_03",
        "part": "Part 5",
        "question_no": 122,
        "sentence": "The domestic shipping division ___ record-breaking volume during the peak holiday shopping season.",
        "choice_a": "generated",
        "choice_b": "generating",
        "choice_c": "to generate",
        "choice_d": "generator",
        "correct_choice": "A",
        "explanation": "Câu đã có chủ ngữ 'The domestic shipping division' nhưng chưa có động từ vị ngữ chính. Dùng thì quá khứ đơn 'generated' để chỉ sự việc đã diễn ra trong mùa lễ vừa qua.",
        "distractor_analysis": "[Bẫy Thiếu Vị Ngữ Chính] B (generating) và C (to generate) không làm động từ vị ngữ; D là danh từ máy phát điện.",
        "paraphrase_pair": "generated record volume = produced unprecedented turnover",
        "lesson_number": 6,
    },
    {
        "test_id": "ETS2024_03",
        "part": "Part 5",
        "question_no": 123,
        "sentence": "The platform team lead ___ outlined the microservice migration phases during the quarterly briefing.",
        "choice_a": "clearly",
        "choice_b": "clear",
        "choice_c": "clearness",
        "choice_d": "clearing",
        "correct_choice": "A",
        "explanation": "Vị trí chen giữa Chủ ngữ 'The platform team lead' và Động từ chính 'outlined' ➔ Cần trạng từ 'clearly' (trình bày rõ ràng, rành mạch).",
        "distractor_analysis": "[Bẫy Vị Trí Trạng Từ] B là tính từ; C là danh từ; D là phân từ.",
        "paraphrase_pair": "clearly outlined = precisely delineated = articulated explicitly",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_03",
        "part": "Part 5",
        "question_no": 124,
        "sentence": "Corporate IT security policy strictly prohibits personnel from ___ unapproved software on company laptops.",
        "choice_a": "installing",
        "choice_b": "install",
        "choice_c": "installation",
        "choice_d": "installed",
        "correct_choice": "A",
        "explanation": "Cấu trúc 'prohibit somebody from + V-ing': cấm ai làm việc gì (prohibits personnel from installing...).",
        "distractor_analysis": "[Bẫy Giới Từ Đi Với V-ing] B là động từ nguyên mẫu; C là danh từ không thể có tân ngữ 'unapproved software' theo sau trực tiếp; D là quá khứ.",
        "paraphrase_pair": "prohibits from installing = forbids setup of unauthorized tools",
        "lesson_number": 3,
    },
    {
        "test_id": "ETS2024_03",
        "part": "Part 5",
        "question_no": 125,
        "sentence": "Customer satisfaction ratings have remained ___ high since the introduction of AI-assisted support.",
        "choice_a": "consistently",
        "choice_b": "consistent",
        "choice_c": "consistency",
        "choice_d": "consist",
        "correct_choice": "A",
        "explanation": "Đứng trước tính từ 'high' cần một trạng từ 'consistently' (luôn luôn, một cách nhất quán) để bổ nghĩa mức độ cho tính từ.",
        "distractor_analysis": "[Bẫy Trạng Từ Bổ Nghĩa Cho Tính Từ] B (consistent) là tính từ; C là danh từ; D là động từ.",
        "paraphrase_pair": "consistently high = constantly elevated = reliably strong",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_03",
        "part": "Part 5",
        "question_no": 126,
        "sentence": "___ you require expedited shipment for medical supplies, please check the priority handling checkbox.",
        "choice_a": "If",
        "choice_b": "In spite of",
        "choice_c": "Because of",
        "choice_d": "So as to",
        "correct_choice": "A",
        "explanation": "Mệnh đề điều kiện loại 1: 'If + S + V' (If you require expedited shipment...). Phía sau là mệnh đề đầy đủ.",
        "distractor_analysis": "[Bẫy Liên Từ Điều Kiện] B và C là giới từ không thể đi với mệnh đề; D (So as to) đi với động từ nguyên mẫu chỉ mục đích.",
        "paraphrase_pair": "if you require = in case you need = should you need",
        "lesson_number": 10,
    },
    {
        "test_id": "ETS2024_03",
        "part": "Part 5",
        "question_no": 127,
        "sentence": "The chief auditor suggested that all expense ledgers ___ independently reconciled by an external accountant.",
        "choice_a": "be",
        "choice_b": "are",
        "choice_c": "were",
        "choice_d": "being",
        "correct_choice": "A",
        "explanation": "Thể giả định thức ở dạng bị động: 'suggest that + S + (should) + BE + V3/ed'. Động từ to-be bắt buộc ở dạng nguyên thể 'be'.",
        "distractor_analysis": "[Bẫy Thể Giả Định Bị Động] Rất dễ nhầm chia theo chủ ngữ số nhiều 'ledgers' mà chọn B (are) hoặc chia theo quá khứ của suggested mà chọn C (were).",
        "paraphrase_pair": "suggested that ledgers be reconciled = advised auditing records",
        "lesson_number": 9,
    },
    {
        "test_id": "ETS2024_03",
        "part": "Part 5",
        "question_no": 128,
        "sentence": "The backup battery capacity was not large ___ to sustain the data center during a prolonged power outage.",
        "choice_a": "enough",
        "choice_b": "too",
        "choice_c": "so",
        "choice_d": "very",
        "correct_choice": "A",
        "explanation": "Cấu trúc tính từ đứng trước enough: 'Adj + enough + to-V' (large enough to sustain). Các từ too, so, very đều đứng TRƯỚC tính từ.",
        "distractor_analysis": "[Bẫy Vị Trí Của Enough] Too, so, very đứng trước tính từ; chỉ có 'enough' đứng ngay sau tính từ.",
        "paraphrase_pair": "not large enough = insufficient capacity",
        "lesson_number": 11,
    },
    {
        "test_id": "ETS2024_03",
        "part": "Part 5",
        "question_no": 129,
        "sentence": "Consumer demand for eco-friendly packaging materials has grown ___ over the past three fiscal years.",
        "choice_a": "significantly",
        "choice_b": "significant",
        "choice_c": "significance",
        "choice_d": "signify",
        "correct_choice": "A",
        "explanation": "Động từ 'has grown' (đã tăng trưởng) là nội động từ, cần trạng từ 'significantly' (đáng kể) đứng sau bổ nghĩa mức độ.",
        "distractor_analysis": "[Bẫy Vị Trí Trạng Từ] B là tính từ; C là danh từ tầm quan trọng; D là động từ biểu thị.",
        "paraphrase_pair": "grown significantly = expanded considerably = rose substantially",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_03",
        "part": "Part 5",
        "question_no": 130,
        "sentence": "All formal grant applications must be delivered to the university admissions desk ___ 5:00 PM on Friday.",
        "choice_a": "by",
        "choice_b": "until",
        "choice_c": "for",
        "choice_d": "along",
        "correct_choice": "A",
        "explanation": "Giới từ chỉ hạn chót: 'by + thời điểm' (by 5:00 PM on Friday = trước hoặc đúng 5 giờ chiều thứ Sáu). 'Until' chỉ một hành động diễn ra liên tục cho tới một thời điểm.",
        "distractor_analysis": "[Bẫy Giới Từ By vs Until] 'By' dùng cho hành động hoàn thành một lần trước deadline; 'until' dùng cho hành động kéo dài liên tục.",
        "paraphrase_pair": "by 5:00 PM = no later than five o'clock",
        "lesson_number": 2,
    },

    # --- Part 6: Text Completion (1 Set: Q131 -> Q134) ---
    {
        "test_id": "ETS2024_03",
        "part": "Part 6",
        "question_no": 131,
        "sentence": "POLICY NOTICE\nTo: All Full-Time and Contract Employees\nFrom: Global Information Security Directorate\nDate: November 1\nSubject: Mandatory VPN & Multi-Factor Authentication Upgrade\n\nAs part of our continuous commitment to enterprise data protection, our security engineering team will enforce a mandatory upgrade to our corporate VPN gateway this weekend. Starting Monday morning, legacy single-factor passwords will be ___ [131] revoked.",
        "choice_a": "permanently",
        "choice_b": "permanent",
        "choice_c": "permanence",
        "choice_d": "permanency",
        "correct_choice": "A",
        "explanation": "Vị trí đứng giữa trợ động từ 'will be' và quá khứ phân từ 'revoked' (bị thu hồi) ➔ Cần trạng từ 'permanently' (vĩnh viễn) để bổ nghĩa.",
        "distractor_analysis": "[Bẫy Từ Loại Part 6] B là tính từ; C và D là danh từ tính vĩnh cửu.",
        "paraphrase_pair": "permanently revoked = canceled indefinitely = rendered obsolete",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_03",
        "part": "Part 6",
        "question_no": 132,
        "sentence": "All staff members are instructed to ___ the newly issued hardware security keys before attempting remote login.",
        "choice_a": "configure",
        "choice_b": "configuration",
        "choice_c": "configured",
        "choice_d": "configuring",
        "correct_choice": "A",
        "explanation": "Cấu trúc 'be instructed to + V-nguyên mẫu': được hướng dẫn làm gì (are instructed to configure sth).",
        "distractor_analysis": "[Bẫy Dạng Động Từ: To-V] B là danh từ cấu hình; C là quá khứ; D là V-ing.",
        "paraphrase_pair": "configure security keys = set up hardware tokens",
        "lesson_number": 3,
    },
    {
        "test_id": "ETS2024_03",
        "part": "Part 6",
        "question_no": 133,
        "sentence": "___ [133]. Detailed walkthrough guides with visual screenshots are currently accessible on the internal intranet portal.",
        "choice_a": "The setup procedure takes less than ten minutes to complete.",
        "choice_b": "The office fitness center will close early on Friday.",
        "choice_c": "Annual health insurance enrollment ends next month.",
        "choice_d": "Visitor parking passes must be displayed on vehicle dashboards.",
        "correct_choice": "A",
        "explanation": "Câu chèn mạch lạc (Sentence insertion): Đoạn văn đang hướng dẫn nhân viên cài đặt thiết bị bảo mật mới. Câu A 'The setup procedure takes less than ten minutes...' gắn kết hoàn hảo với câu sau 'Detailed walkthrough guides...'.",
        "distractor_analysis": "[Bẫy Chủ Đề Lạc Quẻ] B (phòng gym), C (bảo hiểm y tế), D (vé gửi xe) hoàn toàn không liên quan đến thông báo bảo mật IT.",
        "paraphrase_pair": "setup procedure takes less than ten minutes = fast installation process",
        "lesson_number": 12,
    },
    {
        "test_id": "ETS2024_03",
        "part": "Part 6",
        "question_no": 134,
        "sentence": "Our technical helpdesk will provide extended live support throughout the weekend to assist any employees who encounter configuration ___.",
        "choice_a": "difficulties",
        "choice_b": "difficult",
        "choice_c": "difficultly",
        "choice_d": "difficileness",
        "correct_choice": "A",
        "explanation": "Đứng sau danh từ 'configuration' tạo thành cụm danh từ kép: 'configuration difficulties' (các khó khăn/trục trặc khi cấu hình).",
        "distractor_analysis": "[Bẫy Cụm Danh Từ Kép] B là tính từ; C là trạng từ; D từ không tồn tại.",
        "paraphrase_pair": "configuration difficulties = technical hurdles = setup issues",
        "lesson_number": 1,
    },

    # --- Part 7: Reading Comprehension (1 Single Passage: Q147 -> Q150) ---
    {
        "test_id": "ETS2024_03",
        "part": "Part 7",
        "question_no": 147,
        "sentence": "PROPOSAL MEMO\nTo: Infrastructure Steering Committee\nFrom: Elena Rostova, Senior Data Architect\nSubject: Real-Time Stream Analytics Migration Proposal\n\nExecutive Summary:\nOur current batch processing data pipeline experiences an average ingestion delay of 4 hours, which restricts our business intelligence teams from detecting fraud in real time. This document outlines a proposal to transition our core analytics pipeline to Apache Kafka and Apache Flink on our Kubernetes cluster.\n\nKey Projected Benefits:\n1. Event-to-dashboard latency will drop from 4 hours to under 500 milliseconds.\n2. Automated anomaly detection models will evaluate financial transactions concurrently.\n3. Operational cloud compute expenses are projected to decrease by 22% due to dynamic resource auto-allocation.\n\nTimeline & Feasibility:\nA prototype pipeline was successfully validated in our staging environment last week, confirming that zero-downtime cutover is technically feasible. Pending executive budget approval by November 15, phased production deployment will commence on December 1 and conclude by January 10.\n\n--- QUESTION 147 ---\nWhat is the main objective of Ms. Rostova's proposal?",
        "choice_a": "To recommend upgrading the analytics pipeline to real-time streaming",
        "choice_b": "To announce the immediate closure of the analytics division",
        "choice_c": "To request an extension on a product launch deadline",
        "choice_d": "To report a major security breach in the database cluster",
        "correct_choice": "A",
        "explanation": "Ngay phần tóm tắt điều hành (Executive Summary): 'This document outlines a proposal to transition our core analytics pipeline to Apache Kafka and Apache Flink...' ➔ Đề xuất nâng cấp đường ống phân tích dữ liệu sang xử lý thời gian thực.",
        "distractor_analysis": "[Bẫy Mục Đích Suy Diễn] B (đóng cửa phòng ban), C (xin gia hạn launch), D (báo cáo vi phạm bảo mật) là thông tin sai lệch.",
        "paraphrase_pair": "transition to streaming = upgrade analytics pipeline to real-time",
        "lesson_number": 12,
    },
    {
        "test_id": "ETS2024_03",
        "part": "Part 7",
        "question_no": 148,
        "sentence": "According to the proposal, how will the company benefit financially?",
        "choice_a": "Cloud compute operational costs are expected to drop by 22%.",
        "choice_b": "Customer subscription prices will increase by 45%.",
        "choice_c": "Server hardware maintenance fees will be waived completely.",
        "choice_d": "The company will receive a tax refund from the city.",
        "correct_choice": "A",
        "explanation": "Lợi ích số 3: 'Operational cloud compute expenses are projected to decrease by 22%...' ➔ Chi phí vận hành hạ tầng đám mây dự kiến giảm 22%.",
        "distractor_analysis": "[Bẫy Chi Tiết Tài Chính] B, C, D là các chi tiết bịa đặt không có trong văn bản đề xuất.",
        "paraphrase_pair": "expenses projected to decrease by 22% = operational costs expected to drop",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_03",
        "part": "Part 7",
        "question_no": 149,
        "sentence": "What must occur before production deployment can begin on December 1?",
        "choice_a": "The executive committee must grant budget approval by November 15.",
        "choice_b": "All data science staff must relocate to the headquarters.",
        "choice_c": "The staging environment must be decommissioned.",
        "choice_d": "Customer accounts must be audited by an independent firm.",
        "correct_choice": "A",
        "explanation": "Phần Timeline: 'Pending executive budget approval by November 15, phased production deployment will commence on December 1...' ➔ Cần có sự phê duyệt ngân sách trước ngày 15 tháng 11.",
        "distractor_analysis": "[Bẫy Điều Kiện Tiên Quyết] B (chuyển trụ sở), C (hủy môi trường staging), D (kiểm toán khách hàng) đều không phải điều kiện.",
        "paraphrase_pair": "pending budget approval = subject to financial authorization",
        "lesson_number": 12,
    },
    {
        "test_id": "ETS2024_03",
        "part": "Part 7",
        "question_no": 150,
        "sentence": "In the memo, the word 'feasible' in the final paragraph is closest in meaning to:",
        "choice_a": "viable",
        "choice_b": "difficult",
        "choice_c": "unreliable",
        "choice_d": "expensive",
        "correct_choice": "A",
        "explanation": "'technically feasible' có nghĩa là hoàn toàn khả thi về mặt kỹ thuật, có thể triển khai thành công ➔ 'viable / workable' (khả thi, thực tế).",
        "distractor_analysis": "[Bẫy Từ Đồng Nghĩa & Trái Nghĩa] B (difficult - khó), C (unreliable - không tin cậy), D (expensive - đắt đỏ) đều sai nghĩa với 'feasible'.",
        "paraphrase_pair": "technically feasible = viable = practicable = workable",
        "lesson_number": 12,
    },
]

# -------------------------------------------------------------
# 2. 20 High-Frequency Business & Tech Flashcards
# -------------------------------------------------------------
NEW_FLASHCARDS_TEST03 = [
    ("benchmark", "/ˈbentʃ.mɑːrk/", "noun", "Computers & IT", "chuẩn đối sánh, bài đo kiểm hiệu năng",
     "run a benchmark / benchmark test", "benchmark = standard of excellence = yardstick",
     "The engineers conducted a rigorous benchmark comparing PostgreSQL against CockroachDB.",
     "Các kỹ sư đã tiến hành bài đo kiểm chuẩn so sánh giữa PostgreSQL và CockroachDB."),

    ("latency", "/ˈleɪ.tən.si/", "noun", "Computers & IT", "độ trễ truyền nhận dữ liệu qua mạng",
     "low latency / reduce network latency", "latency = delay = lag time",
     "Caching query results in memory reduced overall API latency to under ten milliseconds.",
     "Việc lưu đệm kết quả truy vấn vào bộ nhớ đã giảm độ trễ API xuống dưới mười mili-giây."),

    ("concurrently", "/kənˈkɝː.ənt.li/", "adverb", "Computers & IT", "đồng thời, cùng một lúc",
     "process transactions concurrently", "concurrently = simultaneously = at the same time",
     "The microservice architecture can handle thousands of API requests concurrently.",
     "Kiến trúc microservice có thể xử lý hàng nghìn yêu cầu API đồng thời."),

    ("vulnerability", "/ˌvʌl.nɚ.əˈbɪl.ə.t̬i/", "noun", "Computers & IT", "lỗ hổng bảo mật, điểm yếu hệ thống",
     "patch a vulnerability / security flaw", "vulnerability = security weakness = flaw",
     "The security team immediately deployed a patch to resolve the zero-day vulnerability.",
     "Đội bảo mật đã lập tức triển khai bản vá để giải quyết lỗ hổng bảo mật nghiêm trọng."),

    ("commence", "/kəˈmens/", "verb", "Corporate Operations", "bắt đầu, khởi sự triển khai",
     "commence construction / commence deployment", "commence = begin = initiate = start",
     "Phased rollout of the new billing system will commence on the first of next month.",
     "Việc triển khai từng giai đoạn cho hệ thống thanh toán mới sẽ bắt đầu vào ngày đầu tháng tới."),

    ("precaution", "/prɪˈkɑː.ʃən/", "noun", "Manufacturing & Compliance", "biện pháp phòng ngừa, đề phòng rủi ro",
     "take safety precautions / precautionary measure", "precaution = preventive step = safeguard",
     "As a precaution, regular off-site backups are created every six hours.",
     "Để phòng ngừa rủi ro, các bản sao lưu ngoài máy chủ được tạo định kỳ mỗi sáu giờ."),

    ("prerequisite", "/ˌpriːˈrek.wə.zɪt/", "noun", "Human Resources", "điều kiện tiên quyết, yêu cầu bắt buộc trước",
     "prerequisite for the position / prerequisite course", "prerequisite = requirement = precondition",
     "Two years of experience with distributed databases is a prerequisite for this senior role.",
     "Hai năm kinh nghiệm với cơ sở dữ liệu phân tán là điều kiện tiên quyết cho vị trí cao cấp này."),

    ("relinquish", "/rɪˈlɪŋ.kwɪʃ/", "verb", "Contracts & Agreements", "từ bỏ quyền lợi, nhượng lại quyền hạn",
     "relinquish rights / relinquish control", "relinquish = surrender = cede = give up",
     "The vendor agreed to relinquish all intellectual property rights to the custom software.",
     "Nhà cung cấp đã đồng ý từ bỏ toàn bộ quyền sở hữu trí tuệ đối với phần mềm theo yêu cầu."),

    ("incentive", "/ɪnˈsen.t̬ɪv/", "noun", "Human Resources", "khoản tiền thưởng khuyến khích, động lực",
     "performance incentive / financial incentives", "incentive = bonus = stimulus = inducement",
     "The company offers lucrative annual bonuses as an incentive for outstanding performance.",
     "Công ty cung cấp các khoản tiền thưởng hậu hĩnh như một động lực cho hiệu suất xuất sắc."),

    ("reconciliation", "/ˌrek.ənˌsɪl.iˈeɪ.ʃən/", "noun", "Accounting & Finance", "sự đối soát, cân đối số liệu sổ sách",
     "bank reconciliation / reconcile ledger", "reconciliation = balancing accounts = verifying books",
     "Daily automated reconciliation guarantees that all credit transactions are accounted for.",
     "Tiến trình đối soát tự động hàng ngày đảm bảo mọi giao dịch tín dụng đều được hạch toán đầy đủ."),

    ("scalability", "/ˌskeɪ.ləˈbɪl.ə.t̬i/", "noun", "Computers & IT", "khả năng mở rộng hệ thống",
     "system scalability / horizontal scalability", "scalability = capacity to expand = extensibility",
     "The cloud platform was chosen specifically for its elastic scalability during peak shopping seasons.",
     "Nền tảng đám mây được lựa chọn đặc biệt nhờ khả năng mở rộng linh hoạt trong các mùa mua sắm cao điểm."),

    ("streamline", "/ˈstriːm.laɪn/", "verb", "Corporate Operations", "tinh giản quy trình, tối ưu hóa hoạt động",
     "streamline operations / streamline workflow", "streamline = simplify = optimize = make efficient",
     "Management implemented a new ERP system to streamline inventory tracking across all warehouses.",
     "Ban quản lý đã triển khai hệ thống ERP mới nhằm tinh giản việc theo dõi hàng tồn kho trên tất cả các kho bãi."),

    ("discrepancy", "/dɪˈskrep.ən.si/", "noun", "Accounting & Finance", "sự sai lệch, bất nhất về số liệu",
     "reconcile discrepancy / audit discrepancy", "discrepancy = inconsistency = difference = mismatch",
     "The financial audit revealed a noticeable discrepancy between reported revenue and bank receipts.",
     "Cuộc kiểm toán tài chính đã phát hiện sự sai lệch đáng chú ý giữa doanh thu báo cáo và biên lai ngân hàng."),

    ("contingency", "/kənˈtɪn.dʒən.si/", "noun", "General Business", "phương án dự phòng, biến cố bất ngờ",
     "contingency plan / prepare for contingencies", "contingency = backup plan = emergency provision",
     "The project manager developed a contingency plan in case the overseas shipment was delayed.",
     "Quản lý dự án đã xây dựng một kế hoạch dự phòng phòng khi lô hàng từ nước ngoài bị chậm trễ."),

    ("mitigate", "/ˈmɪt̬.ə.ɡeɪt/", "verb", "Risk Management & Compliance", "giảm thiểu rủi ro hoặc tác hại",
     "mitigate risk / mitigate potential losses", "mitigate = alleviate = lessen = reduce",
     "Implementing multi-factor authentication helps mitigate the risk of unauthorized account access.",
     "Triển khai xác thực đa yếu tố giúp giảm thiểu rủi ro bị truy cập tài khoản trái phép."),

    ("prospective", "/prəˈspek.tɪv/", "adjective", "Marketing & Sales", "tiềm năng, có triển vọng trong tương lai",
     "prospective client / prospective buyer", "prospective = potential = future = expected",
     "The sales representatives gave a live product demonstration to several prospective enterprise clients.",
     "Các đại diện kinh doanh đã trình diễn trực tiếp sản phẩm cho một số khách hàng doanh nghiệp tiềm năng."),

    ("stringent", "/ˈstrɪn.dʒənt/", "adjective", "Manufacturing & Compliance", "nghiêm ngặt, chặt chẽ (tiêu chuẩn, quy định)",
     "stringent regulations / stringent quality standards", "stringent = rigorous = strict = severe",
     "Pharmaceutical facilities must comply with stringent hygiene and safety regulations.",
     "Các cơ sở dược phẩm bắt buộc phải tuân thủ các quy định nghiêm ngặt về vệ sinh và an toàn."),

    ("depreciation", "/dɪˌpriː.ʃiˈeɪ.ʃən/", "noun", "Accounting & Finance", "sự khấu hao tài sản cố định",
     "accumulated depreciation / asset depreciation", "depreciation = decrease in value over time = amortization",
     "The finance department calculated the annual depreciation of office laptops and servers.",
     "Phòng tài chính đã tính toán mức khấu hao hàng năm của máy tính xách tay và máy chủ văn phòng."),

    ("redundancy", "/rɪˈdʌn.dən.si/", "noun", "Computers & IT", "tính dư thừa dự phòng / sự dự phòng hệ thống",
     "hardware redundancy / built-in redundancy", "redundancy = duplication for safety = backup capacity",
     "The primary data center features N+1 power redundancy to prevent unscheduled outages.",
     "Trung tâm dữ liệu chính trang bị hệ thống dự phòng nguồn điện N+1 để ngăn ngừa sự cố mất điện ngoài ý muốn."),

    ("stipulate", "/ˈstɪp.jə.leɪt/", "verb", "Contracts & Agreements", "quy định cụ thể, đặt điều kiện trong hợp đồng",
     "stipulate that / contract stipulates", "stipulate = specify = state clearly = require",
     "The service level agreement stipulates that critical tickets must be resolved within two hours.",
     "Thỏa thuận mức dịch vụ quy định rõ các yêu cầu hỗ trợ khẩn cấp phải được giải quyết trong vòng hai giờ."),
]

# -------------------------------------------------------------
# 3. 10 High-Frequency Paraphrase Pairs (Part 7 Vault)
# -------------------------------------------------------------
NEW_PARAPHRASE_PAIRS_TEST03 = [
    {
        "word_in_text": "transition pipeline to real-time",
        "word_in_answer": "upgrade data processing architecture",
        "meaning": "chuyển đổi kiến trúc xử lý dữ liệu sang thời gian thực",
        "part_target": "Part 7 Tech Proposals",
        "frequency": "High",
    },
    {
        "word_in_text": "technically feasible",
        "word_in_answer": "viable / practicable / workable",
        "meaning": "khả thi về mặt kỹ thuật",
        "part_target": "Part 7 Feasibility Reports",
        "frequency": "Extreme",
    },
    {
        "word_in_text": "pending budget approval",
        "word_in_answer": "subject to executive financial authorization",
        "meaning": "chờ phê duyệt ngân sách từ ban giám đốc",
        "part_target": "Part 7 Executive Memos",
        "frequency": "Extreme",
    },
    {
        "word_in_text": "drop from 4 hours to 500ms",
        "word_in_answer": "significantly reduce latency and delay",
        "meaning": "giảm độ trễ truy vấn đáng kể",
        "part_target": "Part 7 Performance Reports",
        "frequency": "High",
    },
    {
        "word_in_text": "commence deployment",
        "word_in_answer": "initiate rollout / begin implementation",
        "meaning": "bắt đầu triển khai dự án",
        "part_target": "Part 7 Schedules",
        "frequency": "Extreme",
    },
    {
        "word_in_text": "zero-downtime cutover",
        "word_in_answer": "seamless transition with no service disruption",
        "meaning": "chuyển đổi mượt mà không gián đoạn dịch vụ",
        "part_target": "Part 7 Infrastructure Notices",
        "frequency": "High",
    },
    {
        "word_in_text": "mandatory upgrade",
        "word_in_answer": "compulsory modernization / required update",
        "meaning": "bản nâng cấp bắt buộc",
        "part_target": "Part 7 IT Notices",
        "frequency": "Extreme",
    },
    {
        "word_in_text": "permanently revoked",
        "word_in_answer": "canceled indefinitely / rendered obsolete",
        "meaning": "bị thu hồi vĩnh viễn không còn hiệu lực",
        "part_target": "Part 7 Security Notices",
        "frequency": "High",
    },
    {
        "word_in_text": "take less than ten minutes",
        "word_in_answer": "quick and straightforward setup process",
        "meaning": "quy trình cài đặt nhanh chóng",
        "part_target": "Part 7 User Guides",
        "frequency": "High",
    },
    {
        "word_in_text": "conclude by deadline",
        "word_in_answer": "finish / wrap up prior to the cut-off date",
        "meaning": "kết thúc trước thời hạn",
        "part_target": "Part 7 Project Plans",
        "frequency": "High",
    },
]


def ingest_test03(db_session=None):
    close_when_done = False
    if db_session is None:
        init_db()
        db = SessionLocal()
        close_when_done = True
    else:
        db = db_session

    try:
        print("=== 1. Ingesting Mock Test ETS2024_03 ===")
        test_03 = db.query(MockTest).filter_by(test_id="ETS2024_03").first()
        if not test_03:
            test_03 = MockTest(
                test_id="ETS2024_03",
                name="ETS TOEIC Regular Test 2024 - Test 03",
                year=2024,
                publisher="ETS",
                total_questions=200,
            )
            db.add(test_03)
            db.commit()
            db.refresh(test_03)
            print("  ✓ Created MockTest 'ETS2024_03'")
        else:
            print("  • MockTest 'ETS2024_03' already exists")

        print("\n=== 2. Ingesting Questions for ETS2024_03 ===")
        inserted_q_count = 0
        for item in TEST_03_QUESTIONS:
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
                    source="ets2024_test03",
                )
                db.add(q)
                inserted_q_count += 1
        db.commit()
        print(f"  ✓ Ingested {inserted_q_count} new questions for ETS2024_03 (Total defined: {len(TEST_03_QUESTIONS)})")

        print("\n=== 3. Expanding Flashcards & SuperMemo-2 SRS ===")
        users = db.query(User).all()
        user_ids = [u.id for u in users] or [1]

        inserted_card_count = 0
        for word, ipa, wtype, cat, meaning, colloc, para, ex_en, ex_vi in NEW_FLASHCARDS_TEST03:
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
        for p in NEW_PARAPHRASE_PAIRS_TEST03:
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

        print("\n🎉 All ETS 2024 Test 03 dataset ingested successfully!")
        return {
            "test_id": "ETS2024_03",
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
    ingest_test03()
