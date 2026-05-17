"""
OAuth and Token Management for Zerodha Kite Connect
====================================================
Secure credential handling and automatic token refresh.
"""

import logging
import asyncio
import time
import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
import json

import requests
from pymongo import MongoClient

from ...config import Config


logger = logging.getLogger('zerodha.auth')


class TokenStatus(str, Enum):
    VALID = "VALID"
    EXPIRED = "EXPIRED"
    REFRESHING = "REFRESHING"
    INVALID = "INVALID"


@dataclass
class TokenSet:
    access_token: str
    refresh_token: str
    api_key: str
    expires_at: datetime
    user_id: Optional[str] = None
    login_time: Optional[datetime] = None

    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) >= self.expires_at

    @property
    def needs_refresh(self) -> bool:
        return (self.expires_at - datetime.now(timezone.utc)).total_seconds() < 300

    def to_dict(self) -> Dict[str, Any]:
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "api_key": self.api_key,
            "expires_at": self.expires_at.isoformat(),
            "user_id": self.user_id,
        }


@dataclass
class OAuthConfig:
    api_key: str
    api_secret: str
    redirect_uri: str
    broker: str = "zerodha"

    def validate(self) -> bool:
        if not self.api_key or len(self.api_key) < 10:
            return False
        if not self.api_secret or len(self.api_secret) < 10:
            return False
        if not self.redirect_uri or not self.redirect_uri.startswith("http"):
            return False
        return True


