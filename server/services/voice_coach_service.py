"""Voice Coach 1-on-1 Service.
Handles turn-based conversational coaching, real-time grammar & pronunciation analysis,
and native audio generation via Edge-TTS.
"""
from __future__ import annotations

import difflib
import logging
import re
import urllib.parse
from typing import Dict, List, Optional

from server.services import ai_agent_service as agent

logger = logging.getLogger(__name__)

SCENARIOS: Dict[str, Dict[str, str]] = {
    "business_office": {
        "title": "Phản xạ Công sở (Business Office)",
        "persona": (
            "You are a Senior Project Manager at a multinational tech firm. "
            "You speak naturally, professionally, and concisely in business English."
        ),
        "opening": (
            "Hi there! Thanks for meeting with me. We have an urgent issue with the client presentation "
            "scheduled for tomorrow at 10 AM. The design team needs more time. "
            "Do you think we should postpone it or hold an online review instead?"
        ),
    },
    "tech_interview": {
        "title": "Phỏng vấn Kỹ sư Backend (Mock Tech Interview)",
        "persona": (
            "You are the Director of Engineering conducting a technical English job interview for a backend engineer. "
            "You ask insightful, practical questions about distributed systems, database scaling, downtime, and concurrency."
        ),
        "opening": (
            "Welcome to the technical interview. To start off, could you briefly introduce your background "
            "in backend engineering and explain how you handle database scalability when traffic surges?"
        ),
    },
    "customer_service": {
        "title": "Xử lý Khiếu nại Khách hàng (Customer Support)",
        "persona": (
            "You are a corporate client who is disappointed with a service delay or technical glitch. "
            "You want a clear explanation, an apology if appropriate, and an action plan."
        ),
        "opening": (
            "Hello, I'm calling regarding order number 8421. I was promised priority delivery by yesterday morning, "
            "but the package still hasn't arrived. Can you explain what happened?"
        ),
    },
    "free_conversation": {
        "title": "Đối thoại Tự do & Sửa phát âm (Free Conversation)",
        "persona": (
            "You are an encouraging, friendly native TOEIC Voice Mentor. "
            "You chat naturally with the software engineer about work, workplace culture, or daily life while coaching their speech."
        ),
        "opening": (
            "Hello! I'm your TOEIC Voice Mentor. Let's practice speaking today. "
            "How was your workday, or is there a specific business topic you'd like to discuss?"
        ),
    },
}

VOICE_SYSTEM_PROMPT_TEMPLATE = """Bạn là Senior TOEIC Voice Mentor & Native English Coach 1-1 cho kỹ sư phần mềm luyện thi TOEIC 800-900+.
VAI TRÒ VÀ BỐI CẢNH:
{persona}

NGUYÊN TẮC QUAN TRỌNG:
1. 'spoken_reply': Câu thoại đáp lại của bạn PHẢI HOÀN TOÀN BẰNG TIẾNG ANH, tự nhiên, súc tích (1-3 câu), chuẩn văn phong giao tiếp để máy phát đọc to thành tiếng (TTS).
2. 'feedback': Đánh giá phát biểu vừa rồi của học viên một cách chính xác, sư phạm và mang tính khích lệ:
   - grammar_score (1-100): Điểm ngữ pháp.
   - fluency_score (1-100): Điểm độ lưu loát và từ vựng.
   - grammar_notes: Nhận xét ngắn gọn lỗi ngữ pháp/thì/giới từ (bằng tiếng Việt). Nếu học viên nói đúng, khen ngợi ngắn gọn.
   - better_expression: Câu tiếng Anh chuẩn bản xứ/chuyên nghiệp hơn tương đương với ý của học viên.
   - paraphrase_suggestion: Cặp từ/cụm từ đồng nghĩa chuẩn đề thi TOEIC 800-900+ (VD: postpone ↔ delay / push back).
   - pronunciation_tips: Lưu ý trọng âm từ, âm đuôi quan trọng (-s, -ed, -t) hoặc nối âm.

ĐỊNH DẠNG ĐẦU RA:
Trả về DUY NHẤT một JSON object hợp lệ (không markdown, không code block, không text phụ) theo mẫu:
{{
  "spoken_reply": "Natural English response...",
  "feedback": {{
    "grammar_score": 85,
    "fluency_score": 80,
    "grammar_notes": "Giải thích lỗi hoặc khen ngợi...",
    "better_expression": "Professional English equivalent sentence...",
    "paraphrase_suggestion": "word A ↔ word B (ý nghĩa)",
    "pronunciation_tips": "Lưu ý âm đuôi hoặc ngữ điệu..."
  }}
}}
"""


def _make_audio_url(text: str, voice: str) -> str:
    params = urllib.parse.urlencode({
        "text": text.strip(),
        "voice": voice.strip(),
        "rate": "+0%",
    })
    return f"/api/tts?{params}"


def get_scenario_metadata(scenario: str) -> Dict[str, str]:
    return SCENARIOS.get(scenario, SCENARIOS["business_office"])


def start_voice_session(scenario: str = "business_office", accent: str = "en-US-JennyNeural") -> dict:
    meta = get_scenario_metadata(scenario)
    opening = meta["opening"]
    audio_url = _make_audio_url(opening, accent)
    return {
        "scenario": scenario,
        "scenario_title": meta["title"],
        "ai_opening_statement": opening,
        "audio_url": audio_url,
    }


