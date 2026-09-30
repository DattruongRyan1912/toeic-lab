FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source modules, scripts, and web docs
COPY server /app/server
COPY scripts /app/scripts
COPY docs /app/docs

# Create persistent storage directories
RUN mkdir -p /app/server/cache /app/server/data

ENV PORT=8000
ENV PYTHONPATH=/app
EXPOSE 8000

CMD ["python3", "-m", "uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]
