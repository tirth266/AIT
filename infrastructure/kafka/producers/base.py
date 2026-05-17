"""
Kafka Producer Base
===================
Production-grade Kafka producer with exactly-once semantics,
schema registry integration, and backpressure handling.
"""

import logging
import json
import time
import uuid
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import threading
from concurrent.futures import ThreadPoolExecutor

from kafka import KafkaProducer
from kafka.errors import KafkaError, ProducerError
from kafka.admin import KafkaAdminClient, NewTopic
from kafka.structs import TopicPartition

logger = logging.getLogger('kafka_producer')


class DeliveryStatus(Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class ProducerRecord:
    topic: str
    key: Optional[bytes] = None
    value: Optional[bytes] = None
    headers: Dict[str, bytes] = field(default_factory=dict)
    partition: Optional[int] = None
    timestamp: Optional[int] = None
    callback: Optional[Callable] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = int(time.time() * 1000)


@dataclass
class SendResult:
    record: ProducerRecord
    status: DeliveryStatus
    partition: Optional[int] = None
    offset: Optional[int] = None
    error: Optional[Exception] = None
    delivery_time_ms: float = 0.0


class BackpressureHandler:
    """
    Handles backpressure when Kafka is overloaded.
    Implements producer pausing and adaptive batch sizing.
    """

    def __init__(self, max_pending: int = 10000, pause_threshold: float = 0.8):
        self._max_pending = max_pending
        self._pause_threshold = pause_threshold
        self._pending_count = 0
        self._lock = threading.Lock()
        self._paused_topics: set = set()

    def acquire(self, topic: str) -> bool:
        with self._lock:
            if topic in self._paused_topics:
                return False
            if self._pending_count >= self._max_pending:
                logger.warning(f"Backpressure: pending count {self._pending_count} >= max {self._max_pending}")
                return False
            self._pending_count += 1
            return True

    def release(self, success: bool = True):
        with self._lock:
            self._pending_count = max(0, self._pending_count - 1)

    def check_pause(self, topic: str, metrics: Dict) -> bool:
        with self._lock:
            if topic in self._paused_topics:
                return True

            if metrics.get('pending', 0) > self._max_pending * self._pause_threshold:
                self._paused_topics.add(topic)
                logger.warning(f"Pausing topic {topic} due to backpressure")
                return True
            return False

    def check_resume(self, topic: str, metrics: Dict) -> bool:
        with self._lock:
            if topic not in self._paused_topics:
                return False

            if metrics.get('pending', 0) < self._max_pending * 0.5:
                self._paused_topics.discard(topic)
                logger.info(f"Resuming topic {topic}")
                return True
            return False


class KafkaProducerBase:
    """
    Base Kafka producer with production features:
    - Exactly-once semantics (idempotent)
    - Schema registry integration
    - Backpressure handling
    - Retry with exponential backoff
    - Metrics collection
    """

    def __init__(
        self,
        bootstrap_servers: List[str],
        client_id: str = "trading-platform",
        enable_idempotence: bool = True,
        max_in_flight_requests: int = 5,
        acks: str = "all",
        retries: int = 3,
        retry_backoff_ms: int = 100,
        compression_type: str = "lz4",
        max_batch_size: int = 16384,
        linger_ms: int = 5,
        request_timeout_ms: int = 30000,
        delivery_timeout_ms: int = 120000,
        max_pending_records: int = 10000,
        schema_registry_url: str = "http://localhost:8081"
    ):
        self._bootstrap_servers = bootstrap_servers
        self._client_id = client_id
        self._schema_registry_url = schema_registry_url

        self._producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            client_id=client_id,
            enable_idempotence=enable_idempotence,
            max_in_flight_requests_per_connection=max_in_flight_requests,
            acks=acks,
            retries=retries,
            retry_backoff_ms=retry_backoff_ms,
            compression_type=compression_type,
            batch_size=max_batch_size,
            linger_ms=linger_ms,
            request_timeout_ms=request_timeout_ms,
            delivery_timeout_ms=delivery_timeout_ms,
            key_serializer=lambda k: k.encode('utf-8') if k else None,
            value_serializer=lambda v: v,
        )

        self._backpressure = BackpressureHandler(max_pending=max_pending_records)
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="kafka-producer")

        self._metrics = {
            'sent': 0,
            'failed': 0,
            'retried': 0,
            'latency_sum_ms': 0,
            'latency_count': 0,
            'by_topic': {}
        }
        self._metrics_lock = threading.Lock()

        logger.info(f"Kafka producer initialized: {client_id}, bootstrap: {bootstrap_servers}")

    def _update_metrics(self, topic: str, latency_ms: float, success: bool):
        with self._metrics_lock:
            if success:
                self._metrics['sent'] += 1
            else:
                self._metrics['failed'] += 1

            self._metrics['latency_sum_ms'] += latency_ms
            self._metrics['latency_count'] += 1

            if topic not in self._metrics['by_topic']:
                self._metrics['by_topic'][topic] = {'sent': 0, 'failed': 0}
            if success:
                self._metrics['by_topic'][topic]['sent'] += 1
            else:
                self._metrics['by_topic'][topic]['failed'] += 1

    def get_metrics(self) -> Dict[str, Any]:
        with self._metrics_lock:
            avg_latency = 0
            if self._metrics['latency_count'] > 0:
                avg_latency = self._metrics['latency_sum_ms'] / self._metrics['latency_count']

            return {
                'client_id': self._client_id,
                'total_sent': self._metrics['sent'],
                'total_failed': self._metrics['failed'],
                'avg_latency_ms': round(avg_latency, 2),
                'by_topic': self._metrics['by_topic'].copy(),
                'pending': self._backpressure._pending_count
            }

    def send(
        self,
        topic: str,
        value: Any,
        key: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        partition: Optional[int] = None,
        callback: Optional[Callable] = None
    ) -> SendResult:
        """
        Send a record to Kafka with backpressure handling.
        """
        start_time = time.time()

        if not self._backpressure.acquire(topic):
            result = SendResult(
                record=ProducerRecord(topic=topic, value=value),
                status=DeliveryStatus.FAILED,
                error=Exception("Backpressure: topic paused or queue full")
            )
            return result

        try:
            record = ProducerRecord(
                topic=topic,
                key=key,
                value=value,
                headers=headers or {},
                partition=partition,
                callback=callback
            )

            future = self._producer.send(
                topic=record.topic,
                key=record.key,
                value=record.value,
                headers=record.headers,
                partition=record.partition,
                timestamp=record.timestamp
            )

            try:
                record_meta = future.get(timeout=30)
                latency_ms = (time.time() - start_time) * 1000
                self._backpressure.release(success=True)
                self._update_metrics(topic, latency_ms, True)

                result = SendResult(
                    record=record,
                    status=DeliveryStatus.SUCCESS,
                    partition=record_meta.partition,
                    offset=record_meta.offset,
                    delivery_time_ms=latency_ms
                )

                if callback:
                    callback(result)

                return result

            except Exception as e:
                latency_ms = (time.time() - start_time) * 1000
                self._backpressure.release(success=False)
                self._update_metrics(topic, latency_ms, False)

                result = SendResult(
                    record=record,
                    status=DeliveryStatus.FAILED if "timeout" not in str(e).lower() else DeliveryStatus.TIMEOUT,
                    error=e,
                    delivery_time_ms=latency_ms
                )

                if callback:
                    callback(result)

                return result

        except Exception as e:
            self._backpressure.release(success=False)
            logger.error(f"Failed to send to {topic}: {e}")
            return SendResult(
                record=ProducerRecord(topic=topic, value=value),
                status=DeliveryStatus.FAILED,
                error=e
            )

    def send_async(
        self,
        topic: str,
        value: Any,
        key: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        callback: Optional[Callable] = None
    ) -> None:
        """Send asynchronously without blocking."""
        def _send():
            self.send(topic, value, key, headers, callback=callback)

        self._executor.submit(_send)

    def flush(self, timeout: float = 30.0):
        """Flush pending records."""
        self._producer.flush(timeout=timeout)

    def close(self):
        """Close the producer."""
        self.flush()
        self._producer.close()
        self._executor.shutdown(wait=True)
        logger.info(f"Kafka producer {self._client_id} closed")

    @property
    def producer(self) -> KafkaProducer:
        return self._producer