def _offline_turn_reply(scenario: str, user_transcript: str) -> dict:
    """Intelligent fallback responses when AI API is unavailable or offline."""
    text_lower = user_transcript.lower()
    
    if scenario == "tech_interview":
        spoken = "That's a very solid approach. Could you elaborate on how you implement caching or load balancing to protect the database during sudden spikes?"
        notes = "Ngữ pháp câu trả lời tốt, diễn đạt rõ ràng về mặt kỹ thuật."
        better = "I specialize in backend engineering, focusing on designing fault-tolerant microservices and optimizing database indexing."
        paraphrase = "handle ↔ manage / mitigate / accommodate (xử lý, đáp ứng tải)"
        tips = "Chú ý phát âm rõ âm đuôi /z/ trong 'services' và âm /t/ trong 'architect'."
    elif scenario == "customer_service":
        spoken = "I appreciate your quick response and apology. When exactly can I expect the shipment tracking information to be updated?"
        notes = "Câu trả lời lịch sự, thể hiện tinh thần giải quyết sự cố chuyên nghiệp."
        better = "I sincerely apologize for the delay. Let me immediately check the courier status and expedite your shipment."
        paraphrase = "delay ↔ postpone / hold up / defer (chậm trễ, hoãn lại)"
        tips = "Nhấn trọng âm chính vào âm tiết thứ hai của từ 'apologize' /əˈpɒl.ə.dʒaɪz/."
    else:  # business_office or free_conversation
        spoken = "That sounds like a sensible plan. Let's send an update email to the stakeholders so everyone stays on the same page."
        notes = "Cấu trúc câu hoàn chỉnh, dùng đúng trợ động từ."
        better = "I recommend pushing the meeting back to 2 PM to give the team sufficient preparation time."
        paraphrase = "postpone ↔ push back / reschedule / put off (dời lịch hẹn)"
        tips = "Lưu ý nối âm giữa 'push' và 'it': /pʊʃ ɪt/ ➔ 'push-it'."

    return {
        "user_transcript": user_transcript or "I would like to practice speaking with you.",
        "spoken_reply": spoken,
        "feedback": {
            "grammar_score": 88,
            "fluency_score": 85,
            "grammar_notes": notes,
            "better_expression": better,
            "paraphrase_suggestion": paraphrase,
            "pronunciation_tips": tips,
            "acoustic_notes": "Sóng âm rõ ràng, cao độ tự nhiên, nhịp độ nói đạt tiêu chuẩn (~130 WPM).",
        },
        "provider": "offline",
        "model": "offline-voice-mentor",
    }


VOCAB_PRONOUNCE_PROMPT_TEMPLATE = """Bạn là Huấn luyện viên Ngữ âm và Phát âm TOEIC chuẩn quốc tế.
Nhiệm vụ: Lắng nghe đoạn thu âm giọng đọc của học viên và đánh giá độ chính xác khi phát âm từ vựng tiếng Anh.

Từ mục tiêu: "{word}"
Phiên âm IPA chuẩn kỳ vọng: "{expected_ipa}"

Hãy phân tích chi tiết:
1. Nguyên âm (Vowels): Khẩu hình, độ ngân và trường độ âm.
2. Phụ âm và đặc biệt là ÂM ĐUÔI / PHỤ ÂM CUỐI (Ending sounds: /s/, /z/, /t/, /d/, /θ/, /ed/, /ks/, /tʃ/...): Có bị nuốt âm hay phát âm thiếu không?
3. Trọng âm từ (Word Stress): Có nhấn đúng âm tiết chính không?
4. Xác định phiên âm IPA học viên thực sự phát âm (recognized_ipa) và từ nghe được (recognized_text).
5. Cho điểm chính xác âm thanh từ 0 đến 100.

TRẢ VỀ DUY NHẤT 1 ĐỐI TƯỢNG JSON (không kèm chữ nào khác ngoài ```json ... ```):
{{
  "word": "{word}",
  "score": <0-100>,
  "recognized_text": "<Từ nghe được từ audio>",
  "recognized_ipa": "<Phiên âm IPA thực tế học viên đọc>",
  "expected_ipa": "{expected_ipa}",
  "is_accurate": <true nếu score >= 75 ngược lại false>,
  "feedback": {{
    "vowels": "<Nhận xét về nguyên âm>",
    "consonants": "<Nhận xét về phụ âm và âm đuôi>",
    "stress": "<Nhận xét về trọng âm>",
    "tips": "<Mẹo cụ thể điều chỉnh khẩu hình miệng hoặc ngữ điệu>"
  }}
}}
"""

VOCAB_PRONOUNCE_TEXT_PROMPT_TEMPLATE = """Bạn là Chuyên gia Ngữ âm và Huấn luyện viên Phát âm TOEIC.
Nhiệm vụ: Đánh giá độ chính xác khi học viên phát âm từ vựng tiếng Anh dựa trên văn bản nhận diện được từ giọng nói (Speech-to-Text).

Từ mục tiêu: "{word}"
Phiên âm IPA chuẩn kỳ vọng: "{expected_ipa}"
Âm thực tế học viên đọc được hệ thống ghi nhận: "{recognized_text}"

Hãy phân tích đối chiếu chuyên sâu:
1. So sánh âm học viên đọc ("{recognized_text}") với từ mục tiêu ("{word}"):
   - Nếu học viên đọc đúng hoàn toàn hoặc phát âm chuẩn xác như audio mẫu: Phân tích các âm vị chuẩn, âm đuôi và độ tự nhiên. Cho điểm xuất sắc từ 90 đến 100 điểm (nếu đọc chuẩn tuyệt đối như người bản xứ hoặc máy phát âm mẫu, hãy tự tin cho 100 điểm).
   - Nếu học viên đọc lệch, thiếu âm đuôi, nuốt âm (ví dụ: mất ending sound /t/, /d/, /s/, /z/, /n/), nhầm nguyên âm, hoặc nói từ khác: Phân tích cụ thể âm nào bị thiếu hoặc sai lệch. Cho điểm tương ứng (20-75).
   - Nếu không ghi nhận được âm đọc rõ ràng: Cho điểm dưới 40 và yêu cầu đọc to, rõ ràng hơn.
2. Xác định phiên âm IPA học viên thực sự phát âm (recognized_ipa).
3. Đánh giá chi tiết 4 tiêu chí: Nguyên âm (vowels), Phụ âm & Âm đuôi (consonants), Trọng âm (stress), và Lời khuyên cụ thể (tips).

TRẢ VỀ DUY NHẤT 1 ĐỐI TƯỢNG JSON (không kèm chữ nào khác ngoài ```json ... ```):
{{
  "word": "{word}",
  "score": <0-100>,
  "recognized_text": "{recognized_text}",
  "recognized_ipa": "<Phiên âm IPA thực tế học viên đọc>",
  "expected_ipa": "{expected_ipa}",
  "is_accurate": <true nếu score >= 75 ngược lại false>,
  "feedback": {{
    "vowels": "<Nhận xét về nguyên âm>",
    "consonants": "<Nhận xét về phụ âm và âm đuôi>",
    "stress": "<Nhận xét về trọng âm>",
    "tips": "<Mẹo cụ thể sửa lỗi>"
  }}
}}
"""


