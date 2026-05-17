"""
Heartbeat Optimization and Reconnect Handling
==============================================
Optimized heartbeat system with adaptive intervals, connection state management,
and automatic reconnection handling.
"""

import os
import logging
import time
import asyncio
import threading
import random
from typing import Dict, Optional, Callable, List, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class ConnectionStatus(Enum):
    CONNECTING = "connecting"
    CONNECTED = "connected"
    STALE = "stale"
    RECONNECTING = "reconnecting"
    DISCONNECTED = "disconnected"


@dataclass
class HeartbeatState:
    """Heartbeat state for a connection."""
    sid: str
    user_id: str
    last_ping: float
    last_pong: float
    ping_interval: float
    timeout: float
    missed_pings: int = 0
    status: ConnectionStatus = ConnectionStatus.CONNECTING


class AdaptiveHeartbeat:
    """
    Adaptive heartbeat system that adjusts ping intervals based on connection health.
    """

    DEFAULT_PING_INTERVAL = 25
    DEFAULT_TIMEOUT = 60
    MIN_INTERVAL = 10
    MAX_INTERVAL = 60

    def __init__(
        self,
        on_timeout: Callable[[str], None] = None,
        on_stale: Callable[[str], None] = None,
        stats_callback: Callable[[Dict], None] = None
    ):
        self._heartbeats: Dict[str, HeartbeatState] = {}
        self._lock = threading.Lock()
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None
        self._check_interval = 5

        self._on_timeout = on_timeout
        self._on_stale = on_stale
        self._stats_callback = stats_callback

        self._latency_samples: Dict[str, List[float]] = defaultdict(list)
        self._avg_latency: Dict[str, float] = {}
        self._max_latency_samples = 10

    def start(self):
        """Start heartbeat monitor."""
        if self._running:
            return
        self._running = True
        self._worker_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._worker_thread.start()
        logger.info("Heartbeat monitor started")

    def stop(self):
        """Stop heartbeat monitor."""
        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=2)
        logger.info("Heartbeat monitor stopped")

    def register(self, sid: str, user_id: str) -> float:
        """Register new connection for heartbeat."""
        with self._lock:
            self._heartbeats[sid] = HeartbeatState(
                sid=sid,
                user_id=user_id,
                last_ping=time.time(),
                last_pong=time.time(),
                ping_interval=self.DEFAULT_PING_INTERVAL,
                timeout=self.DEFAULT_TIMEOUT,
                status=ConnectionStatus.CONNECTED
            )
            return self.DEFAULT_PING_INTERVAL

    def unregister(self, sid: str):
        """Unregister connection from heartbeat."""
        with self._lock:
            self._heartbeats.pop(sid, None)
            self._latency_samples.pop(sid, None)
            self._avg_latency.pop(sid, None)

    def record_ping(self, sid: str):
        """Record ping sent to client."""
        with self._lock:
            if sid in self._heartbeats:
                self._heartbeats[sid].last_ping = time.time()

    def record_pong(self, sid: str, client_timestamp: float = None):
        """Record pong received from client."""
        now = time.time()
        latency = 0

        if client_timestamp:
            latency = (now - client_timestamp) * 1000

        with self._lock:
            if sid in self._heartbeats:
                hb = self._heartbeats[sid]
                hb.last_pong = now
                hb.missed_pings = 0
                hb.status = ConnectionStatus.CONNECTED

                if latency > 0:
                    self._latency_samples[sid].append(latency)
                    if len(self._latency_samples[sid]) > self._max_latency_samples:
                        self._latency_samples[sid].pop(0)
                    self._avg_latency[sid] = sum(self._latency_samples[sid]) / len(self._latency_samples[sid])

                    self._adjust_interval(sid)

    def _adjust_interval(self, sid: str):
        """Adjust heartbeat interval based on latency."""
        avg_latency = self._avg_latency.get(sid, 0)

        with self._lock:
            if sid not in self._heartbeats:
                return

            current_interval = self._heartbeats[sid].ping_interval

            if avg_latency < 50:
                new_interval = min(current_interval * 1.2, self.MAX_INTERVAL)
            elif avg_latency > 200:
                new_interval = max(current_interval * 0.8, self.MIN_INTERVAL)
            else:
                return

            self._heartbeats[sid].ping_interval = new_interval

    def _monitor_loop(self):
        """Monitor loop for checking heartbeat status."""
        while self._running:
            time.sleep(self._check_interval)
            self._check_heartbeats()

    def _check_heartbeats(self):
        """Check all heartbeat states."""
        now = time.time()
        stale_connections = []
        timeout_connections = []

        with self._lock:
            for sid, hb in list(self._heartbeats.items()):
                time_since_pong = now - hb.last_pong

                if time_since_pong > hb.timeout:
                    timeout_connections.append(sid)
                elif time_since_pong > hb.ping_interval * 1.5:
                    stale_connections.append(sid)
                    hb.status = ConnectionStatus.STALE

        for sid in stale_connections:
            if self._on_stale:
                try:
                    self._on_stale(sid)
                except Exception as e:
                    logger.error(f"Stale callback error: {e}")

        for sid in timeout_connections:
            if self._on_timeout:
                try:
                    self._on_timeout(sid)
                except Exception as e:
                    logger.error(f"Timeout callback error: {e}")
            self.unregister(sid)

    def get_interval(self, sid: str) -> float:
        """Get current ping interval for connection."""
        with self._lock:
            return self._heartbeats.get(sid, HeartbeatState("", "", 0, 0, self.DEFAULT_PING_INTERVAL, self.DEFAULT_TIMEOUT)).ping_interval

    def get_stats(self) -> Dict:
        """Get heartbeat statistics."""
        with self._lock:
            return {
                'active_heartbeats': len(self._heartbeats),
                'avg_latency': sum(self._avg_latency.values()) / len(self._avg_latency) if self._avg_latency else 0,
                'per_connection': {
                    sid: {
                        'interval': hb.ping_interval,
                        'latency': self._avg_latency.get(sid, 0),
                        'missed': hb.missed_pings,
                        'status': hb.status.value
                    }
                    for sid, hb in self._heartbeats.items()
                }
            }


