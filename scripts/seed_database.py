#!/usr/bin/env python3
"""
Seed script to ingest canonical gold-standard learning materials into SQLite/PostgreSQL Database.
Includes:
1. Default User Profile (Backend Engineer, 800+ target)
2. 24-Week Roadmap & Sprint Tasks
3. 12 Core Syntax Lessons for Part 5 (Hackers Grammar)
4. Core Business Vocabulary Flashcards with SRS records
5. Paraphrase Vault pairs
6. Benchmark ETS 2024 Sample Test Questions with Distractor Analysis
7. Default Daily Study Reminder
"""

import re
import sys
from pathlib import Path
from typing import Optional

# Ensure project root in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from server.database import SessionLocal, init_db
from server.utils.timeutil import utcnow
from server.models import (
    User, Roadmap, SprintTask, Flashcard, UserCardSRS,
    KnowledgeLesson, ParaphrasePair, MockTest, TestQuestion, StudyReminder
)

LESSONS_DIR = BASE_DIR / "lessons"


def latex_to_markdown(markdown: str) -> str:
    """lessons/*.md write formulas as $$\\text{..}$$; the web app renders plain Markdown, so turn them into code spans."""

    def simplify(expr: str) -> str:
        previous = None
        while previous != expr:
            previous = expr
            expr = re.sub(r"\\(?:text|mathbf|mathrm|textbf)\{([^{}]*)\}", r"\1", expr)
        return expr.replace("\\,", " ").replace("\\ ", " ").strip()

    markdown = re.sub(r"\$\$(.+?)\$\$", lambda m: f"`{simplify(m.group(1))}`", markdown, flags=re.S)
    return re.sub(r"\$([^$\n]+?)\$", lambda m: simplify(m.group(1)), markdown)


def load_lesson_markdown(number: int) -> Optional[str]:
    """Full lesson content lives in lessons/bai_NN_*.md (single source for the web app and the DB)."""
    for path in sorted(LESSONS_DIR.glob(f"bai_{number:02d}_*.md")):
        text = path.read_text(encoding="utf-8")
        text = re.sub(r"^\s*#\s+.*\n", "", text, count=1)  # the title is rendered separately
        return latex_to_markdown(text).strip()
    return None


