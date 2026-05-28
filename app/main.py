import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime

from app.routers import analytics_router, chat_router, suggest_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('smashcourt_ai.log')
    ]
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("SmashCourt AI service started")
    logger.info(f"Environment: {_ENV}")
    logger.info(f"Swagger UI: http://localhost:8000/docs")
    yield
    logger.info("SmashCourt AI service shutting down")


_ENV = os.getenv("APP_ENV", "development")
_VERSION = "1.0.0"
_docs_url = "/docs" if _ENV == "development" else None
_redoc_url = "/redoc" if _ENV == "development" else None

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
    version=_VERSION,
    lifespan=lifespan,
    docs_url=_docs_url,
    redoc_url=_redoc_url,
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


# ─── Health check ─────────────────────────────────────────────────────────────
@app.get("/health", tags=["system"])
async def health_check():
    """
    Health check endpoint với thông tin chi tiết
    Dùng để verify service đang chạy và môi trường deployment
    """
    return {
        "status": "ok",
        "service": "SmashCourt AI Service",
        "version": _VERSION,
        "environment": _ENV,
        "timestamp": datetime.now().isoformat()
    }