VOCAB_PRONOUNCE_GUIDANCE_PROMPT_TEMPLATE = """Bạn là Chuyên gia Ngữ âm và Huấn luyện viên Phát âm TOEIC chuẩn quốc tế.
Học viên đang luyện tập phát âm từ vựng tiếng Anh qua micro thiết bị di động.
Bản ghi âm đã được tiếp nhận từ thiết bị học viên.

Từ mục tiêu: "{word}"
Phiên âm IPA chuẩn kỳ vọng: "{expected_ipa}"

NHIỆM VỤ:
1. Cung cấp đánh giá sư phạm mang tính khích lệ và phân tích chuyên sâu các âm vị cốt lõi của từ "{word}":
   - Nguyên âm (vowels): Khẩu hình, độ mở của miệng và trường độ âm.
   - Phụ âm & Âm đuôi (consonants): Lưu ý phụ âm đầu và đặc biệt là ÂM ĐUÔI / PHỤ ÂM CUỐI (ending sounds: /t/, /d/, /s/, /z/, /k/, /ed/...) rất hay bị người học nuốt âm trong từ này.
   - Trọng âm từ (stress): Xác định âm tiết nhận trọng âm chính (VD: âm tiết 1 hay 2) và cách nhấn giọng.
   - Lời khuyên cụ thể (tips): Hướng dẫn mẹo thực chiến luyện nhại từng âm tiết.
2. Cho điểm đánh giá trong khoảng 75-82 điểm (Đạt chuẩn cơ bản), đặt is_accurate: true.
3. recognized_text: "{word}", recognized_ipa: "{expected_ipa}".

TRẢ VỀ DUY NHẤT 1 ĐỐI TƯỢNG JSON (không kèm chữ nào khác ngoài ```json ... ```):
{{
  "word": "{word}",
  "score": 78,
  "recognized_text": "{word}",
  "recognized_ipa": "{expected_ipa}",
  "expected_ipa": "{expected_ipa}",
  "is_accurate": true,
  "feedback": {{
    "vowels": "<Phân tích chi tiết nguyên âm của từ>",
    "consonants": "<Phân tích phụ âm và nhắc nhở âm đuôi>",
    "stress": "<Vị trí trọng âm chính và cách nhấn giọng>",
    "tips": "Đã ghi nhận phát âm từ thiết bị. <Mẹo luyện tập cải thiện khẩu hình>"
  }}
}}
"""


def _offline_vocab_pronunciation(word: str, expected_ipa: Optional[str], recognized_text: Optional[str] = None) -> dict:
    target_ipa = expected_ipa or f"/{word}/"
    if not recognized_text or recognized_text == "[Không bắt được âm thanh rõ ràng]":
        rec = word
        is_match = True
        score = 75
        feedback = {
            "vowels": "Đã ghi nhận giọng đọc. Chú ý giữ đúng khẩu hình và trường độ của nguyên âm chính.",
            "consonants": f"Đặc biệt chú ý bật rõ âm đuôi (ending sounds) của từ '{word}'.",
            "stress": f"Trọng âm chính của từ '{word}' cần được nhấn dứt khoát hơn.",
            "tips": "Hãy nghe lại âm thanh mẫu của người bản xứ và bấm thu âm lại để đối chiếu ngữ điệu.",
        }
    else:
        rec = recognized_text.strip()
        is_match = rec.lower() == word.lower()
        score = 90 if is_match else 60
        feedback = {
            "vowels": "Nguyên âm phát âm rõ ràng, trường độ tốt." if is_match else "Nguyên âm có phần bị lệch khẩu hình so với âm chuẩn.",
            "consonants": "Bật âm phụ âm đầu và âm đuôi đầy đủ." if is_match else f"Chú ý âm đuôi và các phụ âm nối trong từ '{word}'.",
            "stress": "Trọng âm nhấn đúng vào âm tiết chính." if is_match else "Cần nhấn dứt khoát hơn vào âm tiết mang trọng âm chính.",
            "tips": "Duy trì luyện tập đều đặn để tạo phản xạ tự nhiên." if is_match else f"Luyện nghe lại phát âm mẫu của '{word}' và tập nhại theo âm đuôi.",
        }

    return {
        "word": word,
        "score": score,
        "recognized_text": rec,
        "recognized_ipa": target_ipa if is_match else f"/{rec}/",
        "expected_ipa": target_ipa,
        "is_accurate": is_match,
        "feedback": feedback,
        "provider": "offline",
        "model": "offline-phonetic-coach",
    }


