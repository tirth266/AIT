"""
Connection Manager with Redis-Backed Presence Tracking
=======================================================
Manages WebSocket connections with distributed presence tracking,
user connection limits, and session management across multiple nodes.
"""

import os
import logging
import json
import time
import asyncio
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import threading

from app.websocket.redis_manager import get_redis, get_redis_async

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    CONNECTING = "connecting"
    AUTHENTICATED = "authenticated"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"


@dataclass
class ConnectionInfo:
    """Detailed connection information."""
    sid: str
    user_id: str
    node_id: str
    state: ConnectionState
    connected_at: float
    last_heartbeat: float
    last_activity: float
    subscriptions: Set[str] = field(default_factory=set)
    metadata: Dict = field(default_factory=dict)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    session_token: Optional[str] = None


class PresenceTracker:
    """
    Redis-backed presence tracking for distributed WebSocket connections.
    Tracks online users across multiple server nodes.
    """

    KEY_PREFIX = "ws:presence:"
    USER_SESSIONS_PREFIX = "ws:user_sessions:"
    NODE_CONNECTIONS_PREFIX = "ws:node:"
    USER_COUNT_PREFIX = "ws:user_count:"

    def __init__(self, node_id: str, ttl: int = 300):
        self.node_id = node_id
        self.ttl = ttl
        self._lock = threading.Lock()

    def _get_connection_key(self, user_id: str) -> str:
        return f"{self.KEY_PREFIX}{user_id}"

    def _get_user_sessions_key(self, user_id: str) -> str:
        return f"{self.USER_SESSIONS_PREFIX}{user_id}"

    def _get_node_key(self) -> str:
        return f"{self.NODE_CONNECTIONS_PREFIX}{self.node_id}"

    def _get_user_count_key(self, date: str = None) -> str:
        if date is None:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return f"{self.USER_COUNT_PREFIX}{date}"

    async def user_online(self, user_id: str, session_data: Dict) -> bool:
        """Mark user as online with session info."""
        try:
            redis = get_redis_async()
            key = self._get_connection_key(user_id)
            session_data['node_id'] = self.node_id
            session_data['last_update'] = time.time()

            pipe = redis.pipeline()
            pipe.set(key, json.dumps(session_data), ex=self.ttl)
            pipe.sadd(self._get_user_sessions_key(user_id), session_data.get('sid', ''))
            pipe.hset(self._get_node_key(), mapping={session_data.get('sid', ''): json.dumps(session_data)})
            pipe.expire(self._get_node_key(), self.ttl)
            await pipe.execute()

            redis.incr(self._get_user_count_key())
            redis.expire(self._get_user_count_key(), 86400 * 2)

            return True
        except Exception as e:
            logger.error(f"Failed to mark user online: {e}")
            return False

    async def user_offline(self, user_id: str, sid: str) -> bool:
        """Mark user as offline."""
        try:
            redis = get_redis_async()
            pipe = redis.pipeline()
            pipe.srem(self._get_user_sessions_key(user_id), sid)
            pipe.hdel(self._get_node_key(), sid)
            await pipe.execute()

            session_count = await redis.scard(self._get_user_sessions_key(user_id))
            if session_count == 0:
                await redis.delete(self._get_connection_key(user_id))

            return True
        except Exception as e:
            logger.error(f"Failed to mark user offline: {e}")
            return False

    async def get_user_presence(self, user_id: str) -> Optional[Dict]:
        """Get user's presence information."""
        try:
            redis = get_redis_async()
            data = await redis.get(self._get_connection_key(user_id))
            if data:
                return json.loads(data)
        except Exception as e:
            logger.error(f"Failed to get user presence: {e}")
        return None

    async def is_user_online(self, user_id: str) -> bool:
        """Check if user is online."""
        try:
            redis = get_redis_async()
            return await redis.exists(self._get_connection_key(user_id))
        except Exception:
            return False

    async def get_online_users(self) -> Set[str]:
        """Get all online user IDs."""
        try:
            redis = get_redis_async()
            keys = await redis.keys(f"{self.KEY_PREFIX}*")
            return {k.replace(self.KEY_PREFIX, '') for k in keys}
        except Exception as e:
            logger.error(f"Failed to get online users: {e}")
            return set()

    async def get_node_connections(self) -> Dict:
        """Get all connections on this node."""
        try:
            redis = get_redis_async()
            data = await redis.hgetall(self._get_node_key())
            return {k: json.loads(v) for k, v in data.items()}
        except Exception as e:
            logger.error(f"Failed to get node connections: {e}")
            return {}

    async def update_heartbeat(self, user_id: str, sid: str) -> bool:
        """Update user's last heartbeat timestamp."""
        try:
            redis = get_redis_async()
            key = self._get_connection_key(user_id)
            data = await redis.get(key)
            if data:
                session_data = json.loads(data)
                session_data['last_heartbeat'] = time.time()
                session_data['last_update'] = time.time()
                await redis.set(key, json.dumps(session_data), ex=self.ttl)
                return True
        except Exception as e:
            logger.error(f"Failed to update heartbeat: {e}")
        return False

    async def get_all_online_users_count(self) -> int:
        """Get total count of online users across all nodes."""
        try:
            redis = get_redis_async()
            keys = await redis.keys(f"{self.KEY_PREFIX}*")
            return len(keys)
        except Exception as e:
            logger.error(f"Failed to get online users count: {e}")
            return 0


