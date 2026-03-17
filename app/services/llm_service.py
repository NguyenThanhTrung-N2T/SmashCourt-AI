import os

from dotenv import load_dotenv
from google import genai

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

_client = genai.Client(api_key=GEMINI_API_KEY)


async def call_gemini(message: str, context: str | None = None) -> tuple[str, str]:
    """
    Send a message to Gemini and return (reply_text, model_name).
    """
    prompt = message
    if context:
        prompt = f"Context:\n{context}\n\nUser message:\n{message}"

    response = await _client.aio.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    )
    return response.text, GEMINI_MODEL