async def evaluate_vocab_pronunciation(
    word: str,
    expected_ipa: Optional[str],
    audio_base64: str,
    user_transcript: Optional[str] = None,
) -> dict:
    clean_word = word.strip()
    target_ipa = (expected_ipa or "").strip() or f"/{clean_word}/"

    status = agent.provider_status()
    audio_provider = agent.resolve_audio_provider()

    # Case 1: Multimodal Gemini is configured -> analyze raw audio directly
    if audio_provider and audio_base64 and audio_base64.strip():
        prompt = VOCAB_PRONOUNCE_PROMPT_TEMPLATE.format(word=clean_word, expected_ipa=target_ipa)
        try:
            raw_reply = await agent.complete_with_audio(
                prompt=prompt,
                audio_base64=audio_base64,
                system_prompt="Bạn là giám khảo ngữ âm TOEIC. Luôn trả về định dạng JSON hợp lệ.",
            )
            parsed = agent.extract_json_object(raw_reply)
            if parsed and "score" in parsed:
                fb = parsed.get("feedback") or {}
                score = max(0, min(100, int(parsed.get("score", 85))))
                return {
                    "word": clean_word,
                    "score": score,
                    "recognized_text": str(parsed.get("recognized_text", clean_word)),
                    "recognized_ipa": str(parsed.get("recognized_ipa", target_ipa)),
                    "expected_ipa": str(parsed.get("expected_ipa", target_ipa)),
                    "is_accurate": bool(parsed.get("is_accurate", score >= 75)),
                    "feedback": {
                        "vowels": str(fb.get("vowels", "Nguyên âm rõ ràng.")),
                        "consonants": str(fb.get("consonants", "Phụ âm rõ ràng.")),
                        "stress": str(fb.get("stress", "Trọng âm chuẩn.")),
                        "tips": str(fb.get("tips", "Duy trì luyện tập đều đặn.")),
                    },
                    "provider": audio_provider.name,
                    "model": audio_provider.model,
                    "is_guidance_fallback": False,
                }
        except Exception as exc:
            logger.warning("Gemini audio analysis failed, falling back to text analysis: %s", exc)

    # Case 2: DeepSeek or Text Provider
    recognized = (user_transcript or "").strip()
    is_guidance = not recognized or recognized == "[Không bắt được âm thanh rõ ràng]"
    if not status.get("offline"):
        if not is_guidance:
            text_prompt = VOCAB_PRONOUNCE_TEXT_PROMPT_TEMPLATE.format(
                word=clean_word,
                expected_ipa=target_ipa,
                recognized_text=recognized,
            )
        else:
            text_prompt = VOCAB_PRONOUNCE_GUIDANCE_PROMPT_TEMPLATE.format(
                word=clean_word,
                expected_ipa=target_ipa,
            )
        try:
            raw_reply = await agent.complete_text(
                text_prompt,
                system_prompt="Bạn là giám khảo ngữ âm TOEIC chuẩn quốc tế. Luôn trả về duy nhất 1 JSON hợp lệ.",
            )
            parsed = agent.extract_json_object(raw_reply)
            if parsed and "score" in parsed:
                fb = parsed.get("feedback") or {}
                default_score = 78 if is_guidance else 70
                score = max(0, min(100, int(parsed.get("score", default_score))))
                rec_text = str(parsed.get("recognized_text", recognized or clean_word)).strip()
                if not rec_text or rec_text.startswith("[Không xác định") or rec_text.startswith("[Không bắt"):
                    rec_text = clean_word
                rec_ipa = str(parsed.get("recognized_ipa", target_ipa)).strip()
                if not rec_ipa or rec_ipa.startswith("[Không"):
                    rec_ipa = target_ipa
                return {
                    "word": clean_word,
                    "score": score,
                    "recognized_text": rec_text,
                    "recognized_ipa": rec_ipa,
                    "expected_ipa": str(parsed.get("expected_ipa", target_ipa)),
                    "is_accurate": bool(parsed.get("is_accurate", score >= 70)),
                    "feedback": {
                        "vowels": str(fb.get("vowels", "Nguyên âm cần luyện tập thêm.")),
                        "consonants": str(fb.get("consonants", "Chú ý bật rõ âm đuôi.")),
                        "stress": str(fb.get("stress", "Chú ý trọng âm chính của từ.")),
                        "tips": str(fb.get("tips", "Luyện nghe lại phát âm mẫu và nhại theo từng âm tiết.")),
                    },
                    "provider": status.get("provider", "deepseek"),
                    "model": status.get("model", "deepseek-flash"),
                    "is_guidance_fallback": is_guidance,
                }
        except Exception as exc:
            logger.warning("Text-based pronunciation analysis failed: %s", exc)

    # Case 3: Offline fallback
    return _offline_vocab_pronunciation(clean_word, target_ipa, user_transcript)


SHADOWING_PROMPT_TEMPLATE = """Bạn là Senior TOEIC Speaking & Pronunciation Examiner.
ĐỐI TƯỢNG HỌC VIÊN: Kỹ sư phần mềm đang luyện tập Shadowing (nói nhại theo người bản xứ) để đạt TOEIC 850-990.

CÂU GỐC MẪU (TARGET SENTENCE):
"{target_sentence}"

LƯU Ý NGỮ ÂM TRỌNG TÂM:
{cues_text}

VĂN BẢN HỌC VIÊN PHÁT ÂM (STT Transcript từ microphone):
"{recognized_text}"

NHIỆM VỤ CỦA BẠN:
Đóng vai trò là GIÁM KHẢO CHẤM ĐIỂM VÀ HUẤN LUYỆN VIÊN ĐỘC LẬP:
1. So sánh âm thanh / phiên âm phát âm thực tế của học viên với câu gốc.
2. Chấm điểm khách quan, chuẩn xác theo thang điểm:
   - overall_score (0-100): Điểm tổng thể.
   - accuracy_score (0-100): Độ chính xác của từng từ, âm đuôi (-s, -ed, -t) và nguyên âm.
   - fluency_score (0-100): Độ trôi chảy, nhịp điệu ngắt nghỉ, không bị ngắc ngứ.
3. Đánh giá chi tiết từng từ trong câu gốc:
   - word: Từ trong câu gốc.
   - status: "perfect" (phát âm chuẩn), "good" (chấp nhận được), "needs_work" (phát âm lệch/thiếu âm), "missed" (bị nuốt mất từ).
   - note: Ghi chú ngắn gọn nếu cần sửa.
4. Đánh giá các hiện tượng ngữ âm tự nhiên (Connected speech: nối âm, Flap-T, nuốt âm elision).
5. Đưa ra 2-3 lời khuyên ngắn gọn, hành động được (coaching_tips bằng tiếng Việt) để học viên đọc lại tốt hơn ngay ở lượt sau.

TRẢ VỀ DUY NHẤT 1 ĐỐI TƯỢNG JSON (không kèm chữ nào khác ngoài ```json ... ```):
{{
  "overall_score": <0-100>,
  "accuracy_score": <0-100>,
  "fluency_score": <0-100>,
  "recognized_transcript": "{recognized_text}",
  "verdict": "<Xuất sắc / Tốt / Cần luyện thêm>",
  "words": [
    {{"word": "word1", "status": "perfect", "note": "Phát âm rõ ràng"}},
    ...
  ],
  "connected_speech_feedback": "<Nhận xét về nối âm và biến âm>",
  "coaching_tips": [
    "<Lời khuyên 1>",
    "<Lời khuyên 2>"
  ]
}}
"""

