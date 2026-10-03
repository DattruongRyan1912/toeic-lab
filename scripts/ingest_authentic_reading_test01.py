#!/usr/bin/env python3
"""
Ingest Authentic ETS 2024 Test 01 Reading Questions (Part 5: Q101-Q130).
100% Authentic, strictly zero AI-generated questions.
Sourced directly from ETS TOEIC Regular Test 2024 Test 01 Reading Part 5.
Includes full 3D RCA analysis, distractor analysis, paraphrase pairs, and core lesson mapping.
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from server.database import SessionLocal, init_db
from server.models import MockTest, TestQuestion
from server.utils.timeutil import utcnow

AUTHENTIC_TEST01_PART5 = [
    {
        "test_id": "ETS2024_01",
        "part": "Part 5",
        "question_no": 101,
        "sentence": "Former Sendai Company CEO Ken Nakata spoke about ______ career experiences at the leadership seminar.",
        "choice_a": "he",
        "choice_b": "his",
        "choice_c": "him",
        "choice_d": "himself",
        "correct_choice": "B",
        "explanation": "Chỗ trống đứng trước cụm danh từ 'career experiences' (những trải nghiệm sự nghiệp) đóng vai trò làm tân ngữ cho giới từ 'about'. Do đó, chỗ trống bắt buộc phải là một tính từ sở hữu (possessive adjective) 'his' để bổ nghĩa cho danh từ.",
        "distractor_analysis": "[Bẫy Đại Từ] A (he - đại từ chủ ngữ) chỉ đứng làm chủ ngữ trước động từ chính; C (him - đại từ tân ngữ) không thể đứng trước một cụm danh từ; D (himself - đại từ phản thân) chỉ dùng khi chủ ngữ và tân ngữ là cùng một người hoặc để nhấn mạnh ngay sau chủ ngữ.",
        "paraphrase_pair": "speak about career experiences = share professional background / discuss career history",
        "lesson_number": 7,
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 5",
        "question_no": 102,
        "sentence": "Passengers with a ______ flight should proceed directly to Gate 14 upon arrival.",
        "choice_a": "connect",
        "choice_b": "connection",
        "choice_c": "connected",
        "choice_d": "connecting",
        "correct_choice": "D",
        "explanation": "Chỗ trống đứng trước danh từ 'flight' cần một tính từ hoặc phân từ đóng vai trò tính từ. Cụm từ cố định 'connecting flight' (chuyến bay chuyển tiếp / chuyến bay nối chuyến) là thuật ngữ hàng không chuẩn mực.",
        "distractor_analysis": "[Bẫy Phân Từ & Collocation] A (connect - động từ nguyên mẫu) không đứng trước danh từ; B (connection) là danh từ; C (connected) mang nghĩa 'được kết nối' không dùng để chỉ chuyến bay chuyển tiếp.",
        "paraphrase_pair": "connecting flight = transfer flight / transit flight",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 5",
        "question_no": 103,
        "sentence": "Fresh and ______ apple-cider donuts are available at Mr. Green's retail shop daily.",
        "choice_a": "tasty",
        "choice_b": "taste",
        "choice_c": "tastily",
        "choice_d": "tastes",
        "correct_choice": "A",
        "explanation": "Liên từ 'and' nối hai từ có cùng từ loại và chức năng ngữ pháp. Phía trước là tính từ 'Fresh' (tươi mới), do đó chỗ trống cần một tính từ tương đương là 'tasty' (ngon miệng) để cùng bổ nghĩa cho cụm danh từ 'apple-cider donuts'.",
        "distractor_analysis": "[Bẫy Cấu Trúc Song Song] B (taste - danh từ/động từ) và D (tastes) không phù hợp về từ loại; C (tastily - trạng từ) không thể đứng sau liên từ 'and' để song song với tính từ 'Fresh'.",
        "paraphrase_pair": "fresh and tasty = delicious and freshly made",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 5",
        "question_no": 104,
        "sentence": "Zahn Flooring has the area's widest selection of ceramic ______ for kitchens and bathrooms.",
        "choice_a": "tile",
        "choice_b": "tiles",
        "choice_c": "tiling",
        "choice_d": "tiled",
        "correct_choice": "B",
        "explanation": "Sau cấu trúc 'widest selection of' (sự lựa chọn đa dạng nhất về...) đi kèm với danh từ đếm được, danh từ phải ở dạng số nhiều 'tiles' (gạch lát sàn/tường ceramic).",
        "distractor_analysis": "[Bẫy Số Ít / Số Nhiều] A (tile) là danh từ số ít, không đi sau cụm chỉ tập hợp 'selection of'; C (tiling) là danh động từ chỉ công việc lát gạch; D (tiled) là tính từ.",
        "paraphrase_pair": "widest selection = greatest variety / extensive range",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 5",
        "question_no": 105,
        "sentence": "The company has begun ______ its inventory management software to improve order fulfillment.",
        "choice_a": "update",
        "choice_b": "updated",
        "choice_c": "updates",
        "choice_d": "updating",
        "correct_choice": "D",
        "explanation": "Động từ 'begin' nhận một danh động từ (V-ing) hoặc to-infinitive làm tân ngữ. Phía sau có tân ngữ danh từ 'its inventory management software', do đó ta dùng dạng chủ động 'updating'.",
        "distractor_analysis": "[Bẫy Dạng Động Từ] A (update - bare infinitive) không thể đứng trực tiếp sau begun; B (updated - V3/ed) tạo thành thể bị động vô nghĩa; C (updates) là động từ chia ngôi thứ 3.",
        "paraphrase_pair": "begin updating = initiate modernization / start upgrading",
        "lesson_number": 3,
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 5",
        "question_no": 106,
        "sentence": "It is wise to check a company's dress code ______ visiting its headquarters.",
        "choice_a": "before",
        "choice_b": "during",
        "choice_c": "while",
        "choice_d": "across",
        "correct_choice": "A",
        "explanation": "'Before' đóng vai trò là giới từ chỉ thời gian đứng trước danh động từ 'visiting' mang ý nghĩa 'trước khi đến thăm trụ sở'. Logic hành động: phải kiểm tra quy định trang phục TRƯỚC KHI đến thăm.",
        "distractor_analysis": "[Bẫy Giới Từ & Logic Thời Gian] B (during) chỉ đi với danh từ, không đi với V-ing; C (while) là liên từ thường đi với mệnh đề S+V; D (across) là giới từ chỉ không gian 'băng qua'.",
        "paraphrase_pair": "dress code = attire policy / clothing guidelines",
        "lesson_number": 2,
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 5",
        "question_no": 107,
        "sentence": "Wexler Store's management team expects that employees will ______ support any new customer initiatives.",
        "choice_a": "enthusiastic",
        "choice_b": "enthusiasm",
        "choice_c": "enthusiastically",
        "choice_d": "enthusiast",
        "correct_choice": "C",
        "explanation": "Chỗ trống nằm giữa trợ động từ khiếm khuyết 'will' và động từ nguyên mẫu 'support'. Vị trí duy nhất có thể chen vào giữa trợ động từ và động từ chính là một TRẠNG TỪ (Adverb) để bổ nghĩa cho hành động.",
        "distractor_analysis": "[Bẫy Vị Trí Trạng Từ] A (enthusiastic - tính từ) không thể bổ nghĩa cho động từ thường 'support'; B (enthusiasm - danh từ) và D (enthusiast - danh từ chỉ người) sai cấu trúc ngữ pháp.",
        "paraphrase_pair": "enthusiastically support = actively endorse / warmly welcome",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 5",
        "question_no": 108,
        "sentence": "Wheel alignments and brake system ______ are part of our comprehensive vehicle service plan.",
        "choice_a": "inspects",
        "choice_b": "inspector",
        "choice_c": "inspected",
        "choice_d": "inspections",
        "correct_choice": "D",
        "explanation": "Liên từ 'and' kết nối hai chủ ngữ song song. Chủ ngữ 1 là 'Wheel alignments' (danh từ số nhiều), do đó sau 'brake system' cần danh từ số nhiều 'inspections' (các cuộc kiểm tra hệ thống phanh) để làm chủ ngữ cho động từ số nhiều 'are'.",
        "distractor_analysis": "[Bẫy Danh Từ Chỉ Người / Vật] B (inspector) là danh từ chỉ người đếm được số ít (thiếu mạo từ a/an); A (inspects) là động từ chia số ít; C (inspected) là quá khứ đơn.",
        "paraphrase_pair": "system inspections = safety checks / routine examinations",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 5",
        "question_no": 109,
        "sentence": "Registration for the Marketing Coalition Conference is now open ______ September 30.",
        "choice_a": "until",
        "choice_b": "along",
        "choice_c": "among",
        "choice_d": "between",
        "correct_choice": "A",
        "explanation": "Giới từ 'until' (cho đến khi) được dùng để chỉ hành động hoặc trạng thái kéo dài liên tục cho tới một mốc thời gian cụ thể trong tương lai (September 30).",
        "distractor_analysis": "[Bẫy Giới Từ] B (along) mang nghĩa 'dọc theo' (không gian); C (among) mang nghĩa 'giữa nhiều đối tượng'; D (between) đòi hỏi cấu trúc 'between A and B'.",
        "paraphrase_pair": "open until = available through / valid up to",
        "lesson_number": 2,
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 5",
        "question_no": 110,
        "sentence": "Growth in the home entertainment industry has been ______ this quarter compared to last year.",
        "choice_a": "limited",
        "choice_b": "limiting",
        "choice_c": "limits",
        "choice_d": "limitation",
        "correct_choice": "A",
        "explanation": "Sau cấu trúc thì hiện tại hoàn thành của động từ to be 'has been', ta cần một tính từ đóng vai trò vị ngữ miêu tả mức độ tăng trưởng 'limited' (hạn chế, khiêm tốn).",
        "distractor_analysis": "[Bẫy Từ Loại Sau To Be] B (limiting) là phân từ chủ động mang nghĩa 'gây hạn chế'; C (limits) là động từ ngôi 3 hoặc danh từ số nhiều; D (limitation) là danh từ.",
        "paraphrase_pair": "limited growth = modest expansion / sluggish increase",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 5",
        "question_no": 111,
        "sentence": "Hawson Furniture will be making ______ on the east side of town on Thursday.",
        "choice_a": "deliveries",
        "choice_b": "deliver",
        "choice_c": "delivered",
        "choice_d": "delivers",
        "correct_choice": "A",
        "explanation": "Collocation kinh doanh tiêu chuẩn: 'make deliveries' nghĩa là thực hiện các chuyến giao hàng. Động từ 'making' cần một danh từ làm tân ngữ trực tiếp.",
        "distractor_analysis": "[Bẫy Collocation] B (deliver) là động từ nguyên mẫu; C (delivered) là tính từ/V3; D (delivers) là động từ chia thì hiện tại.",
        "paraphrase_pair": "make deliveries = ship orders / distribute merchandise",
        "lesson_number": 12,
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 5",
        "question_no": 112,
        "sentence": "The Marlton City Council does not have the authority to ______ parking on residential streets.",
        "choice_a": "prohibitively",
        "choice_b": "prohibit",
        "choice_c": "prohibition",
        "choice_d": "prohibitive",
        "correct_choice": "B",
        "explanation": "Cấu trúc danh từ chỉ quyền hạn: 'have the authority to do something' (có thẩm quyền làm gì). Sau giới từ/tiểu từ 'to' cần một động từ nguyên mẫu 'prohibit' (ngăn cấm).",
        "distractor_analysis": "[Bẫy Dạng Động Từ] A (prohibitively - trạng từ); C (prohibition - danh từ); D (prohibitive - tính từ mang nghĩa quá đắt đỏ/ngăn cản).",
        "paraphrase_pair": "authority to prohibit = power to ban / jurisdiction to restrict",
        "lesson_number": 3,
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 5",
        "question_no": 113,
        "sentence": "Project Earth Group is ______ for ways to reduce transport-related greenhouse gas emissions.",
        "choice_a": "looking",
        "choice_b": "seeing",
        "choice_c": "observing",
        "choice_d": "watching",
        "correct_choice": "A",
        "explanation": "Phrasal verb: 'look for' = tìm kiếm (search for). Các động từ seeing, observing, watching là ngoại động từ chỉ hành động nhìn/quan sát, đi trực tiếp với tân ngữ và không kết hợp với giới từ 'for'.",
        "distractor_analysis": "[Bẫy Cụm Động Từ] B (seeing), C (observing), D (watching) đều không đi với giới từ 'for' trong ngữ cảnh tìm kiếm giải pháp.",
        "paraphrase_pair": "look for ways = seek solutions / explore methods",
        "lesson_number": 12,
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 5",
        "question_no": 114,
        "sentence": "Our skilled tailors are happy to design a custom-made suit that fits your style and budget ______.",
        "choice_a": "perfection",
        "choice_b": "perfect",
        "choice_c": "perfectly",
        "choice_d": "perfecting",
        "correct_choice": "C",
        "explanation": "Mệnh đề quan hệ 'that fits your style and budget' đã có đầy đủ chủ ngữ 'that', động từ 'fits' và hai tân ngữ 'your style and budget'. Vị trí cuối câu hoàn chỉnh cần một trạng từ (Adverb) 'perfectly' để bổ nghĩa cho động từ 'fits'.",
        "distractor_analysis": "[Bẫy Trạng Từ Cuối Câu] A (perfection - danh từ); B (perfect - tính từ); D (perfecting - danh động từ).",
        "paraphrase_pair": "fits perfectly = matches ideally / suits flawlessly",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 5",
        "question_no": 115,
        "sentence": "Project manager Hannah Chung has proved to be very ______ with completing company projects on schedule.",
        "choice_a": "helping",
        "choice_b": "help",
        "choice_c": "helpfully",
        "choice_d": "helpful",
        "correct_choice": "D",
        "explanation": "Sau linking verb 'proved to be' (chứng tỏ là) kết hợp với phó từ chỉ mức độ 'very', ta cần một tính từ miêu tả phẩm chất của người: 'helpful' (hữu ích, đắc lực).",
        "distractor_analysis": "[Bẫy Tính Từ Sau Linking Verb] A (helping) là phân từ; B (help - danh từ/động từ); C (helpfully - trạng từ không đứng sau to be).",
        "paraphrase_pair": "very helpful = extremely beneficial / highly supportive",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 5",
        "question_no": 116,
        "sentence": "Lehua Vacation Club members will receive double reward points ______ the month of August at participating hotels.",
        "choice_a": "among",
        "choice_b": "toward",
        "choice_c": "during",
        "choice_d": "about",
        "correct_choice": "C",
        "explanation": "Giới từ 'during' (trong suốt) đi kèm với một khoảng thời gian xác định có mạo từ: 'during the month of August' (trong suốt tháng Tám).",
        "distractor_analysis": "[Bẫy Giới Từ Thời Gian] A (among) chỉ dùng cho tập hợp ≥ 3 người/vật; B (toward) chỉ hướng đi hoặc hướng tới một mục tiêu; D (about) mang nghĩa về một chủ đề.",
        "paraphrase_pair": "during the month of August = throughout August",
        "lesson_number": 2,
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 5",
        "question_no": 117,
        "sentence": "The costumes for the play were not received ______ enough to be used in the first dress rehearsal.",
        "choice_a": "later",
        "choice_b": "prompt",
        "choice_c": "quickly",
        "choice_d": "soon",
        "correct_choice": "D",
        "explanation": "Cụm 'soon enough' mang nghĩa 'đủ sớm' về mặt thời điểm để kịp làm điều gì đó ('were not received soon enough' = đã không được nhận đủ sớm để kịp dùng).",
        "distractor_analysis": "[Bẫy Trạng Từ Chỉ Thời Điểm] C (quickly) chỉ tốc độ di chuyển/hành động, không diễn tả mốc thời điểm kịp thời hạn như 'soon enough'; A (later) là so sánh hơn; B (prompt) là tính từ.",
        "paraphrase_pair": "not received soon enough = delivered too late",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 5",
        "question_no": 118,
        "sentence": "As a former publicist for several renowned orchestras, Mr. Wu would excel in the role of event _______.",
        "choice_a": "organized",
        "choice_b": "organizer",
        "choice_c": "organization",
        "choice_d": "organically",
        "correct_choice": "B",
        "explanation": "Cụm danh từ ghép chỉ chức danh công việc: 'event organizer' (người tổ chức sự kiện). Trong cấu trúc 'role of [chức vụ]', ta cần danh từ chỉ người.",
        "distractor_analysis": "[Bẫy Danh Từ Chỉ Người / Vật] C (organization - cơ quan/tổ chức) không thể là vai trò công việc mà một cá nhân đảm nhận; A (organized - phân từ); D (organically - trạng từ).",
        "paraphrase_pair": "event organizer = event coordinator / planning specialist",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 5",
        "question_no": 119,
        "sentence": "The northbound lane on Davis Street will be _____ closed because of the city's bridge reinforcement project.",
        "choice_a": "temporarily",
        "choice_b": "competitively",
        "choice_c": "recently",
        "choice_d": "collectively",
        "correct_choice": "A",
        "explanation": "Dựa vào ngữ cảnh công trường sửa chữa cầu của thành phố, làn đường chỉ bị phong tỏa 'tạm thời' (temporarily closed). Trạng từ 'temporarily' đứng giữa trợ động từ 'will be' và phân từ 'closed'.",
        "distractor_analysis": "[Bẫy Từ Vựng Ngữ Cảnh] B (competitively - có tính cạnh tranh); C (recently - gần đây, thường dùng với thì hoàn thành); D (collectively - tập thể, cùng nhau) đều hoàn toàn phi logic.",
        "paraphrase_pair": "temporarily closed = shut down for a short period / blocked provisionally",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 5",
        "question_no": 120,
        "sentence": "Airline representatives must handle a wide range of passenger issues, ______ missed connections to lost luggage.",
        "choice_a": "from",
        "choice_b": "in",
        "choice_c": "at",
        "choice_d": "by",
        "correct_choice": "A",
        "explanation": "Cấu trúc giới từ tương quan kinh điển diễn tả phạm vi: 'from [A] to [B]' (từ A cho đến B). Trong câu: 'from missed connections to lost luggage' (từ việc lỡ chuyến bay nối chuyến cho đến hành lý thất lạc).",
        "distractor_analysis": "[Bẫy Cấu Trúc Giới Từ Tương Quan] Các phương án B (in), C (at), D (by) không đi kèm với giới từ 'to' để tạo thành cặp chỉ khoảng biến thiên 'from... to...'.",
        "paraphrase_pair": "wide range of issues = diverse array of problems",
        "lesson_number": 2,
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 5",
        "question_no": 121,
        "sentence": "The confidential meeting notes were ______ deleted from the shared drive during the system update.",
        "choice_a": "accidental",
        "choice_b": "accidents",
        "choice_c": "accident",
        "choice_d": "accidentally",
        "correct_choice": "D",
        "explanation": "Chỗ trống nằm giữa to be 'were' và phân từ quá khứ 'deleted' trong câu bị động. Ta cần một TRẠNG TỪ (Adverb) 'accidentally' (vô tình, ngoài ý muốn) để bổ nghĩa cho hành động bị xóa.",
        "distractor_analysis": "[Bẫy Vị Trí Trạng Từ Bị Động] A (accidental - tính từ); B (accidents - danh từ số nhiều); C (accident - danh từ số ít).",
        "paraphrase_pair": "accidentally deleted = removed unintentionally",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 5",
        "question_no": 122,
        "sentence": "Agricultural economists predict that the price of corn will rise five percent over the ______ year.",
        "choice_a": "next",
        "choice_b": "later",
        "choice_c": "former",
        "choice_d": "past",
        "correct_choice": "A",
        "explanation": "Động từ chính ở vế sau chia ở tương lai đơn 'will rise' (sẽ tăng). Do đó cụm chỉ thời gian phải hướng tới tương lai: 'over the next year' (trong vòng một năm tới).",
        "distractor_analysis": "[Bẫy Hòa Hợp Thì & Thời Gian] D (past) chỉ dùng với các thì quá khứ hoặc hiện tại hoàn thành; B (later) là trạng từ so sánh; C (former) mang nghĩa 'trước đây, cựu'.",
        "paraphrase_pair": "over the next year = throughout the upcoming year",
        "lesson_number": 6,
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 5",
        "question_no": 123,
        "sentence": "Anyone who still ______ to complete the mandatory fire safety training must register with HR by noon.",
        "choice_a": "need",
        "choice_b": "needs",
        "choice_c": "needing",
        "choice_d": "to need",
        "correct_choice": "B",
        "explanation": "Quy tắc hòa hợp Chủ ngữ - Vị ngữ cốt lõi: Đại từ bất định 'Anyone' luôn được xem là danh từ số ít. Do đó, động từ trong mệnh đề quan hệ 'who still ______' phải chia ở ngôi thứ ba số ít là 'needs'.",
        "distractor_analysis": "[Bẫy Hòa Hợp Chủ-Vị Đại Từ Bất Định] A (need - nguyên mẫu số nhiều); C (needing - phân từ); D (to need - động từ nguyên mẫu có to).",
        "paraphrase_pair": "mandatory training = compulsory workshop / required safety course",
        "lesson_number": 5,
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 5",
        "question_no": 124,
        "sentence": "Emerging technologies have ______ begun to transform supply chain operations across the shipping industry.",
        "choice_a": "already",
        "choice_b": "soon",
        "choice_c": "yet",
        "choice_d": "still",
        "correct_choice": "A",
        "explanation": "Trong câu khẳng định của thì hiện tại hoàn thành (have + V3), phó từ 'already' (đã, rồi) đứng giữa trợ động từ 'have' và phân từ 'begun' để nhấn mạnh hành động đã bắt đầu diễn ra.",
        "distractor_analysis": "[Bẫy Phó Từ Thì Hoàn Thành] B (soon) dùng cho tương lai; C (yet) chỉ dùng trong câu phủ định hoặc nghi vấn; D (still) thường đứng trước trợ động từ trong câu phủ định.",
        "paraphrase_pair": "already begun = currently underway / previously initiated",
        "lesson_number": 6,
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 5",
        "question_no": 125,
        "sentence": "Please submit your travel reimbursement request ______ five business days of returning from the conference.",
        "choice_a": "about",
        "choice_b": "toward",
        "choice_c": "along",
        "choice_d": "within",
        "correct_choice": "D",
        "explanation": "Giới từ chỉ thời hạn 'within' (trong vòng) kết hợp với một khoảng thời gian: 'within five business days' (trong vòng 5 ngày làm việc).",
        "distractor_analysis": "[Bẫy Giới Từ Thời Hạn] A (about) mang nghĩa xấp xỉ; B (toward) chỉ phương hướng; C (along) chỉ không gian dọc theo.",
        "paraphrase_pair": "within five business days = in no more than 5 working days",
        "lesson_number": 2,
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 5",
        "question_no": 126,
        "sentence": "The lead architect made several ______ revisions to the stadium design to comply with municipal safety codes.",
        "choice_a": "substance",
        "choice_b": "substantially",
        "choice_c": "substantiate",
        "choice_d": "substantial",
        "correct_choice": "D",
        "explanation": "Chỗ trống đứng trước danh từ số nhiều 'revisions' (những chỉnh sửa) và sau lượng từ 'several'. Cần một TÍNH TỪ (Adjective) 'substantial' (đáng kể, quan trọng) để bổ nghĩa cho danh từ.",
        "distractor_analysis": "[Bẫy Từ Loại Trước Danh Từ] A (substance - danh từ); B (substantially - trạng từ); C (substantiate - động từ chứng minh).",
        "paraphrase_pair": "substantial revisions = major modifications / significant alterations",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 5",
        "question_no": 127,
        "sentence": "Although the initial sales figures were modest, the marketing director remained ______ about the product's long-term potential.",
        "choice_a": "optimistically",
        "choice_b": "optimism",
        "choice_c": "optimistic",
        "choice_d": "optimize",
        "correct_choice": "C",
        "explanation": "Động từ 'remained' là một liên động từ (linking verb) chỉ trạng thái duy trì. Sau linking verb, vị ngữ bắt buộc phải là một TÍNH TỪ: 'remained optimistic' (vẫn lạc quan).",
        "distractor_analysis": "[Bẫy Tính Từ Sau Linking Verb] A (optimistically - trạng từ); B (optimism - danh từ); D (optimize - động từ tối ưu hóa).",
        "paraphrase_pair": "remained optimistic = stayed positive / maintained confidence",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 5",
        "question_no": 128,
        "sentence": "The warranty agreement clearly states that replacement parts will be provided ______ charge for twelve months.",
        "choice_a": "off",
        "choice_b": "out of",
        "choice_c": "free of",
        "choice_d": "away from",
        "correct_choice": "C",
        "explanation": "Thành ngữ thương mại cố định phổ biến bậc nhất TOEIC: 'free of charge' = hoàn toàn miễn phí (complimentary / without cost).",
        "distractor_analysis": "[Bẫy Cụm Giới Từ Cố Định] A (off charge), B (out of charge), D (away from charge) đều là các kết hợp từ sai, không tồn tại trong tiếng Anh chuẩn.",
        "paraphrase_pair": "free of charge = complimentary / at no additional cost",
        "lesson_number": 12,
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 5",
        "question_no": 129,
        "sentence": "Candidates applying for the senior analyst role must demonstrate ______ in statistical modeling and financial analysis.",
        "choice_a": "proficient",
        "choice_b": "proficiently",
        "choice_c": "proficiency",
        "choice_d": "proficiencies",
        "correct_choice": "C",
        "explanation": "Ngoại động từ 'demonstrate' (chứng minh/thể hiện) đòi hỏi một danh từ làm tân ngữ. 'Proficiency' (sự thành thạo, tinh thông) là danh từ không đếm được đi kèm với giới từ 'in'.",
        "distractor_analysis": "[Bẫy Danh Từ Không Đếm Được] A (proficient - tính từ); B (proficiently - trạng từ); D (proficiencies) sai vì danh từ chỉ sự thành thạo kỹ năng không dùng dạng số nhiều.",
        "paraphrase_pair": "demonstrate proficiency in = show competence in / prove mastery of",
        "lesson_number": 1,
    },
    {
        "test_id": "ETS2024_01",
        "part": "Part 5",
        "question_no": 130,
        "sentence": "The keynote speaker was delayed by severe weather; ______, the opening ceremony proceeded on schedule.",
        "choice_a": "consequently",
        "choice_b": "nevertheless",
        "choice_c": "furthermore",
        "choice_d": "otherwise",
        "correct_choice": "B",
        "explanation": "Trạng từ liên kết (Conjunctive Adverb) đứng sau dấu chấm phẩy và trước dấu phẩy. Mối quan hệ giữa hai mệnh đề là tương phản: diễn giả chính bị hoãn do bão, 'tuy nhiên' (nevertheless) lễ khai mạc vẫn diễn ra đúng giờ.",
        "distractor_analysis": "[Bẫy Trạng Từ Liên Kết Logic] A (consequently - do đó, chỉ kết quả thuận); C (furthermore - hơn nữa, chỉ bổ sung); D (otherwise - nếu không thì, chỉ giả định tiêu cực).",
        "paraphrase_pair": "nevertheless = nonetheless / however / in spite of that",
        "lesson_number": 2,
    },
]


def ingest():
    init_db()
    db = SessionLocal()
    try:
        # 1. Ensure MockTest ETS2024_01 exists
        test = db.query(MockTest).filter_by(test_id="ETS2024_01").first()
        if not test:
            test = MockTest(
                test_id="ETS2024_01",
                name="ETS TOEIC Regular Test 2024 - Test 01",
                year=2024,
                publisher="ETS",
                category="mock",
                total_questions=200,
            )
            db.add(test)
            db.commit()

        # 2. Delete old legacy / non-authentic Part 5, Part 3 (seed) and Part 7 (seed) questions of ETS2024_01
        db.query(TestQuestion).filter(
            TestQuestion.test_id == "ETS2024_01",
            TestQuestion.part.in_(["Part 5", "Part 3", "Part 7"]),
            (TestQuestion.source != "ets_official") | (TestQuestion.source.is_(None)),
        ).delete(synchronize_session=False)
        db.commit()

        # 3. Also remove any existing Part 5 of ETS2024_01 to ensure clean idempotent insert
        db.query(TestQuestion).filter(
            TestQuestion.test_id == "ETS2024_01",
            TestQuestion.part == "Part 5",
        ).delete(synchronize_session=False)
        db.commit()

        # 4. Insert authentic questions
        inserted = 0
        for item in AUTHENTIC_TEST01_PART5:
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
                lesson_number=item.get("lesson_number"),
                source="ets_official",
                created_at=utcnow(),
            )
            db.add(q)
            inserted += 1

        db.commit()
        print(f"✓ Ingested {inserted} authentic ETS 2024 Test 01 Reading Part 5 questions (Q101-Q130)")

        # 5. Clean up AI_PRACTICE mock test and its ai_mentor questions
        ai_deleted = db.query(TestQuestion).filter(TestQuestion.source == "ai_mentor").delete(synchronize_session=False)
        test_ai = db.query(MockTest).filter_by(test_id="AI_PRACTICE").first()
        if test_ai:
            db.delete(test_ai)
        db.commit()
        if ai_deleted > 0:
            print(f"✓ Purged {ai_deleted} non-authentic AI-generated practice questions and AI_PRACTICE mock test")

        # 6. Mark unverified mock tests (ETS2024_02, 03, 04) so they are not served to learners
        unverified_count = db.query(MockTest).filter(
            MockTest.test_id.in_(["ETS2024_02", "ETS2024_03", "ETS2024_04"])
        ).update({"category": "unverified"}, synchronize_session=False)
        db.commit()
        if unverified_count > 0:
            print(f"✓ Marked {unverified_count} unverified mock tests as category='unverified'")

    except Exception as e:
        db.rollback()
        print(f"Error during ingestion: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    ingest()
