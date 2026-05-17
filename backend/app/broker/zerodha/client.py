"""
Zerodha Kite Connect Client
============================
Production-grade HTTP client with retry logic and error handling.
"""

import logging
import asyncio
import time
import uuid
import json
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass
from enum import Enum

import requests

from .auth import TokenManager, get_token_manager
from .circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerOpenError
from .rate_limiter import RateLimiter, RateLimitConfig, RateLimitExceededError
from .models import (
    ZerodhaOrder,
    ZerodhaPosition,
    ZerodhaPortfolio,
    ZerodhaMargin,
    ZerodhaInstrument,
    ZerodhaTick,
    MarketSession,
)

logger = logging.getLogger('zerodha.client')


class BrokerError(Exception):
    def __init__(self, message: str, code: Optional[str] = None, retryable: bool = False):
        super().__init__(message)
        self.message = message
        self.code = code
        self.retryable = retryable


class AuthenticationError(BrokerError):
    pass


class RateLimitError(BrokerError):
    pass


class OrderRejectedError(BrokerError):
    def __init__(self, message: str, exchange_code: Optional[str] = None, **kwargs):
        super().__init__(message, retryable=False, **kwargs)
        self.exchange_code = exchange_code


class NetworkError(BrokerError):
    def __init__(self, message: str, retryable: bool = True, **kwargs):
        super().__init__(message, retryable=retryable, **kwargs)


class RetryConfig:
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter

    def get_delay(self, attempt: int) -> float:
        delay = min(self.base_delay * (self.exponential_base ** attempt), self.max_delay)

        if self.jitter:
            import random
            delay *= (0.5 + random.random())

        return delay


@dataclass
class APIResponse:
    success: bool
    data: Any = None
    error: Optional[str] = None
    status_code: int = 0
    retryable: bool = False


