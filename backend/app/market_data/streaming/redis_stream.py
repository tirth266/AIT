"""
Redis Stream Architecture
==========================
High-performance Redis stream for market data distribution.
"""

import logging
import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import threading
import redis

from ..core.models import Tick, OrderBook, Candle, Exchange

logger = logging.getLogger('market_data.streaming')


class StreamTopic(str, Enum):
    TICKS = "market:ticks"
    ORDERBOOK = "market:orderbook"
    CANDLES = "market:candles"
    TRADES = "market:trades"
    INDICES = "market:indices"
    SYSTEM = "market:system"


@dataclass
class StreamConfig:
    redis_url: str = "redis://localhost:6379/0"
    max_stream_length: int = 10000
    consumer_group: str = "market_data"
    block_timeout_ms: int = 1000
    enable_persistence: bool = True
    batch_size: int = 100


@dataclass
class StreamMessage:
    topic: StreamTopic
    key: str
    data: Dict[str, Any]
    timestamp: datetime
    sequence: int = 0


class RedisMarketDataStream:
    """
    Redis stream-based market data distribution system.
    """

    def __init__(
        self,
        config: Optional[StreamConfig] = None,
    ):
        self.config = config or StreamConfig()

        self._redis: Optional[redis.Redis] = None
        self._connected = False
        self._running = False

        self._publish_callbacks: Dict[StreamTopic, List[Callable]] = defaultdict(list)
        self._consumers: Dict[str, List[Callable]] = {}

        self._stats = {
            "messages_published": 0,
            "messages_consumed": 0,
            "publish_errors": 0,
            "consume_errors": 0,
            "bytes_published": 0,
        }

        self._lock = threading.RLock()

    def connect(self) -> bool:
        try:
            self._redis = redis.from_url(
                self.config.redis_url,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
            )
            self._redis.ping()
            self._connected = True
            logger.info("Redis stream connected")
            return True
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            self._connected = False
            return False

    def disconnect(self) -> None:
        if self._redis:
            self._redis.close()
        self._connected = False

    def publish_tick(self, tick: Tick) -> bool:
        if not self._connected:
            return False

        try:
            topic = StreamTopic.TICKS
            key = f"{tick.symbol}:{tick.exchange.value}"

            message = {
                "symbol": tick.symbol,
                "exchange": tick.exchange.value,
                "timestamp": tick.timestamp.isoformat(),
                "last_price": tick.last_price,
                "last_quantity": tick.last_quantity,
                "volume": tick.volume,
                "open": tick.open,
                "high": tick.high,
                "low": tick.low,
                "close": tick.close,
                "change": tick.change,
                "change_percent": tick.change_percent,
                "tick_id": tick.tick_id,
            }

            self._publish_message(topic, key, message)

            for callback in self._publish_callbacks.get(topic, []):
                try:
                    callback(tick)
                except Exception as e:
                    logger.warning(f"Publish callback error: {e}")

            return True

        except Exception as e:
            logger.error(f"Publish tick error: {e}")
            self._stats["publish_errors"] += 1
            return False

    def publish_orderbook(self, orderbook: OrderBook) -> bool:
        if not self._connected:
            return False

        try:
            topic = StreamTopic.ORDERBOOK
            key = f"{orderbook.symbol}:{orderbook.exchange.value}"

            message = orderbook.to_dict()

            self._publish_message(topic, key, message)

            for callback in self._publish_callbacks.get(topic, []):
                try:
                    callback(orderbook)
                except Exception as e:
                    logger.warning(f"Publish callback error: {e}")

            return True

        except Exception as e:
            logger.error(f"Publish orderbook error: {e}")
            return False

    def publish_candle(self, candle: Candle) -> bool:
        if not self._connected:
            return False

        try:
            topic = StreamTopic.CANDLES
            key = f"{candle.symbol}:{candle.exchange.value}:{candle.interval.value}"

            message = candle.to_dict()

            self._publish_message(topic, key, message)

            return True

        except Exception as e:
            logger.error(f"Publish candle error: {e}")
            return False

    def _publish_message(
        self,
        topic: StreamTopic,
        key: str,
        data: Dict[str, Any],
    ) -> None:
        if not self._redis:
            return

        message_json = json.dumps(data)

        stream_key = topic.value

        self._redis.xadd(
            stream_key,
            {"key": key, "data": message_json},
            maxlen=self.config.max_stream_length,
            approximate=True,
        )

        self._stats["messages_published"] += 1
        self._stats["bytes_published"] += len(message_json)

    def subscribe_to_topic(
        self,
        topic: StreamTopic,
        callback: Callable[[StreamMessage], None],
        consumer_name: Optional[str] = None,
    ) -> str:
        consumer_id = consumer_name or f"consumer_{threading.get_ident()}"

        self._consumers[consumer_id] = [topic, callback]

        logger.info(f"Subscribed to {topic.value} as {consumer_id}")

        return consumer_id

    def unsubscribe(self, consumer_id: str) -> bool:
        if consumer_id in self._consumers:
            del self._consumers[consumer_id]
            return True
        return False

    def read_stream(
        self,
        topic: StreamTopic,
        count: int = 100,
        last_id: Optional[str] = None,
    ) -> List[StreamMessage]:
        if not self._connected:
            return []

        try:
            stream_key = topic.value

            if last_id:
                messages = self._redis.xread({stream_key: last_id}, count=count, block=self.config.block_timeout_ms)
            else:
                messages = self._redis.xread({stream_key: "0"}, count=count)

            results = []
            for stream_name, entries in messages:
                for msg_id, msg_data in entries:
                    msg = StreamMessage(
                        topic=topic,
                        key=msg_data.get("key", ""),
                        data=json.loads(msg_data.get("data", "{}")),
                        timestamp=datetime.now(timezone.utc),
                        sequence=int(msg_id.split("-")[0]) if "-" in msg_id else 0,
                    )
                    results.append(msg)

                    self._stats["messages_consumed"] += 1

            return results

        except Exception as e:
            logger.error(f"Read stream error: {e}")
            self._stats["consume_errors"] += 1
            return []

    def register_publish_callback(
        self,
        topic: StreamTopic,
        callback: Callable,
    ) -> None:
        self._publish_callbacks[topic].append(callback)

    def get_stream_info(self, topic: StreamTopic) -> Optional[Dict[str, Any]]:
        if not self._connected:
            return None

        try:
            info = self._redis.xinfo_stream(topic.value)
            return {
                "length": info.get("length", 0),
                "first_entry": info.get("first-entry", []),
                "last_entry": info.get("last-entry", []),
                "max_length": info.get("max-length", 0),
            }
        except Exception as e:
            logger.warning(f"Stream info error: {e}")
            return None

    def trim_stream(self, topic: StreamTopic, count: int = 1000) -> bool:
        if not self._connected:
            return False

        try:
            self._redis.xtrim(topic.value, count, approximate=True)
            return True
        except Exception as e:
            logger.error(f"Trim stream error: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        return {
            "connected": self._connected,
            "messages_published": self._stats["messages_published"],
            "messages_consumed": self._stats["messages_consumed"],
            "publish_errors": self._stats["publish_errors"],
            "consume_errors": self._stats["consume_errors"],
            "bytes_published": self._stats["bytes_published"],
            "active_consumers": len(self._consumers),
        }

    @property
    def is_connected(self) -> bool:
        return self._connected


class DataPublisher:
    """
    High-level publisher for market data with batching.
    """

    def __init__(self, stream: RedisMarketDataStream):
        self._stream = stream
        self._batch_buffer: Dict[StreamTopic, List] = defaultdict(list)
        self._last_flush = time.perf_counter()

    def publish(self, topic: StreamTopic, data: Any) -> None:
        if isinstance(data, Tick):
            self._stream.publish_tick(data)
        elif isinstance(data, OrderBook):
            self._stream.publish_orderbook(data)
        elif isinstance(data, Candle):
            self._stream.publish_candle(data)

    async def flush(self) -> None:
        pass


class DataSubscriber:
    """
    High-level subscriber for market data streams.
    """

    def __init__(self, stream: RedisMarketDataStream):
        self._stream = stream
        self._subscriptions: Dict[str, Any] = {}

    def subscribe(
        self,
        topic: StreamTopic,
        callback: Callable[[StreamMessage], None],
    ) -> str:
        return self._stream.subscribe_to_topic(topic, callback)


_stream: Optional[RedisMarketDataStream] = None


def get_redis_stream() -> RedisMarketDataStream:
    global _stream
    if _stream is None:
        _stream = RedisMarketDataStream()
        _stream.connect()
    return _stream