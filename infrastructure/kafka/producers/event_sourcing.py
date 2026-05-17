"""
Event Sourcing Infrastructure
==============================
Implements event sourcing pattern for trading engine state management.
Provides aggregate roots, event store, and state reconstruction.
"""

import logging
import json
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
from collections import defaultdict

logger = logging.getLogger('event_sourcing')


class EventType(str, Enum):
    # Order events
    ORDER_CREATED = "ORDER_CREATED"
    ORDER_SUBMITTED = "ORDER_SUBMITTED"
    ORDER_FILLED = "ORDER_FILLED"
    ORDER_PARTIAL_FILL = "ORDER_PARTIAL_FILL"
    ORDER_CANCELLED = "ORDER_CANCELLED"
    ORDER_REJECTED = "ORDER_REJECTED"
    ORDER_MODIFIED = "ORDER_MODIFIED"

    # Position events
    POSITION_OPENED = "POSITION_OPENED"
    POSITION_CLOSED = "POSITION_CLOSED"
    POSITION_MODIFIED = "POSITION_MODIFIED"

    # Trade events
    TRADE_EXECUTED = "TRADE_EXECUTED"
    TRADE_SETTLED = "TRADE_SETTLED"

    # Risk events
    MARGIN_CHECK = "MARGIN_CHECK"
    RISK_LIMIT_BREACH = "RISK_LIMIT_BREACH"

    # Signal events
    SIGNAL_GENERATED = "SIGNAL_GENERATED"
    SIGNAL_EXECUTED = "SIGNAL_EXECUTED"


@dataclass
class BaseEvent:
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType = EventType.ORDER_CREATED
    aggregate_id: str = ""
    aggregate_type: str = ""
    version: int = 1
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            'event_id': self.event_id,
            'event_type': self.event_type.value,
            'aggregate_id': self.aggregate_id,
            'aggregate_type': self.aggregate_type,
            'version': self.version,
            'timestamp': self.timestamp.isoformat(),
            'correlation_id': self.correlation_id,
            'causation_id': self.causation_id,
            'metadata': self.metadata
        }


@dataclass
class OrderCreatedEvent(BaseEvent):
    user_id: str = ""
    strategy_id: Optional[str] = None
    symbol: str = ""
    exchange: str = "NSE"
    transaction_type: str = "BUY"
    order_type: str = "MARKET"
    product_type: str = "MIS"
    quantity: int = 0
    price: float = 0.0
    trigger_price: float = 0.0
    validity: str = "DAY"
    mode: str = "paper"
    source: str = "manual"

    def __post_init__(self):
        self.event_type = EventType.ORDER_CREATED
        self.aggregate_type = "Order"
        self.aggregate_id = self.metadata.get('order_id', '')


@dataclass
class OrderFilledEvent(BaseEvent):
    order_id: str = ""
    filled_quantity: int = 0
    average_price: float = 0.0

    def __post_init__(self):
        self.event_type = EventType.ORDER_FILLED
        self.aggregate_type = "Order"


@dataclass
class TradeExecutedEvent(BaseEvent):
    trade_id: str = ""
    order_id: str = ""
    position_id: Optional[str] = None
    user_id: str = ""
    symbol: str = ""
    exchange: str = "NSE"
    transaction_type: str = "BUY"
    quantity: int = 0
    price: float = 0.0
    brokerage: float = 0.0
    mode: str = "paper"
    broker: str = ""

    def __post_init__(self):
        self.event_type = EventType.TRADE_EXECUTED
        self.aggregate_type = "Trade"


@dataclass
class PositionOpenedEvent(BaseEvent):
    position_id: str = ""
    user_id: str = ""
    strategy_id: Optional[str] = None
    symbol: str = ""
    exchange: str = "NSE"
    product_type: str = "MIS"
    quantity: int = 0
    entry_price: float = 0.0
    mode: str = "paper"

    def __post_init__(self):
        self.event_type = EventType.POSITION_OPENED
        self.aggregate_type = "Position"


