import logging
from flask_cors import CORS

logger = logging.getLogger('trading_app')

def init_cors(app):
    """
    Initialize CORS with explicit origins to support credentials and preflight requests.
    """
    CORS(
        app,
        resources={r"/api/*": {"origins": [
            "http://localhost:5173",
            "https://ait-flame.vercel.app"
        ]}},
        supports_credentials=True
    )
    
    logger.info("CORS initialized explicitly for localhost and Vercel.")
