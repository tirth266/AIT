# DEPLOYMENT DOCUMENTATION

## Overview
Complete deployment guide for the automated trading platform. Covers local development with Docker, production deployment on Render and Vercel, and operational procedures.

---

## 1. LOCAL DEVELOPMENT (DOCKER)

### 1.1 Prerequisites

- Docker Desktop (Windows/Mac) or Docker Engine (Linux)
- Docker Compose
- 4GB RAM available
- Ports: 5000 (backend), 5173 (frontend), 27017 (MongoDB), 6379 (Redis)

### 1.2 Project Structure

```
project-root/
├── docker-compose.yml
├── docker/
│   ├── backend.Dockerfile
│   └── frontend.Dockerfile
├── backend/
│   ├── app/
│   ├── requirements.txt
│   └── .env
└── frontend/
    ├── src/
    ├── package.json
    └── .env
```

### 1.3 Docker Compose Configuration

```yaml
# docker-compose.yml
version: '3.8'

services:
  # Backend Flask Application
  backend:
    build:
      context: ./backend
      dockerfile: ../docker/backend.Dockerfile
    container_name: trading_backend
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=development
      - MONGO_URI=mongodb://mongo:27017/trading_db
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/1
      - CELERY_RESULT_BACKEND=redis://redis:6379/2
      - JWT_SECRET=dev-secret-key-change-in-production
      - OWNER_PASSWORD_HASH=$2b$12$hashfrombcrypt
    depends_on:
      - mongo
      - redis
    volumes:
      - ./backend:/app
      - /app/__pycache__
    restart: unless-stopped
    networks:
      - trading_network

  # Frontend React Application
  frontend:
    build:
      context: ./frontend
      dockerfile: ../docker/frontend.Dockerfile
    container_name: trading_frontend
    ports:
      - "5173:5173"
    environment:
      - VITE_API_URL=http://localhost:5000
      - VITE_SOCKET_URL=http://localhost:5000
    depends_on:
      - backend
    volumes:
      - ./frontend:/app
      - /app/node_modules
    restart: unless-stopped
    networks:
      - trading_network

  # MongoDB Database
  mongo:
    image: mongo:7.0
    container_name: trading_mongo
    ports:
      - "27017:27017"
    environment:
      - MONGO_INITDB_DATABASE=trading_db
    volumes:
      - mongo_data:/data/db
    restart: unless-stopped
    networks:
      - trading_network

  # Redis Cache & Celery Broker
  redis:
    image: redis:7-alpine
    container_name: trading_redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    restart: unless-stopped
    networks:
      - trading_network

  # Celery Worker
  celery_worker:
    build:
      context: ./backend
      dockerfile: ../docker/backend.Dockerfile
    container_name: trading_celery
    command: celery -A app.celery worker -l INFO -Q trading,backtest,maintenance
    environment:
      - FLASK_ENV=development
      - MONGO_URI=mongodb://mongo:27017/trading_db
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/1
      - CELERY_RESULT_BACKEND=redis://redis:6379/2
    depends_on:
      - mongo
      - redis
      - backend
    volumes:
      - ./backend:/app
    restart: unless-stopped
    networks:
      - trading_network

  # Celery Beat (Scheduler)
  celery_beat:
    build:
      context: ./backend
      dockerfile: ../docker/backend.Dockerfile
    container_name: trading_celery_beat
    command: celery -A app.celery beat -l INFO
    environment:
      - MONGO_URI=mongodb://mongo:27017/trading_db
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/1
    depends_on:
      - redis
    volumes:
      - ./backend:/app
    restart: unless-stopped
    networks:
      - trading_network

volumes:
  mongo_data:
  redis_data:

networks:
  trading_network:
    driver: bridge
```

### 1.4 Backend Dockerfile

```dockerfile
# docker/backend.Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ .

# Create logs directory
RUN mkdir -p /app/logs

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 5000

# Run with gunicorn for production-like behavior
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--worker-class", "eventlet", "--reload", "app:app"]
```

### 1.5 Frontend Dockerfile

```dockerfile
# docker/frontend.Dockerfile
FROM node:20-alpine

WORKDIR /app

# Copy package files first for better caching
COPY frontend/package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY frontend/ .

# Expose Vite dev server port
EXPOSE 5173

# Start development server with hot reload
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
```

### 1.6 Running Local Development

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down

# Rebuild specific service
docker-compose up -d --build backend

