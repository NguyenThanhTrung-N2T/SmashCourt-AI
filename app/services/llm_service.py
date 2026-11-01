# llm service - tích hợp api với gemini
import json
import logging
import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types

from app.services import telemetry

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
# Chỉ đặt ở môi trường đo hiệu năng (Epic 6C): trỏ client vào LLM giả thay cho Google; để trống thì gọi Gemini thật
GEMINI_BASE_URL = os.getenv("GEMINI_BASE_URL", "")

_client: genai.Client | None = None
# metric lời gọi gemini (ob-ai-1); test thay bằng meter riêng
gemini_metrics = telemetry.gemini_metrics


def build_client_kwargs(api_key: str, base_url: str) -> dict:
    """
    tham số tạo genai.Client: thêm http_options.base_url khi có GEMINI_BASE_URL (LLM giả của môi trường đo)
    """
    kwargs: dict = {"api_key": api_key}
    if base_url.strip():
        kwargs["http_options"] = types.HttpOptions(base_url=base_url.strip())
    return kwargs


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY chưa được cấu hình trong .env")
        _client = genai.Client(**build_client_kwargs(GEMINI_API_KEY, GEMINI_BASE_URL))
    return _client


async def _generate(operation: str, **kwargs):
    """
    mọi lời gọi gemini đi qua đây để đo độ trễ, kết quả (ok / quota / error) và số token
    """
    client = _get_client()
    started = time.perf_counter()
    try:
        response = await client.aio.models.generate_content(model=GEMINI_MODEL, **kwargs)
    except Exception as e:
        outcome = telemetry.OUTCOME_QUOTA if _is_quota_error(e) else telemetry.OUTCOME_ERROR
        gemini_metrics.record(operation=operation, model=GEMINI_MODEL, outcome=outcome, duration_s=time.perf_counter() - started)
        raise
    gemini_metrics.record(
        operation=operation,
        model=GEMINI_MODEL,
        outcome=telemetry.OUTCOME_OK,
        duration_s=time.perf_counter() - started,
        usage=getattr(response, "usage_metadata", None),
    )
    return response


async def call_gemini(message: str, context: str | None = None) -> tuple[str, str]:
    """
    gửi tin nhắn text thuần tới gemini
    """
    prompt = message
    if context:
        prompt = f"Context:\n{context}\n\nUser message:\n{message}"

    response = await _generate("plain", contents=prompt)
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
        response = await _generate("structured", contents=user_content, config=config)
    except Exception as e:
        _handle_gemini_error(e)
        raise

    raw = response.text
    try:
        return json.loads(raw), GEMINI_MODEL
    except json.JSONDecodeError:
        import re
        # Xử lý fallback: Loại bỏ các block markdown ```json
        cleaned = raw.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        # Tìm block JSON dạng { ... } lớn nhất nếu Gemini trả về cả chữ bình thường
        first_brace = cleaned.find('{')
        last_brace = cleaned.rfind('}')
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            cleaned = cleaned[first_brace:last_brace+1]

        # Loại bỏ dấu phẩy thừa cuối cùng (trailing commas)
        cleaned = re.sub(r',(\s*[}\]])', r'\1', cleaned)

        try:
            return json.loads(cleaned), GEMINI_MODEL
        except json.JSONDecodeError as final_err:
            # Ghi log lỗi thô của Gemini để dễ gỡ lỗi
            logging.getLogger(__name__).error(f"Failed to parse cleaned JSON. Raw response was: {raw}")
            raise final_err


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
        response = await _generate("text", contents=user_content, config=config)
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


def _is_quota_error(e: Exception) -> bool:
    err_str = str(e).lower()
    return "429" in err_str or "resource_exhausted" in err_str or "quota" in err_str


def _handle_gemini_error(e: Exception) -> None:
    if _is_quota_error(e):
        raise QuotaExceedError(
            "AI tạm thời không khả dụng do đã hết giới hạn miễn phí. "
            "Vui lòng thử lại sau vài phút."
        )
    raise LlmError(f"Lỗi khi gọi Gemini: {e}")
