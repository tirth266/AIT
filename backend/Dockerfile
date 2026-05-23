FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production
ENV PYTHONPATH=.

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    curl \
    tzdata \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ensure the entrypoint script is executable
RUN chmod +x scripts/docker-entrypoint.sh

# Render will pass the PORT environment variable
ENV PORT=10000

# Entrypoint script for debugging and validation
ENTRYPOINT ["scripts/docker-entrypoint.sh"]

# Using gunicorn with eventlet for optimal WebSocket support
# We bind to 0.0.0.0:$PORT to ensure Render can route traffic to it
CMD gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:$PORT run:app
