"""
AI Schemas — Pydantic models cho 3 nhóm tính năng AI của SmashCourt
"""
from datetime import datetime
from pydantic import BaseModel, Field


# ─── Common ──────────────────────────────────────────────────────────────────

class AiBaseResponse(BaseModel):
    model: str
    generated_at: datetime = Field(default_factory=datetime.now)


# ─── Group 1: Customer Chatbot ────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    context: str | None = None
    session_id: str | None = None
    user_id: str | None = None


class ChatResponse(AiBaseResponse):
    reply: str
    suggestions: list[str] = []
    session_id: str | None = None


class FaqItem(BaseModel):
    id: str
    question: str
    category: str


class FaqListResponse(BaseModel):
    items: list[FaqItem]
    total: int


class FaqReplyRequest(BaseModel):
    faq_id: str
    question: str
    user_id: str | None = None


class FaqReplyResponse(AiBaseResponse):
    faq_id: str
    question: str
    reply: str


# ─── Group 2: Personal Suggestions ───────────────────────────────────────────

class BookingHistoryItem(BaseModel):
    booking_date: str                 # "2025-03-20"
    branch_name: str
    court_type: str
    time_slots: list[str]             # ["08:00-09:00", "09:00-10:00"]
    status: str                       # CONFIRMED / CANCELLED / PENDING
    total_amount: float


class BookingSuggestionRequest(BaseModel):
    user_id: str
    user_name: str | None = None
    booking_history: list[BookingHistoryItem]
    current_branch_id: str | None = None
    current_branch_name: str | None = None


class SuggestionItem(BaseModel):
    type: str                          # "time_slot" | "court_type" | "branch" | "promotion"
    title: str
    description: str
    action: str | None = None          # label cho CTA button, None = chỉ thông tin


class BookingSuggestionResponse(AiBaseResponse):
    user_id: str
    suggestions: list[SuggestionItem]


class ProfileSuggestionRequest(BaseModel):
    user_id: str
    user_name: str | None = None
    booking_history: list[BookingHistoryItem]
    loyalty_points: int = 0
    loyalty_tier: str | None = None   # "Silver" / "Gold" / "Platinum"


class ProfileSuggestionResponse(AiBaseResponse):
    user_id: str
    summary: str                       # Tóm tắt hành vi người dùng
    suggestions: list[SuggestionItem]


# ─── Group 3: Owner / Manager Analytics ──────────────────────────────────────

class RevenueByType(BaseModel):
    court_type: str
    revenue: float


class TopPromotion(BaseModel):
    name: str
    usage_count: int


class AnalyticsMetrics(BaseModel):
    total_revenue: float
    total_bookings: int
    cancelled_bookings: int
    cancellation_rate: float           # 0.0 – 1.0
    avg_occupancy_rate: float          # 0.0 – 1.0
    peak_hours: list[str]
    low_hours: list[str]
    revenue_by_court_type: list[RevenueByType] = []
    top_promotions: list[TopPromotion] = []


class AnalyticsRequest(BaseModel):
    branch_id: str
    branch_name: str
    period: str                        # "2025-03" hoặc "2025-Q1"
    metrics: AnalyticsMetrics
    # Optional: so sánh kỳ trước
    prev_period: str | None = None
    prev_metrics: AnalyticsMetrics | None = None


class InsightItem(BaseModel):
    category: str                     # "revenue" | "occupancy" | "cancellation" | "promotion"
    severity: str                     # "info" | "warning" | "critical" | "positive"
    title: str
    description: str
    recommendation: str | None = None


class AnalyticsSummaryResponse(AiBaseResponse):
    branch_id: str
    branch_name: str
    period: str
    insights: list[InsightItem]


# Revenue-only request (lighter payload)
class RevenueRequest(BaseModel):
    branch_id: str
    branch_name: str
    period: str
    total_revenue: float
    prev_total_revenue: float | None = None
    revenue_by_court_type: list[RevenueByType] = []
    revenue_by_day: dict[str, float] = {}  # {"2025-03-01": 1500000, ...}


class RevenueResponse(AiBaseResponse):
    branch_id: str
    period: str
    insights: list[InsightItem]


# Occupancy-only request
class OccupancyRequest(BaseModel):
    branch_id: str
    branch_name: str
    period: str
    avg_occupancy_rate: float
    peak_hours: list[str]
    low_hours: list[str]
    occupancy_by_hour: dict[str, float] = {}  # {"08:00": 0.35, ...}


class OccupancyResponse(AiBaseResponse):
    branch_id: str
    period: str
    insights: list[InsightItem]


# Cancellation-only request
class CancellationRequest(BaseModel):
    branch_id: str
    branch_name: str
    period: str
    total_bookings: int
    cancelled_bookings: int
    cancellation_rate: float
    cancel_reasons: dict[str, int] = {}   # {"customer_request": 10, "no_show": 5}
    cancel_by_day: dict[str, int] = {}    # {"2025-03-01": 2, ...}


class CancellationResponse(AiBaseResponse):
    branch_id: str
    period: str
    insights: list[InsightItem]