class ConnectionLimitManager:
    """
    Manages per-user connection limits to prevent resource abuse.
    """

    KEY_PREFIX = "ws:connection_limit:"
    DEFAULT_MAX_CONNECTIONS = 5

    def __init__(self, default_limit: int = None):
        self.default_limit = default_limit or self.DEFAULT_MAX_CONNECTIONS
        self._limits: Dict[str, int] = {}
        self._lock = threading.Lock()

    def set_limit(self, user_id: str, limit: int):
        """Set custom connection limit for a user."""
        with self._lock:
            self._limits[user_id] = limit

    def get_limit(self, user_id: str) -> int:
        """Get connection limit for a user."""
        with self._lock:
            return self._limits.get(user_id, self.default_limit)

    async def can_connect(self, user_id: str) -> Tuple[bool, int]:
        """Check if user can establish a new connection."""
        try:
            redis = get_redis_async()
            key = f"{self.KEY_PREFIX}{user_id}"
            current = await redis.get(key)

            limit = self.get_limit(user_id)
            current_count = int(current) if current else 0

            if current_count >= limit:
                return False, limit

            await redis.incr(key)
            await redis.expire(key, 3600)

            return True, limit
        except Exception as e:
            logger.error(f"Connection limit check failed: {e}")
            return True, self.default_limit

    async def release_connection(self, user_id: str):
        """Release a connection slot for user."""
        try:
            redis = get_redis_async()
            key = f"{self.KEY_PREFIX}{user_id}"
            await redis.decr(key)
        except Exception as e:
            logger.error(f"Failed to release connection: {e}")