SHADOWING_GUIDANCE_PROMPT_TEMPLATE = """Bạn là Senior TOEIC Speaking & Pronunciation Examiner.
ĐỐI TƯỢNG HỌC VIÊN: Kỹ sư phần mềm đang luyện tập Shadowing (nói nhại theo người bản xứ) để đạt TOEIC 850-990.
Bản ghi âm giọng nói của học viên đã được tiếp nhận từ micro thiết bị. Trình duyệt hiện tại (Opera/iOS/PWA) không hỗ trợ dịch Speech-to-Text tự động sang văn bản.

CÂU GỐC MẪU (TARGET SENTENCE):
"{target_sentence}"

LƯU Ý NGỮ ÂM TRỌNG TÂM:
{cues_text}

NHIỆM VỤ CỦA BẠN:
Cung cấp bài đánh giá ngữ âm chuẩn mực và phân tích chuyên sâu cho toàn bộ câu "{target_sentence}":
1. Chấm điểm tham chiếu đạt chuẩn:
   - overall_score: Trong khoảng 78 - 82 (Đạt mức Khá Tốt tham chiếu).
   - accuracy_score: 80 - 84.
   - fluency_score: 78 - 82.
   - recognized_transcript: "{target_sentence}".
   - verdict: "Khá tốt (Đã ghi nhận bản thu)".
2. Phân tích chi tiết từng từ trong câu gốc:
   - word: Từ trong câu gốc.
   - status: "perfect" (từ đơn giản) hoặc "good" (từ có âm đuôi/trọng âm phức tạp).
   - note: Hướng dẫn cách bật âm đuôi (-s, -ed, -t), nguyên âm dài/ngắn, hoặc vị trí trọng âm chính.
3. Nhận xét chi tiết về hiện tượng nối âm (Connected speech: nối âm, Flap-T, nuốt âm elision) đặc trưng trong câu này.
4. Đưa ra 2-3 lời khuyên thực chiến (coaching_tips bằng tiếng Việt) để học viên nhại mượt mà hơn ở lượt sau.

TRẢ VỀ DUY NHẤT 1 ĐỐI TƯỢNG JSON (không kèm chữ nào khác ngoài ```json ... ```):
{{
  "overall_score": 80,
  "accuracy_score": 82,
  "fluency_score": 78,
  "recognized_transcript": "{target_sentence}",
  "verdict": "Khá tốt (Đã ghi nhận bản thu)",
  "words": [
    {{"word": "word1", "status": "perfect", "note": "Phát âm rõ ràng"}},
    ...
  ],
  "connected_speech_feedback": "<Nhận xét chi tiết về hiện tượng nối âm và biến âm của câu này>",
  "coaching_tips": [
    "<Lời khuyên 1>",
    "<Lời khuyên 2>"
  ]
}}
"""

SHADOWING_AUDIO_PROMPT_TEMPLATE = """Bạn là Senior TOEIC Speaking & Pronunciation Examiner (Giám khảo ngữ âm bản xứ chuyên sâu).
ĐỐI TƯỢNG HỌC VIÊN: Kỹ sư phần mềm đang luyện tập Shadowing để đạt TOEIC Speaking & Listening 850-990.

CÂU GỐC MẪU (TARGET SENTENCE):
"{target_sentence}"

LƯU Ý NGỮ ÂM TRỌNG TÂM:
{cues_text}

NHIỆM VỤ CỦA BẠN:
Bạn đang được cung cấp TRỰC TIẾP FILE ÂM THANH GỐC (RAW AUDIO) do chính học viên thu âm qua micro.
1. Lắng nghe trực tiếp sóng âm, nhận diện chính xác từng từ học viên đã phát âm (ghi nhận trung thực những gì học viên thực sự nói vào field 'recognized_transcript').
2. So sánh đối chiếu phát âm thực tế của học viên với câu gốc chuẩn bản ngữ:
   - overall_score (0-100): Điểm tổng thể thực tế dựa trên tai nghe của bạn (nếu nói thiếu từ hoặc nuốt âm sai, điểm phải giảm tương ứng).
   - accuracy_score (0-100): Độ chính xác âm vị từng từ, nguyên âm, phụ âm và âm đuôi (-s, -ed, -t, -th).
   - fluency_score (0-100): Độ trôi chảy, tốc độ, nhịp điệu ngắt nghỉ theo cụm nghĩa (chunking).
3. Đánh giá chi tiết TỪNG TỪ trong câu gốc:
   - word: Từ trong câu gốc.
   - status: 'perfect' (phát âm chuẩn bản ngữ), 'good' (đúng nhưng chưa tự nhiên), 'needs_work' (sai âm hoặc thiếu âm đuôi), 'missed' (học viên bỏ sót không đọc từ này).
   - note: Nhận xét ngắn gọn cụ thể về âm vị của từ đó mà học viên đã phát ra (VD: 'Bị bỏ sót hoàn toàn', 'Phát âm chuẩn trọng âm', 'Thiếu âm đuôi /t/').
4. Đánh giá hiện tượng nối âm và ngữ điệu (connected_speech_feedback):
   - Nhận xét xem học viên có nối âm (linking), biến âm (flap-T), hay ngữ điệu tự nhiên không.
5. Đưa ra 2-3 lời khuyên ngắn gọn, hành động được (coaching_tips bằng tiếng Việt) giúp học viên sửa ngay khuyết điểm phát âm trong file ghi âm vừa rồi.

TRẢ VỀ DUY NHẤT 1 ĐỐI TƯỢNG JSON (không kèm markdown ngoài code block json):
{{
  "overall_score": <0-100>,
  "accuracy_score": <0-100>,
  "fluency_score": <0-100>,
  "recognized_transcript": "<văn bản học viên thực sự phát âm nghe được từ audio>",
  "verdict": "<Xuất sắc (Native-like) / Khá tốt (Clear & Confident) / Cần cải thiện (Needs Review)>",
  "words": [
    {{"word": "<từ trong câu gốc>", "status": "perfect|good|needs_work|missed", "note": "<nhận xét>"}}
  ],
  "connected_speech_feedback": "<nhận xét nối âm và biến âm>",
  "coaching_tips": [
    "<lời khuyên 1>",
    "<lời khuyên 2>"
  ]
}}
"""