def seed_all():
    print("=== Initializing Database Schema ===")
    init_db()
    db = SessionLocal()

    try:
        # 1. Seed User
        print("\n--- 1. Seeding User Profile ---")
        user = db.query(User).filter_by(username="learner").first()
        if not user:
            user = User(
                username="learner",
                target_score=800,
                daily_goal_minutes=60
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"  ✓ Created user: {user.username} (ID: {user.id})")
        else:
            print(f"  • User {user.username} already exists (ID: {user.id})")

        # 2. Seed Roadmap & Sprint Tasks
        print("\n--- 2. Seeding 24-Week Roadmap & Sprints ---")
        roadmap = db.query(Roadmap).filter_by(user_id=user.id).first()
        if not roadmap:
            roadmap = Roadmap(
                user_id=user.id,
                title="Lộ trình 24 tuần Chinh phục TOEIC 800+ cho Backend Developer",
                total_weeks=24,
                current_week=1
            )
            db.add(roadmap)
            db.commit()
            db.refresh(roadmap)

            TASKS_DATA = [
                # Phase 1: Weeks 1 - 8
                (1, 1, "Syntax", "Bài 01: Vị trí 4 loại từ cốt lõi (Word Forms) & 5 câu bài tập", True),
                (1, 1, "Vocab", "Cài đặt Anki / SRS, import 50 thẻ từ vựng chủ đề Hợp đồng & Doanh nghiệp", True),
                (1, 2, "Listening", "Dictation 10 câu hỏi Part 2 (Dạng Who/Where/When) để xóa bẫy âm thanh", False),
                (1, 2, "Syntax", "Bài 02 (Liên từ vs Giới từ) & Bài 03 (Dạng động từ To-V / V-ing)", False),
                (1, 3, "Syntax", "Bài 04: Câu Bị động (Passive Voice) & Cách nhận diện trong 10 giây", False),
                (1, 4, "Syntax", "Bài 05 (Hòa hợp Chủ-Vị) & Bài 06 (6 Thì thời gian trọng tâm)", False),
                (1, 6, "Vocab", "Hoàn thành 300 từ vựng kinh doanh (Chủ đề 1-7 Hackers Vocab)", False),
                (1, 8, "Test", "Mini-Test chốt Phase 1: Mục tiêu đạt > 620 điểm ETS", False),

                # Phase 2: Weeks 9 - 16
                (2, 9, "Listening", "Kỹ thuật 'Đi trước băng 30s' cho Part 3 & 4; Shadowing tốc độ 1.0x", False),
                (2, 11, "Reading", "Rút ngắn thời gian Part 5 xuống dưới 12 phút (độ chính xác 24/30)", False),
                (2, 13, "Reading", "Kỹ thuật 3-Pass Scanning cho Part 7 đoạn đơn (Email, Memo, Notice)", False),
                (2, 15, "Reading", "Làm chủ các câu hỏi ngụ ý (Inference) và 50 cặp từ Paraphrase Vault", False),
                (2, 16, "Test", "Mini-Test chốt Phase 2: Mục tiêu đạt 700 - 750 điểm", False),

                # Phase 3: Weeks 17 - 24
                (3, 17, "Test", "Full Test 1 ETS 2024 (120 phút áp lực thật). Ghi nhật ký lỗi sai RCA", False),
                (3, 19, "Reading", "Khắc phục điểm yếu Triple Passages (Đoạn 3), kiểm soát Part 7 còn dư 3 phút", False),
                (3, 21, "Test", "Full Test 2 & 3 (Mục tiêu ổn định > 770 điểm trên 2 bài liên tiếp)", False),
                (3, 23, "Vocab", "Ôn lại toàn bộ Error Log và 150 cặp từ Paraphrase Vault", False),
                (3, 24, "Test", "Đăng ký thi thật tại IIG Việt Nam! Mục tiêu 800 - 850+", False)
            ]

            for phase, week, cat, title, done in TASKS_DATA:
                t = SprintTask(
                    roadmap_id=roadmap.id,
                    phase=phase,
                    week_number=week,
                    category=cat,
                    title=title,
                    is_completed=done,
                    completed_at=utcnow() if done else None
                )
                db.add(t)
            db.commit()
            print(f"  ✓ Seeded roadmap tasks ({len(TASKS_DATA)} tasks)")
        else:
            print("  • Roadmap tasks already exist")

        # 3. Seed 12 Syntax Lessons (Part 5 Hackers Grammar)
        print("\n--- 3. Seeding 12 Core Syntax Lessons ---")
        LESSONS_DATA = [
            (1, "Vị Trí 4 Loại Từ (Word Forms)", "Nouns, Verbs, Adjectives, Adverbs",
             "S + V + O | Adj + N | Adv + Adj/V | Giới từ + N/V-ing",
             "Nhận diện hậu tố (-tion, -ment, -able, -ly), 4 vị trí vàng, bẫy ngoại lệ đuôi -ly và -al."),
            (2, "Liên Từ vs Giới Từ (Conjunctions vs Prepositions)", "Because vs Because of, Although vs Despite",
             "Liên từ + Mệnh đề (S + V) | Giới từ + Cụm danh từ / V-ing",
             "Bí kíp 5 giây nhìn phía sau chỗ trống để loại trừ ngay 2 đáp án sai."),
            (3, "Dạng Động Từ: To-V hay V-ing?", "Gerunds vs Infinitives",
             "V + to-V (decide, plan, agree) | V + V-ing (consider, postpone, avoid)",
             "Danh sách 20 động từ kinh điển hay gặp nhất trong đề thi ETS."),
            (4, "Câu Bị Động & Cách Nhận Diện Trong 10 Giây", "Active vs Passive Voice",
             "Chủ động: S + V + O (có tân ngữ) | Bị động: S + be + V3/ed + (by O / giới từ)",
             "Quy tắc vàng: Nếu sau chỗ trống KHÔNG CÓ tân ngữ danh từ ➔ 90% chọn Bị động."),
            (5, "Hòa Hợp Chủ Ngữ - Vị Ngữ (Subject-Verb Agreement)", "Singular vs Plural Verbs",
             "S (số ít) ➔ V (thêm s/es) | S (số nhiều) ➔ V (nguyên mẫu)",
             "Bẫy xen kẽ cụm giới từ giữa S và V (The cost of these servers is/are...)."),
            (6, "6 Thì Thời Gian Trọng Tâm Trong Đề Thi TOEIC", "Tenses in Business Context",
             "Hiện tại đơn (lịch trình) | HT tiếp diễn | HT hoàn thành (since/for) | QK đơn | Tương lai đơn",
             "Dấu hiệu nhận biết nhanh trạng từ chỉ thời gian: recently, currently, already, yet."),
            (7, "Đại Từ & Tính Từ Sở Hữu", "Pronouns & Possessives",
             "S + V ➔ Chủ ngữ | V + O ➔ Tân ngữ | Tính từ sở hữu + N | Đại từ phản thân (-self)",
             "Bẫy đại từ phản thân đứng cuối câu để nhấn mạnh hành động tự thân."),
            (8, "Rút Gọn Mệnh Đề Quan Hệ (Participles)", "V-ing (chủ động) & V-ed (bị động)",
             "N + V-ing (chủ động làm gì) | N + V-ed (bị/được tác động)",
             "Một trong những dạng câu phân hóa điểm 750 - 850+ hay gặp nhất Part 5."),
            (9, "Thể Giả Định & Động Từ Cầu Khiến (Subjunctive Mood)", "Demand, Request, Recommend, Require",
             "S1 + recommend/require/suggest + that + S2 + (SHOULD) + V-nguyên mẫu",
             "Luôn chọn động từ nguyên thể dù S2 là he/she/it."),
            (10, "Câu Điều Kiện & Đảo Ngữ (Conditionals & Inversion)", "If types 1, 2 and Inversion",
             "Đảo ngữ loại 1: Should S + V | Loại 2: Were S to-V | Loại 3: Had S + V3/ed",
             "Dấu hiệu nhận biết khi đầu câu xuất hiện Should, Were hoặc Had đứng đầu."),
            (11, "Cấu Trúc So Sánh (Comparisons)", "Equal, Comparative, Superlative",
             "as...as | more...than / -er than | the most / -est | The more... the more...",
             "Bẫy trạng từ bổ nghĩa cho so sánh hơn: much, significantly, far, substantially."),
            (12, "50 Cụm Từ Đi Liền Nhau (Business Collocations)", "Office & Corporate Collocations",
             "unanimously approve | conduct a survey | strictly comply with | meet the deadline",
             "Cách giải câu từ vựng trong 3 giây nhờ thói quen phản xạ theo cụm cố định.")
        ]

        for num, title, subtitle, formula, summary in LESSONS_DATA:
            lesson = db.query(KnowledgeLesson).filter_by(lesson_number=num).first()
            content_md = load_lesson_markdown(num)
            if not lesson:
                lesson = KnowledgeLesson(
                    lesson_number=num,
                    title=f"Bài {num:02d}: {title}",
                    subtitle=subtitle,
                    syntax_formula=formula,
                    summary=summary,
                    content_html=f"<h3>{title}</h3><p><strong>Công thức cốt lõi:</strong> <code>{formula}</code></p><p>{summary}</p>",
                    content_md=content_md,
                    is_unlocked=True
                )
                db.add(lesson)
            elif content_md and lesson.content_md != content_md:
                lesson.content_md = content_md  # keep DB in sync with lessons/*.md
        db.commit()
        print("  ✓ Seeded 12 core syntax lessons (full content from lessons/*.md when available)")

        # 4. Seed Core Flashcards with Audio URLs
        print("\n--- 4. Seeding Core Vocabulary Flashcards & SRS ---")
        VOCAB_DATA = [
            ("General Business", "postpone", "pəʊstˈpəʊn", "verb", "hoãn lại, dời lịch", "postpone a meeting, postpone indefinitely", "postpone = delay = put off = defer", "The board of directors decided to postpone the annual shareholder meeting until next Friday.", "audio/words/postpone.mp3", "audio/sentences/1_postpone.mp3"),
            ("Corporate & Finance", "conduct", "kənˈdʌkt", "verb", "tiến hành, thực hiện", "conduct an audit, conduct a survey, conduct an inspection", "conduct = carry out = perform = execute", "The internal auditing committee will conduct a comprehensive inspection of financial records.", "audio/words/conduct.mp3", "audio/sentences/2_conduct.mp3"),
            ("Manufacturing & Compliance", "comply", "kəmˈplaɪ", "verb", "tuân thủ, tuân theo", "comply with safety regulations, comply with standards", "comply with = adhere to = conform to = abide by", "All manufacturing plants must strictly comply with environmental and workplace safety regulations.", "audio/words/comply.mp3", "audio/sentences/3_comply.mp3"),
            ("Human Resources", "eligible", "ˈelɪdʒəbl", "adjective", "đủ điều kiện, đủ tư cách", "eligible for a promotion, eligible for reimbursement", "eligible for = qualified for = entitled to", "Full-time software engineers are eligible for tuition reimbursement after six months of service.", "audio/words/eligible.mp3", "audio/sentences/4_eligible.mp3"),
            ("Finance & Expenses", "reimburse", "ˌriːɪmˈbɜːs", "verb", "hoàn tiền, bồi hoàn chi phí", "reimburse travel expenses, reimburse employees", "reimburse = compensate = pay back = refund", "Please submit your travel receipts so that the finance department can reimburse your business expenses.", "audio/words/reimburse.mp3", "audio/sentences/5_reimburse.mp3"),
            ("General Business", "unanimously", "juːˈnænɪməsli", "adverb", "nhất trí, đồng thuận 100%", "unanimously approved, unanimously agreed", "unanimously = with complete agreement = by consensus", "The shareholders unanimously approved the proposed merger with the technology firm.", "audio/words/unanimously.mp3", "audio/sentences/6_unanimously.mp3"),
            ("Purchasing & Warranty", "comprehensive", "ˌkɒmprɪˈhensɪv", "adjective", "toàn diện, bao quát", "comprehensive coverage, comprehensive training", "comprehensive = complete = thorough = all-inclusive", "The warranty provided with this server rack provides comprehensive coverage for hardware defects.", "audio/words/comprehensive.mp3", "audio/sentences/7_comprehensive.mp3"),
            ("Project Management", "tentative", "ˈentətɪv", "adjective", "dự kiến, thăm dò (chưa chốt)", "tentative agreement, tentative schedule", "tentative = provisional = subject to change", "The project timeline shared yesterday is only tentative and subject to change based on client feedback.", "audio/words/tentative.mp3", "audio/sentences/8_tentative.mp3"),
            ("Office Operations", "facilitate", "fəˈsɪlɪteɪt", "verb", "tạo điều kiện thuận lợi, thúc đẩy", "facilitate communication, facilitate growth", "facilitate = ease = promote = make easier", "The engineering department introduced a new ticketing system to facilitate cross-team collaboration.", "audio/words/facilitate.mp3", "audio/sentences/9_facilitate.mp3"),
            ("Finance & IT", "allocate", "ˈæləkeɪt", "verb", "phân bổ, chỉ định ngân sách/tài nguyên", "allocate funds, allocate resources", "allocate = assign = distribute = set aside", "The management agreed to allocate additional budget funds to upgrade cloud infrastructure.", "audio/words/allocate.mp3", "audio/sentences/10_allocate.mp3"),
            ("Purchasing & Contracts", "expire", "ɪkˈspaɪər", "verb", "hết hạn, hết hiệu lực", "expire at the end of, warranty expires", "expire = terminate = end = lapse", "Your subscription to the enterprise cloud platform will expire at the end of this billing cycle.", "audio/words/expire.mp3", "audio/sentences/11_expire.mp3"),
            ("Human Resources", "exceptional", "ɪkˈsepʃənl", "adjective", "xuất chúng, đặc biệt xuất sắc", "exceptional candidate, exceptional performance", "exceptional = outstanding = extraordinary", "The hiring manager noted that Mr. Tran is an exceptional candidate with strong distributed systems expertise.", "audio/words/exceptional.mp3", "audio/sentences/12_exceptional.mp3"),
            ("Shipping & Logistics", "anticipate", "ænˈtɪsɪpeɪt", "verb", "lường trước, dự đoán", "anticipate delays, anticipate growth", "anticipate = expect = foresee = predict", "The logistics provider does not anticipate any delivery delays despite the adverse weather conditions.", "audio/words/anticipate.mp3", "audio/sentences/13_anticipate.mp3"),
            ("Technical & IT", "implement", "ˈɪmplɪment", "verb", "triển khai, thi hành", "implement a policy, implement security measures", "implement = execute = apply = put into practice", "The security division will implement stricter authentication protocols across all production databases.", "audio/words/implement.mp3", "audio/sentences/14_implement.mp3"),
            ("Travel & Hospitality", "itinerary", "aɪˈtɪnərəri", "noun", "lịch trình chuyến đi", "travel itinerary, detailed itinerary", "itinerary = travel plan = schedule", "Please review the detailed flight itinerary sent by the travel agency before departing for Tokyo.", "audio/words/itinerary.mp3", "audio/sentences/15_itinerary.mp3"),
            ("Human Resources", "mandatory", "ˈmændətəri", "adjective", "bắt buộc", "mandatory attendance, mandatory training", "mandatory = compulsory = required = obligatory", "Attendance at tomorrow morning's orientation session is mandatory for all newly hired software engineers.", "audio/words/mandatory.mp3", "audio/sentences/16_mandatory.mp3"),
            ("Customer Service", "prompt", "prɒmpt", "adjective", "nhanh chóng, kịp thời", "prompt response, prompt delivery", "prompt = immediate = timely = quick", "Thank you for your prompt response to our customer inquiry regarding service availability.", "audio/words/prompt.mp3", "audio/sentences/17_prompt.mp3"),
            ("Finance & Sales", "substantially", "səbˈstænʃəli", "adverb", "đáng kể, rất nhiều", "substantially increase, substantially higher", "substantially = significantly = considerably", "Quarterly net revenues increased substantially following the launch of the new subscription model.", "audio/words/substantially.mp3", "audio/sentences/18_substantially.mp3"),
            ("Dining & Hospitality", "accommodate", "əˈkɒmədeɪt", "verb", "đáp ứng, chứa được, cung cấp chỗ", "accommodate guests, accommodate requests", "accommodate = serve = cater to = provide room for", "The conference venue is fully equipped to accommodate up to 500 attendees with specialized accessibility needs.", "audio/words/accommodate.mp3", "audio/sentences/19_accommodate.mp3"),
            ("Human Resources & Legal", "confidential", "ˌkɒnfɪˈdenʃl", "adjective", "bảo mật, tuyệt mật", "strictly confidential, confidential information", "confidential = secret = private = non-public", "All employee compensation records and personnel files must remain strictly confidential.", "audio/words/confidential.mp3", "audio/sentences/20_confidential.mp3")
        ]

        card_count = 0
        for cat, word, ipa, wtype, meaning, colloc, para, sentence, a_word, a_sent in VOCAB_DATA:
            card = db.query(Flashcard).filter_by(word=word).first()
            if not card:
                card = Flashcard(
                    category=cat,
                    word=word,
                    ipa=ipa,
                    word_type=wtype,
                    meaning=meaning,
                    collocations=colloc,
                    paraphrase_pair=para,
                    example_sentence=sentence,
                    audio_word_url=a_word,
                    audio_sentence_url=a_sent
                )
                db.add(card)
                db.commit()
                db.refresh(card)

            # Link SRS to user
            srs = db.query(UserCardSRS).filter_by(user_id=user.id, card_id=card.id).first()
            if not srs:
                srs = UserCardSRS(
                    user_id=user.id,
                    card_id=card.id,
                    state="new",
                    interval_days=1,
                    ease_factor=2.5,
                    repetition_count=0,
                    next_review_at=utcnow()
                )
                db.add(srs)
            card_count += 1

        db.commit()
        print(f"  ✓ Seeded {card_count} flashcards with SM-2 SRS tracking")

        # 5. Seed Paraphrase Vault Pairs
        print("\n--- 5. Seeding Paraphrase Vault ---")
        PARAPHRASE_DATA = [
            ("postpone", "delay / put off / defer", "hoãn lại lịch trình", "Part 7 Email & Notices"),
            ("conduct a survey", "carry out an inspection / poll", "tiến hành khảo sát/kiểm tra", "Part 7 Articles"),
            ("strictly comply with", "adhere to / abide by / conform to", "tuân thủ nghiêm ngặt quy định", "Part 5 & Part 7"),
            ("eligible for", "qualified for / entitled to", "đủ điều kiện hưởng quyền lợi", "Part 5 Human Resources"),
            ("reimburse expenses", "compensate / pay back / refund", "hoàn trả chi phí công tác", "Part 7 Travel policy"),
            ("comprehensive coverage", "full / thorough / all-inclusive", "chế độ bảo hành toàn diện", "Part 7 Warranty"),
            ("tentative schedule", "provisional / subject to change", "lịch trình dự kiến (chưa chốt)", "Part 7 Meeting schedule"),
            ("mandatory attendance", "compulsory / required / obligatory", "tham gia bắt buộc", "Part 7 Office memo"),
            ("substantially increase", "significantly / considerably grow", "tăng trưởng đáng kể", "Part 7 Financial report"),
            ("complimentary", "free of charge / at no cost", "miễn phí kèm theo", "Part 7 Hospitality")
        ]

        for word, syn, meaning, part in PARAPHRASE_DATA:
            p = db.query(ParaphrasePair).filter_by(word_in_text=word).first()
            if not p:
                p = ParaphrasePair(
                    word_in_text=word,
                    word_in_answer=syn,
                    meaning=meaning,
                    part_target=part
                )
                db.add(p)
        db.commit()
        print(f"  ✓ Seeded {len(PARAPHRASE_DATA)} core Paraphrase pairs")

        # 6. Seed Benchmark Test & Sample Questions (ETS 2024 Test 01)
        print("\n--- 6. Seeding ETS 2024 Test 01 Sample Questions ---")
        mock_test = db.query(MockTest).filter_by(test_id="ETS2024_01").first()
        if not mock_test:
            mock_test = MockTest(
                test_id="ETS2024_01",
                name="ETS TOEIC Regular Test 2024 - Test 01",
                year=2024,
                publisher="ETS",
                total_questions=200
            )
            db.add(mock_test)
            db.commit()

        SAMPLE_QUESTIONS = [
            ("ETS2024_01", "Part 5", 101,
             "Customer service representatives must speak ___ and politely when handling client inquiries.",
             "clear", "clearly", "clearness", "cleared", "B",
             "Cần trạng từ (clearly) đứng sau động từ 'speak' và liên từ 'and' song hành với trạng từ 'politely'.",
             "[Bẫy Từ Loại] A là tính từ, C là danh từ, D là dạng phân từ. Chỗ trống bổ nghĩa cho hành động 'speak'.",
             "speak clearly and politely"),

            ("ETS2024_01", "Part 5", 108,
             "The board members ___ approved the revised budget for cloud computing modernization.",
             "unanimity", "unanimous", "unanimities", "unanimously", "D",
             "Cần trạng từ (unanimously) đứng trước động từ chính 'approved' để bổ nghĩa cho hành động phê duyệt.",
             "[Bẫy Vị Trí Từ Loại] B là tính từ (unanimous), A/C là danh từ. Không đứng chen giữa Chủ ngữ và Động từ vị ngữ được.",
             "unanimously approved = approved by consensus"),

            ("ETS2024_01", "Part 5", 115,
             "___ the adverse snowstorm in Chicago, the delivery trucks arrived on schedule.",
             "Although", "Despite", "Because", "Even if", "B",
             "Phía sau là cụm danh từ 'the adverse snowstorm...', chỉ sự nhượng bộ ➔ Chọn giới từ 'Despite'.",
             "[Bẫy Liên Từ vs Giới Từ] 'Although' và 'Even if' là liên từ, bắt buộc đi với mệnh đề (S + V). 'Because' chỉ nguyên nhân trái nghĩa với ngữ cảnh.",
             "despite + Noun Phrase = in spite of"),

            ("ETS2024_01", "Part 7", 164,
             "What is stated about the hardware warranty on the server equipment?",
             "It is only valid for twelve months.",
             "It provides comprehensive protection against manufacturing defects.",
             "It requires an additional monthly insurance fee.",
             "It does not cover power supply replacements.", "B",
             "Dòng 4 trong thông báo: 'The warranty provides complete and all-inclusive coverage for all factory defects.'",
             "[Bẫy Thông Tin Lệch] A/C/D là các điều khoản suy diễn không có trong bài hoặc bị phủ định.",
             "comprehensive protection = all-inclusive coverage")
        ]

        for tid, part, qno, sentence, ca, cb, cc, cd, ans, exp, trap, para in SAMPLE_QUESTIONS:
            q = db.query(TestQuestion).filter_by(test_id=tid, question_no=qno).first()
            if not q:
                q = TestQuestion(
                    test_id=tid,
                    part=part,
                    question_no=qno,
                    sentence=sentence,
                    choice_a=ca,
                    choice_b=cb,
                    choice_c=cc,
                    choice_d=cd,
                    correct_choice=ans,
                    explanation=exp,
                    distractor_analysis=trap,
                    paraphrase_pair=para
                )
                db.add(q)
        db.commit()
        print(f"  ✓ Seeded {len(SAMPLE_QUESTIONS)} benchmark questions with full RCA distractor analysis")

        # 7. Seed Daily Study Reminder
        print("\n--- 7. Seeding Default Study Reminder ---")
        rem = db.query(StudyReminder).filter_by(user_id=user.id).first()
        if not rem:
            rem = StudyReminder(
                user_id=user.id,
                reminder_type="daily_study",
                scheduled_time="21:00",
                message="Đã 21:00 rồi! Đã đến giờ ôn 15 thẻ Flashcard và 1 bài tập cú pháp Part 5 hôm nay.",
                is_active=True
            )
            db.add(rem)
            db.commit()
            print("  ✓ Seeded daily reminder (21:00)")
        else:
            print("  • Study reminder already exists")

        print("\n=== Database Seeding Completed Successfully! ===")

    except Exception as e:
        db.rollback()
        print(f"ERROR Seeding Database: {e}")
        raise e
    finally:
        db.close()


