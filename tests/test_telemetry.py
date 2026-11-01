# OB-AI-1 (Epic 6C, gói 6C-3a): metric lời gọi Gemini (độ trễ, kết quả, token) và bật/tắt OpenTelemetry
import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from app.services import llm_service, telemetry
from app.services.llm_service import LlmError, QuotaExceedError, call_gemini_structured, call_gemini_text
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader

pytestmark = pytest.mark.catalog("OB-AI-1")


@pytest.fixture
def reader(monkeypatch: pytest.MonkeyPatch) -> InMemoryMetricReader:
    # meter riêng của test (provider toàn cục chỉ đặt được một lần mỗi tiến trình)
    metric_reader = InMemoryMetricReader()
    provider = MeterProvider(metric_readers=[metric_reader])
    monkeypatch.setattr(llm_service, "gemini_metrics", telemetry.GeminiMetrics(provider.get_meter(telemetry.METER_NAME)))
    return metric_reader


def _points(reader: InMemoryMetricReader, name: str) -> list:
    data = reader.get_metrics_data()
    return [
        point
        for resource_metrics in data.resource_metrics
        for scope_metrics in resource_metrics.scope_metrics
        for metric in scope_metrics.metrics
        if metric.name == name
        for point in metric.data.data_points
    ]


def test_successful_call_records_duration_with_ok_outcome_and_operation(fake_llm, reader):
    fake_llm.reply("xin chào")

    asyncio.run(call_gemini_text("system", "user"))

    [point] = _points(reader, telemetry.GEMINI_DURATION)
    assert point.count == 1
    assert dict(point.attributes) == {
        "gemini.operation": "text",
        "gemini.model": llm_service.GEMINI_MODEL,
        "outcome": telemetry.OUTCOME_OK,
    }


def test_successful_call_counts_input_and_output_tokens(fake_llm, reader):
    fake_llm.reply_with_usage(json.dumps({"reply": "ok"}), prompt_tokens=120, output_tokens=30)

    asyncio.run(call_gemini_structured("system", "user"))

    tokens = {point.attributes["token.type"]: point.value for point in _points(reader, telemetry.GEMINI_TOKENS)}
    assert tokens == {"input": 120, "output": 30}


def test_response_without_usage_records_no_tokens(fake_llm, reader):
    fake_llm.reply("không có usage")

    asyncio.run(call_gemini_text("system", "user"))

    assert _points(reader, telemetry.GEMINI_TOKENS) == []


def test_quota_error_is_recorded_as_quota_outcome(fake_llm, reader):
    fake_llm.fail(Exception("429 RESOURCE_EXHAUSTED"))

    with pytest.raises(QuotaExceedError):
        asyncio.run(call_gemini_text("system", "user"))

    [point] = _points(reader, telemetry.GEMINI_DURATION)
    assert point.attributes["outcome"] == telemetry.OUTCOME_QUOTA


def test_other_error_is_recorded_as_error_outcome(fake_llm, reader):
    fake_llm.fail(Exception("mất kết nối"))

    with pytest.raises(LlmError):
        asyncio.run(call_gemini_structured("system", "user"))

    [point] = _points(reader, telemetry.GEMINI_DURATION)
    assert point.attributes == {
        "gemini.operation": "structured",
        "gemini.model": llm_service.GEMINI_MODEL,
        "outcome": telemetry.OUTCOME_ERROR,
    }


def test_setup_telemetry_is_off_by_default(monkeypatch: pytest.MonkeyPatch):
    from fastapi import FastAPI

    monkeypatch.delenv("OTEL_ENABLED", raising=False)
    app = FastAPI()

    assert telemetry.setup_telemetry(app) is False
    assert not getattr(app, "_is_instrumented_by_opentelemetry", False)


# Chạy trong tiến trình riêng: bật OTel đặt provider toàn cục, không được ảnh hưởng các test khác
_ENABLED_PROBE = """
from fastapi.testclient import TestClient
from opentelemetry import metrics, trace
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.trace import TracerProvider
from app.main import app

assert getattr(app, "_is_instrumented_by_opentelemetry", False), "FastAPI chưa được instrument"
assert isinstance(metrics.get_meter_provider(), MeterProvider)
assert isinstance(trace.get_tracer_provider(), TracerProvider)
resource = trace.get_tracer_provider().resource.attributes
assert resource["service.name"] == "smashcourt-ai", resource
assert resource["service.version"] == "sha-test", resource
with TestClient(app) as client:
    assert client.get("/health").status_code == 200
print("OK")
"""


def test_setup_telemetry_when_enabled_instruments_app_and_sets_providers():
    env = {
        **os.environ,
        "OTEL_ENABLED": "true",
        # cổng 9 từ chối ngay: exporter chạy nền lỗi nhưng app vẫn phục vụ
        "OTEL_EXPORTER_OTLP_ENDPOINT": "http://127.0.0.1:9",
        "APP_VERSION": "sha-test",
        "GEMINI_API_KEY": "khoa-gia",
    }
    env.pop("OTEL_SERVICE_NAME", None)

    result = subprocess.run(
        [sys.executable, "-c", _ENABLED_PROBE],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr[-2000:]
    assert "OK" in result.stdout
