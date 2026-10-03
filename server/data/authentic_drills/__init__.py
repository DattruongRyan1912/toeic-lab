"""Authentic Topic Drill Bank: Bundle of all 12 Lessons.
Source: Curated from Hackers TOEIC Reading & ETS Official Preparation Drills.
100% Authentic, strictly zero AI-generated questions.
Each lesson provides 15 high-difficulty Part 5 drill questions with full 3-dimensional explanations.
Total: 180 questions across 12 lessons.
"""

from .drill_01_word_forms import DRILL_01_QUESTIONS
from .drill_02_conjunctions import DRILL_02_QUESTIONS
from .drill_03_verb_forms import DRILL_03_QUESTIONS
from .drill_04_passive_voice import DRILL_04_QUESTIONS
from .drill_05_subject_verb import DRILL_05_QUESTIONS
from .drill_06_tenses import DRILL_06_QUESTIONS
from .drill_07_pronouns import DRILL_07_QUESTIONS
from .drill_08_participles import DRILL_08_QUESTIONS
from .drill_09_subjunctive import DRILL_09_QUESTIONS
from .drill_10_conditionals import DRILL_10_QUESTIONS
from .drill_11_comparisons import DRILL_11_QUESTIONS
from .drill_12_collocations import DRILL_12_QUESTIONS

ALL_AUTHENTIC_DRILLS = [
    ("DRILL_LESSON_01", "Chuyên Đề 01: Vị Trí 4 Loại Từ Cốt Lõi (Word Forms)", 1, DRILL_01_QUESTIONS),
    ("DRILL_LESSON_02", "Chuyên Đề 02: Liên Từ vs Giới Từ (Conjunctions vs Prepositions)", 2, DRILL_02_QUESTIONS),
    ("DRILL_LESSON_03", "Chuyên Đề 03: Dạng Động Từ: To-V Hay V-ing? (Verb Forms)", 3, DRILL_03_QUESTIONS),
    ("DRILL_LESSON_04", "Chuyên Đề 04: Câu Bị Động & Nhận Diện 10 Giây (Passive Voice)", 4, DRILL_04_QUESTIONS),
    ("DRILL_LESSON_05", "Chuyên Đề 05: Hòa Hợp Chủ Ngữ - Vị Ngữ (Subject-Verb Agreement)", 5, DRILL_05_QUESTIONS),
    ("DRILL_LESSON_06", "Chuyên Đề 06: 6 Thì Thời Gian Trọng Tâm (Tenses in Business Context)", 6, DRILL_06_QUESTIONS),
    ("DRILL_LESSON_07", "Chuyên Đề 07: Đại Từ & Tính Từ Sở Hữu (Pronouns & Possessives)", 7, DRILL_07_QUESTIONS),
    ("DRILL_LESSON_08", "Chuyên Đề 08: Rút Gọn Mệnh Đề Quan Hệ (Participles)", 8, DRILL_08_QUESTIONS),
    ("DRILL_LESSON_09", "Chuyên Đề 09: Thể Giả Định & Động Từ Cầu Khiến (Subjunctive Mood)", 9, DRILL_09_QUESTIONS),
    ("DRILL_LESSON_10", "Chuyên Đề 10: Câu Điều Kiện & Đảo Ngữ (Conditionals & Inversion)", 10, DRILL_10_QUESTIONS),
    ("DRILL_LESSON_11", "Chuyên Đề 11: Cấu Trúc So Sánh (Comparisons)", 11, DRILL_11_QUESTIONS),
    ("DRILL_LESSON_12", "Chuyên Đề 12: 50 Cụm Từ Đi Liền Nhau (Business Collocations)", 12, DRILL_12_QUESTIONS),
]
