import os

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

genai.configure(api_key=GEMINI_API_KEY)


async def call_gemini(message: str, context: str | None = None) -> tuple[str, str]:
    """
    Send a message to Gemini and return (reply_text, model_name).
    """
    model = genai.GenerativeModel(GEMINI_MODEL)

    prompt = message
    if context:
        prompt = f"Context:\n{context}\n\nUser message:\n{message}"

    response = model.generate_content(prompt)
    return response.text, GEMINI_MODEL
