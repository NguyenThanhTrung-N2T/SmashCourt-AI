# llm service - tích hợp api với gemini
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


async def call_gemini(message: str, context: str | None = None) -> tuple[str, str]:
    """
    gửi tin nhắn text thuần tới gemini
    """
    prompt = message
    if context:
        prompt = f"Context:\n{context}\n\nUser message:\n{message}"

    response = await _get_client().aio.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    )
    return response.text, GEMINI_MODEL


async def call_gemini_structured(
    system_prompt: str,
    user_content: str,
) -> tuple[dict, str]:
    """
    gọi gemini với system prompt và yêu cầu cấu trúc dữ liệu trả về dạng json
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
        raise

    raw = response.text
    try:
        return json.loads(raw), GEMINI_MODEL
    except json.JSONDecodeError:
        # xử lý fallback nếu text trả về bị bọc trong markdown block
        cleaned = raw.strip().removeprefix("```json").removesuffix("```").strip()
        return json.loads(cleaned), GEMINI_MODEL


async def call_gemini_text(
    system_prompt: str,
    user_content: str,
) -> tuple[str, str]:
    """
    gọi gemini với system prompt và trả về text thuần
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


class QuotaExceedError(Exception):
    """
    lỗi vượt quá giới hạn lượt gọi api (free tier)
    """
    pass


class LlmError(Exception):
    """
    lỗi chung từ dịch vụ llm
    """
    pass


def _handle_gemini_error(e: Exception) -> None:
    err_str = str(e).lower()
    if "429" in err_str or "resource_exhausted" in err_str or "quota" in err_str:
        raise QuotaExceedError(
            "AI tạm thời không khả dụng do đã hết giới hạn miễn phí. "
            "Vui lòng thử lại sau vài phút."
        )
    raise LlmError(f"Lỗi khi gọi Gemini: {e}")
