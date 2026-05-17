"""
Locust Load Testing Framework for Trading Platform
Supports: API Load Testing, WebSocket Load Testing, Order Execution Benchmarking
"""

import random
import time
import json
import logging
from typing import Dict, List, Any, Optional
from locust import HttpUser, task, between, events, constant, events
from locust.runners import MasterRunner, WorkerRunner
import gevent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TradingAPIClient:
    """Base client for trading API interactions"""

    def __init__(self, base_url: str, auth_token: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.auth_token = auth_token
        self.session_id = None
        self.positions = []
        self.orders = []

    def get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        if self.session_id:
            headers["X-Session-ID"] = self.session_id
        return headers

    def authenticate(self, username: str, password: str) -> bool:
        """Authenticate user and get session token"""
        try:
            with self.client.post(
                f"{self.base_url}/api/auth/login",
                json={"username": username, "password": password},
                catch_response=True
            ) as response:
                if response.status_code == 200:
                    data = response.json()
                    self.auth_token = data.get("token")
                    self.session_id = data.get("session_id")
                    response.success()
                    return True
                else:
                    response.failure(f"Auth failed: {response.status_code}")
                    return False
        except Exception as e:
            logger.error(f"Auth error: {e}")
            return False

    def get_market_data(self, symbol: str) -> Optional[Dict]:
        """Fetch real-time market data for a symbol"""
        try:
            with self.client.get(
                f"{self.base_url}/api/market/{symbol}",
                headers=self.get_headers(),
                catch_response=True
            ) as response:
                if response.status_code == 200:
                    response.success()
                    return response.json()
                response.failure(f"Market data failed: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Market data error: {e}")
            return None

    def place_order(
        self,
        symbol: str,
        quantity: int,
        order_type: str,
        side: str,
        price: Optional[float] = None
    ) -> Optional[Dict]:
        """Place a trading order"""
        order_payload = {
            "symbol": symbol,
            "quantity": quantity,
            "order_type": order_type,
            "side": side,
            "timestamp": time.time()
        }
        if price:
            order_payload["price"] = price

        try:
            with self.client.post(
                f"{self.base_url}/api/orders",
                json=order_payload,
                headers=self.get_headers(),
                catch_response=True
            ) as response:
                if response.status_code in [200, 201]:
                    order_data = response.json()
                    self.orders.append(order_data)
                    response.success()
                    return order_data
                response.failure(f"Order placement failed: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Order placement error: {e}")
            return None

    def get_order_book(self, symbol: str) -> Optional[Dict]:
        """Get order book for a symbol"""
        try:
            with self.client.get(
                f"{self.base_url}/api/market/{symbol}/orderbook",
                headers=self.get_headers(),
                catch_response=True
            ) as response:
                if response.status_code == 200:
                    response.success()
                    return response.json()
                response.failure(f"Order book failed: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Order book error: {e}")
            return None

    def get_positions(self) -> List[Dict]:
        """Get current positions"""
        try:
            with self.client.get(
                f"{self.base_url}/api/positions",
                headers=self.get_headers(),
                catch_response=True
            ) as response:
                if response.status_code == 200:
                    response.success()
                    self.positions = response.json()
                    return self.positions
                response.failure(f"Positions failed: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Positions error: {e}")
            return []

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an existing order"""
        try:
            with self.client.delete(
                f"{self.base_url}/api/orders/{order_id}",
                headers=self.get_headers(),
                catch_response=True
            ) as response:
                if response.status_code in [200, 204]:
                    response.success()
                    return True
                response.failure(f"Cancel failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Cancel order error: {e}")
            return False

    def get_portfolio(self) -> Optional[Dict]:
        """Get portfolio summary"""
        try:
            with self.client.get(
                f"{self.base_url}/api/portfolio",
                headers=self.get_headers(),
                catch_response=True
            ) as response:
                if response.status_code == 200:
                    response.success()
                    return response.json()
                response.failure(f"Portfolio failed: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Portfolio error: {e}")
            return None

    def get_historical_data(
        self,
        symbol: str,
        interval: str = "1m",
        limit: int = 100
    ) -> Optional[List[Dict]]:
        """Get historical OHLCV data"""
        try:
            with self.client.get(
                f"{self.base_url}/api/market/{symbol}/history",
                params={"interval": interval, "limit": limit},
                headers=self.get_headers(),
                catch_response=True
            ) as response:
                if response.status_code == 200:
                    response.success()
                    return response.json()
                response.failure(f"History failed: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Historical data error: {e}")
            return None


class HighFrequencyTrader(HttpUser):
    """High-frequency trading user simulation"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = TradingAPIClient(self.host)
        self.symbols = self._generate_symbols(50)
        self.strategy_id = None

    def _generate_symbols(self, count: int) -> List[str]:
        """Generate mock trading symbols"""
        prefixes = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "KOTAKBANK",
                    "SBIN", "BHARTIARTL", "ITC", "L&T"]
        return [f"{random.choice(prefixes)}{random.randint(1, 999)}" for _ in range(count)]

    def on_start(self):
        """Initialize user session"""
        self.client.authenticate(f"user_{self.environment.runner.user_count}",
                                  "test_password_123")

    @task(10)
    def place_market_order(self):
        """Place market order - high frequency"""
        symbol = random.choice(self.symbols)
        side = random.choice(["BUY", "SELL"])
        quantity = random.randint(1, 100) * random.choice([1, 5, 10, 25, 50])
        start_time = time.perf_counter()
        self.client.place_order(symbol, quantity, "MARKET", side)
        latency = (time.perf_counter() - start_time) * 1000
        events.request.fire(
            request_type="POST",
            name="place_market_order",
            response_time=latency,
            response_length=0,
            context={},
            exception=None
        )

    @task(5)
    def place_limit_order(self):
        """Place limit order with price"""
        symbol = random.choice(self.symbols)
        side = random.choice(["BUY", "SELL"])
        quantity = random.randint(1, 50) * 10
        price = random.uniform(100, 5000)
        self.client.place_order(symbol, quantity, "LIMIT", side, price)

    @task(20)
    def get_market_quote(self):
        """Fetch market data - very high frequency"""
        symbol = random.choice(self.symbols)
        start_time = time.perf_counter()
        self.client.get_market_data(symbol)
        latency = (time.perf_counter() - start_time) * 1000

    @task(15)
    def get_order_book(self):
        """Get order book depth"""
        symbol = random.choice(self.symbols)
        start_time = time.perf_counter()
        self.client.get_order_book(symbol)
        latency = (time.perf_counter() - start_time) * 1000

    @task(3)
    def get_positions(self):
        """Check positions"""
        self.client.get_positions()

    @task(2)
    def get_portfolio(self):
        """Check portfolio"""
        self.client.get_portfolio()

    @task(1)
    def cancel_order(self):
        """Cancel random order"""
        if self.client.orders:
            order_id = random.choice(self.client.orders).get("order_id")
            if order_id:
                self.client.cancel_order(order_id)

    wait_time = constant(0.01)


