# 🎯 TOEIC Lab — Tự học TOEIC 800-900+ cho kỹ sư phần mềm

Ứng dụng tự học TOEIC gồm **FastAPI** (dữ liệu, chấm điểm, SRS, AI Mentor, TTS) và **Next.js** (giao diện chính), dùng chung một database SQLite. Phương pháp: Spaced Repetition (SM-2), phân tích lỗi theo 5 mã RCA, 12 chuyên đề cú pháp Part 5, AI Mentor có function calling.

## Kiến trúc

```text
Trình duyệt ──► Next.js apps/web (:3005)
                  └─ /api/* (BFF proxy, server-side) ──► FastAPI server/ (:8000) ──► SQLite server/data/toeic_lab.db
                                                           ├─ Edge TTS (giọng ETS, cache server/cache/)
                                                           ├─ Gemini / DeepSeek / OpenAI (function calling)
                                                           └─ /legacy/ : UI HTML tự chứa cũ (docs/)
```

| Thư mục | Vai trò |
| :--- | :--- |
| `apps/web/` | Giao diện chính (Next.js 16, Tailwind, base-ui). Xem `apps/web/README.md` |
| `server/` | API FastAPI: models, routers, services, tests. Xem `server/README.md` |
| `scripts/` | Seed database, CLI tính điểm, xuất Anki, công cụ sinh UI legacy |
| `lessons/` | Nội dung đầy đủ của bài học (`bai_NN_*.md`) — seed nạp vào database |
| `docs/` | UI HTML legacy + báo cáo kiến trúc (phục vụ tại `/legacy/`) |
| `templates/`, `decks/` | Mẫu error log / tracker, bộ thẻ Anki đã xuất |
| `.agents/`, `GEMINI.md`, `AGENTS.md` | Quy tắc & skill cho AI agent làm việc trong repo |

## Chạy nhanh (local)

Yêu cầu: Python 3.12+, Node 20+ và pnpm.

```bash
cp -n .env.example .env       # tùy chọn: thêm GEMINI_API_KEY hoặc DEEPSEEK_API_KEY
make install                  # .venv + dependencies backend & frontend
make seed                     # tạo/migrate DB, nạp 12 bài học, 60 thẻ từ vựng, 32 câu ETS (idempotent)
make dev-api                  # terminal 1 → http://127.0.0.1:8000/docs
make dev-web                  # terminal 2 → http://localhost:3005
```

Chạy bằng Docker (API + web, tự seed khi database trống):

```bash
docker compose up -d --build  # web :3005, API :8000
```

> ⚠️ Chưa có đăng nhập: app chạy ở chế độ một học viên (`user_id = 1`). Khi deploy lên VPS, đặt `API_BIND=127.0.0.1` / `WEB_BIND=127.0.0.1` và đưa ra ngoài qua reverse proxy có xác thực (Basic Auth, Cloudflare Access...).

## Cá nhân hoá & lộ trình thích ứng

- **Onboarding** (`/onboarding`): mục tiêu, ngày thi, điểm đầu vào, ngày học trong tuần, thẻ mới/ngày, Part ưu tiên, phong cách giải thích của AI. Đổi lại bất kỳ lúc nào ở *Cài đặt › Cá nhân hoá* hoặc nhờ AI Mentor.
- **Theo dõi quá trình học**: mỗi câu trả lời (đúng/sai, thời gian), phút học thật (chỉ tính khi tab mở và bạn đang tương tác), thời gian đọc bài, lượt ôn thẻ.
- **Mô hình kỹ năng** (*Phân tích*): mức thành thạo 12 chuyên đề / 7 Part (câu gần đây nặng ký hơn, điểm đầu vào làm điểm xuất phát), xu hướng, tốc độ so với nhịp thi, điểm dự đoán kèm khoảng tin cậy.
- **Kế hoạch 7 ngày** (*Lộ trình*, Dashboard): xếp theo số phút/ngày, chuyên đề yếu nhất, câu sai đến hạn ôn (1 → 3 → 7 ngày), thẻ SRS, mốc lộ trình và ngày thi (2 tuần cuối tăng thi thử bấm giờ). Nhiệm vụ tự tick khi bạn làm; bỏ qua / dời ngày / thêm nhiệm vụ riêng đều được giữ khi lập lại kế hoạch. Tuần trước hoàn thành dưới 50% thì kế hoạch mới tự nhẹ hơn 25% (tắt được).
- **AI agent**: 29 công cụ đọc/ghi gần như mọi dữ liệu học (hồ sơ, trí nhớ, thẻ từ & lịch SRS, Sổ lỗi, kế hoạch, lộ trình, câu luyện riêng, ghi chú bài, paraphrase, lịch nhắc). Mọi thay đổi có nhật ký và **hoàn tác** được (trong chat, Mentor, *Cài đặt › AI Mentor được làm gì*).

