"""
Event Bus
=========
Async event-driven architecture for strategy communication.
"""

import asyncio
import logging
import time
from typing import Dict, Optional, Any, Callable, List, Set
from dataclasses import dataclass, field
from collections import defaultdict
from datetime import datetime
import uuid
import weakref

logger = logging.getLogger('event_bus')


@dataclass
class Event:
    """Event structure."""
    event_id: str
    event_type: str
    data: Dict[str, Any]
    source: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class EventBus:
    """
    Async event bus for pub/sub communication.
    
    Features:
    - Topic-based subscription
    - Event filtering
    - Async event handlers
    - Event persistence
    - Dead letter queue
    """

    def __init__(self, max_queue_size: int = 10000):
        self._max_queue_size = max_queue_size
        self._subscribers: Dict[str, List[weakref.ref]] = defaultdict(list)
        self._event_queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self._running = False
        self._processor_task: Optional[asyncio.Task] = None
        
        self._event_history: List[Event] = []
        self._max_history = 1000
        
        self._dead_letter: List[Event] = []
        self._dead_letter_max = 100
        
        self._stats = {
            'events_published': 0,
            'events_delivered': 0,
            'events_failed': 0
        }

    async def start(self) -> None:
        """Start the event bus."""
        if self._running:
            return
        
        self._running = True
        self._processor_task = asyncio.create_task(self._process_events())
        logger.info("EventBus started")

    async def stop(self, timeout: float = 10.0) -> None:
        """Stop the event bus."""
        self._running = False
        
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await asyncio.wait_for(self._processor_task, timeout=timeout)
            except asyncio.CancelledError:
                pass
        
        logger.info("EventBus stopped")

    async def _process_events(self) -> None:
        """Process events from queue."""
        while self._running:
            try:
                event = await asyncio.wait_for(
                    self._event_queue.get(),
                    timeout=1.0
                )
                await self._deliver_event(event)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Event processing error: {e}")
                self._stats['events_failed'] += 1

    async def _deliver_event(self, event: Event) -> None:
        """Deliver event to subscribers."""
        try:
            handlers = self._subscribers.get(event.event_type, [])
            
            for ref in list(handlers):
                handler = ref()
                if handler:
                    if asyncio.iscoroutinefunction(handler):
                        try:
                            await handler(event)
                        except Exception as e:
                            logger.error(f"Event handler error: {e}")
                            self._stats['events_failed'] += 1
                    else:
                        try:
                            handler(event)
                        except Exception as e:
                            logger.error(f"Event handler error: {e}")
                            self._stats['events_failed'] += 1
            
            self._event_history.append(event)
            if len(self._event_history) > self._max_history:
                self._event_history.pop(0)
            
            self._stats['events_delivered'] += 1
            
        except Exception as e:
            logger.error(f"Event delivery error: {e}")
            self._dead_letter.append(event)
            if len(self._dead_letter) > self._dead_letter_max:
                self._dead_letter.pop(0)

    async def publish(
        self,
        event_type: str,
        data: Dict[str, Any],
        source: str = 'system',
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Publish an event."""
        event = Event(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            data=data,
            source=source,
            correlation_id=correlation_id,
            metadata=metadata or {}
        )
        
        try:
            self._event_queue.put_nowait(event)
            self._stats['events_published'] += 1
            return event.event_id
        except asyncio.QueueFull:
            logger.warning(f"Event queue full, dropping event: {event_type}")
            self._dead_letter.append(event)
            return event.event_id

    def subscribe(
        self,
        event_type: str,
        handler: Callable,
        filter_func: Optional[Callable] = None
    ) -> str:
        """Subscribe to an event type."""
        subscription_id = str(uuid.uuid4())
        
        if filter_func:
            async def filtered_handler(event: Event):
                if await filter_func(event):
                    await handler(event)
            ref = weakref.ref(filtered_handler)
        else:
            ref = weakref.ref(handler)
        
        self._subscribers[event_type].append(ref)
        
        logger.debug(f"Subscribed to {event_type} with handler")
        return subscription_id

    def unsubscribe(self, event_type: str, subscription_id: str) -> bool:
        """Unsubscribe from event type."""
        handlers = self._subscribers.get(event_type, [])
        
        for i, ref in enumerate(handlers):
            handler = ref()
            if handler and str(id(handler)) == subscription_id:
                handlers.pop(i)
                return True
        
        return False

    async def publish_signal(
        self,
        strategy_id: str,
        signal: Dict[str, Any]
    ) -> str:
        """Publish a trading signal event."""
        return await self.publish(
            event_type='signal_generated',
            data={
                'strategy_id': strategy_id,
                'signal': signal
            },
            source=f'strategy_{strategy_id}'
        )

    async def publish_trade(
        self,
        strategy_id: str,
        trade: Dict[str, Any]
    ) -> str:
        """Publish a trade execution event."""
        return await self.publish(
            event_type='trade_executed',
            data={
                'strategy_id': strategy_id,
                'trade': trade
            },
            source=f'strategy_{strategy_id}'
        )

    async def publish_market_data(
        self,
        symbol: str,
        candles: List[Dict],
        timeframe: str
    ) -> str:
        """Publish market data event."""
        return await self.publish(
            event_type='market_data',
            data={
                'symbol': symbol,
                'candles': candles,
                'timeframe': timeframe
            },
            source='market_data'
        )

    def get_recent_events(self, event_type: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Get recent events."""
        events = self._event_history
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        events = events[-limit:]
        
        return [
            {
                'event_id': e.event_id,
                'event_type': e.event_type,
                'data': e.data,
                'source': e.source,
                'timestamp': e.timestamp.isoformat()
            }
            for e in events
        ]

    def get_dead_letter(self) -> List[Dict]:
        """Get dead letter events."""
        return [
            {
                'event_id': e.event_id,
                'event_type': e.event_type,
                'data': e.data,
                'timestamp': e.timestamp.isoformat()
            }
            for e in self._dead_letter
        ]

    def get_stats(self) -> Dict:
        """Get event bus statistics."""
        return {
            **self._stats,
            'subscribers': {
                event_type: len(handlers)
                for event_type, handlers in self._subscriptions().items()
            },
            'queue_size': self._event_queue.qsize(),
            'dead_letter_count': len(self._dead_letter)
        }

    def _subscriptions(self) -> Dict[str, int]:
        """Get subscription counts."""
        return {
            event_type: len(handlers)
            for event_type, handlers in self._subscribers.items()
        }


_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get the global event bus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus