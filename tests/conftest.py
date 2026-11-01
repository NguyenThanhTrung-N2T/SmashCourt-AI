# LLM giả cho test (Epic 6C, gói 6C-1, AI-UT): thay client Gemini của llm_service, không bao giờ gọi Google thật
from collections.abc import Iterator
from types import SimpleNamespace

import pytest
from app.main import app
from app.services import llm_service
from fastapi.testclient import TestClient


class FakeLlm:
    """
    giả lập genai.Client: chỉ có aio.models.generate_content (đường duy nhất llm_service dùng);
    ghi lại từng lời gọi, trả lần lượt các response đã đặt hoặc ném lỗi đã đặt
    """

    def __init__(self) -> None:
        self.calls: list[dict] = []
        self._outcomes: list[SimpleNamespace | Exception] = []
        self.aio = SimpleNamespace(models=SimpleNamespace(generate_content=self._generate_content))

    def reply(self, *texts: str) -> "FakeLlm":
        self._outcomes.extend(SimpleNamespace(text=text) for text in texts)
        return self

    def reply_with_usage(self, text: str, prompt_tokens: int, output_tokens: int) -> "FakeLlm":
        # response kèm usage_metadata như Gemini thật (số token vào/ra) cho test metric OB-AI-1
        usage = SimpleNamespace(prompt_token_count=prompt_tokens, candidates_token_count=output_tokens)
        self._outcomes.append(SimpleNamespace(text=text, usage_metadata=usage))
        return self

    def fail(self, error: Exception) -> "FakeLlm":
        self._outcomes.append(error)
        return self

    async def _generate_content(self, *, model: str, contents: str, config=None):
        self.calls.append({"model": model, "contents": contents, "config": config})
        if not self._outcomes:
            raise AssertionError("LLM giả được gọi nhưng test chưa đặt response (reply/fail)")
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


@pytest.fixture(autouse=True)
def fake_llm(monkeypatch: pytest.MonkeyPatch) -> FakeLlm:
    # Áp cho MỌI test: kể cả khi .env có khóa thật, không lời gọi nào ra tới Gemini
    fake = FakeLlm()
    monkeypatch.setattr(llm_service, "_client", fake)
    return fake


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