class OrderExecutionBenchmark(HttpUser):
    """Specialized user for order execution benchmarking"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = TradingAPIClient(self.host)
        self.order_latencies = []
        self.symbols = ["RELIANCE", "TCS", "INFY", "HDFCBANK"]

    def on_start(self):
        self.client.authenticate("benchmark_user", "bench_pass")

    @task
    def benchmark_order_placement(self):
        """Benchmark order placement latency"""
        symbol = random.choice(self.symbols)
        start_time = time.perf_counter()
        result = self.client.place_order(symbol, 10, "MARKET", "BUY")
        latency = (time.perf_counter() - start_time) * 1000

        self.order_latencies.append(latency)

        if len(self.order_latencies) >= 100:
            avg_latency = sum(self.order_latencies) / len(self.order_latencies)
            p50 = sorted(self.order_latencies)[len(self.order_latencies) // 2]
            p95 = sorted(self.order_latencies)[int(len(self.order_latencies) * 0.95)]
            p99 = sorted(self.order_latencies)[int(len(self.order_latencies) * 0.99)]

            logger.info(f"Order Latency - Avg: {avg_latency:.2f}ms, P50: {p50:.2f}ms, "
                       f"P95: {p95:.2f}ms, P99: {p99:.2f}ms")

            self.order_latencies.clear()

    wait_time = constant(0.1)


class LatencyBenchmark(HttpUser):
    """Latency benchmarking user"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = TradingAPIClient(self.host)
        self.latencies = {
            "market_data": [],
            "order_placement": [],
            "order_book": [],
            "portfolio": []
        }

    def on_start(self):
        self.client.authenticate("latency_user", "latency_pass")

    @task(10)
    def benchmark_market_data_latency(self):
        """Benchmark market data fetching latency"""
        symbol = random.choice(["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"])
        start = time.perf_counter()
        self.client.get_market_data(symbol)
        self.latencies["market_data"].append((time.perf_counter() - start) * 1000)

    @task(5)
    def benchmark_order_placement_latency(self):
        """Benchmark order placement latency"""
        symbol = random.choice(["RELIANCE", "TCS", "INFY"])
        start = time.perf_counter()
        self.client.place_order(symbol, 10, "MARKET", "BUY")
        self.latencies["order_placement"].append((time.perf_counter() - start) * 1000)

    @task(8)
    def benchmark_order_book_latency(self):
        """Benchmark order book latency"""
        symbol = random.choice(["RELIANCE", "TCS", "INFY", "HDFCBANK"])
        start = time.perf_counter()
        self.client.get_order_book(symbol)
        self.latencies["order_book"].append((time.perf_counter() - start) * 1000)

    @task(2)
    def benchmark_portfolio_latency(self):
        """Benchmark portfolio fetch latency"""
        start = time.perf_counter()
        self.client.get_portfolio()
        self.latencies["portfolio"].append((time.perf_counter() - start) * 1000)

    def on_stop(self):
        """Report latency statistics"""
        for endpoint, lats in self.latencies.items():
            if lats:
                lats.sort()
                count = len(lats)
                avg = sum(lats) / count
                p50 = lats[count // 2]
                p95 = lats[int(count * 0.95)]
                p99 = lats[int(count * 0.99)]
                logger.info(f"{endpoint} - Avg: {avg:.2f}ms, P50: {p50:.2f}ms, "
                           f"P95: {p95:.2f}ms, P99: {p99:.2f}ms, Max: {max(lats):.2f}ms")

    wait_time = between(0.1, 0.5)


class MixedWorkloadUser(HttpUser):
    """Mixed workload simulating realistic trading patterns"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = TradingAPIClient(self.host)
        self.watchlist = random.sample(
            ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN",
             "BHARTIARTL", "ITC", "L&T", "MARUTI", "SUNPHARMA", "ADANIPORTS"],
            k=6
        )
        self.state = "watching"

    def on_start(self):
        self.client.authenticate(f"trader_{random.randint(1000, 9999)}", "password")

    @task(30)
    def monitor_watchlist(self):
        """Monitor watchlist prices"""
        for symbol in self.watchlist:
            self.client.get_market_data(symbol)
        self.state = "watching"

    @task(5)
    def analyze_order_book(self):
        """Deep dive into order book"""
        symbol = random.choice(self.watchlist)
        self.client.get_order_book(symbol)
        self.state = "analyzing"

    @task(3)
    def place_order_sequence(self):
        """Execute a sequence of orders"""
        symbol = random.choice(self.watchlist)
        self.client.place_order(symbol, 50, "LIMIT", "BUY", random.uniform(100, 5000))
        gevent.sleep(random.uniform(0.1, 0.5))
        self.client.get_order_book(symbol)
        self.state = "trading"

    @task(2)
    def check_positions(self):
        """Review positions"""
        self.client.get_positions()
        self.client.get_portfolio()
        self.state = "reviewing"

    @task(1)
    def historical_analysis(self):
        """Analyze historical data"""
        symbol = random.choice(self.watchlist)
        self.client.get_historical_data(symbol, "5m", 100)

    wait_time = between(1, 5)


class StressTestUser(HttpUser):
    """Aggressive stress testing user"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = TradingAPIClient(self.host)

    def on_start(self):
        self.client.authenticate("stress_user", "stress_pass")

    @task
    def continuous_orders(self):
        """Fire orders continuously"""
        symbols = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"]
        for _ in range(10):
            symbol = random.choice(symbols)
            self.client.place_order(
                symbol,
                random.randint(1, 100),
                random.choice(["MARKET", "LIMIT"]),
                random.choice(["BUY", "SELL"])
            )
            gevent.sleep(0.01)

    @task
    def rapid_market_data(self):
        """Rapid market data requests"""
        symbols = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK",
                   "SBIN", "BHARTIARTL", "ITC", "L&T", "MARUTI"]
        for symbol in symbols:
            self.client.get_market_data(symbol)
            gevent.sleep(0.005)

    wait_time = constant(0)


