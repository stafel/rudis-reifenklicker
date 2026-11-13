# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN opentelemetry-bootstrap -a install

COPY app ./app

# Die Version wird beim Build "eingebacken". So bestimmt das Image-Tag
# (v1 = Sommerreifen, v2 = Winterreifen) die angezeigte Version im UI.
ARG APP_VERSION=v1
ENV APP_VERSION=${APP_VERSION}

RUN useradd --uid 10001 --create-home appuser
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/healthz')"

ENV OTEL_SERVICE_NAME=reifenklicker-backend
ENV OTEL_TRACES_EXPORTER=otlp
ENV OTEL_METRICS_EXPORTER=otlp
ENV OTEL_LOGS_EXPORTER=otlp

ENV OTEL_EXPORTER_OTLP_ENDPOINT="http://opentelemetry-collector.otelo11y-otel-collector.svc.cluster.local"

CMD ["opentelemetry-instrument", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
