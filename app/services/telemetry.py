# opentelemetry cho ai (epic 6c, gói 6c-3a, ob-ai-1): metric/trace/log qua otlp
# chỉ bật khi OTEL_ENABLED=true (bản deploy); địa chỉ collector và chu kỳ gửi đọc từ biến chuẩn
# OTEL_EXPORTER_OTLP_ENDPOINT, OTEL_METRIC_EXPORT_INTERVAL; tắt thì api otel là no-op, metric gemini không tốn gì
import logging
import os

from fastapi import FastAPI
from opentelemetry import metrics
from opentelemetry.metrics import Meter

METER_NAME = "smashcourt.ai"
SERVICE_NAME = "smashcourt-ai"

# tên metric: một nơi duy nhất, dashboard "vận hành" tab ai dùng đúng các tên này
GEMINI_DURATION = "gemini.request.duration"
GEMINI_TOKENS = "gemini.tokens"

# nhãn outcome có giới hạn giá trị
OUTCOME_OK = "ok"
OUTCOME_QUOTA = "quota"
OUTCOME_ERROR = "error"

# biên bucket (giây): lời gọi llm chậm hơn request thường nhiều
GEMINI_DURATION_BOUNDARIES = [0.25, 0.5, 1, 2, 4, 8, 16, 32]
# cùng biên với be để so được và giữ số chuỗi trong gói miễn phí grafana cloud
REQUEST_DURATION_BOUNDARIES = [0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]

logger = logging.getLogger(__name__)


class GeminiMetrics:
    """
    metric của lời gọi gemini: độ trễ theo kết quả (ok, quota = bị giới hạn 429, error) và số token vào/ra
    """

    def __init__(self, meter: Meter) -> None:
        self._duration = meter.create_histogram(
            GEMINI_DURATION,
            unit="s",
            description="Thời gian một lời gọi Gemini",
            explicit_bucket_boundaries_advisory=GEMINI_DURATION_BOUNDARIES,
        )
        self._tokens = meter.create_counter(GEMINI_TOKENS, unit="{token}", description="Số token Gemini đã dùng")

    def record(self, *, operation: str, model: str, outcome: str, duration_s: float, usage: object | None = None) -> None:
        self._duration.record(duration_s, {"gemini.operation": operation, "gemini.model": model, "outcome": outcome})
        if usage is None:
            return
        for token_type, value in (
            ("input", getattr(usage, "prompt_token_count", None)),
            ("output", getattr(usage, "candidates_token_count", None)),
        ):
            if value:
                self._tokens.add(value, {"gemini.model": model, "token.type": token_type})


def setup_telemetry(app: FastAPI) -> bool:
    """
    bật otel cho app khi OTEL_ENABLED=true: metric + trace + log xuất otlp http/protobuf (collector chết thì chỉ lỗi nền, app vẫn chạy);
    trả về False khi tắt
    """
    if os.getenv("OTEL_ENABLED", "").strip().lower() != "true":
        return False

    # tên metric http theo semconv ổn định (http.server.request.duration, giây) giống be; phải đặt trước khi instrument
    os.environ.setdefault("OTEL_SEMCONV_STABILITY_OPT_IN", "http")
    os.environ.setdefault("OTEL_SERVICE_NAME", SERVICE_NAME)

    from opentelemetry import trace
    from opentelemetry._logs import set_logger_provider
    from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
    from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
    from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.metrics.view import ExplicitBucketHistogramAggregation, View
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    resource = Resource.create({"service.version": os.getenv("APP_VERSION", "local")})

    metrics.set_meter_provider(
        MeterProvider(
            resource=resource,
            metric_readers=[PeriodicExportingMetricReader(OTLPMetricExporter())],
            views=[
                View(
                    instrument_name="http.server.request.duration",
                    aggregation=ExplicitBucketHistogramAggregation(REQUEST_DURATION_BOUNDARIES),
                )
            ],
        )
    )

    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(tracer_provider)

    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter()))
    set_logger_provider(logger_provider)
    logging.getLogger().addHandler(LoggingHandler(level=logging.INFO, logger_provider=logger_provider))

    # docker healthcheck gọi /health mỗi 10 giây: không trace
    FastAPIInstrumentor.instrument_app(app, excluded_urls="health")
    # httpx là thư viện http của google-genai: lời gọi gemini có span + metric http client
    HTTPXClientInstrumentor().instrument()

    logger.info("OpenTelemetry bật, gửi tới %s", os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318"))
    return True


# meter toàn cục: trước setup_telemetry là proxy, sau đó tự gắn vào provider thật
gemini_metrics = GeminiMetrics(metrics.get_meter(METER_NAME))
