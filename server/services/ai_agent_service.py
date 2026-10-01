"""AI Mentor engine.

* Provider-agnostic: Gemini (REST generateContent) or any OpenAI-compatible chat API (DeepSeek, OpenAI).
* Real function calling over a registry of ~28 tools (services/agent_tools.py): the model can read the
  learner's skills, plan, error log and vocabulary, and change almost every piece of learning data
  (profile, memories, flashcards, SRS schedule, error log, plan, practice questions, reminders, notes...).
  Every change is audited with undo data.
* Personalized: each request carries the learner context (profile, exam date, mastery, pace, plan,
  suggestions, long-term memories, preferred explanation style), built from the same data as the dashboard.
* Offline fallback: without an API key (or when the provider fails) replies are assembled from the database;
  a few explicit commands (remember / replan / show plan / weaknesses) still run through audited tools.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Callable, Optional

import httpx
from sqlalchemy.orm import Session

from server import config
from server.models import AIMessage, Flashcard, ParaphrasePair, TestQuestion
from server.services import agent_tools, curriculum, insights

logger = logging.getLogger(__name__)

ERROR_TYPES = curriculum.ERROR_TYPES
_DATA_URL_RE = re.compile(r"^data:((?:image|audio)/[a-zA-Z0-9.+-]+);base64,(.+)$", re.S)
_ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp", "image/heic", "image/heif"}
_ALLOWED_AUDIO_TYPES = {"audio/webm", "audio/wav", "audio/mp3", "audio/mpeg", "audio/ogg", "audio/m4a", "audio/x-m4a", "audio/aac", "audio/flac"}


BASE_SYSTEM_PROMPT = """Bạn là Senior TOEIC AI Mentor & Learning Strategist — huấn luyện viên cá nhân của một kỹ sư phần mềm tự học TOEIC (mục tiêu 800-900+). Bạn có quyền đọc và chỉnh sửa dữ liệu học của học viên qua công cụ.

NGUYÊN TẮC:
1. Trả lời bằng tiếng Việt, logic, dùng thuật ngữ TOEIC chuẩn, định dạng Markdown. Tuân theo "Phong cách giải thích mong muốn" trong dữ liệu học viên.
2. Khi giải một câu hỏi, phân tích 3 chiều: (1) vì sao đáp án đúng, (2) 3 phương án còn lại là bẫy gì (VOCAB, GRAMMAR, PHONETICS, TRAP, TIME), (3) cặp Paraphrase & Collocation cần nhớ.
3. Cá nhân hoá: dựa vào DỮ LIỆU HỌC VIÊN (mastery, lỗi, tốc độ, kế hoạch, ngày thi, điều đã ghi nhớ) để chọn ví dụ, mức độ và việc nên làm. Chỉ dùng số liệu có trong dữ liệu hoặc đọc qua công cụ; không bịa.
4. Công cụ đọc (get_*, list_*, search_*, find_*): gọi khi cần số liệu chi tiết hơn phần tóm tắt.
5. Công cụ ghi: chỉ thực hiện khi học viên yêu cầu hoặc đã đồng ý với đề xuất của bạn. Ngoại lệ: được chủ động dùng remember_learner_fact để ghi nhớ thông tin ổn định học viên vừa chia sẻ (mục tiêu, lịch, sở thích, điểm yếu lặp lại).
   - Khi tạo nội dung (create_practice_questions, create_flashcards_bulk, add_lesson_note), bám vào lỗi và chuyên đề yếu của học viên; câu luyện phải đúng chuẩn TOEIC, có đúng 1 đáp án, kèm giải thích và tag bẫy.
   - Câu hỏi thuộc ngân hàng đề: đáp án lấy từ ngân hàng, không tự đổi.
