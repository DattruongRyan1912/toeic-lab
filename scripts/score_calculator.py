#!/usr/bin/env python3
"""
TOEIC Score Calculator & Performance Diagnostic CLI Tool
Quy đổi điểm thô (0-100) Listening & Reading sang điểm scaled TOEIC (10-990).
Dùng chung đường cong với API web (server/services/scoring.py) nên kết quả luôn khớp nhau.
"""

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from server.services import scoring  # noqa: E402


def diagnose_performance(l_raw: int, r_raw: int, target: int) -> scoring.ScoreBreakdown:
    result = scoring.convert(l_raw, r_raw, target)

    print("=" * 65)
    print("           🎯 KẾT QUẢ ĐÁNH GIÁ NĂNG LỰC TOEIC")
    print("=" * 65)
    print(f"📊 Listening: {l_raw}/100 câu đúng  ➔  Điểm quy đổi: {result.scaled_listening}/495")
    print(f"📊 Reading:   {r_raw}/100 câu đúng  ➔  Điểm quy đổi: {result.scaled_reading}/495")
    print("-" * 65)
    print(f"🏆 TỔNG ĐIỂM TOEIC ƯỚC LƯỢNG: {result.total_score} / 990")
    print(f"🌐 Trình độ CEFR: {result.cefr_level}")
    print(f"   ({result.cefr_description})")
    print("=" * 65)

    print(f"\n🎯 Phân tích Mục tiêu: {target} điểm")
    if result.target_gap == 0:
        print(f"🎉 Xuất sắc! Bạn đã đạt mục tiêu (+{result.total_score - target} điểm).")
        print("   👉 Đề xuất nâng mục tiêu lên mốc tiếp theo.")
    else:
        print(f"⚠️  Khoảng cách cần bù đắp: {result.target_gap} điểm.")
        print(
            f"   💡 Cần thêm tối thiểu: Listening +{result.suggested_gain_listening} câu, "
            f"Reading +{result.suggested_gain_reading} câu."
        )

    print("\n🔍 ĐỀ XUẤT HÀNH ĐỘNG CỤ THỂ:")
    for tip in result.recommendations:
        print(f"  • {tip}")
    print("=" * 65)
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Tính điểm quy đổi TOEIC từ số câu đúng chuẩn ETS")
    parser.add_argument("--l-raw", type=int, required=True, help="Số câu đúng Listening (0 - 100)")
    parser.add_argument("--r-raw", type=int, required=True, help="Số câu đúng Reading (0 - 100)")
    parser.add_argument("--target", type=int, default=800, help="Điểm TOEIC mục tiêu (mặc định 800)")
    args = parser.parse_args(argv)

    if not (0 <= args.l_raw <= 100 and 0 <= args.r_raw <= 100):
        print("❌ Lỗi: Số câu đúng phải nằm trong khoảng từ 0 đến 100!")
        return 1
    diagnose_performance(args.l_raw, args.r_raw, args.target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