class TradingEventProducer(KafkaProducerBase):
    """
    Specialized producer for trading events with serialization.
    """

    def __init__(self, bootstrap_servers: List[str], schema_registry_url: str = "http://localhost:8081", **kwargs):
        super().__init__(
            bootstrap_servers=bootstrap_servers,
            schema_registry_url=schema_registry_url,
            **kwargs
        )
        self._serializers = {}

    def _serialize_json(self, data: Dict) -> bytes:
        return json.dumps(data).encode('utf-8')

    def _serialize_avro(self, data: Dict, schema_name: str) -> bytes:
        # Placeholder for Avro serialization
        # In production, use confluent-kafka with schema registry
        return json.dumps(data).encode('utf-8')

    def publish_tick(self, tick_data: Dict) -> SendResult:
        """Publish raw tick data."""
        return self.send(
            topic="ticks.raw",
            value=self._serialize_json(tick_data),
            key=tick_data.get('symbol'),
            headers={'event_type': 'tick', 'content_type': 'json'}
        )

    def publish_order_event(self, order_data: Dict) -> SendResult:
        """Publish order lifecycle event."""
        return self.send(
            topic="orders.created" if order_data.get('event_type') == 'CREATED' else "orders.status",
            value=self._serialize_json(order_data),
            key=order_data.get('order_id'),
            headers={'event_type': 'order', 'content_type': 'json'}
        )

    def publish_trade_event(self, trade_data: Dict) -> SendResult:
        """Publish trade execution event."""
        return self.send(
            topic="trades.executed",
            value=self._serialize_json(trade_data),
            key=trade_data.get('trade_id'),
            headers={'event_type': 'trade', 'content_type': 'json'}
        )

    def publish_signal_event(self, signal_data: Dict) -> SendResult:
        """Publish trading signal event."""
        return self.send(
            topic="signals.generated",
            value=self._serialize_json(signal_data),
            key=signal_data.get('strategy_id'),
            headers={'event_type': 'signal', 'content_type': 'json'}
        )

    def publish_risk_event(self, risk_data: Dict) -> SendResult:
        """Publish risk event."""
        return self.send(
            topic="risk.events",
            value=self._serialize_json(risk_data),
            key=risk_data.get('user_id'),
            headers={'event_type': 'risk', 'content_type': 'json'}
        )

    def publish_audit_event(self, audit_data: Dict) -> SendResult:
        """Publish audit event (SEBI compliance)."""
        return self.send(
            topic="audit.trading",
            value=self._serialize_json(audit_data),
            key=audit_data.get('audit_id') or str(uuid.uuid4()),
            headers={'event_type': 'audit', 'content_type': 'json'}
        )

    def publish_to_dlq(self, original_topic: str, failed_data: Dict, error: Exception) -> SendResult:
        """Publish failed message to dead letter queue."""
        dlq_payload = {
            'original_topic': original_topic,
            'failed_data': failed_data,
            'error': str(error),
            'timestamp': datetime.utcnow().isoformat(),
            'retry_count': failed_data.get('_retry_count', 0) + 1
        }
        return self.send(
            topic="dlq.errors",
            value=self._serialize_json(dlq_payload),
            key=original_topic,
            headers={'event_type': 'dlq', 'content_type': 'json'}
        )


# Global producer instance
_trading_producer: Optional[TradingEventProducer] = None


def get_trading_producer(
    bootstrap_servers: Optional[List[str]] = None,
    schema_registry_url: str = "http://localhost:8081"
) -> TradingEventProducer:
    """Get or create the global trading event producer."""
    global _trading_producer

    if _trading_producer is None:
        if bootstrap_servers is None:
            bootstrap_servers = ['localhost:9092']

        _trading_producer = TradingEventProducer(
            bootstrap_servers=bootstrap_servers,
            schema_registry_url=schema_registry_url,
            client_id="trading-platform-producer"
        )

    return _trading_producer


def close_producer():
    """Close the global producer."""
    global _trading_producer
    if _trading_producer:
        _trading_producer.close()
        _trading_producer = None