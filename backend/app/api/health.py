"""
=============================================================================
HEALTH CHECK API
=============================================================================
Production-ready health and readiness checks for:
- Kubernetes/Container orchestration
- Load balancer integration
- Monitoring systems

Endpoints:
- /api/v1/health - Basic health check (liveness)
- /api/v1/ready - Readiness check (dependencies)
- /api/v1/status - Detailed system status
- /api/v1/metrics - Application metrics

Author: Staff Engineer
"""

import logging
import os
import time
import psutil
from datetime import datetime
from flask import Blueprint, jsonify, request
from typing import Dict, Any

logger = logging.getLogger('trading_app')

bp = Blueprint('health', __name__)


# =============================================================================
# BASIC HEALTH CHECK (Liveness Probe)
# =============================================================================
@bp.route('/health', methods=['GET'])
def health_check():
    """
    Basic health check endpoint (Kubernetes liveness probe).

    Returns:
        System health status with basic checks
    """
    checks = {
        'mongo': check_mongodb(),
        'redis': check_redis(),
        'websocket': check_websocket()
    }

    all_healthy = all(checks.values())
    status_code = 200 if all_healthy else 503

    return jsonify({
        'status': 'healthy' if all_healthy else 'unhealthy',
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'checks': checks,
        'version': os.environ.get('APP_VERSION', '1.0.0')
    }), status_code


# =============================================================================
# READINESS CHECK (Kubernetes Readiness Probe)
# =============================================================================
@bp.route('/ready', methods=['GET'])
def ready():
    """
    Readiness check for Kubernetes/Container orchestration.
    Returns 503 if required dependencies are not available.

    This endpoint should be used for:
    - Kubernetes readiness probe
    - Load balancer health checks
    - Docker HEALTHCHECK
    """
    mongo_ok = check_mongodb()
    redis_ok = check_redis()

    if not mongo_ok:
        return jsonify({
            'ready': False,
            'reason': 'MongoDB not available',
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }), 503

    if not redis_ok:
        return jsonify({
            'ready': False,
            'reason': 'Redis not available',
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }), 503

    return jsonify({
        'ready': True,
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }), 200


# =============================================================================
# DETAILED STATUS (Dashboard)
# =============================================================================
@bp.route('/status', methods=['GET'])
def status():
    """
    Detailed system status for monitoring dashboards.

    Returns:
        Comprehensive system information including:
        - Service connectivity
        - Trading statistics
        - System resources
        - Configuration
    """
    from app.config import config

    # Service checks
    mongo_status = check_mongodb()
    redis_status = check_redis()
    ws_status = check_websocket()

    # Database statistics
    db_stats = get_mongodb_stats()
    redis_info = get_redis_stats()

    # System resources
    system_info = get_system_info()

    # Trading metrics
    trading_info = get_trading_info()

    return jsonify({
        'status': 'running',
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'version': os.environ.get('APP_VERSION', '1.0.0'),
        'environment': os.environ.get('FLASK_ENV', 'production'),
        'uptime': os.environ.get('APP_START_TIME', datetime.utcnow().isoformat() + 'Z'),
        'services': {
            'mongodb': {
                'status': 'connected' if mongo_status else 'disconnected',
                'stats': db_stats
            },
            'redis': {
                'status': 'connected' if redis_status else 'disconnected',
                'info': redis_info
            },
            'websocket': {
                'status': 'active' if ws_status else 'inactive'
            },
            'celery': {
                'status': check_celery()
            }
        },
        'trading': trading_info,
        'system': system_info,
        'configuration': {
            'trading_mode': os.environ.get('TRADING_MODE', 'paper'),
            'log_level': os.environ.get('LOG_LEVEL', 'INFO'),
            'debug': os.environ.get('FLASK_DEBUG', '0') == '1'
        }
    }), 200