class EventStore:
    """
    Event store for persisting and retrieving events.
    Integrates with Kafka for event streaming.
    """

    def __init__(self, kafka_producer=None):
        self._producer = kafka_producer
        self._in_memory_store: Dict[str, List[BaseEvent]] = defaultdict(list)
        self._event_handlers: Dict[EventType, List[Callable]] = defaultdict(list)

    def append(self, event: BaseEvent) -> None:
        """Append event to store and publish to Kafka."""
        aggregate_events = self._in_memory_store[event.aggregate_id]
        event.version = len(aggregate_events) + 1
        aggregate_events.append(event)

        if self._producer:
            self._publish_event(event)

        self._dispatch_event(event)

    def _publish_event(self, event: BaseEvent):
        """Publish event to Kafka."""
        try:
            topic_map = {
                EventType.ORDER_CREATED: 'orders.created',
                EventType.ORDER_FILLED: 'orders.status',
                EventType.ORDER_CANCELLED: 'orders.status',
                EventType.TRADE_EXECUTED: 'trades.executed',
                EventType.POSITION_OPENED: 'risk.position',
                EventType.POSITION_CLOSED: 'risk.position',
                EventType.SIGNAL_GENERATED: 'signals.generated'
            }

            topic = topic_map.get(event.event_type, 'system.health')
            self._producer.send(topic, event.to_dict(), key=event.aggregate_id)

        except Exception as e:
            logger.error(f"Failed to publish event {event.event_id}: {e}")

    def _dispatch_event(self, event: BaseEvent):
        """Dispatch event to registered handlers."""
        for handler in self._event_handlers.get(event.event_type, []):
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Event handler error for {event.event_type}: {e}")

    def get_events_for_aggregate(self, aggregate_id: str) -> List[BaseEvent]:
        """Get all events for an aggregate."""
        return self._in_memory_store.get(aggregate_id, []).copy()

    def get_events_by_type(self, event_type: EventType) -> List[BaseEvent]:
        """Get all events of a specific type."""
        events = []
        for aggregate_events in self._in_memory_store.values():
            events.extend([e for e in aggregate_events if e.event_type == event_type])
        return events

    def register_handler(self, event_type: EventType, handler: Callable):
        """Register an event handler."""
        self._event_handlers[event_type].append(handler)

    def replay(self, aggregate_id: str, from_version: int = 1) -> List[BaseEvent]:
        """Replay events for an aggregate from a specific version."""
        events = self._in_memory_store.get(aggregate_id, [])
        return [e for e in events if e.version >= from_version]


class EventSourcedAggregate(ABC):
    """
    Base class for event-sourced aggregates.
    """

    def __init__(self, aggregate_id: str, event_store: EventStore):
        self._id = aggregate_id
        self._event_store = event_store
        self._uncommitted_events: List[BaseEvent] = []
        self._version = 0

    @property
    def id(self) -> str:
        return self._id

    @property
    def version(self) -> int:
        return self._version

    def _add_uncommitted_event(self, event: BaseEvent):
        """Add an event to the uncommitted list."""
        event.aggregate_id = self._id
        event.version = self._version + 1
        self._uncommitted_events.append(event)

    def commit(self):
        """Commit all uncommitted events to the event store."""
        for event in self._uncommitted_events:
            self._event_store.append(event)
            self._version = event.version
        self._uncommitted_events.clear()

    def load_from_events(self, events: List[BaseEvent]):
        """Reconstruct aggregate state from events."""
        for event in events:
            self._apply_event(event)
            self._version = event.version

    @abstractmethod
    def _apply_event(self, event: BaseEvent):
        """Apply an event to update aggregate state."""
        pass


