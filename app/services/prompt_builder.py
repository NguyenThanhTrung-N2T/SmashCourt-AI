"""
Prompt Builder — Build system prompt và user prompt theo từng use case
"""
from app.models.ai_schemas import (
    AnalyticsRequest,
    BookingSuggestionRequest,
    CancellationRequest,
    OccupancyRequest,
    ProfileSuggestionRequest,
    RevenueRequest,
)

# ─── System Prompts ──────────────────────────────────────────────────────────

CHATBOT_SYSTEM_PROMPT = """Bạn là trợ lý AI của SmashCourt — hệ thống đặt sân cầu lông và pickleball.
Nhiệm vụ của bạn là hỗ trợ khách hàng một cách thân thiện, ngắn gọn và chính xác.

Quy tắc:
- Trả lời bằng tiếng Việt, ngắn gọn (tối đa 150 từ)
- Chỉ trả lời các câu hỏi liên quan đến đặt sân, lịch sân, giá cả, chính sách hủy, khuyến mãi
- Nếu không biết thông tin cụ thể, hướng dẫn khách liên hệ chi nhánh
- Cuối câu trả lời, gợi ý 2-3 hành động tiếp theo ngắn gọn

Format trả về (JSON):
{
  "reply": "nội dung trả lời",
  "suggestions": ["hành động 1", "hành động 2", "hành động 3"]
}
"""

FAQ_SYSTEM_PROMPT = """Bạn là trợ lý AI của SmashCourt. Hãy trả lời câu hỏi thường gặp một cách rõ ràng, đầy đủ nhưng ngắn gọn.
Trả lời bằng tiếng Việt. Tối đa 200 từ. Không cần gợi ý hành động.
Chỉ trả về nội dung văn bản thuần (plain text), không JSON.
"""

BOOKING_SUGGEST_SYSTEM_PROMPT = """Bạn là AI phân tích hành vi đặt sân của SmashCourt.
Dựa vào lịch sử đặt sân của khách hàng, hãy đưa ra 2-4 gợi ý cá nhân hóa ngắn gọn, thực tế.

Quy tắc:
- Trả lời bằng tiếng Việt
- Gợi ý phải dựa trên pattern thực từ lịch sử (giờ hay đặt, loại sân, chi nhánh)
- Mỗi gợi ý ngắn gọn, có title và mô tả
- Luôn trả về JSON hợp lệ

Format trả về:
{
  "suggestions": [
    {
      "type": "time_slot|court_type|branch|promotion",
      "title": "tiêu đề ngắn",
      "description": "mô tả 1-2 câu",
      "action": "label CTA hoặc null"
    }
  ]
}
"""

PROFILE_SUGGEST_SYSTEM_PROMPT = """Bạn là AI phân tích hành vi của SmashCourt. Phân tích lịch sử đặt sân và đưa ra:
1. Tóm tắt ngắn về thói quen chơi thể thao của người dùng (1-2 câu)
2. 3-4 gợi ý cá nhân hóa theo hành vi

Quy tắc:
- Trả lời bằng tiếng Việt, thân thiện
- Luôn trả về JSON hợp lệ

Format trả về:
{
  "summary": "Tóm tắt thói quen...",
  "suggestions": [
    {
      "type": "time_slot|court_type|branch|loyalty",
      "title": "tiêu đề",
      "description": "mô tả",
      "action": "label CTA hoặc null"
    }
  ]
}
"""

ANALYTICS_SYSTEM_PROMPT = """Bạn là chuyên gia phân tích kinh doanh của SmashCourt. 
Phân tích các số liệu và đưa ra insight + khuyến nghị cụ thể cho chủ hệ thống / quản lý chi nhánh.

Quy tắc:
- Trả lời bằng tiếng Việt, chuyên nghiệp
- Mỗi insight phải có severity: "info" | "warning" | "critical" | "positive"
- Khuyến nghị phải thực tế và có thể thực hiện ngay (manual, không tự động)
- Đưa ra 3-5 insight
- Luôn trả về JSON hợp lệ

Format trả về:
{
  "insights": [
    {
      "category": "revenue|occupancy|cancellation|promotion",
      "severity": "info|warning|critical|positive",
      "title": "tiêu đề ngắn",
      "description": "mô tả 2-3 câu với số liệu cụ thể",
      "recommendation": "hành động đề xuất hoặc null"
    }
  ]
}
"""


# ─── User Prompt Builders ────────────────────────────────────────────────────

def build_chat_prompt(message: str, context: str | None) -> str:
    if context:
        return f"Context bổ sung: {context}\n\nCâu hỏi khách hàng: {message}"
    return f"Câu hỏi khách hàng: {message}"


def build_faq_prompt(question: str) -> str:
    return f"Câu hỏi: {question}"