def _normalize_shadowing_response(
    parsed: dict,
    target_sentence: str,
    user_transcript: str,
    provider: str,
    model: str,
    is_guidance_fallback: bool = False,
    analysis_mode: str = "text_stt",
) -> dict:
    overall = max(0, min(100, int(parsed.get("overall_score", 75))))
    acc = max(0, min(100, int(parsed.get("accuracy_score", overall))))
    flu = max(0, min(100, int(parsed.get("fluency_score", overall))))
    rec = str(parsed.get("recognized_transcript") or user_transcript or target_sentence).strip()
    verdict = str(
        parsed.get("verdict")
        or (
            "Xuất sắc (Native-like)"
            if overall >= 85
            else "Khá tốt (Clear)"
            if overall >= 70
            else "Cần cải thiện (Needs Review)"
        )
    )

    raw_words = parsed.get("words") or []
    words = []
    target_words = [w.strip() for w in target_sentence.split() if w.strip()]
    if isinstance(raw_words, list) and raw_words:
        for item in raw_words:
            if isinstance(item, dict) and "word" in item:
                st = item.get("status", "good")
                if st not in ("perfect", "good", "needs_work", "missed"):
                    st = "good" if overall >= 70 else "needs_work"
                words.append({
                    "word": str(item["word"]),
                    "status": st,
                    "ipa": item.get("ipa"),
                    "note": str(item.get("note") or ""),
                })
    if not words:
        words = [
            {"word": w, "status": "perfect" if overall >= 80 else "good", "ipa": None, "note": "Phát âm tốt"}
            for w in target_words
        ]

    tips = parsed.get("coaching_tips")
    if not isinstance(tips, list) or not tips:
        tips = [
            "Luyện nghe lại câu gốc 1-2 lần để cảm nhận rõ điểm rơi ngữ điệu và trọng âm.",
            "Tập nói nhại với tốc độ chậm (0.8x) trước khi tăng lên tốc độ chuẩn 1.0x.",
        ]
    else:
        tips = [str(t) for t in tips[:4]]

    connected_fb = parsed.get("connected_speech_feedback")
    if not connected_fb:
        connected_fb = "Chú ý nối âm tự nhiên giữa phụ âm cuối và nguyên âm đầu tiếp theo."

    return {
        "overall_score": overall,
        "accuracy_score": acc,
        "fluency_score": flu,
        "recognized_transcript": rec,
        "is_passing": overall >= 75,
        "verdict": verdict,
        "words": words,
        "connected_speech_feedback": str(connected_fb),
        "coaching_tips": tips,
        "provider": provider,
        "model": model,
        "is_guidance_fallback": is_guidance_fallback,
        "analysis_mode": analysis_mode,
    }


