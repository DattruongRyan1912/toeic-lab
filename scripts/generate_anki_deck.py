#!/usr/bin/env python3
"""
Generate TOEIC Flashcards in Anki Package format (.apkg)
Tạo bộ thẻ Anki chuyên biệt chuẩn ETS kèm IPA, Collocations và Paraphrase Vault.
"""

import os
import sys
import genanki

# Unique Model ID and Deck ID
MODEL_ID = 1607392319
DECK_ID = 2059392320

# Modern CSS Styling for Anki Cards
CARD_CSS = """
.card {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  font-size: 16px;
  text-align: left;
  color: #1e293b;
  background-color: #f8fafc;
  padding: 24px;
  line-height: 1.6;
}

.nightMode .card {
  color: #f8fafc;
  background-color: #0f172a;
}

.tag-badge {
  display: inline-block;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 3px 8px;
  border-radius: 4px;
  background-color: rgba(56, 189, 248, 0.15);
  color: #0284c7;
  margin-bottom: 12px;
}
.nightMode .tag-badge {
  color: #38bdf8;
  background-color: rgba(56, 189, 248, 0.2);
}

.sentence {
  font-size: 18px;
  font-weight: 500;
  margin-bottom: 16px;
  line-height: 1.5;
}

.blank {
  font-weight: 700;
  color: #0284c7;
  border-bottom: 2px solid #0284c7;
  padding: 0 4px;
}
.nightMode .blank {
  color: #38bdf8;
  border-bottom-color: #38bdf8;
}

.word-header {
  border-top: 1px solid #e2e8f0;
  padding-top: 16px;
  margin-top: 16px;
}
.nightMode .word-header {
  border-top-color: #334155;
}

.word-title {
  font-size: 24px;
  font-weight: 800;
  color: #0f172a;
  display: inline-block;
}
.nightMode .word-title {
  color: #38bdf8;
}

.ipa {
  font-family: "JetBrains Mono", monospace;
  font-size: 14px;
  color: #64748b;
  margin-left: 8px;
}
.nightMode .ipa {
  color: #94a3b8;
}

.word-type {
  font-size: 13px;
  font-style: italic;
  color: #7c3aed;
  font-weight: 600;
  margin-left: 6px;
}
.nightMode .word-type {
  color: #c084fc;
}

.vietnamese-meaning {
  font-size: 16px;
  font-weight: 700;
  color: #059669;
  margin: 8px 0;
}
.nightMode .vietnamese-meaning {
  color: #34d399;
}

.section-box {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px 14px;
  margin-top: 10px;
  font-size: 14px;
}
.nightMode .section-box {
  background: #1e293b;
  border-color: #334155;
}

.section-title {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  color: #64748b;
  margin-bottom: 4px;
}
.nightMode .section-title {
  color: #94a3b8;
}

.collocation-highlight {
  font-weight: 600;
  color: #d97706;
}
.nightMode .collocation-highlight {
  color: #fbbf24;
}

.paraphrase-highlight {
  font-weight: 600;
  color: #0284c7;
}
.nightMode .paraphrase-highlight {
  color: #38bdf8;
}
"""

toeic_model = genanki.Model(
    MODEL_ID,
    'TOEIC Engineering Flashcard Model',
    fields=[
        {'name': 'Sentence_Front'},
        {'name': 'Domain_Category'},
        {'name': 'Target_Word'},
        {'name': 'IPA'},
        {'name': 'Word_Type'},
        {'name': 'Vietnamese_Meaning'},
        {'name': 'Collocations'},
        {'name': 'Paraphrase_Equivalence'},
        {'name': 'Full_Sentence_Back'},
    ],
    templates=[
        {
            'name': 'TOEIC Card Template',
            'qfmt': """
<div class="tag-badge">{{Domain_Category}}</div>
<div class="sentence">{{Sentence_Front}}</div>
            """,
            'afmt': """
<div class="tag-badge">{{Domain_Category}}</div>
<div class="sentence">{{Full_Sentence_Back}}</div>

<div class="word-header">
  <span class="word-title">{{Target_Word}}</span>
  <span class="ipa">/{{IPA}}/</span>
  <span class="word-type">({{Word_Type}})</span>
</div>

<div class="vietnamese-meaning">➔ {{Vietnamese_Meaning}}</div>

<div class="section-box">
  <div class="section-title">⚡ Collocations Đi Kèm:</div>
  <div class="collocation-highlight">{{Collocations}}</div>
</div>

<div class="section-box">
  <div class="section-title">🔄 Paraphrase Trong Đề Thi ETS:</div>
  <div class="paraphrase-highlight">{{Paraphrase_Equivalence}}</div>
</div>
            """,
        },
    ],
    css=CARD_CSS,
)

