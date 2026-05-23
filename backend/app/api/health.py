import os
import logging
import traceback
from datetime import datetime
from flask import Blueprint, jsonify

from app.database.connection import get_db

logger = logging.getLogger('trading_app')

health_bp = Blueprint("health", __name__)

@health_bp.route("/ping")
def ping():
    """Simple ping for keep-alive."""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat()
    })

@health_bp.route("/status")
def health_check():
    """Comprehensive health check."""
    try:
        # Avoid circular import by importing here
        from app import START_TIME
    except ImportError:
        START_TIME = datetime.utcnow()
    
    db_status = "error"
    db_msg = "unknown"
    try:
        db = get_db()
        if db is not None:
            # list_collection_names is a safe way to test connection
            db.list_collection_names()
            db_status = "ok"
            db_msg = "connected"
        else:
            db_msg = "connection_returned_none"
    except Exception as e:
        db_msg = str(e)
        logger.error(f"Health check DB failure: {e}")
        # logger.error(traceback.format_exc())

    # Environment check
    required_vars = [
        "MONGO_URI", "JWT_SECRET_KEY", "SECRET_KEY",
        "ANGEL_API_KEY", "ANGEL_CLIENT_ID", "ANGEL_TOTP_SECRET"
    ]
    env_status = {}
    for var in required_vars:
        env_status[var] = "present" if os.environ.get(var) else "missing"

    uptime = datetime.utcnow() - START_TIME

    return jsonify({
        "status": "ok" if db_status == "ok" else "degraded",
        "database": {
            "status": db_status,
            "message": db_msg
        },
        "environment": env_status,
        "flask_env": os.environ.get('FLASK_ENV', 'unknown'),
        "uptime_seconds": int(uptime.total_seconds()),
        "timestamp": datetime.utcnow().isoformat()
    })
