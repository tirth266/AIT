"""
Redis Stress Testing Framework for Trading Platform
Tests: Connection pooling, pub/sub throughput, data structure operations, caching
"""

import time
import random
import threading
import statistics
import logging
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import redis
except ImportError:
    print("Installing redis...")
    import subprocess
    subprocess.check_call(["pip", "install", "redis"])
    import redis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class RedisMetrics:
    """Redis operation metrics"""
    operation: str
    count: int = 0
    total_time_ms: float = 0
    errors: int = 0
    latencies: List[float] = field(default_factory=list)

    def add(self, latency_ms: float, error: bool = False):
        self.count += 1
        self.total_time_ms += latency_ms
        if latency_ms > 0:
            self.latencies.append(latency_ms)
        if error:
            self.errors += 1

    def get_stats(self) -> Dict[str, Any]:
        if not self.latencies:
            return {"count": self.count, "errors": self.errors}
        sorted_lats = sorted(self.latencies)
        return {
            "operation": self.operation,
            "count": self.count,
            "errors": self.errors,
            "avg_ms": statistics.mean(self.latencies),
            "p50_ms": sorted_lats[len(sorted_lats) // 2],
            "p95_ms": sorted_lats[int(len(sorted_lats) * 0.95)],
            "p99_ms": sorted_lats[int(len(sorted_lats) * 0.99)],
            "max_ms": max(self.latencies),
            "ops_per_sec": self.count / (self.total_time_ms / 1000) if self.total_time_ms > 0 else 0
        }


class RedisStressor:
    """Redis stress testing orchestrator"""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None
    ):
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.client = None
        self.pubsub_client = None
        self.metrics: Dict[str, RedisMetrics] = {}
        self.running = False
        self.subscribers: List[Dict] = []

    def connect(self, pool_size: int = 50) -> bool:
        """Connect to Redis"""
        try:
            self.client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                max_connections=pool_size,
                socket_timeout=5,
                socket_connect_timeout=5,
                decode_responses=True
            )
            self.client.ping()
            logger.info(f"Connected to Redis: {self.host}:{self.port}")
            return True
        except redis.ConnectionError as e:
            logger.error(f"Redis connection failed: {e}")
            return False

    def setup_test_data(self):
        """Setup initial test data"""
        symbols = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK",
                   "SBIN", "BHARTIARTL", "ITC", "L&T", "MARUTI"]

        # Setup market data cache
        for symbol in symbols:
            data = {
                "price": random.uniform(100, 5000),
                "volume": random.randint(10000, 1000000),
                "bid": random.uniform(99, 4999),
                "ask": random.uniform(101, 5001),
                "timestamp": time.time()
            }
            self.client.setex(f"market:{symbol}", 3600, json.dumps(data))

        # Setup order cache
        for i in range(1000):
            order = {
                "order_id": f"ORD_{i}",
                "symbol": random.choice(symbols),
                "quantity": random.randint(1, 1000),
                "status": random.choice(["PENDING", "FILLED", "CANCELLED"])
            }
            self.client.set(f"order:{i}", json.dumps(order))

        # Setup user sessions
        for i in range(100):
            session = {
                "user_id": f"user_{i}",
                "session_id": f"sess_{i}",
                "balance": random.uniform(10000, 1000000)
            }
            self.client.setex(f"session:{i}", 3600, json.dumps(session))

        logger.info("Test data setup complete")

    def stress_test_strings(
        self,
        num_operations: int = 100000,
        num_threads: int = 20
    ):
        """Stress test string operations"""
        logger.info(f"Stress testing strings: {num_operations} ops, {num_threads} threads")

        self.metrics["string_set"] = RedisMetrics("string_set")
        self.metrics["string_get"] = RedisMetrics("string_get")
        self.metrics["string_incr"] = RedisMetrics("string_incr")
        self.metrics["string_mget"] = RedisMetrics("string_mget")

        def worker(worker_id: int):
            for _ in range(num_operations // num_threads):
                # SET operations
                try:
                    start = time.perf_counter()
                    key = f"test:str:{random.randint(1, 10000)}"
                    value = f"value_{random.randint(1, 1000000)}"
                    self.client.set(key, value, ex=3600)
                    self.metrics["string_set"].add((time.perf_counter() - start) * 1000)
                except Exception as e:
                    self.metrics["string_set"].add(0, error=True)

                # GET operations
                try:
                    start = time.perf_counter()
                    key = f"test:str:{random.randint(1, 10000)}"
                    self.client.get(key)
                    self.metrics["string_get"].add((time.perf_counter() - start) * 1000)
                except Exception as e:
                    self.metrics["string_get"].add(0, error=True)

                # INCR operations (for counters)
                try:
                    start = time.perf_counter()
                    counter_key = f"counter:{random.randint(1, 100)}"
                    self.client.incr(counter_key)
                    self.metrics["string_incr"].add((time.perf_counter() - start) * 1000)
                except Exception as e:
                    self.metrics["string_incr"].add(0, error=True)

                # MGET operations
                try:
                    start = time.perf_counter()
                    keys = [f"test:str:{i}" for i in random.sample(range(1, 10001), 10)]
                    self.client.mget(keys)
                    self.metrics["string_mget"].add((time.perf_counter() - start) * 1000)
                except Exception as e:
                    self.metrics["string_mget"].add(0, error=True)

        self._run_parallel_workers(worker, num_threads)
        self._report_metrics("string")

    def stress_test_hashes(
        self,
        num_operations: int = 50000,
        num_threads: int = 10
    ):
        """Stress test hash operations (important for market data)"""
        logger.info(f"Stress testing hashes: {num_operations} ops, {num_threads} threads")

        self.metrics["hash_hset"] = RedisMetrics("hash_hset")
        self.metrics["hash_hget"] = RedisMetrics("hash_hget")
        self.metrics["hash_hgetall"] = RedisMetrics("hash_hgetall")
        self.metrics["hash_hincr"] = RedisMetrics("hash_hincr")

        symbols = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"]

        def worker(worker_id: int):
            for _ in range(num_operations // num_threads):
                symbol = random.choice(symbols)

                # HSET (update market data)
                try:
                    start = time.perf_counter()
                    self.client.hset(
                        f"market:data:{symbol}",
                        mapping={
                            "price": str(random.uniform(100, 5000)),
                            "volume": str(random.randint(10000, 1000000)),
                            "bid": str(random.uniform(99, 4999)),
                            "ask": str(random.uniform(101, 5001)),
                            "timestamp": str(time.time())
                        }
                    )
                    self.metrics["hash_hset"].add((time.perf_counter() - start) * 1000)
                except Exception as e:
                    self.metrics["hash_hset"].add(0, error=True)

                # HGET
                try:
                    start = time.perf_counter()
                    self.client.hget(f"market:data:{symbol}", "price")
                    self.metrics["hash_hget"].add((time.perf_counter() - start) * 1000)
                except Exception as e:
                    self.metrics["hash_hget"].add(0, error=True)

                # HGETALL
                try:
                    start = time.perf_counter()
                    self.client.hgetall(f"market:data:{symbol}")
                    self.metrics["hash_hgetall"].add((time.perf_counter() - start) * 1000)
                except Exception as e:
                    self.metrics["hash_hgetall"].add(0, error=True)

                # HINCR (for volume counters)
                try:
                    start = time.perf_counter()
                    self.client.hincrby(f"market:stats:{symbol}", "tick_count", 1)
                    self.metrics["hash_hincr"].add((time.perf_counter() - start) * 1000)
                except Exception as e:
                    self.metrics["hash_hincr"].add(0, error=True)

        self._run_parallel_workers(worker, num_threads)
        self._report_metrics("hash")

    def stress_test_lists(
        self,
        num_operations: int = 30000,
        num_threads: int = 10
    ):
        """Stress test list operations (for order queues)"""
        logger.info(f"Stress testing lists: {num_operations} ops, {num_threads} threads")

        self.metrics["list_lpush"] = RedisMetrics("list_lpush")
        self.metrics["list_rpush"] = RedisMetrics("list_rpush")
        self.metrics["list_lpop"] = RedisMetrics("list_lpop")
        self.metrics["list_lrange"] = RedisMetrics("list_lrange")

        def worker(worker_id: int):
            for _ in range(num_operations // num_threads):
                queue = f"order:queue:{random.randint(1, 10)}"

                # LPUSH (add to queue)
                try:
                    start = time.perf_counter()
                    order = json.dumps({
                        "order_id": f"ORD_{random.randint(1, 100000)}",
                        "symbol": random.choice(["RELIANCE", "TCS", "INFY"]),
                        "side": random.choice(["BUY", "SELL"])
                    })
                    self.client.lpush(queue, order)
                    self.metrics["list_lpush"].add((time.perf_counter() - start) * 1000)
                except Exception as e:
                    self.metrics["list_lpush"].add(0, error=True)

                # RPUSH
                try:
                    start = time.perf_counter()
                    self.client.rpush(queue, f"item_{random.randint(1, 1000)}")
                    self.metrics["list_rpush"].add((time.perf_counter() - start) * 1000)
                except Exception as e:
                    self.metrics["list_rpush"].add(0, error=True)

                # LRANGE
                try:
                    start = time.perf_counter()
                    self.client.lrange(queue, 0, 99)
                    self.metrics["list_lrange"].add((time.perf_counter() - start) * 1000)
                except Exception as e:
                    self.metrics["list_lrange"].add(0, error=True)

                # LPOP (consume from queue)
                try:
                    start = time.perf_counter()
                    self.client.lpop(queue)
                    self.metrics["list_lpop"].add((time.perf_counter() - start) * 1000)
                except Exception as e:
                    self.metrics["list_lpop"].add(0, error=True)

        self._run_parallel_workers(worker, num_threads)
        self._report_metrics("list")

    def stress_test_sets(
        self,
        num_operations: int = 30000,
        num_threads: int = 10
    ):
        """Stress test set operations (for watchlists)"""
        logger.info(f"Stress testing sets: {num_operations} ops, {num_threads} threads")

        self.metrics["set_sadd"] = RedisMetrics("set_sadd")
        self.metrics["set_smembers"] = RedisMetrics("set_smembers")
        self.metrics["set_sismember"] = RedisMetrics("set_sismember")
        self.metrics["set_spop"] = RedisMetrics("set_spop")

        def worker(worker_id: int):
            for _ in range(num_operations // num_threads):
                user_id = random.randint(1, 100)
                watchlist_key = f"watchlist:{user_id}"

                # SADD
                try:
                    start = time.perf_counter()
                    symbol = random.choice(["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"])
                    self.client.sadd(watchlist_key, symbol)
                    self.metrics["set_sadd"].add((time.perf_counter() - start) * 1000)
                except Exception as e:
                    self.metrics["set_sadd"].add(0, error=True)

                # SISMEMBER
                try:
                    start = time.perf_counter()
                    self.client.sismember(watchlist_key, "RELIANCE")
                    self.metrics["set_sismember"].add((time.perf_counter() - start) * 1000)
                except Exception as e:
                    self.metrics["set_sismember"].add(0, error=True)

                # SMEMBERS
                try:
                    start = time.perf_counter()
                    self.client.smembers(watchlist_key)
                    self.metrics["set_smembers"].add((time.perf_counter() - start) * 1000)
                except Exception as e:
                    self.metrics["set_smembers"].add(0, error=True)

                # SPOP (simulate remove)
                try:
                    start = time.perf_counter()
                    self.client.spop(watchlist_key)
                    self.metrics["set_spop"].add((time.perf_counter() - start) * 1000)
                except Exception as e:
                    self.metrics["set_spop"].add(0, error=True)

        self._run_parallel_workers(worker, num_threads)
        self._report_metrics("set")

    def stress_test_sorted_sets(
        self,
        num_operations: int = 30000,
        num_threads: int = 10
    ):
        """Stress test sorted set operations (for leaderboards, price levels)"""
        logger.info(f"Stress testing sorted sets: {num_operations} ops, {num_threads} threads")

        self.metrics["zset_zadd"] = RedisMetrics("zset_zadd")
        self.metrics["zset_zrange"] = RedisMetrics("zset_zrange")
        self.metrics["zset_zrank"] = RedisMetrics("zset_zrank")
        self.metrics["zset_zscore"] = RedisMetrics("zset_zscore")

        def worker(worker_id: int):
            for _ in range(num_operations // num_threads):
                # Price levels (order book)
                symbol = random.choice(["RELIANCE", "TCS", "INFY"])
                level_key = f"prices:{symbol}"

                # ZADD
                try:
                    start = time.perf_counter()
                    price = random.uniform(100, 5000)
                    self.client.zadd(level_key, {f"order_{random.randint(1, 10000)}": price})
                    self.metrics["zset_zadd"].add((time.perf_counter() - start) * 1000)
                except Exception as e:
                    self.metrics["zset_zadd"].add(0, error=True)

                # ZRANGE (get top N prices)
                try:
                    start = time.perf_counter()
                    self.client.zrange(level_key, 0, 9)
                    self.metrics["zset_zrange"].add((time.perf_counter() - start) * 1000)
                except Exception as e:
                    self.metrics["zset_zrange"].add(0, error=True)

                # ZRANK
                try:
                    start = time.perf_counter()
                    self.client.zrank(level_key, f"order_{random.randint(1, 1000)}")
                    self.metrics["zset_zrank"].add((time.perf_counter() - start) * 1000)
                except Exception as e:
                    self.metrics["zset_zrank"].add(0, error=True)

                # ZSCORE
                try:
                    start = time.perf_counter()
                    self.client.zscore(level_key, f"order_{random.randint(1, 1000)}")
                    self.metrics["zset_zscore"].add((time.perf_counter() - start) * 1000)
                except Exception as e:
                    self.metrics["zset_zscore"].add(0, error=True)

        self._run_parallel_workers(worker, num_threads)
        self._report_metrics("zset")

    def pubsub_throughput_test(
        self,
        num_publishers: int = 10,
        num_subscribers: int = 10,
        duration: int = 30
    ):
        """Test pub/sub throughput"""
        logger.info(f"Testing pub/sub: {num_publishers} publishers, {num_subscribers} subscribers")

        self.metrics["pubsub_publish"] = RedisMetrics("pubsub_publish")
        self.metrics["pubsub_subscribe"] = RedisMetrics("pubsub_subscribe")

        messages_received = {"count": 0, "lock": threading.Lock()}

        # Create subscriber clients
        for i in range(num_subscribers):
            sub_client = redis.Redis(host=self.host, port=self.port, db=self.db)
            pubsub = sub_client.pubsub()
            channel = f"market:updates:{i % 5}"
            pubsub.subscribe(channel)
            self.subscribers.append({"client": sub_client, "pubsub": pubsub, "channel": channel})

            def listen(sub_id):
                for message in pubsub.listen():
                    if message["type"] == "message":
                        with messages_received["lock"]:
                            messages_received["count"] += 1

            t = threading.Thread(target=listen, args=(i,), daemon=True)
            t.start()

        # Publish messages
        def publisher(pub_id):
            end_time = time.time() + duration
            while time.time() < end_time:
                try:
                    start = time.perf_counter()
                    channel = f"market:updates:{pub_id % 5}"
                    message = json.dumps({
                        "symbol": random.choice(["RELIANCE", "TCS", "INFY"]),
                        "price": random.uniform(100, 5000),
                        "timestamp": time.time()
                    })
                    self.client.publish(channel, message)
                    self.metrics["pubsub_publish"].add((time.perf_counter() - start) * 1000)
                except Exception as e:
                    self.metrics["pubsub_publish"].add(0, error=True)
                time.sleep(0.01)

        publishers = []
        for i in range(num_publishers):
            t = threading.Thread(target=publisher, args=(i,), daemon=True)
            t.start()
            publishers.append(t)

        time.sleep(duration)

        # Cleanup
        for sub in self.subscribers:
            sub["pubsub"].unsubscribe(sub["channel"])
            sub["pubsub"].close()
            sub["client"].close()

        logger.info(f"Pub/Sub Test: Published {self.metrics['pubsub_publish'].count} messages, "
                   f"Received ~{messages_received['count']} messages")
        self._report_metrics("pubsub")

    def connection_pool_test(
        self,
        num_connections: int = 50,
        operations_per_connection: int = 1000
    ):
        """Test connection pool performance"""
        logger.info(f"Testing connection pool: {num_connections} connections")

        self.metrics["pool_get"] = RedisMetrics("pool_get")
        self.metrics["pool_execute"] = RedisMetrics("pool_execute")

        pool = redis.ConnectionPool(
            host=self.host,
            port=self.port,
            db=self.db,
            max_connections=num_connections
        )

        def pool_worker(worker_id: int):
            client = redis.Redis(connection_pool=pool)
            for _ in range(operations_per_connection):
                try:
                    start = time.perf_counter()
                    client.ping()
                    self.metrics["pool_get"].add((time.perf_counter() - start) * 1000)
                except Exception as e:
                    self.metrics["pool_get"].add(0, error=True)

                try:
                    start = time.perf_counter()
                    client.get(f"test:key:{random.randint(1, 1000)}")
                    self.metrics["pool_execute"].add((time.perf_counter() - start) * 1000)
                except Exception as e:
                    self.metrics["pool_execute"].add(0, error=True)

        self._run_parallel_workers(pool_worker, num_connections)
        self._report_metrics("pool")

    def pipelining_test(self, num_operations: int = 100000):
        """Test Redis pipelining performance"""
        logger.info(f"Testing pipelining: {num_operations} operations")

        self.metrics["pipeline_set"] = RedisMetrics("pipeline_set")
        self.metrics["pipeline_get"] = RedisMetrics("pipeline_get")

        # Batch SET with pipeline
        start = time.perf_counter()
        pipe = self.client.pipeline()
        for i in range(num_operations):
            pipe.set(f"pipe:set:{i}", f"value_{i}", ex=3600)
        pipe.execute()
        self.metrics["pipeline_set"].add((time.perf_counter() - start) * 1000)
        logger.info(f"Pipeline SET: {num_operations} ops in {(time.perf_counter() - start)*1000:.2f}ms")

        # Batch GET with pipeline
        start = time.perf_counter()
        pipe = self.client.pipeline()
        for i in range(num_operations):
            pipe.get(f"pipe:set:{i}")
        results = pipe.execute()
        self.metrics["pipeline_get"].add((time.perf_counter() - start) * 1000)
        logger.info(f"Pipeline GET: {num_operations} ops in {(time.perf_counter() - start)*1000:.2f}ms")

        self._report_metrics("pipeline")

    def _run_parallel_workers(self, worker_func, num_threads: int):
        """Run workers in parallel"""
        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=worker_func, args=(i,))
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

    def _report_metrics(self, test_name: str):
        """Report metrics for a test"""
        logger.info(f"\n=== {test_name.upper()} Test Results ===")
        for name, metrics in self.metrics.items():
            if name.startswith(test_name.split('_')[0]) or test_name == "all":
                stats = metrics.get_stats()
                logger.info(f"\n{stats['operation']}:")
                logger.info(f"  Count: {stats['count']}")
                logger.info(f"  Errors: {stats['errors']}")
                logger.info(f"  Avg: {stats.get('avg_ms', 0):.2f}ms")
                logger.info(f"  P95: {stats.get('p95_ms', 0):.2f}ms")
                logger.info(f"  Ops/sec: {stats.get('ops_per_sec', 0):.0f}")

    def cleanup(self):
        """Cleanup test data"""
        if self.client:
            patterns = ["test:*", "market:*", "order:*", "prices:*", "watchlist:*", "counter:*"]
            for pattern in patterns:
                try:
                    keys = self.client.keys(pattern)
                    if keys:
                        self.client.delete(*keys)
                except:
                    pass

            self.client.close()
            logger.info("Redis connection closed")


if __name__ == "__main__":
    import sys

    redis_host = sys.argv[1] if len(sys.argv) > 1 else "localhost"
    redis_port = int(sys.argv[2]) if len(sys.argv) > 2 else 6379

    stress = RedisStressor(host=redis_host, port=redis_port)

    if stress.connect():
        stress.setup_test_data()

        stress.stress_test_strings(num_operations=50000, num_threads=20)
        stress.stress_test_hashes(num_operations=30000, num_threads=10)
        stress.stress_test_lists(num_operations=20000, num_threads=10)
        stress.stress_test_sets(num_operations=20000, num_threads=10)
        stress.stress_test_sorted_sets(num_operations=20000, num_threads=10)
        stress.pubsub_throughput_test(num_publishers=5, num_subscribers=5, duration=20)
        stress.connection_pool_test(num_connections=30, operations_per_connection=500)
        stress.pipelining_test(num_operations=10000)

        stress.cleanup()
    else:
        logger.error("Failed to connect to Redis")