#!/usr/bin/env python3
"""
Corpus Expansion Script for TOEIC Lab:
1. Ingests full 30 Part 5 benchmark questions (Q101 -> Q130) of ETS 2024 Test 01
   with deep 3-dimensional analysis (Explanation, Distractor Traps, Paraphrase Pairs).
2. Expands Flashcard Vocabulary from 20 to 60 Core Business Words with full collocations,
   paraphrase pairs, IPA, and SuperMemo-2 SRS initialization.
"""

import sys
from pathlib import Path

from sqlalchemy import func

# Set up environment path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from server.database import SessionLocal, init_db
from server.models import Flashcard, UserCardSRS, TestQuestion, MockTest
from server.utils.timeutil import utcnow

# -------------------------------------------------------------
# 1. 30 Part 5 Benchmark Questions (ETS 2024 Test 01: Q101 -> Q130)
# -------------------------------------------------------------
PART5_QUESTIONS = [
    {
        "test_id": "ETS2024_01",
        "part": "Part 5",
        "question_no": 101,
        "sentence": "Customer service representatives must speak ___ and politely when handling client inquiries.",
        "choice_a": "clear",
        "choice_b": "clearly",
        "choice_c": "clearness",
        "choice_d": "cleared",
        "correct_choice": "B",
        "explanation": "Cần một trạng từ (clearly) đứng sau động từ 'speak' và liên từ song hành 'and' liên kết với trạng từ 'politely' (speak clearly and politely).",
        "distractor_analysis": "[Bẫy Từ Loại] A (clear) là tính từ; C (clearness) là danh từ; D (cleared) là phân từ/quá khứ. Không thể bổ nghĩa trực tiếp cho động từ hành động 'speak'.",
        "paraphrase_pair": "speak clearly and politely"
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 5",
        "question_no": 102,
        "sentence": "All department managers must submit ___ quarterly budget forecasts by Friday afternoon.",
        "choice_a": "they",
        "choice_b": "them",
        "choice_c": "their",
        "choice_d": "themselves",
        "correct_choice": "C",
        "explanation": "Chỗ trống đứng trước cụm danh từ 'quarterly budget forecasts' nên cần tính từ sở hữu 'their' để bổ nghĩa.",
        "distractor_analysis": "[Bẫy Đại Từ] A (they) là đại từ chủ ngữ; B (them) là tân ngữ; D (themselves) là đại từ phản thân.",
        "paraphrase_pair": "submit their forecasts = hand in their estimates"
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 5",
        "question_no": 103,
        "sentence": "The internal audit committee will ___ a thorough review of the financial transactions next week.",
        "choice_a": "conduct",
        "choice_b": "conductively",
        "choice_c": "conductor",
        "choice_d": "conducting",
        "correct_choice": "A",
        "explanation": "Sau trợ động từ khuyết thiếu 'will', động từ chính bắt buộc ở dạng nguyên thể không 'to' (will conduct). Ngoài ra 'conduct a review' là collocation quen thuộc.",
        "distractor_analysis": "[Bẫy Dạng Động Từ] B là trạng từ; C là danh từ chỉ người; D là dạng V-ing không đi trực tiếp sau will.",
        "paraphrase_pair": "conduct a review = carry out an inspection"
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 5",
        "question_no": 104,
        "sentence": "Ms. Tanaka will present the final design blueprints ___ the executive committee tomorrow morning.",
        "choice_a": "to",
        "choice_b": "at",
        "choice_c": "on",
        "choice_d": "by",
        "correct_choice": "A",
        "explanation": "Cấu trúc giới từ chuẩn: 'present something to somebody' (thuyết trình/trình bày cái gì cho ai).",
        "distractor_analysis": "[Bẫy Giới Từ] At/On/By không đi với cấu trúc chuyển giao thông tin của động từ 'present sth to sb'.",
        "paraphrase_pair": "present to the committee = showcase before the board"
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 5",
        "question_no": 105,
        "sentence": "Each of the participating software engineers ___ granted access to the production server.",
        "choice_a": "was",
        "choice_b": "were",
        "choice_c": "have",
        "choice_d": "are",
        "correct_choice": "A",
        "explanation": "Chủ ngữ là đại từ 'Each' (Each of + danh từ số nhiều), động từ luôn chia ở số ít ('was'). Câu ở dạng bị động thì quá khứ đơn.",
        "distractor_analysis": "[Bẫy Hòa Hợp Chủ-Vị] Thí sinh dễ nhìn nhầm danh từ số nhiều 'engineers' đứng ngay trước chỗ trống mà chọn động từ số nhiều B (were) hoặc D (are).",
        "paraphrase_pair": "be granted access = be authorized to enter"
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 5",
        "question_no": 106,
        "sentence": "In order ___ travel expenses, all employees must book flights through the corporate portal.",
        "choice_a": "reduce",
        "choice_b": "reducing",
        "choice_c": "to reduce",
        "choice_d": "reduction",
        "correct_choice": "C",
        "explanation": "Cụm chỉ mục đích chuẩn ngữ pháp: 'In order to + V-bare' (để làm gì).",
        "distractor_analysis": "[Bẫy Cụm Mục Đích] A thiếu 'to'; B dùng V-ing sai cấu trúc 'in order to'; D là danh từ.",
        "paraphrase_pair": "in order to reduce expenses = so as to cut costs"
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 5",
        "question_no": 107,
        "sentence": "The company offers a ___ warranty that covers all hardware replacements for three full years.",
        "choice_a": "comprehend",
        "choice_b": "comprehensive",
        "choice_c": "comprehensively",
        "choice_d": "comprehension",
        "correct_choice": "B",
        "explanation": "Vị trí đứng trước danh từ 'warranty' và sau mạo từ 'a' cần một tính từ ('comprehensive' - toàn diện).",
        "distractor_analysis": "[Bẫy Vị Trí Tính Từ] A (comprehend) là động từ; C (comprehensively) là trạng từ; D (comprehension) là danh từ.",
        "paraphrase_pair": "comprehensive warranty = full/all-inclusive coverage"
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 5",
        "question_no": 108,
        "sentence": "The board members ___ approved the revised budget for cloud computing modernization.",
        "choice_a": "unanimity",
        "choice_b": "unanimous",
        "choice_c": "unanimities",
        "choice_d": "unanimously",
        "correct_choice": "D",
        "explanation": "Vị trí đứng chen giữa chủ ngữ 'The board members' và động từ chính 'approved' chỉ có thể là trạng từ (Adv) bổ nghĩa cho hành động phê duyệt.",
        "distractor_analysis": "[Bẫy Vị Trí Trạng Từ] B (unanimous) là tính từ; A/C là danh từ. Tính từ không thể đứng bổ nghĩa cho động từ vị ngữ.",
        "paraphrase_pair": "unanimously approved = approved by complete consensus"
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 5",
        "question_no": 109,
        "sentence": "Since Mr. Gomez was appointed director, overall manufacturing productivity ___ by 25 percent.",
        "choice_a": "increases",
        "choice_b": "has increased",
        "choice_c": "will increase",
        "choice_d": "increased",
        "correct_choice": "B",
        "explanation": "Công thức kinh điển với liên từ 'Since': Mệnh đề 'Since + Quá khứ đơn', mệnh đề chính chia ở 'Hiện tại hoàn thành' (has increased).",
        "distractor_analysis": "[Bẫy Thì Thời Gian] A là hiện tại đơn; C là tương lai; D là quá khứ đơn. Không phù hợp với mốc thời gian bắt đầu từ quá khứ kéo dài đến hiện tại của 'Since'.",
        "paraphrase_pair": "productivity has increased = output has grown"
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 5",
        "question_no": 110,
        "sentence": "The annual shareholder conference will be ___ at the Grand Hyatt Convention Hall.",
        "choice_a": "hold",
        "choice_b": "holding",
        "choice_c": "held",
        "choice_d": "holds",
        "correct_choice": "C",
        "explanation": "Cấu trúc bị động tương lai: 'will be + V3/ed'. Hội nghị được tổ chức ➔ 'will be held'.",
        "distractor_analysis": "[Bẫy Thể Bị Động] A là nguyên thể; B là chủ động tiếp diễn; D là hiện tại đơn.",
        "paraphrase_pair": "be held at = take place at"
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 5",
        "question_no": 111,
        "sentence": "The outdoor corporate banquet was relocated indoors ___ the sudden thunderstorm.",
        "choice_a": "because",
        "choice_b": "although",
        "choice_c": "because of",
        "choice_d": "despite of",
        "correct_choice": "C",
        "explanation": "Phía sau chỗ trống là một cụm danh từ ('the sudden thunderstorm'). 'Because of' là giới từ đi với cụm danh từ để chỉ nguyên nhân.",
        "distractor_analysis": "[Bẫy Liên Từ vs Giới Từ] A (because) là liên từ phải đi với mệnh đề (S + V). B (although) chỉ nhượng bộ. D (despite of) là từ sai ngữ pháp tiếng Anh (chỉ có 'despite' hoặc 'in spite of').",
        "paraphrase_pair": "because of = due to = owing to"
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 5",
        "question_no": 112,
        "sentence": "The project development team worked overtime to ensure they would ___ the strict client deadline.",
        "choice_a": "meet",
        "choice_b": "gain",
        "choice_c": "catch",
        "choice_d": "fulfill",
        "correct_choice": "A",
        "explanation": "Collocation thương mại then chốt: 'meet the deadline' (kịp hạn chót).",
        "distractor_analysis": "[Bẫy Collocation] Mặc dù 'fulfill' có nghĩa hoàn thành nhưng khi đi với 'deadline' trong đề thi ETS thì 'meet the deadline' là cụm chuẩn nhất.",
        "paraphrase_pair": "meet the deadline = complete on time"
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 5",
        "question_no": 113,
        "sentence": "Experienced backend programmers are capable of resolving complex database deadlocks by ___.",
        "choice_a": "them",
        "choice_b": "their",
        "choice_c": "they",
        "choice_d": "themselves",
        "correct_choice": "D",
        "explanation": "Cấu trúc nhấn mạnh tự mình làm: 'by + đại từ phản thân' (by themselves = on their own).",
        "distractor_analysis": "[Bẫy Đại Từ Phản Thân] A/B/C không thể đứng sau giới từ 'by' với ý nghĩa tự mình thực hiện hành động.",
        "paraphrase_pair": "by themselves = independently = on their own"
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 5",
        "question_no": 114,
        "sentence": "After ___ the contract terms thoroughly, the legal advisor signed the procurement agreement.",
        "choice_a": "review",
        "choice_b": "reviewed",
        "choice_c": "reviewing",
        "choice_d": "reviews",
        "correct_choice": "C",
        "explanation": "Sau giới từ 'After', động từ phải ở dạng danh động từ 'V-ing' (After reviewing sth) hoặc rút gọn mệnh đề cùng chủ ngữ chủ động.",
        "distractor_analysis": "[Bẫy Dạng Động Từ Sau Giới Từ] A là V-bare; B là V-ed; D là chia số ít.",
        "paraphrase_pair": "after reviewing = upon examining"
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 5",
        "question_no": 115,
        "sentence": "___ the adverse snowstorm in Chicago, the delivery trucks arrived on schedule.",
        "choice_a": "Although",
        "choice_b": "Despite",
        "choice_c": "Because",
        "choice_d": "Even if",
        "correct_choice": "B",
        "explanation": "Phía sau chỗ trống là cụm danh từ ('the adverse snowstorm...'). Để thể hiện nghĩa tương phản/nhượng bộ đi với cụm Noun, ta dùng giới từ 'Despite'.",
        "distractor_analysis": "[Bẫy Liên Từ Nhượng Bộ] 'Although' và 'Even if' là liên từ, đòi hỏi đi kèm một mệnh đề hoàn chỉnh có động từ vị ngữ (S + V).",
        "paraphrase_pair": "despite = in spite of = regardless of"
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 5",
        "question_no": 116,
        "sentence": "The newly installed air conditioning unit operates much more ___ than the older system.",
        "choice_a": "quiet",
        "choice_b": "quietly",
        "choice_c": "quietness",
        "choice_d": "quieting",
        "correct_choice": "B",
        "explanation": "Động từ 'operates' (vận hành) là động từ hành động thường, do đó cần trạng từ 'quietly' để bổ nghĩa trong cấu trúc so sánh hơn (operates more quietly).",
        "distractor_analysis": "[Bẫy Từ Loại Trong So Sánh] Thí sinh dễ nhầm tưởng sau 'more' luôn là tính từ (quiet) mà quên mất động từ chính phía trước là 'operates'.",
        "paraphrase_pair": "operate quietly = run with minimal noise"
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 5",
        "question_no": 117,
        "sentence": "Quarterly revenue for the cloud storage division was substantially ___ than initial analyst estimates.",
        "choice_a": "high",
        "choice_b": "higher",
        "choice_c": "highest",
        "choice_d": "highly",
        "correct_choice": "B",
        "explanation": "Có từ 'than' ở phía sau ➔ Dấu hiệu bắt buộc của so sánh hơn (higher than). 'Substantially' là trạng từ nhấn mạnh mức độ chênh lệch.",
        "distractor_analysis": "[Bẫy So Sánh] A là tính từ nguyên; C là so sánh nhất (cần 'the'); D là trạng từ chỉ mức độ (rất/cao độ).",
        "paraphrase_pair": "substantially higher than = significantly exceeded"
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 5",
        "question_no": 118,
        "sentence": "Please verify that all information entered on the job application is ___ and up to date.",
        "choice_a": "accuracy",
        "choice_b": "accurate",
        "choice_c": "accurately",
        "choice_d": "accurateness",
        "correct_choice": "B",
        "explanation": "Đứng sau liên động từ 'is' và trước liên từ 'and' nối với tính từ 'up to date', chỗ trống cần một tính từ ('accurate' - chính xác).",
        "distractor_analysis": "[Bẫy Tính Từ Sau Linking Verb] A (accuracy) là danh từ; C (accurately) là trạng từ; D là danh từ hiếm gặp.",
        "paraphrase_pair": "accurate = precise = correct"
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 5",
        "question_no": 119,
        "sentence": "The CEO requested that every regional manager ___ present at the emergency strategy meeting.",
        "choice_a": "is",
        "choice_b": "was",
        "choice_c": "be",
        "choice_d": "being",
        "correct_choice": "C",
        "explanation": "Cấu trúc Thể giả định (Subjunctive Mood): Sau động từ yêu cầu 'requested that + S + (should) + V-bare'. Do đó động từ to be ở dạng nguyên thể là 'be'.",
        "distractor_analysis": "[Bẫy Thể Giả Định] Bẫy rất khó: Thí sinh thấy 'requested' ở quá khứ và chủ ngữ 'every manager' số ít nên hay chọn A (is) hoặc B (was).",
        "paraphrase_pair": "requested that S be = mandated the attendance of"
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 5",
        "question_no": 120,
        "sentence": "All factory workers are strictly required to ___ with the newly updated safety protocols.",
        "choice_a": "comply",
        "choice_b": "agree",
        "choice_c": "conform",
        "choice_d": "observe",
        "correct_choice": "A",
        "explanation": "Collocation kinh điển Part 5: 'comply with' (tuân thủ theo). 'Conform' thường đi với 'to', 'Observe' là ngoại động từ đi trực tiếp với tân ngữ không có giới từ.",
        "distractor_analysis": "[Bẫy Giới Từ Đi Kèm Động Từ] 'Observe' đi với tân ngữ thẳng (observe regulations). 'Conform' đi với 'to'.",
        "paraphrase_pair": "comply with = adhere to = abide by"
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 5",
        "question_no": 121,
        "sentence": "Next Monday, the logistics department ___ a new automated tracking system across all branches.",
        "choice_a": "launched",
        "choice_b": "will launch",
        "choice_c": "had launched",
        "choice_d": "has launched",
        "correct_choice": "B",
        "explanation": "Dấu hiệu thời gian 'Next Monday' chỉ hành động sẽ xảy ra trong tương lai ➔ Chia thì tương lai đơn 'will launch'.",
        "distractor_analysis": "[Bẫy Thì Tương Lai] A là quá khứ đơn; C là quá khứ hoàn thành; D là hiện tại hoàn thành.",
        "paraphrase_pair": "will launch = will introduce = will deploy"
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 5",
        "question_no": 122,
        "sentence": "___ who wishes to attend the leadership seminar must submit a registration form by noon.",
        "choice_a": "Anyone",
        "choice_b": "Someone",
        "choice_c": "Those",
        "choice_d": "These",
        "correct_choice": "A",
        "explanation": "Động từ theo sau là 'wishes' (chia số ít) ➔ Cần đại từ bất định số ít 'Anyone' (Anyone who wishes). 'Those' đi với động từ số nhiều (Those who wish).",
        "distractor_analysis": "[Bẫy Đại Từ Quan Hệ Số Ít vs Số Nhiều] Thí sinh hay nhớ máy móc cụm 'Those who' mà không để ý động từ 'wishes' có đuôi -es.",
        "paraphrase_pair": "anyone who wishes = any person interested"
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 5",
        "question_no": 123,
        "sentence": "The marketing team developed a ___ effective advertising campaign targeting young professionals.",
        "choice_a": "high",
        "choice_b": "highly",
        "choice_c": "height",
        "choice_d": "heighten",
        "correct_choice": "B",
        "explanation": "Chỗ trống đứng trước tính từ 'effective' để bổ nghĩa về mức độ ➔ Cần trạng từ 'highly' (highly effective = cực kỳ hiệu quả).",
        "distractor_analysis": "[Bẫy Trạng Từ Bổ Nghĩa Cho Tính Từ] A (high) là tính từ; C là danh từ; D là động từ.",
        "paraphrase_pair": "highly effective = extremely successful"
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 5",
        "question_no": 124,
        "sentence": "___ you experience any difficulties accessing the internal portal, please contact the IT helpdesk.",
        "choice_a": "If",
        "choice_b": "Should",
        "choice_c": "Were",
        "choice_d": "Had",
        "correct_choice": "B",
        "explanation": "Cấu trúc đảo ngữ câu điều kiện loại 1 trang trọng: 'Should + S + V-bare, (please) V...' thay cho 'If you experience...'.",
        "distractor_analysis": "[Bẫy Đảo Ngữ Câu Điều Kiện] Nếu chọn A (If) thì câu vẫn đúng nhưng trong đề thi khi có dạng trang trọng thì 'Should' thường là phương án kiểm tra kiến thức đảo ngữ.",
        "paraphrase_pair": "Should you experience = In the event that you encounter"
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 5",
        "question_no": 125,
        "sentence": "The new policy requires employees to either submit a doctor's note ___ take an unpaid leave day.",
        "choice_a": "and",
        "choice_b": "or",
        "choice_c": "nor",
        "choice_d": "but",
        "correct_choice": "B",
        "explanation": "Cặp liên từ tương quan cố định: 'either ... or' (hoặc cái này hoặc cái kia).",
        "distractor_analysis": "[Bẫy Liên Từ Tương Quan] A đi với 'both ... and'; C đi với 'neither ... nor'; D đi với 'not only ... but also'.",
        "paraphrase_pair": "either A or B"
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 5",
        "question_no": 126,
        "sentence": "Full-time developers with over two years of tenure are ___ for tuition reimbursement.",
        "choice_a": "eligible",
        "choice_b": "capable",
        "choice_c": "possible",
        "choice_d": "probable",
        "correct_choice": "A",
        "explanation": "Cụm tính từ đi với giới từ 'for' chỉ tư cách quyền lợi: 'eligible for sth' (đủ điều kiện hưởng quyền lợi). 'Capable' đi với giới từ 'of'.",
        "distractor_analysis": "[Bẫy Tính Từ Đi Với Giới Từ] 'Capable of doing sth'; 'Possible/Probable' không dùng làm vị ngữ cho người chỉ quyền lợi.",
        "paraphrase_pair": "eligible for = qualified for = entitled to"
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 5",
        "question_no": 127,
        "sentence": "The promotional discounts will be applied ___ accordance with the terms outlined in the coupon.",
        "choice_a": "at",
        "choice_b": "in",
        "choice_c": "on",
        "choice_d": "by",
        "correct_choice": "B",
        "explanation": "Cụm giới từ cố định bắt buộc: 'in accordance with' (phù hợp với / chiếu theo quy định).",
        "distractor_analysis": "[Bẫy Cụm Giới Từ Cố Định] Không có cụm 'at accordance with' hay 'on accordance with'.",
        "paraphrase_pair": "in accordance with = in compliance with = following"
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 5",
        "question_no": 128,
        "sentence": "The replacement parts ___ from Germany are expected to arrive at the port tomorrow morning.",
        "choice_a": "order",
        "choice_b": "ordering",
        "choice_c": "ordered",
        "choice_d": "were ordered",
        "correct_choice": "C",
        "explanation": "Rút gọn mệnh đề quan hệ dạng bị động: 'The replacement parts [which were ordered] from Germany...'. Rút gọn còn phân từ quá khứ 'ordered'. Động từ chính của câu là 'are expected'.",
        "distractor_analysis": "[Bẫy Hai Động Từ Chính Trong Câu] Thí sinh chọn D (were ordered) sẽ khiến câu có 2 vị ngữ mà không có liên từ nối.",
        "paraphrase_pair": "parts ordered from = components purchased from"
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 5",
        "question_no": 129,
        "sentence": "The convention center is large enough to ___ up to 1,500 participants comfortably.",
        "choice_a": "accommodate",
        "choice_b": "commute",
        "choice_c": "associate",
        "choice_d": "negotiate",
        "correct_choice": "A",
        "explanation": "Từ vựng then chốt trong lĩnh vực nhà hàng khách sạn hội nghị: 'accommodate' (chứa được, cung cấp chỗ cho số lượng khách).",
        "distractor_analysis": "[Bẫy Từ Vựng Cùng Loại] B (commute) là đi lại làm việc; C (associate) là liên kết; D (negotiate) là đàm phán thương lượng.",
        "paraphrase_pair": "accommodate up to = provide capacity for"
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 5",
        "question_no": 130,
        "sentence": "The delivery schedule provided by the supplier is only ___ and may change depending on customs clearance.",
        "choice_a": "tentative",
        "choice_b": "definite",
        "choice_c": "permanent",
        "choice_d": "absolute",
        "correct_choice": "A",
        "explanation": "Căn cứ vào vế sau 'and may change' (và có thể thay đổi), chỗ trống cần tính từ chỉ tính chất tạm thời, dự kiến: 'tentative' (dự kiến, chưa chốt).",
        "distractor_analysis": "[Bẫy Từ Trái Nghĩa] B (definite), C (permanent), D (absolute) đều mang nghĩa cố định, chắc chắn, trái ngược với ngữ cảnh.",
        "paraphrase_pair": "tentative schedule = provisional/subject to change timetable"
    }
]

