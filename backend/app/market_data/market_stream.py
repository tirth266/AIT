"""
Subscription Manager
====================
Manages market data subscriptions and broadcasts.
"""

import logging
import threading
from typing import Dict, Set, List, Callable
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger('trading_app')


@dataclass
class Subscription:
    """Market data subscription."""
    session_id: str
    symbol: str
    channels: Set[str] = field(default_factory=set)
    subscribed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SubscriptionManager:
    """Manages market data subscriptions."""

    def __init__(self):
        self._subscriptions: Dict[str, Dict[str, Subscription]] = defaultdict(dict)
        self._symbol_subscribers: Dict[str, Set[str]] = defaultdict(set)
        self._lock = threading.RLock()
        logger.info("SubscriptionManager initialized")

    def subscribe(self, session_id: str, symbol: str, channels: Set[str] = None) -> bool:
        """Subscribe a session to a symbol's market data."""
        with self._lock:
            symbol = symbol.upper()
            
            if channels is None:
                channels = {'quotes', 'candles', 'depth', 'indicators'}
            
            if symbol not in self._subscriptions[session_id]:
                self._subscriptions[session_id][symbol] = Subscription(
                    session_id=session_id,
                    symbol=symbol,
                    channels=channels
                )
            else:
                self._subscriptions[session_id][symbol].channels.update(channels)
            
            self._symbol_subscribers[symbol].add(session_id)
            
            logger.debug(f"Session {session_id} subscribed to {symbol} on channels {channels}")
            return True

    def unsubscribe(self, session_id: str, symbol: str = None):
        """Unsubscribe a session from a symbol or all symbols."""
        with self._lock:
            if symbol:
                symbol = symbol.upper()
                if symbol in self._subscriptions[session_id]:
                    del self._subscriptions[session_id][symbol]
                    self._symbol_subscribers[symbol].discard(session_id)
            else:
                if session_id in self._subscriptions:
                    for sym in list(self._subscriptions[session_id].keys()):
                        self._symbol_subscribers[sym].discard(session_id)
                    del self._subscriptions[session_id]

    def get_subscribed_symbols(self, session_id: str) -> List[str]:
        """Get symbols a session is subscribed to."""
        with self._lock:
            return list(self._subscriptions.get(session_id, {}).keys())

    def get_subscribers(self, symbol: str) -> Set[str]:
        """Get sessions subscribed to a symbol."""
        with self._lock:
            return self._symbol_subscribers.get(symbol.upper(), set()).copy()

    def get_subscription_count(self, symbol: str = None) -> int:
        """Get number of subscriptions."""
        with self._lock:
            if symbol:
                return len(self._symbol_subscribers.get(symbol.upper(), set()))
            return sum(len(subs) for subs in self._subscriptions.values())

    def is_subscribed(self, session_id: str, symbol: str) -> bool:
        """Check if session is subscribed to symbol."""
        with self._lock:
            return symbol.upper() in self._subscriptions.get(session_id, {})


_subscription_manager = SubscriptionManager()


def get_subscription_manager() -> SubscriptionManager:
    """Get the global subscription manager instance."""
    return _subscription_manager