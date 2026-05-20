"""
Angel One Standardized Client
=============================
Provides a singleton SmartConnect client and async execution wrapper.
"""

import asyncio
import logging
import os
from typing import Any, Callable, Optional, Dict
from SmartApi import SmartConnect
from app.config import config

logger = logging.getLogger('angelone.api')

def get_settings():
    """Get active configuration settings."""
    env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])

class AngelOneClient:
    """
    Standardized wrapper for Angel One SmartApi.
    Provides async execution of synchronous API calls.
    """
    
    def __init__(self):
        settings = get_settings()
        self.api_key = getattr(settings, 'ANGELONE_API_KEY', os.environ.get('ANGELONE_API_KEY', ''))
        self.client_id = getattr(settings, 'ANGELONE_CLIENT_ID', os.environ.get('ANGELONE_CLIENT_ID', ''))
        self.password = getattr(settings, 'ANGELONE_MPIN', os.environ.get('ANGELONE_MPIN', ''))
        self.totp_secret = getattr(settings, 'ANGELONE_TOTP_SECRET', os.environ.get('ANGELONE_TOTP_SECRET', ''))
        
        self.smart_api = SmartConnect(api_key=self.api_key)
        logger.info("AngelOneClient wrapper initialized")
        
    async def execute_async(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a synchronous SmartApi function in an async-friendly way.
        Uses the default thread pool executor.
        """
        loop = asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(None, lambda: func(*args, **kwargs))
        except Exception as e:
            logger.error(f"Angel One API execution error: {str(e)}")
            raise

    # ─── COMPATIBILITY METHODS ────────────────────────────────────────────────
    # These methods proxy to smart_api and handle session restoration if possible.
    # Note: These are synchronous for backward compatibility with endpoints.py.

    def _execute_sync(self, func, *args, **kwargs) -> Dict:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"API call failed: {e}")
            return {'status': False, 'message': str(e)}

    def get_profile(self, refresh_token: str = None):
        token = refresh_token or getattr(self.smart_api, 'refresh_token', None)
        return self._execute_sync(self.smart_api.getProfile, token)

    def get_funds(self):
        return self._execute_sync(self.smart_api.rmsLimit)

    def place_order(self, params):
        return self._execute_sync(self.smart_api.placeOrder, params)

    def modify_order(self, params):
        return self._execute_sync(self.smart_api.modifyOrder, params)

    def cancel_order(self, order_id, variety='NORMAL'):
        return self._execute_sync(self.smart_api.cancelOrder, order_id, variety)

    def get_order_book(self):
        return self._execute_sync(self.smart_api.orderBook)

    def get_trade_book(self):
        return self._execute_sync(self.smart_api.tradeBook)

    def get_positions(self):
        return self._execute_sync(self.smart_api.position)

    def get_holdings(self):
        return self._execute_sync(self.smart_api.holding)

    def get_ltp(self, exchange, symbol, token):
        return self._execute_sync(self.smart_api.ltpData, exchange, symbol, token)

    def get_historical_data(self, params):
        return self._execute_sync(self.smart_api.getCandleData, params)

# Singleton instance management
_client_instance: Optional[AngelOneClient] = None
_client_init_error: Optional[Exception] = None

def get_client() -> AngelOneClient:
    """
    Get or create the AngelOneClient singleton instance.
    """
    global _client_instance, _client_init_error
    if _client_instance is None:
        try:
            _client_instance = AngelOneClient()
        except Exception as e:
            logger.error(f"Critical error initializing AngelOne client: {e}")
            import traceback
            logger.error(traceback.format_exc())
            _client_init_error = e
            raise
    return _client_instance

# Global alias for convenience
api_client = get_client()
