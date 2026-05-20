import asyncio
from fastapi import FastAPI
from .routes import auth_routes, order_routes, market_routes, portfolio_routes
from .websocket.manager import ws_manager
from .utils.logger import get_logger

logger = get_logger(__name__)

class AngelOneManager:
    """
    Main integration manager. Binds routes to FastAPI app and controls lifecycle.
    """
    def __init__(self, app: FastAPI):
        self.app = app
        self._register_routes()

    def _register_routes(self):
        self.app.include_router(auth_routes.router)
        self.app.include_router(order_routes.router)
        self.app.include_router(market_routes.router)
        self.app.include_router(portfolio_routes.router)
        logger.info("Angel One routes registered.")

    async def start(self):
        """
        Start websocket and other background tasks.
        """
        logger.info("Starting Angel One integration...")
        ws_manager.connect()

    async def stop(self):
        """
        Graceful shutdown.
        """
        logger.info("Stopping Angel One integration...")
        ws_manager.disconnect()

# To use this in main.py:
# from brokers.angelone.manager import AngelOneManager
# angel_manager = AngelOneManager(app)
# @app.on_event("startup")
# async def startup():
#     await angel_manager.start()
# @app.on_event("shutdown")
# async def shutdown():
#     await angel_manager.stop()