# Access services
# Frontend: http://localhost:5173
# Backend: http://localhost:5000
# MongoDB: localhost:27017
# Redis: localhost:6379
```

---

## 2. PRODUCTION DEPLOYMENT

### 2.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        PRODUCTION DEPLOYMENT                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────┐      ┌──────────────────┐                    │
│  │    Vercel        │      │    Render       │                    │
│  │   (Frontend)     │      │   (Backend)     │                    │
│  │                  │      │                  │                    │
│  │  React + Vite   │─────▶│  Flask + SocketIO│                    │
│  │  Auto-deploy    │      │  Gunicorn +     │                    │
│  │                  │      │  Eventlet       │                    │
│  └──────────────────┘      └────────┬─────────┘                    │
│                                     │                               │
│                    ┌────────────────┼────────────────┐              │
│                    │                │                │              │
│                    ▼                ▼                ▼              │
│             ┌───────────┐    ┌───────────┐    ┌───────────┐     │
│             │  Render   │    │ Upstash   │    │ MongoDB    │     │
│             │ (Celery)  │    │  (Redis)  │    │   Atlas    │     │
│             └───────────┘    └───────────┘    └───────────┘     │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 MongoDB Atlas Setup

**Step 1: Create Account**
1. Go to https://www.mongodb.com/cloud/atlas
2. Create free account

**Step 2: Create Cluster**
1. Choose "Free" tier (M0)
2. Select region (nearest to you)
3. Create cluster

**Step 3: Configure Security**
1. Create database user (username/password)
2. Network Access: Add IP 0.0.0.0/0 (allow all) OR add Render's IP
3. Get connection string:
```
mongodb+srv://<username>:<password>@cluster0.xxxx.mongodb.net/trading_db?retryWrites=true&w=majority
```

**Step 4: Save Connection String**
- Add to Render environment variables as `MONGO_URI`

---

### 2.3 Upstash Redis Setup

**Step 1: Create Account**
1. Go to https://upstash.com
2. Create free account

**Step 2: Create Database**
1. Create new Redis database
2. Copy connection string:
```
redis://default:password@host:port
```

**Step 3: Save Configuration**
- `REDIS_URL` = connection string
- `CELERY_BROKER_URL` = same as above

---

### 2.4 Render Backend Deployment

**Step 1: Connect Repository**
1. Go to https://render.com
2. Connect GitHub repository
3. Select backend folder

**Step 2: Configure Web Service**

| Setting | Value |
|---------|-------|
| Name | trading-backend |
| Region | Oregon (or nearest) |
| Branch | main |
| Runtime | Python 3.11 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `gunicorn app:app --worker-class eventlet -w 1` |

**Step 3: Environment Variables**

| Variable | Value | Required |
|----------|-------|----------|
| `MONGO_URI` | mongodb+srv://... | Yes |
| `REDIS_URL` | redis://... | Yes |
| `CELERY_BROKER_URL` | redis://... | Yes |
| `JWT_SECRET` | random-32-char-string | Yes |
| `OWNER_PASSWORD_HASH` | bcrypt hash | Yes |
| `FLASK_ENV` | production | No |
| `LOG_LEVEL` | INFO | No |
| `TELEGRAM_BOT_TOKEN` | optional | No |

**Step 4: Deploy**
- Deploy automatically on push to main

**Step 5: Create Background Worker (Celery)**

| Setting | Value |
|---------|-------|
| Name | trading-celery |
| Region | Same as backend |
| Branch | main |
| Runtime | Python 3.11 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `celery -A app.celery worker -l INFO -Q trading,backtest,maintenance` |
| Environment Variables | Same as web service |

---

### 2.5 Vercel Frontend Deployment

**Step 1: Connect Repository**
1. Go to https://vercel.com
2. Import GitHub repository

**Step 2: Configure Project**

| Setting | Value |
|---------|-------|
| Framework Preset | Vite |
| Build Command | `npm run build` |
| Output Directory | `dist` |

**Step 3: Environment Variables**

| Variable | Value |
|----------|-------|
| `VITE_API_URL` | https://your-backend.onrender.com |
| `VITE_SOCKET_URL` | https://your-backend.onrender.com |

**Step 4: Deploy**
- Auto-deploy on push

---

## 3. ENVIRONMENT VARIABLES

### 3.1 Backend Variables

```bash
# Required
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/trading_db
JWT_SECRET=your-random-32-character-secret-key-here
OWNER_PASSWORD_HASH=$2b$12$your-bcrypt-hash-here

# Redis (Upstash)
REDIS_URL=redis://default:password@host:port
CELERY_BROKER_URL=redis://default:password@host:port
CELERY_RESULT_BACKEND=redis://default:password@host:port

