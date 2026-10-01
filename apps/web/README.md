# TOEIC Lab — Web app (Next.js 16)

Giao diện chính của TOEIC Lab. Mọi dữ liệu đến từ FastAPI (`server/`) qua route handler `app/api/[...path]/route.ts` (BFF proxy): trình duyệt chỉ gọi cùng origin `/api/*`, Next.js chuyển tiếp sang `BACKEND_URL` phía server.

## Chạy

```bash
pnpm install
cp -n .env.example .env.local   # BACKEND_URL, mặc định http://127.0.0.1:8000
pnpm dev                        # http://localhost:3005 (FastAPI phải đang chạy)
```

Kiểm tra trước khi commit: `pnpm exec tsc --noEmit && pnpm lint && pnpm build` (hoặc `make check` ở gốc repo).
Docker: `Dockerfile` build bản `output: "standalone"`; chạy cùng API bằng `docker compose up -d --build` ở gốc repo.

## Cấu trúc

| Đường dẫn | Nội dung |
| :--- | :--- |
| `app/(dashboard)/` | Các trang: Dashboard, Vocab (SRS), Mock tests, Lessons, Error log, Analytics, Roadmaps, Mentor, Settings |
| `app/api/[...path]/route.ts` | BFF proxy: chặn path traversal, chỉ chuyển header cần thiết, stream body (audio), timeout |
| `lib/api.ts`, `lib/use-api.ts` | Client fetch (thông báo lỗi FastAPI) và hook tải dữ liệu |
| `lib/learner-store.ts` | Số liệu học viên dùng chung (Topbar, Sidebar, Dashboard) — gọi `refreshLearner()` sau khi thay đổi dữ liệu |
| `lib/mentor-store.ts` | Hội thoại AI dùng chung cho trang `/mentor` và widget nổi; `askMentor()` mở widget kèm ngữ cảnh câu hỏi |
| `lib/settings.ts`, `lib/audio.ts` | Giọng đọc ETS đã chọn (localStorage) và phát âm (Edge TTS qua server, dự phòng giọng trình duyệt) |
| `modules/vocab`, `modules/mock-tests` | Flashcard player, kho từ, form thêm từ; phòng thi |
| `components/ui` | Primitive shadcn (base-ui) |
| `types/index.ts` | Kiểu dữ liệu, phải khớp `server/schemas/__init__.py` |

## Quy ước

- Không hardcode số liệu học viên trên UI: cần số mới thì thêm vào API.
- Không lưu API key ở frontend — key AI chỉ nằm trong `.env` của server.
- Next.js 16 có thay đổi phá vỡ so với bản cũ: đọc `node_modules/next/dist/docs/` trước khi dùng API lạ (xem `AGENTS.md`).