# -------------------------------------------------------------
# 2. 40 Additional Core Business Flashcards (From #21 to #60)
# -------------------------------------------------------------
ADDITIONAL_FLASHCARDS = [
    {
        "id": 21,
        "category": "Corporate & Finance",
        "word": "revenue",
        "ipa": "ˈrevənjuː",
        "word_type": "noun",
        "meaning": "doanh thu, tiền thu nhập của công ty",
        "collocations": "annual revenue, generate revenue, gross revenue",
        "paraphrase_pair": "revenue = turnover = income = earnings",
        "example_sentence": "The tech company reported a 15% increase in annual <span class='blank'>______</span> driven by cloud software sales.",
        "audio_word_url": "audio/words/revenue.mp3",
        "audio_sentence_url": "audio/sentences/sentence_21.mp3"
    },
    {
        "id": 22,
        "category": "Banking & Accounting",
        "word": "deficit",
        "ipa": "ˈdefɪsɪt",
        "word_type": "noun",
        "meaning": "sự thâm hụt ngân sách",
        "collocations": "budget deficit, trade deficit, reduce the deficit",
        "paraphrase_pair": "deficit = shortfall = shortage",
        "example_sentence": "The finance director introduced spending cuts to eliminate the operating budget <span class='blank'>______</span>.",
        "audio_word_url": "audio/words/deficit.mp3",
        "audio_sentence_url": "audio/sentences/sentence_22.mp3"
    },
    {
        "id": 23,
        "category": "Corporate Operations",
        "word": "merger",
        "ipa": "ˈmɜːdʒər",
        "word_type": "noun",
        "meaning": "sự sáp nhập doanh nghiệp",
        "collocations": "proposed merger, approve a merger, merger and acquisition",
        "paraphrase_pair": "merger = amalgamation = consolidation",
        "example_sentence": "The shareholders voted overwhelmingly in favor of the <span class='blank'>______</span> between the two telecom providers.",
        "audio_word_url": "audio/words/merger.mp3",
        "audio_sentence_url": "audio/sentences/sentence_23.mp3"
    },
    {
        "id": 24,
        "category": "Corporate Operations",
        "word": "acquisition",
        "ipa": "ˌækwɪˈzɪʃn",
        "word_type": "noun",
        "meaning": "sự mua lại, thâu tóm công ty",
        "collocations": "corporate acquisition, complete the acquisition, recent acquisition",
        "paraphrase_pair": "acquisition = takeover = buyout",
        "example_sentence": "Following the <span class='blank'>______</span> of the startup, our engineering team expanded by thirty engineers.",
        "audio_word_url": "audio/words/acquisition.mp3",
        "audio_sentence_url": "audio/sentences/sentence_24.mp3"
    },
    {
        "id": 25,
        "category": "Marketing & Advertising",
        "word": "promote",
        "ipa": "prəˈməʊt",
        "word_type": "verb",
        "meaning": "thúc đẩy, quảng bá; thăng chức",
        "collocations": "promote a new product, promote brand awareness, promote an employee",
        "paraphrase_pair": "promote = advertise = market = upgrade",
        "example_sentence": "The marketing agency designed an aggressive campaign to <span class='blank'>______</span> the newly developed mobile banking app.",
        "audio_word_url": "audio/words/promote.mp3",
        "audio_sentence_url": "audio/sentences/sentence_25.mp3"
    },
    {
        "id": 26,
        "category": "Marketing & Advertising",
        "word": "campaign",
        "ipa": "kæmˈpeɪn",
        "word_type": "noun",
        "meaning": "chiến dịch (quảng cáo, tiếp thị)",
        "collocations": "advertising campaign, launch a campaign, promotional campaign",
        "paraphrase_pair": "campaign = drive = initiative = marketing effort",
        "example_sentence": "The social media marketing <span class='blank'>______</span> generated over one million views in its first week.",
        "audio_word_url": "audio/words/campaign.mp3",
        "audio_sentence_url": "audio/sentences/sentence_26.mp3"
    },
    {
        "id": 27,
        "category": "Marketing & Advertising",
        "word": "consumer",
        "ipa": "kənˈsjuːmər",
        "word_type": "noun",
        "meaning": "người tiêu dùng",
        "collocations": "consumer demand, consumer satisfaction, protect consumers",
        "paraphrase_pair": "consumer = customer = buyer = purchaser",
        "example_sentence": "Recent survey findings indicate a sharp shift in <span class='blank'>______</span> preferences toward eco-friendly packaging.",
        "audio_word_url": "audio/words/consumer.mp3",
        "audio_sentence_url": "audio/sentences/sentence_27.mp3"
    },
    {
        "id": 28,
        "category": "Marketing & Advertising",
        "word": "target",
        "ipa": "ˈtɑːɡɪt",
        "word_type": "verb",
        "meaning": "nhắm mục tiêu vào nhóm đối tượng",
        "collocations": "target an audience, target market, meet sales targets",
        "paraphrase_pair": "target = aim at = focus on",
        "example_sentence": "The promotional pricing strategy specifically seeks to <span class='blank'>______</span> young software developers and tech startups.",
        "audio_word_url": "audio/words/target.mp3",
        "audio_sentence_url": "audio/sentences/sentence_28.mp3"
    },
    {
        "id": 29,
        "category": "Marketing & Advertising",
        "word": "launch",
        "ipa": "lɔːntʃ",
        "word_type": "verb",
        "meaning": "khởi động, ra mắt sản phẩm mới",
        "collocations": "launch a product, official launch, launch a website",
        "paraphrase_pair": "launch = introduce = release = roll out",
        "example_sentence": "The tech giant is preparing to <span class='blank'>______</span> its next-generation artificial intelligence platform next month.",
        "audio_word_url": "audio/words/launch.mp3",
        "audio_sentence_url": "audio/sentences/sentence_29.mp3"
    },
    {
        "id": 30,
        "category": "Banking & Accounting",
        "word": "surplus",
        "ipa": "ˈsɜːpləs",
        "word_type": "noun",
        "meaning": "khoản thặng dư, dôi dư",
        "collocations": "budget surplus, trade surplus, surplus inventory",
        "paraphrase_pair": "surplus = excess = extra amount",
        "example_sentence": "Due to disciplined cost controls, the logistics division finished the fiscal year with a considerable cash <span class='blank'>______</span>.",
        "audio_word_url": "audio/words/surplus.mp3",
        "audio_sentence_url": "audio/sentences/sentence_30.mp3"
    },
    {
        "id": 31,
        "category": "Banking & Accounting",
        "word": "dividend",
        "ipa": "ˈdɪvɪdend",
        "word_type": "noun",
        "meaning": "cổ tức chi trả cho cổ đông",
        "collocations": "quarterly dividend, pay dividends, increase dividend payouts",
        "paraphrase_pair": "dividend = shareholder distribution = share payout",
        "example_sentence": "The board resolved to distribute a quarterly cash <span class='blank'>______</span> of fifty cents per common share.",
        "audio_word_url": "audio/words/dividend.mp3",
        "audio_sentence_url": "audio/sentences/sentence_31.mp3"
    },
    {
        "id": 32,
        "category": "Corporate Operations",
        "word": "restructure",
        "ipa": "ˌriːˈstrʌktʃər",
        "word_type": "verb",
        "meaning": "tái cấu trúc lại tổ chức hoặc nợ",
        "collocations": "restructure the organization, restructure debt, corporate restructuring",
        "paraphrase_pair": "restructure = reorganize = streamline",
        "example_sentence": "In order to remain competitive, management decided to <span class='blank'>______</span> the product engineering divisions.",
        "audio_word_url": "audio/words/restructure.mp3",
        "audio_sentence_url": "audio/sentences/sentence_32.mp3"
    },
    {
        "id": 33,
        "category": "Personnel & Training",
        "word": "designate",
        "ipa": "ˈdezɪɡneɪt",
        "word_type": "verb",
        "meaning": "chỉ định, bổ nhiệm vào vị trí",
        "collocations": "designate a representative, designated parking area, officially designate",
        "paraphrase_pair": "designate = appoint = assign = name",
        "example_sentence": "The executive committee will <span class='blank'>______</span> an acting department head during Mr. Adams' absence.",
        "audio_word_url": "audio/words/designate.mp3",
        "audio_sentence_url": "audio/sentences/sentence_33.mp3"
    },
    {
        "id": 34,
        "category": "Customer Relations",
        "word": "resolution",
        "ipa": "ˌrezəˈluːʃn",
        "word_type": "noun",
        "meaning": "biện pháp giải quyết vấn đề, nghị quyết",
        "collocations": "dispute resolution, swift resolution, board resolution",
        "paraphrase_pair": "resolution = settlement = solution = decision",
        "example_sentence": "Our primary customer support objective is the prompt <span class='blank'>______</span> of all client billing complaints.",
        "audio_word_url": "audio/words/resolution.mp3",
        "audio_sentence_url": "audio/sentences/sentence_34.mp3"
    },
    {
        "id": 35,
        "category": "Customer Relations",
        "word": "satisfaction",
        "ipa": "ˌsætɪsˈfækʃn",
        "word_type": "noun",
        "meaning": "sự hài lòng, thỏa mãn của khách hàng",
        "collocations": "customer satisfaction, guarantee satisfaction, express satisfaction",
        "paraphrase_pair": "satisfaction = contentment = approval",
        "example_sentence": "High client <span class='blank'>______</span> scores contributed directly to our contract renewal rate reaching 95 percent.",
        "audio_word_url": "audio/words/satisfaction.mp3",
        "audio_sentence_url": "audio/sentences/sentence_35.mp3"
    },
    {
        "id": 36,
        "category": "Purchasing & Warranty",
        "word": "warranty",
        "ipa": "ˈwɒrənti",
        "word_type": "noun",
        "meaning": "phiếu bảo hành, cam kết bảo hành",
        "collocations": "under warranty, extended warranty, warranty period",
        "paraphrase_pair": "warranty = guarantee = guarantee certificate",
        "example_sentence": "Please retain your sales receipt to validate the one-year manufacturer <span class='blank'>______</span> on this monitor.",
        "audio_word_url": "audio/words/warranty.mp3",
        "audio_sentence_url": "audio/sentences/sentence_36.mp3"
    },
    {
        "id": 37,
        "category": "Customer Relations",
        "word": "refund",
        "ipa": "ˈriːfʌnd",
        "word_type": "noun",
        "meaning": "tiền hoàn trả lại",
        "collocations": "full refund, issue a refund, request a refund",
        "paraphrase_pair": "refund = repayment = reimbursement",
        "example_sentence": "Customers returning unopened merchandise within 14 days will receive a full <span class='blank'>______</span> to their credit card.",
        "audio_word_url": "audio/words/refund.mp3",
        "audio_sentence_url": "audio/sentences/sentence_37.mp3"
    },
    {
        "id": 38,
        "category": "Customer Relations",
        "word": "feedback",
        "ipa": "ˈfiːdbæk",
        "word_type": "noun",
        "meaning": "ý kiến đóng góp, phản hồi",
        "collocations": "customer feedback, constructive feedback, solicit feedback",
        "paraphrase_pair": "feedback = comments = input = reviews",
        "example_sentence": "We genuinely appreciate your valuable <span class='blank'>______</span> as it helps us enhance our API performance.",
        "audio_word_url": "audio/words/feedback.mp3",
        "audio_sentence_url": "audio/sentences/sentence_38.mp3"
    },
    {
        "id": 39,
        "category": "Office & Administration",
        "word": "procedure",
        "ipa": "prəˈsiːdʒər",
        "word_type": "noun",
        "meaning": "thủ tục, quy trình thực hiện",
        "collocations": "standard operating procedure, safety procedure, follow procedures",
        "paraphrase_pair": "procedure = process = method = steps",
        "example_sentence": "All staff members must adhere strictly to the established emergency evacuation <span class='blank'>______</span>.",
        "audio_word_url": "audio/words/procedure.mp3",
        "audio_sentence_url": "audio/sentences/sentence_39.mp3"
    },
    {
        "id": 40,
        "category": "Technical & IT",
        "word": "protocol",
        "ipa": "ˈprəʊtəkɒl",
        "word_type": "noun",
        "meaning": "giao thức, nghi thức làm việc",
        "collocations": "security protocol, communication protocol, follow protocol",
        "paraphrase_pair": "protocol = rules = standard convention = code",
        "example_sentence": "The infrastructure team updated the network security <span class='blank'>______</span> to prevent unauthorized remote logins.",
        "audio_word_url": "audio/words/protocol.mp3",
        "audio_sentence_url": "audio/sentences/sentence_40.mp3"
    },
    {
        "id": 41,
        "category": "Office & Administration",
        "word": "archive",
        "ipa": "ˈɑːkaɪv",
        "word_type": "verb",
        "meaning": "lưu trữ vào kho hồ sơ",
        "collocations": "archive records, digitally archive, archival storage",
        "paraphrase_pair": "archive = store = file away = keep in records",
        "example_sentence": "The administrative department will <span class='blank'>______</span> all past project contracts onto secure cloud servers.",
        "audio_word_url": "audio/words/archive.mp3",
        "audio_sentence_url": "audio/sentences/sentence_41.mp3"
    },
    {
        "id": 42,
        "category": "Legal & Contracts",
        "word": "breach",
        "ipa": "briːtʃ",
        "word_type": "noun",
        "meaning": "hành vi vi phạm hợp đồng hoặc an ninh",
        "collocations": "breach of contract, security breach, commit a breach",
        "paraphrase_pair": "breach = violation = infraction = non-compliance",
        "example_sentence": "Failing to deliver source code on the agreed date constitutes a direct <span class='blank'>______</span> of contract.",
        "audio_word_url": "audio/words/breach.mp3",
        "audio_sentence_url": "audio/sentences/sentence_42.mp3"
    },
    {
        "id": 43,
        "category": "Legal & Contracts",
        "word": "binding",
        "ipa": "ˈbaɪndɪŋ",
        "word_type": "adjective",
        "meaning": "có tính ràng buộc về mặt pháp lý",
        "collocations": "legally binding agreement, binding contract, binding decision",
        "paraphrase_pair": "binding = mandatory = enforceable = obligating",
        "example_sentence": "Once signed by authorized representatives of both parties, the agreement becomes legally <span class='blank'>______</span>.",
        "audio_word_url": "audio/words/binding.mp3",
        "audio_sentence_url": "audio/sentences/sentence_43.mp3"
    },
    {
        "id": 44,
        "category": "Legal & Contracts",
        "word": "terminate",
        "ipa": "ˈtɜːmɪneɪt",
        "word_type": "verb",
        "meaning": "chấm dứt hiệu lực (hợp đồng, việc làm)",
        "collocations": "terminate an agreement, terminate employment, terminate prematurely",
        "paraphrase_pair": "terminate = end = cancel = discontinue",
        "example_sentence": "Either party reserves the legal right to <span class='blank'>______</span> the contract with thirty days written notice.",
        "audio_word_url": "audio/words/terminate.mp3",
        "audio_sentence_url": "audio/sentences/sentence_44.mp3"
    },
    {
        "id": 45,
        "category": "Legal & Contracts",
        "word": "clause",
        "ipa": "klɔːz",
        "word_type": "noun",
        "meaning": "điều khoản trong văn bản hợp đồng",
        "collocations": "confidentiality clause, penalty clause, include a clause",
        "paraphrase_pair": "clause = provision = stipulation = article",
        "example_sentence": "Please review Section 4 to verify the non-compete <span class='blank'>______</span> before signing the employment contract.",
        "audio_word_url": "audio/words/clause.mp3",
        "audio_sentence_url": "audio/sentences/sentence_45.mp3"
    },
    {
        "id": 46,
        "category": "Legal & Contracts",
        "word": "dispute",
        "ipa": "dɪˈspjuːt",
        "word_type": "noun",
        "meaning": "sự bất đồng, tranh chấp",
        "collocations": "settle a dispute, labor dispute, contractual dispute",
        "paraphrase_pair": "dispute = conflict = disagreement = controversy",
        "example_sentence": "Both companies agreed to hire an independent mediator to resolve their ongoing intellectual property <span class='blank'>______</span>.",
        "audio_word_url": "audio/words/dispute.mp3",
        "audio_sentence_url": "audio/sentences/sentence_46.mp3"
    },
    {
        "id": 47,
        "category": "Shipping & Logistics",
        "word": "freight",
        "ipa": "freɪt",
        "word_type": "noun",
        "meaning": "hàng hóa chuyên chở bằng đường biển/hàng không",
        "collocations": "freight charges, air freight, freight forwarder",
        "paraphrase_pair": "freight = cargo = shipment = goods",
        "example_sentence": "Due to soaring container shipping rates, international <span class='blank'>______</span> charges rose sharply this quarter.",
        "audio_word_url": "audio/words/freight.mp3",
        "audio_sentence_url": "audio/sentences/sentence_47.mp3"
    },
    {
        "id": 48,
        "category": "Shipping & Logistics",
        "word": "warehouse",
        "ipa": "ˈweəhaʊs",
        "word_type": "noun",
        "meaning": "kho bãi chứa hàng",
        "collocations": "central warehouse, warehouse inventory, store in a warehouse",
        "paraphrase_pair": "warehouse = storage facility = depot",
        "example_sentence": "All incoming electrical components are temporarily stored at the central distribution <span class='blank'>______</span>.",
        "audio_word_url": "audio/words/warehouse.mp3",
        "audio_sentence_url": "audio/sentences/sentence_48.mp3"
    },
    {
        "id": 49,
        "category": "Shipping & Logistics",
        "word": "dispatch",
        "ipa": "dɪˈspætʃ",
        "word_type": "verb",
        "meaning": "gửi đi, điều phối đơn hàng",
        "collocations": "dispatch an order, dispatch technicians, prompt dispatch",
        "paraphrase_pair": "dispatch = send out = ship = transmit",
        "example_sentence": "Our logistics operations team will <span class='blank'>______</span> your hardware package within twenty-four hours of payment.",
        "audio_word_url": "audio/words/dispatch.mp3",
        "audio_sentence_url": "audio/sentences/sentence_49.mp3"
    },
    {
        "id": 50,
        "category": "Personnel & Training",
        "word": "appraisal",
        "ipa": "əˈpreɪzl",
        "word_type": "noun",
        "meaning": "sự đánh giá hiệu suất công việc",
        "collocations": "performance appraisal, annual appraisal, employee appraisal",
        "paraphrase_pair": "appraisal = evaluation = assessment = review",
        "example_sentence": "Year-end salary increments are determined strictly based on the annual performance <span class='blank'>______</span>.",
        "audio_word_url": "audio/words/appraisal.mp3",
        "audio_sentence_url": "audio/sentences/sentence_50.mp3"
    },
    {
        "id": 51,
        "category": "Personnel & Training",
        "word": "mentor",
        "ipa": "ˈmentɔːr",
        "word_type": "noun",
        "meaning": "người hướng dẫn, cố vấn nghề nghiệp",
        "collocations": "assigned mentor, mentor program, career mentor",
        "paraphrase_pair": "mentor = adviser = coach = guide",
        "example_sentence": "Every junior backend engineer is assigned an experienced senior architect to serve as their professional <span class='blank'>______</span>.",
        "audio_word_url": "audio/words/mentor.mp3",
        "audio_sentence_url": "audio/sentences/sentence_51.mp3"
    },
    {
        "id": 52,
        "category": "Personnel & Training",
        "word": "turnover",
        "ipa": "ˈtɜːnəʊvər",
        "word_type": "noun",
        "meaning": "tỷ lệ luân chuyển nhân sự; doanh số",
        "collocations": "high staff turnover, reduce turnover, employee turnover rate",
        "paraphrase_pair": "turnover = staff attrition = churn rate",
        "example_sentence": "Human resources introduced hybrid work policies in an effort to curb high developer <span class='blank'>______</span>.",
        "audio_word_url": "audio/words/turnover.mp3",
        "audio_sentence_url": "audio/sentences/sentence_52.mp3"
    },
    {
        "id": 53,
        "category": "Personnel & Training",
        "word": "qualification",
        "ipa": "ˌkwɒlɪfɪˈkeɪʃn",
        "word_type": "noun",
        "meaning": "văn bằng, năng lực chuyên môn đạt chuẩn",
        "collocations": "professional qualification, minimum qualifications, possess qualifications",
        "paraphrase_pair": "qualification = credential = certification = capability",
        "example_sentence": "Candidates must possess relevant engineering <span class='blank'>______</span> and at least three years of microservices experience.",
        "audio_word_url": "audio/words/qualification.mp3",
        "audio_sentence_url": "audio/sentences/sentence_53.mp3"
    },
    {
        "id": 54,
        "category": "Personnel & Training",
        "word": "resign",
        "ipa": "rɪˈzaɪn",
        "word_type": "verb",
        "meaning": "từ chức, xin nghỉ việc",
        "collocations": "resign from one's position, tender resignation, decide to resign",
        "paraphrase_pair": "resign = step down = leave one's post = quit",
        "example_sentence": "The chief financial officer chose to <span class='blank'>______</span> in order to pursue personal entrepreneurial ventures.",
        "audio_word_url": "audio/words/resign.mp3",
        "audio_sentence_url": "audio/sentences/sentence_54.mp3"
    },
    {
        "id": 55,
        "category": "Corporate & Finance",
        "word": "negotiation",
        "ipa": "nɪˌɡəʊʃiˈeɪʃn",
        "word_type": "noun",
        "meaning": "cuộc đàm phán, thương lượng hợp đồng",
        "collocations": "contract negotiation, enter negotiations, successful negotiation",
        "paraphrase_pair": "negotiation = discussions = talks = bargaining",
        "example_sentence": "After weeks of intense <span class='blank'>______</span>, the vendor agreed to lower server rack maintenance fees by 10%.",
        "audio_word_url": "audio/words/negotiation.mp3",
        "audio_sentence_url": "audio/sentences/sentence_55.mp3"
    },
    {
        "id": 56,
        "category": "Banking & Accounting",
        "word": "invoice",
        "ipa": "ˈɪnvɔɪs",
        "word_type": "noun",
        "meaning": "hóa đơn thanh toán",
        "collocations": "issue an invoice, pay an invoice, itemized invoice",
        "paraphrase_pair": "invoice = bill = payment request = receipt",
        "example_sentence": "Please verify that the total figure on the supplier's <span class='blank'>______</span> matches the approved purchase order.",
        "audio_word_url": "audio/words/invoice.mp3",
        "audio_sentence_url": "audio/sentences/sentence_56.mp3"
    },
    {
        "id": 57,
        "category": "Technical & IT",
        "word": "overhaul",
        "ipa": "ˈəʊvəhɔːl",
        "word_type": "verb",
        "meaning": "đại tu, kiểm tra và nâng cấp toàn bộ",
        "collocations": "major overhaul, overhaul the system, complete overhaul",
        "paraphrase_pair": "overhaul = renovate = revamp = reconstruct",
        "example_sentence": "The IT director proposed to <span class='blank'>______</span> the legacy authentication system before the product launch.",
        "audio_word_url": "audio/words/overhaul.mp3",
        "audio_sentence_url": "audio/sentences/sentence_57.mp3"
    },
    {
        "id": 58,
        "category": "Human Resources",
        "word": "personnel",
        "ipa": "ˌpɜːsəˈnel",
        "word_type": "noun",
        "meaning": "toàn thể nhân viên, nhân sự",
        "collocations": "personnel department, trained personnel, key personnel",
        "paraphrase_pair": "personnel = staff = employees = workforce",
        "example_sentence": "Only authorized security <span class='blank'>______</span> are permitted to enter the main datacenter server room.",
        "audio_word_url": "audio/words/personnel.mp3",
        "audio_sentence_url": "audio/sentences/sentence_58.mp3"
    },
    {
        "id": 59,
        "category": "Human Resources",
        "word": "vacancy",
        "ipa": "ˈveɪkənsi",
        "word_type": "noun",
        "meaning": "vị trí tuyển dụng còn trống; phòng trống",
        "collocations": "job vacancy, fill a vacancy, current vacancies",
        "paraphrase_pair": "vacancy = opening = job position = available slot",
        "example_sentence": "The engineering team posted an urgent <span class='blank'>______</span> for a senior distributed systems architect.",
        "audio_word_url": "audio/words/vacancy.mp3",
        "audio_sentence_url": "audio/sentences/sentence_59.mp3"
    },
    {
        "id": 60,
        "category": "Marketing & Sales",
        "word": "prospective",
        "ipa": "prəˈspektɪv",
        "word_type": "adjective",
        "meaning": "tiềm năng, có triển vọng trong tương lai",
        "collocations": "prospective client, prospective buyer, prospective employee",
        "paraphrase_pair": "prospective = potential = future = expected",
        "example_sentence": "The sales team will host an online demonstration tomorrow for several <span class='blank'>______</span> enterprise clients.",
        "audio_word_url": "audio/words/prospective.mp3",
        "audio_sentence_url": "audio/sentences/sentence_60.mp3"
    }
]