6. Sau khi gọi công cụ ghi, xác nhận ngắn gọn kết quả và nhắc rằng có thể bấm "Hoàn tác" nếu không muốn thay đổi đó."""

VOCAB_SYSTEM_PROMPT = "Bạn là chuyên gia từ vựng TOEIC. Chỉ trả về một object JSON hợp lệ, không kèm văn bản khác."


# --------------------------------------------------------------------------- providers
@dataclass
class ProviderInfo:
    name: str
    model: str
    api_key: str
    base_url: str
    vision: bool


def _configured_providers() -> dict:
    providers = {}
    if config.GEMINI_API_KEY:
        providers["gemini"] = ProviderInfo("gemini", config.GEMINI_MODEL, config.GEMINI_API_KEY, config.GEMINI_BASE_URL, True)
    if config.DEEPSEEK_API_KEY:
        providers["deepseek"] = ProviderInfo(
            "deepseek", config.DEEPSEEK_MODEL, config.DEEPSEEK_API_KEY, config.DEEPSEEK_BASE_URL, False
        )
    if config.OPENAI_API_KEY:
        providers["openai"] = ProviderInfo("openai", config.OPENAI_MODEL, config.OPENAI_API_KEY, config.OPENAI_BASE_URL, True)
    return providers


def resolve_provider() -> Optional[ProviderInfo]:
    providers = _configured_providers()
    if config.AI_PROVIDER in providers:
        return providers[config.AI_PROVIDER]
    if config.AI_PROVIDER not in ("", "auto") and config.AI_PROVIDER not in providers:
        logger.warning("AI_PROVIDER=%s has no API key, falling back to auto", config.AI_PROVIDER)
    for name in ("gemini", "deepseek", "openai"):
        if name in providers:
            return providers[name]
    return None


def provider_status() -> dict:
    provider = resolve_provider()
    return {
        "provider": provider.name if provider else "offline",
        "model": provider.model if provider else None,
        "vision": bool(provider and provider.vision),
        "offline": provider is None,
        "configured_providers": list(_configured_providers()),
    }


# --------------------------------------------------------------------------- LLM calls
class LLMError(RuntimeError):
    pass


@dataclass
class ChatTurn:
    role: str  # "user" | "assistant"
    content: str


@dataclass
class AgentResult:
    reply: str
    actions: list = field(default_factory=list)
    provider: str = "offline"
    model: Optional[str] = None


ToolExecutor = Callable[[str, dict], dict]


def _http_client() -> httpx.AsyncClient:
    """Test seam: tests monkeypatch this to inject an httpx.MockTransport."""
    return httpx.AsyncClient(timeout=config.AI_TIMEOUT_SECONDS)


def split_media(media_base64: str, default_mime: str = "image/jpeg") -> tuple:
    value = media_base64.strip()
    match = _DATA_URL_RE.match(value)
    mime, data = (match.group(1).lower(), match.group(2)) if match else (default_mime, value)
    if mime not in _ALLOWED_IMAGE_TYPES and mime not in _ALLOWED_AUDIO_TYPES:
        raise LLMError(f"Định dạng media không hỗ trợ: {mime}")
    return mime, data


def split_image(image_base64: str) -> tuple:
    return split_media(image_base64, default_mime="image/jpeg")


def _normalize_turns(turns: list) -> list:
    """Merge consecutive same-role turns and drop leading assistant turns (Gemini requirement)."""
    merged = []
    for turn in turns:
        if not turn.content:
            continue
        if merged and merged[-1].role == turn.role:
            merged[-1] = ChatTurn(turn.role, merged[-1].content + "\n\n" + turn.content)
        else:
            merged.append(ChatTurn(turn.role, turn.content))
    while merged and merged[0].role != "user":
        merged.pop(0)
    return merged


async def run_agent(
    *,
    system_prompt: str,
    history: list,
    message: str,
    image_base64: Optional[str] = None,
    tool_executor: Optional[ToolExecutor] = None,
    max_rounds: int = 6,
) -> AgentResult:
    provider = resolve_provider()
    if provider is None:
        raise LLMError("Chưa cấu hình API key cho AI provider")
    try:
        if provider.name == "gemini":
            return await _run_gemini(provider, system_prompt, history, message, image_base64, tool_executor, max_rounds)
        return await _run_openai_compatible(provider, system_prompt, history, message, image_base64, tool_executor, max_rounds)
    except httpx.HTTPError as exc:
        raise LLMError(f"Không kết nối được {provider.name}: {exc.__class__.__name__}") from exc


async def _run_gemini(provider, system_prompt, history, message, image_base64, tool_executor, max_rounds) -> AgentResult:
    url = f"{provider.base_url}/models/{provider.model}:generateContent"
    turns = _normalize_turns(list(history))
    contents = [{"role": "model" if t.role == "assistant" else "user", "parts": [{"text": t.content}]} for t in turns]
    user_parts = [{"text": message}]
    if image_base64:
        mime, data = split_image(image_base64)
        user_parts.append({"inlineData": {"mimeType": mime, "data": data}})
    if contents and contents[-1]["role"] == "user":
        contents[-1]["parts"].extend(user_parts)
    else:
        contents.append({"role": "user", "parts": user_parts})

    base = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 2048},
    }
    if tool_executor is not None:
        base["tools"] = [{"functionDeclarations": agent_tools.declarations()}]
    actions = []
    async with _http_client() as client:
        for round_no in range(max_rounds):
            payload = {**base, "contents": contents}
            if tool_executor is not None and round_no == max_rounds - 1:
                payload["toolConfig"] = {"functionCallingConfig": {"mode": "NONE"}}  # force a final text answer
            resp = await client.post(url, headers={"x-goog-api-key": provider.api_key}, json=payload)
            if resp.status_code != 200:
                logger.warning("Gemini error %s: %s", resp.status_code, resp.text[:500])
                raise LLMError(f"Gemini trả về HTTP {resp.status_code}")
            candidate = (resp.json().get("candidates") or [{}])[0]
            parts = (candidate.get("content") or {}).get("parts") or []
            calls = [p["functionCall"] for p in parts if isinstance(p, dict) and p.get("functionCall")]
            text = "".join(p.get("text", "") for p in parts if isinstance(p, dict) and not p.get("thought")).strip()
            if not calls or tool_executor is None:
                if not text:
                    raise LLMError(f"Gemini trả về phản hồi rỗng ({candidate.get('finishReason', 'unknown')})")
                return AgentResult(text, actions, provider.name, provider.model)
            contents.append({"role": "model", "parts": parts})  # keep thought signatures intact
            responses = []
            for call in calls:
                result = tool_executor(call.get("name", ""), call.get("args") or {})
                actions.append(result)
                function_response = {"name": call.get("name", ""), "response": {"result": result}}
                if call.get("id"):
                    function_response["id"] = call["id"]
                responses.append({"functionResponse": function_response})
            contents.append({"role": "user", "parts": responses})
    return AgentResult(_summarize_actions(actions), actions, provider.name, provider.model)


async def _run_openai_compatible(provider, system_prompt, history, message, image_base64, tool_executor, max_rounds) -> AgentResult:
    url = f"{provider.base_url}/chat/completions"
    messages = [{"role": "system", "content": system_prompt}]
    messages += [{"role": t.role, "content": t.content} for t in history if t.content]
    note = ""
    if image_base64 and provider.vision:
        mime, data = split_image(image_base64)
        messages.append(
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": message},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{data}"}},
                ],
            }
        )
    else:
        if image_base64:
            note = f"\n\n> ℹ️ Model `{provider.model}` không đọc được ảnh — hãy dán nội dung câu hỏi dạng chữ."
        messages.append({"role": "user", "content": message})

    tools = [{"type": "function", "function": decl} for decl in agent_tools.declarations()] if tool_executor is not None else None
    actions = []
    async with _http_client() as client:
        for round_no in range(max_rounds):
            payload = {"model": provider.model, "messages": messages, "temperature": 0.3}
            if tools:
                payload["tools"] = tools
                if round_no == max_rounds - 1:
                    payload["tool_choice"] = "none"
            resp = await client.post(url, headers={"Authorization": f"Bearer {provider.api_key}"}, json=payload)
            if resp.status_code != 200:
                logger.warning("%s error %s: %s", provider.name, resp.status_code, resp.text[:500])
                raise LLMError(f"{provider.name} trả về HTTP {resp.status_code}")
            choice = (resp.json().get("choices") or [{}])[0]
            msg = choice.get("message") or {}
            tool_calls = msg.get("tool_calls") or []
            if not tool_calls or tool_executor is None:
                text = (msg.get("content") or "").strip()
                if not text:
                    raise LLMError(f"{provider.name} trả về phản hồi rỗng ({choice.get('finish_reason', 'unknown')})")
                return AgentResult(text + note, actions, provider.name, provider.model)
            assistant = {"role": "assistant", "content": msg.get("content"), "tool_calls": tool_calls}
            if msg.get("reasoning_content"):
                assistant["reasoning_content"] = msg["reasoning_content"]
            messages.append(assistant)
            for call in tool_calls:
                function = call.get("function") or {}
                try:
                    args = json.loads(function.get("arguments") or "{}")
                except json.JSONDecodeError:
                    args = {}
                result = tool_executor(function.get("name", ""), args if isinstance(args, dict) else {})
                actions.append(result)
                messages.append({"role": "tool", "tool_call_id": call.get("id"), "content": json.dumps(result, ensure_ascii=False)})
    return AgentResult(_summarize_actions(actions) + note, actions, provider.name, provider.model)


def _summarize_actions(actions: list) -> str:
    if not actions:
        return "Tôi chưa tạo được câu trả lời, bạn thử hỏi lại nhé."
    return "Đã thực hiện:\n" + "\n".join(f"- {a.get('message', a.get('tool'))}" for a in actions)


async def complete_text(prompt: str, system_prompt: str = VOCAB_SYSTEM_PROMPT) -> str:
    result = await run_agent(system_prompt=system_prompt, history=[], message=prompt, tool_executor=None, max_rounds=1)
    return result.reply


async def complete_with_audio(prompt: str, audio_base64: str, system_prompt: str = VOCAB_SYSTEM_PROMPT) -> str:
    provider = resolve_provider()
    if provider is None:
        raise LLMError("Chưa cấu hình API key cho AI provider")
    if provider.name == "gemini":
        url = f"{provider.base_url}/models/{provider.model}:generateContent"
        mime, data = split_media(audio_base64, default_mime="audio/webm")
        user_parts = [
            {"text": prompt},
            {"inlineData": {"mimeType": mime, "data": data}},
        ]
        payload = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": user_parts}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 2048},
        }
        async with _http_client() as client:
            resp = await client.post(url, headers={"x-goog-api-key": provider.api_key}, json=payload)
            if resp.status_code != 200:
                logger.warning("Gemini audio error %s: %s", resp.status_code, resp.text[:500])
                raise LLMError(f"Gemini trả về HTTP {resp.status_code}")
            candidate = (resp.json().get("candidates") or [{}])[0]
            parts = (candidate.get("content") or {}).get("parts") or []
            return "".join(p.get("text", "") for p in parts if isinstance(p, dict) and not p.get("thought")).strip()
    raise LLMError(f"Provider '{provider.name}' hiện chưa hỗ trợ phân tích trực tiếp sóng âm thanh. Hãy dùng Gemini.")


def extract_json_object(raw: str) -> Optional[dict]:
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    for candidate in (text, text[text.find("{") : text.rfind("}") + 1] if "{" in text else ""):
        if not candidate:
            continue
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return None


# --------------------------------------------------------------------------- grounding
def resolve_question(db: Session, pointer) -> Optional[TestQuestion]:
    """Accept a TestQuestion.id (123 / "123") or a legacy "TESTID_QNO" pointer ("ETS2024_01_108")."""
    if pointer is None or pointer == "":
        return None
    text = str(pointer).strip()
    if text.isdigit():
        return db.get(TestQuestion, int(text))
    test_id, _, number = text.rpartition("_")
    if test_id and number.isdigit():
        return db.query(TestQuestion).filter_by(test_id=test_id, question_no=int(number)).first()
    return None


def question_context(question: TestQuestion, titles: dict) -> str:
    cls = curriculum.classify_question(question)
    choices = " | ".join(
        f"({key}) {value}"
        for key, value in (("A", question.choice_a), ("B", question.choice_b), ("C", question.choice_c), ("D", question.choice_d))
        if value
    )
    lesson = titles.get(cls["lesson_number"]) if cls["lesson_number"] else None
    lines = [
        f"- Đề: {question.test_id} | {question.part} - Câu {question.question_no} (question_id={question.id})",
        f"- Câu hỏi: {question.sentence}",
        f"- Lựa chọn: {choices}",
        f"- Đáp án đúng: {question.correct_choice}",
    ]
    if question.explanation:
        lines.append(f"- Giải thích: {question.explanation}")
    if question.distractor_analysis:
        lines.append(f"- Phân tích bẫy: {question.distractor_analysis}")
    if question.paraphrase_pair:
        lines.append(f"- Paraphrase: {question.paraphrase_pair}")
    lines.append(f"- Phân loại RCA: {cls['error_type']}" + (f" · {lesson}" if lesson else ""))
    return "\n".join(lines)


def build_system_prompt(snapshot: str, question_ctx: Optional[str] = None, page_context: Optional[str] = None) -> str:
    sections = [BASE_SYSTEM_PROMPT, "DỮ LIỆU HỌC VIÊN (từ database, thời gian thực):\n" + snapshot]
    if question_ctx:
        sections.append("CÂU HỎI ĐANG THẢO LUẬN (từ ngân hàng đề — dùng làm căn cứ, không đổi đáp án):\n" + question_ctx)
    if page_context:
        sections.append(f"Học viên đang mở trang: {page_context[:200]}")
    return "\n\n".join(sections)


def load_history(db: Session, user_id: int, limit: int) -> list:
    if limit <= 0:
        return []
    rows = (
        db.query(AIMessage)
        .filter(AIMessage.user_id == user_id, AIMessage.role.in_(("user", "assistant")))
        .order_by(AIMessage.id.desc())
        .limit(limit)
        .all()
    )
    return [ChatTurn(row.role, row.content) for row in reversed(rows)]


# --------------------------------------------------------------------------- tools
def make_tool_executor(db: Session, user_id: int, question: Optional[TestQuestion], sink: list, source: str = "ai_mentor") -> ToolExecutor:
    """Runs registry tools for the model. The model receives full results (incl. data of read tools);
    `sink` collects what the UI shows: every write, and a compact entry for each read."""
    ctx = agent_tools.ToolContext(db=db, user_id=user_id, source=source, question=question)

    def execute(name: str, args: dict) -> dict:
        result = agent_tools.execute(ctx, name, args)
        shown = {key: value for key, value in result.items() if key != "data" or result.get("writes")}
        sink.append(shown)
        return result

    return execute


# --------------------------------------------------------------------------- offline mentor
_REMEMBER_RE = re.compile(r"^\s*(?:hãy\s+)?(?:ghi nhớ|nhớ giúp(?: tôi)?|nhớ rằng|remember)\s*[:：,-]?\s*(.+)$", re.IGNORECASE | re.S)


def offline_command(db: Session, user_id: int, message: str, executor: ToolExecutor) -> Optional[str]:
    """A few explicit commands still work without an LLM (all through audited tools)."""
    text = message.strip()
    lowered = text.lower()
    match = _REMEMBER_RE.match(text)
    if match and len(match.group(1).strip()) >= 3:
        result = executor("remember_learner_fact", {"content": match.group(1).strip(), "category": "other"})
        return f"🧠 {result['message']}. Tôi sẽ dùng thông tin này để cá nhân hoá các gợi ý sau."
    if "kế hoạch" in lowered and any(k in lowered for k in ("lập lại", "lên lại", "làm lại", "cập nhật", "sắp xếp lại", "replan")):
        result = executor("replan_week", {"reason": "offline_command"})
        return f"🗓️ {result['message']}. Xem chi tiết ở trang Lộ trình."
    if "kế hoạch" in lowered or "hôm nay học gì" in lowered or "nên học gì" in lowered:
        plan = executor("get_study_plan", {})
        days = plan.get("data", {}).get("days", [])
        if days:
            today = days[0]
            active = [i for i in today["items"] if i["status"] != "skipped"]
            done = sum(1 for i in active if i["status"] == "done")
            lines = [f"### 🗓️ Kế hoạch hôm nay (~{today['planned_minutes']} phút • xong {done}/{len(active)})"]
            for i in today["items"]:
                if i["status"] == "skipped":
                    lines.append(f"- ~~{i['title']}~~ (đã bỏ qua)")
                elif i["status"] == "done":
                    lines.append(f"- ✅ {i['title']} ({i['minutes']}')")
                else:
                    step = f" — {i['progress']}/{i['target']}" if i.get("target") and i.get("progress") else ""
                    link = f" → [Làm ngay]({i['href']})" if i.get("href", "").startswith("/") and i["kind"] != "custom" else ""
                    lines.append(f"- ⬜ {i['title']} ({i['minutes']}'){step}{link}")
            if not today["items"]:
                lines.append("- Hôm nay là ngày nghỉ theo lịch học của bạn")
            focus = plan["data"].get("focus") or []
            if focus:
                lines.append("\n**Trọng tâm tuần:**")
                lines += [f"- [{f['title']}](/lessons?lesson={f['lesson_number']}) — {f['reason']}" for f in focus]
            return "\n".join(lines)
    if any(k in lowered for k in ("điểm yếu", "lỗ hổng", "yếu nhất", "mastery")):
        report = executor("get_skill_report", {})
        lessons = [l for l in report.get("data", {}).get("lessons", []) if l["attempts"]][:4]
        if lessons:
            lines = ["### 📉 Chuyên đề cần ưu tiên"] + [
                f"- {l['title']}: **{l['mastery_pct']}%** sau {l['attempts']} câu{' (ít dữ liệu)' if l['attempts'] < 3 else ''}, {l['open_errors']} lỗi mở"
                f" → [Ôn bài](/lessons?lesson={l['lesson']}) • [Luyện](/mock-tests?lesson={l['lesson']})"
                for l in lessons
            ]
            lines.append("\nMẹo: nói “Lập lại kế hoạch” để kế hoạch 7 ngày ưu tiên các chuyên đề này.")
            return "\n".join(lines)
    return None


def offline_reply(db: Session, message: str, question: Optional[TestQuestion], dashboard: dict, reason: str,
                  executor: Optional[ToolExecutor] = None, user_id: Optional[int] = None) -> str:
    titles = insights.lesson_titles(db)
    banner = f"> ⚙️ Offline ({reason}) — trả lời trực tiếp từ dữ liệu học của bạn.\n\n"
    if question is not None:
        cls = curriculum.classify_question(question)
        lesson = titles.get(cls["lesson_number"]) if cls["lesson_number"] else None
        choices = "\n".join(
            f"- ({key}) {value}"
            for key, value in (("A", question.choice_a), ("B", question.choice_b), ("C", question.choice_c), ("D", question.choice_d))
            if value
        )
        body = [
            f"### 🎯 {question.part} - Câu {question.question_no} ({question.test_id})",
            f"**Câu hỏi:** {question.sentence}",
            choices,
            f"**Đáp án đúng: ({question.correct_choice})**" + (f" — {question.explanation}" if question.explanation else ""),
        ]
        if question.distractor_analysis:
            body += ["#### 🔍 Bẫy loại trừ", question.distractor_analysis]
        if question.paraphrase_pair:
            body += ["#### 💡 Paraphrase & Collocation", f"`{question.paraphrase_pair}`"]
        body += ["#### ⚠️ Action item", f"- Mã lỗi RCA: **{cls['error_type']}**"]
        if lesson:
            body.append(f"- Ôn lại: **{lesson}**")
        return banner + "\n\n".join(body)

    if executor is not None and user_id is not None:
        command = offline_command(db, user_id, message, executor)
        if command:
            return banner + command

    tokens = set(re.findall(r"[a-z][a-z-]{2,}", message.lower()))
    if tokens:
        card = db.query(Flashcard).filter(Flashcard.word.in_(tokens)).first()
        if card is not None:
            lines = [f"### 📘 {card.word}" + (f" /{card.ipa}/" if card.ipa else ""), f"**Nghĩa:** {card.meaning}"]
            if card.collocations:
                lines.append(f"**Collocations:** {card.collocations}")
            if card.paraphrase_pair:
                lines.append(f"**Paraphrase:** {card.paraphrase_pair}")
            lines.append(f"**Ví dụ:** _{card.example_sentence}_")
            return banner + "\n\n".join(lines)
        pair = db.query(ParaphrasePair).filter(ParaphrasePair.word_in_text.in_(tokens)).first()
        if pair is not None:
            return banner + f"### 🔁 Paraphrase Vault\n\n`{pair.word_in_text}` = `{pair.word_in_answer}` — {pair.meaning or ''} ({pair.part_target})"

    predicted = dashboard.get("predicted_score") or {}
    lines = [
        "### 📋 Tình hình học của bạn",
        f"- Tuần **{dashboard['current_week']}/{dashboard['total_weeks']}** · mục tiêu **{dashboard['target_score']}** "
        f"({dashboard['target_cefr']}) · chuỗi **{dashboard['streak_days']}** ngày",
        f"- Điểm dự đoán: **{predicted.get('total', '—')}** (khoảng {predicted.get('low', '—')}-{predicted.get('high', '—')})",
        f"- SRS: **{dashboard['srs_due_count']}** thẻ cần học hôm nay, đã thuộc {dashboard['srs_mastered_count']}",
        f"- Sổ lỗi: **{dashboard['open_errors']}** câu chưa khắc phục, {dashboard.get('error_reviews_due', 0)} câu đến hạn ôn",
    ]
    if dashboard["learning_gaps"]:
        lines.append("- Lỗ hổng lớn nhất: " + ", ".join(g["topic"] for g in dashboard["learning_gaps"][:3]))
    pending = [task for task in dashboard["today_tasks"] if not task["done"]]
    if pending:
        lines += ["", "**Việc nên làm tiếp:**"] + [f"{i}. {task['title']}" for i, task in enumerate(pending[:3], 1)]
    lines += ["", "_Lệnh dùng được khi offline: 'Ghi nhớ: …', 'Lập lại kế hoạch', 'Kế hoạch hôm nay', 'Điểm yếu của tôi'._"]
    return banner + "\n".join(lines)


def suggested_questions(question: Optional[TestQuestion], page_context: Optional[str], titles: dict) -> list:
    if question is not None:
        lesson_number = curriculum.classify_question(question)["lesson_number"]
        lesson = titles.get(lesson_number) if lesson_number else None
        return [
            "Cho tôi 3 câu tương tự để luyện",
            f"Tóm tắt quy tắc của {lesson}" if lesson else "Quy tắc nhận diện nhanh dạng câu này?",
            "Tôi làm sai câu này, lưu vào Sổ Lỗi giúp tôi",
        ]
    page = page_context or ""
    if "/vocab" in page:
        return ["Thêm 10 từ chủ đề Finance tôi chưa có vào Sổ tay", "Sửa các thẻ tôi hay quên cho dễ nhớ hơn", "Lưu từ 'reimburse' vào Sổ tay"]
    if "/error-log" in page:
        return ["Phân tích lỗ hổng lớn nhất của tôi", "Tạo 5 câu luyện cho chuyên đề tôi yếu nhất", "Quy tắc vàng tránh bẫy [TRAP]"]
    if "/mock-tests" in page:
        return ["Mẹo làm Part 5 dưới 15 giây/câu", "Tạo 5 câu luyện cho lỗi tôi vừa mắc", "Phân bổ thời gian 75 phút Reading"]
    if "/roadmaps" in page:
        return ["Tuần này tôi nên tập trung gì?", "Tôi bận thứ 4, dời nhiệm vụ sang thứ 5", "Lập lại kế hoạch theo dữ liệu mới"]
    return ["Hôm nay tôi nên học gì?", "Phân tích lỗ hổng lớn nhất của tôi", "Ghi nhớ: tôi chỉ rảnh 30 phút buổi tối"]
