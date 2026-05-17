"""
WebSocket Tick Integration for Zerodha Kite Connect
====================================================
Real-time market data streaming with reconnection handling.
"""

import logging
import asyncio
import threading
import time
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Callable, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque

from websocket import create_connection, WebSocketTimeoutException, WebSocketBadStatusException

from .auth import TokenManager
from .models import ZerodhaTick

logger = logging.getLogger('zerodha.websocket')


class WebSocketState(str, Enum):
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    RECONNECTING = "RECONNECTING"
    ERROR = "ERROR"


@dataclass
class WebSocketConfig:
    url: str = "wss://ws.kite.trade"
    reconnect_delay: float = 1.0
    max_reconnect_delay: float = 60.0
    ping_interval: float = 10.0
    ping_timeout: float = 5.0
    max_retries: int = 10
    heartbeat_interval: float = 30.0


@dataclass
class Subscription:
    instrument_tokens: Set[int]
    callback: Optional[Callable[[ZerodhaTick], None]] = None
    symbols: Dict[int, str] = field(default_factory=dict)


class KiteWebSocket:
    """
    WebSocket client for real-time tick data from Zerodha.
    """

    def __init__(
        self,
        token_manager: TokenManager,
        api_key: str,
        config: Optional[WebSocketConfig] = None,
    ):
        self.token_manager = token_manager
        self.api_key = api_key
        self.config = config or WebSocketConfig()

        self._ws = None
        self._state = WebSocketState.DISCONNECTED
        self._lock = threading.Lock()
        self._running = False

        self._subscribed_tokens: Set[int] = set()
        self._subscriptions: Dict[int, List[Callable]] = defaultdict(list)
        self._symbols: Dict[int, str] = {}

        self._reconnect_count = 0
        self._last_connected: Optional[datetime] = None
        self._last_error: Optional[str] = None

        self._on_ticks: Optional[Callable[[List[ZerodhaTick]], None]] = None
        self._on_order_update: Optional[Callable[[Dict], None]] = None
        self._on_connection_change: Optional[Callable[[WebSocketState], None]] = None
        self._on_error: Optional[Callable[[str], None]] = None

        self._tick_buffer: deque = deque(maxlen=1000)
        self._order_update_buffer: deque = deque(maxlen=500)

        self._thread: Optional[threading.Thread] = None
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None

    def set_ticks_callback(self, callback: Callable[[List[ZerodhaTick]], None]) -> None:
        self._on_ticks = callback

    def set_order_update_callback(self, callback: Callable[[Dict], None]) -> None:
        self._on_order_update = callback

    def set_connection_callback(self, callback: Callable[[WebSocketState], None]) -> None:
        self._on_connection_change = callback

    def set_error_callback(self, callback: Callable[[str], None]) -> None:
        self._on_error = callback

    def connect(self, use_thread: bool = True) -> bool:
        with self._lock:
            if self._state in [WebSocketState.CONNECTING, WebSocketState.CONNECTED]:
                logger.warning("WebSocket already connected or connecting")
                return True

            self._running = True

            if use_thread:
                self._thread = threading.Thread(target=self._run_websocket, daemon=True)
                self._thread.start()
                return True

            return self._connect_sync()

    def _connect_sync(self) -> bool:
        try:
            access_token = self.token_manager.access_token
            if not access_token:
                raise ValueError("No access token available")

            url = f"{self.config.url}?api_key={self.api_key}&access_token={access_token}&v=3"

            self._ws = create_connection(
                url,
                timeout=self.config.ping_timeout + 5,
            )

            self._state = WebSocketState.CONNECTED
            self._reconnect_count = 0
            self._last_connected = datetime.now(timezone.utc)

            logger.info("WebSocket connected successfully")

            self._trigger_connection_callback(WebSocketState.CONNECTED)

            self._subscribe_all()

            return True

        except Exception as e:
            self._state = WebSocketState.ERROR
            self._last_error = str(e)
            logger.error(f"WebSocket connection failed: {e}")
            self._trigger_error_callback(str(e))
            return False

    def _run_websocket(self) -> None:
        while self._running:
            try:
                if not self._connect_sync():
                    self._handle_disconnect()
                    continue

                self._receive_loop()

            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                self._last_error = str(e)
                self._trigger_error_callback(str(e))

            if self._running:
                self._handle_disconnect()

    def _receive_loop(self) -> None:
        while self._running and self._ws and self._ws.connected:
            try:
                message = self._ws.recv()

                if not message:
                    continue

                self._process_message(message)

            except WebSocketTimeoutException:
                continue

            except Exception as e:
                if self._running:
                    logger.error(f"WebSocket receive error: {e}")
                break

    def _process_message(self, message: str) -> None:
        try:
            data = json.loads(message)

            message_type = data.get("type")

            if message_type == "tick":
                ticks_data = data.get("data", [])
                ticks = []

                for tick_data in ticks_data:
                    tick = ZerodhaTick.from_zerodha_ticker(tick_data)
                    if tick:
                        if tick.instrument_token in self._symbols:
                            tick.tradingsymbol = self._symbols[tick.instrument_token]
                        ticks.append(tick)
                        self._tick_buffer.append(tick)

                        for callback in self._subscriptions.get(tick.instrument_token, []):
                            try:
                                callback(tick)
                            except Exception as e:
                                logger.error(f"Tick callback error: {e}")

                if ticks and self._on_ticks:
                    self._on_ticks(ticks)

            elif message_type == "order":
                order_data = data.get("data", {})
                self._order_update_buffer.append(order_data)

                if self._on_order_update:
                    self._on_order_update(order_data)

            elif message_type == "error":
                error_data = data.get("data", {})
                error_message = error_data.get("message", "Unknown error")
                logger.error(f"WebSocket server error: {error_message}")
                self._trigger_error_callback(error_message)

            elif message_type == "close":
                logger.warning("WebSocket connection closed by server")

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON message: {e}")

        except Exception as e:
            logger.error(f"Message processing error: {e}")

    def subscribe(self, instrument_tokens: List[int]) -> bool:
        if self._state != WebSocketState.CONNECTED:
            logger.warning(f"Cannot subscribe - WebSocket not connected (state: {self._state})")
            return False

        new_tokens = set(instrument_tokens) - self._subscribed_tokens

        if not new_tokens:
            return True

        try:
            subscribe_data = {
                "type": "subscribe",
                "instruments": [f"N:{token}" for token in new_tokens],
            }

            self._ws.send(json.dumps(subscribe_data))

            self._subscribed_tokens.update(new_tokens)

            logger.info(f"Subscribed to {len(new_tokens)} instruments")
            return True

        except Exception as e:
            logger.error(f"Subscription failed: {e}")
            return False

    def unsubscribe(self, instrument_tokens: List[int]) -> bool:
        if self._state != WebSocketState.CONNECTED:
            return False

        tokens_to_remove = set(instrument_tokens) & self._subscribed_tokens

        if not tokens_to_remove:
            return True

        try:
            unsubscribe_data = {
                "type": "unsubscribe",
                "instruments": [f"N:{token}" for token in tokens_to_remove],
            }

            self._ws.send(json.dumps(unsubscribe_data))

            self._subscribed_tokens -= tokens_to_remove

            logger.info(f"Unsubscribed from {len(tokens_to_remove)} instruments")
            return True

        except Exception as e:
            logger.error(f"Unsubscription failed: {e}")
            return False

    def _subscribe_all(self) -> None:
        if self._subscribed_tokens:
            subscribe_data = {
                "type": "subscribe",
                "instruments": [f"N:{token}" for token in self._subscribed_tokens],
            }

            if self._ws:
                self._ws.send(json.dumps(subscribe_data))

    def register_symbols(self, symbols: Dict[int, str]) -> None:
        self._symbols.update(symbols)

    def add_tick_listener(self, instrument_token: int, callback: Callable[[ZerodhaTick], None]) -> None:
        self._subscriptions[instrument_token].append(callback)

    def remove_tick_listener(self, instrument_token: int, callback: Callable[[ZerodhaTick], None]) -> None:
        if callback in self._subscriptions[instrument_token]:
            self._subscriptions[instrument_token].remove(callback)

    def disconnect(self) -> None:
        self._running = False

        with self._lock:
            if self._ws:
                try:
                    self._ws.close()
                except Exception:
                    pass

                self._ws = None

        self._state = WebSocketState.DISCONNECTED
        self._trigger_connection_callback(WebSocketState.DISCONNECTED)

        logger.info("WebSocket disconnected")

    def _handle_disconnect(self) -> None:
        self._state = WebSocketState.RECONNECTING
        self._trigger_connection_callback(WebSocketState.RECONNECTING)

        if self._reconnect_count >= self.config.max_retries:
            logger.error(f"Max reconnection attempts ({self.config.max_retries}) reached")
            self._state = WebSocketState.ERROR
            self._trigger_connection_callback(WebSocketState.ERROR)
            return

        self._reconnect_count += 1
        delay = min(self.config.reconnect_delay * (2 ** (self._reconnect_count - 1)), self.config.max_reconnect_delay)

        logger.info(f"Reconnecting in {delay:.1f}s (attempt {self._reconnect_count}/{self.config.max_retries})")

        time.sleep(delay)

    def _trigger_connection_callback(self, state: WebSocketState) -> None:
        if self._on_connection_change:
            try:
                self._on_connection_change(state)
            except Exception as e:
                logger.error(f"Connection callback error: {e}")

    def _trigger_error_callback(self, error: str) -> None:
        if self._on_error:
            try:
                self._on_error(error)
            except Exception as e:
                logger.error(f"Error callback error: {e}")

    @property
    def state(self) -> WebSocketState:
        return self._state

    @property
    def is_connected(self) -> bool:
        return self._state == WebSocketState.CONNECTED

    @property
    def subscribed_count(self) -> int:
        return len(self._subscribed_tokens)

    def get_recent_ticks(self, count: int = 100) -> List[ZerodhaTick]:
        return list(self._tick_buffer)[-count:]

    def get_order_updates(self, count: int = 50) -> List[Dict]:
        return list(self._order_update_buffer)[-count:]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "state": self._state.value,
            "subscribed_count": len(self._subscribed_tokens),
            "reconnect_count": self._reconnect_count,
            "last_connected": self._last_connected.isoformat() if self._last_connected else None,
            "tick_buffer_size": len(self._tick_buffer),
            "order_update_buffer_size": len(self._order_update_buffer),
            "last_error": self._last_error,
        }


_websocket_instance: Optional[KiteWebSocket] = None


def get_kite_websocket(token_manager: Optional[TokenManager] = None, api_key: str = "") -> KiteWebSocket:
    global _websocket_instance

    if _websocket_instance is None:
        from .auth import get_token_manager
        from ...config import Config

        tm = token_manager or get_token_manager()
        key = api_key or Config.KITE_API_KEY or ""

        _websocket_instance = KiteWebSocket(token_manager=tm, api_key=key)

    return _websocket_instance