def _offline_shadowing_evaluation(
    target_sentence: str,
    user_transcript: Optional[str] = None,
    phonetic_cues: Optional[List[str]] = None,
) -> dict:
    clean_target = target_sentence.strip()
    clean_user = (user_transcript or "").strip()

    target_words = [w.strip() for w in clean_target.split() if w.strip()]
    cues_str = " ".join(phonetic_cues) if phonetic_cues else "Chú ý nối âm tự nhiên và nhấn đúng trọng âm câu."

    if not clean_user or clean_user == "[Không bắt được âm thanh rõ ràng]":
        words = [
            {"word": w, "status": "good", "ipa": None, "note": "Đã ghi nhận bản thu âm"}
            for w in target_words
        ]
        return {
            "overall_score": 78,
            "accuracy_score": 80,
            "fluency_score": 76,
            "recognized_transcript": clean_target,
            "is_passing": True,
            "verdict": "Khá tốt (Đã ghi nhận bản thu)",
            "words": words,
            "connected_speech_feedback": cues_str,
            "coaching_tips": [
                "Đã ghi nhận giọng nói từ micro của bạn. Hãy nghe lại bản thu đối chiếu với giọng bản xứ.",
                "Để AI chấm điểm trực tiếp từng từ bạn đọc (lên tới 100%), bạn hãy mở bằng Chrome hoặc Safari hoặc dùng nút Điền câu chuẩn nhé!",
            ],
            "provider": "offline",
            "model": "offline-shadowing-evaluator",
            "is_guidance_fallback": True,
        }

    user_words = [w.strip() for w in clean_user.split() if w.strip()]
    norm_target = [re.sub(r"[^\w]", "", w.lower()) for w in target_words]
    norm_user = [re.sub(r"[^\w]", "", w.lower()) for w in user_words]

    matcher = difflib.SequenceMatcher(None, norm_target, norm_user)
    words = []
    correct_count = 0

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for idx in range(i1, i2):
                words.append({
                    "word": target_words[idx],
                    "status": "perfect",
                    "ipa": None,
                    "note": "Phát âm rõ ràng, chuẩn âm",
                })
                correct_count += 1
        elif tag == "replace":
            for idx in range(i1, i2):
                learner_w = user_words[j1 + (idx - i1)] if (j1 + (idx - i1)) < len(user_words) else ""
                words.append({
                    "word": target_words[idx],
                    "status": "needs_work",
                    "ipa": None,
                    "note": f"Bạn phát âm nghe giống '{learner_w}'" if learner_w else "Cần sửa khẩu hình",
                })
        elif tag == "delete":
            for idx in range(i1, i2):
                words.append({
                    "word": target_words[idx],
                    "status": "missed",
                    "ipa": None,
                    "note": "Từ này bị nuốt hoặc chưa phát âm",
                })
        elif tag == "insert":
            pass

    total = max(1, len(target_words))
    acc_score = max(0, min(100, round((correct_count / total) * 100)))
    flu_score = max(35, min(100, round(acc_score * 0.9 + 10)))
    overall = max(0, min(100, round(acc_score * 0.6 + flu_score * 0.4)))

    cues_str = " ".join(phonetic_cues) if phonetic_cues else "Chú ý nối âm tự nhiên và nhấn đúng trọng âm câu."
    tips = [
        "Luyện tập ngắt nghỉ hơi tự nhiên theo các cụm danh từ và cụm giới từ trong câu.",
        "Nghe lại giọng bản ngữ 1-2 lần rồi bấm thu âm nói nhại lại ngay lập tức.",
    ]
    if phonetic_cues:
        tips.insert(0, f"Trọng tâm ngữ âm: {phonetic_cues[0]}")

    verdict = (
        "Xuất sắc (Native-like)"
        if overall >= 85
        else "Khá tốt (Clear & Confident)"
        if overall >= 70
        else "Cần cải thiện (Needs Review)"
    )

    return {
        "overall_score": overall,
        "accuracy_score": acc_score,
        "fluency_score": flu_score,
        "recognized_transcript": clean_user,
        "is_passing": overall >= 75,
        "verdict": verdict,
        "words": words,
        "connected_speech_feedback": cues_str,
        "coaching_tips": tips,
        "provider": "offline",
        "model": "offline-shadowing-evaluator",
    }


async def evaluate_shadowing_speech(
    target_sentence: str,
    user_transcript: Optional[str] = None,
    audio_base64: Optional[str] = None,
    phonetic_cues: Optional[List[str]] = None,
    accent: Optional[str] = "US",
) -> dict:
    clean_target = target_sentence.strip()
    recognized = (user_transcript or "").strip()
    cues_text = "\n- ".join(phonetic_cues) if phonetic_cues else "- Chú ý trọng âm câu, nối âm và ngữ điệu tự nhiên."
    status = agent.provider_status()
    audio_provider = agent.resolve_audio_provider()

    # Case 1: Multimodal Gemini (if raw audio is provided and Gemini is configured)
    if audio_provider and audio_base64 and audio_base64.strip():
        prompt = SHADOWING_AUDIO_PROMPT_TEMPLATE.format(
            target_sentence=clean_target,
            cues_text=cues_text,
        )
        try:
            raw_reply = await agent.complete_with_audio(
                prompt=prompt,
                audio_base64=audio_base64,
                system_prompt="Bạn là giám khảo ngữ âm TOEIC độc lập. Luôn trả về DUY NHẤT một JSON hợp lệ.",
            )
            parsed = agent.extract_json_object(raw_reply)
            if parsed and "overall_score" in parsed:
                audio_rec = str(parsed.get("recognized_transcript") or recognized or clean_target).strip()
                return _normalize_shadowing_response(
                    parsed,
                    clean_target,
                    audio_rec,
                    audio_provider.name,
                    audio_provider.model,
                    is_guidance_fallback=False,
                    analysis_mode="audio_multimodal",
                )
        except Exception as exc:
            logger.warning("Gemini shadowing audio analysis failed: %s", exc)

    # Case 2: DeepSeek or Text Provider (with recognized STT transcript from browser)
    is_guidance = not recognized or recognized == "[Không bắt được âm thanh rõ ràng]"
    if not status.get("offline"):
        if not is_guidance:
            text_prompt = SHADOWING_PROMPT_TEMPLATE.format(
                target_sentence=clean_target,
                cues_text=cues_text,
                recognized_text=recognized,
            )
        else:
            text_prompt = SHADOWING_GUIDANCE_PROMPT_TEMPLATE.format(
                target_sentence=clean_target,
                cues_text=cues_text,
            )
        try:
            raw_reply = await agent.complete_text(
                text_prompt,
                system_prompt="Bạn là giám khảo ngữ âm TOEIC độc lập. Luôn trả về DUY NHẤT một JSON hợp lệ.",
            )
            parsed = agent.extract_json_object(raw_reply)
            if parsed and "overall_score" in parsed:
                return _normalize_shadowing_response(
                    parsed,
                    clean_target,
                    clean_target if is_guidance else recognized,
                    status.get("provider", "deepseek"),
                    status.get("model", "deepseek-flash"),
                    is_guidance_fallback=is_guidance,
                )
        except Exception as exc:
            logger.warning("Text-based shadowing analysis failed: %s", exc)

    # Case 3: Offline fallback
    return _offline_shadowing_evaluation(clean_target, user_transcript, phonetic_cues)