class ScalabilityTestUser(HttpUser):
    """User for scalability testing - long running with varying patterns"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = TradingAPIClient(self.host)
        self.symbols = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK",
                        "SBIN", "BHARTIARTL", "ITC", "L&T", "MARUTI"]

    def on_start(self):
        self.client.authenticate(f"scalability_user_{id(self)}", "scale_pass")

    @task
    def sustained_market_data_load(self):
        """Sustained market data load"""
        for _ in range(100):
            symbol = random.choice(self.symbols)
            self.client.get_market_data(symbol)
            gevent.sleep(0.05)

    @task
    def sustained_order_flow(self):
        """Sustained order flow"""
        for _ in range(20):
            symbol = random.choice(self.symbols)
            self.client.place_order(symbol, 10, "MARKET", random.choice(["BUY", "SELL"]))
            gevent.sleep(0.1)

    @task
    def sustained_mixed_operations(self):
        """Sustained mixed operations"""
        for _ in range(50):
            operation = random.choice([
                lambda: self.client.get_market_data(random.choice(self.symbols)),
                lambda: self.client.get_order_book(random.choice(self.symbols)),
                lambda: self.client.get_positions(),
                lambda: self.client.get_portfolio()
            ])
            operation()
            gevent.sleep(0.05)

    wait_time = between(1, 3)