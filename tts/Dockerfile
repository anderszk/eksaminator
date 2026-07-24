FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    wget ca-certificates espeak-ng \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    piper-tts \
    fastapi \
    "uvicorn[standard]"

COPY server.py .

RUN useradd --create-home appuser \
    && mkdir -p /voices \
    && chown -R appuser /app /voices
USER appuser

EXPOSE 9002
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "9002"]
