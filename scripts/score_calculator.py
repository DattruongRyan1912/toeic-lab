#!/usr/bin/env python3
"""
TOEIC Score Calculator & Performance Diagnostic CLI Tool
Quy đổi điểm thô (Raw Score: 0-100) Listening & Reading sang điểm scaled TOEIC (10-990)
theo chuẩn phân phối thống kê của ETS.
"""

import argparse
import sys

# ETS Scaled Score Mapping Tables (Standard Equating Curve)
# Mapping raw correct answers (0-100) to standard scaled score (5-495)
def get_listening_scaled(raw: int) -> int:
    if raw <= 0:
        return 5
    if raw >= 96:
        return 495
    if raw >= 93:
        return 490
    if raw >= 90:
        return 480
    if raw >= 85:
        return 450 + (raw - 85) * 6
    if raw >= 75:
        return 390 + (raw - 75) * 6
    if raw >= 65:
        return 330 + (raw - 65) * 6
    if raw >= 50:
        return 240 + (raw - 50) * 6
    if raw >= 35:
        return 150 + (raw - 35) * 6
    if raw >= 20:
        return 75 + (raw - 20) * 5
    return max(5, raw * 4)

def get_reading_scaled(raw: int) -> int:
    if raw <= 0:
        return 5
    if raw >= 97:
        return 495
    if raw >= 94:
        return 485
    if raw >= 90:
        return 460
    if raw >= 85:
        return 425 + (raw - 85) * 7
    if raw >= 75:
        return 360 + (raw - 75) * 6.5
    if raw >= 65:
        return 295 + (raw - 65) * 6.5
    if raw >= 50:
        return 205 + (raw - 50) * 6
    if raw >= 35:
        return 125 + (raw - 35) * 5.3
    if raw >= 20:
        return 65 + (raw - 20) * 4
    return max(5, raw * 3.25)

def get_cefr_level(total: int) -> tuple[str, str]:
    if total >= 945:
        return "C1 - Advanced Professional", "Khả năng giao tiếp và làm việc quốc tế hoàn hảo, tương đương người bản xứ."
    elif total >= 785:
        return "B2 - Working Proficiency", "Đủ điều kiện làm việc trong các tập đoàn đa quốc gia và môi trường kỹ thuật quốc tế."
    elif total >= 550:
        return "B1 - Independent User", "Giao tiếp căn bản trong công việc, hiểu các chủ đề thường nhật, cần trau dồi thêm từ vựng chuyên ngành."
    elif total >= 255:
        return "A2 - Elementary", "Giao tiếp đơn giản, nắm được ngữ pháp căn bản nhưng phản xạ nghe còn chậm."
    else:
        return "A1 - Beginner", "Cần xây dựng lại nền tảng ngữ pháp, phát âm và từ vựng cốt lõi."

def diagnose_performance(l_raw: int, r_raw: int, target: int):
    l_scale = int(round(get_listening_scaled(l_raw) / 5) * 5)
    r_scale = int(round(get_reading_scaled(r_raw) / 5) * 5)
    total_scale = l_scale + r_scale
    cefr, cefr_desc = get_cefr_level(total_scale)

    print("=" * 65)
    print("           🎯 KẾT QUẢ ĐÁNH GIÁ NĂNG LỰC TOEIC")
    print("=" * 65)
    print(f"📊 Listening: {l_raw}/100 câu đúng  ➔  Điểm quy đổi: {l_scale}/495")
    print(f"📊 Reading:   {r_raw}/100 câu đúng  ➔  Điểm quy đổi: {r_scale}/495")
    print("-" * 65)
    print(f"🏆 TỔNG ĐIỂM TOEIC ƯỚC LƯỢNG: {total_scale} / 990")
    print(f"🌐 Trình độ CEFR: {cefr}")
    print(f"   ({cefr_desc})")
    print("=" * 65)

    # Gap analysis
    if target:
        diff = target - total_scale
        print(f"\n🎯 Phân tích Mục tiêu: {target} điểm")
        if diff <= 0:
            print(f"🎉 Xuất sắc! Bạn đã vượt mục tiêu (+{abs(diff)} điểm).")
            print("   👉 Đề xuất nâng mục tiêu lên mốc tiếp theo để tối ưu hóa năng lực.")
        else:
            print(f"⚠️  Khoảng cách cần bù đắp: Cần tăng thêm {diff} điểm.")
            needed_l_raw = min(98, l_raw + max(3, diff // 10))
            needed_r_raw = min(98, r_raw + max(4, diff // 9))
            print(f"   💡 Đề xuất tăng số câu đúng: Listening +{needed_l_raw - l_raw} câu, Reading +{needed_r_raw - r_raw} câu.")

    print("\n🔍 ĐỀ XUẤT HÀNH ĐỘNG CỤ THỂ:")
    if l_raw < 70:
        print("  • Listening: Cần tập trung cao độ vào Part 1 & Part 2. Luyện nghe Dictation để bắt âm nối/nuốt.")
    elif l_raw < 85:
        print("  • Listening: Nâng cấp Part 3 & Part 4 bằng kỹ thuật Skimming 3 câu hỏi trước băng và Shadowing 1.0x.")
    else:
        print("  • Listening: Duy trì phong độ với các bài nói tốc độ 1.15x, xử lý các bẫy ngụ ý và giọng Úc/Anh.")

    if r_raw < 65:
        print("  • Reading: Củng cố 12 chuyên đề ngữ pháp Part 5. Đảm bảo tốc độ Part 5 không quá 15 phút.")
    elif r_raw < 80:
        print("  • Reading: Tối ưu hóa kỹ thuật 3-Pass Scanning cho Part 7 đoạn đơn, kiểm soát thời gian Part 5 < 12 phút.")
    else:
        print("  • Reading: Tập trung vào liên kết chéo đoạn kép/đoạn ba (Triple Passages) và Paraphrase Vault.")
    print("=" * 65)

def main():
    parser = argparse.ArgumentParser(description="Tính điểm quy đổi TOEIC từ số câu đúng chuẩn ETS")
    parser.add_argument("--l-raw", type=int, required=True, help="Số câu đúng Listening (0 - 100)")
    parser.add_argument("--r-raw", type=int, required=True, help="Số câu đúng Reading (0 - 100)")
    parser.add_argument("--target", type=int, default=800, help="Điểm TOEIC mục tiêu (mặc định 800)")

    args = parser.parse_args()
    if not (0 <= args.l_raw <= 100 and 0 <= args.r_raw <= 100):
        print("❌ Lỗi: Số câu đúng phải nằm trong khoảng từ 0 đến 100!")
        sys.exit(1)

    diagnose_performance(args.l_raw, args.r_raw, args.target)

if __name__ == "__main__":
    main()
