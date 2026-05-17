"""
Order Repository
================
MongoDB-based persistence for orders with Redis caching.
"""

import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from dataclasses import asdict
import hashlib
from bson import ObjectId

from ..database.connection import get_db, get_redis
from .state_machine import OrderState, OrderEvent, StateTransition


logger = logging.getLogger('oms.repository')


class OrderRepository:
    """
    Repository pattern for order persistence.
    Supports MongoDB with Redis caching layer.
    """
    
    COLLECTION = "orders"
    TRANSITIONS_COLLECTION = "order_transitions"
    CACHE_TTL = 300
    
    def __init__(self):
        self.db = get_db()
        self.redis = get_redis()
    
    def _cache_key(self, order_id: str) -> str:
        return f"order:{order_id}"
    
    def _order_cache_key(self, user_id: str, symbol: str) -> str:
        return f"user_orders:{user_id}:{symbol}"
    
    async def create(self, order_data: Dict) -> str:
        """Create new order in MongoDB."""
        collection = self.db[self.COLLECTION]
        
        order_data['created_at'] = datetime.now(timezone.utc)
        order_data['updated_at'] = datetime.now(timezone.utc)
        
        result = await collection.insert_one(order_data)
        
        self._cache_order(order_data)
        
        logger.info(f"Order created: {order_data.get('order_id')}")
        return str(result.inserted_id)
    
    async def update(self, order_id: str, update_data: Dict) -> bool:
        """Update order in MongoDB and cache."""
        collection = self.db[self.COLLECTION]
        
        update_data['updated_at'] = datetime.now(timezone.utc)
        
        result = await collection.update_one(
            {'order_id': order_id},
            {'$set': update_data}
        )
        
        self._invalidate_cache(order_id)
        
        return result.modified_count > 0
    
    async def find_by_id(self, order_id: str) -> Optional[Dict]:
        """Get order by ID with Redis cache."""
        cached = self._get_cache(order_id)
        if cached:
            return cached
        
        collection = self.db[self.COLLECTION]
        order = await collection.find_one({'order_id': order_id})
        
        if order:
            order.pop('_id', None)
            self._cache_order(order)
        
        return order
    
    async def find_by_user(self, user_id: str, filters: Optional[Dict] = None) -> List[Dict]:
        """Find orders by user with optional filters."""
        collection = self.db[self.COLLECTION]
        
        query = {'user_id': user_id}
        if filters:
            query.update(filters)
        
        cursor = collection.find(query).sort('created_at', -1)
        orders = await cursor.to_list(length=1000)
        
        return [{**o, '_id': str(o.get('_id', ''))} for o in orders]
    
    async def find_pending(self, limit: int = 100) -> List[Dict]:
        """Find all pending orders for processing."""
        collection = self.db[self.COLLECTION]
        
        pending_states = [
            OrderState.PENDING_SUBMISSION.value,
            OrderState.SUBMITTED.value,
            OrderState.ACKNOWLEDGED.value,
            OrderState.OPEN.value,
            OrderState.PARTIALLY_FILLED.value,
        ]
        
        cursor = collection.find({
            'status': {'$in': pending_states},
            'mode': 'live'
        }).sort('created_at', 1).limit(limit)
        
        orders = await cursor.to_list(length=limit)
        return [{**o, '_id': str(o.get('_id', ''))} for o in orders]
    
    async def find_by_parent(self, parent_order_id: str) -> List[Dict]:
        """Find child orders for a parent order."""
        collection = self.db[self.COLLECTION]
        
        cursor = collection.find({'parent_order_id': parent_order_id})
        orders = await cursor.to_list(length=100)
        
        return [{**o, '_id': str(o.get('_id', ''))} for o in orders]
    
    async def save_transition(self, transition: StateTransition) -> None:
        """Save state transition to MongoDB."""
        collection = self.db[self.TRANSITIONS_COLLECTION]
        
        transition_data = transition.to_dict()
        transition_data['timestamp'] = transition.timestamp
        
        await collection.insert_one(transition_data)
    
    async def get_transitions(self, order_id: str, limit: int = 100) -> List[Dict]:
        """Get state transitions for an order."""
        collection = self.db[self.TRANSITIONS_COLLECTION]
        
        cursor = collection.find(
            {'order_id': order_id}
        ).sort('timestamp', 1).limit(limit)
        
        return await cursor.to_list(length=limit)
    
    async def add_child_order(self, parent_id: str, child_id: str) -> bool:
        """Add child order reference to parent."""
        collection = self.db[self.COLLECTION]
        
        result = await collection.update_one(
            {'order_id': parent_id},
            {'$addToSet': {'child_orders': child_id}}
        )
        
        self._invalidate_cache(parent_id)
        return result.modified_count > 0
    
    def _cache_order(self, order: Dict) -> None:
        """Cache order in Redis."""
        if self.redis:
            try:
                key = self._cache_key(order['order_id'])
                self.redis.setex(key, self.CACHE_TTL, json.dumps(order, default=str))
            except Exception as e:
                logger.warning(f"Failed to cache order: {e}")
    
    def _get_cache(self, order_id: str) -> Optional[Dict]:
        """Get order from Redis cache."""
        if self.redis:
            try:
                key = self._cache_key(order_id)
                cached = self.redis.get(key)
                if cached:
                    return json.loads(cached)
            except Exception as e:
                logger.warning(f"Failed to get cached order: {e}")
        return None
    
    def _invalidate_cache(self, order_id: str) -> None:
        """Invalidate Redis cache for order."""
        if self.redis:
            try:
                key = self._cache_key(order_id)
                self.redis.delete(key)
            except Exception as e:
                logger.warning(f"Failed to invalidate cache: {e}")
    
    async def get_order_count(self, user_id: str, status: Optional[str] = None) -> int:
        """Get order count for user with optional status filter."""
        collection = self.db[self.COLLECTION]
        
        query = {'user_id': user_id}
        if status:
            query['status'] = status
        
        return await collection.count_documents(query)


order_repository = OrderRepository()


def get_order_repository() -> OrderRepository:
    return order_repository