# SmashCourt AI Service

LLM gateway service của hệ thống SmashCourt, xây dựng bằng **FastAPI**. Service này nhận request từ **BE**, gọi **Gemini API** và trả về response — BE là proxy, FE không gọi trực tiếp.

## Tech Stack

- [FastAPI](https://fastapi.tiangolo.com/)
- [Uvicorn](https://www.uvicorn.org/) – ASGI server
- [google-genai](https://pypi.org/project/google-genai/) – Gemini SDK
- Python 3.12

## Cấu trúc thư mục

```
app/
├── main.py                  # FastAPI app, CORS, routing
├── routers/
│   ├── chat_router.py       # /api/v1/ai/chat
│   ├── suggest_router.py    # /api/v1/ai/suggest
│   └── analytics_router.py  # /api/v1/ai/analytics
├── models/
│   ├── schemas.py           # Schema cũ (chat đơn giản)
│   └── ai_schemas.py        # Pydantic schemas cho 3 nhóm tính năng
└── services/
    ├── llm_service.py       # Logic gọi Gemini API
    └── prompt_builder.py    # Xây dựng system prompt & user prompt
```

## Cài đặt & Chạy local

```bash
# Tạo virtual environment
python -m venv .venv
.venv\Scripts\activate   # Windows

# Cài dependencies
pip install -r requirements.txt

# Copy env và điền API key
cp .env.example .env
```

Điền API key vào `.env`:

```env
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.5-flash
APP_ENV=development
```

Chạy dev server:

```powershell
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Swagger UI (chỉ bật khi `APP_ENV=development`): [http://localhost:8000/docs](http://localhost:8000/docs)

## Chạy bằng Docker

```bash
docker build -t smashcourt-ai .
docker run -p 8000:8000 --env-file .env smashcourt-ai
```

## API Endpoints

### 🤖 Chatbot (khách hàng)

| Method | Path                       | Mô tả                         |
| ------ | -------------------------- | ----------------------------- |
| `POST` | `/api/v1/ai/chat`          | Chat tự do với AI             |
| `GET`  | `/api/v1/ai/chat/faq`      | Danh sách câu hỏi gợi ý (FAQ) |
| `POST` | `/api/v1/ai/chat/faq-reply`| Trả lời một câu hỏi FAQ       |

### 👤 Gợi ý cá nhân (khách hàng)

| Method | Path                        | Mô tả                              |
| ------ | --------------------------- | ---------------------------------- |
| `POST` | `/api/v1/ai/suggest/booking`| Gợi ý sân/giờ khi đặt sân          |
| `POST` | `/api/v1/ai/suggest/profile`| Gợi ý hiển thị trên trang cá nhân  |

### 📊 Analytics (chủ hệ thống / quản lý)

| Method | Path                              | Mô tả                          |
| ------ | --------------------------------- | ------------------------------ |
| `POST` | `/api/v1/ai/analytics/summary`    | Tổng hợp insight toàn chi nhánh|
| `POST` | `/api/v1/ai/analytics/revenue`    | Phân tích doanh thu            |
| `POST` | `/api/v1/ai/analytics/occupancy`  | Phân tích tỉ lệ lấp đầy        |
| `POST` | `/api/v1/ai/analytics/cancellation`| Phân tích hủy booking         |

### System

| Method | Path      | Mô tả        |
| ------ | --------- | ------------ |
| `GET`  | `/health` | Health check |

## Environment Variables

| Variable         | Mô tả                                      |
| ---------------- | ------------------------------------------ |
| `GEMINI_API_KEY` | Google Gemini API key (lấy tại [aistudio.google.com](https://aistudio.google.com/apikey)) |
| `GEMINI_MODEL`   | Model name (khuyến nghị: `gemini-2.5-flash`) |
| `APP_ENV`        | `development` (bật Swagger) hoặc `production` (tắt Swagger) |
