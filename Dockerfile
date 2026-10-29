# syntax=docker/dockerfile:1
FROM python:3.12-slim

# Prevent Python from buffering stdout/stderr and creating .pyc files
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install system dependencies (if any are needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies first (for better layer caching)
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy source code and config files
COPY . .

# Run the bot
CMD ["python", "-m", "src.main"]
