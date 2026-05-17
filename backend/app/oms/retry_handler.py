"""
Retry Handler & Dead Letter Queue
==================================
Implements exponential backoff retry with DLQ for failed orders.
"""

import logging
import asyncio
import json
from typing import Dict, Optional, Callable, Any, List
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
from collections import deque

logger = logging.getLogger('oms.retry')


class RetryStrategy(str, Enum):
    EXPONENTIAL = "EXPONENTIAL"
    LINEAR = "LINEAR"
    FIBONACCI = "FIBONACCI"


class FailureReason(str, Enum):
    TIMEOUT = "TIMEOUT"
    CONNECTION_ERROR = "CONNECTION_ERROR"
    BROKER_REJECT = "BROKER_REJECT"
    RATE_LIMIT = "RATE_LIMIT"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INSUFFICIENT_MARGIN = "INSUFFICIENT_MARGIN"
    UNKNOWN = "UNKNOWN"


@dataclass
class RetryAttempt:
    """Single retry attempt record."""
    attempt_number: int
    timestamp: datetime
    error: str
    failure_reason: FailureReason
    duration_ms: float = 0


@dataclass
class RetryContext:
    """Context for retryable operation."""
    order_id: str
    user_id: str
    operation: str
    payload: Dict
    retry_count: int = 0
    max_retries: int = 3
    base_delay_ms: int = 1000
    max_delay_ms: int = 30000
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    attempts: List[RetryAttempt] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_attempt_at: Optional[datetime] = None
    
    def get_delay(self) -> float:
        """Calculate next retry delay based on strategy."""
        if self.retry_count >= self.max_retries:
            return -1
        
        if self.strategy == RetryStrategy.EXPONENTIAL:
            delay = self.base_delay_ms * (2 ** self.retry_count)
        elif self.strategy == RetryStrategy.LINEAR:
            delay = self.base_delay_ms * (self.retry_count + 1)
        elif self.strategy == RetryStrategy.FIBONACCI:
            delay = self.base_delay_ms * self._fibonacci(self.retry_count + 2)
        else:
            delay = self.base_delay_ms
        
        return min(delay, self.max_delay_ms) / 1000.0
    
    def _fibonacci(self, n: int) -> int:
        a, b = 0, 1
        for _ in range(n):
            a, b = b, a + b
        return a
    
    def can_retry(self) -> bool:
        return self.retry_count < self.max_retries


class DeadLetterQueue:
    """
    Dead Letter Queue for orders that fail after all retries.
    Supports manual review and replay.
    """
    
    COLLECTION = "dead_letter_queue"
    
    def __init__(self):
        from ..database.connection import get_db
        self.db = get_db()
    
    async def add(self, context: RetryContext, error: str, failure_reason: FailureReason) -> str:
        """Add failed order to dead letter queue."""
        collection = self.db[self.COLLECTION]
        
        record = {
            'order_id': context.order_id,
            'user_id': context.user_id,
            'operation': context.operation,
            'payload': context.payload,
            'retry_count': context.retry_count,
            'max_retries': context.max_retries,
            'error': error,
            'failure_reason': failure_reason.value,
            'attempts': [
                {
                    'attempt_number': a.attempt_number,
                    'timestamp': a.timestamp.isoformat(),
                    'error': a.error,
                    'failure_reason': a.failure_reason.value,
                    'duration_ms': a.duration_ms,
                }
                for a in context.attempts
            ],
            'created_at': datetime.now(timezone.utc),
            'status': 'PENDING_REVIEW',
            'reviewed_by': None,
            'review_notes': None,
            'replayed': False,
        }
        
        result = await collection.insert_one(record)
        logger.warning(f"Order {context.order_id} added to DLQ: {error}")
        
        return str(result.inserted_id)
    
    async def get_pending(self, limit: int = 100) -> List[Dict]:
        """Get pending DLQ entries for review."""
        collection = self.db[self.COLLECTION]
        
        cursor = collection.find({
            'status': 'PENDING_REVIEW'
        }).sort('created_at', -1).limit(limit)
        
        return await cursor.to_list(length=limit)
    
    async def mark_reviewed(self, dlq_id: str, reviewed_by: str, 
                            notes: str, action: str) -> bool:
        """Mark DLQ entry as reviewed."""
        collection = self.db[self.COLLECTION]
        
        result = await collection.update_one(
            {'_id': dlq_id},
            {'$set': {
                'status': 'REVIEWED',
                'reviewed_by': reviewed_by,
                'review_notes': notes,
                'action': action,
                'reviewed_at': datetime.now(timezone.utc),
            }}
        )
        
        return result.modified_count > 0
    
    async def replay(self, dlq_id: str) -> Optional[Dict]:
        """Replay a failed order from DLQ."""
        collection = self.db[self.COLLECTION]
        
        entry = await collection.find_one({'_id': dlq_id})
        if not entry:
            return None
        
        await collection.update_one(
            {'_id': dlq_id},
            {'$set': {
                'replayed': True,
                'replayed_at': datetime.now(timezone.utc),
            }}
        )
        
        return entry.get('payload')


