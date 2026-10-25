# SmashCourt-AI — AI Service (LLM Gateway)

FastAPI (Python 3.12) + `google-genai` (Gemini). Cung cấp chatbot, gợi ý đặt sân/giá/khuyến mãi, phân tích doanh thu cho SmashCourt.
**Chỉ SmashCourt-BE được gọi service này** (FE không gọi trực tiếp). Không có database. Thuộc workspace 4 repo — xem `../CLAUDE.md`.

## Lệnh (Windows, venv tại `.venv/`)
```bash
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000    # Swagger /docs khi APP_ENV=development
.venv/Scripts/python.exe -m compileall -q app                            # kiểm tra cú pháp nhanh
.venv/Scripts/python.exe -m ruff check .                                # = CI (ruff 0.16.9 đã cài trong .venv; bộ luật ở ruff.toml)
```
CI (`.github/workflows/ci.yml`): `ruff check .` (ruff ghim `0.16.9`, luật khai báo tường minh ở `ruff.toml`) + `compileall` → build Docker image. Đổi phiên bản ruff hoặc thêm luật phải sửa cả `ci.yml` và `ruff.toml`, chạy lint trước. Chưa có test tự động.

## Kiến trúc (chi tiết: skill `smashcourt-ai-architecture`)
```
app/main.py                  → FastAPI app, CORS, logging (smashcourt_ai.log), include_router(prefix="/api/v1"), GET /health
app/routers/chat_router.py      → /api/v1/ai/chat, /faq, /faq-reply
app/routers/suggest_router.py   → /api/v1/ai/suggest/booking | profile | pricing | promotions | ...
app/routers/analytics_router.py → /api/v1/ai/analytics/...
app/models/ai_schemas.py     → toàn bộ Pydantic schema: {X}Request, {X}Response(AiBaseResponse)
app/services/llm_service.py  → call_gemini_structured / call_gemini_text, QuotaExceedError(→503), LlmError(→500)
app/services/prompt_builder.py → {X}_SYSTEM_PROMPT + build_{x}_prompt(req)
```

## Điểm cần nhớ
- Field schema **snake_case** (BE gửi/nhận bằng `JsonNamingPolicy.SnakeCaseLower`). Response kế thừa `AiBaseResponse` (`model`, `generated_at`).
- Mọi lời gọi Gemini đi qua `llm_service`; prompt nằm ở `prompt_builder`.
- Đổi schema/endpoint ⇒ sửa đồng bộ `SmashCourt-BE/Integrations/AI/DTOs/*` và các service AI của BE.
- Cấu hình qua env: `GEMINI_API_KEY`, `GEMINI_MODEL`, `APP_ENV`. Không đọc/in/sửa `.env`.
- Package mới → `requirements.txt` với version pin `==`.

## Quy tắc làm việc
- **Không tự ý `git commit` / `push` / `merge` / `rebase` / `reset`** — chỉ khi người dùng yêu cầu rõ ràng (xem `../.claude/rules/git-safety.md`).
- Sửa code xong **phải** chạy `compileall` và `ruff check .` rồi sửa hết lỗi trước khi báo xong (skill `build-verify`).
- Endpoint/schema/prompt mới theo skill `smashcourt-ai-architecture`.
