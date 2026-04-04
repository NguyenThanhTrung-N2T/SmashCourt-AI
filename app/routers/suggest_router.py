"""
Suggest Router — Personal suggestion endpoints
  POST /api/v1/ai/suggest/booking  — Gợi ý khi đặt sân
  POST /api/v1/ai/suggest/profile  — Gợi ý trên trang cá nhân
"""
from datetime import datetime

from app.models.ai_schemas import (
    BookingSuggestionRequest,
    BookingSuggestionResponse,
    ProfileSuggestionRequest,
    ProfileSuggestionResponse,
    SuggestionItem,
)
from app.services.llm_service import (
    LlmError,
    QuotaExceedError,
    call_gemini_structured,
)
from app.services.prompt_builder import (
    BOOKING_SUGGEST_SYSTEM_PROMPT,
    PROFILE_SUGGEST_SYSTEM_PROMPT,
    build_booking_suggest_prompt,
    build_profile_suggest_prompt,
)
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/ai/suggest", tags=["AI — Personal Suggestions"])


def _parse_suggestions(raw: list) -> list[SuggestionItem]:
    """Parse list dict từ LLM thành list SuggestionItem, bỏ qua item lỗi."""
    items = []
    for s in raw:
        try:
            items.append(SuggestionItem(**s))
        except Exception:
            pass
    return items


@router.post("/booking", response_model=BookingSuggestionResponse, summary="Gợi ý sân/giờ khi đặt sân")
async def suggest_booking(req: BookingSuggestionRequest):
    """
    Nhận lịch sử booking của khách hàng, phân tích và trả về gợi ý sân/giờ phù hợp
    để hiển thị khi khách đang trong luồng đặt sân.
    """
    if not req.booking_history:
        # Khách mới chưa có lịch sử → trả về gợi ý mặc định mà không cần gọi LLM
        return BookingSuggestionResponse(
            user_id=req.user_id,
            suggestions=[
                SuggestionItem(
                    type="general",
                    title="Chào mừng bạn đến SmashCourt!",
                    description="Hãy thử đặt sân sáng sớm (6h-8h) hoặc buổi tối (19h-21h) để có giá tốt nhất.",
                    action="Xem lịch sân",
                ),
            ],
            model="none",
            generated_at=datetime.now(),
        )

    user_content = build_booking_suggest_prompt(req)
    try:
        data, model = await call_gemini_structured(BOOKING_SUGGEST_SYSTEM_PROMPT, user_content)
    except QuotaExceedError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except LlmError as e:
        raise HTTPException(status_code=500, detail=str(e))

    suggestions = _parse_suggestions(data.get("suggestions", []))

    return BookingSuggestionResponse(
        user_id=req.user_id,
        suggestions=suggestions,
        model=model,
        generated_at=datetime.now(),
    )


@router.post("/profile", response_model=ProfileSuggestionResponse, summary="Gợi ý trên trang cá nhân")
async def suggest_profile(req: ProfileSuggestionRequest):
    """
    Nhận lịch sử booking và thông tin loyalty của khách hàng,
    sinh tóm tắt hành vi và gợi ý cá nhân hóa để hiển thị trên trang cá nhân.
    """
    if not req.booking_history:
        return ProfileSuggestionResponse(
            user_id=req.user_id,
            summary="Bạn chưa có lịch sử đặt sân. Hãy thử đặt sân đầu tiên để nhận gợi ý cá nhân hóa!",
            suggestions=[
                SuggestionItem(
                    type="general",
                    title="Bắt đầu hành trình thể thao",
                    description="Đặt sân lần đầu và tích lũy điểm thành viên.",
                    action="Đặt sân ngay",
                )
            ],
            model="none",
            generated_at=datetime.now(),
        )

    user_content = build_profile_suggest_prompt(req)
    try:
        data, model = await call_gemini_structured(PROFILE_SUGGEST_SYSTEM_PROMPT, user_content)
    except QuotaExceedError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except LlmError as e:
        raise HTTPException(status_code=500, detail=str(e))

    suggestions = _parse_suggestions(data.get("suggestions", []))

    return ProfileSuggestionResponse(
        user_id=req.user_id,
        summary=data.get("summary", ""),
        suggestions=suggestions,
        model=model,
        generated_at=datetime.now(),
    )