def build_booking_suggest_prompt(req: BookingSuggestionRequest) -> str:
    name = req.user_name or "Khách hàng"
    history_lines = []
    for b in req.booking_history[-10:]:  # Chỉ lấy 10 booking gần nhất
        history_lines.append(
            f"  - Ngày {b.booking_date} | {b.branch_name} | {b.court_type} | "
            f"Giờ: {', '.join(b.time_slots)} | Trạng thái: {b.status} | "
            f"Tổng: {b.total_amount:,.0f} VNĐ"
        )
    history_text = "\n".join(history_lines) if history_lines else "  (Chưa có lịch sử đặt sân)"
    branch_ctx = f"\nChi nhánh hiện tại: {req.current_branch_name}" if req.current_branch_name else ""

    return f"""Khách hàng: {name}
Lịch sử đặt sân gần đây:
{history_text}{branch_ctx}

Hãy phân tích và đưa ra gợi ý phù hợp.
"""


def build_profile_suggest_prompt(req: ProfileSuggestionRequest) -> str:
    name = req.user_name or "Khách hàng"
    history_lines = []
    for b in req.booking_history[-15:]:
        history_lines.append(
            f"  - Ngày {b.booking_date} | {b.branch_name} | {b.court_type} | "
            f"Giờ: {', '.join(b.time_slots)} | {b.status}"
        )
    history_text = "\n".join(history_lines) if history_lines else "  (Chưa có lịch sử)"
    loyalty = f"\nHạng thành viên: {req.loyalty_tier} | Điểm tích lũy: {req.loyalty_points:,}" if req.loyalty_tier else ""

    return f"""Khách hàng: {name}{loyalty}
Lịch sử đặt sân:
{history_text}

Hãy phân tích hành vi và đưa ra gợi ý cá nhân hóa cho trang cá nhân.
"""


def build_analytics_summary_prompt(req: AnalyticsRequest) -> str:
    m = req.metrics
    revenue_lines = "\n".join(
        f"    + {r.court_type}: {r.revenue:,.0f} VNĐ" for r in m.revenue_by_court_type
    )
    promo_lines = "\n".join(
        f"    + {p.name}: {p.usage_count} lượt dùng" for p in m.top_promotions
    )
    prev_ctx = ""
    if req.prev_metrics:
        pm = req.prev_metrics
        prev_ctx = f"""
Kỳ trước ({req.prev_period}):
  - Doanh thu: {pm.total_revenue:,.0f} VNĐ
  - Tổng booking: {pm.total_bookings}
  - Tỉ lệ hủy: {pm.cancellation_rate:.1%}
  - Tỉ lệ lấp đầy TB: {pm.avg_occupancy_rate:.1%}"""

    return f"""Báo cáo chi nhánh: {req.branch_name}
Kỳ: {req.period}

Số liệu:
  - Doanh thu: {m.total_revenue:,.0f} VNĐ
  - Tổng booking: {m.total_bookings}
  - Booking bị hủy: {m.cancelled_bookings} ({m.cancellation_rate:.1%})
  - Tỉ lệ lấp đầy TB: {m.avg_occupancy_rate:.1%}
  - Giờ cao điểm: {', '.join(m.peak_hours)}
  - Giờ thấp điểm: {', '.join(m.low_hours)}
  - Doanh thu theo loại sân:
{revenue_lines if revenue_lines else "    (không có)"}
  - Khuyến mãi nổi bật:
{promo_lines if promo_lines else "    (không có)"}{prev_ctx}

Hãy phân tích và đưa ra các insight + khuyến nghị.
"""


def build_revenue_prompt(req: RevenueRequest) -> str:
    prev = f"\n  - Doanh thu kỳ trước: {req.prev_total_revenue:,.0f} VNĐ" if req.prev_total_revenue else ""
    by_type = "\n".join(f"    + {r.court_type}: {r.revenue:,.0f} VNĐ" for r in req.revenue_by_court_type)
    return f"""Phân tích doanh thu chi nhánh: {req.branch_name}
Kỳ: {req.period}
  - Doanh thu: {req.total_revenue:,.0f} VNĐ{prev}
  - Theo loại sân:
{by_type if by_type else "    (không có)"}

Hãy phân tích insight về doanh thu.
"""


def build_occupancy_prompt(req: OccupancyRequest) -> str:
    by_hour = "\n".join(f"    + {h}: {v:.0%}" for h, v in req.occupancy_by_hour.items())
    return f"""Phân tích tỉ lệ lấp đầy — {req.branch_name} | Kỳ: {req.period}
  - Tỉ lệ TB: {req.avg_occupancy_rate:.1%}
  - Giờ cao điểm: {', '.join(req.peak_hours)}
  - Giờ thấp điểm: {', '.join(req.low_hours)}
  - Chi tiết theo giờ:
{by_hour if by_hour else "    (không có)"}

Hãy phân tích và đưa ra gợi ý tối ưu tỉ lệ lấp đầy.
"""


def build_cancellation_prompt(req: CancellationRequest) -> str:
    reasons = "\n".join(f"    + {r}: {c} lần" for r, c in req.cancel_reasons.items())
    return f"""Phân tích hủy booking — {req.branch_name} | Kỳ: {req.period}
  - Tổng booking: {req.total_bookings}
  - Số hủy: {req.cancelled_bookings} ({req.cancellation_rate:.1%})
  - Lý do hủy:
{reasons if reasons else "    (không phân loại)"}

Hãy phân tích xu hướng hủy và đưa ra gợi ý giảm tỉ lệ hủy.
"""
