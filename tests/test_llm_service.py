# AI-UT-02, AI-UT-03 (mức service) và task 1.46 (GEMINI_BASE_URL) — Epic 6C, gói 6C-1
import json

import pytest
from app.services import llm_service
from app.services.llm_service import LlmError, QuotaExceedError, build_client_kwargs, call_gemini_structured, call_gemini_text
from google.genai import types


# ── 1.46: client Gemini trỏ được vào LLM giả của môi trường đo ──

def test_build_client_kwargs_without_base_url_uses_google_endpoint():
    assert build_client_kwargs("khoa-gia", "") == {"api_key": "khoa-gia"}


def test_build_client_kwargs_with_base_url_points_http_options_at_it():
    kwargs = build_client_kwargs("khoa-gia", "http://llm-gia:9000")

    assert kwargs["api_key"] == "khoa-gia"
    assert isinstance(kwargs["http_options"], types.HttpOptions)
    assert kwargs["http_options"].base_url == "http://llm-gia:9000"


def test_build_client_kwargs_ignores_blank_base_url():
    assert "http_options" not in build_client_kwargs("khoa-gia", "   ")


# ── AI-UT-02: đọc response JSON của LLM ──

async def _structured(fake_llm, text: str) -> dict:
    fake_llm.reply(text)
    data, model = await call_gemini_structured("system", "user")
    assert model == llm_service.GEMINI_MODEL
    return data


@pytest.mark.parametrize(
    "raw",
    [
        '{"reply": "Chào bạn", "suggestions": ["Đặt sân"]}',
        '```json\n{"reply": "Chào bạn", "suggestions": ["Đặt sân"]}\n```',
        'Đây là kết quả: {"reply": "Chào bạn", "suggestions": ["Đặt sân"],}',
    ],
    ids=["json-thuan", "khoi-markdown", "chu-thua-va-dau-phay-cuoi"],
)
def test_structured_response_is_parsed_from_common_llm_shapes(fake_llm, raw):
    import asyncio

    data = asyncio.run(_structured(fake_llm, raw))

    assert data == {"reply": "Chào bạn", "suggestions": ["Đặt sân"]}


def test_structured_call_sends_system_prompt_and_asks_for_json(fake_llm):
    import asyncio

    fake_llm.reply(json.dumps({"reply": "ok"}))
    asyncio.run(call_gemini_structured("vai trò hệ thống", "nội dung người dùng"))

    call = fake_llm.calls[0]
    assert call["model"] == llm_service.GEMINI_MODEL
    assert call["contents"] == "nội dung người dùng"
    assert call["config"].system_instruction == "vai trò hệ thống"
    assert call["config"].response_mime_type == "application/json"


def test_structured_response_that_is_not_json_raises(fake_llm):
    import asyncio

    fake_llm.reply("Xin lỗi, tôi không trả lời được.")

    with pytest.raises(json.JSONDecodeError):
        asyncio.run(call_gemini_structured("system", "user"))


# ── AI-UT-03: lỗi của Gemini được đổi thành lỗi có nghĩa ──

@pytest.mark.parametrize(
    "message",
    ["429 Too Many Requests", "RESOURCE_EXHAUSTED: limit", "Quota exceeded for metric"],
)
def test_quota_errors_become_quota_exceed_error(fake_llm, message):
    import asyncio

    fake_llm.fail(RuntimeError(message))

    with pytest.raises(QuotaExceedError):
        asyncio.run(call_gemini_structured("system", "user"))


def test_other_errors_become_llm_error_for_both_call_styles(fake_llm):
    import asyncio

    fake_llm.fail(TimeoutError("deadline exceeded")).fail(ConnectionError("reset"))

    with pytest.raises(LlmError):
        asyncio.run(call_gemini_structured("system", "user"))
    with pytest.raises(LlmError):
        asyncio.run(call_gemini_text("system", "user"))
