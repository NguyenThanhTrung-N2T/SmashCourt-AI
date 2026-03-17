from app.models.schemas import ChatRequest, ChatResponse
from app.services.llm_service import call_gemini
from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Receives a user message, forwards it to Gemini, and returns the response.
    """
    try:
        reply, model_name = await call_gemini(request.message, request.context)
        return ChatResponse(reply=reply, model=model_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
