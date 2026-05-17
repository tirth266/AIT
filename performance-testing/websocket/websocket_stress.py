"""
WebSocket Load Testing Framework for Trading Platform
Supports: 1000+ concurrent connections, tick throughput testing, latency benchmarking
"""

import asyncio
import json
import time
import random
import logging
import threading
import statistics
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
import queue

try:
    import websocket
except ImportError:
    print("Installing websocket-client...")
    import subprocess
    subprocess.check_call(["pip", "install", "websocket-client"])
    import websocket

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MessageType(Enum):
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    MARKET_DATA = "market_data"
    ORDER_UPDATE = "order_update"
    TRADE = "trade"
    HEARTBEAT = "heartbeat"
    ERROR = "error"


@dataclass
class TickData:
    """Tick data structure"""
    symbol: str
    price: float
    volume: int
    timestamp: float
    bid: float
    ask: float
    bid_size: int
    ask_size: int


@dataclass
class LatencySample:
    """Latency measurement sample"""
    send_time: float
    receive_time: float
    latency_ms: float
    message_type: str


@dataclass
class WebSocketMetrics:
    """WebSocket connection metrics"""
    total_messages_sent: int = 0
    total_messages_received: int = 0
    total_bytes_sent: int = 0
    total_bytes_received: int = 0
    errors: int = 0
    reconnections: int = 0
    latencies: List[float] = field(default_factory=list)
    message_types: Dict[str, int] = field(default_factory=dict)

    def get_stats(self) -> Dict[str, Any]:
        if not self.latencies:
            return {"error": "No latency data"}
        sorted_lats = sorted(self.latencies)
        return {
            "messages_sent": self.total_messages_sent,
            "messages_received": self.total_messages_received,
            "bytes_sent": self.total_bytes_sent,
            "bytes_received": self.total_bytes_received,
            "errors": self.errors,
            "reconnections": self.reconnections,
            "latency_avg_ms": statistics.mean(self.latencies),
            "latency_p50_ms": sorted_lats[len(sorted_lats) // 2],
            "latency_p95_ms": sorted_lats[int(len(sorted_lats) * 0.95)],
            "latency_p99_ms": sorted_lats[int(len(sorted_lats) * 0.99)],
            "latency_max_ms": max(self.latencies),
            "latency_min_ms": min(self.latencies),
            "message_types": self.message_types
        }


class TradingWebSocketClient:
    """WebSocket client for trading platform"""

    def __init__(
        self,
        url: str,
        client_id: int,
        symbols: List[str],
        auth_token: Optional[str] = None,
        on_message: Optional[Callable] = None,
        on_connect: Optional[Callable] = None,
        on_disconnect: Optional[Callable] = None,
        on_error: Optional[Callable] = None
    ):
        self.url = url
        self.client_id = client_id
        self.symbols = symbols
        self.auth_token = auth_token
        self.on_message = on_message
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect
        self.on_error = on_error

        self.ws = None
        self.is_connected = False
        self.is_running = False
        self.metrics = WebSocketMetrics()
        self.latency_samples: List[LatencySample] = []
        self.subscribed_symbols = set()

        self._receive_queue = queue.Queue(maxsize=1000)
        self._send_queue = queue.Queue()
        self._latency_map: Dict[str, float] = {}

    def connect(self, timeout: float = 10.0) -> bool:
        """Establish WebSocket connection"""
        try:
            headers = {}
            if self.auth_token:
                headers["Authorization"] = f"Bearer {self.auth_token}"
            headers["X-Client-ID"] = str(self.client_id)

            self.ws = websocket.WebSocketApp(
                self.url,
                header=headers,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
                on_pong=self._on_pong
            )

            self._ws_thread = threading.Thread(target=self._run_ws, daemon=True)
            self._ws_thread.start()

            start_time = time.time()
            while not self.is_connected and time.time() - start_time < timeout:
                time.sleep(0.1)

            return self.is_connected
        except Exception as e:
            logger.error(f"Connection error for client {self.client_id}: {e}")
            return False

    def _run_ws(self):
        """Run WebSocket in thread"""
        self.ws.run_forever(ping_interval=30, ping_timeout=10)

    def _on_open(self, ws):
        """WebSocket opened"""
        self.is_connected = True
        logger.debug(f"Client {self.client_id} connected")
        if self.on_connect:
            self.on_connect(self.client_id)

        self._send_auth()

    def _on_message(self, ws, message):
        """Handle incoming message"""
        try:
            self.metrics.total_messages_received += 1
            self.metrics.total_bytes_received += len(message)

            data = json.loads(message)
            msg_type = data.get("type", "unknown")
            self.metrics.message_types[msg_type] = self.metrics.message_types.get(msg_type, 0) + 1

            if "request_id" in data and data["request_id"] in self._latency_map:
                send_time = self._latency_map.pop(data["request_id"])
                latency = (time.time() - send_time) * 1000
                self.latency_samples.append(LatencySample(
                    send_time=send_time,
                    receive_time=time.time(),
                    latency_ms=latency,
                    message_type=msg_type
                ))
                self.metrics.latencies.append(latency)

            if self.on_message:
                self.on_message(self.client_id, data)

            self._receive_queue.put(data)
        except Exception as e:
            logger.error(f"Message parse error: {e}")

    def _on_error(self, ws, error):
        """Handle WebSocket error"""
        self.metrics.errors += 1
        logger.error(f"Client {self.client_id} error: {error}")
        if self.on_error:
            self.on_error(self.client_id, error)

    def _on_close(self, ws, close_status_code, close_msg):
        """WebSocket closed"""
        self.is_connected = False
        logger.debug(f"Client {self.client_id} disconnected: {close_status_code}")
        if self.on_disconnect:
            self.on_disconnect(self.client_id)

    def _on_pong(self, ws, data):
        """Handle pong response"""
        pass

    def _send_auth(self):
        """Send authentication message"""
        auth_msg = {
            "type": "auth",
            "token": self.auth_token or f"guest_{self.client_id}",
            "client_id": self.client_id
        }
        self._send(json.dumps(auth_msg))

    def _send(self, message: str):
        """Send message through WebSocket"""
        if self.is_connected and self.ws:
            try:
                self.ws.send(message)
                self.metrics.total_messages_sent += 1
                self.metrics.total_bytes_sent += len(message)
            except Exception as e:
                logger.error(f"Send error: {e}")
                self.metrics.errors += 1

    def subscribe(self, symbols: List[str]):
        """Subscribe to symbols"""
        for symbol in symbols:
            if symbol not in self.subscribed_symbols:
                msg = {
                    "type": "subscribe",
                    "symbol": symbol,
                    "request_id": f"sub_{symbol}_{time.time()}"
                }
                self._latency_map[msg["request_id"]] = time.time()
                self._send(json.dumps(msg))
                self.subscribed_symbols.add(symbol)

    def unsubscribe(self, symbols: List[str]):
        """Unsubscribe from symbols"""
        for symbol in symbols:
            if symbol in self.subscribed_symbols:
                msg = {
                    "type": "unsubscribe",
                    "symbol": symbol
                }
                self._send(json.dumps(msg))
                self.subscribed_symbols.discard(symbol)

    def place_order(self, symbol: str, quantity: int, side: str, order_type: str = "MARKET"):
        """Place order via WebSocket"""
        msg = {
            "type": "order",
            "order_id": f"ord_{self.client_id}_{time.time()}",
            "symbol": symbol,
            "quantity": quantity,
            "side": side,
            "order_type": order_type,
            "timestamp": time.time()
        }
        self._latency_map[msg["order_id"]] = time.time()
        self._send(json.dumps(msg))

    def request_market_data(self, symbol: str):
        """Request market data snapshot"""
        msg = {
            "type": "market_data_request",
            "symbol": symbol,
            "request_id": f"md_{symbol}_{time.time()}"
        }
        self._latency_map[msg["request_id"]] = time.time()
        self._send(json.dumps(msg))

    def send_heartbeat(self):
        """Send heartbeat"""
        msg = {
            "type": "heartbeat",
            "timestamp": time.time()
        }
        self._send(json.dumps(msg))

    def disconnect(self):
        """Disconnect WebSocket"""
        self.is_running = False
        if self.ws:
            self.ws.close()


class WebSocketLoadTest:
    """WebSocket load testing orchestrator"""

    def __init__(
        self,
        url: str,
        num_clients: int = 1000,
        symbols_per_client: int = 10,
        target_tps: int = 50000
    ):
        self.url = url
        self.num_clients = num_clients
        self.symbols_per_client = symbols_per_client
        self.target_tps = target_tps

        self.clients: List[TradingWebSocketClient] = []
        self.tick_buffer: List[TickData] = []
        self.tick_lock = threading.Lock()
        self.start_time = None
        self.end_time = None

        self.total_ticks = 0
        self.tick_throughput = 0

        self.symbols = self._generate_symbols(100)
        self.metrics = {
            "connection_success": 0,
            "connection_failure": 0,
            "messages_sent": 0,
            "messages_received": 0,
            "total_latencies": []
        }

    def _generate_symbols(self, count: int) -> List[str]:
        """Generate trading symbols"""
        prefixes = [
            "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "KOTAKBANK",
            "SBIN", "BHARTIARTL", "ITC", "L&T", "MARUTI", "SUNPHARMA",
            "ADANIPORTS", "TATAMOTORS", "WIPRO", "HCLTECH", "TECHM"
        ]
        symbols = []
        for _ in range(count):
            prefix = random.choice(prefixes)
            suffix = random.randint(1, 999)
            symbols.append(f"{prefix}{suffix}")
        return symbols

    def _handle_message(self, client_id: int, data: Dict):
        """Handle incoming message"""
        msg_type = data.get("type")
        if msg_type == "tick":
            tick = TickData(
                symbol=data.get("symbol", ""),
                price=data.get("price", 0),
                volume=data.get("volume", 0),
                timestamp=data.get("timestamp", time.time()),
                bid=data.get("bid", 0),
                ask=data.get("ask", 0),
                bid_size=data.get("bid_size", 0),
                ask_size=data.get("ask_size", 0)
            )
            with self.tick_lock:
                self.tick_buffer.append(tick)
                self.total_ticks += 1
        elif msg_type == "order_update":
            self.metrics["messages_received"] += 1

    def create_clients(self) -> int:
        """Create and connect all clients"""
        logger.info(f"Creating {self.num_clients} WebSocket clients...")

        for i in range(self.num_clients):
            client_symbols = random.sample(
                self.symbols,
                k=min(self.symbols_per_client, len(self.symbols))
            )

            client = TradingWebSocketClient(
                url=self.url,
                client_id=i,
                symbols=client_symbols,
                auth_token=f"token_{i}",
                on_message=self._handle_message
            )

            if client.connect(timeout=15):
                self.metrics["connection_success"] += 1
                client.subscribe(client_symbols)
            else:
                self.metrics["connection_failure"] += 1

            self.clients.append(client)

            if (i + 1) % 100 == 0:
                logger.info(f"Connected {i + 1}/{self.num_clients} clients")

        logger.info(f"Connection complete: {self.metrics['connection_success']} succeeded, "
                   f"{self.metrics['connection_failure']} failed")
        return self.metrics["connection_success"]

    def run_load_test(
        self,
        duration_seconds: int = 300,
        ramp_up_seconds: int = 30,
        message_interval_ms: int = 100
    ):
        """Run WebSocket load test"""
        logger.info(f"Starting load test: {duration_seconds}s duration, "
                   f"{ramp_up_seconds}s ramp-up")

        self.start_time = time.time()
        end_time = self.start_time + duration_seconds

        message_count = 0
        last_log = time.time()

        while time.time() < end_time:
            elapsed = time.time() - self.start_time

            if elapsed < ramp_up_seconds:
                active_clients = int(self.metrics["connection_success"] *
                                    (elapsed / ramp_up_seconds))
            else:
                active_clients = len(self.clients)

            for i in range(active_clients):
                client = self.clients[i]
                if client.is_connected:
                    client.request_market_data(random.choice(client.symbols))
                    message_count += 1

            current_time = time.time()
            if current_time - last_log >= 5:
                self._log_progress(message_count)
                last_log = current_time

            time.sleep(message_interval_ms / 1000.0)

        self.end_time = time.time()
        self._calculate_throughput()

    def _log_progress(self, message_count: int):
        """Log test progress"""
        elapsed = self.end_time - self.start_time if self.end_time else time.time() - self.start_time
        tick_count = self.total_ticks

        logger.info(f"Progress - Elapsed: {elapsed:.1f}s, "
                   f"Messages: {message_count}, "
                   f"Ticks: {tick_count}, "
                   f"Connected: {sum(1 for c in self.clients if c.is_connected)}")

    def _calculate_throughput(self):
        """Calculate tick throughput"""
        if self.start_time and self.end_time:
            duration = self.end_time - self.start_time
            self.tick_throughput = self.total_ticks / duration if duration > 0 else 0
            logger.info(f"Tick Throughput: {self.tick_throughput:.2f} ticks/sec")

    def run_latency_test(self, duration_seconds: int = 60):
        """Run latency benchmarking test"""
        logger.info(f"Starting latency test for {duration_seconds}s")

        start_time = time.time()
        end_time = start_time + duration_seconds

        while time.time() < end_time:
            for client in self.clients:
                if client.is_connected:
                    symbol = random.choice(client.symbols)
                    client.request_market_data(symbol)

            time.sleep(0.1)

        self._report_latency_stats()

    def _report_latency_stats(self):
        """Report latency statistics"""
        all_latencies = []
        for client in self.clients:
            all_latencies.extend(client.metrics.latencies)

        if all_latencies:
            all_latencies.sort()
            count = len(all_latencies)
            logger.info(f"Latency Stats (n={count}):")
            logger.info(f"  Avg: {statistics.mean(all_latencies):.2f}ms")
            logger.info(f"  P50: {all_latencies[count // 2]:.2f}ms")
            logger.info(f"  P95: {all_latencies[int(count * 0.95)]:.2f}ms")
            logger.info(f"  P99: {all_latencies[int(count * 0.99)]:.2f}ms")
            logger.info(f"  Max: {max(all_latencies):.2f}ms")

    def run_concurrency_test(self, max_concurrent: int = 1000):
        """Test concurrent connection handling"""
        logger.info(f"Testing concurrent connections up to {max_concurrent}")

        results = []
        for num_clients in [100, 250, 500, 750, max_concurrent]:
            logger.info(f"Testing with {num_clients} clients...")
            test_clients = []

            start = time.time()
            for i in range(num_clients):
                client = TradingWebSocketClient(
                    url=self.url,
                    client_id=i,
                    symbols=random.sample(self.symbols, k=5)
                )
                if client.connect(timeout=10):
                    test_clients.append(client)

            connect_time = time.time() - start

            time.sleep(5)

            for client in test_clients:
                client.disconnect()

            success_rate = len(test_clients) / num_clients
            results.append({
                "clients": num_clients,
                "connected": len(test_clients),
                "success_rate": success_rate,
                "connect_time": connect_time
            })

            logger.info(f"Result: {len(test_clients)}/{num_clients} connected "
                       f"in {connect_time:.2f}s")

        for r in results:
            logger.info(f"{r['clients']} clients: {r['connected']} connected, "
                       f"{r['success_rate']*100:.1f}% success rate")

    def cleanup(self):
        """Cleanup all connections"""
        logger.info("Cleaning up connections...")
        for client in self.clients:
            try:
                client.disconnect()
            except:
                pass

    def get_summary(self) -> Dict[str, Any]:
        """Get test summary"""
        connected = sum(1 for c in self.clients if c.is_connected)
        total_latencies = []
        total_messages_sent = 0
        total_messages_received = 0
        total_bytes_sent = 0
        total_bytes_received = 0

        for client in self.clients:
            total_latencies.extend(client.metrics.latencies)
            total_messages_sent += client.metrics.total_messages_sent
            total_messages_received += client.metrics.total_messages_received
            total_bytes_sent += client.metrics.total_bytes_sent
            total_bytes_received += client.metrics.total_bytes_received

        return {
            "total_clients": self.num_clients,
            "connected_clients": connected,
            "connection_success_rate": connected / self.num_clients if self.num_clients > 0 else 0,
            "total_ticks": self.total_ticks,
            "tick_throughput": self.tick_throughput,
            "total_messages_sent": total_messages_sent,
            "total_messages_received": total_messages_received,
            "total_bytes_sent": total_bytes_sent,
            "total_bytes_received": total_bytes_received,
            "latency": {
                "avg_ms": statistics.mean(total_latencies) if total_latencies else 0,
                "p50_ms": sorted(total_latencies)[len(total_latencies)//2] if total_latencies else 0,
                "p95_ms": sorted(total_latencies)[int(len(total_latencies)*0.95)] if total_latencies else 0,
                "p99_ms": sorted(total_latencies)[int(len(total_latencies)*0.99)] if total_latencies else 0,
                "max_ms": max(total_latencies) if total_latencies else 0
            } if total_latencies else {}
        }


class TickThroughputTest:
    """Dedicated tick throughput testing"""

    def __init__(self, url: str):
        self.url = url
        self.tick_producer = None
        self.tick_consumers = []
        self.ticks_processed = 0
        self.processing_times: List[float] = []

    def simulate_tick_stream(self, ticks_per_second: int, duration: int):
        """Simulate high-frequency tick stream"""
        logger.info(f"Simulating {ticks_per_second} ticks/sec for {duration}s")

        symbols = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"]

        start_time = time.time()
        interval = 1.0 / ticks_per_second

        while time.time() - start_time < duration:
            tick_start = time.time()

            for symbol in symbols:
                tick = {
                    "type": "tick",
                    "symbol": symbol,
                    "price": random.uniform(100, 5000),
                    "volume": random.randint(1, 10000),
                    "timestamp": time.time(),
                    "bid": random.uniform(99, 4999),
                    "ask": random.uniform(101, 5001),
                    "bid_size": random.randint(1, 1000),
                    "ask_size": random.randint(1, 1000)
                }
                self.ticks_processed += 1

            process_time = time.time() - tick_start
            self.processing_times.append(process_time)

            sleep_time = interval - process_time
            if sleep_time > 0:
                time.sleep(sleep_time)

        self._report_throughput()

    def _report_throughput(self):
        """Report throughput statistics"""
        if self.processing_times:
            avg_processing = statistics.mean(self.processing_times)
            max_processing = max(self.processing_times)
            logger.info(f"Processing Stats:")
            logger.info(f"  Total ticks: {self.ticks_processed}")
            logger.info(f"  Avg processing time: {avg_processing*1000:.2f}ms")
            logger.info(f"  Max processing time: {max_processing*1000:.2f}ms")
            logger.info(f"  Processing rate: {1/avg_processing:.0f} ticks/sec")


if __name__ == "__main__":
    import sys

    test_url = sys.argv[1] if len(sys.argv) > 1 else "ws://localhost:8080/ws"

    print(f"Running WebSocket load test against {test_url}")

    test = WebSocketLoadTest(
        url=test_url,
        num_clients=1000,
        symbols_per_client=10,
        target_tps=50000
    )

    try:
        test.create_clients()
        test.run_load_test(duration_seconds=60, ramp_up_seconds=10)
        test.run_latency_test(duration_seconds=30)
    finally:
        summary = test.get_summary()
        print("\n=== Test Summary ===")
        print(json.dumps(summary, indent=2))
        test.cleanup()