"""
Health Check Module
===================
Comprehensive health checks for:
- Application components
- External dependencies
- System resources
- Custom health endpoints
"""

import time
import psutil
import logging
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logger = logging.getLogger('trading_app.health')

health_check_registry: List['HealthCheck'] = []


class HealthStatus(Enum):
    """Health status enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthCheck:
    """Represents a health check."""
    name: str
    check_fn: Callable
    timeout: float = 5.0
    critical: bool = False
    tags: List[str] = field(default_factory=list)
    last_checked: Optional[float] = None
    last_status: Optional[HealthStatus] = None
    last_message: Optional[str] = None

    def run(self) -> Dict[str, Any]:
        """Run the health check."""
        self.last_checked = time.time()
        start_time = time.time()

        try:
            result = self.check_fn()
            if isinstance(result, dict):
                status = result.get('status', 'unknown')
                message = result.get('message', 'OK')
                details = result.get('details', {})
            else:
                status = 'healthy' if result else 'unhealthy'
                message = 'OK' if result else 'Failed'
                details = {}

            self.last_status = HealthStatus(status)
            self.last_message = message

            return {
                'status': status,
                'message': message,
                'details': details,
                'duration_ms': int((time.time() - start_time) * 1000)
            }
        except Exception as e:
            self.last_status = HealthStatus.UNHEALTHY
            self.last_message = str(e)

            return {
                'status': 'unhealthy',
                'message': str(e),
                'details': {'exception': type(e).__name__},
                'duration_ms': int((time.time() - start_time) * 1000)
            }


def register_health_check(
    name: str,
    check_fn: Callable,
    timeout: float = 5.0,
    critical: bool = False,
    tags: Optional[List[str]] = None
) -> None:
    """Register a health check."""
    check = HealthCheck(
        name=name,
        check_fn=check_fn,
        timeout=timeout,
        critical=critical,
        tags=tags or []
    )
    health_check_registry.append(check)
    logger.info(f"Registered health check: {name}")


def get_health_status(include_details: bool = True) -> Dict[str, Any]:
    """Get overall health status."""
    checks = []
    overall_status = HealthStatus.HEALTHY
    critical_failures = 0

    for check in health_check_registry:
        result = check.run()
        checks.append({
            'name': check.name,
            'status': result['status'],
            'message': result['message'],
            'duration_ms': result['duration_ms']
        })

        if check.critical and result['status'] == 'unhealthy':
            critical_failures += 1
            if overall_status == HealthStatus.HEALTHY:
                overall_status = HealthStatus.UNHEALTHY
        elif result['status'] == 'unhealthy' and overall_status == HealthStatus.HEALTHY:
            overall_status = HealthStatus.DEGRADED
        elif result['status'] == 'degraded':
            if overall_status == HealthStatus.HEALTHY:
                overall_status = HealthStatus.DEGRADED

    response = {
        'status': overall_status.value,
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'checks': checks if include_details else None,
        'summary': {
            'total': len(checks),
            'healthy': sum(1 for c in checks if c['status'] == 'healthy'),
            'degraded': sum(1 for c in checks if c['status'] == 'degraded'),
            'unhealthy': sum(1 for c in checks if c['status'] == 'unhealthy'),
            'critical_failures': critical_failures
        }
    }

    if not include_details:
        response.pop('checks')

    return response


def setup_health_checks(app):
    """Setup default health checks."""

    def check_mongodb():
        try:
            from app.database.connection import get_db
            db = get_db()
            result = db.command('ping')
            return {
                'status': 'healthy',
                'message': 'MongoDB connected',
                'details': {'version': result.get('ok')}
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'message': f'MongoDB connection failed: {str(e)}'
            }

    def check_redis():
        try:
            from app.services.redis_service import get_redis_client
            redis_client = get_redis_client()
            redis_client.ping()
            info = redis_client.info('server')
            return {
                'status': 'healthy',
                'message': 'Redis connected',
                'details': {'version': info.get('redis_version')}
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'message': f'Redis connection failed: {str(e)}'
            }

    def check_system_resources():
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        issues = []
        status = 'healthy'

        if cpu_percent > 90:
            issues.append(f'CPU at {cpu_percent}%')
            status = 'degraded'

        if memory.percent > 90:
            issues.append(f'Memory at {memory.percent}%')
            status = 'degraded'

        if disk.percent > 90:
            issues.append(f'Disk at {disk.percent}%')
            status = 'unhealthy'

        return {
            'status': status,
            'message': ', '.join(issues) if issues else 'All resources OK',
            'details': {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'disk_percent': disk.percent
            }
        }

    def check_celery_workers():
        try:
            from app.celery_app import celery_app
            inspect = celery_app.control.inspect(timeout=2.0)
            stats = inspect.stats()
            if stats:
                worker_count = len(stats)
                return {
                    'status': 'healthy',
                    'message': f'{worker_count} workers active',
                    'details': {'workers': list(stats.keys())}
                }
            return {
                'status': 'unhealthy',
                'message': 'No Celery workers available'
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'message': f'Celery check failed: {str(e)}'
            }

    def check_websocket_connections():
        try:
            from app.websocket.socket_manager import get_ws_manager
            manager = get_ws_manager()
            active = len(manager.get_active_connections()) if hasattr(manager, 'get_active_connections') else 0
            return {
                'status': 'healthy',
                'message': f'{active} active connections',
                'details': {'active_connections': active}
            }
        except Exception as e:
            return {
                'status': 'degraded',
                'message': f'WebSocket check failed: {str(e)}'
            }

    def check_market_data_engine():
        try:
            from app.market_data.engine import get_market_engine
            engine = get_market_engine()
            symbols = engine.get_subscribed_symbols() if hasattr(engine, 'get_subscribed_symbols') else []
            return {
                'status': 'healthy',
                'message': f'{len(symbols)} symbols tracked',
                'details': {'symbols': symbols}
            }
        except Exception as e:
            return {
                'status': 'degraded',
                'message': f'Market data engine check failed: {str(e)}'
            }

    register_health_check('mongodb', check_mongodb, critical=True, tags=['database'])
    register_health_check('redis', check_redis, critical=True, tags=['cache', 'broker'])
    register_health_check('system', check_system_resources, tags=['system'])
    register_health_check('celery', check_celery_workers, tags=['async'])
    register_health_check('websocket', check_websocket_connections, tags=['realtime'])
    register_health_check('market_data', check_market_data_engine, tags=['trading'])

    @app.route('/health')
    def health_endpoint():
        """Main health endpoint."""
        return get_health_status(include_details=False)

    @app.route('/health/detailed')
    def health_detailed_endpoint():
        """Detailed health endpoint."""
        return get_health_status(include_details=True)

    @app.route('/health/live')
    def liveness_probe():
        """Kubernetes liveness probe."""
        return {'status': 'alive'}, 200

    @app.route('/health/ready')
    def readiness_probe():
        """Kubernetes readiness probe."""
        status = get_health_status(include_details=False)
        if status['status'] in ['healthy', 'degraded']:
            return {'status': 'ready'}, 200
        return {'status': 'not ready'}, 503

    logger.info("Health checks initialized")


from flask import Flask