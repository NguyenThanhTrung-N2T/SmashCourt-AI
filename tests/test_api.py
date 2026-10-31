# AI-UT-01 (dựng prompt), AI-UT-03 (mã lỗi trả về), AI-UT-04 (schema vào/ra), AI-UT-05 (/health) qua HTTP — Epic 6C, gói 6C-1
import json

import pytest
from app.services import llm_service
from app.services.prompt_builder import CHATBOT_SYSTEM_PROMPT, FAQ_SYSTEM_PROMPT, build_booking_suggest_prompt


# ── AI-UT-05: /health ──

def test_health_returns_ok_without_calling_llm(client, fake_llm):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert fake_llm.calls == []


# ── AI-UT-01: nội dung gửi cho LLM ──

def test_chat_sends_chatbot_system_prompt_with_message_and_context(client, fake_llm):
    fake_llm.reply(json.dumps({"reply": "Còn sân lúc 18h", "suggestions": []}))

    client.post("/api/v1/ai/chat", json={"message": "Tối nay còn sân không?", "context": "Chi nhánh Thủ Đức"})

    call = fake_llm.calls[0]
    assert call["config"].system_instruction == CHATBOT_SYSTEM_PROMPT
    assert "Tối nay còn sân không?" in call["contents"]
    assert "Chi nhánh Thủ Đức" in call["contents"]


def test_faq_reply_sends_faq_system_prompt_with_question(client, fake_llm):
    fake_llm.reply("Bạn có thể hủy trước 24 giờ.")

    response = client.post("/api/v1/ai/chat/faq-reply", json={"faq_id": "faq-3", "question": "Có thể hủy đặt sân không?"})

    assert response.status_code == 200
    call = fake_llm.calls[0]
    assert call["config"].system_instruction == FAQ_SYSTEM_PROMPT
    assert "Có thể hủy đặt sân không?" in call["contents"]


def test_booking_prompt_keeps_only_the_ten_latest_bookings():
    from app.models.ai_schemas import BookingHistoryItem, BookingSuggestionRequest

    history = [
        BookingHistoryItem(booking_date=f"2026-10-{day:02d}", branch_name="CN A", court_type="Tiêu chuẩn",
                           time_slots=["08:00-09:00"], status="CONFIRMED", total_amount=100000)
        for day in range(1, 13)
    ]
    prompt = build_booking_suggest_prompt(BookingSuggestionRequest(user_id="u1", booking_history=history))

    assert "2026-10-12" in prompt and "2026-10-03" in prompt
    assert "2026-10-01" not in prompt and "2026-10-02" not in prompt


# ── AI-UT-04: schema vào/ra ──

def test_chat_response_has_reply_suggestions_model_session_and_timestamp(client, fake_llm):
    fake_llm.reply(json.dumps({"reply": "Chào bạn", "suggestions": ["Đặt sân", "Xem giá"]}))

    response = client.post("/api/v1/ai/chat", json={"message": "Xin chào", "session_id": "s-1"})

    assert response.status_code == 200
    body = response.json()
    assert body["reply"] == "Chào bạn"
    assert body["suggestions"] == ["Đặt sân", "Xem giá"]
    assert body["model"] == llm_service.GEMINI_MODEL
    assert body["session_id"] == "s-1"
    assert body["generated_at"]


@pytest.mark.parametrize("message", ["", "x" * 2001], ids=["rong", "qua-2000-ky-tu"])
def test_chat_rejects_invalid_message_without_calling_llm(client, fake_llm, message):
    response = client.post("/api/v1/ai/chat", json={"message": message})

    assert response.status_code == 422
    assert fake_llm.calls == []


def test_faq_list_needs_no_llm(client, fake_llm):
    response = client.get("/api/v1/ai/chat/faq")

    assert response.status_code == 200
    assert response.json()["total"] == len(response.json()["items"]) > 0
    assert fake_llm.calls == []


# ── AI-UT-03: lỗi của Gemini ⇒ mã HTTP mà BE xử lý ──

def test_chat_quota_exceeded_returns_503_with_message(client, fake_llm):
    fake_llm.fail(RuntimeError("429 RESOURCE_EXHAUSTED"))

    response = client.post("/api/v1/ai/chat", json={"message": "Xin chào"})

    assert response.status_code == 503
    assert "giới hạn" in response.json()["detail"]


def test_chat_other_llm_error_returns_500(client, fake_llm):
    fake_llm.fail(ConnectionError("connection reset"))

    response = client.post("/api/v1/ai/chat", json={"message": "Xin chào"})

    assert response.status_code == 500


def test_faq_reply_quota_exceeded_returns_503(client, fake_llm):
    fake_llm.fail(RuntimeError("quota exceeded"))

    response = client.post("/api/v1/ai/chat/faq-reply", json={"faq_id": "faq-1", "question": "Giá thuê sân?"})

    assert response.status_code == 503