def main():
    print("=== TOEIC LAB: EXPANDING CORPUS DATA ===")
    init_db()
    db = SessionLocal()

    try:
        # 1. Update MockTest total_questions
        test = db.query(MockTest).filter_by(test_id="ETS2024_01").first()
        if not test:
            test = MockTest(
                test_id="ETS2024_01",
                name="ETS TOEIC Regular Test 2024 - Test 01",
                year=2024,
                publisher="ETS",
                total_questions=200
            )
            db.add(test)
            db.commit()

        # 2. Ingest 30 Part 5 Questions (Q101 -> Q130)
        print("\n--- 1. Ingesting Full 30 Part 5 Questions (Q101 -> Q130) ---")
        q_count = 0
        for item in PART5_QUESTIONS:
            existing = db.query(TestQuestion).filter_by(
                test_id=item["test_id"],
                question_no=item["question_no"]
            ).first()

            if existing:
                # Update existing
                existing.part = item["part"]
                existing.sentence = item["sentence"]
                existing.choice_a = item["choice_a"]
                existing.choice_b = item["choice_b"]
                existing.choice_c = item["choice_c"]
                existing.choice_d = item["choice_d"]
                existing.correct_choice = item["correct_choice"]
                existing.explanation = item["explanation"]
                existing.distractor_analysis = item["distractor_analysis"]
                existing.paraphrase_pair = item["paraphrase_pair"]
            else:
                new_q = TestQuestion(
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
                    paraphrase_pair=item["paraphrase_pair"]
                )
                db.add(new_q)
            q_count += 1

        db.commit()
        print(f"  ✓ Processed {q_count} Part 5 questions (Q101 -> Q130) with 3D RCA analysis!")

        # 3. Ingest 40 Additional Flashcards (Total 60 Cards)
        print("\n--- 2. Ingesting 40 Additional Flashcards (Cards #21 -> #60) ---")
        fc_count = 0
        for item in ADDITIONAL_FLASHCARDS:
            # Match by word, never by id: an id may already belong to a card the learner added.
            existing_fc = db.query(Flashcard).filter(func.lower(Flashcard.word) == item["word"].lower()).first()
            if existing_fc:
                existing_fc.category = item["category"]
                existing_fc.ipa = item["ipa"]
                existing_fc.word_type = item["word_type"]
                existing_fc.meaning = item["meaning"]
                existing_fc.collocations = item["collocations"]
                existing_fc.paraphrase_pair = item["paraphrase_pair"]
                existing_fc.example_sentence = item["example_sentence"]
                existing_fc.audio_word_url = item["audio_word_url"]
                existing_fc.audio_sentence_url = item["audio_sentence_url"]
                card = existing_fc
            else:
                card = Flashcard(
                    category=item["category"],
                    word=item["word"],
                    ipa=item["ipa"],
                    word_type=item["word_type"],
                    meaning=item["meaning"],
                    collocations=item["collocations"],
                    paraphrase_pair=item["paraphrase_pair"],
                    example_sentence=item["example_sentence"],
                    audio_word_url=item["audio_word_url"],
                    audio_sentence_url=item["audio_sentence_url"]
                )
                if db.get(Flashcard, item["id"]) is None:
                    card.id = item["id"]  # keep the canonical id when it is free
                db.add(card)
                db.flush()

            # Ensure UserCardSRS record exists
            srs = db.query(UserCardSRS).filter_by(card_id=card.id, user_id=1).first()
            if not srs:
                srs = UserCardSRS(
                    user_id=1,
                    card_id=card.id,
                    ease_factor=2.5,
                    interval_days=1,
                    repetition_count=0,
                    state="new",
                    next_review_at=utcnow()
                )
                db.add(srs)
            fc_count += 1

        db.commit()
        print(f"  ✓ Ingested {fc_count} additional flashcards (Total 60 cards in database)!")

        # Summary check
        total_questions = db.query(TestQuestion).filter_by(test_id="ETS2024_01").count()
        total_cards = db.query(Flashcard).count()
        print(f"\n=== SUCCESS SUMMARY ===")
        print(f"  • Total Test Questions in ETS2024_01: {total_questions}")
        print(f"  • Total Flashcards in Vault: {total_cards}")

    except Exception as e:
        db.rollback()
        print(f"ERROR Expanding Corpus Data: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    main()
