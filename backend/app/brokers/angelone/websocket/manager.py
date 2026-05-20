"""
Angel One WebSocket Manager
===========================
Enterprise-grade websocket manager for live ticks.
Supports auto-reconnect, subscription management, and integration with the market data engine.
"""

import threading
import logging
import time
from typing import Dict, List, Set, Optional
from SmartApi.smartWebSocketV2 import SmartWebSocketV2
from ..auth.session import session_manager

logger = logging.getLogger('angelone.websocket')

class AngelOneWebSocket:
    """Manages SmartWebSocketV2 connection for live market data."""
    
    def __init__(self):
        self.session = session_manager
        self.ws: Optional[SmartWebSocketV2] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._subscriptions: Set[str] = set()
        
    def start(self):
        """Initialize and start the websocket connection."""
        if self._running:
            return
            
        if not self.session.is_connected:
            if not self.session.check_and_restore_session():
                logger.error("Cannot start WebSocket: Not connected to Angel One")
                return

        try:
            self.ws = SmartWebSocketV2(
                self.session.jwt_token,
                self.session.api_key,
                self.session.client_id,
                self.session.feed_token
            )
            
            # Assign callbacks
            self.ws.on_data = self._on_data
            self.ws.on_open = self._on_open
            self.ws.on_error = self._on_error
            self.ws.on_close = self._on_close
            
            self._running = True
            
            # Run in background thread
            self._thread = threading.Thread(target=self._run_ws, daemon=True)
            self._thread.start()
            
            logger.info("Angel One WebSocket initialization started")
        except Exception as e:
            logger.error(f"Failed to start Angel One WebSocket: {e}")
            self._running = False

    def _run_ws(self):
        """Blocking call to start websocket."""
        while self._running:
            try:
                self.ws.connect()
            except Exception as e:
                logger.error(f"WebSocket connection dropped: {e}")
                
            if self._running:
                logger.info("Reconnecting WebSocket in 5 seconds...")
                time.sleep(5)
                # Attempt token renewal before reconnecting
                self.session.check_and_restore_session()
                # Re-initialize websocket instance with potentially new tokens
                self.ws = SmartWebSocketV2(
                    self.session.jwt_token,
                    self.session.api_key,
                    self.session.client_id,
                    self.session.feed_token
                )
                self.ws.on_data = self._on_data
                self.ws.on_open = self._on_open
                self.ws.on_error = self._on_error
                self.ws.on_close = self._on_close

    def stop(self):
        """Stop websocket connection."""
        self._running = False
        if self.ws:
            try:
                self.ws.close_connection()
            except Exception:
                pass
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        logger.info("Angel One WebSocket stopped")

    def subscribe(self, exchange: str, symbol_token: str, mode: int = 1):
        """
        Subscribe to symbol.
        mode: 1 (LTP), 2 (Quote), 3 (SnapQuote)
        """
        token_str = f"{exchange}|{symbol_token}"
        self._subscriptions.add(token_str)
        
        if self.ws and self._running:
            try:
                self.ws.subscribe("my_correlation_id", mode, [{"exchangeType": 1, "tokens": [symbol_token]}])
                logger.info(f"Subscribed to {token_str}")
            except Exception as e:
                logger.error(f"Subscription failed: {e}")

    # ─── CALLBACKS ────────────────────────────────────────────────────────────

    def _on_data(self, ws, message):
        """Handle incoming tick data."""
        try:
            # Here we would integrate with the app's market_data engine
            # e.g., market_data_engine.process_tick(message)
            pass
        except Exception as e:
            logger.error(f"Error processing websocket data: {e}")

    def _on_open(self, ws):
        """Handle connection open."""
        logger.info("Angel One WebSocket Connected")
        # Resubscribe to existing tokens
        if self._subscriptions:
            logger.info("Restoring subscriptions...")
            # For simplicity, assuming NSE equity (exchangeType=1)
            tokens = [t.split('|')[1] for t in self._subscriptions if '|' in t]
            if tokens:
                try:
                    self.ws.subscribe("reconnect_corr", 1, [{"exchangeType": 1, "tokens": tokens}])
                except Exception as e:
                    logger.error(f"Failed to resubscribe: {e}")

    def _on_error(self, ws, error):
        """Handle connection error."""
        logger.error(f"Angel One WebSocket Error: {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        """Handle connection close."""
        logger.warning(f"Angel One WebSocket Closed: {close_status_code} - {close_msg}")

ws_manager = AngelOneWebSocket()
