#!/bin/bash
# =============================================================================
# DOCKER ENTRYPOINT SCRIPT
# =============================================================================
# Production startup script with validation and graceful shutdown
#
# Features:
# - Environment validation
# - Database connection check
# - Graceful shutdown handling
# - Logging setup

set -euo pipefail

echo "=========================================="
echo "  Trading Platform - Starting Backend"
echo "=========================================="

# =============================================================================
# CONFIGURATION
# =============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="/app"
LOG_DIR="${APP_DIR}/logs"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# =============================================================================
# LOGGING FUNCTIONS
# =============================================================================
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# =============================================================================
# VALIDATION
# =============================================================================
validate_environment() {
    log_info "Validating environment variables..."

    local required_vars=(
        "MONGO_URI"
        "REDIS_URL"
        "SECRET_KEY"
        "JWT_SECRET_KEY"
    )

    local missing_vars=()

    for var in "${required_vars[@]}"; do
        if [ -z "${!var:-}" ]; then
            missing_vars+=("$var")
        fi
    done

    if [ ${#missing_vars[@]} -gt 0 ]; then
        log_error "Missing required environment variables:"
        for var in "${missing_vars[@]}"; do
            echo "  - $var"
        done
        exit 1
    fi

    # Validate SECRET_KEY length (minimum 32 characters)
    if [ ${#SECRET_KEY} -lt 32 ]; then
        log_error "SECRET_KEY must be at least 32 characters"
        exit 1
    fi

    # Validate JWT_SECRET_KEY length
    if [ ${#JWT_SECRET_KEY} -lt 32 ]; then
        log_error "JWT_SECRET_KEY must be at least 32 characters"
        exit 1
    fi

    log_info "Environment validation passed"
}

# =============================================================================
# WAIT FOR SERVICES
# =============================================================================
wait_for_mongodb() {
    log_info "Waiting for MongoDB..."

    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if mongosh --eval "db.adminCommand('ping')" "${MONGO_URI}" &>/dev/null; then
            log_info "MongoDB is ready"
            return 0
        fi
        echo "  Attempt $attempt/$max_attempts..."
        sleep 2
        ((attempt++))
    done

    log_error "MongoDB connection failed after $max_attempts attempts"
    return 1
}

wait_for_redis() {
    log_info "Waiting for Redis..."

    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if redis-cli -u "${REDIS_URL}" ping &>/dev/null; then
            log_info "Redis is ready"
            return 0
        fi
        echo "  Attempt $attempt/$max_attempts..."
        sleep 2
        ((attempt++))
    done

    log_error "Redis connection failed after $max_attempts attempts"
    return 1
}

# =============================================================================
# GRACEFUL SHUTDOWN
# =============================================================================
cleanup() {
    log_info "Received shutdown signal, cleaning up..."

    # Kill all background processes
    pkill -f "gunicorn" 2>/dev/null || true
    pkill -f "celery" 2>/dev/null || true

    log_info "Shutdown complete"
    exit 0
}

trap cleanup SIGTERM SIGINT SIGQUIT

# =============================================================================
# MAIN
# =============================================================================
main() {
    log_info "Starting application..."

    # Validate environment
    validate_environment

    # Wait for services (only in production mode)
    if [ "${FLASK_ENV:-production}" = "production" ]; then
        wait_for_mongodb || log_warn "MongoDB not available, continuing anyway..."
        wait_for_redis || log_warn "Redis not available, continuing anyway..."
    fi

    # Create log directory
    mkdir -p "${LOG_DIR}"

    # Run database migrations if needed
    # python scripts/migrate.py || log_warn "Migration failed, continuing..."

    log_info "Starting Gunicorn..."

    # Start Gunicorn with production settings
    # Using multiple workers for production (2 * CPU + 1)
    exec gunicorn \
        --bind 0.0.0.0:5000 \
        --workers 4 \
        --worker-class sync \
        --worker-connections 1000 \
        --max-requests 1000 \
        --max-requests-jitter 50 \
        --timeout 120 \
        --keep-alive 5 \
        --access-logfile "${LOG_DIR}/access.log" \
        --error-logfile "${LOG_DIR}/error.log" \
        --log-level info \
        --capture-output \
        --enable-stdio-inheritance \
        "app:create_app()"
}

main "$@"