class TokenManager:
    """
    Manages OAuth tokens with automatic refresh and secure storage.
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        redirect_uri: str,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        db_client: Optional[MongoClient] = None,
    ):
        self.config = OAuthConfig(
            api_key=api_key,
            api_secret=api_secret,
            redirect_uri=redirect_uri,
        )

        self._tokens: Optional[TokenSet] = None
        self._status = TokenStatus.INVALID
        self._refresh_lock = asyncio.Lock()
        self._db_client = db_client
        self._db_collection = None

        if access_token and refresh_token:
            self._tokens = TokenSet(
                access_token=access_token,
                refresh_token=refresh_token,
                api_key=api_key,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=23, minutes=50),
            )
            self._status = TokenStatus.VALID

        self._on_token_refreshed: Optional[Callable[[TokenSet], None]] = None

    def set_db_collection(self, collection) -> None:
        self._db_collection = collection

    def set_token_refreshed_callback(self, callback: Callable[[TokenSet], None]) -> None:
        self._on_token_refreshed = callback

    @property
    def access_token(self) -> Optional[str]:
        return self._tokens.access_token if self._tokens else None

    @property
    def is_valid(self) -> bool:
        return self._status == TokenStatus.VALID and self._tokens and not self._tokens.is_expired

    @property
    def status(self) -> TokenStatus:
        return self._status

    def get_login_url(self) -> str:
        return f"https://kite.zerodha.com/connect/login?api_key={self.config.api_key}&v=3"

    def get_request_token_url(self, request_token: str) -> str:
        checksum = hashlib.sha256(
            (self.config.api_key + request_token + self.config.api_secret).encode()
        ).hexdigest()
        return f"{self.config.redirect_uri}?request_token={request_token}&api_key={self.config.api_key}&checksum={checksum}"

    def generate_session(self, request_token: str) -> TokenSet:
        if not self.config.validate():
            raise ValueError("Invalid OAuth configuration")

        url = "https://api.kite.trade/session/token"
        data = {
            "api_key": self.config.api_key,
            "request_token": request_token,
            "checksum": hashlib.sha256(
                (self.config.api_key + request_token + self.config.api_secret).encode()
            ).hexdigest(),
        }

        response = requests.post(url, data=data, timeout=30)
        response.raise_for_status()

        session_data = response.json()

        access_token = session_data.get("data", {}).get("access_token")
        refresh_token = session_data.get("data", {}).get("refresh_token")
        user_id = session_data.get("data", {}).get("user_id")

        if not access_token or not refresh_token:
            raise ValueError("Invalid session response from Kite")

        self._tokens = TokenSet(
            access_token=access_token,
            refresh_token=refresh_token,
            api_key=self.config.api_key,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=23, minutes=50),
            user_id=user_id,
            login_time=datetime.now(timezone.utc),
        )
        self._status = TokenStatus.VALID

        self._persist_tokens()

        logger.info(f"Session generated for user {user_id}")
        return self._tokens

    async def refresh_token(self) -> TokenSet:
        async with self._refresh_lock:
            if self._status == TokenStatus.REFRESHING:
                await asyncio.sleep(1)
                if self._tokens:
                    return self._tokens
                raise ValueError("Token refresh failed")

            if not self._tokens or not self._tokens.refresh_token:
                raise ValueError("No refresh token available")

            self._status = TokenStatus.REFRESHING

            try:
                url = "https://api.kite.trade/session/refresh"
                data = {
                    "api_key": self.config.api_key,
                    "refresh_token": self._tokens.refresh_token,
                }

                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: requests.post(url, data=data, timeout=30)
                )
                response.raise_for_status()

                session_data = response.json()
                access_token = session_data.get("data", {}).get("access_token")
                refresh_token = session_data.get("data", {}).get("refresh_token")

                if not access_token:
                    raise ValueError("Failed to refresh access token")

                self._tokens = TokenSet(
                    access_token=access_token,
                    refresh_token=refresh_token or self._tokens.refresh_token,
                    api_key=self.config.api_key,
                    expires_at=datetime.now(timezone.utc) + timedelta(hours=23, minutes=50),
                    user_id=self._tokens.user_id,
                    login_time=self._tokens.login_time,
                )
                self._status = TokenStatus.VALID

                self._persist_tokens()

                if self._on_token_refreshed:
                    self._on_token_refreshed(self._tokens)

                logger.info("Access token refreshed successfully")
                return self._tokens

            except Exception as e:
                self._status = TokenStatus.EXPIRED
                logger.error(f"Token refresh failed: {e}")
                raise

    async def ensure_valid_token(self) -> str:
        if not self._tokens:
            raise ValueError("No token set")

        if self._tokens.needs_refresh:
            await self.refresh_token()

        if not self.is_valid:
            raise ValueError("Token is invalid or expired")

        return self._tokens.access_token

    def invalidate(self) -> None:
        self._tokens = None
        self._status = TokenStatus.INVALID
        self._clear_persisted_tokens()
        logger.warning("Tokens invalidated")

    def _persist_tokens(self) -> None:
        if not self._db_collection or not self._tokens:
            return

        try:
            self._db_collection.update_one(
                {"broker": "zerodha"},
                {
                    "$set": {
                        "access_token": self._tokens.access_token,
                        "refresh_token": self._tokens.refresh_token,
                        "updated_at": datetime.now(timezone.utc),
                    }
                },
                upsert=True,
            )
        except Exception as e:
            logger.error(f"Failed to persist tokens: {e}")

    def _clear_persisted_tokens(self) -> None:
        if not self._db_collection:
            return

        try:
            self._db_collection.update_one(
                {"broker": "zerodha"},
                {"$unset": {"access_token": "", "refresh_token": ""}},
            )
        except Exception as e:
            logger.error(f"Failed to clear persisted tokens: {e}")

    def get_user_profile(self) -> Dict[str, Any]:
        if not self._tokens:
            raise ValueError("No token set")

        url = "https://api.kite.trade/user/profile"
        headers = {"Authorization": f"token {self.config.api_key}:{self._tokens.access_token}"}

        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        return response.json()


def get_token_manager() -> TokenManager:
    api_key = Config.KITE_API_KEY or ""
    api_secret = Config.KITE_API_SECRET or ""
    redirect_uri = Config.KITE_REDIRECT_URI or "http://localhost:5000/callback"

    token_manager = TokenManager(
        api_key=api_key,
        api_secret=api_secret,
        redirect_uri=redirect_uri,
    )

    return token_manager