# Universal Agent Guidelines - TOEIC Self-Study Workspace

## Project Purpose
Workspace tự học, luyện thi TOEIC Listening & Reading đạt 800 - 900+ cho kỹ sư phần mềm, gồm:
1. Lộ trình học tập (Roadmaps & Sprints)
2. Thư viện kỹ năng tự học (Listening Dictation/Shadowing, Reading Skimming/Scanning, Vocabulary SRS, Mock Test Analysis)
3. Nhật ký lỗi sai (Error Logs) và Kho từ đồng nghĩa (Paraphrase Vaults)
4. Ứng dụng web full-stack (FastAPI + Next.js) và công cụ tính điểm, tạo flashcard

## General Working Rules for All Agents
1. **Language**: Giao tiếp bằng tiếng Việt thân thiện, súc tích, logic. Dùng thuật ngữ TOEIC chuẩn quốc tế.
2. **Quality of Explanations**: Mọi câu hỏi ngữ pháp hoặc đọc hiểu phải kèm dẫn chứng, phân tích bẫy (distractor analysis) và cặp từ đồng nghĩa (paraphrase pairs).
3. **HTML-First Reporting**: Báo cáo thi thử, tài liệu tổng quan, lộ trình học: ưu tiên HTML tự chứa (CSS/JS nhúng) trong `docs/`.
4. **Tools & Scripts**:
   - Quy đổi điểm: `python scripts/score_calculator.py` (cùng đường cong với web, nguồn: `server/services/scoring.py`).
   - Mẫu bảng trong `templates/` khi cập nhật error log hoặc lộ trình thủ công.

## Codebase Map (khi sửa ứng dụng)
- `server/` — FastAPI. Router mỏng trong `routers/`, logic trong `services/`:
  - `insights.py`: số liệu dashboard, streak, hoạt động, lỗ hổng, bài gợi ý, snapshot cho AI.
  - `curriculum.py`: tag bẫy `[Bẫy ...]` → mã RCA + bài học (Bài 01-12).
  - `scoring.py`: đường cong raw → scaled, CEFR (dùng chung API + CLI).
  - `ai_agent_service.py`: Gemini / OpenAI-compatible, function calling, chế độ offline.
  - `error_log_service.py` (lịch ôn câu sai 1→3→7 ngày), `vocab_service.py`, `srs_service.py`, `reminder_service.py`.
  - Cá nhân hoá: `activity.py` (phút học), `practice_service.py` (nộp bài đa đề, attempt + thời gian), `skills.py` (mastery, dự đoán), `planner.py` (kế hoạch 7 ngày, co giãn lộ trình), `coach.py` (gợi ý), `weekly_report.py` (báo cáo tuần), `profile_service.py`.
  - AI agent: `agent_tools.py` (registry tool đọc/ghi; tool ghi bắt buộc có thao tác hoàn tác + kết quả JSON-safe), `learner_context.py` (prompt cá nhân hoá).
- `apps/web/` — Next.js 16 (đọc `apps/web/AGENTS.md` trước khi viết code Next). Gọi API qua `lib/api.ts`; số liệu toàn app qua `lib/learner-store.ts`; types trong `types/index.ts` phải khớp `server/schemas/__init__.py`.
- `scripts/seed_database.py` — nạp nội dung (idempotent); nội dung bài học lấy từ `lessons/bai_NN_*.md`.

## Engineering Rules
1. **Một nguồn dữ liệu**: không hardcode số liệu học viên trên UI; thêm field vào API rồi đọc từ đó.
2. **Thời gian**: lưu UTC naive (`server.utils.timeutil.utcnow`); "hôm nay"/streak tính theo `APP_TIMEZONE`.
3. **Schema**: thêm cột mới ở dạng nullable (`database.init_db` tự `ALTER TABLE ADD COLUMN`); không xóa/đổi tên cột đang có dữ liệu.
4. **Bí mật**: API key chỉ nằm trong `.env` phía server; không đưa vào frontend, localStorage hay git.
5. **Database thật**: `server/data/toeic_lab.db` là dữ liệu học thật — sao lưu trước khi chạy script ghi dữ liệu; test luôn dùng DB tạm.
   Test nhiều ngày: dùng `timeutil.set_now()` / `timeutil.advance()` (conftest tự trả đồng hồ về thực sau mỗi test).
6. **Kiểm tra trước khi xong việc**: `make check` (pytest + tsc + eslint + next build).
