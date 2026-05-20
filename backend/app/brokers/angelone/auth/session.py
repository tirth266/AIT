"""
Angel One Authentication & Session Management
===========================================
Handles SmartAPI login, TOTP generation, JWT token management, and auto-relogin.
"""

import os
import pyotp
import logging
from typing import Dict, Optional, Tuple
from SmartApi import SmartConnect
from app.database.connection import get_redis

logger = logging.getLogger('angelone.auth')

class AngelOneSession:
    """Manages SmartAPI session lifecycle and tokens."""
    
    def __init__(self):
        self.client_id = os.environ.get('ANGELONE_CLIENT_ID')
        self.api_key = os.environ.get('ANGELONE_API_KEY')
        self.secret_key = os.environ.get('ANGELONE_SECRET_KEY')
        self.mpin = os.environ.get('ANGELONE_MPIN')
        self.totp_secret = os.environ.get('ANGELONE_TOTP_SECRET')
        
        self.smart_api = None
        self.feed_token = None
        self.jwt_token = None
        self.refresh_token = None
        self.is_connected = False
        
        self.redis = get_redis()
        self.session_key = f"angelone_session:{self.client_id}"
        
    def _generate_totp(self) -> str:
        """Generate time-based OTP."""
        if not self.totp_secret:
            raise ValueError("TOTP secret not configured")
        totp = pyotp.TOTP(self.totp_secret)
        return totp.now()

    def connect(self) -> bool:
        """Authenticate with Angel One SmartAPI."""
        from ..api.client import get_client
        client = get_client()
        
        if not all([client.client_id, client.api_key, client.password]):
            logger.error("Missing Angel One credentials")
            return False
            
        try:
            # Use the shared SmartConnect instance
            self.smart_api = client.smart_api
            
            # 2. Generate TOTP
            totp = pyotp.TOTP(client.totp_secret).now()
            
            # 3. Login
            data = self.smart_api.generateSession(
                client.client_id, 
                client.password, 
                totp
            )
            
            if data.get('status') and data.get('data'):
                session_data = data['data']
                self.jwt_token = session_data.get('jwtToken')
                self.refresh_token = session_data.get('refreshToken')
                self.feed_token = session_data.get('feedToken')
                self.is_connected = True
                
                # Cache session in Redis
                if self.redis:
                    self.redis.set(self.session_key, self.jwt_token, ex=86400) # 24h expiry
                    self.redis.set(f"{self.session_key}:refresh", self.refresh_token, ex=86400 * 30)
                    self.redis.set(f"{self.session_key}:feed", self.feed_token, ex=86400)
                    
                logger.info("Successfully connected to Angel One SmartAPI")
                return True
            else:
                logger.error(f"Angel One login failed: {data.get('message', 'Unknown error')}")
                return False
                
        except Exception as e:
            logger.error(f"Angel One connection error: {e}")
            return False

    def check_and_restore_session(self) -> bool:
        """Restore session from Redis if valid."""
        if self.is_connected:
            return True
            
        if not self.redis:
            return self.connect()
            
        jwt = self.redis.get(self.session_key)
        refresh = self.redis.get(f"{self.session_key}:refresh")
        feed = self.redis.get(f"{self.session_key}:feed")
        
        if jwt and refresh and feed:
            try:
                # Re-initialize without full login
                self.smart_api = SmartConnect(api_key=self.api_key)
                self.smart_api.setAccessToken(jwt)
                self.smart_api.setRefreshToken(refresh)
                
                self.jwt_token = jwt
                self.refresh_token = refresh
                self.feed_token = feed
                self.is_connected = True
                
                # Test connection via profile
                profile = self.smart_api.getProfile(refresh)
                if profile.get('status'):
                    logger.info("Angel One session restored from cache")
                    return True
                else:
                    logger.warning("Cached session invalid, generating new session")
                    return self.connect()
                    
            except Exception:
                logger.warning("Failed to restore session, re-authenticating")
                return self.connect()
                
        return self.connect()

    def renew_token(self) -> bool:
        """Renew expired JWT token."""
        if not self.smart_api or not self.jwt_token:
            return self.connect()
            
        try:
            refresh_response = self.smart_api.generateToken(self.refresh_token)
            if refresh_response.get('status') and refresh_response.get('data'):
                tokens = refresh_response['data']
                self.jwt_token = tokens.get('jwtToken')
                self.feed_token = tokens.get('feedToken')
                
                if self.redis:
                    self.redis.set(self.session_key, self.jwt_token, ex=86400)
                    self.redis.set(f"{self.session_key}:feed", self.feed_token, ex=86400)
                
                logger.info("Angel One token successfully renewed")
                return True
            else:
                logger.warning("Token renewal failed, re-authenticating")
                return self.connect()
        except Exception as e:
            logger.error(f"Error renewing token: {e}")
            return self.connect()

    def disconnect(self) -> bool:
        """Logout and terminate session."""
        try:
            if self.smart_api and self.client_id:
                self.smart_api.terminateSession(self.client_id)
            self.is_connected = False
            self.jwt_token = None
            self.refresh_token = None
            self.feed_token = None
            
            if self.redis:
                self.redis.delete(self.session_key)
                self.redis.delete(f"{self.session_key}:refresh")
                self.redis.delete(f"{self.session_key}:feed")
                
            logger.info("Disconnected from Angel One")
            return True
        except Exception as e:
            logger.error(f"Error disconnecting from Angel One: {e}")
            return False

    def set_tokens(self, jwt_token: str, refresh_token: str, feed_token: str):
        """Manually set tokens after successful login."""
        self.jwt_token = jwt_token
        self.refresh_token = refresh_token
        self.feed_token = feed_token
        self.is_connected = True
        
        if self.redis:
            self.redis.set(self.session_key, self.jwt_token, ex=86400)
            self.redis.set(f"{self.session_key}:refresh", self.refresh_token, ex=86400 * 30)
            self.redis.set(f"{self.session_key}:feed", self.feed_token, ex=86400)
        
        logger.info("Angel One session tokens updated manually")

session_manager = AngelOneSession()
