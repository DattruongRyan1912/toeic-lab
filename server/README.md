# TOEIC Lab API (FastAPI)

Backend của TOEIC Lab: dữ liệu học (SQLite qua SQLAlchemy), chấm bài, SRS SM-2, Sổ lỗi RCA, lỗ hổng kiến thức, AI Mentor (function calling) và Edge TTS. Giao diện chính là `apps/web` (gọi API qua BFF proxy); UI HTML cũ trong `docs/` được phục vụ tại `/legacy/`.

## Chạy

```bash
# từ thư mục gốc repo
python3 -m venv .venv && ./.venv/bin/pip install -r server/requirements-dev.txt
./.venv/bin/python scripts/seed_database.py     # tạo + migrate DB, nạp nội dung (idempotent)
./.venv/bin/python -m uvicorn server.main:app --host 127.0.0.1 --port 8000 --reload --reload-dir server
```

Swagger: `http://127.0.0.1:8000/docs`. Docker: `docker compose up -d --build` ở thư mục gốc (service `toeic-lab-app`, tự seed khi DB trống).

## Cấu trúc

| Đường dẫn | Nội dung |
| :--- | :--- |
| `main.py` | App, CORS, `/health` + `/api/health`, `/api/voices`, `/api/tts`, mount `/legacy` |
| `config.py` | Biến môi trường (xem `.env.example` ở gốc repo) |
| `database.py` | Engine, session, `init_db()` (tạo bảng + thêm cột nullable còn thiếu) |
| `models/`, `schemas/` | ORM models, Pydantic schemas (hợp đồng API — `apps/web/types` phải khớp) |
| `routers/` | Endpoint mỏng, gọi sang `services/` |
| `services/` | `insights` (dashboard, streak, gaps, gợi ý bài), `curriculum` (tag bẫy → RCA + bài), `scoring`, `ai_agent_service`, `error_log_service` (lịch ôn câu sai 1→3→7 ngày), `vocab_service`, `srs_service`, `reminder_service` |
| `services/` (cá nhân hoá) | `activity` (phút học thật), `practice_service` (nộp bài đa đề, review queue, smart set), `skills` (mastery, pace, dự đoán điểm), `planner` (kế hoạch 7 ngày, co giãn lộ trình, tự giảm tải), `coach` (gợi ý 1 chạm), `agent_tools` (29 tool AI, audit + hoàn tác), `weekly_report` (báo cáo 7 ngày, gửi Telegram), `learner_context` (prompt cá nhân hoá), `profile_service`, `maintenance` (backfill khi khởi động) |
| `tests/` | pytest với DB tạm, không gọi mạng (AI được giả lập bằng `httpx.MockTransport`) |

## API chính

| Nhóm | Endpoint |
| :--- | :--- |
| Hồ sơ | `GET/PATCH /api/users/me` = `GET/PATCH /api/learner/profile`, `POST /api/learner/onboarding` |
| Cá nhân hoá | `GET /api/learner/insights` (mastery, dự đoán, tốc độ, phút học), `GET /api/learner/weekly-report?end=`, `GET /api/learner/suggestions`, `GET/POST/PATCH/DELETE /api/learner/memories`, `POST /api/learner/activity` |
| Kế hoạch 7 ngày | `GET /api/plan/week`, `POST /api/plan/replan`, `POST /api/plan/items`, `PATCH/DELETE /api/plan/items/{id}` |
| Luyện tập | `POST /api/practice/submit` (đa đề, `mode`, `time_ms` từng câu), `GET /api/practice/review-queue`, `GET /api/practice/smart` |
| Dashboard | `GET /api/dashboard/stats` — tuần hiện tại, streak, hoạt động 7 ngày, nhiệm vụ hôm nay, lỗ hổng, bài gợi ý |
| Lộ trình | `GET/PATCH /api/roadmaps` (ngày bắt đầu), `PATCH /api/roadmaps/tasks/{id}` |
| Từ vựng & SRS | `GET/POST /api/flashcards`, `DELETE /api/flashcards/{id}`, `GET /api/flashcards/summary`, `GET /api/flashcards/due`, `POST /api/flashcards/{id}/review`, `POST /api/flashcards/ai-fill` |
| Đề thi | `GET /api/tests`, `GET /api/tests/{test}/questions?part=&lesson=`, `GET /api/tests/{test}/questions/{no}`, `POST /api/tests/{test}/submit`, `GET /api/tests/submissions`, `POST /api/tests/calculate-score` |
| Sổ lỗi | `GET/POST /api/error-logs`, `PATCH/DELETE /api/error-logs/{id}` |
| Bài học | `GET /api/knowledge/lessons`, `GET /api/knowledge/lessons/{n}` (nội dung, câu hỏi, ghi chú, tiến độ), `POST /api/knowledge/lessons/{n}/progress`, `GET/POST /api/knowledge/lessons/{n}/notes`, `DELETE /api/knowledge/lessons/{n}/notes/{id}`, `GET /api/knowledge/paraphrases` |
| AI Mentor | `POST /api/ai/chat`, `GET /api/ai/status`, `GET/DELETE /api/ai/history`, `GET /api/ai/tools`, `GET /api/ai/actions`, `POST /api/ai/actions/{id}/undo`, `POST /api/ai/actions/execute` |
| Nhắc học | `GET/POST /api/reminders` (`daily_study`, `review_error_log`, `srs_due`, `weekly_report` = Chủ nhật), `PATCH/DELETE /api/reminders/{id}` |
| Âm thanh | `GET /api/voices`, `GET /api/tts?text=&voice=&rate=` (giọng phải thuộc `/api/voices`, tốc độ ±50%) |

## Quy ước

- Thời gian lưu dạng UTC naive; "hôm nay", streak và lịch nhắc tính theo `APP_TIMEZONE` (mặc định `Asia/Ho_Chi_Minh`).
- Chế độ một học viên: `user_id` mặc định 1 (`deps.current_user_id`) — điểm duy nhất cần thay khi thêm xác thực.
- AI: `AI_PROVIDER=auto` chọn provider có key theo thứ tự gemini → deepseek → openai. Không có key hoặc provider lỗi → mentor offline: trả lời từ DB; chỉ vài lệnh rõ ràng mới ghi dữ liệu (“Ghi nhớ: …”, “Lập lại kế hoạch”), và vẫn đi qua tool có audit + hoàn tác.
- Tool AI mới: khai báo bằng `@_tool(...)` trong `services/agent_tools.py`; tool ghi phải trả thao tác hoàn tác (`op_delete`/`op_restore`…) và kết quả JSON-safe. Frontend lấy nhãn từ `apps/web/lib/actions.ts` (`TOOL_LABELS`).
- Kế hoạch: nhiệm vụ do planner tạo được tạo lại mỗi ngày/khi lập lại; quyết định của học viên (xong, bỏ qua, dời ngày, nhiệm vụ tự thêm) luôn được giữ.
- Nhắc học qua Telegram chạy nền trong process API khi có `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID`.

## Test

```bash
./.venv/bin/python -m pytest      # hoặc: make test
```

## Audio tĩnh (tùy chọn)

`python scripts/pre_render_audio.py` sinh sẵn MP3 vào `docs/audio/words/` và `docs/audio/sentences/` để host UI legacy dạng tĩnh mà không cần server.
