FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    android-tools-adb \
    android-tools-fastboot \
    aapt \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY app.py .
COPY templates/ ./templates/

RUN pip install --no-cache-dir fastapi uvicorn python-multipart

RUN mkdir -p /data/uploads /data/logs

EXPOSE 6767

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:6767/health || exit 1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "6767", "--workers", "2"]
