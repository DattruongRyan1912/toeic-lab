# 🎯 TOEIC Lab — Nền Tảng Tự Học TOEIC 800 - 900+ Cho Kỹ Sư Phần Mềm

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI%200.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Frontend-Next.js%2016-black?logo=next.js&logoColor=white)](https://nextjs.org)
[![Python](https://img.shields.io/badge/Python-3.12%2B-blue?logo=python&logoColor=white)](https://python.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0%2B-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](https://www.docker.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**TOEIC Lab** là nền tảng tự học và luyện thi TOEIC Listening & Reading toàn diện hướng tới mục tiêu **750+ đến 900+** được thiết kế chuyên biệt cho Kỹ sư Phần mềm (Software Engineers / Backend Developers). Hệ thống kết hợp giữa phương pháp học khoa học (**Spaced Repetition SM-2**, **Root Cause Analysis 5 mã lỗi**, **Dictation & Shadowing**) và kiến trúc web full-stack hiện đại (**FastAPI + Next.js 16 + SQLite**).

---

## 🧭 Triết Lý Kỹ Thuật & Nguyên Tắc Cốt Lõi

1. **Thực lực thay vì mẹo vặt rẻ tiền (Engineering-First)**:
   - Xóa bỏ các mẹo suy đoán không căn cứ ("thấy từ này thì chọn đáp án kia").
   - Tập trung vào bản chất bài thi: Phản xạ âm thanh nối/nuốt âm (Connected Speech, Elision, Flap-T), cụm từ kinh doanh cố định (Collocations), phân tích cấu trúc cú pháp 10 giây (Syntax Parsing) và tư duy nhận diện từ đồng nghĩa (Paraphrasing).
2. **100% Học liệu chuẩn quốc tế (Strictly Zero AI-Generated Exam/Grammar Content)**:
   - Toàn bộ đề thi thử (Mock Tests) và câu hỏi rèn luyện (Topic Drills) được trích xuất và chuẩn hóa từ các bộ đề uy tín hàng đầu: **ETS TOEIC Regular Test 2020–2024** và **Hackers TOEIC (David Cho)**. Tuyệt đối không để AI tự bịa câu hỏi nhằm bảo đảm 100% văn phong thương mại và ma trận bẫy sát đề thi thật.
   - Lý thuyết ngữ pháp và ma trận từ loại trong `lessons/` được đối soát từ **Hackers TOEIC Grammar**, **Raymond Murphy English Grammar in Use** và **Barron's 600 Essential Words**.
   - AI chỉ giữ vai trò làm Master Mentor: phân tích 3 chiều, bóc tách nguyên nhân gốc (RCA), xây dựng kho từ đồng nghĩa Paraphrase Vault và huấn luyện phản xạ.
3. **Phân tích nguyên nhân gốc lỗi sai (Root Cause Analysis - RCA)**:
   - Mọi câu làm sai đều được phân loại tự động vào 5 nhóm nguyên nhân gốc:
     * `[VOCAB]`: Thiếu từ vựng hoặc hiểu sai nghĩa theo ngữ cảnh kinh doanh.
     * `[GRAMMAR]`: Sai cấu trúc ngữ pháp (thì, dạng động từ, mệnh đề quan hệ, liên từ/giới từ).
     * `[PHONETICS]`: Không nhận diện được âm thanh (nuốt âm, nối âm, biến âm, trọng âm, accent Anh/Úc).
     * `[TRAP]`: Mắc bẫy đề thi (bẫy từ đồng âm similar sound, bẫy phủ định ngầm, bẫy lệch thì/chủ ngữ).
     * `[TIME]`: Áp lực thời gian, đọc lướt ẩu hoặc bỏ trống.

---

## 🏛️ Kiến Trúc Hệ Thống (System Architecture)

```text
                                    ┌────────────────────────────────────────────────────────┐
                                    │                     TRÌNH DUYỆT                        │
                                    └──────────────┬─────────────────────────┬───────────────┘
                                                   │                         │
                                      (Web UI / JWT Auth)              (Audio Stream)
                                                   ▼                         │
                         ┌─────────────────────────────────────────┐         │
                         │          Next.js 16 (apps/web)          │         │
                         │    • App Router • Turbopack • Base UI   │         │
                         │    • Port :3005 (Local) / :18160 (VPS)  │         │
                         └────────────────────┬────────────────────┘         │
                                              │                              │
                                   BFF Reverse Proxy (/api/*)                │
                                              │                              │
                                              ▼                              ▼
                         ┌─────────────────────────────────────────────────────────┐
                         │                  FastAPI Backend (server/)              │
                         │             • Port :8000 (Local) / :18161 (VPS)         │
                         ├─────────────────────────────────────────────────────────┤
                         │  • Auth Router (JWT, bcrypt/Argon2, Multi-user)         │
                         │  • Scoring Service (ETS Scaled Score Curve & CEFR)      │
                         │  • Adaptive Study Planner (Rolling 7-day schedule)      │
                         │  • SRS Engine (SuperMemo SM-2 Interval Calculation)     │
                         │  • Skill Mastery Engine (Bayesian-decay skill tracking) │
                         │  • Edge TTS Engine (Microsoft Neural Voices, cache)     │
                         │  • AI Mentor Hub (Gemini / DeepSeek / OpenAI + 29 Tools)│
                         └────────────┬─────────────────────────────┬──────────────┘
                                      │                             │
                                      ▼                             ▼
                 ┌───────────────────────────────┐     ┌─────────────────────────┐
                 │       SQLite Database         │     │    External Services    │
                 │   (server/data/toeic_lab.db)  │     │  • Gemini / OpenAI API  │
                 │   • Non-destructive migration │     │  • Telegram Bot Alerts  │
                 │   • Safe transaction rollback │     │  • Edge TTS Neural API  │
                 └───────────────────────────────┘     └─────────────────────────┘
```

### Phân Bổ Thư Mục

| Thư mục | Vai trò |
| :--- | :--- |
| `apps/web/` | Giao diện người dùng Next.js 16, Tailwind CSS, Lucide Icons, Base UI, Zustand stores. Xem [`apps/web/README.md`](file:///Users/ryantruong/Project/Tu_hoc_Toeic/apps/web/README.md). |
| `server/` | Backend FastAPI: Routers, ORM Models, Schemas, Business Services, Test suite (103 tests). Xem [`server/README.md`](file:///Users/ryantruong/Project/Tu_hoc_Toeic/server/README.md). |
| `lessons/` | 12 bài giảng ngữ pháp cốt lõi Part 5 (`bai_01_*.md` đến `bai_12_*.md`) biên soạn theo chuẩn Hackers Grammar. |
| `scripts/` | Bộ công cụ trích xuất dữ liệu, nạp đề thi chuẩn ETS, cắt audio, tính điểm và xuất Anki. |
| `docs/` | Báo cáo chu kỳ phát triển, kiến trúc hệ thống HTML tự chứa (phục vụ tại `/legacy/`). |
| `templates/` | Mẫu tài liệu theo dõi tiến độ, bảng phân tích lỗi sai và lộ trình Sprint. |
| `decks/` | Tệp xuất bộ thẻ từ vựng Anki (`.apkg`, `.csv`) đồng bộ từ hệ thống. |
| `.agents/`, `AGENTS.md` | Bộ chỉ thị kỹ thuật, hướng dẫn tiêu chuẩn và kỹ năng chuyên biệt cho AI Agent trong repo. |

---

## 📚 Ngân Hàng Học Liệu Chuẩn Quốc Tế (Authentic Corpus)

Hệ thống được nạp sẵn kho tài nguyên học tập đã qua kiểm duyệt nghiêm ngặt:

1. **Đề thi thử ETS TOEIC Regular Test 2024 - Test 01**:
   - **Part 1 (6 câu)**: Toàn bộ ảnh màu độ nét cao kèm file audio gốc trích xuất từ đề thi ETS 2024.
   - **Part 2 (25 câu)**: Câu hỏi Q7 – Q31 với audio gốc bản quyền của giọng đọc ETS (Mỹ, Anh, Úc, Canada).
   - **Part 5 (30 câu)**: Câu hỏi Q101 – Q130 với đáp án chuẩn, phân tích bẫy 3 chiều (`[Bẫy ...]`), trích xuất cặp từ đồng nghĩa Paraphrase Vault và gắn thẻ bài học ngữ pháp tương ứng.
2. **12 Chuyên đề rèn phản xạ Part 5 (180 câu Topic Drills)**:
   - Các bộ đề `DRILL_LESSON_01` đến `DRILL_LESSON_12` (mỗi bộ 15 câu) trích xuất từ **Hackers TOEIC & ETS Grammar Drills**:
     * *Chuyên đề 01*: Vị trí 4 loại từ cốt lõi (Word Forms).
     * *Chuyên đề 02*: Liên từ vs Giới từ (Conjunctions vs Prepositions).
     * *Chuyên đề 03*: Dạng động từ: To-V hay V-ing? (Verb Forms).
     * *Chuyên đề 04*: Câu bị động & Nhận diện 10 giây (Passive Voice).
     * *Chuyên đề 05*: Hòa hợp Chủ ngữ - Vị ngữ (Subject-Verb Agreement).
     * *Chuyên đề 06*: 6 Thì thời gian trọng tâm (Tenses in Business Context).
     * *Chuyên đề 07*: Đại từ & Tính từ sở hữu (Pronouns & Possessives).
     * *Chuyên đề 08*: Rút gọn mệnh đề quan hệ & Phân từ (Participles).
     * *Chuyên đề 09*: Thể giả định & Động từ cầu khiến (Subjunctive Mood).
     * *Chuyên đề 10*: Câu điều kiện & Đảo ngữ (Conditionals & Inversion).
     * *Chuyên đề 11*: Cấu trúc so sánh (Comparisons).
     * *Chuyên đề 12*: 50 Cụm từ đi liền nhau kinh doanh (Business Collocations).
3. **698 Thẻ từ vựng thương mại chuẩn hóa (Flashcards SRS)**:
   - Bao quát 14+ chủ đề kinh doanh thiết yếu (*Computers & IT, General Business, Human Resources, Accounting & Finance, Contracts, Office Operations, Shipping & Logistics...*).
   - 100% ví dụ đã được chuẩn hóa về ngữ cảnh tiếng Anh thương mại hành chính thực tế, loại bỏ hoàn toàn các câu ví dụ gượng ép.
4. **12 Bài giảng ngữ pháp Part 5 chuyên sâu (`lessons/`)**:
   - Biên soạn theo công thức ngắn gọn, dễ nhớ, có bảng tổng hợp và nhận diện bẫy đề thi.

---

## 🚀 Các Phân Hệ Tính Năng Chính

### 1. Xác thực & Quản lý người dùng (Authentication & Multi-User)
- Hệ thống bảo mật với **JWT (JSON Web Token)**, mật khẩu mã hóa an toàn bằng bcrypt / Argon2.
- Đầy đủ tính năng Đăng ký, Đăng nhập, Hồ sơ cá nhân (`/settings`), hỗ trợ nhiều học viên học tập song song với tiến độ và Sổ lỗi độc lập.

### 2. Phòng thi thử & Luyện đề trực tuyến (`/mock-tests`)
- **Hai chế độ thi**: *Chế độ làm bài bấm giờ mô phỏng áp lực phòng thi* hoặc *Chế độ luyện tập từng câu (xem giải thích và bẫy ngay lập tức)*.
- **Bộ lọc thông minh**: Lọc theo Đề thi thử (Mock Test), Chuyên đề (Topic Drill) hoặc lọc câu hỏi theo Chuyên đề bài học ngữ pháp (`?lesson=N`).
- **Tự động chấm điểm & Phân tích RCA**: Sau khi nộp bài, điểm số được quy đổi sang thang điểm 10-990 theo đường cong ETS; các câu sai tự động chuyển thành bản ghi Sổ lỗi kèm phân loại RCA và gợi ý bài học cần ôn tập.

### 3. Phòng luyện nghe chuyên sâu (`/listening`)
- **Dictation (Chép chính tả)**: Nghe từng câu Part 1 & Part 2 với audio chuẩn ETS, gõ lại câu nghe được, đối soát transcript từng từ để xóa điểm mù nối âm và nuốt âm.
- **Shadowing (Nói nhại)**: Luyện nói đuổi theo giọng đọc bản xứ để rèn phản xạ âm thanh tự nhiên mà không cần dịch thầm sang tiếng Việt.
- **Tính năng hỗ trợ**: Tùy chỉnh tốc độ phát (0.75x, 1.0x, 1.25x), lặp lại câu không giới hạn, ẩn/hiện gợi ý và bản dịch song ngữ.

### 4. Hệ thống ghi nhớ từ vựng Spaced Repetition (`/vocab`)
- Thuật toán lặp lại ngắt quãng **SuperMemo SM-2** tối ưu hóa chu kỳ nhớ từ.
- Mỗi phiên học tính toán khoa học giữa *Số thẻ đến hạn ôn* và *Chỉ tiêu thẻ mới mỗi ngày* (mặc định 15 thẻ/ngày).
- Tích hợp phát âm chuẩn qua Microsoft Edge Neural TTS, đo lường tốc độ phản xạ và tỉ lệ ghi nhớ thành công.

### 5. Sổ lỗi & Bản đồ lỗ hổng kiến thức (`/error-log`)
- Quản lý toàn bộ câu hỏi làm sai từ các bài thi thử.
- Tự động gắn nhãn bẫy đề thi và phân loại vào 5 mã RCA.
- Chu kỳ ôn tập câu sai giãn cách **1 ngày → 3 ngày → 7 ngày**; khi học viên trả lời đúng trong các lần ôn tập tiếp theo, trạng thái lỗi sẽ được nâng dần lên *"Đã nắm chắc"* và tự động đóng lỗ hổng kiến thức tương ứng trên Dashboard.

### 6. Lộ trình học thích ứng 7 ngày (Adaptive Planner)
- Tự động lập kế hoạch tuần dựa trên:
  * Quỹ thời gian học mỗi ngày và các ngày học trong tuần của học viên.
  * Thẻ từ vựng SRS đến hạn ôn.
  * Câu sai trong Sổ lỗi cần làm lại.
  * Chuyên đề ngữ pháp có độ thành thạo (mastery) yếu nhất.
  * Mốc ngày thi thực tế (càng gần ngày thi càng tăng cường thi thử bấm giờ).
- Cơ chế co giãn thông minh: Nếu tuần trước học viên bận rộn hoàn thành dưới 50% mục tiêu, kế hoạch tuần mới sẽ tự động giảm tải 25% để tránh quá tải.

### 7. Báo cáo phân tích năng lực & Dự đoán điểm (`/analytics`)
- Biểu đồ mạng nhện (Radar Chart) đo lường độ thành thạo trên 12 chuyên đề cú pháp và 7 Part bài thi.
- Công cụ dự đoán điểm thi ETS dựa trên xác suất Bayesian decay (câu làm gần đây có trọng số lớn hơn).
- Báo cáo tiến độ tuần tự động (Weekly Summary) gửi thông báo về bot Telegram vào mỗi tối Chủ nhật.

### 8. AI Master Mentor (`/mentor`)
- Trợ giảng cá nhân hóa có nhận thức đầy đủ về hồ sơ học viên, điểm mạnh, điểm yếu, lịch sử lỗi sai và kế hoạch học trong ngày.
- Trang bị **29 function calling tools** giúp AI đọc/ghi dữ liệu học tập (thêm thẻ từ vựng, cập nhật kế hoạch, ghi nhớ ghi chú, tra cứu ngữ pháp).
- **Audit Trail & Undo**: Mọi thao tác ghi của AI đều lưu lịch sử và hỗ trợ **nút Hoàn tác (Undo)** 1-chạm nếu học viên muốn hủy bỏ thay đổi.
- **Chế độ Offline dự phòng**: Hoạt động mượt mà ngay cả khi không có API key AI (phản hồi dựa trên cơ sở dữ liệu nội bộ và các lệnh điều khiển cấu trúc).

---

## 🛠️ Hướng Dẫn Cài Đặt & Khởi Chạy

### Yêu Cầu Môi Trường
- **Python**: 3.12 trở lên
- **Node.js**: 20 trở lên
- **Package Manager**: `pnpm`
- **Docker & Docker Compose** (Tùy chọn, cho môi trường container)

---

### Cách 1: Khởi Chạy Cục Bộ (Local Development)

#### 1. Clone repository & cấu hình biến môi trường
```bash
git clone https://github.com/DattruongRyan1912/toeic-lab.git
cd toeic-lab
cp -n .env.example .env
```
*(Chỉnh sửa file `.env` nếu bạn muốn kích hoạt AI Mentor bằng API Key Gemini / OpenAI / DeepSeek hoặc nhận thông báo Telegram)*.

#### 2. Cài đặt toàn bộ dependencies (Backend + Frontend)
```bash
make install
```

#### 3. Khởi tạo cơ sở dữ liệu & nạp học liệu chuẩn
```bash
make seed
```
Lệnh trên thực hiện quá trình khởi tạo schema, migrate bảng dữ liệu, nạp 12 bài học lý thuyết, 698 thẻ từ vựng thương mại, 12 bộ chuyên đề Topic Drills (180 câu) và đề thi chuẩn ETS 2024 Test 01. Quá trình này hoàn toàn mang tính lũy kế (idempotent), an toàn khi chạy lại.

#### 4. Khởi chạy ứng dụng
Mở 2 cửa sổ terminal:

- **Terminal 1 (Backend API FastAPI)**:
  ```bash
  make dev-api
  ```
  ➜ Swagger UI API: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

- **Terminal 2 (Frontend Web Next.js)**:
  ```bash
  make dev-web
  ```
  ➜ Giao diện người dùng: [http://localhost:3005](http://localhost:3005) (hoặc `http://localhost:3000`)

---

### Cách 2: Khởi Chạy Bằng Docker Compose

Dành cho môi trường staging, VPS hoặc triển khai nhanh không cần cài môi trường Python/Node cục bộ:

```bash
# Khởi động cả 2 container backend và frontend
docker compose up -d --build
```

Container backend sẽ tự động kiểm tra cơ sở dữ liệu và nạp dữ liệu khởi tạo nếu database trống.
- **Web App**: `http://localhost:3005` (hoặc cổng cấu hình qua `WEB_PORT`)
- **API Backend**: `http://localhost:8000` (hoặc cổng cấu hình qua `HOST_PORT`)

Để dừng container:
```bash
docker compose down
```

---

## ⚙️ Cấu Hình Biến Môi Trường (`.env`)

Mọi thông số cấu hình đều được quản lý tại file `.env` phía server (tuyệt đối không để lộ ra frontend):

| Tên biến | Mặc định | Ý nghĩa |
| :--- | :--- | :--- |
| `AI_PROVIDER` | `auto` | Bộ chọn AI model: `auto` (chọn theo thứ tự Gemini ➔ DeepSeek ➔ OpenAI), hoặc chỉ định `gemini`, `deepseek`, `openai`, `offline`. |
| `GEMINI_API_KEY` | *(trống)* | API Key của Google Gemini AI. |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Tên model Gemini sử dụng. |
| `DEEPSEEK_API_KEY` | *(trống)* | API Key DeepSeek (OpenAI-compatible). |
| `DEEPSEEK_MODEL` | `deepseek-flash` | Model DeepSeek. |
| `OPENAI_API_KEY` | *(trống)* | API Key OpenAI. |
| `OPENAI_MODEL` | `gpt-4o-mini` | Model OpenAI. |
| `DATABASE_URL` | `sqlite:///server/data/toeic_lab.db` | Đường dẫn kết nối CSDL SQLite. |
| `APP_TIMEZONE` | `Asia/Ho_Chi_Minh` | Múi giờ ứng dụng để tính streak và nhiệm vụ hôm nay. |
| `SRS_NEW_CARDS_PER_DAY` | `15` | Số thẻ từ vựng mới mặc định nạp vào phiên học mỗi ngày. |
| `CORS_ORIGINS` | `http://localhost:3005,...` | Danh sách domain được phép gọi API trực tiếp. |
| `WEB_APP_URL` | `http://localhost:3005` | Địa chỉ web frontend chính. |
| `TELEGRAM_BOT_TOKEN` | *(trống)* | Token bot Telegram để gửi thông báo nhắc học & báo cáo tuần. |
| `TELEGRAM_CHAT_ID` | *(trống)* | Chat ID Telegram nhận thông báo. |
| `JWT_SECRET_KEY` | *(tự sinh)* | Secret key dùng để ký JSON Web Token xác thực học viên. |

---

## 🧪 Đảm Bảo Chất Lượng & Kiểm Thử (`make check`)

Dự án áp dụng quy chuẩn kiểm thử nghiêm ngặt trước khi bàn giao mã nguồn:

```bash
make check
```

Lệnh `make check` tự động thực hiện 3 bước kiểm tra toàn diện:
1. **Kiểm thử Backend (Pytest)**: Chạy toàn bộ **103 test cases** độc lập trên database tạm thời in-memory, mô phỏng đầy đủ các flow từ chấm bài, tính điểm, ghi Sổ lỗi, thuật toán SRS đến function calling của AI Mentor.
2. **Kiểm tra kiểu dữ liệu & Linting Frontend**: Chạy `tsc --noEmit` và `eslint` trên Next.js 16.
3. **Build thử nghiệm Production**: Chạy `next build` để phát hiện sớm các lỗi SSR / Dynamic rendering.

---

## 🧰 Các Lệnh CLI & Script Thường Dùng

| Lệnh | Cú pháp | Chức năng |
| :--- | :--- | :--- |
| **Quy đổi điểm TOEIC** | `make score L=78 R=72 T=800` | Quy đổi điểm thô Listening & Reading sang thang 10-990 theo đường cong chuẩn ETS. |
| **Xuất thẻ Anki** | `make anki` | Xuất toàn bộ từ vựng trong CSDL ra file Anki package (`decks/toeic_master.apkg`) và file CSV. |
| **Cắt audio đề thi** | `python scripts/slice_ets2024_test01_audio.py` | Cắt băng audio đề thi thật ETS 2024 Test 01 thành các file mp3 từng câu cho Part 1 và Part 2. |
| **Nạp câu hỏi Reading** | `python scripts/ingest_authentic_reading_test01.py` | Nạp 30 câu hỏi chuẩn xác Part 5 từ đề thi ETS 2024 Test 01. |
| **Nạp câu hỏi Drills** | `python scripts/ingest_authentic_drills.py` | Nạp 180 câu hỏi từ 12 chuyên đề Hackers & ETS Grammar Drills. |
| **Chuẩn hóa từ vựng** | `python scripts/normalize_flashcards_business.py` | Chuẩn hóa các câu ví dụ flashcard sang tiếng Anh thương mại quốc tế. |

---

## 🛡️ Quy Chuẩn Kỹ Thuật Dành Cho Đóng Góp Mã Nguồn

Khi tham gia phát triển dự án hoặc sử dụng AI coding agent, bắt buộc tuân thủ các quy tắc sau:

1. **Một nguồn chân lý duy nhất (Single Source of Truth)**:
   - Tuyệt đối không hardcode số liệu thống kê của học viên trên UI. Mọi chỉ số phải được tính toán từ API backend (`server/services/`).
2. **Quy chuẩn lưu trữ thời gian**:
   - Lưu thời gian vào database dưới dạng UTC naive (`server.utils.timeutil.utcnow`).
   - Mọi logic tính toán "hôm nay", chuỗi ngày học liên tục (streak) và lịch nhắc nhở phải dựa trên `APP_TIMEZONE`.
3. **Tiến hóa Schema không phá hủy (Non-Destructive Migrations)**:
   - Các cột mới bổ sung phải ở dạng nullable (`database.init_db()` sẽ tự động `ALTER TABLE ADD COLUMN` khi khởi động). Không xóa hoặc đổi tên các cột đang chứa dữ liệu học viên.
4. **Bảo mật tuyệt đối thông tin nhạy cảm**:
   - API Key và Secret token chỉ được đặt trong file `.env` của server; không bao giờ được commit lên git hay truyền về frontend.
5. **Cơ sở dữ liệu thật**:
   - `server/data/toeic_lab.db` là dữ liệu học tập thật. Luôn tạo bản sao lưu (`.bak`) trước khi chạy bất kỳ script chỉnh sửa dữ liệu hàng loạt nào.

---

## 📄 Bản Quyền & Giấy Phép

Dự án được phân phối dưới giấy phép **MIT License**. Các tài liệu đề thi và câu hỏi chuẩn trích dẫn từ ETS và Hackers TOEIC phục vụ mục đích học tập và nghiên cứu cá nhân phi thương mại.
