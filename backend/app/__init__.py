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
from flask_socketio import SocketIO, emit
socketio = SocketIO(
    cors_allowed_origins=[
        "https://ait-flame.vercel.app",
        "http://localhost:5173"
    ],
    async_mode="eventlet",
    logger=True,
    engineio_logger=True,
    ping_timeout=180,
    ping_interval=60
)

def check_environment():
    """Verify all required environment variables exist."""
    required_vars = [
        "MONGO_URI", "JWT_SECRET_KEY", "SECRET_KEY",
        "ANGEL_API_KEY", "ANGEL_CLIENT_ID", "ANGEL_TOTP_SECRET"
    ]
    missing = [var for var in required_vars if not os.environ.get(var)]
    if missing:
        print(f"[CRITICAL] Missing environment variables: {', '.join(missing)}", flush=True)
    else:
        print("[OK] All critical environment variables present", flush=True)

def check_db_health():
    """Test the DB connection."""
    from .database.connection import get_db
    try:
        db = get_db()
        if db is not None:
            # For MongoDB, we can try a list_collection_names or similar light operation
            db.list_collection_names()
            print("[OK] Database connection verified", flush=True)
            return True
        else:
            print("[CRITICAL] Database connection failed (get_db returned None)", flush=True)
            return False
    except Exception as e:
        print(f"[CRITICAL] Database health check failed: {e}", flush=True)
        return False

def create_app(config_name: str = None) -> Flask:
    """
    Create and configure Flask application in a failsafe manner.
    """
    print("Starting Flask app factory...", flush=True)
    
    # Run startup checks
    check_environment()
    
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'production')

    app = Flask(__name__)
    
    # Initialize CORS explicitly
    try:
        init_cors(app)
        print("[OK] CORS initialized", flush=True)
    except Exception as e:
        print(f"[CRITICAL] CORS initialization failed: {e}", flush=True)

    # Handle configuration gracefully
    try:
        if config_name in config:
            app.config.from_object(config[config_name])
        else:
            app.config.from_object(config['production'])
    except Exception as e:
        print(f"Config loading failed: {e}", flush=True)

    # Register middleware (CORS, Security, etc.) IMMEDIATELY after config
    try:
        from .middleware import register_middleware
        register_middleware(app)
        print("[OK] Middleware registered", flush=True)
    except Exception as e:
        print(f"[CRITICAL] Middleware registration failed: {e}", flush=True)

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

    @socketio.on('ping')
    def handle_ping():
        """Handle ping from client and return heartbeat with timestamp."""
        import datetime
        emit('heartbeat', {
            'status': 'ok', 
            'timestamp': datetime.datetime.utcnow().isoformat()
        })

    @socketio.on('heartbeat')
    def handle_heartbeat(data):
        """Handle heartbeat from client and return heartbeat_ack."""
        emit('heartbeat_ack', {'status': 'ok'})

    # JWT Error Handlers
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        print(f"[JWT] Invalid token: {error}", flush=True)
        return jsonify({
            "success": False, 
            "error": "invalid_token",
            "message": f"Invalid token: {error}"
        }), 422

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_data):
        print(f"[JWT] Token expired: {jwt_data}", flush=True)
        return jsonify({
            "success": False, 
            "error": "token_expired",
            "message": "Token has expired"
        }), 401

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        print(f"[JWT] Missing token: {error}", flush=True)
        return jsonify({
            "success": False, 
            "error": "unauthorized",
            "message": f"Missing authorization header: {error}"
        }), 401

    # Robust initialization of extensions and middleware
    try:
        init_extensions(app)
        # Check DB after extensions initialized
        check_db_health()
        print("[OK] Core extensions initialized", flush=True)
    except Exception as e:
        import traceback
        print(f"[CRITICAL] Extensions failed: {e}", flush=True)
        traceback.print_exc()

    try:
        register_blueprints(app)
        print("[OK] Blueprints registered", flush=True)
    except Exception as e:
        print(f"[ERROR] Blueprint registration failed: {e}", flush=True)

    # Print registered routes for debugging
    with app.app_context():
        print("=== REGISTERED ROUTES ===", flush=True)
        for rule in app.url_map.iter_rules():
            print(f"{rule.methods} {rule}", flush=True)
        print("=========================", flush=True)

    print("Application initialized successfully", flush=True)
    return app


