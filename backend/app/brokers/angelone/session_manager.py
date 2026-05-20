"""
Angel One Persistent Session Manager
====================================
Production-grade session lifecycle management with Redis + MongoDB persistence.
Handles token storage, refresh, and automatic reconnection.

Architecture:
- Redis: Fast active session cache
- MongoDB: Persistent backup storage
- WebSocket: Automatic recovery after session restore

Author: Staff Engineer
"""

import os
import time
import json
import logging
from typing import Dict, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from threading import Lock, Timer

logger = logging.getLogger('angelone.session_manager')


@dataclass
class AngelOneSessionData:
    """Session data structure for Angel One broker."""
    user_id: str
    client_id: str
    api_key: str
    jwt_token: str
    refresh_token: str
    feed_token: str
    mac_address: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    last_refresh: Optional[datetime] = None
    is_active: bool = True
    
    def to_dict(self) -> Dict:
        return {
            'user_id': self.user_id,
            'client_id': self.client_id,
            'api_key': self.api_key,
            'jwt_token': self.jwt_token,
            'refresh_token': self.refresh_token,
            'feed_token': self.feed_token,
            'mac_address': self.mac_address,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'last_refresh': self.last_refresh.isoformat() if self.last_refresh else None,
            'is_active': self.is_active
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'AngelOneSessionData':
        created_at = data.get('created_at')
        expires_at = data.get('expires_at')
        last_refresh = data.get('last_refresh')
        
        return cls(
            user_id=data.get('user_id', ''),
            client_id=data.get('client_id', ''),
            api_key=data.get('api_key', ''),
            jwt_token=data.get('jwt_token', ''),
            refresh_token=data.get('refresh_token', ''),
            feed_token=data.get('feed_token', ''),
            mac_address=data.get('mac_address'),
            created_at=datetime.fromisoformat(created_at) if created_at else datetime.utcnow(),
            expires_at=datetime.fromisoformat(expires_at) if expires_at else None,
            last_refresh=datetime.fromisoformat(last_refresh) if last_refresh else None,
            is_active=data.get('is_active', True)
        )


class PersistentSessionManager:
    """
    Persistent session manager for Angel One broker.
    
    Features:
    - Redis cache for fast access
    - MongoDB backup for persistence
    - Automatic token refresh before expiry
    - WebSocket recovery hooks
    - Thread-safe operations
    """
    
    # Configuration
    REDIS_KEY_PREFIX = 'angelone:session:'
    MONGO_COLLECTION = 'broker_sessions'
    TOKEN_EXPIRY_SECONDS = 86400  # 24 hours
    REFRESH_BEFORE_SECONDS = 3600  # Refresh 1 hour before expiry
    REFRESH_RETRY_ATTEMPTS = 3
    REFRESH_RETRY_DELAY = 5  # seconds
    
    _instance = None
    _lock = Lock()
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        self._initialized = True
        self._redis_client = None
        self._mongo_db = None
        self._current_session: Optional[AngelOneSessionData] = None
        self._refresh_timer: Optional[Timer] = None
        self._on_reconnect_callbacks: list = []
        
        self._init_connections()
        self._schedule_token_refresh()
    
    def _init_connections(self):
        """Initialize Redis and MongoDB connections."""
        try:
            from app.database.connection import get_redis, get_db
            self._redis_client = get_redis()
            self._mongo_db = get_db()
            logger.info("[OK] Session manager: Redis and MongoDB connections initialized")
        except Exception as e:
            logger.warning(f"Session manager: Database connections unavailable: {e}")
            self._redis_client = None
            self._mongo_db = None
    
    def _get_redis_key(self, user_id: str) -> str:
        """Get Redis key for user session."""
        return f"{self.REDIS_KEY_PREFIX}{user_id}"
    
    def _get_mongo_filter(self, user_id: str) -> Dict:
        """Get MongoDB filter for user session."""
        return {'user_id': user_id, 'broker': 'angelone', 'is_active': True}
    
    # ─── SESSION CREATION ─────────────────────────────────────────────────────
    
    def create_session(
        self,
        user_id: str,
        client_id: str,
        api_key: str,
        jwt_token: str,
        refresh_token: str,
        feed_token: str,
        mac_address: str = None
    ) -> AngelOneSessionData:
        """
        Create a new session with token storage in Redis and MongoDB.
        
        Args:
            user_id: User identifier
            client_id: Angel One client ID
            api_key: Angel One API key
            jwt_token: JWT access token
            refresh_token: Refresh token
            feed_token: Feed token for websocket
            mac_address: MAC address for feed token
        
        Returns:
            AngelOneSessionData: Created session data
        """
        session_data = AngelOneSessionData(
            user_id=user_id,
            client_id=client_id,
            api_key=api_key,
            jwt_token=jwt_token,
            refresh_token=refresh_token,
            feed_token=feed_token,
            mac_address=mac_address,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(seconds=self.TOKEN_EXPIRY_SECONDS),
            last_refresh=datetime.utcnow(),
            is_active=True
        )
        
        self._store_session(session_data)
        self._current_session = session_data
        
        logger.info(f"[OK] Session created for user: {user_id}")
        self._schedule_token_refresh()
        
        return session_data
    
    def _store_session(self, session: AngelOneSessionData):
        """Store session in both Redis and MongoDB."""
        session_dict = session.to_dict()
        
        # Store in Redis (fast cache)
        if self._redis_client:
            try:
                redis_key = self._get_redis_key(session.user_id)
                self._redis_client.set(
                    redis_key,
                    json.dumps(session_dict),
                    ex=self.TOKEN_EXPIRY_SECONDS
                )
                
                self._redis_client.set(
                    f"{redis_key}:refresh",
                    session.refresh_token,
                    ex=self.TOKEN_EXPIRY_SECONDS * 30
                )
                
                self._redis_client.set(
                    f"{redis_key}:feed",
                    session.feed_token,
                    ex=self.TOKEN_EXPIRY_SECONDS
                )
                
                logger.info(f"[OK] Session stored in Redis: {redis_key}")
            except Exception as e:
                logger.error(f"Failed to store session in Redis: {e}")
        
        # Store in MongoDB (persistent backup)
        if self._mongo_db:
            try:
                collection = self._mongo_db[self.MONGO_COLLECTION]
                
                collection.update_one(
                    self._get_mongo_filter(session.user_id),
                    {'$set': session_dict},
                    upsert=True
                )
                
                logger.info(f"[OK] Session stored in MongoDB: {session.user_id}")
            except Exception as e:
                logger.error(f"Failed to store session in MongoDB: {e}")
    
    # ─── SESSION RESTORE ─────────────────────────────────────────────────────
    
    def restore_session(self, user_id: str) -> Optional[AngelOneSessionData]:
        """
        Restore session from Redis (preferred) or MongoDB (fallback).
        
        Args:
            user_id: User identifier
        
        Returns:
            AngelOneSessionData or None if session not found
        """
        session = self._restore_from_redis(user_id)
        
        if session is None:
            session = self._restore_from_mongo(user_id)
        
        if session:
            self._current_session = session
            logger.info(f"[OK] Session restored for user: {user_id}")
            self._schedule_token_refresh()
            return session
        
        logger.warning(f"[WARN] No session found for user: {user_id}")
        return None
    
    def _restore_from_redis(self, user_id: str) -> Optional[AngelOneSessionData]:
        """Restore session from Redis cache."""
        if not self._redis_client:
            return None
        
        try:
            redis_key = self._get_redis_key(user_id)
            session_json = self._redis_client.get(redis_key)
            
            if session_json:
                session_dict = json.loads(session_json)
                logger.info(f"[OK] Session restored from Redis: {user_id}")
                return AngelOneSessionData.from_dict(session_dict)
        except Exception as e:
            logger.error(f"Failed to restore from Redis: {e}")
        
        return None
    
    def _restore_from_mongo(self, user_id: str) -> Optional[AngelOneSessionData]:
        """Restore session from MongoDB persistent storage."""
        if not self._mongo_db:
            return None
        
        try:
            collection = self._mongo_db[self.MONGO_COLLECTION]
            doc = collection.find_one(self._get_mongo_filter(user_id))
            
            if doc:
                doc.pop('_id', None)
                logger.info(f"[OK] Session restored from MongoDB: {user_id}")
                
                # Restore to Redis for future fast access
                session = AngelOneSessionData.from_dict(doc)
                if self._redis_client:
                    self._store_session(session)
                
                return session
        except Exception as e:
            logger.error(f"Failed to restore from MongoDB: {e}")
        
        return None
    
    # ─── SESSION VALIDATION ──────────────────────────────────────────────────
    
    def is_session_valid(self, user_id: str = None) -> bool:
        """
        Check if session is valid and not expired.
        
        Args:
            user_id: Optional user ID (uses current session if not provided)
        
        Returns:
            bool: True if session is valid
        """
        session = self._current_session if user_id is None else self.restore_session(user_id)
        
        if session is None:
            return False
        
        if not session.is_active:
            return False
        
        # Check expiration
        if session.expires_at and datetime.utcnow() > session.expires_at:
            logger.warning(f"Session expired for user: {session.user_id}")
            return False
        
        return True
    
    def get_current_session(self) -> Optional[AngelOneSessionData]:
        """Get current active session."""
        return self._current_session
    
    def get_tokens(self) -> Optional[Dict[str, str]]:
        """Get current tokens (jwt, refresh, feed)."""
        session = self._current_session
        if session is None:
            return None
        
        return {
            'jwt_token': session.jwt_token,
            'refresh_token': session.refresh_token,
            'feed_token': session.feed_token
        }
    
    # ─── TOKEN REFRESH ───────────────────────────────────────────────────────
    
    def refresh_session(self, user_id: str = None) -> bool:
        """
        Refresh session tokens.
        
        Args:
            user_id: Optional user ID (uses current session if not provided)
        
        Returns:
            bool: True if refresh successful
        """
        session = self._current_session if user_id is None else self.restore_session(user_id)
        
        if session is None:
            logger.error("[ERROR] Cannot refresh: No session found")
            return False
        
        logger.info(f"[INFO] Refreshing session for user: {session.user_id}")
        
        for attempt in range(self.REFRESH_RETRY_ATTEMPTS):
            try:
                from .api.client import get_client
                client = get_client()
                smart_api = client.smart_api
                smart_api.setAccessToken(session.jwt_token)
                smart_api.setRefreshToken(session.refresh_token)
                
                refresh_response = smart_api.generateToken(session.refresh_token)
                
                if refresh_response and refresh_response.get('status') and refresh_response.get('data'):
                    tokens = refresh_response['data']
                    
                    session.jwt_token = tokens.get('jwtToken', session.jwt_token)
                    session.feed_token = tokens.get('feedToken', session.feed_token)
                    session.last_refresh = datetime.utcnow()
                    session.expires_at = datetime.utcnow() + timedelta(seconds=self.TOKEN_EXPIRY_SECONDS)
                    
                    # Update storage
                    self._store_session(session)
                    
                    logger.info(f"[OK] Token refresh successful for user: {session.user_id}")
                    
                    # Trigger reconnect callbacks
                    self._trigger_reconnect()
                    
                    return True
                else:
                    logger.warning(f"[WARN] Token refresh response invalid: {refresh_response}")
                    
            except Exception as e:
                logger.error(f"[ERROR] Token refresh failed (attempt {attempt + 1}): {e}")
            
            if attempt < self.REFRESH_RETRY_ATTEMPTS - 1:
                time.sleep(self.REFRESH_RETRY_DELAY)
        
        logger.error(f"[ERROR] Token refresh failed after {self.REFRESH_RETRY_ATTEMPTS} attempts")
        return False
    
    def _schedule_token_refresh(self):
        """Schedule automatic token refresh before expiry."""
        if self._refresh_timer:
            self._refresh_timer.cancel()
        
        if self._current_session and self._current_session.expires_at:
            expires_in = (self._current_session.expires_at - datetime.utcnow()).total_seconds()
            refresh_in = max(expires_in - self.REFRESH_BEFORE_SECONDS, 60)
            
            self._refresh_timer = Timer(refresh_in, self._do_scheduled_refresh)
            self._refresh_timer.daemon = True
            self._refresh_timer.start()
            
            logger.info(f"[INFO] Token refresh scheduled in {refresh_in:.0f} seconds")
    
    def _do_scheduled_refresh(self):
        """Execute scheduled token refresh."""
        logger.info("[INFO] Executing scheduled token refresh")
        if self._current_session:
            self.refresh_session(self._current_session.user_id)
    
    # ─── SESSION INVALIDATION ─────────────────────────────────────────────────
    
    def invalidate_session(self, user_id: str = None) -> bool:
        """
        Invalidate session and cleanup storage.
        
        Args:
            user_id: Optional user ID (uses current session if not provided)
        
        Returns:
            bool: True if invalidation successful
        """
        session = self._current_session if user_id is None else self.restore_session(user_id)
        
        if session is None:
            return False
        
        logger.info(f"[INFO] Invalidating session for user: {session.user_id}")
        
        session.is_active = False
        
        # Cleanup Redis
        if self._redis_client:
            try:
                redis_key = self._get_redis_key(session.user_id)
                self._redis_client.delete(redis_key)
                self._redis_client.delete(f"{redis_key}:refresh")
                self._redis_client.delete(f"{redis_key}:feed")
                logger.info(f"[OK] Session removed from Redis: {session.user_id}")
            except Exception as e:
                logger.error(f"Failed to remove session from Redis: {e}")
        
        # Update MongoDB
        if self._mongo_db:
            try:
                collection = self._mongo_db[self.MONGO_COLLECTION]
                collection.update_one(
                    self._get_mongo_filter(session.user_id),
                    {'$set': {'is_active': False, 'invalidated_at': datetime.utcnow().isoformat()}}
                )
                logger.info(f"[OK] Session marked inactive in MongoDB: {session.user_id}")
            except Exception as e:
                logger.error(f"Failed to update session in MongoDB: {e}")
        
        if self._current_session and self._current_session.user_id == session.user_id:
            self._current_session = None
        
        if self._refresh_timer:
            self._refresh_timer.cancel()
        
        return True
    
    # ─── WEBSOCKET RECOVERY ───────────────────────────────────────────────────
    
    def register_reconnect_callback(self, callback: Callable):
        """Register callback to be called after session refresh/reconnect."""
        self._on_reconnect_callbacks.append(callback)
    
    def _trigger_reconnect(self):
        """Trigger all registered reconnect callbacks."""
        logger.info(f"[INFO] Triggering {len(self._on_reconnect_callbacks)} reconnect callbacks")
        
        for callback in self._on_reconnect_callbacks:
            try:
                callback(self._current_session)
            except Exception as e:
                logger.error(f"Error in reconnect callback: {e}")
    
    def reconnect_websocket(self):
        """Trigger websocket reconnection with new tokens."""
        logger.info("[INFO] Triggering websocket reconnection")
        self._trigger_reconnect()
    
    # ─── STATUS & UTILITIES ──────────────────────────────────────────────────
    
    def get_status(self) -> Dict[str, Any]:
        """Get current session status."""
        if self._current_session is None:
            return {'status': 'no_session', 'is_valid': False}
        
        session = self._current_session
        expires_in = None
        if session.expires_at:
            expires_in = (session.expires_at - datetime.utcnow()).total_seconds()
        
        return {
            'status': 'active' if session.is_active else 'inactive',
            'user_id': session.user_id,
            'client_id': session.client_id,
            'is_valid': self.is_session_valid(),
            'expires_in_seconds': expires_in,
            'last_refresh': session.last_refresh.isoformat() if session.last_refresh else None
        }
    
    def clear_all_sessions(self) -> int:
        """Clear all Angel One sessions (for testing/maintenance)."""
        count = 0
        
        if self._redis_client:
            try:
                pattern = f"{self.REDIS_KEY_PREFIX}*"
                keys = self._redis_client.keys(pattern)
                if keys:
                    count = len(keys)
                    self._redis_client.delete(*keys)
                logger.info(f"[OK] Cleared {count} sessions from Redis")
            except Exception as e:
                logger.error(f"Failed to clear Redis sessions: {e}")
        
        if self._mongo_db:
            try:
                result = self._mongo_db[self.MONGO_COLLECTION].update_many(
                    {'broker': 'angelone'},
                    {'$set': {'is_active': False}}
                )
                logger.info(f"[OK] Marked {result.modified_count} sessions inactive in MongoDB")
            except Exception as e:
                logger.error(f"Failed to clear MongoDB sessions: {e}")
        
        return count


# Global singleton instance
persistent_session_manager = PersistentSessionManager()