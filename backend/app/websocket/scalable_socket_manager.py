"""
Scalable WebSocket Manager
==========================
Production-ready WebSocket manager with Redis Pub/Sub horizontal scaling,
batching, presence tracking, and optimized heartbeat.
"""

import os
import logging
import time
import json
import asyncio
import threading
from typing import Dict, List, Optional, Set, Any, Callable
from datetime import datetime, timezone

from flask_socketio import emit, join, leave, disconnect
from flask import request, Flask
import jwt
import zlib

from app.websocket.redis_manager import get_redis, get_redis_async, get_redis_pool
from app.websocket.connection_manager import (
    get_connection_manager,
    ConnectionManager,
    ConnectionInfo
)
from app.websocket.batching import get_event_batcher, EventBatcher
from app.websocket.middleware import (
    get_auth_middleware,
    get_rate_limiter,
    get_throttler,
    SocketAuthMiddleware,
    SocketRateLimiter
)
from app.websocket.pubsub_manager import (
    get_pubsub_manager,
    get_room_manager,
    RedisPubSubManager,
    RoomManager
)
from app.websocket.heartbeat import (
    get_heartbeat,
    get_reconnection_manager,
    get_session_persistence,
    AdaptiveHeartbeat,
    ReconnectionManager,
    SessionPersistence
)

logger = logging.getLogger(__name__)


