# 🎙️ TOEIC Studio Audio Microservice (Backend)

Backend Microservice chuyên biệt phục vụ âm thanh chuẩn ETS cho dự án **TOEIC Lab**.

---

## 🌟 Tính Năng Cốt Lõi
1. **Microsoft Azure Neural TTS Engine**: Tích hợp các giọng phát thanh viên chuẩn ETS (Jenny, Guy - Mỹ; Sonia, Ryan - Anh; Natasha - Úc; Clara - Canada).
2. **MD5 Disk Caching**: Câu/từ nào đã phát 1 lần sẽ được lưu vào `cache/{hash}.mp3`, lần sau trả về với độ trễ **0ms** kèm header `Cache-Control: public, max-age=31536000, immutable`.
3. **CORS Enabled**: Cho phép gọi từ bất kỳ domain nào (GitHub Pages, localhost, domain riêng).
4. **All-in-One Serving**: Tự động mount thư mục `docs/` để serve toàn bộ ứng dụng web tĩnh trên cùng 1 cổng duy nhất.

---

## 🚀 Cách Chạy Nhanh Trên VPS

### Cách 1: Dùng Docker Compose (Khuyên dùng - 1 Click)
```bash
# Clone repo về VPS
git clone git@github.com:DattruongRyan1912/toeic-lab.git
cd toeic-lab

# Khởi động service chạy nền
docker compose up -d
```
Service sẽ lắng nghe tại cổng `http://your-vps-ip:8000`:
- Web UI & Audio: `http://your-vps-ip:8000/toeic_study_guide.html`
- Health check: `http://your-vps-ip:8000/health`
- Danh sách voice: `http://your-vps-ip:8000/api/voices`

---

### Cách 2: Chạy trực tiếp bằng Python venv / Systemd / PM2
```bash
cd toeic-lab
python3 -m venv server/.venv
source server/.venv/bin/activate
pip install -r server/requirements.txt

# Chạy server
uvicorn server.main:app --host 0.0.0.0 --port 8000
```

Hoặc dùng **PM2**:
```bash
pm2 start "server/.venv/bin/uvicorn server.main:app --host 0.0.0.0 --port 8000" --name "toeic-audio-api"
pm2 save
```

---

## 🛠️ API Reference

### 1. Health Check
`GET /health`
```json
{
  "status": "healthy",
  "service": "TOEIC Audio Engine",
  "cached_audio_count": 40
}
```

### 2. Danh sách giọng đọc
`GET /api/voices`

### 3. Tổng hợp âm thanh MP3
`GET /api/tts?text=postpone&voice=en-US-JennyNeural&rate=%2B0%25`
- Trả về: `Content-Type: audio/mpeg`
- Headers: `X-Audio-Cache: HIT` (nếu lấy từ đĩa) hoặc `MISS` (nếu vừa sinh mới).

---

## 📦 Kịch Bản Sinh Trước Audio Tĩnh (Pre-render)
Nếu bạn chỉ muốn host web tĩnh thuần (Nginx/Cloudflare Pages) mà không cần bật server Python:
```bash
python scripts/pre_render_audio.py
```
Toàn bộ file `.mp3` chất lượng cao sẽ được sinh vào:
- `docs/audio/words/*.mp3`
- `docs/audio/sentences/*.mp3`
