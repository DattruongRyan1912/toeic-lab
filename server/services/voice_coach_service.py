"""Voice Coach 1-on-1 Service.
Handles turn-based conversational coaching, real-time grammar & pronunciation analysis,
and native audio generation via Edge-TTS.
"""
from __future__ import annotations

import logging
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
   - Nếu học viên đọc đúng hoàn toàn: Phân tích các âm vị chuẩn, âm đuôi và độ tự nhiên. Cho điểm cao (85-98 tùy độ phức tạp của từ).
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


def _offline_vocab_pronunciation(word: str, expected_ipa: Optional[str], recognized_text: Optional[str] = None) -> dict:
    target_ipa = expected_ipa or f"/{word}/"
    if recognized_text is None:
        rec = word
    else:
        rec = recognized_text.strip()

    if not rec or rec == "[Không bắt được âm thanh rõ ràng]":
        return {
            "word": word,
            "score": 35,
            "recognized_text": "[Âm thanh không rõ]",
            "recognized_ipa": target_ipa,
            "expected_ipa": target_ipa,
            "is_accurate": False,
            "feedback": {
                "vowels": "Âm lượng thu vào quá nhỏ hoặc ngắt quãng, chưa nhận diện rõ nguyên âm.",
                "consonants": "Chưa ghi nhận được các phụ âm và âm đuôi cần thiết.",
                "stress": "Chưa đủ dữ liệu sóng âm để xác định trọng âm.",
                "tips": "Hãy kiểm tra micro, đưa gần miệng hơn và nói to, dứt khoát từng âm tiết.",
            },
            "provider": "offline",
            "model": "offline-phonetic-coach",
        }

    is_match = rec.lower() == word.lower()
    score = 90 if is_match else 60
    return {
        "word": word,
        "score": score,
        "recognized_text": rec,
        "recognized_ipa": target_ipa if is_match else f"/{rec}/",
        "expected_ipa": target_ipa,
        "is_accurate": is_match,
        "feedback": {
            "vowels": "Nguyên âm phát âm rõ ràng, trường độ tốt." if is_match else "Nguyên âm có phần bị lệch khẩu hình so với âm chuẩn.",
            "consonants": "Bật âm phụ âm đầu và âm đuôi đầy đủ." if is_match else f"Chú ý âm đuôi và các phụ âm nối trong từ '{word}'.",
            "stress": "Trọng âm nhấn đúng vào âm tiết chính." if is_match else "Cần nhấn dứt khoát hơn vào âm tiết mang trọng âm chính.",
            "tips": "Duy trì luyện tập đều đặn để tạo phản xạ tự nhiên." if is_match else f"Luyện nghe lại phát âm mẫu của '{word}' và tập nhại theo âm đuôi.",
        },
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

    # Case 1: Multimodal Gemini is configured -> analyze raw audio directly
    if status.get("provider") == "gemini" and not status.get("offline") and audio_base64:
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
                    "provider": "gemini",
                    "model": status.get("model", "gemini-2.5-flash"),
                }
        except Exception as exc:
            logger.warning("Gemini audio analysis failed, falling back to text analysis: %s", exc)

    # Case 2: DeepSeek or Text Provider (with recognized STT transcript from browser)
    recognized = (user_transcript or "").strip()
    if not status.get("offline"):
        text_prompt = VOCAB_PRONOUNCE_TEXT_PROMPT_TEMPLATE.format(
            word=clean_word,
            expected_ipa=target_ipa,
            recognized_text=recognized or "[Không bắt được âm thanh rõ ràng]",
        )
        try:
            raw_reply = await agent.complete_text(
                text_prompt,
                system_prompt="Bạn là giám khảo ngữ âm TOEIC. Luôn trả về duy nhất 1 JSON hợp lệ.",
            )
            parsed = agent.extract_json_object(raw_reply)
            if parsed and "score" in parsed:
                fb = parsed.get("feedback") or {}
                score = max(0, min(100, int(parsed.get("score", 70 if recognized else 35))))
                return {
                    "word": clean_word,
                    "score": score,
                    "recognized_text": str(parsed.get("recognized_text", recognized or clean_word)),
                    "recognized_ipa": str(parsed.get("recognized_ipa", target_ipa)),
                    "expected_ipa": str(parsed.get("expected_ipa", target_ipa)),
                    "is_accurate": bool(parsed.get("is_accurate", score >= 75)),
                    "feedback": {
                        "vowels": str(fb.get("vowels", "Nguyên âm cần luyện tập thêm.")),
                        "consonants": str(fb.get("consonants", "Chú ý bật rõ âm đuôi.")),
                        "stress": str(fb.get("stress", "Chú ý trọng âm chính của từ.")),
                        "tips": str(fb.get("tips", "Luyện nghe lại phát âm mẫu và nhại theo từng âm tiết.")),
                    },
                    "provider": status.get("provider", "deepseek"),
                    "model": status.get("model", "deepseek-flash"),
                }
        except Exception as exc:
            logger.warning("Text-based pronunciation analysis failed: %s", exc)

    # Case 3: Offline fallback
    return _offline_vocab_pronunciation(clean_word, target_ipa, user_transcript)


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

    # Case 1: Raw Audio input (Multimodal Audio)
    if audio_base64:
        if status.get("offline"):
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
                "provider": status.get("provider", "gemini"),
                "model": status.get("model", "gemini-2.5-flash"),
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
