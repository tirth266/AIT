import os
import sys
import logging
from dotenv import load_dotenv

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

from app import create_app, socketio

app = create_app()

@app.route("/")
def home():
    return {
        "status": "running",
        "service": "AIT Trading Platform"
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    
    print("Starting Flask application...")
    print(f"PORT: {port}")
    print(f"ENV: {os.environ.get('FLASK_ENV', 'production')}")

    socketio.run(
        app,
        host="0.0.0.0",
        port=port,
        debug=False,
        allow_unsafe_werkzeug=True
    )