class ReconnectionManager:
    """
    Handles reconnection logic with exponential backoff and state management.
    """

    INITIAL_DELAY = 1
    MAX_DELAY = 60
    MAX_RETRIES = 10
    BACKOFF_FACTOR = 2
    JITTER = 0.3

    def __init__(self, on_reconnect: Callable[[str, Dict], bool] = None):
        self._reconnect_states: Dict[str, Dict] = {}
        self._lock = threading.Lock()
        self._on_reconnect = on_reconnect

        self._reconnection_callbacks: List[Callable] = []

    def start_reconnection(self, sid: str, user_id: str, session_data: Dict = None) -> bool:
        """Start reconnection process."""
        with self._lock:
            if sid in self._reconnect_states:
                state = self._reconnect_states[sid]
                if state['retries'] >= self.MAX_RETRIES:
                    return False
            else:
                self._reconnect_states[sid] = {
                    'user_id': user_id,
                    'session_data': session_data or {},
                    'retries': 0,
                    'delay': self.INITIAL_DELAY,
                    'started_at': time.time()
                }
                return True

            state = self._reconnect_states[sid]
            state['retries'] += 1
            state['delay'] = min(
                state['delay'] * self.BACKOFF_FACTOR,
                self.MAX_DELAY
            )
            return True

    def get_delay(self, sid: str) -> float:
        """Get current delay for reconnection."""
        with self._lock:
            state = self._reconnect_states.get(sid, {})
            return state.get('delay', self.INITIAL_DELAY)

    def get_retry_count(self, sid: str) -> int:
        """Get retry count for reconnection."""
        with self._lock:
            return self._reconnect_states.get(sid, {}).get('retries', 0)

    async def attempt_reconnect(self, sid: str) -> bool:
        """Attempt reconnection with backoff."""
        delay = self.get_delay(sid)
        jitter = random.uniform(-delay * self.JITTER, delay * self.JITTER)
        await asyncio.sleep(max(0, delay + jitter))

        if self._on_reconnect:
            with self._lock:
                session_data = self._reconnect_states.get(sid, {}).get('session_data', {})
            return await self._on_reconnect(sid, session_data)

        return True

    def cancel_reconnection(self, sid: str):
        """Cancel reconnection for session."""
        with self._lock:
            self._reconnect_states.pop(sid, None)

    def register_reconnection_callback(self, callback: Callable):
        """Register callback for reconnection events."""
        self._reconnection_callbacks.append(callback)

    def _trigger_callbacks(self, sid: str, success: bool):
        """Trigger registered callbacks."""
        for callback in self._reconnection_callbacks:
            try:
                callback(sid, success)
            except Exception as e:
                logger.error(f"Reconnection callback error: {e}")

    def get_stats(self) -> Dict:
        """Get reconnection statistics."""
        with self._lock:
            return {
                'active_reconnections': len(self._reconnect_states),
                'states': {
                    sid: {
                        'retries': s['retries'],
                        'delay': s['delay'],
                        'elapsed': time.time() - s['started_at']
                    }
                    for sid, s in self._reconnect_states.items()
                }
            }


class SessionPersistence:
    """
    Persists session state for reconnection recovery.
    """

    KEY_PREFIX = "ws:session:"
    SESSION_TTL = 3600

    def __init__(self):
        from app.websocket.redis_manager import get_redis_async
        self._redis = get_redis_async

    async def save_session(self, sid: str, session_data: Dict):
        """Save session data for recovery."""
        try:
            redis = await self._redis()
            await redis.set(
                f"{self.KEY_PREFIX}{sid}",
                json.dumps(session_data),
                ex=self.SESSION_TTL
            )
        except Exception as e:
            logger.error(f"Failed to save session: {e}")

    async def load_session(self, sid: str) -> Optional[Dict]:
        """Load session data for recovery."""
        try:
            redis = await self._redis()
            data = await redis.get(f"{self.KEY_PREFIX}{sid}")
            if data:
                return json.loads(data)
        except Exception as e:
            logger.error(f"Failed to load session: {e}")
        return None

    async def delete_session(self, sid: str):
        """Delete session data."""
        try:
            redis = await self._redis()
            await redis.delete(f"{self.KEY_PREFIX}{sid}")
        except Exception as e:
            logger.error(f"Failed to delete session: {e}")


import json


_global_heartbeat: Optional[AdaptiveHeartbeat] = None
_global_reconnection: Optional[ReconnectionManager] = None
_global_persistence: Optional[SessionPersistence] = None


def get_heartbeat() -> AdaptiveHeartbeat:
    """Get global heartbeat manager."""
    global _global_heartbeat
    if _global_heartbeat is None:
        _global_heartbeat = AdaptiveHeartbeat()
        _global_heartbeat.start()
    return _global_heartbeat


def get_reconnection_manager() -> ReconnectionManager:
    """Get global reconnection manager."""
    global _global_reconnection
    if _global_reconnection is None:
        _global_reconnection = ReconnectionManager()
    return _global_reconnection


def get_session_persistence() -> SessionPersistence:
    """Get global session persistence."""
    global _global_persistence
    if _global_persistence is None:
        _global_persistence = SessionPersistence()
    return _global_persistence