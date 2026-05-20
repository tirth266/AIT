import asyncio
import json
import os
from typing import Optional, Dict
from .logger import get_logger
from app.database.connection import get_redis, get_db

logger = get_logger(__name__)

REDIS_KEY = "angelone:tokens"
MONGO_COLLECTION = "broker_tokens"


class TokenManager:
    """
    Manages persistence and in-memory caching of Angel One tokens.
    Uses Redis for fast access, MongoDB for durable backup.
    """
    def __init__(self, token_file: str = "angel_tokens.json"):
        self.token_file = token_file
        self.jwt_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.feed_token: Optional[str] = None
        self.mac_address: Optional[str] = None
        self._redis = None
        self._mongo = None
        self._init_connections()
        self._load_tokens()

    def _init_connections(self):
        try:
            self._redis = get_redis()
            self._mongo = get_db()
        except Exception as e:
            logger.warning(f"Database connections unavailable: {e}")

    def _load_tokens(self):
        try:
            if self._redis:
                data = self._redis.get(REDIS_KEY)
                if data:
                    parsed = json.loads(data)
                    self.jwt_token = parsed.get("jwt_token")
                    self.refresh_token = parsed.get("refresh_token")
                    self.feed_token = parsed.get("feed_token")
                    self.mac_address = parsed.get("mac_address")
                    logger.info("Tokens loaded from Redis.")
                    return

            if self._mongo:
                doc = self._mongo[MONGO_COLLECTION].find_one({"broker": "angelone"})
                if doc:
                    self.jwt_token = doc.get("jwt_token")
                    self.refresh_token = doc.get("refresh_token")
                    self.feed_token = doc.get("feed_token")
                    self.mac_address = doc.get("mac_address")
                    logger.info("Tokens loaded from MongoDB.")
                    return

            if os.path.exists(self.token_file):
                with open(self.token_file, "r") as f:
                    data = json.load(f)
                    self.jwt_token = data.get("jwt_token")
                    self.refresh_token = data.get("refresh_token")
                    self.feed_token = data.get("feed_token")
                    self.mac_address = data.get("mac_address")
                logger.info("Tokens loaded from file.")
        except Exception as e:
            logger.error(f"Failed to load tokens: {e}")

    def save_tokens(self, jwt_token: str, refresh_token: str, feed_token: str, mac_address: Optional[str] = None):
        self.jwt_token = jwt_token
        self.refresh_token = refresh_token
        self.feed_token = feed_token
        if mac_address:
            self.mac_address = mac_address

        token_data = {
            "jwt_token": self.jwt_token,
            "refresh_token": self.refresh_token,
            "feed_token": self.feed_token,
            "mac_address": self.mac_address
        }

        if self._redis:
            try:
                self._redis.set(REDIS_KEY, json.dumps(token_data), ex=86400)
                logger.info("Tokens persisted to Redis.")
            except Exception as e:
                logger.error(f"Failed to persist tokens to Redis: {e}")

        if self._mongo:
            try:
                self._mongo[MONGO_COLLECTION].update_one(
                    {"broker": "angelone"},
                    {"$set": token_data},
                    upsert=True
                )
                logger.info("Tokens persisted to MongoDB.")
            except Exception as e:
                logger.error(f"Failed to persist tokens to MongoDB: {e}")

        try:
            with open(self.token_file, "w") as f:
                json.dump(token_data, f)
            logger.info("Tokens persisted to file.")
        except Exception as e:
            logger.error(f"Failed to persist tokens to file: {e}")

    def clear_tokens(self):
        self.jwt_token = None
        self.refresh_token = None
        self.feed_token = None
        if os.path.exists(self.token_file):
            os.remove(self.token_file)
        if self._redis:
            self._redis.delete(REDIS_KEY)
        if self._mongo:
            self._mongo[MONGO_COLLECTION].delete_many({"broker": "angelone"})
        logger.info("Tokens cleared.")

    def get_tokens(self) -> Optional[Dict[str, str]]:
        if not (self.jwt_token and self.refresh_token and self.feed_token):
            return None
        return {
            "jwt_token": self.jwt_token,
            "refresh_token": self.refresh_token,
            "feed_token": self.feed_token,
            "mac_address": self.mac_address
        }

    def refresh_tokens(self) -> bool:
        if not self.refresh_token:
            logger.error("No refresh token available")
            return False
        try:
            from ..api.client import get_client
            client = get_client()
            smart_api = client.smart_api
            smart_api.setAccessToken(self.jwt_token)
            smart_api.setRefreshToken(self.refresh_token)
            response = smart_api.generateToken(self.refresh_token)
            if response and response.get('status') and response.get('data'):
                tokens = response['data']
                self.save_tokens(
                    jwt_token=tokens.get('jwtToken', self.jwt_token),
                    refresh_token=self.refresh_token,
                    feed_token=tokens.get('feedToken', self.feed_token),
                    mac_address=self.mac_address
                )
                logger.info("Tokens refreshed successfully.")
                return True
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
        return False

    def has_valid_tokens(self) -> bool:
        return bool(self.jwt_token and self.feed_token)


token_manager = TokenManager()