- **Báo cáo tuần** (*Phân tích*, xem lại các tuần trước): phút học so với mục tiêu, độ chính xác so với tuần trước, chuyên đề tiến bộ/đi xuống (so 2 ảnh chụp mô hình kỹ năng), câu sai đã nắm chắc, tỉ lệ nhớ thẻ, việc nên làm tuần tới. Đặt lịch nhắc loại *Báo cáo tuần* để nhận qua Telegram mỗi Chủ nhật; nhắc hằng ngày kèm danh sách nhiệm vụ còn lại hôm nay.

Báo cáo chu kỳ phát triển (QA, phản hồi người dùng, changelog, backlog): `docs/dev_cycle_report.html` — mở tại `http://127.0.0.1:8000/legacy/dev_cycle_report.html`.

## Các module được nối với nhau thế nào

- **Thi thử → Sổ lỗi → Lỗ hổng → Bài học**: nộp bài được chấm trên server; câu sai tự vào Sổ lỗi với mã RCA lấy từ tag bẫy của câu (`[Bẫy Vị Trí Trạng Từ]` → `GRAMMAR`, Bài 01; câu bỏ trống → `TIME`). Lỗi còn mở được gom thành lỗ hổng theo chủ đề; đánh dấu "Đã nắm chắc" thì lỗ hổng tự đóng. Làm lại sai cùng câu không tạo bản ghi trùng.
- **Bài học ↔ câu hỏi**: mỗi bài có độ chính xác, số câu luyện, số lỗi mở; có thể luyện riêng câu của chuyên đề (`/mock-tests?lesson=N`).
- **SRS**: phiên ôn chỉ gồm thẻ đến hạn + số thẻ mới/ngày theo hồ sơ (mặc định `SRS_NEW_CARDS_PER_DAY`); mỗi lượt ôn ghi cả thời gian trả lời để tính phút học, tỉ lệ nhớ và thẻ hay quên.
- **Dashboard / Topbar / Sidebar**: cùng một nguồn `GET /api/dashboard/stats` — tuần hiện tại, chuỗi ngày học (ngày có ≥ 1 phút học thật), nhiệm vụ hôm nay lấy từ kế hoạch 7 ngày, điểm dự đoán, phút học, câu sai đến hạn, số ngày đến kỳ thi.
- **AI Mentor**: prompt hệ thống gồm hồ sơ, mức thành thạo, kế hoạch hôm nay, trí nhớ về bạn và phong cách giải thích bạn chọn; hỏi về một câu thì gửi con trỏ câu hỏi, đáp án lấy từ ngân hàng đề (model không ghi đè được). Model tự đọc dữ liệu qua công cụ và chỉ thay đổi dữ liệu khi bạn yêu cầu. Không có API key → chế độ offline trả lời từ database và hiểu vài lệnh: “Kế hoạch hôm nay”, “Điểm yếu”, “Lập lại kế hoạch”, “Ghi nhớ: …”.
- **Điểm quy đổi**: một đường cong duy nhất (`server/services/scoring.py`) cho trang Phân tích, điểm ước lượng sau bài thi và CLI.
- **Nhắc học**: lưu trong database; gửi qua Telegram khi có `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID`.

## Lệnh thường dùng

```bash
make check                     # pytest + tsc + eslint + next build
make score L=78 R=72 T=800     # = python scripts/score_calculator.py --l-raw 78 --r-raw 72 --target 800
make anki                      # xuất Sổ tay từ vựng (database) ra decks/*.csv và decks/*.apkg
```

## Cấu hình

Toàn bộ biến môi trường có trong `.env.example`. API key chỉ đặt ở server (`.env`), trình duyệt không bao giờ nhận key. Mặc định model: `gemini-2.5-flash`, `deepseek-flash`, `gpt-4o-mini` — đổi bằng `GEMINI_MODEL` / `DEEPSEEK_MODEL` / `OPENAI_MODEL`.

## Dữ liệu học

`server/data/toeic_lab.db` chứa tiến độ thật (thẻ SRS, sổ lỗi, bài nộp, lịch sử chat). Server tự thêm cột mới khi khởi động (migration bổ sung, không xóa dữ liệu). Nên sao lưu trước khi nâng cấp: `cp server/data/toeic_lab.db server/data/backups/`.

## Phương pháp học (tóm tắt)

| Kỹ năng | Phương pháp | Cơ chế |
| :--- | :--- | :--- |
| Listening Part 1-2 | Dictation | Xóa điểm mù nối âm, nuốt âm, flap-T |
| Listening Part 3-4 | Shadowing + đọc trước câu hỏi 30s | Tăng tốc độ tiếp nhận, phản xạ không dịch |
| Reading Part 5-6 | Phân tích cấu trúc câu (≤ 20s/câu) | Tách câu từ loại (nhìn trước/sau) và câu từ vựng (collocation) |
| Reading Part 7 | 3-Pass Scanning & đối chiếu chéo | Định vị paraphrase, xử lý đoạn kép/ba |
| Từ vựng | SRS SM-2 + collocation | Ghi nhớ dài hạn theo ngữ cảnh |
| Chữa đề | Quy tắc 1-3, 5 mã RCA | `VOCAB`, `GRAMMAR`, `PHONETICS`, `TRAP`, `TIME` |
