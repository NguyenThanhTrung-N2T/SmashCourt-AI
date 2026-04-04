from contextlib import asynccontextmanager

from app.routers import analytics_router, chat_router, suggest_router, weather
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("SmashCourt AI service started.")
    print("Swagger UI: http://localhost:8000/docs")
    yield
    print("SmashCourt AI service shutting down.")


app = FastAPI(
    title="SmashCourt AI Service",
    description=(
        "LLM Gateway cho hệ thống SmashCourt.\n\n"
        "**3 nhóm tính năng:**\n"
        "- 🤖 **Chatbot** (`/ai/chat`): Hỗ trợ khách hàng tự do + FAQ\n"
        "- 👤 **Gợi ý cá nhân** (`/ai/suggest`): Từ lịch sử booking của khách\n"
        "- 📊 **Analytics** (`/ai/analytics`): Insight cho chủ/quản lý chi nhánh\n\n"
        "> Tất cả caller phải là **BE** (không gọi thẳng từ FE)."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # TODO: restrict to BE origin in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ──────────────────────────────────────────────────────────────────
PREFIX = "/api/v1"

app.include_router(chat_router.router,      prefix=PREFIX)
app.include_router(suggest_router.router,   prefix=PREFIX)
app.include_router(analytics_router.router, prefix=PREFIX)
app.include_router(weather.router,          prefix=PREFIX, tags=["weather"])


# ─── Health check ─────────────────────────────────────────────────────────────
@app.get("/health", tags=["system"])
async def health_check():
    return {"status": "ok", "service": "SmashCourt AI Service"}
