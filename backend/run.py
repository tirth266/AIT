"""
Backend Entry Point
===================
Start the Flask + Flask-SocketIO server with threading mode.

Usage:
    python run.py          # uses .env in this directory
    PORT=8080 python run.py
"""

import os
import sys
import logging

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# ── 1. Load .env BEFORE importing the app ──────────────────────────────────────
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# ── 2. Server configuration ───────────────────────────────────────────────────
port = int(os.environ.get('PORT', 10000))
DEBUG = os.environ.get('FLASK_DEBUG', '0') == '1'

# ── 3. Setup logging ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# ── 4. Import app + socketio ───────────────────────────────────────────────────
from app import app, socketio

print("\n!!! RUN.PY EXECUTING - VERSION 1.0.2 !!!\n")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))

    socketio.run(
        app,
        host="0.0.0.0",
        port=port,
        debug=False
    )