class OrderAggregate(EventSourcedAggregate):
    """
    Event-sourced Order aggregate.
    """

    def __init__(self, order_id: str, event_store: EventStore):
        super().__init__(order_id, event_store)
        self._status = "NEW"
        self._filled_quantity = 0
        self._average_price = 0.0
        self._cancelled_quantity = 0

    @property
    def status(self) -> str:
        return self._status

    @property
    def filled_quantity(self) -> int:
        return self._filled_quantity

    @property
    def average_price(self) -> float:
        return self._average_price

    def create_order(
        self,
        user_id: str,
        symbol: str,
        transaction_type: str,
        quantity: int,
        order_type: str = "MARKET",
        price: float = 0.0,
        validity: str = "DAY",
        mode: str = "paper",
        strategy_id: Optional[str] = None
    ):
        """Create a new order."""
        event = OrderCreatedEvent(
            aggregate_id=self._id,
            metadata={
                'order_id': self._id,
                'user_id': user_id,
                'symbol': symbol,
                'transaction_type': transaction_type,
                'quantity': quantity,
                'order_type': order_type,
                'price': price,
                'validity': validity,
                'mode': mode,
                'strategy_id': strategy_id
            },
            user_id=user_id,
            strategy_id=strategy_id,
            symbol=symbol,
            transaction_type=transaction_type,
            order_type=order_type,
            quantity=quantity,
            price=price,
            validity=validity,
            mode=mode
        )
        self._add_uncommitted_event(event)
        return self

    def fill(self, filled_quantity: int, average_price: float):
        """Record a fill."""
        event = OrderFilledEvent(
            aggregate_id=self._id,
            metadata={'filled_quantity': filled_quantity, 'average_price': average_price},
            order_id=self._id,
            filled_quantity=filled_quantity,
            average_price=average_price
        )
        self._add_uncommitted_event(event)
        return self

    def _apply_event(self, event: BaseEvent):
        """Apply event to update state."""
        if event.event_type == EventType.ORDER_CREATED:
            self._status = "OPEN"
        elif event.event_type == EventType.ORDER_FILLED:
            self._filled_quantity += event.filled_quantity
            self._average_price = event.average_price
            if self._filled_quantity >= getattr(self, '_original_quantity', self._filled_quantity):
                self._status = "FILLED"


class StateReconstructor:
    """
    Reconstructs application state from event store.
    """

    def __init__(self, event_store: EventStore):
        self._event_store = event_store

    def reconstruct_order(self, order_id: str) -> Optional[OrderAggregate]:
        """Reconstruct an order from events."""
        events = self._event_store.get_events_for_aggregate(order_id)
        if not events:
            return None

        aggregate = OrderAggregate(order_id, self._event_store)
        aggregate.load_from_events(events)
        return aggregate

    def get_order_history(self, user_id: str) -> List[Dict]:
        """Get order history for a user by replaying events."""
        # In production, this would query the event store efficiently
        # For now, return summary of order events
        order_events = self._event_store.get_events_by_type(EventType.ORDER_CREATED)
        return [
            {
                'order_id': e.aggregate_id,
                'user_id': e.metadata.get('user_id'),
                'symbol': e.metadata.get('symbol'),
                'quantity': e.metadata.get('quantity'),
                'timestamp': e.timestamp.isoformat()
            }
            for e in order_events
            if e.metadata.get('user_id') == user_id
        ]


class ProjectionBuilder:
    """
    Builds read models (projections) from event stream.
    """

    def __init__(self, event_store: EventStore):
        self._event_store = event_store
        self._projections: Dict[str, Any] = {}

    def build_position_projection(self) -> Dict[str, Any]:
        """Build current position state from events."""
        positions = {}
        position_opened = self._event_store.get_events_by_type(EventType.POSITION_OPENED)
        position_closed = self._event_store.get_events_by_type(EventType.POSITION_CLOSED)

        for event in position_opened:
            pos_id = event.position_id
            positions[pos_id] = {
                'position_id': pos_id,
                'user_id': event.user_id,
                'symbol': event.symbol,
                'quantity': event.quantity,
                'entry_price': event.entry_price,
                'status': 'OPEN'
            }

        for event in position_closed:
            pos_id = event.position_id
            if pos_id in positions:
                positions[pos_id]['status'] = 'CLOSED'
                positions[pos_id]['closed_at'] = event.timestamp.isoformat()

        return positions


# Global event store
_event_store: Optional[EventStore] = None


def get_event_store(kafka_producer=None) -> EventStore:
    """Get or create the global event store."""
    global _event_store
    if _event_store is None:
        _event_store = EventStore(kafka_producer)
    return _event_store