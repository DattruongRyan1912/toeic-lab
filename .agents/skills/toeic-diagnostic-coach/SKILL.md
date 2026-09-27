---
name: toeic-diagnostic-coach
description: >-
  Chẩn đoán trình độ TOEIC hiện tại, phân tích điểm mạnh/điểm yếu theo từng Part, thiết lập lộ trình ôn luyện theo Sprint (4, 8, 12 tuần) theo các mục tiêu 550, 750, 850, 990 và điều phối kế hoạch học tập hàng ngày.
---

# TOEIC Diagnostic & Sprint Coach

Skill này giúp thiết lập mục tiêu điểm số, đánh giá thực lực hiện tại, tính điểm scale chuẩn xác và kiến tạo lộ trình học tập tối ưu hóa thời gian cho người đi làm / kỹ sư phần mềm.

## 1. Quy trình chẩn đoán (Diagnostic Flow)
1. **Thu thập thông tin đầu vào**:
   - Điểm số gần nhất (nếu đã từng thi thật hoặc thi thử, chia rõ Listening/Reading).
   - Điểm mục tiêu mong muốn và thời hạn (Deadline, ví dụ: 2 tháng, 3 tháng).
   - Quỹ thời gian có thể dành ra mỗi ngày (ví dụ: 1 tiếng ngày thường, 3 tiếng cuối tuần).
2. **Kiểm tra chẩn đoán nhanh (Mini Diagnostic Test)**:
   - Nếu học viên chưa từng thi thử, hướng dẫn làm Mini-Test 50 câu (Listening 25 câu, Reading 25 câu trích từ bộ đề ETS chuẩn).
   - Tính điểm ước lượng bằng script: `python scripts/score_calculator.py --l-raw <số câu đúng> --r-raw <số câu đúng>`.
3. **Phân tích khoảng cách (Gap Analysis)**:
   - Xác định chênh lệch số câu cần đúng ở từng Part để đạt mục tiêu.

## 2. Ma trận lộ trình Sprint theo mục tiêu

### Sprint A: Nền tảng 550+ (Thời gian: 4 - 6 tuần)
- **Mục tiêu câu đúng**: Listening ~65-70 câu (300-330đ), Reading ~55-60 câu (220-250đ).
- **Trọng tâm**:
  * Listening: Part 1 (luyện phản xạ tranh người/vật), Part 2 (học cách nghe từ để hỏi 5W1H và loại trừ phương án bẫy).
  * Reading: Hoàn thành 12 chuyên đề ngữ pháp Part 5 căn bản (Thì, Dạng từ, Giới từ, Liên từ).
  * Từ vựng: 600 từ vựng TOEIC cơ bản.

### Sprint B: Bứt phá 750+ (Thời gian: 6 - 8 tuần)
- **Mục tiêu câu đúng**: Listening ~80-85 câu (380-410đ), Reading ~75-80 câu (350-370đ).
- **Trọng tâm**:
  * Listening: Chuyển sang Part 3 & 4. Luyện kỹ thuật "đi trước băng" 30 giây, kỹ thuật chép chính tả (Dictation) để bắt trọn cụm từ nối âm.
  * Reading: Nâng tốc độ Part 5 xuống < 12 phút (đạt độ chính xác 25/30 câu). Làm chủ Part 6 và Part 7 đoạn đơn (Single Passages).
  * Từ vựng: 1000 Collocations công sở và kinh doanh.

### Sprint C: Thượng thừa 850 - 990 (Thời gian: 6 - 8 tuần)
- **Mục tiêu câu đúng**: Listening 90-98 câu (440-495đ), Reading 88-96 câu (420-495đ).
- **Trọng tâm**:
  * Listening: Khắc chế các câu ngụ ý (Inference), câu kết hợp biểu đồ (Graphic questions), luyện nghe các giọng Anh/Úc tốc độ 1.1x - 1.2x.
  * Reading: Làm chủ triệt để Part 7 đoạn kép (Double) và đoạn ba (Triple Passages). Kỹ năng liên kết thông tin chéo giữa 2-3 tài liệu.
  * Phân tích bẫy tinh vi: Bẫy suy diễn thái quá (over-generalization), bẫy mốc thời gian, bẫy điều kiện ngoại lệ.

## 3. Lịch học mẫu cho Kỹ sư phần mềm (10-12 giờ/tuần)
- **Thứ 2 (60 phút)**: Listening Part 2 & Part 3 (Dictation 3-5 đoạn hội thoại).
- **Thứ 3 (60 phút)**: Reading Part 5 & Part 6 (Luyện 30 câu Part 5 tốc độ cao + phân tích ngữ pháp).
- **Thứ 4 (60 phút)**: Vocabulary & Collocation SRS (Ôn Anki 50 từ + học 20 từ mới qua ngữ cảnh).
- **Thứ 5 (60 phút)**: Listening Part 4 (Shadowing 3 bài nói độc thoại).
- **Thứ 6 (60 phút)**: Reading Part 7 (Đọc sâu 3 bài đọc dài, xây dựng bảng Paraphrase).
- **Thứ 7 (150 phút)**: Mock Test thực chiến (Làm 1 test trọn vẹn 120 phút theo đồng hồ bấm giờ nghiêm ngặt).
- **Chủ nhật (90 phút)**: Deep Error Log Analysis (Phân tích toàn bộ câu sai của đề Thứ 7, bổ sung vào sổ tay bẫy).
