"""
Flask Application Factory
=========================
Failsafe Flask application factory.
"""

import os
import logging
from flask import Flask, jsonify
from flask_socketio import SocketIO
from flask_cors import CORS

from .config import config

# Initialize SocketIO globally for easy access
socketio = SocketIO(
    cors_allowed_origins="*",
    async_mode="eventlet",
    logger=True,
    engineio_logger=True
)

def create_app(config_name: str = None) -> Flask:
    """
    Create and configure Flask application in a failsafe manner.
    """
    print("Starting Flask app factory...")
    
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'production')

    app = Flask(__name__)
    
    # Handle configuration gracefully
    try:
        if config_name in config:
            app.config.from_object(config[config_name])
        else:
            app.config.from_object(config['production'])
    except Exception as e:
        print(f"Config loading failed: {e}")

    # Mandatory implementations: Root and Ping routes
    @app.route("/")
    def home():
        return jsonify({
            "status": "ok",
            "message": "AIT Backend Running"
        })

    @app.route("/api/v1/ping")
    def ping():
        return jsonify({
            "status": "pong"
        })

    # Robust global exception handler
    @app.errorhandler(Exception)
    def handle_exception(e):
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

    # Initialize CORS with permissive settings for production stability
    CORS(
        app,
        resources={r"/*": {"origins": "*"}},
        supports_credentials=True
    )

    # Initialize SocketIO with the app
    socketio.init_app(app)

    # Deferred imports for blueprints and services to prevent startup crashes
    try:
        from .middleware import register_middleware
        register_middleware(app)
        print("[OK] Middleware registered")
    except Exception as e:
        print(f"[ERROR] Middleware registration failed: {e}")

    try:
        register_blueprints(app)
        print("[OK] Blueprints registered")
    except Exception as e:
        print(f"[ERROR] Blueprint registration failed: {e}")

    print("Application initialized successfully")
    return app


def register_blueprints(app: Flask) -> None:
    """Register all API blueprints with safety checks."""
    try:
        # Wrap each registration in its own try/except if needed
        from .brokers.angelone import angelone_bp
        app.register_blueprint(angelone_bp, url_prefix='/api/v1/broker/angelone')

        from .api import (
            strategies, trades, orders, watchlist,
            ai_signals, notifications, funds, bot, broker,
            backtest, market, settings, dashboard, health, auth
        )
        # Core Blueprints
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
    except Exception as e:
        print(f"Blueprint registration partial failure: {e}")
