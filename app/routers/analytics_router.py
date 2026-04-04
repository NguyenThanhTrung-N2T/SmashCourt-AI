"""
Analytics Router — Owner / Manager analytics insight endpoints
  POST /api/v1/ai/analytics/summary      — Tổng hợp toàn diện
  POST /api/v1/ai/analytics/revenue      — Phân tích doanh thu
  POST /api/v1/ai/analytics/occupancy    — Phân tích tỉ lệ lấp đầy
  POST /api/v1/ai/analytics/cancellation — Phân tích hủy booking
"""
from datetime import datetime

from app.models.ai_schemas import (
    AnalyticsRequest,
    AnalyticsSummaryResponse,
    CancellationRequest,
    CancellationResponse,
    InsightItem,
    OccupancyRequest,
    OccupancyResponse,
    RevenueRequest,
    RevenueResponse,
)
from app.services.llm_service import (
    LlmError,
    QuotaExceedError,
    call_gemini_structured,
)
from app.services.prompt_builder import (
    ANALYTICS_SYSTEM_PROMPT,
    build_analytics_summary_prompt,
    build_cancellation_prompt,
    build_occupancy_prompt,
    build_revenue_prompt,
)
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/ai/analytics", tags=["AI — Analytics Insights"])


def _parse_insights(raw: list) -> list[InsightItem]:
    """Parse list dict từ LLM thành list InsightItem, bỏ qua item lỗi."""
    items = []
    for item in raw:
        try:
            items.append(InsightItem(**item))
        except Exception:
            pass
    return items


@router.post(
    "/summary",
    response_model=AnalyticsSummaryResponse,
    summary="Tổng hợp gợi ý từ toàn bộ số liệu",
)
async def analytics_summary(req: AnalyticsRequest):
    """
    Nhận đầy đủ số liệu của một chi nhánh trong một kỳ,
    trả về tổng hợp insight + khuyến nghị cho chủ hệ thống / quản lý.
    """
    user_content = build_analytics_summary_prompt(req)
    try:
        data, model = await call_gemini_structured(ANALYTICS_SYSTEM_PROMPT, user_content)
    except QuotaExceedError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except LlmError as e:
        raise HTTPException(status_code=500, detail=str(e))

    insights = _parse_insights(data.get("insights", []))

    return AnalyticsSummaryResponse(
        branch_id=req.branch_id,
        branch_name=req.branch_name,
        period=req.period,
        insights=insights,
        model=model,
        generated_at=datetime.now(),
    )


@router.post(
    "/revenue",
    response_model=RevenueResponse,
    summary="Phân tích insight doanh thu",
)
async def analytics_revenue(req: RevenueRequest):
    """Nhận số liệu doanh thu, trả về insight và khuyến nghị liên quan đến doanh thu."""
    user_content = build_revenue_prompt(req)
    try:
        data, model = await call_gemini_structured(ANALYTICS_SYSTEM_PROMPT, user_content)
    except QuotaExceedError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except LlmError as e:
        raise HTTPException(status_code=500, detail=str(e))

    insights = _parse_insights(data.get("insights", []))

    return RevenueResponse(
        branch_id=req.branch_id,
        period=req.period,
        insights=insights,
        model=model,
        generated_at=datetime.now(),
    )


@router.post(
    "/occupancy",
    response_model=OccupancyResponse,
    summary="Phân tích tỉ lệ lấp đầy sân",
)
async def analytics_occupancy(req: OccupancyRequest):
    """Nhận số liệu lấp đầy theo giờ, trả về gợi ý tối ưu lịch sân."""
    user_content = build_occupancy_prompt(req)
    try:
        data, model = await call_gemini_structured(ANALYTICS_SYSTEM_PROMPT, user_content)
    except QuotaExceedError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except LlmError as e:
        raise HTTPException(status_code=500, detail=str(e))

    insights = _parse_insights(data.get("insights", []))

    return OccupancyResponse(
        branch_id=req.branch_id,
        period=req.period,
        insights=insights,
        model=model,
        generated_at=datetime.now(),
    )


@router.post(
    "/cancellation",
    response_model=CancellationResponse,
    summary="Phân tích xu hướng hủy booking",
)
async def analytics_cancellation(req: CancellationRequest):
    """Nhận số liệu hủy booking, phân tích xu hướng và đề xuất biện pháp giảm hủy."""
    user_content = build_cancellation_prompt(req)
    try:
        data, model = await call_gemini_structured(ANALYTICS_SYSTEM_PROMPT, user_content)
    except QuotaExceedError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except LlmError as e:
        raise HTTPException(status_code=500, detail=str(e))

    insights = _parse_insights(data.get("insights", []))

    return CancellationResponse(
        branch_id=req.branch_id,
        period=req.period,
        insights=insights,
        model=model,
        generated_at=datetime.now(),
    )