# Optional
FLASK_ENV=production
LOG_LEVEL=INFO
SESSION_SECRET=another-secret-key

# Telegram (optional)
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_CHAT_ID=your-chat-id
```

### 3.2 Frontend Variables

```bash
VITE_API_URL=https://your-backend.onrender.com
VITE_SOCKET_URL=https://your-backend.onrender.com
```

---

## 4. SSL & DOMAIN

### 4.1 Automatic SSL
- **Vercel**: Automatic SSL on vercel.app domain
- **Render**: Automatic SSL on onrender.com domain

### 4.2 Custom Domain (Optional)

**Vercel**:
1. Go to Project Settings → Domains
2. Add custom domain
3. Update DNS records

**Render**:
1. Go to Web Service Settings → Custom Domains
2. Add domain
3. Update DNS records

---

## 5. HEALTH MONITORING

### 5.1 Health Check Endpoint

```bash
# Test health endpoint
curl https://your-backend.onrender.com/api/v1/health
```

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "checks": {
    "mongo": "connected",
    "redis": "connected",
    "celery": "running"
  },
  "version": "1.0.0"
}
```

### 5.2 Uptime Monitoring

Use free monitoring services:
- **UptimeRobot**: https://uptimerobot.com
- **Healthchecks.io**: https://healthchecks.io

Configure to check `/api/v1/health` every 5 minutes.

---

## 6. BACKUP & RECOVERY

### 6.1 MongoDB Backups

**Automatic (MongoDB Atlas)**:
- Daily automated backups on M0 free tier
- Retention: 7 days
- Restore from Atlas dashboard

**Manual Export**:
```bash
# Export all collections
mongodump --uri="mongodb+srv://..." --out=./backup

# Export specific collection
mongodump --uri="mongodb+srv://..." --collection=strategies --out=./backup
```

### 6.2 Restore Procedure

```bash
# Restore from backup
mongorestore --uri="mongodb+srv://..." --dir=./backup
```

---

## 7. LOGGING & MONITORING

### 7.1 Application Logs

**View in Render**:
- Dashboard → Web Service → Logs
- Real-time streaming

**Log Levels**:
- DEBUG - Detailed debug info (development)
- INFO - General operations
- WARNING - Non-critical issues
- ERROR - Errors requiring attention

### 7.2 Structured Logging

```python
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'message': record.getMessage(),
            'module': record.module,
        })
```

---

## 8. TROUBLESHOOTING

### 8.1 Common Issues

| Issue | Solution |
|-------|----------|
| Backend not responding | Check Render logs, verify environment variables |
| WebSocket connection failed | Check CORS settings, verify URL |
| MongoDB connection error | Verify MONGO_URI, check network access |
| Celery tasks not running | Check background worker logs |
| High memory usage | Reduce number of concurrent workers |

### 8.2 Debug Commands

```bash
# Check container status
docker-compose ps

# View logs
docker-compose logs -f backend

# Access container shell
docker exec -it trading_backend sh

# Check Celery tasks
celery -A app.celery inspect active

# Check Redis
redis-cli -h localhost -p 6379
```

---

## 9. DEPLOYMENT CHECKLIST

### Pre-Deployment
- [ ] All environment variables configured
- [ ] MongoDB Atlas cluster created and accessible
- [ ] Upstash Redis database created
- [ ] GitHub repository connected to Render/Vercel

### Backend Deployment
- [ ] Web service deployed and healthy
- [ ] Background worker deployed and running
- [ ] Health endpoint returns "healthy"
- [ ] WebSocket connection works

### Frontend Deployment
- [ ] Frontend deployed and accessible
- [ ] API URL configured correctly
- [ ] Login page works
- [ ] Dashboard loads with real data

### Post-Deployment
- [ ] Start a test bot (paper mode)
- [ ] Verify trades execute in paper mode
- [ ] Test Telegram notifications (if configured)
- [ ] Monitor logs for errors

---

## 10. PRODUCTION SECURITY

### 10.1 Security Checklist
- [ ] Change default JWT_SECRET
- [ ] Use strong OWNER_PASSWORD_HASH
- [ ] Enable 2FA
- [ ] Restrict CORS to frontend domain only
- [ ] Use HTTPS only
- [ ] Rotate API keys periodically
- [ ] Enable rate limiting

### 10.2 Rate Limiting
```python
# Flask-Limiter configuration
limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["100 per minute"]
)
```

---

*End of Deployment Documentation*