class ConnectionManager:
    """
    Distributed connection manager with Redis-backed presence and limits.
    """

    def __init__(self, node_id: str = None, max_connections_per_user: int = 5):
        self.node_id = node_id or os.environ.get('NODE_ID', f"node-{uuid.uuid4().hex[:8]}")
        self.presence = PresenceTracker(self.node_id)
        self.limit_manager = ConnectionLimitManager(max_connections_per_user)

        self._local_connections: Dict[str, ConnectionInfo] = {}
        self._lock = threading.Lock()

        self._connection_callbacks: List[Callable] = []
        self._disconnection_callbacks: List[Callable] = []

        self._stats = {
            'total_connections': 0,
            'total_disconnections': 0,
            'failed_auth': 0,
            'connection_limit_rejected': 0
        }

    def register_connection_callback(self, callback: Callable):
        """Register callback for new connections."""
        self._connection_callbacks.append(callback)

    def register_disconnection_callback(self, callback: Callable):
        """Register callback for disconnections."""
        self._disconnection_callbacks.append(callback)

    async def add_connection(self, sid: str, user_id: str, metadata: Dict = None) -> bool:
        """Add a new connection."""
        can_connect, limit = await self.limit_manager.can_connect(user_id)
        if not can_connect:
            logger.warning(f"Connection limit exceeded for user {user_id} (limit: {limit})")
            self._stats['connection_limit_rejected'] += 1
            return False

        now = time.time()
        conn_info = ConnectionInfo(
            sid=sid,
            user_id=user_id,
            node_id=self.node_id,
            state=ConnectionState.CONNECTING,
            connected_at=now,
            last_heartbeat=now,
            last_activity=now,
            metadata=metadata or {}
        )

        with self._lock:
            self._local_connections[sid] = conn_info

        await self.presence.user_online(user_id, {
            'sid': sid,
            'connected_at': now,
            'metadata': metadata
        })

        self._stats['total_connections'] += 1
        self._trigger_connection_callbacks(conn_info)

        logger.info(f"Connection added: {sid} for user {user_id} on node {self.node_id}")
        return True

    async def remove_connection(self, sid: str) -> Optional[ConnectionInfo]:
        """Remove a connection."""
        conn_info = None

        with self._lock:
            conn_info = self._local_connections.pop(sid, None)

        if conn_info:
            await self.presence.user_offline(conn_info.user_id, sid)
            await self.limit_manager.release_connection(conn_info.user_id)

            self._stats['total_disconnections'] += 1
            self._trigger_disconnection_callbacks(conn_info)

            logger.info(f"Connection removed: {sid} for user {conn_info.user_id}")
            return conn_info
        return None

    async def update_heartbeat(self, sid: str) -> bool:
        """Update connection heartbeat."""
        with self._lock:
            if sid in self._local_connections:
                self._local_connections[sid].last_heartbeat = time.time()
                self._local_connections[sid].state = ConnectionState.CONNECTED
                return True

        await self.presence.update_heartbeat(
            self._local_connections.get(sid, ConnectionInfo("", "", "", ConnectionState.CONNECTED, 0, 0, 0)).user_id,
            sid
        )
        return False

    def get_connection(self, sid: str) -> Optional[ConnectionInfo]:
        """Get connection info by session ID."""
        with self._lock:
            return self._local_connections.get(sid)

    def get_user_connections(self, user_id: str) -> List[ConnectionInfo]:
        """Get all connections for a user."""
        with self._lock:
            return [c for c in self._local_connections.values() if c.user_id == user_id]

    async def get_online_users(self) -> Set[str]:
        """Get all online users across all nodes."""
        return await self.presence.get_online_users()

    def get_local_connection_count(self) -> int:
        """Get connection count on this node."""
        with self._lock:
            return len(self._local_connections)

    def get_stats(self) -> Dict:
        """Get connection statistics."""
        return {
            **self._stats,
            'local_connections': self.get_local_connection_count(),
            'node_id': self.node_id
        }

    def _trigger_connection_callbacks(self, conn_info: ConnectionInfo):
        """Trigger registered connection callbacks."""
        for callback in self._connection_callbacks:
            try:
                callback(conn_info)
            except Exception as e:
                logger.error(f"Connection callback error: {e}")

    def _trigger_disconnection_callbacks(self, conn_info: ConnectionInfo):
        """Trigger registered disconnection callbacks."""
        for callback in self._disconnection_callbacks:
            try:
                callback(conn_info)
            except Exception as e:
                logger.error(f"Disconnection callback error: {e}")


_global_connection_manager: Optional[ConnectionManager] = None


def get_connection_manager() -> ConnectionManager:
    """Get global connection manager instance."""
    global _global_connection_manager
    if _global_connection_manager is None:
        _global_connection_manager = ConnectionManager()
    return _global_connection_manager