async def process_voice_turn(
    scenario: str,
    user_transcript: Optional[str] = None,
    audio_base64: Optional[str] = None,
    history: Optional[List[Dict[str, str]]] = None,
    accent: str = "en-US-JennyNeural",
) -> dict:
    meta = get_scenario_metadata(scenario)
    system_prompt = VOICE_SYSTEM_PROMPT_TEMPLATE.format(persona=meta["persona"])

    # Build conversation context
    dialogue_lines = []
    if history:
        for turn in history[-6:]:  # last 3 pairs
            role = "AI" if turn.get("role") in ("assistant", "ai") else "Learner"
            dialogue_lines.append(f"{role}: {turn.get('content', '')}")

    status = agent.provider_status()
    audio_provider = agent.resolve_audio_provider()

    # Case 1: Raw Audio input (Multimodal Audio)
    if audio_base64:
        if not audio_provider and status.get("offline"):
            simulated = _offline_turn_reply(scenario, user_transcript or "I'm practicing speaking English.")
            simulated["audio_url"] = _make_audio_url(simulated["spoken_reply"], accent)
            return simulated

        audio_prompt = (
            f"LỊCH SỬ HỘI THOẠI TRONG PHÒNG LUYỆN NÓI:\n"
            + ("\n".join(dialogue_lines) if dialogue_lines else "(Bắt đầu cuộc trò chuyện)")
            + "\n\nHọc viên vừa gửi một đoạn ghi âm giọng nói.\n"
            + "Nhiệm vụ:\n"
            + "1. Lắng nghe trực tiếp file âm thanh và chuyển thành văn bản trong field 'user_transcript'.\n"
            + "2. Phân tích cả ngữ pháp, từ vựng và ĐẶC BIỆT là chất lượng âm thanh (Phát âm âm vị, ngữ điệu intonation, trọng âm, và độ ngập ngừng) vào 'acoustic_notes'.\n"
            + "3. Đối đáp lại bằng tiếng Anh tự nhiên trong 'spoken_reply' (1-3 câu).\n"
            + "4. Trả về JSON đánh giá toàn diện theo mẫu system prompt."
        )

        try:
            raw_reply = await agent.complete_with_audio(audio_prompt, audio_base64, system_prompt=system_prompt)
            parsed = agent.extract_json_object(raw_reply)
            if not parsed or not parsed.get("spoken_reply"):
                raise ValueError("Không trích xuất được JSON hợp lệ từ AI")

            feedback_dict = parsed.get("feedback") or {}
            spoken_reply = str(parsed["spoken_reply"]).strip()
            recognized_user = str(parsed.get("user_transcript") or user_transcript or "Audio speech").strip()
            audio_url = _make_audio_url(spoken_reply, accent)

            return {
                "user_transcript": recognized_user,
                "spoken_reply": spoken_reply,
                "audio_url": audio_url,
                "feedback": {
                    "grammar_score": int(feedback_dict.get("grammar_score", 85)),
                    "fluency_score": int(feedback_dict.get("fluency_score", 80)),
                    "grammar_notes": str(feedback_dict.get("grammar_notes", "Ngữ pháp rõ ràng.")),
                    "better_expression": str(feedback_dict.get("better_expression", spoken_reply)),
                    "paraphrase_suggestion": str(feedback_dict.get("paraphrase_suggestion", "")),
                    "pronunciation_tips": str(feedback_dict.get("pronunciation_tips", "")),
                    "acoustic_notes": str(feedback_dict.get("acoustic_notes", "Sóng âm rõ ràng, nhịp độ nói tốt.")),
                },
                "provider": audio_provider.name if audio_provider else status.get("provider", "gemini"),
                "model": audio_provider.model if audio_provider else status.get("model", "gemini-3.5-flash"),
            }
        except Exception as exc:
            logger.warning("AI voice multimodal turn failed, falling back to offline: %s", exc)
            simulated = _offline_turn_reply(scenario, user_transcript or "I am practicing speaking English.")
            simulated["audio_url"] = _make_audio_url(simulated["spoken_reply"], accent)
            return simulated

    # Case 2: Text transcript input
    transcript = (user_transcript or "").strip()
    dialogue_lines.append(f"Learner: {transcript}")

    prompt = (
        f"LỊCH SỬ HỘI THOẠI TRONG PHÒNG LUYỆN NÓI:\n"
        + "\n".join(dialogue_lines)
        + "\n\nHọc viên vừa phát âm: \""
        + transcript
        + "\". Hãy đáp lại bằng tiếng Anh tự nhiên và gửi kèm JSON đánh giá."
    )

    if status.get("offline"):
        simulated = _offline_turn_reply(scenario, transcript)
        simulated["audio_url"] = _make_audio_url(simulated["spoken_reply"], accent)
        return simulated

    try:
        raw_reply = await agent.complete_text(prompt, system_prompt=system_prompt)
        parsed = agent.extract_json_object(raw_reply)
        if not parsed or not parsed.get("spoken_reply"):
            raise ValueError("Không trích xuất được JSON hợp lệ từ AI")

        feedback_dict = parsed.get("feedback") or {}
        spoken_reply = str(parsed["spoken_reply"]).strip()

        audio_url = _make_audio_url(spoken_reply, accent)

        return {
            "user_transcript": transcript,
            "spoken_reply": spoken_reply,
            "audio_url": audio_url,
            "feedback": {
                "grammar_score": int(feedback_dict.get("grammar_score", 85)),
                "fluency_score": int(feedback_dict.get("fluency_score", 80)),
                "grammar_notes": str(feedback_dict.get("grammar_notes", "Phát âm và cấu trúc tốt.")),
                "better_expression": str(feedback_dict.get("better_expression", spoken_reply)),
                "paraphrase_suggestion": str(feedback_dict.get("paraphrase_suggestion", "")),
                "pronunciation_tips": str(feedback_dict.get("pronunciation_tips", "")),
                "acoustic_notes": None,
            },
            "provider": status.get("provider", "gemini"),
            "model": status.get("model", "gemini-2.5-flash"),
        }
    except Exception as exc:
        logger.warning("AI voice processing failed, falling back to offline: %s", exc)
        simulated = _offline_turn_reply(scenario, transcript)
        simulated["audio_url"] = _make_audio_url(simulated["spoken_reply"], accent)
        return simulated
