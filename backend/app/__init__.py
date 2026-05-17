"""
Flask Application Factory
=========================
Production-ready Flask application factory with extensions, blueprints,
websocket, and logging initialization.
"""

import os
import logging
from flask import Flask, jsonify
from flask_socketio import SocketIO

from app.config import config
from app.extensions import init_extensions
from app.logs import setup_logging, init_correlation_middleware
from app.errors.handlers import register_error_handlers
from app.middleware import register_middleware
from app.observability import (
    setup_metrics,
    setup_tracing,
    setup_health_checks,
    metrics_collector
)

socketio = SocketIO(
    cors_allowed_origins="*",
    async_mode='eventlet',
    ping_timeout=60,
    ping_interval=25,
    max_http_buffer_size=10000000,
    message_queue=os.environ.get('SOCKETIO_MESSAGE_QUEUE', 'redis://localhost:6379/3'),
    channel='socketio',
    spark_events=True,
    logger=True,
    engineio_logger=False
)

def create_app(config_name: str = None) -> Flask:
    """
    Create and configure Flask application.

    Args:
        config_name: Environment name (development, production, testing)

    Returns:
        Configured Flask application instance
    """
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    setup_logging(app)
    init_correlation_middleware(app)
    logger = logging.getLogger('trading_app')
    logger.info(f"Starting application in {config_name} mode")

    init_extensions(app)
    register_blueprints(app)
    register_socket_events(app)
    register_error_handlers(app)
    register_middleware(app)

    setup_metrics(app)
    setup_tracing(app)
    setup_health_checks(app)

    logger.info("Observability stack initialized (metrics, tracing, health checks)")

    logger.info("Application initialized successfully")
    return app


def register_blueprints(app: Flask) -> None:
    """Register all API blueprints."""
    from app.api import (
        auth, strategies, trades, orders, watchlist,
        ai_signals, notifications, funds, bot, broker,
        backtest, market, settings, dashboard, health
    )
    from app.api.trading_engine import bp as trading_engine_bp

    app.register_blueprint(auth.bp, url_prefix='/api/v1/auth')
    app.register_blueprint(strategies.bp, url_prefix='/api/v1/strategies')
    app.register_blueprint(trades.bp, url_prefix='/api/v1/trades')
    app.register_blueprint(orders.bp, url_prefix='/api/v1/orders')
    app.register_blueprint(watchlist.bp, url_prefix='/api/v1/watchlist')
    app.register_blueprint(ai_signals.bp, url_prefix='/api/v1/signals')
    app.register_blueprint(notifications.bp, url_prefix='/api/v1/notifications')
    app.register_blueprint(funds.bp, url_prefix='/api/v1/funds')
    app.register_blueprint(bot.bp, url_prefix='/api/v1/bot')
    app.register_blueprint(broker.bp, url_prefix='/api/v1/broker')
    app.register_blueprint(backtest.bp, url_prefix='/api/v1/backtest')
    app.register_blueprint(market.bp, url_prefix='/api/v1/market')
    app.register_blueprint(settings.bp, url_prefix='/api/v1/settings')
    app.register_blueprint(dashboard.bp, url_prefix='/api/v1/dashboard')
    app.register_blueprint(health.bp, url_prefix='/api/v1')
    app.register_blueprint(trading_engine_bp, url_prefix='/api/v1/trading')
    app.register_blueprint(strategy_engine_bp, url_prefix='/api/v1/engine')


def register_socket_events(app: Flask) -> None:
    """Initialize SocketIO with the Flask app."""
    from app.websocket.redis_manager import get_redis_pool
    get_redis_pool().initialize()

    socketio.init_app(app, cors_allowed_origins="*")
    from app.websocket.scalable_handlers import register_scalable_handlers
    register_scalable_handlers(socketio, app)

    logger = logging.getLogger('trading_app')
    logger.info("Scalable WebSocket handlers registered")


def initialize_market_data_engine():
    """Initialize the market data engine."""
    from app.market_data.engine import initialize_market_engine
    from app.websocket.socket_manager import get_ws_manager
    
    engine = initialize_market_engine()
    
    def broadcast_callback(event: str, data: dict, symbol: str = None):
        ws_manager = get_ws_manager()
        if symbol:
            ws_manager.broadcast_to_room(f"market:{symbol}", event, data)
        else:
            ws_manager.broadcast(event, data)
    
    engine.set_broadcast_callback(broadcast_callback)
    logger.info("Market data engine initialized")
    return engine


market_data_engine = initialize_market_data_engine()


app = create_app()