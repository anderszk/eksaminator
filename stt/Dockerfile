FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir \
    faster-whisper \
    fastapi \
    "uvicorn[standard]" \
    python-multipart

COPY server.py .

RUN useradd --create-home appuser && chown -R appuser /app
USER appuser

EXPOSE 9001
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "9001"]
