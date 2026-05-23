import os
import time
import logging
from flask import Blueprint, jsonify
from datetime import datetime

logger = logging.getLogger('trading_app')

health_bp = Blueprint("health", __name__)
START_TIME = time.time()

@health_bp.route("/status")
def status():
    """Safe health check endpoint that never crashes."""
    # 1. Check required environment variables
    required_vars = ["MONGO_URI", "JWT_SECRET_KEY", "SECRET_KEY", "ANGEL_API_KEY"]
    env_status = {var: "present" if os.environ.get(var) else "MISSING" for var in required_vars}

    # 2. Check Database Connection safely
    db_status = "unknown"
    try:
        from app.extensions import get_mongo_db
        db = get_mongo_db()
        if db is not None:
            # Simple ping to verify connection
            db.command("ping")
            db_status = "connected"
        else:
            db_status = "error: db_is_none"
    except Exception as e:
        db_status = f"error: {str(e)}"
        logger.error(f"Health status DB check failed: {e}")

    # 3. Calculate Uptime
    uptime = time.time() - START_TIME

    return jsonify({
        "status": "ok",
        "uptime_seconds": round(uptime, 2),
        "database": db_status,
        "environment": env_status,
        "flask_env": os.environ.get("FLASK_ENV", "not set"),
        "timestamp": datetime.utcnow().isoformat()
    }), 200

@health_bp.route("/ping")
def ping():
    """Ultra-lightweight ping for keep-alive."""
    return jsonify({"status": "ok"}), 200