class ZerodhaClient:
    """
    Production-grade Kite Connect client with circuit breaker, rate limiting, and retry logic.
    """

    BASE_URL = "https://api.kite.trade"
    MARGIN_URL = "https://api.kite.trade/margins"
    ORDERS_URL = "https://api.kite.trade/orders"
    POSITIONS_URL = "https://api.kite.trade/positions"
    PORTFOLIO_URL = "https://api.kite.trade/portfolio"
    INSTRUMENTS_URL = "https://api.kite.trade/instruments"
    HOLDINGS_URL = "https://api.kite.trade/holdings"

    def __init__(
        self,
        token_manager: Optional[TokenManager] = None,
        retry_config: Optional[RetryConfig] = None,
        circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
        rate_limit_config: Optional[RateLimitConfig] = None,
    ):
        self.token_manager = token_manager or get_token_manager()
        self.retry_config = retry_config or RetryConfig()
        self.circuit_breaker = CircuitBreaker("zerodha_api", circuit_breaker_config or CircuitBreakerConfig())
        self.rate_limiter = RateLimiter(rate_limit_config or RateLimitConfig())

        self._session = requests.Session()
        self._session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "TradingPlatform/1.0",
        })

        self._request_callbacks: List[Callable] = []
        self._response_callbacks: List[Callable] = []

        self._idempotency_keys: Dict[str, str] = {}

    def register_request_callback(self, callback: Callable) -> None:
        self._request_callbacks.append(callback)

    def register_response_callback(self, callback: Callable) -> None:
        self._response_callbacks.append(callback)

    def _get_headers(self) -> Dict[str, str]:
        access_token = self.token_manager.access_token
        if not access_token:
            raise AuthenticationError("No access token available")

        return {
            "Authorization": f"token {self.token_manager.config.api_key}:{access_token}",
            "X-Kite-Version": "3",
        }

    def _make_request(
        self,
        method: str,
        url: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        retry_count: int = 0,
    ) -> APIResponse:
        for callback in self._request_callbacks:
            try:
                callback(method, url, params, data)
            except Exception as e:
                logger.warning(f"Request callback error: {e}")

        try:
            response = self._session.request(
                method=method,
                url=url,
                params=params,
                json=data,
                headers=self._get_headers(),
                timeout=30,
            )

            if response.status_code == 401:
                return APIResponse(
                    success=False,
                    error="Authentication failed - token may be expired",
                    status_code=401,
                    retryable=False,
                )

            if response.status_code == 429:
                return APIResponse(
                    success=False,
                    error="Rate limit exceeded",
                    status_code=429,
                    retryable=True,
                )

            if response.status_code >= 500:
                return APIResponse(
                    success=False,
                    error=f"Server error: {response.status_code}",
                    status_code=response.status_code,
                    retryable=True,
                )

            if response.status_code >= 400:
                error_data = response.json() if response.content else {}
                error_message = error_data.get("message", f"Request failed: {response.status_code}")

                exchange_error = error_data.get("error_type") == "NetworkError"

                return APIResponse(
                    success=False,
                    error=error_message,
                    status_code=response.status_code,
                    retryable=exchange_error,
                )

            result = response.json()

            if "error" in result:
                return APIResponse(
                    success=False,
                    error=result["error"],
                    status_code=response.status_code,
                    retryable=False,
                )

            for callback in self._response_callbacks:
                try:
                    callback(result)
                except Exception as e:
                    logger.warning(f"Response callback error: {e}")

            return APIResponse(
                success=True,
                data=result.get("data"),
                status_code=response.status_code,
            )

        except requests.exceptions.Timeout:
            return APIResponse(
                success=False,
                error="Request timeout",
                status_code=408,
                retryable=True,
            )

        except requests.exceptions.ConnectionError as e:
            return APIResponse(
                success=False,
                error=f"Connection error: {str(e)}",
                status_code=0,
                retryable=True,
            )

        except requests.exceptions.RequestException as e:
            return APIResponse(
                success=False,
                error=f"Request failed: {str(e)}",
                status_code=0,
                retryable=True,
            )

    async def _make_request_async(
        self,
        method: str,
        url: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
    ) -> APIResponse:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self._make_request(method, url, params, data)
        )

    async def _execute_with_retry(
        self,
        method: str,
        url: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        skip_rate_limit: bool = False,
    ) -> APIResponse:
        if not skip_rate_limit:
            if not await self.rate_limiter.acquire_api_call():
                raise RateLimitError("API rate limit exceeded")

        last_error: Optional[APIResponse] = None

        for attempt in range(self.retry_config.max_retries):
            try:
                result = await self._make_request_async(method, url, params, data)

                if result.success:
                    return result

                last_error = result

                if not result.retryable:
                    break

                if attempt < self.retry_config.max_retries - 1:
                    delay = self.retry_config.get_delay(attempt)
                    logger.warning(f"Retry {attempt + 1}/{self.retry_config.max_retries} after {delay:.2f}s: {result.error}")
                    await asyncio.sleep(delay)

            except CircuitBreakerOpenError as e:
                logger.error(f"Circuit breaker open: {e}")
                raise BrokerError(str(e), retryable=True)

            except RateLimitError as e:
                logger.error(f"Rate limit error: {e}")
                raise

            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                last_error = APIResponse(success=False, error=str(e), retryable=True)

                if attempt < self.retry_config.max_retries - 1:
                    delay = self.retry_config.get_delay(attempt)
                    await asyncio.sleep(delay)

        raise BrokerError(
            last_error.error if last_error else "Unknown error",
            retryable=last_error.retryable if last_error else False,
        )

    async def get_profile(self) -> Dict[str, Any]:
        result = await self._execute_with_retry("GET", f"{self.BASE_URL}/user/profile")
        return result.data if result.data else {}

    async def get_margins(self) -> ZerodhaMargin:
        result = await self._execute_with_retry("GET", self.MARGIN_URL)
        if result.data:
            return ZerodhaMargin.from_zerodha_response(result.data)
        return ZerodhaMargin()

    async def get_orders(self) -> List[ZerodhaOrder]:
        result = await self._execute_with_retry("GET", self.ORDERS_URL)
        if result.data:
            return [ZerodhaOrder.from_zerodha_response(order) for order in result.data]
        return []

    async def get_order_history(self, order_id: str) -> List[Dict]:
        result = await self._execute_with_retry("GET", f"{self.ORDERS_URL}/{order_id}")
        return result.data if result.data else []

    async def get_positions(self) -> List[ZerodhaPosition]:
        result = await self._execute_with_retry("GET", self.POSITIONS_URL)
        if result.data:
            return [ZerodhaPosition.from_zerodha_response(pos) for pos in result.data]
        return []

    async def get_holdings(self) -> List[Dict]:
        result = await self._execute_with_retry("GET", self.HOLDINGS_URL)
        return result.data if result.data else []

    async def get_portfolio(self) -> List[ZerodhaPortfolio]:
        result = await self._execute_with_retry("GET", self.PORTFOLIO_URL)
        if result.data:
            return [ZerodhaPortfolio.from_zerodha_response(item) for item in result.data]
        return []

    async def get_instruments(self, exchange: Optional[str] = None) -> List[ZerodhaInstrument]:
        url = self.INSTRUMENTS_URL
        if exchange:
            url = f"{self.INSTRUMENTS_URL}/{exchange}"

        result = await self._execute_with_retry("GET", url, skip_rate_limit=True)

        if result.data and isinstance(result.data, list):
            return [ZerodhaInstrument.from_zerodha_response(item) for item in result.data]

        return []

    def get_instruments_sync(self, exchange: Optional[str] = None) -> List[ZerodhaInstrument]:
        url = self.INSTRUMENTS_URL
        if exchange:
            url = f"{self.INSTRUMENTS_URL}/{exchange}"

        result = self._make_request_sync("GET", url)

        if result.data and isinstance(result.data, list):
            return [ZerodhaInstrument.from_zerodha_response(item) for item in result.data]

        return []

    def _make_request_sync(self, method: str, url: str, params: Optional[Dict] = None, data: Optional[Dict] = None) -> APIResponse:
        for callback in self._request_callbacks:
            try:
                callback(method, url, params, data)
            except Exception as e:
                logger.warning(f"Request callback error: {e}")

        try:
            response = self._session.request(
                method=method,
                url=url,
                params=params,
                json=data,
                headers=self._get_headers(),
                timeout=30,
            )

            if response.status_code == 401:
                return APIResponse(
                    success=False,
                    error="Authentication failed",
                    status_code=401,
                    retryable=False,
                )

            if response.status_code >= 400:
                error_data = response.json() if response.content else {}
                error_message = error_data.get("message", f"Request failed: {response.status_code}")

                return APIResponse(
                    success=False,
                    error=error_message,
                    status_code=response.status_code,
                    retryable=False,
                )

            result = response.json()

            for callback in self._response_callbacks:
                try:
                    callback(result)
                except Exception as e:
                    logger.warning(f"Response callback error: {e}")

            return APIResponse(
                success=True,
                data=result.get("data"),
                status_code=response.status_code,
            )

        except Exception as e:
            return APIResponse(
                success=False,
                error=str(e),
                status_code=0,
                retryable=True,
            )

    def place_order_sync(self, params: Dict[str, Any]) -> ZerodhaOrder:
        result = self._make_request_sync("POST", self.ORDERS_URL, data=params)

        if not result.success:
            if "duplicate" in result.error.lower() or "already exists" in result.error.lower():
                raise OrderRejectedError(result.error, exchange_code="DUPLICATE_ORDER")
            raise BrokerError(result.error, retryable=result.retryable)

        return ZerodhaOrder.from_zerodha_response(result.data)

    def modify_order_sync(self, order_id: str, params: Dict[str, Any]) -> ZerodhaOrder:
        result = self._make_request_sync("PUT", f"{self.ORDERS_URL}/{order_id}", data=params)

        if not result.success:
            raise BrokerError(result.error, retryable=result.retryable)

        return ZerodhaOrder.from_zerodha_response(result.data)

    def cancel_order_sync(self, order_id: str, variety: str = "regular") -> ZerodhaOrder:
        result = self._make_request_sync("DELETE", f"{self.ORDERS_URL}/{order_id}", params={"variety": variety})

        if not result.success:
            raise BrokerError(result.error, retryable=result.retryable)

        return ZerodhaOrder.from_zerodha_response(result.data)

    def get_order_info_sync(self, order_id: str) -> ZerodhaOrder:
        result = self._make_request_sync("GET", f"{self.ORDERS_URL}/{order_id}")

        if not result.success:
            raise BrokerError(result.error, retryable=result.retryable)

        return ZerodhaOrder.from_zerodha_response(result.data)

    def get_quote_sync(self, instrument_token: int) -> Dict[str, Any]:
        result = self._make_request_sync("GET", f"{self.BASE_URL}/quote", params={"i": instrument_token})

        if not result.success:
            raise BrokerError(result.error, retryable=result.retryable)

        return result.data.get(str(instrument_token), {}) if result.data else {}

    def get_quotes_sync(self, instrument_tokens: List[int]) -> Dict[str, Any]:
        tokens = ",".join(str(t) for t in instrument_tokens)
        result = self._make_request_sync("GET", f"{self.BASE_URL}/quote", params={"i": tokens})

        if not result.success:
            raise BrokerError(result.error, retryable=result.retryable)

        return result.data if result.data else {}

    async def get_quote(self, instrument_token: int) -> Dict[str, Any]:
        result = await self._execute_with_retry("GET", f"{self.BASE_URL}/quote", params={"i": instrument_token})

        if not result.success:
            raise BrokerError(result.error, retryable=result.retryable)

        return result.data.get(str(instrument_token), {}) if result.data else {}

    def get_market_session(self) -> MarketSession:
        return MarketSession.from_exchange()

    def generate_idempotency_key(self, prefix: str = "ORD") -> str:
        return f"{prefix}{uuid.uuid4().hex[:12].upper()}"

    def get_circuit_breaker_stats(self) -> Dict[str, Any]:
        return self.circuit_breaker.get_stats()

    def get_rate_limit_stats(self) -> Dict[str, int]:
        return self.rate_limiter.get_remaining_quota()


_zerodha_client: Optional[ZerodhaClient] = None


def get_zerodha_client() -> ZerodhaClient:
    global _zerodha_client
    if _zerodha_client is None:
        _zerodha_client = ZerodhaClient()
    return _zerodha_client


def initialize_zerodha_client(
    token_manager: TokenManager,
    retry_config: Optional[RetryConfig] = None,
) -> ZerodhaClient:
    global _zerodha_client
    _zerodha_client = ZerodhaClient(
        token_manager=token_manager,
        retry_config=retry_config,
    )
    return _zerodha_client