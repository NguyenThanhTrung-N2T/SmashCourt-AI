import json
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY chưa được cấu hình trong .env")
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


# ─── Basic call (plain text) ──────────────────────────────────────────────────

async def call_gemini(message: str, context: str | None = None) -> tuple[str, str]:
    """Gửi message đơn giản tới Gemini, trả về (reply_text, model_name)."""
    prompt = message
    if context:
        prompt = f"Context:\n{context}\n\nUser message:\n{message}"

    response = await _get_client().aio.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    )
    return response.text, GEMINI_MODEL


# ─── Structured call (with system prompt + JSON output) ──────────────────────

async def call_gemini_structured(
    system_prompt: str,
    user_content: str,
) -> tuple[dict, str]:
    """
    Gọi Gemini với system prompt riêng, yêu cầu trả về JSON.
    Trả về (parsed_dict, model_name).
    Ném QuotaExceedError nếu hết free tier.
    """
    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        response_mime_type="application/json",
    )

    try:
        response = await _get_client().aio.models.generate_content(
            model=GEMINI_MODEL,
            contents=user_content,
            config=config,
        )
    except Exception as e:
        _handle_gemini_error(e)
        raise  # unreachable nhưng để type checker vui

    raw = response.text
    try:
        return json.loads(raw), GEMINI_MODEL
    except json.JSONDecodeError:
        # Fallback: cố parse nếu có dấu ```json ... ```
        cleaned = raw.strip().removeprefix("```json").removesuffix("```").strip()
        return json.loads(cleaned), GEMINI_MODEL


async def call_gemini_text(
    system_prompt: str,
    user_content: str,
) -> tuple[str, str]:
    """
    Gọi Gemini với system prompt, trả về plain text (không JSON).
    Trả về (text, model_name).
    """
    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
    )

    try:
        response = await _get_client().aio.models.generate_content(
            model=GEMINI_MODEL,
            contents=user_content,
            config=config,
        )
    except Exception as e:
        _handle_gemini_error(e)
        raise

    return response.text.strip(), GEMINI_MODEL


# ─── Error handling ───────────────────────────────────────────────────────────

class QuotaExceedError(Exception):
    """Ném khi Gemini API hết free tier quota (HTTP 429)."""
    pass


class LlmError(Exception):
    """Lỗi chung từ Gemini API."""
    pass


def _handle_gemini_error(e: Exception) -> None:
    err_str = str(e).lower()
    if "429" in err_str or "resource_exhausted" in err_str or "quota" in err_str:
        raise QuotaExceedError(
            "AI tạm thời không khả dụng do đã hết giới hạn miễn phí. "
            "Vui lòng thử lại sau vài phút."
        )
    raise LlmError(f"Lỗi khi gọi Gemini: {e}")
