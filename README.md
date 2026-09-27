# 🎯 Hệ Thống Tự Học TOEIC 800 - 900+ (Engineering-First)

Hệ sinh thái tự học TOEIC được cấu hình chuyên biệt cho kỹ sư phần mềm / backend developer, áp dụng phương pháp luận khoa học (Cognitive Science, Spaced Repetition, Root Cause Analysis) kết hợp cùng hệ thống **AI Mentor Antigravity đa kỹ năng**.

---

## 📁 Cấu Trúc Dự Án (Workspace Architecture)

```text
Tu_hoc_Toeic/
├── GEMINI.md                               # Cấu hình chính cho AI Mentor (Gemini/Antigravity)
├── AGENTS.md                               # Hướng dẫn đa Agent toàn cục
├── README.md                               # Tài liệu hướng dẫn sử dụng repo
├── .agents/
│   ├── rules/
│   │   └── toeic-study-rules.md            # Quy chuẩn học tập & phân loại 5 dạng bẫy
│   └── skills/
│       ├── toeic-diagnostic-coach/         # Skill 1: Chẩn đoán & Lập Sprint 4-8 tuần
│       ├── toeic-listening-mastery/        # Skill 2: Luyện nghe Dictation & Shadowing
│       ├── toeic-reading-mastery/          # Skill 3: Time-boxing 75 phút & 3-Pass Reading
│       ├── toeic-vocab-builder/            # Skill 4: Từ vựng Anki SRS & Paraphrase Vault
│       └── toeic-mock-test-analyst/        # Skill 5: Chữa đề 1-3 & Phân tích bẫy thi thử
├── templates/
│   ├── error_log_template.csv              # File CSV ghi nhật ký câu sai & mã lỗi
│   ├── paraphrase_notebook_template.md     # Sổ tay lưu trữ cặp từ đồng nghĩa
│   └── weekly_study_tracker.md             # Kế hoạch học tập & Retrospective theo tuần
├── scripts/
│   └── score_calculator.py                 # Công cụ CLI quy đổi điểm thô sang Scaled ETS
└── docs/
    └── toeic_study_guide.html              # Báo cáo HTML-First tương tác độc lập
```

---

## 🔬 Tóm Tắt Nghiên Cứu Phương Pháp Tự Học Hiệu Quả Nhất

| Kỹ năng / Lĩnh vực | Phương pháp tối ưu | Lợi ích & Cơ chế tác động |
| :--- | :--- | :--- |
| **Listening Part 1 & 2** | **Dictation (Chép chính tả)** | Xóa điểm mù âm thanh: nối âm (linking), nuốt âm (elision), biến âm flap-T. |
| **Listening Part 3 & 4** | **Shadowing + Đi trước băng 30s** | Tăng tốc độ tiếp nhận âm thanh lên 150-180 WPM, phản xạ không cần dịch tiếng Việt. |
| **Reading Part 5 & 6** | **Syntax Tree Parsing (20s/câu)** | Phân định rạch ròi câu Từ loại (nhìn trước sau) và câu Từ vựng (tìm Collocation). |
| **Reading Part 7** | **3-Pass Scanning & Cross-Referencing** | Định vị Paraphrase nhanh, liên kết thông tin giữa các đoạn kép/ba không bị quá tải. |
| **Từ vựng (Vocabulary)** | **Spaced Repetition (Anki) + Collocations** | Ghi nhớ dài hạn dựa trên thuật toán SM-2, tránh học từ đơn lẻ không ngữ cảnh. |
| **Chữa đề (Review)** | **Quy tắc 1 - 3 (Làm 1 giờ - Chữa 3 giờ)** | Phân loại lỗi sai theo 5 mã: `VOCAB`, `GRAMMAR`, `PHONETICS`, `TRAP`, `TIME`. |

---

## 🚀 Cách Bắt Đầu Học Cùng AI Mentor

### 1. Mở Tài Liệu & Bảng Tính Điểm Trực Quan (HTML-First)
Mở trực tiếp file `docs/toeic_study_guide.html` trên trình duyệt:
```bash
open docs/toeic_study_guide.html
```
Giao diện bao gồm:
- **Interactive Score Calculator**: Kéo thanh trượt số câu đúng Listening & Reading để xem điểm ước lượng, xếp hạng CEFR và phân tích khoảng cách đến mục tiêu (Gap Analysis).
- **Tab lộ trình Sprint**: Chọn xem Sprint 550+, 750-850+, hoặc 900-990.
- **Error Log Demo**: Bảng phân loại bẫy đề thi thực tế.

### 2. Sử Dụng CLI Tính Điểm Thô ➔ Điểm Scale ETS
Chạy lệnh trực tiếp từ terminal trong thư mục dự án:
```bash
# Ví dụ: Làm đúng 78 câu Listening, 72 câu Reading, mục tiêu 800
python3 scripts/score_calculator.py --l-raw 78 --r-raw 72 --target 800
```

### 3. Tương Tác Trực Tiếp Với AI Trong Đoạn Chat
Bạn chỉ cần gửi yêu cầu bằng tiếng Việt bình thường, ví dụ:
- *"Tôi vừa làm sai câu này: [Dán câu hỏi]. Hãy phân tích nguyên nhân sai và chỉ ra bẫy giúp tôi."*
- *"Tạo cho tôi 5 câu bài tập Dictation Part 2 về chủ đề Họp hành / Lịch trình."*
- *"Trích xuất các từ vựng quan trọng trong đoạn văn này thành bảng Anki Flashcard."*
- *"Lập kế hoạch học tuần 1 cho mục tiêu 850 điểm, mỗi ngày 1 tiếng."*