class RetryHandler:
    """
    Handles retry logic with exponential backoff.
    Integrates with Dead Letter Queue for failed orders.
    """
    
    def __init__(self):
        self.dlq = DeadLetterQueue()
        self._retry_queue: deque = deque(maxlen=10000)
        self._running = False
        self._handlers: Dict[str, Callable] = {}
    
    def register_handler(self, operation: str, handler: Callable) -> None:
        """Register handler for specific operation."""
        self._handlers[operation] = handler
    
    async def execute_with_retry(self, context: RetryContext) -> tuple[bool, Any]:
        """
        Execute operation with retry logic.
        Returns (success, result_or_error)
        """
        start_time = datetime.now(timezone.utc)
        
        while context.can_retry():
            try:
                handler = self._handlers.get(context.operation)
                if not handler:
                    return False, f"No handler for operation: {context.operation}"
                
                result = await handler(context.payload)
                
                context.retry_count += 1
                return True, result
                
            except Exception as e:
                duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                
                failure_reason = self._classify_failure(e)
                
                attempt = RetryAttempt(
                    attempt_number=context.retry_count + 1,
                    timestamp=datetime.now(timezone.utc),
                    error=str(e),
                    failure_reason=failure_reason,
                    duration_ms=duration_ms,
                )
                context.attempts.append(attempt)
                
                context.retry_count += 1
                context.last_attempt_at = datetime.now(timezone.utc)
                
                if not context.can_retry():
                    break
                
                delay = context.get_delay()
                if delay > 0:
                    logger.info(f"Retrying {context.order_id} in {delay:.2f}s (attempt {context.retry_count})")
                    await asyncio.sleep(delay)
        
        await self.dlq.add(context, "Max retries exceeded", FailureReason.UNKNOWN)
        return False, "Max retries exceeded"
    
    def _classify_failure(self, error: Exception) -> FailureReason:
        error_str = str(error).lower()
        
        if 'timeout' in error_str:
            return FailureReason.TIMEOUT
        elif 'connection' in error_str or 'network' in error_str:
            return FailureReason.CONNECTION_ERROR
        elif 'rate limit' in error_str or 'throttl' in error_str:
            return FailureReason.RATE_LIMIT
        elif 'margin' in error_str or 'insufficient' in error_str:
            return FailureReason.INSUFFICIENT_MARGIN
        elif 'reject' in error_str or 'invalid' in error_str:
            return FailureReason.BROKER_REJECT
        else:
            return FailureReason.UNKNOWN
    
    async def start(self) -> None:
        """Start background retry processor."""
        self._running = True
        asyncio.create_task(self._process_retry_queue())
        logger.info("Retry handler started")
    
    async def stop(self) -> None:
        """Stop retry processor."""
        self._running = False
        logger.info("Retry handler stopped")
    
    async def _process_retry_queue(self) -> None:
        """Background task to process retry queue."""
        while self._running:
            try:
                if self._retry_queue:
                    context = self._retry_queue.popleft()
                    await self.execute_with_retry(context)
            except Exception as e:
                logger.error(f"Retry queue processing error: {e}")
            
            await asyncio.sleep(1)
    
    def add_to_queue(self, context: RetryContext) -> None:
        """Add context to retry queue."""
        self._retry_queue.append(context)


retry_handler = RetryHandler()
dead_letter_queue = DeadLetterQueue()


def get_retry_handler() -> RetryHandler:
    return retry_handler


def get_dead_letter_queue() -> DeadLetterQueue:
    return dead_letter_queue