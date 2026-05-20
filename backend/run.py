import eventlet
eventlet.monkey_patch()

import os
import sys
import logging
from dotenv import load_dotenv

# Add current directory and its parent to path to handle various import styles
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Load environment variables
load_dotenv()

from app import create_app, socketio

app = create_app()

@app.route("/")
def health_check_root():
    return {
        "status": "running",
        "service": "AIT Trading Platform",
        "environment": os.environ.get("FLASK_ENV", "production")
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    
    print("Starting Flask application via socketio.run...")
    print(f"PORT: {port}")
    print(f"ENV: {os.environ.get('FLASK_ENV', 'production')}")

    socketio.run(
        app,
        host="0.0.0.0",
        port=port,
        debug=False,
        allow_unsafe_werkzeug=True
    )
