# Universal Agent Guidelines - TOEIC Self-Study Workspace

## Project Purpose
Workspace chuyên biệt phục vụ việc tự học, luyện thi TOEIC Listening & Reading đạt chuẩn 800 - 900+ cho kỹ sư phần mềm. Dự án quản lý:
1. Lộ trình học tập (Roadmaps & Sprints)
2. Thư viện kỹ năng tự học (Listening Dictation/Shadowing, Reading Skimming/Scanning, Vocabulary SRS, Mock Test Analysis)
3. Nhật ký lỗi sai (Error Logs) và Kho từ đồng nghĩa (Paraphrase Vaults)
4. Công cụ hỗ trợ tính điểm và tạo flashcard

## General Working Rules for All Agents
1. **Language**: Giao tiếp bằng tiếng Việt thân thiện, súc tích, logic. Sử dụng thuật ngữ TOEIC chuẩn quốc tế.
2. **Quality of Explanations**: Mọi câu hỏi ngữ pháp hoặc đọc hiểu phải kèm dẫn chứng, phân tích bẫy (distractor analysis) và cặp từ đồng nghĩa (paraphrase pairs).
3. **HTML-First Reporting**: Khi tạo báo cáo kết quả kiểm tra thử, tài liệu hướng dẫn tổng quan, lộ trình học tập, luôn ưu tiên xuất bản dưới định dạng HTML tự chứa (standalone HTML với CSS/JS nhúng).
4. **Tools & Scripts**:
   - Sử dụng các script trong `scripts/` (như `score_calculator.py`) khi cần quy đổi điểm thô sang điểm scale TOEIC.
   - Sử dụng mẫu bảng trong `templates/` khi cập nhật error log hoặc lộ trình học tập cho người dùng.
