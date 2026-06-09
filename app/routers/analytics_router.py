# analytics router - cung cấp các endpoint phân tích dữ liệu cho chủ sân và quản lý
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
    StrategicSuggestionRequest,
    StrategicSuggestionResponse,
    StrategicInsight,
    BranchPerformance,
    StaffingRecommendation,
    DemandForecast,
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
    STRATEGIC_SUGGEST_SYSTEM_PROMPT,
    build_strategic_suggest_prompt,
)
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/ai/analytics", tags=["AI — Analytics Insights"])


def _parse_insights(raw: list) -> list[InsightItem]:
    """
    parse danh sách insight trả về từ llm thành list InsightItem
    """
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
    phân tích tổng hợp số liệu chi nhánh để đưa ra insight và khuyến nghị vận hành
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
    """
    phân tích doanh thu và đề xuất cải thiện
    """
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
    """
    phân tích tỉ lệ lấp đầy theo khung giờ để tối ưu lịch sân
    """
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
    """
    phân tích xu hướng hủy đặt sân và đề xuất phương án khắc phục
    """
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


def _parse_strategic_insights(raw: list) -> list[StrategicInsight]:
    items = []
    for item in raw:
        try:
            items.append(StrategicInsight(**item))
        except Exception:
            pass
    return items


def _parse_branch_performances(raw: list) -> list[BranchPerformance]:
    items = []
    for item in raw:
        try:
            items.append(BranchPerformance(**item))
        except Exception:
            pass
    return items


def _parse_staffing_recommendations(raw: list) -> list[StaffingRecommendation]:
    items = []
    for item in raw:
        try:
            items.append(StaffingRecommendation(**item))
        except Exception:
            pass
    return items


@router.post(
    "/strategic",
    response_model=StrategicSuggestionResponse,
    summary="Đề xuất chiến lược toàn hệ thống (Owner)",
)
async def analytics_strategic(req: StrategicSuggestionRequest):
    """
    so sánh hiệu suất giữa các chi nhánh để đưa ra phân tích chiến lược mở rộng và nhân sự
    """
    user_content = build_strategic_suggest_prompt(req)
    try:
        data, model = await call_gemini_structured(STRATEGIC_SUGGEST_SYSTEM_PROMPT, user_content)
    except QuotaExceedError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except LlmError as e:
        raise HTTPException(status_code=500, detail=str(e))

    insights = _parse_strategic_insights(data.get("insights", []))
    branch_performances = _parse_branch_performances(data.get("branch_performances", []))
    staffing_recommendations = _parse_staffing_recommendations(data.get("staffing_recommendations", []))
    
    demand_forecast = None
    df_raw = data.get("demand_forecast")
    if df_raw:
        try:
            demand_forecast = DemandForecast(**df_raw)
        except Exception:
            pass

    return StrategicSuggestionResponse(
        period=req.period,
        insights=insights,
        branch_performances=branch_performances,
        staffing_recommendations=staffing_recommendations,
        demand_forecast=demand_forecast,
        model=model,
        generated_at=datetime.now(),
    )

