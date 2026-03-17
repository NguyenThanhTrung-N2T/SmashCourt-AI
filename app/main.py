from app.routers import chat
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("SmashCourt AI service started.")
    yield
    # Shutdown
    print("SmashCourt AI service shutting down.")


app = FastAPI(
    title="SmashCourt AI Service",
    description="LLM gateway service powered by Gemini",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api/v1", tags=["chat"])


@app.get("/health")
async def health_check():
    return {"status": "ok"}
