# SmashCourt AI Service

LLM gateway service của hệ thống SmashCourt, xây dựng bằng **FastAPI**. Service này nhận request, gọi **Gemini API** và trả về response — không chứa model ML.

## Tech Stack

- [FastAPI](https://fastapi.tiangolo.com/)
- [Uvicorn](https://www.uvicorn.org/) – ASGI server
- [google-generativeai](https://pypi.org/project/google-generativeai/) – Gemini SDK
- Python 3.12

## Cấu trúc thư mục

```
app/
├── main.py          # FastAPI app, CORS, routing
├── routers/
│   └── chat.py      # POST /api/v1/chat
├── models/
│   └── schemas.py   # Pydantic request/response models
└── services/
    └── llm_service.py  # Logic gọi Gemini API
```

## Cài đặt & Chạy local

```bash
# Tạo virtual environment
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate  # Linux/macOS

# Cài dependencies
pip install -r requirements.txt

# Copy env và điền API key
cp .env.example .env

# Chạy dev server
uvicorn app.main:app --reload
```

Mở [http://localhost:8000/docs](http://localhost:8000/docs) để xem Swagger UI.

## Chạy bằng Docker

```bash
docker build -t smashcourt-ai .
docker run -p 8000:8000 --env-file .env smashcourt-ai
```

## API Endpoints

| Method | Path | Mô tả |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/api/v1/chat` | Gửi message → Gemini → nhận reply |

**Request body (`/api/v1/chat`):**
```json
{
  "message": "Câu hỏi của bạn",
  "context": "Ngữ cảnh thêm (tuỳ chọn)"
}
```

## Environment Variables

| Variable | Mô tả |
|---|---|
| `GEMINI_API_KEY` | Google Gemini API key |
| `GEMINI_MODEL` | Model name (mặc định: `gemini-2.0-flash`) |
