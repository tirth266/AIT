"""
Redis Pub/Sub Broadcasting System
================================
Distributed message broadcasting across multiple SocketIO server nodes.
Enables horizontal scaling with cross-node communication.
Falls back to local in-memory mode if Redis is unavailable.
"""

import os
import logging
import json
import time
import asyncio
import threading
from typing import Dict, List, Optional, Callable, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import redis
from redis.asyncio import Redis as AsyncRedis

from app.websocket.redis_manager import get_redis, get_redis_async, get_redis_pool

logger = logging.getLogger(__name__)


class MessagePriority(Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class PubSubMessage:
    """Pub/Sub message structure."""
    id: str
    channel: str
    event: str
    data: Dict
    timestamp: float
    priority: MessagePriority = MessagePriority.NORMAL
    source_node: str = ""
    target_sids: List[str] = field(default_factory=list)
    target_room: Optional[str] = None
    compress: bool = False


class RedisPubSubManager:
    """
    Redis Pub/Sub manager for distributed WebSocket broadcasting.
    Handles cross-node message routing and subscription management.
    Falls back to local in-memory mode if Redis is unavailable.
    """

    CHANNEL_PREFIX = "ws:pub:"
    NODE_CHANNEL_PREFIX = "ws:node:"
    ROOM_CHANNEL_PREFIX = "ws:room:"

    def __init__(self, node_id: str = None):
        self.node_id = node_id or os.environ.get('NODE_ID', f"node-{os.urandom(4).hex()}")
        self._pubsub: Optional[redis.client.PubSub] = None
        self._async_pubsub: Optional[Any] = None
        self._pubsub_thread: Optional[threading.Thread] = None
        self._running = False
        self._redis_available = False

        self._subscribers: Dict[str, Set[Callable]] = {}
        self._room_members: Dict[str, Set[str]] = {}
        self._lock = threading.Lock()

        self._message_queue: asyncio.Queue = asyncio.Queue(maxsize=10000)
        self._worker_task: Optional[asyncio.Task] = None

        self._local_messages: List[Dict] = []
        self._local_messages_lock = threading.Lock()

    def initialize(self):
        """Initialize Pub/Sub subscriptions with graceful fallback."""
        try:
            self._setup_pubsub()
            self._start_subscriber_thread()
            self._redis_available = True
            logger.info(f"[OK] Redis Pub/Sub connected for node {self.node_id}")
        except Exception as e:
            self._redis_available = False
            logger.warning(f"[WARN] Redis unavailable: {e}")
            logger.warning(f"[WARN] Using local in-memory websocket mode (scalability disabled)")
        
        self._start_async_worker()
        logger.info(f"PubSub manager initialized for node {self.node_id}")

    def _setup_pubsub(self):
        """Setup Redis pub/sub connections."""
        pool = get_redis_pool()
        self._pubsub = pool.get_pubsub()

        self._pubsub.subscribe(
            f"{self.NODE_CHANNEL_PREFIX}{self.node_id}",
            f"{self.CHANNEL_PREFIX}broadcast",
            f"{self.CHANNEL_PREFIX}events"
        )

    def _start_subscriber_thread(self):
        """Start background thread for pub/sub message handling."""
        self._running = True
        self._pubsub_thread = threading.Thread(target=self._pubsub_loop, daemon=True)
        self._pubsub_thread.start()

    def _pubsub_loop(self):
        """Pub/Sub message listening loop."""
        try:
            for message in self._pubsub.listen():
                if not self._running:
                    break
                if message['type'] == 'message':
                    try:
                        data = json.loads(message['data'])
                        asyncio.run(self._handle_message(data))
                    except Exception as e:
                        logger.error(f"Failed to handle pubsub message: {e}")
        except Exception as e:
            logger.warning(f"Pub/Sub listener stopped: {e}")
            self._redis_available = False

    def _start_async_worker(self):
        """Start async worker for processing messages."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                self._worker_task = loop.create_task(self._process_messages())
            else:
                self._worker_task = asyncio.create_task(self._process_messages())
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._worker_task = loop.create_task(self._process_messages())

    async def _process_messages(self):
        """Async message processor."""
        while self._running:
            try:
                message = await asyncio.wait_for(
                    self._message_queue.get(),
                    timeout=1.0
                )
                await self._deliver_message(message)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Message processing error: {e}")

    async def _handle_message(self, data: Dict):
        """Handle incoming pub/sub message."""
        await self._message_queue.put(data)

    async def _deliver_message(self, message: Dict):
        """Deliver message to local subscribers."""
        channel = message.get('channel', '')
        event = message.get('event', '')

        with self._lock:
            callbacks = self._subscribers.get(channel, set()).copy()

        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(message)
                else:
                    callback(message)
            except Exception as e:
                logger.error(f"Callback error for {channel}: {e}")

    def subscribe(self, channel: str, callback: Callable):
        """Subscribe to a channel."""
        with self._lock:
            if channel not in self._subscribers:
                self._subscribers[channel] = set()
            self._subscribers[channel].add(callback)
        logger.debug(f"Subscribed to channel: {channel}")

    def unsubscribe(self, channel: str, callback: Callable):
        """Unsubscribe from a channel."""
        with self._lock:
            if channel in self._subscribers:
                self._subscribers[channel].discard(callback)

    async def publish(
        self,
        channel: str,
        event: str,
        data: Dict,
        priority: MessagePriority = MessagePriority.NORMAL,
        target_sids: List[str] = None,
        target_room: str = None
    ):
        """Publish message to channel."""
        message = {
            'id': f"{time.time()}-{os.urandom(4).hex()}",
            'channel': channel,
            'event': event,
            'data': data,
            'timestamp': time.time(),
            'priority': priority.value,
            'source_node': self.node_id,
            'target_sids': target_sids or [],
            'target_room': target_room
        }

        if self._redis_available:
            try:
                redis_client = get_redis_async()
                await redis_client.publish(
                    f"{self.CHANNEL_PREFIX}{channel}",
                    json.dumps(message)
                )
            except Exception as e:
                logger.error(f"Failed to publish to {channel}: {e}")
        else:
            self._handle_local_message(message)

    def publish_sync(
        self,
        channel: str,
        event: str,
        data: Dict,
        priority: MessagePriority = MessagePriority.NORMAL,
        target_sids: List[str] = None,
        target_room: str = None
    ):
        """Synchronous publish with local fallback."""
        message = {
            'id': f"{time.time()}-{os.urandom(4).hex()}",
            'channel': channel,
            'event': event,
            'data': data,
            'timestamp': time.time(),
            'priority': priority.value,
            'source_node': self.node_id,
            'target_sids': target_sids or [],
            'target_room': target_room
        }

        if self._redis_available:
            try:
                redis_client = get_redis()
                redis_client.publish(f"{self.CHANNEL_PREFIX}{channel}", json.dumps(message))
            except Exception as e:
                logger.error(f"Failed to publish: {e}")
                self._handle_local_message(message)
        else:
            self._handle_local_message(message)

    def _handle_local_message(self, message: Dict):
        """Handle message locally (fallback mode)."""
        with self._local_messages_lock:
            self._local_messages.append(message)
            if len(self._local_messages) > 1000:
                self._local_messages = self._local_messages[-500:]

    async def join_room(self, room: str, sid: str):
        """Join a room for distributed broadcasting."""
        with self._lock:
            if room not in self._room_members:
                self._room_members[room] = set()
            self._room_members[room].add(sid)

        if self._redis_available:
            try:
                redis_client = get_redis_async()
                await redis_client.sadd(f"{self.ROOM_CHANNEL_PREFIX}{room}", sid)
            except Exception as e:
                logger.debug(f"Failed to join room in Redis: {e}")

    async def leave_room(self, room: str, sid: str):
        """Leave a room."""
        with self._lock:
            if room in self._room_members:
                self._room_members[room].discard(sid)

        if self._redis_available:
            try:
                redis_client = get_redis_async()
                await redis_client.srem(f"{self.ROOM_CHANNEL_PREFIX}{room}", sid)
            except Exception as e:
                logger.debug(f"Failed to leave room in Redis: {e}")

    async def get_room_members(self, room: str) -> Set[str]:
        """Get all members of a room."""
        if self._redis_available:
            try:
                redis_client = get_redis_async()
                members = await redis_client.smembers(f"{self.ROOM_CHANNEL_PREFIX}{room}")
                return members
            except Exception as e:
                logger.debug(f"Failed to get room members from Redis: {e}")
        
        with self._lock:
            return self._room_members.get(room, set()).copy()

    def broadcast_to_room(self, room: str, event: str, data: Dict):
        """Broadcast to all members of a room across nodes."""
        self.publish_sync(
            channel=f"room:{room}",
            event=event,
            data=data,
            target_room=room
        )

    def broadcast_to_node(self, node_id: str, event: str, data: Dict):
        """Broadcast to specific node."""
        self.publish_sync(
            channel=f"node:{node_id}",
            event=event,
            data=data
        )

    def broadcast_to_all(self, event: str, data: Dict):
        """Broadcast to all connected nodes."""
        self.publish_sync(
            channel="broadcast",
            event=event,
            data=data
        )

    def shutdown(self):
        """Shutdown pub/sub manager."""
        self._running = False
        if self._pubsub_thread:
            self._pubsub_thread.join(timeout=2)
        if self._worker_task:
            self._worker_task.cancel()
        if self._pubsub:
            self._pubsub.close()
        logger.info("PubSub manager shut down")


class RoomManager:
    """
    Distributed room management with Redis backend.
    Falls back to local in-memory mode if Redis unavailable.
    """

    ROOM_KEY_PREFIX = "ws:room:"
    ROOM_DATA_PREFIX = "ws:room_data:"

    def __init__(self):
        self._local_rooms: Dict[str, Set[str]] = {}
        self._local_room_data: Dict[str, Dict] = {}
        self._lock = threading.Lock()
        self._redis_available = True

    def _check_redis(self) -> bool:
        """Check if Redis is available."""
        try:
            import redis
            r = redis.from_url(os.environ.get('REDIS_URL', 'redis://localhost:6379/0'))
            r.ping()
            return True
        except Exception:
            return False

    async def create_room(self, room_id: str, metadata: Dict = None) -> bool:
        """Create a new room."""
        if self._redis_available and self._check_redis():
            try:
                redis_client = get_redis_async()
                if metadata:
                    await redis_client.hset(
                        f"{self.ROOM_DATA_PREFIX}{room_id}",
                        mapping=metadata
                    )
                return True
            except Exception as e:
                logger.debug(f"Failed to create room in Redis: {e}")
        
        with self._lock:
            self._local_room_data[room_id] = metadata or {}
        return True

    async def delete_room(self, room_id: str) -> bool:
        """Delete a room."""
        if self._redis_available and self._check_redis():
            try:
                redis_client = get_redis_async()
                await redis_client.delete(
                    f"{self.ROOM_KEY_PREFIX}{room_id}",
                    f"{self.ROOM_DATA_PREFIX}{room_id}"
                )
            except Exception as e:
                logger.debug(f"Failed to delete room from Redis: {e}")
        
        with self._lock:
            self._local_rooms.pop(room_id, None)
            self._local_room_data.pop(room_id, None)
        return True

    async def add_member(self, room_id: str, sid: str) -> bool:
        """Add member to room."""
        if self._redis_available and self._check_redis():
            try:
                redis_client = get_redis_async()
                await redis_client.sadd(f"{self.ROOM_KEY_PREFIX}{room_id}", sid)
            except Exception as e:
                logger.debug(f"Failed to add member in Redis: {e}")

        with self._lock:
            if room_id not in self._local_rooms:
                self._local_rooms[room_id] = set()
            self._local_rooms[room_id].add(sid)
        return True

    async def remove_member(self, room_id: str, sid: str) -> bool:
        """Remove member from room."""
        if self._redis_available and self._check_redis():
            try:
                redis_client = get_redis_async()
                await redis_client.srem(f"{self.ROOM_KEY_PREFIX}{room_id}", sid)
            except Exception as e:
                logger.debug(f"Failed to remove member from Redis: {e}")

        with self._lock:
            if room_id in self._local_rooms:
                self._local_rooms[room_id].discard(sid)
        return True

    async def get_members(self, room_id: str) -> Set[str]:
        """Get all room members."""
        if self._redis_available and self._check_redis():
            try:
                redis_client = get_redis_async()
                members = await redis_client.smembers(f"{self.ROOM_KEY_PREFIX}{room_id}")
                return members
            except Exception as e:
                logger.debug(f"Failed to get members from Redis: {e}")
        
        with self._lock:
            return self._local_rooms.get(room_id, set()).copy()

    async def get_member_count(self, room_id: str) -> int:
        """Get room member count."""
        if self._redis_available and self._check_redis():
            try:
                redis_client = get_redis_async()
                return await redis_client.scard(f"{self.ROOM_KEY_PREFIX}{room_id}")
            except Exception as e:
                logger.debug(f"Failed to get member count from Redis: {e}")
        
        with self._lock:
            return len(self._local_rooms.get(room_id, set()))

    async def get_room_metadata(self, room_id: str) -> Optional[Dict]:
        """Get room metadata."""
        if self._redis_available and self._check_redis():
            try:
                redis_client = get_redis_async()
                data = await redis_client.hgetall(f"{self.ROOM_DATA_PREFIX}{room_id}")
                return data if data else None
            except Exception as e:
                logger.debug(f"Failed to get room metadata from Redis: {e}")
        
        with self._lock:
            return self._local_room_data.get(room_id)


_global_pubsub_manager: Optional[RedisPubSubManager] = None
_global_room_manager: Optional[RoomManager] = None


def get_pubsub_manager() -> RedisPubSubManager:
    """Get global pub/sub manager."""
    global _global_pubsub_manager
    if _global_pubsub_manager is None:
        _global_pubsub_manager = RedisPubSubManager()
        _global_pubsub_manager.initialize()
    return _global_pubsub_manager


def get_room_manager() -> RoomManager:
    """Get global room manager."""
    global _global_room_manager
    if _global_room_manager is None:
        _global_room_manager = RoomManager()
    return _global_room_manager