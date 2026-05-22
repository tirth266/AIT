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

from flask_jwt_extended import JWTManager
from .config import config
from .extensions import init_extensions

# Global JWT instance
jwt = JWTManager()

# Initialize SocketIO globally with production CORS settings
socketio = SocketIO(
    cors_allowed_origins=[
        os.environ.get("FRONTEND_ORIGIN", "https://ait-flame.vercel.app"),
        "https://ait-flame.vercel.app",
        "http://localhost:5173",
        "http://localhost:3000"
    ],
    async_mode="eventlet",
    logger=True,
    engineio_logger=True,
    ping_timeout=60,
    ping_interval=25
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

    # Initialize JWT
    jwt.init_app(app)

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

    @app.route('/favicon.ico')
    def favicon():
        return '', 204

    @app.route("/api/v1/debug/session")
    def debug_session():
        """Unprotected debug endpoint to check server state."""
        from .database.connection import get_db
        db_status = "connected" if get_db() is not None else "disconnected"
        return jsonify({
            "db_status": db_status,
            "env": os.environ.get('FLASK_ENV', 'unknown'),
            "frontend_origin": os.environ.get("FRONTEND_ORIGIN", "not set")
        })

    # Robust global exception handler
    @app.errorhandler(Exception)
    def handle_exception(e):
        import traceback
        print("==== BACKEND ERROR ====")
        print(str(e))
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e),
            "type": type(e).__name__
        }), 500

    # SocketIO will be initialized with the app
    socketio.init_app(app)

    # Robust initialization of extensions and middleware
    try:
        # 1. Initialize database and core extensions
        init_extensions(app)
        print("[OK] Core extensions initialized")
    except Exception as e:
        print(f"[WARN] Some extensions failed to initialize: {e}")
        import traceback
        traceback.print_exc()

    try:
        # 2. Register middleware (CORS, Security, etc.)
        # This MUST run for the API to be accessible
        from .middleware import register_middleware
        register_middleware(app)
        print("[OK] Middleware registered")
    except Exception as e:
        print(f"[CRITICAL] Middleware registration failed: {e}")
        import traceback
        traceback.print_exc()

    try:
        register_blueprints(app)
        print("[OK] Blueprints registered")
    except Exception as e:
        print(f"[ERROR] Blueprint registration failed: {e}")
        import traceback
        traceback.print_exc()

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
