FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8000

WORKDIR /app

COPY server/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Code + content used by the seed script and the legacy UI.
# .dockerignore keeps .env, virtualenvs and server/data (the learner database) out of the image.
COPY server /app/server
COPY scripts /app/scripts
COPY lessons /app/lessons
COPY docs /app/docs
RUN mkdir -p /app/server/cache /app/server/data

EXPOSE 8000
# Seed only an empty database (first start / new volume), then serve.
CMD ["sh", "-c", "python3 scripts/seed_database.py --if-empty && exec python3 -m uvicorn server.main:app --host 0.0.0.0 --port ${PORT}"]