def register_blueprints(app: Flask) -> None:
    """Register all API blueprints with individual safety checks."""

    def safe_register(import_func, name):
        try:
            import_func()
            print(f"[OK] Blueprint registered: {name}", flush=True)
        except Exception as e:
            print(f"[ERROR] Failed to register blueprint '{name}': {e}", flush=True)
            import traceback
            traceback.print_exc()

    def reg_angelone():
        from .brokers.angelone import angelone_bp
        app.register_blueprint(angelone_bp, url_prefix='/api/v1/broker/angelone')

    def reg_auth():
        from .api import auth
        app.register_blueprint(auth.bp, url_prefix='/api/v1/auth')

    def reg_strategies():
        from .api import strategies
        app.register_blueprint(strategies.bp, url_prefix='/api/v1/strategies')

    def reg_trades():
        from .api import trades
        app.register_blueprint(trades.bp, url_prefix='/api/v1/trades')

    def reg_orders():
        from .api import orders
        app.register_blueprint(orders.bp, url_prefix='/api/v1/orders')

    def reg_watchlist():
        from .api import watchlist
        app.register_blueprint(watchlist.bp, url_prefix='/api/v1/watchlists')

    def reg_signals():
        from .api import ai_signals
        app.register_blueprint(ai_signals.bp, url_prefix='/api/v1/signals')

    def reg_notifications():
        from .api import notifications
        app.register_blueprint(notifications.bp, url_prefix='/api/v1/notifications')

    def reg_funds():
        from .api import funds
        app.register_blueprint(funds.bp, url_prefix='/api/v1/funds')

    def reg_bot():
        from .api import bot
        app.register_blueprint(bot.bp, url_prefix='/api/v1/bot')

    def reg_broker():
        from .api import broker
        app.register_blueprint(broker.bp, url_prefix='/api/v1/broker')

    def reg_backtest():
        from .api import backtest
        app.register_blueprint(backtest.bp, url_prefix='/api/v1/backtest')

    def reg_market():
        from .api import market
        app.register_blueprint(market.bp, url_prefix='/api/v1/market')

    def reg_trading_engine():
        from .api import trading_engine
        app.register_blueprint(trading_engine.bp, url_prefix='/api/v1/positions', name='positions_bp')
        app.register_blueprint(trading_engine.bp, url_prefix='/api/v1/trading', name='trading_bp')
        app.register_blueprint(trading_engine.bp, url_prefix='/api/v1/trading/positions', name='trading_positions_bp')

    def reg_settings():
        from .api import settings
        app.register_blueprint(settings.bp, url_prefix='/api/v1/settings')

    def reg_dashboard():
        from .api import dashboard
        app.register_blueprint(dashboard.bp, url_prefix='/api/v1/dashboard')

    def reg_health():
        from .api import health
        app.register_blueprint(health.health_bp, url_prefix='/api/v1/health')

    safe_register(reg_angelone, "angelone")
    safe_register(reg_auth, "auth")
    safe_register(reg_strategies, "strategies")
    safe_register(reg_trades, "trades")
    safe_register(reg_orders, "orders")
    safe_register(reg_watchlist, "watchlist")
    safe_register(reg_signals, "ai_signals")
    safe_register(reg_notifications, "notifications")
    safe_register(reg_funds, "funds")
    safe_register(reg_bot, "bot")
    safe_register(reg_broker, "broker")
    safe_register(reg_backtest, "backtest")
    safe_register(reg_market, "market")
    safe_register(reg_trading_engine, "trading_engine")
    safe_register(reg_settings, "settings")
    safe_register(reg_dashboard, "dashboard")
    safe_register(reg_health, "health")
