---
name: toeic-mock-test-analyst
description: >-
  Quy trình làm đề thi thử (Mock Test) chuẩn ETS/Hacker, phân tích chuyên sâu lỗi sai (Error Log & Distractor Analysis), quản lý tâm lý thi 120 phút và tính điểm scale chuẩn xác.
---

# TOEIC Mock Test Analyst & Performance Gate

Skill này chuẩn hóa quy trình giải đề thi thử, biến mỗi bài test 120 phút thành mỏ vàng kiến thức thông qua phân tích chuyên sâu (Deep Post-Test Review) theo quy tắc 1-3 (Làm 1 giờ - Chữa 3 giờ).

## 1. Môi trường thi thử chuẩn (Simulation Environment)
- **Thời gian**: Đúng 120 phút liên tục (Listening 45 phút, Reading 75 phút). Tuyệt đối không bấm tạm dừng (pause).
- **Công cụ**: Sử dụng phiếu trả lời trắc nghiệm (Answer Sheet tô chì), bút chì 2B và gôm tẩy. Không khoanh vào đề thi.
- **Thiết bị**: Nghe bằng loa ngoài với âm lượng phòng thi thật (không đeo tai nghe chụp tai chống ồn vì thi thật tại IIG dùng loa phòng).
- **Nguồn đề chuẩn**:
  * *ETS TOEIC Regular Test (2024, 2023, 2022)*: Giọng đọc và độ khó sát 100% đề thi thật tại Việt Nam.
  * *Hackers TOEIC 1, 2, 3*: Độ khó cao hơn thi thật 10-15%, dùng để rèn luyện sức bền và từ vựng nâng cao (mục tiêu 850+).
  * *YBM TOEIC*: Đề có các bẫy ngữ pháp và từ vựng lắt léo.

---

## 2. Quy trình chữa đề chuẩn 4 giai đoạn (The 4-Stage Review)

### Giai đoạn 1: Chấm điểm thô (Raw Scoring)
- Chỉ ghi lại câu đúng/sai, **chưa xem đáp án chi tiết**.
- Sử dụng script tính điểm: `python scripts/score_calculator.py --l-raw <số câu LC> --r-raw <số câu RC>`.

### Giai đoạn 2: Tự giải lại lần 2 không giới hạn thời gian (Untimed Re-test)
- Với những câu làm sai: Đọc lại kỹ lưỡng, không xem lời giải.
- Tự trả lời: *Nếu có thêm 2 phút, mình có chọn đúng không?*
  * Nếu chọn đúng ➔ Nguyên nhân do **Áp lực thời gian [TIME]**.
  * Nếu vẫn chọn sai ➔ Nguyên nhân do **Thiếu kiến thức [VOCAB/GRAMMAR/TRAP]**.

### Giai đoạn 3: So sánh Transcript / Lời giải chi tiết
- Nghe lại câu sai kết hợp nhìn Transcript.
- Xác định điểm mù âm thanh (Phonetics) hoặc bẫy lừa của người ra đề (Distractor Trap).

### Giai đoạn 4: Cập nhật Nhật ký lỗi sai (Error Log)
- Điền toàn bộ dữ liệu vào `templates/error_log_template.csv` hoặc bảng Markdown:
  * Mã đề, Số câu, Part
  * Loại lỗi (`VOCAB`, `GRAMMAR`, `PHONETICS`, `TRAP`, `TIME`)
  * Câu hỏi gốc
  * Đáp án đã chọn (sai) vs Đáp án đúng
  * Lý do vì sao chọn sai
  * Cặp Paraphrase hoặc điểm ngữ pháp cốt lõi
  * Biện pháp khắc phục

---

## 3. Phân loại 5 loại bẫy kinh điển (Distractor Taxonomy)
1. **Similar Sound Distractor (Bẫy từ phát âm na ná)**: Thường gặp ở Part 1, 2. (Ví dụ: *plant* vs *plan*, *coffee* vs *copy*).
2. **Opposite / Contradictory Trap (Bẫy thông tin đối lập)**: Thông tin có xuất hiện trong bài nhưng mang ý ngược lại (Ví dụ: bài nói *free for employees*, đáp án ghi *available for all public*).
3. **Out of Context / Irrelevant (Bẫy lạc đề)**: Câu trả lời nghe rất hợp lý trong đời sống nhưng không trả lời trọng tâm câu hỏi.
4. **Extreme Words (Bẫy từ mang tính tuyệt đối)**: Các đáp án chứa *always, never, only, completely, definitely* có tỷ lệ sai lên đến 85%.
5. **Partial Truth (Bẫy đúng một nửa)**: Nửa đầu của phương án hoàn toàn đúng với bài đọc, nhưng nửa sau bị đổi một chi tiết nhỏ (thời gian, địa điểm, đối tượng hưởng lợi).
