"""
Flask Application Factory
=========================
Production-ready Flask application factory with extensions, blueprints,
websocket, and logging initialization.
"""

import os
import logging
import sys
from flask import Flask, jsonify, request, g
from flask_socketio import SocketIO

from .config import config
from .extensions import init_extensions
from .logs import setup_logging, init_correlation_middleware
from .errors.handlers import register_error_handlers
from .middleware import register_middleware
from .observability import (
    setup_metrics,
    setup_tracing,
    setup_health_checks,
    metrics_collector
)
from .trading_engine.execution_engine import get_execution_engine
from .trading_engine.paper.paper_exchange import get_paper_exchange
from .websocket.redis_manager import get_redis_pool
from .websocket.socket_manager import init_websocket_manager

def get_frontend_origins():
    raw_origins = os.environ.get('FRONTEND_URL', '')
    origins = [origin.strip() for origin in raw_origins.split(',') if origin.strip()]
    if not origins:
        # Default for local development
        origins = ['http://localhost:5173', 'http://127.0.0.1:5173']
    return origins


def create_socketio():
    """Create and configure SocketIO instance with production settings."""
    logger = logging.getLogger('socketio')
    logger.setLevel(logging.INFO)

    cors_allowed_origins = get_frontend_origins()

    return SocketIO(
        cors_allowed_origins=cors_allowed_origins,
        async_mode=os.environ.get('SOCKET_ASYNC_MODE', 'eventlet'),
        ping_timeout=60,
        ping_interval=25,
        max_http_buffer_size=10000000,
        logger=logger,
        engineio_logger=False,
        allow_upgrades=True,
        websocket_ping_interval=25,
        websocket_ping_timeout=60,
        manage_session=False,
        cookie=None,
    )

socketio = create_socketio()

def initialize_background_services(app: Flask) -> None:
    """
    Initialize and start background async services safely.
    Uses threading instead of asyncio for eventlet compatibility.
    """
    import threading
    
    try:
        engine = get_execution_engine()
        exchange = get_paper_exchange()
        
        def run_services():
            try:
                engine.start()
            except Exception as e:
                app.logger.error(f"Execution engine error: {e}")
        
        def run_exchange():
            try:
                exchange.start()
            except Exception as e:
                app.logger.error(f"Paper exchange error: {e}")
        
        def run_angel_ws():
            try:
                from .brokers.angelone.websocket.manager import ws_manager as angel_ws
                angel_ws.start()
            except Exception as e:
                app.logger.warning(f"Angel One WS initialization: {e}")
        
        engine_thread = threading.Thread(target=run_services, daemon=True)
        exchange_thread = threading.Thread(target=run_exchange, daemon=True)
        
        engine_thread.start()
        exchange_thread.start()
        
        try:
            from .brokers.angelone.websocket.manager import ws_manager as angel_ws
            angel_ws.start()
        except Exception as e:
            app.logger.warning(f"Angel One WS: {e}")
        
        initialize_market_data_engine()
        
        app.logger.info("Background services initialized")
    except Exception as e:
        app.logger.error(f"Failed to initialize background services: {e}")


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

    @app.route("/api/v1/ping")
    def ping():
        """Direct, stable diagnostic endpoint."""
        return jsonify({
            "status": "pong",
            "timestamp": __import__('datetime').datetime.utcnow().isoformat() + 'Z',
            "version": "1.0.4-stable"
        }), 200

    @app.route("/api/health")
    def api_health():
        """API health check endpoint."""
        return {"status": "healthy"}, 200

    setup_logging(app)
    init_correlation_middleware(app)
    logger = logging.getLogger('trading_app')
    logger.info(f"Starting application in {config_name} mode")

    # Temporarily disabled extensions/services to debug Bad Gateway
    # init_extensions(app)
    register_blueprints(app)
    register_socket_events(app)
    register_error_handlers(app)
    register_middleware(app)

    # setup_metrics(app)
    # setup_tracing(app)
    # setup_health_checks(app)

    @app.errorhandler(Exception)
    def handle_exception(e):
        """Log the full traceback of any unhandled exception."""
        import traceback
        error_msg = f"Unhandled Exception: {str(e)}\n{traceback.format_exc()}"
        app.logger.error(error_msg)
        return jsonify({
            "error": "INTERNAL_ERROR",
            "message": str(e)
        }), 500

    @app.after_request
    def final_response_processing(response):
        """Final global response processing to ensure headers and stability."""
        from flask import request, g
        
        # Ensure Correlation ID is propagated safely
        corr_id = getattr(g, 'correlation_id', None) or getattr(request, 'correlation_id', None)
        if corr_id:
            response.headers['X-Correlation-ID'] = corr_id
            
        return response

    # Initialize background services safely after app creation
    # Temporarily disabled
    # initialize_background_services(app)

    logger.info("Application initialized successfully")
    return app


def register_blueprints(app: Flask) -> None:
    """Register all API blueprints."""
    from .brokers.angelone import angelone_bp
    app.register_blueprint(angelone_bp, url_prefix='/api/v1/broker/angelone')

    from .api import (
        strategies, trades, orders, watchlist,
        ai_signals, notifications, funds, bot, broker,
        backtest, market, settings, dashboard, health, auth
    )
    from .api.trading_engine import bp as trading_engine_bp
    from .api.strategy_engine import bp as strategy_engine_bp

    # API v1 Core Blueprints
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
    app.register_blueprint(health.bp, url_prefix='/api/v1/health')
    app.register_blueprint(trading_engine_bp, url_prefix='/api/v1/trading')
    app.register_blueprint(strategy_engine_bp, url_prefix='/api/v1/strategy')


def register_socket_events(app: Flask) -> None:
    """Initialize SocketIO with the Flask app."""
    app_ws_logger = logging.getLogger('websocket')
    app_ws_logger.info("Initializing WebSocket...")

    # Temporarily disabled Redis message queue
    # redis_pool = get_redis_pool()
    # try:
    #     redis_pool.initialize()
    #     app_ws_logger.info(f"Redis connected: {redis_pool.redis_url}")
    # except Exception as e:
    #     app_ws_logger.warning(f"Redis unavailable: {e}, using local mode")

    socketio.init_app(
        app,
        logger=app_ws_logger,
        engineio_logger=False
    )


def initialize_market_data_engine():
    """Initialize the market data engine."""
    from .market_data.engine import initialize_market_engine, get_market_data_engine
    from .websocket.socket_manager import get_ws_manager

    engine = initialize_market_engine()

    def broadcast_callback(event: str, data: dict, symbol: str = None):
        ws_manager = get_ws_manager()
        if symbol:
            ws_manager.broadcast_to_room(f"market:{symbol}", event, data)
        else:
            ws_manager.broadcast(event, data)

    engine.set_broadcast_callback(broadcast_callback)
    logging.getLogger('trading_app').info("Market data engine initialized")
    return get_market_data_engine()
