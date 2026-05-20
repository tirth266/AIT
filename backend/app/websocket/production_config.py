"""
Production Socket Configuration
===============================
Production-ready SocketIO configuration with optimal settings
for high-performance, horizontal scaling.
"""

import os
from typing import Dict, Any


class ProductionSocketConfig:
    """
    Production-grade SocketIO configuration.
    """

    @staticmethod
    def get_config() -> Dict[str, Any]:
        """Get production configuration."""

        frontend_url = os.getenv('FRONTEND_URL', '')
        cors_allowed_origins = [origin.strip() for origin in frontend_url.split(',') if origin.strip()]
        if not cors_allowed_origins:
            raise RuntimeError(
                'FRONTEND_URL is not set. Set FRONTEND_URL to your frontend deployment URL(s) in production.'
            )

        return {
            'async_mode': os.environ.get('SOCKET_ASYNC_MODE', 'eventlet'),
            'cors_allowed_origins': cors_allowed_origins,
            'ping_timeout': 60,
            'ping_interval': 25,
            'max_http_buffer_size': 10000000,
            'logger': False,
            'engineio_logger': False,
            'json': False,
            'cookie': None,
            'always_connect': False,
            'prepend_http': False,
            'require_session': False,
            'monitor_clients': True,
            'channel': 'socketio'
        }

    @staticmethod
    def get_optimization_config() -> Dict[str, Any]:
        """Get optimization configuration."""

        return {
            'COMPRESSION_ENABLED': True,
            'COMPRESSION_THRESHOLD': 500,
            'BATCHING_ENABLED': True,
            'BATCH_INTERVAL_MS': 50,
            'MAX_BATCH_SIZE': 50,
            'HEARTBEAT_INTERVAL': 25,
            'HEARTBEAT_TIMEOUT': 60,
            'MAX_CONNECTIONS_PER_USER': 5,
            'RATE_LIMIT_PER_MINUTE': 100,
            'RATE_LIMIT_PER_SECOND': 10,
            'PING_INTERVAL_ADAPTIVE': True,
            'PUBSUB_ENABLED': True,
            'PRESENCE_ENABLED': True,
            'SESSION_PERSISTENCE': True
        }


class ScalingConfig:
    """
    Horizontal scaling configuration for 1000+ concurrent users.
    """

    @staticmethod
    def get_redis_config() -> Dict[str, Any]:
        """Get Redis configuration for scaling."""

        return {
            'REDIS_URL': os.environ.get('REDIS_URL', 'redis://localhost:6379/0'),
            'REDIS_ASYNC_URL': os.environ.get('REDIS_ASYNC_URL', 'redis://localhost:6379/1'),
            'MAX_CONNECTIONS': 50,
            'SOCKET_TIMEOUT': 5,
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_KEEPALIVE': True,
            'RETRY_ON_TIMEOUT': True,
            'HEALTH_CHECK_INTERVAL': 30
        }

    @staticmethod
    def get_worker_config() -> Dict[str, Any]:
        """Get worker configuration for gunicorn."""

        return {
            'workers': int(os.environ.get('SOCKETIO_WORKERS', 4)),
            'worker_class': 'eventlet',
            'worker_connections': 1000,
            'max_requests': 1000,
            'max_requests_jitter': 50,
            'timeout': 120,
            'keepalive': 5,
            'preload_app': True
        }

    @staticmethod
    def get_nginx_config() -> Dict[str, Any]:
        """Get nginx proxy configuration recommendations."""

        return {
            'proxy_read_timeout': 300,
            'proxy_send_timeout': 300,
            'proxy_buffering': 'off',
            'proxy_http_version': '1.1',
            'upgrade_upgrade': 'websocket',
            'proxy_set_header Upgrade': '$http_upgrade',
            'proxy_set_header Connection': 'upgrade',
            'proxy_set_header Host': '$host',
            'proxy_set_header X-Real-IP': '$remote_addr',
            'proxy_set_header X-Forwarded-For': '$proxy_add_x_forwarded_for'
        }


class PerformanceConfig:
    """
    Performance optimization recommendations.
    """

    @staticmethod
    def get_tuning_parameters() -> Dict[str, Any]:
        """Get performance tuning parameters."""

        return {
            'target_latency_ms': 20,
            'batch_window_ms': 50,
            'max_queue_size': 10000,
            'compression_level': 6,
            'heartbeat_adaptive': True,
            'connection_pool_size': 50,
            'pubsub_workers': 4,
            'message_buffer_size': 8192
        }

    @staticmethod
    def get_monitoring_metrics() -> list:
        """Get list of metrics to monitor."""

        return [
            'connection_count',
            'messages_per_second',
            'average_latency',
            'p99_latency',
            'queue_depth',
            'redis_pubsub_queue_depth',
            'batching_efficiency',
            'compression_ratio',
            'heartbeat_miss_rate',
            'reconnection_rate'
        ]


def get_production_config() -> Dict[str, Any]:
    """Get complete production configuration."""
    return {
        'socketio': ProductionSocketConfig.get_config(),
        'optimization': ProductionSocketConfig.get_optimization_config(),
        'scaling': {
            'redis': ScalingConfig.get_redis_config(),
            'workers': ScalingConfig.get_worker_config()
        },
        'performance': PerformanceConfig.get_tuning_parameters(),
        'monitoring': PerformanceConfig.get_monitoring_metrics()
    }