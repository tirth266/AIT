# =============================================================================
# PRODUCTION DEPLOYMENT GUIDE
# =============================================================================
# Phase 1: Infrastructure Setup for Algorithmic Trading Platform
#
# This guide covers:
# - Docker setup
# - Environment configuration
# - Security hardening
# - Health monitoring
# - Horizontal scaling preparation
#
# Version: 1.0.0
# Author: Staff Engineer

# =============================================================================
# TABLE OF CONTENTS
# =============================================================================
# 1. Architecture Overview
# 2. Prerequisites
# 3. Environment Setup
# 4. Building and Running
# 5. Testing
# 6. Security Checklist
# 7. Monitoring
# 8. Scaling Guide
# 9. Troubleshooting
# 10. Deployment Checklist

# =============================================================================
# 1. ARCHITECTURE OVERVIEW
# =============================================================================

# ┌─────────────────────────────────────────────────────────────────────────┐
# │                            NGINX (Port 80/443)                          │
# │                     Reverse Proxy + Load Balancer                       │
# └────────────────────────┬────────────────────────────────────────────────┘
#                          │
#         ┌───────────────┼───────────────┐
#         │               │               │
#         ▼               ▼               ▼
#   ┌───────────┐   ┌───────────┐   ┌───────────┐
#   │ Backend 1 │   │ Backend 2 │   │ Backend N │  ← Horizontal Scaling
#   │  :5000    │   │  :5000    │   │  :5000    │
#   └─────┬─────┘   └─────┬─────┘   └─────┬─────┘
#         │               │               │
#         │    Message Queue (Redis)      │  ← SocketIO pub/sub
#         └───────────────┬───────────────┘
#                         │
#    ┌────────────────────┼────────────────────┐
#    │                    │                    │
#    ▼                    ▼                    ▼
# ┌─────────┐        ┌─────────┐         ┌─────────┐
# │ MongoDB │        │  Redis  │         │ Celery  │
# │  :27017 │        │  :6379  │         │ Worker  │
# └─────────┘        └─────────┘         └─────────┘

# =============================================================================
# 2. PREREQUISITES
# =============================================================================
# Install Docker: https://docs.docker.com/get-docker/
# Install Docker Compose: https://docs.docker.com/compose/install/

# System Requirements:
# - Docker 20.10+
# - Docker Compose 2.0+
# - 4GB RAM minimum (8GB recommended)
# - 20GB disk space

# =============================================================================
# 3. ENVIRONMENT SETUP
# =============================================================================

# 3.1 Copy environment file
cp docker/env.production.example .env

# 3.2 Generate secure secrets (RUN THESE COMMANDS):
# SECRET_KEY (64 characters)
python -c "import os; print(os.urandom(32).hex())"
# JWT_SECRET_KEY (64 characters)
python -c "import os; print(os.urandom(32).hex())"
# ENCRYPTION_KEY (base64)
python -c "import base64; import os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"
# MONGO_PASSWORD (alphanumeric, 16+ chars)
python -c "import secrets; print(secrets.token_hex(16))"
# REDIS_PASSWORD (alphanumeric, 16+ chars)
python -c "import secrets; print(secrets.token_hex(16))"

# 3.3 Update .env file with generated values
# IMPORTANT: Never commit .env to version control!

# =============================================================================
# 4. BUILDING AND RUNNING
# =============================================================================

# 4.1 Build all services
docker-compose build

# 4.2 Start all services
docker-compose up -d

# 4.3 Check service status
docker-compose ps

# 4.4 View logs
docker-compose logs -f backend
docker-compose logs -f nginx
docker-compose logs -f redis

# 4.5 Stop all services
docker-compose down

# =============================================================================
# 5. TESTING
# =============================================================================

# 5.1 Health checks
curl http://localhost/api/v1/health
curl http://localhost/api/v1/ready
curl http://localhost/api/v1/status

# 5.2 Check services
docker-compose exec backend python -c "from app.database.connection import get_redis; r = get_redis(); print('Redis:', r.ping())"
docker-compose exec mongodb mongosh --eval "db.adminCommand('ping')"

# 5.3 Validate environment
docker-compose exec backend python scripts/validate-env.py

# 5.4 Test Nginx
curl -I http://localhost/health
curl -I http://localhost/api/v1/health

# =============================================================================
# 6. SECURITY CHECKLIST
# =============================================================================
# [ ] Generate new SECRET_KEY (not default)
# [ ] Generate new JWT_SECRET_KEY (not default)
# [ ] Set CORS_ORIGINS to specific domains (not '*')
# [ ] Enable Redis password authentication
# [ ] Enable MongoDB authentication
# [ ] Configure HTTPS (SSL certificates)
# [ ] Review rate limiting settings
# [ ] Verify security headers in nginx

# =============================================================================
# 7. MONITORING
# =============================================================================

# 7.1 Container metrics
docker stats

# 7.2 Application logs
docker-compose logs --tail=100 backend

# 7.3 System resource usage
docker-compose top

# 7.4 Redis monitoring
docker-compose exec redis redis-cli INFO

# 7.5 MongoDB status
docker-compose exec mongodb mongosh --eval "db.stats()"

# =============================================================================
# 8. SCALING GUIDE
# =============================================================================

# 8.1 Horizontal scaling (multiple backend instances)
docker-compose up -d --scale backend=3

# 8.2 Add more Celery workers
docker-compose up -d --scale celery-worker=2

# 8.3 Update nginx upstream for more backends

# 8.4 Redis clustering (for production scale)

# =============================================================================
# 9. TROUBLESHOOTING
# =============================================================================

# Container won't start
docker-compose logs <service_name>

# Port conflicts
docker-compose ps
# Check if ports 80, 443, 5000, 6379, 27017 are available

# MongoDB connection issues
docker-compose logs mongodb
# Check MONGO_URI format

# Redis connection issues
docker-compose logs redis
# Check REDIS_URL format and password

# Backend won't start
docker-compose exec backend python -c "from app import create_app; app = create_app(); print('OK')"

# =============================================================================
# 10. DEPLOYMENT CHECKLIST
# =============================================================================
# Pre-deployment:
# [ ] All secrets generated and stored securely
# [ ] Environment variables validated
# [ ] Docker images built successfully
# [ ] Health checks pass
# [ ] Backup strategy in place

# Deployment:
# [ ] Run docker-compose up -d
# [ ] Verify all containers running
# [ ] Check health endpoints
# [ ] Monitor logs for errors

# Post-deployment:
# [ ] Verify WebSocket connections
# [ ] Test authentication flow
# [ ] Check rate limiting
# [ ] Verify trading functionality
# [ ] Set up monitoring/alerting
# [ ] Document any issues

# =============================================================================
# QUICK START COMMANDS
# =============================================================================

# Full deployment:
cp docker/env.production.example .env
# Edit .env with your values
docker-compose up -d --build
curl http://localhost/api/v1/health

# Scale to 3 backend instances:
docker-compose up -d --scale backend=3

# View all logs:
docker-compose logs -f

# Stop everything:
docker-compose down -v

# =============================================================================
# PRODUCTION NOTES
# =============================================================================

# 1. Always use specific image tags, not 'latest'
# 2. Set up log rotation at the infrastructure level
# 3. Configure monitoring (Prometheus, Grafana)
# 4. Set up automated backups for MongoDB
# 5. Use secrets management (HashiCorp Vault, AWS Secrets Manager)
# 6. Configure HTTPS with valid SSL certificates
# 7. Set up load balancer health checks
# 8. Plan for disaster recovery

# =============================================================================
# END OF DEPLOYMENT GUIDE
# =============================================================================