# =============================================================================
# METRICS (Prometheus-compatible)
# =============================================================================
@bp.route('/metrics', methods=['GET'])
def metrics():
    """
    Application metrics for monitoring systems.
    Prometheus-compatible format available at /metrics/prometheus

    Returns:
        Application metrics including:
        - Request counts
        - Response times
        - Error rates
        - System resources
    """
    from app.extensions import get_mongo_db, get_redis_client

    # Get database metrics
    mongo_db = None
    try:
        mongo_db = get_mongo_db()
    except Exception:
        pass

    db_metrics = {}
    if mongo_db:
        try:
            db_metrics = {
                'collections': mongo_db.list_collection_names().__len__(),
                'commands_per_second': 0  # Would need profiling for accurate count
            }
        except Exception:
            pass

    # Get Redis metrics
    redis_client = None
    try:
        redis_client = get_redis_client()
    except Exception:
        pass

    redis_metrics = {}
    if redis_client:
        try:
            info = redis_client.info('stats')
            redis_metrics = {
                'total_commands': info.get('total_commands_processed', 0),
                'connections': info.get('connected_clients', 0),
                'memory_used_mb': info.get('used_memory', 0) / (1024 * 1024)
            }
        except Exception:
            pass

    # System metrics
    system_metrics = get_system_info()

    # Request metrics (from nginx forwarded headers)
    request_metrics = {
        'remote_addr': request.remote_addr,
        'forwarded_for': request.headers.get('X-Forwarded-For', 'none')
    }

    return jsonify({
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'metrics': {
            'database': db_metrics,
            'redis': redis_metrics,
            'system': system_metrics,
            'requests': request_metrics
        }
    }), 200


# =============================================================================
# HEALTH CHECK FUNCTIONS
# =============================================================================

def check_mongodb() -> bool:
    """Check MongoDB connection."""
    try:
        from app.database.connection import get_db
        db = get_db()
        if db:
            db.command('ping')
            return True
    except Exception as e:
        logger.error(f"MongoDB health check failed: {e}")
    return False


def check_redis() -> bool:
    """Check Redis connection."""
    try:
        from app.database.connection import get_redis
        redis = get_redis()
        if redis:
            redis.ping()
            return True
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
    return False


def check_websocket() -> bool:
    """Check WebSocket service availability."""
    try:
        from app.websocket.socket_manager import get_ws_manager
        ws_manager = get_ws_manager()
        return ws_manager is not None
    except Exception as e:
        logger.warning(f"WebSocket health check failed: {e}")
        return True  # Fail open for WS


def check_celery() -> str:
    """Check Celery worker status."""
    try:
        from app.celery_app import celery_app
        insp = celery_app.control.inspect()
        stats = insp.stats()
        if stats:
            worker_count = len(stats)
            return f"active ({worker_count} workers)"
        return 'no workers'
    except Exception as e:
        logger.warning(f"Celery health check failed: {e}")
        return 'unavailable'


def get_mongodb_stats() -> Dict[str, Any]:
    """Get MongoDB statistics."""
    stats = {}
    try:
        from app.database.connection import get_db
        db = get_db()
        if db:
            stats = {
                'database': db.name,
                'collections': db.list_collection_names()
            }
            # Get some basic counts
            for coll in ['strategies', 'orders', 'positions', 'trades']:
                try:
                    stats[f'{coll}_count'] = db[coll].count_documents({})
                except Exception:
                    pass
    except Exception as e:
        logger.error(f"Failed to get MongoDB stats: {e}")
    return stats


def get_redis_stats() -> Dict[str, Any]:
    """Get Redis statistics."""
    stats = {}
    try:
        from app.database.connection import get_redis
        redis = get_redis()
        if redis:
            info = redis.info()
            stats = {
                'version': info.get('redis_version', 'unknown'),
                'connected_clients': info.get('connected_clients', 0),
                'used_memory_mb': round(info.get('used_memory', 0) / (1024 * 1024), 2),
                'uptime_days': info.get('uptime_days', 0),
                'total_commands': info.get('total_commands_processed', 0),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0)
            }
    except Exception as e:
        logger.error(f"Failed to get Redis stats: {e}")
    return stats


def get_system_info() -> Dict[str, Any]:
    """Get system resource information."""
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        return {
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'memory_used_mb': round(memory.used / (1024 * 1024), 2),
            'memory_total_mb': round(memory.total / (1024 * 1024), 2),
            'disk_percent': disk.percent,
            'process_count': len(psutil.pids())
        }
    except Exception as e:
        logger.warning(f"Failed to get system info: {e}")
        return {}


def get_trading_info() -> Dict[str, Any]:
    """Get trading-related statistics."""
    info = {
        'active_strategies': 0,
        'open_positions': 0,
        'pending_orders': 0
    }

    try:
        from app.database.connection import get_db
        db = get_db()
        if db:
            info['active_strategies'] = db.strategies.count_documents({'is_active': True})
            info['open_positions'] = db.positions.count_documents({'status': 'open'})
            info['pending_orders'] = db.orders.count_documents({'status': 'pending'})
    except Exception as e:
        logger.warning(f"Failed to get trading info: {e}")

    return info