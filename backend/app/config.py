"""
Configuration Module
====================
Environment-based configuration for Flask application.
"""

import os
from datetime import timedelta
from urllib.parse import quote_plus
import logging

logger = logging.getLogger('trading_app')

def build_mongo_uri() -> str:
    """
    Safely build MongoDB URI from environment variables.
    Handles RFC 3986 escaping for credentials.
    Prioritizes existing MONGO_URI if present.
    """
    if os.environ.get("MONGO_URI"):
        return os.environ.get("MONGO_URI")

    user = os.environ.get("MONGO_USER", "")
    password = quote_plus(os.environ.get("MONGO_PASSWORD", ""))
    host = os.environ.get("MONGO_HOST", "localhost")
    db = os.environ.get("MONGO_DB_NAME", "trading_platform")
    options = os.environ.get("MONGO_OPTIONS", "")

    auth = f"{user}:{password}@" if user else ""

    protocol = (
        "mongodb+srv"
        if ".mongodb.net" in host
        else "mongodb"
    )

    uri = f"{protocol}://{auth}{host}/{db}"

    if options:
        uri += f"?{options}"

    return uri


class Config:
    """Base configuration with common settings."""

    SECRET_KEY = os.getenv("SECRET_KEY")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")

    ANGEL_API_KEY = os.getenv("ANGEL_API_KEY")
    ANGEL_CLIENT_ID = os.getenv("ANGEL_CLIENT_ID")
    ANGEL_PIN = os.getenv("ANGEL_PIN")
    ANGEL_TOTP_SECRET = os.getenv("ANGEL_TOTP_SECRET")

    # Secure MongoDB configuration
    MONGO_URI = build_mongo_uri()
    MONGO_DB_NAME = os.environ.get('MONGO_DB_NAME', 'trading_platform')

    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/1')
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/2')

    SOCKETIO_MESSAGE_QUEUE = os.environ.get('SOCKETIO_MESSAGE_QUEUE', 'redis://localhost:6379/3')

    ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY', None)
    if ENCRYPTION_KEY is None:
        import base64
        ENCRYPTION_KEY = base64.urlsafe_b64encode(os.urandom(32)).decode()

    OWNER_USERNAME = os.environ.get('OWNER_USERNAME', 'owner')
    OWNER_PASSWORD_HASH = os.environ.get('OWNER_PASSWORD_HASH', None)

    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', None)
    TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', None)

    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')

    RATELIMIT_ENABLED = True
    RATELIMIT_DEFAULT = "100/minute"
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FORMAT = os.environ.get('LOG_FORMAT', 'json')

    ENABLE_LOGSTASH = os.environ.get('ENABLE_LOGSTASH', 'false').lower() == 'true'
    LOGSTASH_HOST = os.environ.get('LOGSTASH_HOST', 'localhost')
    LOGSTASH_PORT = int(os.environ.get('LOGSTASH_PORT', '5044'))

    AUDIT_SECRET_KEY = os.environ.get('AUDIT_SECRET_KEY', 'change-me-in-production-audit-key')
    AUDIT_BATCH_SIZE = int(os.environ.get('AUDIT_BATCH_SIZE', '10'))

    ELASTICSEARCH_HOST = os.environ.get('ELASTICSEARCH_HOST', 'localhost')
    ELASTICSEARCH_PORT = int(os.environ.get('ELASTICSEARCH_PORT', '9200'))

    CORRELATION_ID_HEADER = os.environ.get('CORRELATION_ID_HEADER', 'X-Correlation-ID')

    TRADING_MODE = os.environ.get('TRADING_MODE', 'paper')
    PAPER_BALANCE = float(os.environ.get('PAPER_BALANCE', '10000'))

    RISK_MAX_DAILY_LOSS_PERCENT = float(os.environ.get('RISK_MAX_DAILY_LOSS_PERCENT', '5.0'))
    RISK_PER_TRADE_PERCENT = float(os.environ.get('RISK_PER_TRADE_PERCENT', '1.0'))
    RISK_MAX_OPEN_POSITIONS = int(os.environ.get('RISK_MAX_OPEN_POSITIONS', '3'))
    RISK_MAX_CONSECUTIVE_LOSSES = int(os.environ.get('RISK_MAX_CONSECUTIVE_LOSSES', '3'))
    RISK_MAX_DRAWDOWN_PERCENT = float(os.environ.get('RISK_MAX_DRAWDOWN_PERCENT', '10.0'))
    RISK_TRADE_COOLDOWN_MINUTES = int(os.environ.get('RISK_TRADE_COOLDOWN_MINUTES', '5'))

    CELERY_TASK_TRACK_STARTED = True
    CELERY_TASK_TIME_LIMIT = 3600
    CELERY_TASK_SOFT_TIME_LIMIT = 3000
    CELERY_WORKER_PREFETCH_MULTIPLIER = 1

    MAX_POSITION_SIZE = float(os.environ.get('MAX_POSITION_SIZE', '1.0'))
    DEFAULT_STOP_LOSS_PERCENT = float(os.environ.get('DEFAULT_STOP_LOSS_PERCENT', '1.0'))
    DEFAULT_TAKE_PROFIT_PERCENT = float(os.environ.get('DEFAULT_TAKE_PROFIT_PERCENT', '2.0'))

    CANDLE_RETENTION_DAYS = int(os.environ.get('CANDLE_RETENTION_DAYS', '30'))
    LOG_RETENTION_DAYS = int(os.environ.get('LOG_RETENTION_DAYS', '90'))

    KITE_API_KEY = os.environ.get('KITE_API_KEY', '')
    KITE_API_SECRET = os.environ.get('KITE_API_SECRET', '')
    KITE_REDIRECT_URI = os.environ.get('KITE_REDIRECT_URI', 'http://localhost:5000/callback')
    KITE_ACCESS_TOKEN = os.environ.get('KITE_ACCESS_TOKEN', '')
    KITE_REFRESH_TOKEN = os.environ.get('KITE_REFRESH_TOKEN', '')

    BROKER_CIRCUIT_BREAKER_FAILURE_THRESHOLD = int(os.environ.get('BROKER_CIRCUIT_BREAKER_FAILURE_THRESHOLD', '5'))
    BROKER_CIRCUIT_BREAKER_TIMEOUT = int(os.environ.get('BROKER_CIRCUIT_BREAKER_TIMEOUT', '30'))
    BROKER_RETRY_MAX_ATTEMPTS = int(os.environ.get('BROKER_RETRY_MAX_ATTEMPTS', '3'))
    BROKER_RETRY_BASE_DELAY = float(os.environ.get('BROKER_RETRY_BASE_DELAY', '1.0'))
    BROKER_RATE_LIMIT_ORDERS_PER_SECOND = int(os.environ.get('BROKER_RATE_LIMIT_ORDERS_PER_SECOND', '1'))
    BROKER_RATE_LIMIT_ORDERS_PER_MINUTE = int(os.environ.get('BROKER_RATE_LIMIT_ORDERS_PER_MINUTE', '60'))

    BROKER_WEBSOCKET_RECONNECT_DELAY = float(os.environ.get('BROKER_WEBSOCKET_RECONNECT_DELAY', '1.0'))
    BROKER_WEBSOCKET_MAX_RETRIES = int(os.environ.get('BROKER_WEBSOCKET_MAX_RETRIES', '10'))

    ENABLE_LIVE_TRADING = os.environ.get('ENABLE_LIVE_TRADING', 'false').lower() == 'true'
    ENABLE_PAPER_TRADING = os.environ.get('ENABLE_PAPER_TRADING', 'true').lower() == 'true'

    # Angel One Integration (Legacy support)
    ANGELONE_CLIENT_ID = os.environ.get('ANGELONE_CLIENT_ID', '')
    ANGELONE_API_KEY = os.environ.get('ANGELONE_API_KEY', '')
    ANGELONE_SECRET_KEY = os.environ.get('ANGELONE_SECRET_KEY', '')
    ANGELONE_MPIN = os.environ.get('ANGELONE_MPIN', '')
    ANGELONE_TOTP_SECRET = os.environ.get('ANGELONE_TOTP_SECRET', '')

    # SocketIO Configuration
    SOCKET_ASYNC_MODE = os.environ.get('SOCKET_ASYNC_MODE', 'eventlet')
    SOCKETIO_MESSAGE_QUEUE = os.environ.get('SOCKETIO_MESSAGE_QUEUE', 'redis://localhost:6379/3')


class DevelopmentConfig(Config):
    """Development environment configuration."""
    DEBUG = True
    TESTING = False
    ENV = 'development'
    LOG_LEVEL = 'DEBUG'


class ProductionConfig(Config):
    """Production environment configuration."""
    DEBUG = False
    TESTING = False
    ENV = 'production'
    LOG_LEVEL = 'INFO'

    RATELIMIT_DEFAULT = "100/minute"

    @classmethod
    def init_app(cls, app):
        pass


class TestingConfig(Config):
    """Testing environment configuration."""
    DEBUG = True
    TESTING = True
    ENV = 'testing'
    # For testing, we expect MONGO_DB_NAME to be set to a test database in the environment
    MONGO_URI = build_mongo_uri()
    REDIS_URL = os.environ.get('TEST_REDIS_URL', 'redis://localhost:6379/10')
    CELERY_BROKER_URL = os.environ.get('TEST_CELERY_BROKER_URL', 'redis://localhost:6379/11')
    CELERY_RESULT_BACKEND = os.environ.get('TEST_CELERY_RESULT_BACKEND', 'redis://localhost:6379/12')


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
