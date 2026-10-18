FROM python:3.11-slim

WORKDIR /app

# System deps occasionally needed by tokenizers/torch wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# HF model cache lives in a mounted volume (see docker-compose) so it survives restarts
ENV HF_HOME=/app/.hf_cache

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
