"""
Flask Application Factory
=========================
Failsafe Flask application factory.
"""

import os
import logging
from flask import Flask, jsonify
from flask_socketio import SocketIO

from flask_jwt_extended import JWTManager
from .config import config
from .extensions import init_extensions
from .middleware.cors import init_cors

# Global JWT instance
jwt = JWTManager()

# Start time for uptime calculation
START_TIME = __import__('datetime').datetime.utcnow()

# Initialize SocketIO globally with production CORS settings
# Increased ping_timeout and ping_interval to prevent WebSocket heartbeats timeouts
socketio = SocketIO(
    cors_allowed_origins=[
        "https://ait-flame.vercel.app",
        "http://localhost:5173"
    ],
    async_mode="eventlet",
    logger=True,
    engineio_logger=True,
    ping_timeout=120,
    ping_interval=45
)

def check_environment():
    """Verify all required environment variables exist."""
    required_vars = [
        "MONGO_URI", "JWT_SECRET_KEY", "SECRET_KEY",
        "ANGEL_API_KEY", "ANGEL_CLIENT_ID", "ANGEL_TOTP_SECRET"
    ]
    missing = [var for var in required_vars if not os.environ.get(var)]
    if missing:
        print(f"[CRITICAL] Missing environment variables: {', '.join(missing)}")
    else:
        print("[OK] All critical environment variables present")

def check_db_health():
    """Test the DB connection."""
    from .database.connection import get_db
    try:
        db = get_db()
        if db is not None:
            # For MongoDB, we can try a list_collection_names or similar light operation
            db.list_collection_names()
            print("[OK] Database connection verified")
            return True
        else:
            print("[CRITICAL] Database connection failed (get_db returned None)")
            return False
    except Exception as e:
        print(f"[CRITICAL] Database health check failed: {e}")
        return False

def create_app(config_name: str = None) -> Flask:
    """
    Create and configure Flask application in a failsafe manner.
    """
    print("Starting Flask app factory...")
    
    # Run startup checks
    check_environment()
    
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'production')

    app = Flask(__name__)
    
    # Initialize CORS explicitly
    try:
        init_cors(app)
        print("[OK] CORS initialized")
    except Exception as e:
        print(f"[CRITICAL] CORS initialization failed: {e}")

    # Handle configuration gracefully
    try:
        if config_name in config:
            app.config.from_object(config[config_name])
        else:
            app.config.from_object(config['production'])
    except Exception as e:
        print(f"Config loading failed: {e}")

    # Register middleware (CORS, Security, etc.) IMMEDIATELY after config
    try:
        from .middleware import register_middleware
        register_middleware(app)
        print("[OK] Middleware registered")
    except Exception as e:
        print(f"[CRITICAL] Middleware registration failed: {e}")

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
        """Instant ping route for Render keep-alive."""
        return jsonify({"status": "ok"}), 200

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

    # Global exception handler
    @app.errorhandler(Exception)
    def handle_exception(e):
        import traceback
        import logging
        logger = logging.getLogger('trading_app')
        logger.error("==== GLOBAL EXCEPTION CAUGHT ====")
        logger.error(str(e))
        logger.error(traceback.format_exc())
        
        # Include traceback in response if in development mode
        error_response = {
            "success": False,
            "error": str(e),
            "type": type(e).__name__
        }
        if app.debug or os.environ.get('FLASK_ENV') == 'development':
            error_response["traceback"] = traceback.format_exc()
            
        return jsonify(error_response), 500

    # SocketIO will be initialized with the app
    socketio.init_app(app)

    # Robust initialization of extensions and middleware
    try:
        init_extensions(app)
        # Check DB after extensions initialized
        check_db_health()
        print("[OK] Core extensions initialized")
    except Exception as e:
        print(f"[WARN] Some extensions failed to initialize: {e}")

    try:
        register_blueprints(app)
        print("[OK] Blueprints registered")
    except Exception as e:
        print(f"[ERROR] Blueprint registration failed: {e}")

    # Print registered routes for debugging
    with app.app_context():
        print("=== REGISTERED ROUTES ===")
        for rule in app.url_map.iter_rules():
            print(f"{rule.methods} {rule}")
        print("=========================")

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
        app.register_blueprint(health.health_bp, url_prefix='/api/v1/health')
    except Exception as e:
        print(f"Blueprint registration partial failure: {e}")