class ScalableSocketManager:
    """
    Scalable WebSocket manager with distributed state and horizontal scaling.
    """

    def __init__(
        self,
        socketio,
        app: Flask = None,
        config: Dict = None
    ):
        self.socketio = socketio
        self.app = app
        self.config = config or {}

        self.node_id = os.environ.get('NODE_ID', f"node-{os.urandom(4).hex()}")

        self._connection_manager = get_connection_manager()
        self._auth_middleware = get_auth_middleware()
        self._rate_limiter = get_rate_limiter()
        self._throttler = get_throttler()
        self._pubsub_manager = get_pubsub_manager()
        self._room_manager = get_room_manager()
        self._heartbeat = get_heartbeat()
        self._reconnection = get_reconnection_manager()
        self._session_persistence = get_session_persistence()
        self._batcher = get_event_batcher()

        self._batcher.set_batch_callback(self._deliver_batch)

        self._compression_enabled = self.config.get('COMPRESSION_ENABLED', True)
        self._compression_threshold = self.config.get('COMPRESSION_THRESHOLD', 500)

        self._message_handlers: Dict[str, Callable] = {}
        self._running = False

        self._stats = {
            'messages_sent': 0,
            'messages_batched': 0,
            'messages_compressed': 0,
            'bytes_sent': 0,
            'broadcasts': 0
        }

    def initialize(self):
        """Initialize the scalable socket manager."""
        self._setup_pubsub_handlers()
        self._setup_connection_callbacks()
        self._running = True
        logger.info(f"Scalable socket manager initialized for node {self.node_id}")

    def _setup_pubsub_handlers(self):
        """Setup Redis Pub/Sub message handlers."""
        self._pubsub_manager.subscribe(
            f"ws:pub:broadcast",
            self._handle_pubsub_message
        )
        self._pubsub_manager.subscribe(
            f"ws:pub:events",
            self._handle_pubsub_event
        )

    def _setup_connection_callbacks(self):
        """Setup connection lifecycle callbacks."""
        self._connection_manager.register_connection_callback(
            self._on_connection_established
        )
        self._connection_manager.register_disconnection_callback(
            self._on_connection_closed
        )

    def _on_connection_established(self, conn_info: ConnectionInfo):
        """Handle new connection established."""
        logger.info(f"Connection established: {conn_info.sid} for {conn_info.user_id}")

    def _on_connection_closed(self, conn_info: ConnectionInfo):
        """Handle connection closed."""
        logger.info(f"Connection closed: {conn_info.sid} for {conn_info.user_id}")

    def _handle_pubsub_message(self, message: Dict):
        """Handle incoming pub/sub message."""
        target_room = message.get('target_room')
        target_sids = message.get('target_sids', [])

        if target_room:
            self._deliver_to_room(target_room, message['event'], message['data'])
        elif target_sids:
            for sid in target_sids:
                self._deliver_to_sid(sid, message['event'], message['data'])
        else:
            self._broadcast_local(message['event'], message['data'])

    def _handle_pubsub_event(self, message: Dict):
        """Handle pub/sub events."""
        logger.debug(f"PubSub event: {message.get('event')}")

    def authenticate_token(self, token: str) -> Optional[Dict]:
        """Validate JWT token."""
        result = self._auth_middleware.validate_token(token)
        if result.success:
            return {
                'user_id': result.user_id,
                'metadata': result.metadata
            }
        return None

    async def register_connection(self, sid: str, token: str, metadata: Dict = None) -> bool:
        """Register new connection with authentication."""
        if not self._throttler.can_connect():
            logger.warning(f"Connection throttled for {sid}")
            return False

        user_data = self.authenticate_token(token)
        if not user_data:
            self._stats['auth_failed'] = self._stats.get('auth_failed', 0) + 1
            return False

        success = await self._connection_manager.add_connection(
            sid,
            user_data['user_id'],
            metadata
        )

        if success:
            self._heartbeat.register(sid, user_data['user_id'])
            join(f"user:{user_data['user_id']}")

            asyncio.create_task(self._session_persistence.save_session(sid, {
                'user_id': user_data['user_id'],
                'connected_at': time.time(),
                'metadata': metadata
            }))

            await self._room_manager.add_member(f"user:{user_data['user_id']}", sid)

            logger.info(f"Connection registered: {sid} -> {user_data['user_id']}")

        return success

    async def unregister_connection(self, sid: str) -> bool:
        """Unregister connection."""
        conn_info = await self._connection_manager.remove_connection(sid)

        if conn_info:
            self._heartbeat.unregister(sid)
            leave(f"user:{conn_info.user_id}")

            await self._room_manager.remove_member(f"user:{conn_info.user_id}", sid)
            await self._session_persistence.delete_session(sid)

            return True
        return False

    def emit_to_user(self, user_id: str, event: str, data: Dict, batch: bool = True):
        """Emit event to user's all sessions."""
        user_connections = self._connection_manager.get_user_connections(user_id)

        if not user_connections:
            self._emit_via_pubsub(user_id, event, data)
            return

        for conn in user_connections:
            self._deliver_to_sid(conn.sid, event, data, batch=batch)

    def emit_to_symbol(self, symbol: str, event: str, data: Dict):
        """Emit event to symbol subscribers via Redis."""
        room = f"market:{symbol.upper()}"
        self._broadcast_to_room(room, event, data)

    def emit_to_all(self, event: str, data: Dict):
        """Broadcast to all connected clients across nodes."""
        self._stats['broadcasts'] += 1

        self._broadcast_local(event, data)
        self._pubsub_manager.publish_sync(
            channel="broadcast",
            event=event,
            data=data
        )

    def _emit_via_pubsub(self, user_id: str, event: str, data: Dict):
        """Emit via Redis pub/sub for cross-node delivery."""
        self._pubsub_manager.publish_sync(
            channel=f"user:{user_id}",
            event=event,
            data=data,
            target_room=f"user:{user_id}"
        )

    def _broadcast_to_room(self, room: str, event: str, data: Dict):
        """Broadcast to room across nodes."""
        self._pubsub_manager.broadcast_to_room(room, event, data)

    def _broadcast_local(self, event: str, data: Dict):
        """Broadcast to local connected clients."""
        self.socketio.emit(event, data, namespace='/')

    def _deliver_to_sid(self, sid: str, event: str, data: Dict, batch: bool = False):
        """Deliver message to specific session."""
        if batch:
            self._batcher.add_event(event, data, target_sids=[sid])
        else:
            compressed = self._compress_data(data) if self._should_compress(data) else data
            self.socketio.emit(event, compressed, room=sid, namespace='/')
            self._update_stats(data)

    def _deliver_to_room(self, room: str, event: str, data: Dict):
        """Deliver message to room."""
        compressed = self._compress_data(data) if self._should_compress(data) else data
        self.socketio.emit(event, compressed, room=room, namespace='/')

    def _deliver_batch(self, queue_key: str, batch_data: Dict):
        """Deliver batched messages."""
        if batch_data.get('compressed'):
            try:
                data = json.loads(zlib.decompress(bytes.fromhex(batch_data['data'])))
            except Exception:
                return
        else:
            data = batch_data

        events = data.get('events', [])
        if not events:
            return

        for event_data in events:
            if queue_key.startswith('room:'):
                room = queue_key.replace('room:', '')
                self.socketio.emit(event_data['event'], event_data['data'], room=room)
            elif queue_key.startswith('sids:'):
                sids = queue_key.replace('sids:', '').split(',')
                for sid in sids:
                    self.socketio.emit(event_data['event'], event_data['data'], room=sid)
            else:
                self.socketio.emit(event_data['event'], event_data['data'])

        self._stats['messages_batched'] += len(events)

    def _compress_data(self, data: Dict) -> Dict:
        """Compress data using zlib."""
        try:
            json_str = json.dumps(data)
            compressed = zlib.compress(json_str.encode('utf-8'), level=6)
            return {
                '_compressed': True,
                'data': compressed.hex()
            }
        except Exception:
            return data

    def _should_compress(self, data: Dict) -> bool:
        """Check if data should be compressed."""
        if not self._compression_enabled:
            return False
        return len(json.dumps(data)) > self._compression_threshold

    def _update_stats(self, data: Dict):
        """Update sending statistics."""
        self._stats['messages_sent'] += 1
        self._stats['bytes_sent'] += len(json.dumps(data))

    def subscribe_market(self, sid: str, symbols: List[str], user_id: str):
        """Subscribe to market data symbols."""
        for symbol in symbols:
            room = f"market:{symbol.upper()}"
            join(room)
            asyncio.create_task(self._room_manager.add_member(room, sid))

        logger.info(f"Session {sid} subscribed to {len(symbols)} symbols")

    def unsubscribe_market(self, sid: str, symbols: List[str]):
        """Unsubscribe from market data symbols."""
        for symbol in symbols:
            room = f"market:{symbol.upper()}"
            leave(room)
            asyncio.create_task(self._room_manager.remove_member(room, sid))

    def handle_heartbeat(self, sid: str, client_time: float = None):
        """Handle heartbeat/ping from client."""
        self._heartbeat.record_pong(sid, client_time)

    def broadcast_market_tick(self, symbol: str, data: Dict):
        """Broadcast market tick to subscribers."""
        payload = {
            'event': 'market_tick',
            'data': {
                'symbol': symbol.upper(),
                'last_price': data.get('last_price', 0),
                'change': data.get('change', 0),
                'change_percent': data.get('change_percent', 0),
                'volume': data.get('volume', 0),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        }
        room = f"market:{symbol.upper()}"
        self._broadcast_to_room(room, 'market_tick', payload['data'])

    def broadcast_order_update(self, user_id: str, order_data: Dict):
        """Broadcast order update to user."""
        payload = {
            'order_id': order_data.get('order_id'),
            'status': order_data.get('status'),
            'filled_quantity': order_data.get('filled_quantity', 0),
            'average_price': order_data.get('average_price'),
            'message': order_data.get('message', ''),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        self.emit_to_user(user_id, 'order_update', payload)

    def broadcast_position_update(self, user_id: str, position_data: Dict):
        """Broadcast position update to user."""
        payload = {
            'position_id': position_data.get('position_id'),
            'symbol': position_data.get('symbol'),
            'quantity': position_data.get('quantity'),
            'current_price': position_data.get('current_price'),
            'unrealized_pnl': position_data.get('unrealized_pnl', 0),
            'pnl_percent': position_data.get('pnl_percent', 0),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        self.emit_to_user(user_id, 'position_update', payload)

    async def get_online_users(self) -> Set[str]:
        """Get all online users across all nodes."""
        return await self._connection_manager.get_online_users()

    def get_connection_stats(self) -> Dict:
        """Get connection statistics."""
        return {
            **self._connection_manager.get_stats(),
            **self._stats,
            'heartbeat': self._heartbeat.get_stats(),
            'reconnection': self._reconnection.get_stats(),
            'batcher': self._batcher.get_stats()
        }

    def shutdown(self):
        """Shutdown socket manager."""
        self._running = False
        self._heartbeat.stop()
        self._batcher.stop()
        self._pubsub_manager.shutdown()
        logger.info("Scalable socket manager shut down")


_global_socket_manager: Optional[ScalableSocketManager] = None


def get_scalable_socket_manager() -> ScalableSocketManager:
    """Get global scalable socket manager."""
    global _global_socket_manager
    return _global_socket_manager


def init_scalable_socket_manager(socketio, app: Flask) -> ScalableSocketManager:
    """Initialize and return scalable socket manager."""
    global _global_socket_manager
    _global_socket_manager = ScalableSocketManager(socketio, app)
    _global_socket_manager.initialize()
    return _global_socket_manager