def seed_everything():
    """Base seed + expanded corpus + authentic topic drill bank.

    Idempotent, but re-running it re-adds seed flashcards the learner deleted.
    """
    seed_all()
    from scripts import expand_corpus_data

    expand_corpus_data.main()
    from scripts.ingest_authentic_drills import ingest_authentic_drills

    ingest_authentic_drills()
    from scripts.ingest_authentic_listening_test01 import ingest as ingest_listening_test01

    ingest_listening_test01()
    from scripts.ingest_authentic_reading_test01 import ingest as ingest_reading_test01

    ingest_reading_test01()
    from scripts.normalize_flashcards_business import normalize as normalize_flashcards

    normalize_flashcards()


def database_is_empty() -> bool:
    """True when no lesson and no test exist yet (fresh install / new Docker volume)."""
    init_db()
    with SessionLocal() as db:
        return db.query(KnowledgeLesson).count() == 0 and db.query(MockTest).count() == 0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Tạo/migrate database và nạp nội dung học (idempotent)")
    parser.add_argument("--if-empty", action="store_true", help="Bỏ qua nếu đã có nội dung (dùng khi container khởi động)")
    if parser.parse_args().if_empty and not database_is_empty():
        print("Database đã có nội dung — bỏ qua seed (chạy không kèm --if-empty để đồng bộ lại).")
    else:
        seed_everything()