VOCAB_DATA = [
    (
        "The board of directors decided to <span class='blank'>______</span> the annual shareholder meeting until next Friday.",
        "General Business",
        "postpone",
        "pəʊstˈpəʊn",
        "verb",
        "hoãn lại, dời lịch",
        "postpone a meeting, postpone indefinitely",
        "postpone = delay = put off = defer",
        "The board of directors decided to <b style='color:#0284c7'>postpone</b> the annual shareholder meeting until next Friday."
    ),
    (
        "The internal auditing committee will <span class='blank'>______</span> a comprehensive inspection of financial records.",
        "Corporate & Finance",
        "conduct",
        "kənˈdʌkt",
        "verb",
        "tiến hành, thực hiện",
        "conduct an audit, conduct a survey, conduct an inspection",
        "conduct = carry out = perform = execute",
        "The internal auditing committee will <b style='color:#0284c7'>conduct</b> a comprehensive inspection of financial records."
    ),
    (
        "All manufacturing plants must strictly <span class='blank'>______</span> with environmental and workplace safety regulations.",
        "Manufacturing & Compliance",
        "comply",
        "kəmˈplaɪ",
        "verb",
        "tuân thủ, tuân theo",
        "comply with safety regulations, comply with standards",
        "comply with = adhere to = conform to = abide by",
        "All manufacturing plants must strictly <b style='color:#0284c7'>comply</b> with environmental and workplace safety regulations."
    ),
    (
        "Full-time software engineers are <span class='blank'>______</span> for tuition reimbursement after six months of service.",
        "Human Resources",
        "eligible",
        "ˈelɪdʒəbl",
        "adjective",
        "đủ điều kiện, đủ tư cách",
        "eligible for a promotion, eligible for reimbursement, eligible to receive",
        "eligible for = qualified for = entitled to",
        "Full-time software engineers are <b style='color:#0284c7'>eligible</b> for tuition reimbursement after six months of service."
    ),
    (
        "Please submit your travel receipts so that the finance department can <span class='blank'>______</span> your business expenses.",
        "Finance & Expenses",
        "reimburse",
        "ˌriːɪmˈbɜːs",
        "verb",
        "hoàn tiền, bồi hoàn chi phí",
        "reimburse travel expenses, reimburse employees",
        "reimburse = compensate = pay back = refund",
        "Please submit your travel receipts so that the finance department can <b style='color:#0284c7'>reimburse</b> your business expenses."
    ),
    (
        "The shareholders <span class='blank'>______</span> approved the proposed merger with the technology firm.",
        "General Business",
        "unanimously",
        "juːˈnænɪməsli",
        "adverb",
        "nhất trí, đồng thuận 100%",
        "unanimously approved, unanimously agreed, vote unanimously",
        "unanimously = with complete agreement = by consensus",
        "The shareholders <b style='color:#0284c7'>unanimously</b> approved the proposed merger with the technology firm."
    ),
    (
        "The warranty provided with this server rack provides <span class='blank'>______</span> coverage for hardware defects.",
        "Purchasing & Warranty",
        "comprehensive",
        "ˌkɒmprɪˈhensɪv",
        "adjective",
        "toàn diện, bao quát",
        "comprehensive coverage, comprehensive training program, comprehensive guide",
        "comprehensive = complete = thorough = all-inclusive",
        "The warranty provided with this server rack provides <b style='color:#0284c7'>comprehensive</b> coverage for hardware defects."
    ),
    (
        "The project timeline shared yesterday is only <span class='blank'>______</span> and subject to change based on client feedback.",
        "Project Management",
        "tentative",
        "ˈtentətɪv",
        "adjective",
        "dự kiến, thăm dò (chưa chốt)",
        "tentative agreement, tentative schedule, tentative date",
        "tentative = provisional = subject to change = not finalized",
        "The project timeline shared yesterday is only <b style='color:#0284c7'>tentative</b> and subject to change based on client feedback."
    ),
    (
        "The engineering department introduced a new ticketing system to <span class='blank'>______</span> cross-team collaboration.",
        "Office Operations",
        "facilitate",
        "fəˈsɪlɪteɪt",
        "verb",
        "tạo điều kiện thuận lợi, thúc đẩy",
        "facilitate communication, facilitate growth, facilitate discussion",
        "facilitate = ease = promote = make easier",
        "The engineering department introduced a new ticketing system to <b style='color:#0284c7'>facilitate</b> cross-team collaboration."
    ),
    (
        "The management agreed to <span class='blank'>______</span> additional budget funds to upgrade cloud infrastructure.",
        "Finance & IT",
        "allocate",
        "ˈæləkeɪt",
        "verb",
        "phân bổ, chỉ định ngân sách/tài nguyên",
        "allocate funds, allocate resources, allocate budget",
        "allocate = assign = distribute = set aside",
        "The management agreed to <b style='color:#0284c7'>allocate</b> additional budget funds to upgrade cloud infrastructure."
    ),
    (
        "Your subscription to the enterprise cloud platform will <span class='blank'>______</span> at the end of this billing cycle.",
        "Purchasing & Contracts",
        "expire",
        "ɪkˈspaɪər",
        "verb",
        "hết hạn, hết hiệu lực",
        "expire at the end of, contract expires, warranty expires",
        "expire = terminate = end = lapse",
        "Your subscription to the enterprise cloud platform will <b style='color:#0284c7'>expire</b> at the end of this billing cycle."
    ),
    (
        "The hiring manager noted that Mr. Tran is an <span class='blank'>______</span> candidate with strong distributed systems expertise.",
        "Human Resources",
        "exceptional",
        "ɪkˈsepʃənl",
        "adjective",
        "xuất chúng, đặc biệt xuất sắc",
        "exceptional candidate, exceptional performance, exceptional quality",
        "exceptional = outstanding = extraordinary = superior",
        "The hiring manager noted that Mr. Tran is an <b style='color:#0284c7'>exceptional</b> candidate with strong distributed systems expertise."
    ),
    (
        "The logistics provider does not <span class='blank'>______</span> any delivery delays despite the adverse weather conditions.",
        "Shipping & Logistics",
        "anticipate",
        "ænˈtɪsɪpeɪt",
        "verb",
        "lường trước, dự đoán",
        "anticipate delays, anticipate growth, anticipate problems",
        "anticipate = expect = foresee = predict",
        "The logistics provider does not <b style='color:#0284c7'>anticipate</b> any delivery delays despite the adverse weather conditions."
    ),
    (
        "The security division will <span class='blank'>______</span> stricter authentication protocols across all production databases.",
        "Technical & IT",
        "implement",
        "ˈɪmplɪment",
        "verb",
        "triển khai, thi hành",
        "implement a policy, implement security measures, implement changes",
        "implement = execute = apply = put into practice",
        "The security division will <b style='color:#0284c7'>implement</b> stricter authentication protocols across all production databases."
    ),
    (
        "Please review the detailed flight <span class='blank'>______</span> sent by the travel agency before departing for Tokyo.",
        "Travel & Hospitality",
        "itinerary",
        "aɪˈtɪnərəri",
        "noun",
        "lịch trình chuyến đi",
        "travel itinerary, detailed itinerary, revised itinerary",
        "itinerary = travel plan = schedule = timetable",
        "Please review the detailed flight <b style='color:#0284c7'>itinerary</b> sent by the travel agency before departing for Tokyo."
    ),
    (
        "Attendance at tomorrow morning's orientation session is <span class='blank'>______</span> for all newly hired software engineers.",
        "Human Resources",
        "mandatory",
        "ˈmændətəri",
        "adjective",
        "bắt buộc",
        "mandatory attendance, mandatory training, mandatory meeting",
        "mandatory = compulsory = required = obligatory",
        "Attendance at tomorrow morning's orientation session is <b style='color:#0284c7'>mandatory</b> for all newly hired software engineers."
    ),
    (
        "Thank you for your <span class='blank'>______</span> response to our customer inquiry regarding service availability.",
        "Customer Service",
        "prompt",
        "prɒmpt",
        "adjective",
        "nhanh chóng, kịp thời",
        "prompt response, prompt delivery, prompt payment",
        "prompt = immediate = timely = quick",
        "Thank you for your <b style='color:#0284c7'>prompt</b> response to our customer inquiry regarding service availability."
    ),
    (
        "Quarterly net revenues increased <span class='blank'>______</span> following the launch of the new subscription model.",
        "Finance & Sales",
        "substantially",
        "səbˈstænʃəli",
        "adverb",
        "đáng kể, rất nhiều",
        "substantially increase, substantially higher, improve substantially",
        "substantially = significantly = considerably = dramatically",
        "Quarterly net revenues increased <b style='color:#0284c7'>substantially</b> following the launch of the new subscription model."
    ),
    (
        "The conference venue is fully equipped to <span class='blank'>______</span> up to 500 attendees with specialized accessibility needs.",
        "Dining & Hospitality",
        "accommodate",
        "əˈkɒmədeɪt",
        "verb",
        "đáp ứng, chứa được, cung cấp chỗ",
        "accommodate guests, accommodate requests, accommodate needs",
        "accommodate = serve = cater to = provide room for",
        "The conference venue is fully equipped to <b style='color:#0284c7'>accommodate</b> up to 500 attendees with specialized accessibility needs."
    ),
    (
        "All employee compensation records and personnel files must remain strictly <span class='blank'>______</span>.",
        "Human Resources & Legal",
        "confidential",
        "ˌkɒnfɪˈdenʃl",
        "adjective",
        "bảo mật, tuyệt mật",
        "strictly confidential, confidential information, confidential documents",
        "confidential = secret = private = non-public",
        "All employee compensation records and personnel files must remain strictly <b style='color:#0284c7'>confidential</b>."
    )
]

def main():
    deck = genanki.Deck(
        DECK_ID,
        'TOEIC 750+ :: Sprint 1 Core Business Vocab'
    )

    for item in VOCAB_DATA:
        note = genanki.Note(
            model=toeic_model,
            fields=list(item)
        )
        deck.add_note(note)

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_file = os.path.join(base_dir, "decks", "TOEIC_Sprint1_Core_Vocab.apkg")
    genanki.Package(deck).write_to_file(out_file)
    print(f"🎉 Đã xuất thành công bộ thẻ Anki: {out_file} ({len(VOCAB_DATA)} thẻ chuẩn ETS)")

if __name__ == "__main__":
    main()
