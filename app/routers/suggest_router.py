# suggest router - cung cấp các gợi ý cá nhân hóa và gợi ý chiến lược
import logging
from datetime import datetime

from app.models.ai_schemas import (
    BookingSuggestionRequest,
    BookingSuggestionResponse,
    ProfileSuggestionRequest,
    ProfileSuggestionResponse,
    SuggestionItem,
    PricingSuggestionRequest,
    PricingSuggestionResponse,
    PricingInsight,
    PromotionSuggestionRequest,
    PromotionSuggestionResponse,
    PromotionInsight,
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
    PRICING_SUGGEST_SYSTEM_PROMPT,
    PROMOTION_SUGGEST_SYSTEM_PROMPT,
    build_pricing_suggest_prompt,
    build_promotion_suggest_prompt,
)
from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai/suggest", tags=["AI — Personal Suggestions"])


def _parse_suggestions(raw: list[dict]) -> list[SuggestionItem]:
    """
    parse danh sách dictionary trả về từ llm thành list SuggestionItem
    """
    items: list[SuggestionItem] = []
    for s in raw:
        try:
            items.append(SuggestionItem(**s))
        except (TypeError, ValueError) as e:
            logger.warning(f"Failed to parse suggestion item: {e}")
    return items


@router.post("/booking", response_model=BookingSuggestionResponse, summary="Gợi ý sân/giờ khi đặt sân")
async def suggest_booking(req: BookingSuggestionRequest):
    """
    phân tích lịch sử booking và gợi ý sân hoặc giờ chơi phù hợp khi đang đặt sân
    """
    logger.info(f"Booking suggestion request: user_id={req.user_id}, history_count={len(req.booking_history)}")
    
    if not req.booking_history:
        logger.info(f"No booking history for user {req.user_id}, returning default suggestions")
        # trả về gợi ý mặc định nếu chưa có lịch sử booking
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
        logger.info(f"Booking suggestions generated: user_id={req.user_id}, model={model}, count={len(data.get('suggestions', []))}")
    except QuotaExceedError as e:
        logger.error(f"Gemini quota exceeded for booking suggestion: user_id={req.user_id}, error={e}")
        raise HTTPException(status_code=503, detail=str(e))
    except LlmError as e:
        logger.error(f"LLM error in booking suggestion: user_id={req.user_id}, error={e}")
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
    phân tích lịch sử booking và tích lũy điểm để hiển thị trên trang cá nhân
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


def _parse_pricing_insights(raw: list) -> list[PricingInsight]:
    items = []
    for item in raw:
        try:
            items.append(PricingInsight(**item))
        except Exception:
            pass
    return items


def _parse_promotion_insights(raw: list) -> list[PromotionInsight]:
    items = []
    for item in raw:
        try:
            items.append(PromotionInsight(**item))
        except Exception:
            pass
    return items


@router.post("/pricing", response_model=PricingSuggestionResponse, summary="Gợi ý điều chỉnh giá động")
async def suggest_pricing(req: PricingSuggestionRequest):
    """
    phân tích tỉ lệ lấp đầy và doanh thu để gợi ý thay đổi giá theo khung giờ
    """
    user_content = build_pricing_suggest_prompt(req)
    try:
        data, model = await call_gemini_structured(PRICING_SUGGEST_SYSTEM_PROMPT, user_content)
    except QuotaExceedError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except LlmError as e:
        raise HTTPException(status_code=500, detail=str(e))

    insights = _parse_pricing_insights(data.get("insights", []))

    return PricingSuggestionResponse(
        branch_id=req.branch_id or "all",
        period=req.period,
        insights=insights,
        model=model,
        generated_at=datetime.now()
    )


@router.post("/promotions", response_model=PromotionSuggestionResponse, summary="Gợi ý khuyến mãi giờ thấp điểm")
async def suggest_promotions(req: PromotionSuggestionRequest):
    """
    phân tích tỉ lệ lấp đầy để đề xuất khuyến mãi cho khung giờ vắng khách
    """
    user_content = build_promotion_suggest_prompt(req)
    try:
        data, model = await call_gemini_structured(PROMOTION_SUGGEST_SYSTEM_PROMPT, user_content)
    except QuotaExceedError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except LlmError as e:
        raise HTTPException(status_code=500, detail=str(e))

    insights = _parse_promotion_insights(data.get("insights", []))

    return PromotionSuggestionResponse(
        branch_id=req.branch_id or "all",
        period=req.period,
        insights=insights,
        model=model,
        generated_at=datetime.now()
    )

