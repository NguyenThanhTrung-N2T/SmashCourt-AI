"""
Chat Router — Customer chatbot endpoints
  POST /api/v1/ai/chat        — Free-form chat
  GET  /api/v1/ai/chat/faq   — List câu hỏi gợi ý
  POST /api/v1/ai/chat/faq-reply — Trả lời FAQ cụ thể
"""
import logging
from datetime import datetime

from app.models.ai_schemas import (
    ChatRequest,
    ChatResponse,
    FaqItem,
    FaqListResponse,
    FaqReplyRequest,
    FaqReplyResponse,
)
from app.services.llm_service import (
    LlmError,
    QuotaExceedError,
    call_gemini_structured,
    call_gemini_text,
)
from app.services.prompt_builder import (
    CHATBOT_SYSTEM_PROMPT,
    FAQ_SYSTEM_PROMPT,
    build_chat_prompt,
    build_faq_prompt,
)
from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai/chat", tags=["AI — Chatbot"])

# ─── Mock FAQ list (sẽ thay bằng data từ BE sau) ─────────────────────────────
_FAQ_ITEMS: list[FaqItem] = [
    FaqItem(id="faq-1",  question="Giá thuê sân cầu lông là bao nhiêu?",         category="pricing"),
    FaqItem(id="faq-2",  question="Làm thế nào để đặt sân online?",               category="booking"),
    FaqItem(id="faq-3",  question="Có thể hủy đặt sân không? Phí hủy như thế nào?", category="policy"),
    FaqItem(id="faq-4",  question="Sân có cho thuê vợt và giày không?",           category="equipment"),
    FaqItem(id="faq-5",  question="Giờ mở cửa của chi nhánh là mấy giờ?",        category="general"),
    FaqItem(id="faq-6",  question="Có chương trình khuyến mãi hay ưu đãi thành viên không?", category="promotion"),
    FaqItem(id="faq-7",  question="Tôi muốn thuê sân cố định theo tháng thì làm thế nào?", category="booking"),
    FaqItem(id="faq-8",  question="Tôi cần mang gì khi đến chơi?",               category="general"),
]


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("", response_model=ChatResponse, summary="Chat tự do với AI")
async def chat(req: ChatRequest):
    """Nhận câu hỏi tự do của khách hàng, gọi Gemini và trả về câu trả lời kèm gợi ý hành động."""
    logger.info(f"Chat request received: session_id={req.session_id}, message_length={len(req.message)}")
    
    user_content = build_chat_prompt(req.message, req.context)
    try:
        data, model = await call_gemini_structured(CHATBOT_SYSTEM_PROMPT, user_content)
        logger.info(f"Chat response generated successfully: model={model}")
    except QuotaExceedError as e:
        logger.error(f"Gemini quota exceeded: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except LlmError as e:
        logger.error(f"LLM error in chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    return ChatResponse(
        reply=data.get("reply", ""),
        suggestions=data.get("suggestions", []),
        model=model,
        session_id=req.session_id,
        generated_at=datetime.now(),
    )


@router.get("/faq", response_model=FaqListResponse, summary="Danh sách câu hỏi gợi ý")
async def get_faq():
    """Trả về danh sách câu hỏi thường gặp (FAQ) để hiển thị quick-reply buttons."""
    logger.info(f"FAQ list requested: returning {len(_FAQ_ITEMS)} items")
    return FaqListResponse(items=_FAQ_ITEMS, total=len(_FAQ_ITEMS))


@router.post("/faq-reply", response_model=FaqReplyResponse, summary="Trả lời câu hỏi FAQ")
async def faq_reply(req: FaqReplyRequest):
    """Nhận một câu hỏi FAQ cụ thể, gọi Gemini để trả lời chi tiết."""
    logger.info(f"FAQ reply request: faq_id={req.faq_id}, question={req.question[:50]}...")
    
    user_content = build_faq_prompt(req.question)
    try:
        reply, model = await call_gemini_text(FAQ_SYSTEM_PROMPT, user_content)
        logger.info(f"FAQ reply generated successfully: model={model}")
    except QuotaExceedError as e:
        logger.error(f"Gemini quota exceeded for FAQ: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except LlmError as e:
        logger.error(f"LLM error in FAQ reply: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    return FaqReplyResponse(
        faq_id=req.faq_id,
        question=req.question,
        reply=reply,
        model=model,
        generated_at=datetime.now(),
    )
