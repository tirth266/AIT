"""
Idempotency Manager
====================
Ensures duplicate order prevention and exactly-once processing.
"""

import logging
import hashlib
import json
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from dataclasses import dataclass, field

logger = logging.getLogger('oms.idempotency')


@dataclass
class IdempotencyKey:
    """Idempotency key with metadata."""
    key: str
    user_id: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    processed: bool = False
    result: Optional[Dict] = None
    request_hash: str = ""
    expires_at: Optional[datetime] = None


class IdempotencyManager:
    """
    Manages idempotent request processing to prevent duplicates.
    Uses Redis for fast checking and MongoDB for persistence.
    """
    
    KEY_PREFIX = "idempotency:"
    TTL_SECONDS = 86400
    
    def __init__(self):
        from ..database.connection import get_redis
        self.redis = get_redis()
        self._local_cache: Dict[str, IdempotencyKey] = {}
    
    def generate_key(self, user_id: str, order_data: Dict) -> str:
        """Generate deterministic idempotency key from order data."""
        canonical = {
            'user_id': user_id,
            'symbol': order_data.get('symbol', '').upper(),
            'order_type': order_data.get('order_type', 'MARKET').upper(),
            'transaction_type': order_data.get('transaction_type', 'BUY').upper(),
            'quantity': order_data.get('quantity', 0),
            'price': order_data.get('price', 0),
            'exchange': order_data.get('exchange', 'NSE').upper(),
            'product_type': order_data.get('product_type', 'MIS').upper(),
        }
        
        canonical_str = json.dumps(canonical, sort_keys=True)
        request_hash = hashlib.sha256(canonical_str.encode()).hexdigest()
        
        timestamp = order_data.get('timestamp') or datetime.now(timezone.utc).isoformat()
        key = f"{user_id}:{request_hash[:16]}:{timestamp[:10]}"
        
        return key
    
    async def check_and_reserve(self, idempotency_key: str, user_id: str, 
                                  order_data: Dict) -> tuple[bool, Optional[Dict]]:
        """
        Check if request is duplicate, reserve key if new.
        Returns (is_duplicate, previous_result)
        """
        if idempotency_key in self._local_cache:
            cached = self._local_cache[idempotency_key]
            if cached.processed:
                return True, cached.result
            return False, None
        
        if self.redis:
            try:
                redis_key = f"{self.KEY_PREFIX}{idempotency_key}"
                existing = self.redis.get(redis_key)
                
                if existing:
                    result = json.loads(existing)
                    return True, result.get('result')
                
                key_data = {
                    'user_id': user_id,
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'status': 'processing',
                }
                self.redis.setex(redis_key, self.TTL_SECONDS, json.dumps(key_data))
                
                self._local_cache[idempotency_key] = IdempotencyKey(
                    key=idempotency_key,
                    user_id=user_id,
                    request_hash=hashlib.md5(idempotency_key.encode()).hexdigest()
                )
                
                return False, None
                
            except Exception as e:
                logger.error(f"Redis idempotency check failed: {e}")
        
        return False, None
    
    async def mark_completed(self, idempotency_key: str, result: Dict) -> None:
        """Mark idempotency key as processed with result."""
        if idempotency_key in self._local_cache:
            self._local_cache[idempotency_key].processed = True
            self._local_cache[idempotency_key].result = result
        
        if self.redis:
            try:
                redis_key = f"{self.KEY_PREFIX}{idempotency_key}"
                data = {
                    'status': 'completed',
                    'result': result,
                    'completed_at': datetime.now(timezone.utc).isoformat(),
                }
                self.redis.setex(redis_key, self.TTL_SECONDS, json.dumps(data))
            except Exception as e:
                logger.error(f"Failed to mark idempotency completed: {e}")
    
    async def mark_failed(self, idempotency_key: str, error: str) -> None:
        """Mark idempotency key as failed."""
        if idempotency_key in self._local_cache:
            self._local_cache[idempotency_key].processed = True
            self._local_cache[idempotency_key].result = {'error': error}
        
        if self.redis:
            try:
                redis_key = f"{self.KEY_PREFIX}{idempotency_key}"
                data = {
                    'status': 'failed',
                    'error': error,
                    'failed_at': datetime.now(timezone.utc).isoformat(),
                }
                self.redis.setex(redis_key, self.TTL_SECONDS, json.dumps(data))
            except Exception as e:
                logger.error(f"Failed to mark idempotency failed: {e}")
    
    def validate_unique_order(self, user_id: str, symbol: str, 
                              transaction_type: str, quantity: int) -> bool:
        """Quick validation for duplicate pending orders."""
        for key in self._local_cache:
            if key.startswith(user_id):
                return False
        return True


idempotency_manager = IdempotencyManager()


def get_idempotency_manager() -> IdempotencyManager:
    return idempotency_manager