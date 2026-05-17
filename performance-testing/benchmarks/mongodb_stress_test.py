"""
MongoDB Stress Testing Framework for Trading Platform
Tests: CRUD operations, aggregation performance, indexing, connection pooling
"""

import time
import random
import threading
import statistics
import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

try:
    from pymongo import MongoClient, ASCENDING, DESCENDING
    from pymongo.errors import (
        ConnectionFailure, ServerSelectionTimeoutError,
        BulkWriteError, OperationFailure
    )
except ImportError:
    print("Installing pymongo...")
    import subprocess
    subprocess.check_call(["pip", "install", "pymongo"])
    from pymongo import MongoClient, ASCENDING, DESCENDING
    from pymongo.errors import (
        ConnectionFailure, ServerSelectionTimeoutError,
        BulkWriteError, OperationFailure
    )

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class MongoDBMetrics:
    """MongoDB operation metrics"""
    operation: str
    count: int = 0
    total_time_ms: float = 0
    errors: int = 0
    latencies: List[float] = field(default_factory=list)

    def add(self, latency_ms: float, error: bool = False):
        self.count += 1
        self.total_time_ms += latency_ms
        self.latencies.append(latency_ms)
        if error:
            self.errors += 1

    def get_stats(self) -> Dict[str, Any]:
        if not self.latencies:
            return {"count": 0, "errors": self.errors}
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
            "min_ms": min(self.latencies),
            "ops_per_sec": self.count / (self.total_time_ms / 1000) if self.total_time_ms > 0 else 0
        }


class MongoDBStressor:
    """MongoDB stress testing orchestrator"""

    def __init__(
        self,
        connection_string: str = "mongodb://localhost:27017",
        database_name: str = "trading_platform"
    ):
        self.connection_string = connection_string
        self.database_name = database_name
        self.client = None
        self.db = None

        self.metrics: Dict[str, MongoDBMetrics] = {}
        self.running = False

    def connect(self, timeout: int = 10) -> bool:
        """Connect to MongoDB"""
        try:
            self.client = MongoClient(
                self.connection_string,
                serverSelectionTimeoutMS=timeout * 1000,
                maxPoolSize=100,
                minPoolSize=10,
                connectTimeoutMS=10000,
                socketTimeoutMS=30000
            )
            self.client.admin.command('ping')
            self.db = self.client[self.database_name]
            logger.info(f"Connected to MongoDB: {self.database_name}")
            return True
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"MongoDB connection failed: {e}")
            return False

    def setup_collections(self):
        """Create test collections with indexes"""
        collections = [
            "orders", "positions", "market_data", "orderbook",
            "portfolio", "users", "watchlist", "trades", "instruments"
        ]

        for coll_name in collections:
            if coll_name not in self.db.list_collection_names():
                self.db.create_collection(coll_name)
                logger.info(f"Created collection: {coll_name}")

            # Create indexes
            if coll_name == "orders":
                self.db[coll_name].create_index("order_id", unique=True)
                self.db[coll_name].create_index("user_id")
                self.db[coll_name].create_index("symbol")
                self.db[coll_name].create_index([("created_at", DESCENDING)])
                self.db[coll_name].create_index([("status", ASCENDING)])

            elif coll_name == "market_data":
                self.db[coll_name].create_index("symbol")
                self.db[coll_name].create_index([("timestamp", DESCENDING)])
                self.db[coll_name].create_index([("symbol", 1), ("timestamp", -1)])

            elif coll_name == "trades":
                self.db[coll_name].create_index("trade_id", unique=True)
                self.db[coll_name].create_index("order_id")
                self.db[coll_name].create_index("symbol")
                self.db[coll_name].create_index([("timestamp", DESCENDING)])

        logger.info("Collection indexes created")

    def stress_test_orders(
        self,
        num_operations: int = 10000,
        num_threads: int = 10,
        read_write_ratio: float = 0.7
    ):
        """Stress test order operations"""
        logger.info(f"Stress testing orders: {num_operations} operations, {num_threads} threads")

        self.metrics["orders_insert"] = MongoDBMetrics("orders_insert")
        self.metrics["orders_read"] = MongoDBMetrics("orders_read")
        self.metrics["orders_update"] = MongoDBMetrics("orders_update")
        self.metrics["orders_delete"] = MongoDBMetrics("orders_delete")

        symbols = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"]
        statuses = ["PENDING", "FILLED", "CANCELLED", "REJECTED"]

        def worker(worker_id: int):
            for i in range(num_operations // num_threads):
                op_type = random.random()

                if op_type < read_write_ratio:
                    # Read operations
                    try:
                        start = time.perf_counter()
                        symbol = random.choice(symbols)
                        orders = list(self.db.orders.find(
                            {"symbol": symbol},
                            limit=100
                        ).sort("created_at", -1))
                        latency = (time.perf_counter() - start) * 1000
                        self.metrics["orders_read"].add(latency)
                    except Exception as e:
                        self.metrics["orders_read"].add(0, error=True)
                        logger.debug(f"Read error: {e}")

                elif op_type < read_write_ratio + (1 - read_write_ratio) * 0.6:
                    # Insert operations
                    try:
                        start = time.perf_counter()
                        order_doc = {
                            "order_id": f"ORD_{worker_id}_{i}_{time.time_ns()}",
                            "user_id": f"user_{random.randint(1, 1000)}",
                            "symbol": random.choice(symbols),
                            "side": random.choice(["BUY", "SELL"]),
                            "order_type": random.choice(["MARKET", "LIMIT"]),
                            "quantity": random.randint(1, 1000),
                            "price": random.uniform(100, 5000) if random.random() > 0.5 else None,
                            "status": random.choice(statuses),
                            "filled_quantity": random.randint(0, 1000),
                            "created_at": datetime.now(),
                            "updated_at": datetime.now()
                        }
                        self.db.orders.insert_one(order_doc)
                        latency = (time.perf_counter() - start) * 1000
                        self.metrics["orders_insert"].add(latency)
                    except Exception as e:
                        self.metrics["orders_insert"].add(0, error=True)

                else:
                    # Update operations
                    try:
                        start = time.perf_counter()
                        result = self.db.orders.update_one(
                            {"status": "PENDING"},
                            {"$set": {"status": random.choice(statuses), "updated_at": datetime.now()}},
                            upsert=False
                        )
                        latency = (time.perf_counter() - start) * 1000
                        self.metrics["orders_update"].add(latency)
                    except Exception as e:
                        self.metrics["orders_update"].add(0, error=True)

        self._run_parallel_workers(worker, num_threads)
        self._report_metrics("orders")

    def stress_test_market_data(
        self,
        writes_per_second: int = 5000,
        duration_seconds: int = 60
    ):
        """Stress test market data writes (high throughput)"""
        logger.info(f"Stress testing market data: {writes_per_second} writes/sec for {duration_seconds}s")

        self.metrics["market_data_write"] = MongoDBMetrics("market_data_write")
        self.metrics["market_data_read"] = MongoDBMetrics("market_data_read")

        symbols = [f"SYMBOL{i}" for i in range(100)]

        def write_worker():
            interval = 1.0 / writes_per_second
            start_time = time.time()

            while time.time() - start_time < duration_seconds:
                batch_start = time.perf_counter()

                # Batch insert
                docs = []
                for _ in range(100):
                    docs.append({
                        "symbol": random.choice(symbols),
                        "price": random.uniform(100, 5000),
                        "volume": random.randint(1, 100000),
                        "bid": random.uniform(99, 4999),
                        "ask": random.uniform(101, 5001),
                        "bid_size": random.randint(1, 1000),
                        "ask_size": random.randint(1, 1000),
                        "timestamp": datetime.now()
                    })

                try:
                    self.db.market_data.insert_many(docs, ordered=False)
                    latency = (time.perf_counter() - batch_start) * 1000
                    self.metrics["market_data_write"].add(latency)
                except BulkWriteError as e:
                    self.metrics["market_data_write"].add(0, error=True)

                sleep_time = interval * 100 - (time.perf_counter() - batch_start)
                if sleep_time > 0:
                    time.sleep(sleep_time)

        read_thread = threading.Thread(target=self._market_data_reader, args=(duration_seconds,))
        read_thread.start()

        write_worker()
        read_thread.join()

        self._report_metrics("market_data")

    def _market_data_reader(self, duration: int):
        """Background reader for market data"""
        symbols = [f"SYMBOL{i}" for i in range(100)]
        start_time = time.time()

        while time.time() - start_time < duration:
            try:
                start = time.perf_counter()
                symbol = random.choice(symbols)
                data = list(self.db.market_data.find(
                    {"symbol": symbol}
                ).sort("timestamp", -1).limit(10))
                latency = (time.perf_counter() - start) * 1000
                self.metrics["market_data_read"].add(latency)
            except Exception as e:
                self.metrics["market_data_read"].add(0, error=True)

            time.sleep(0.01)

    def stress_test_aggregations(self, num_operations: int = 1000):
        """Stress test aggregation pipelines"""
        logger.info(f"Stress testing aggregations: {num_operations} operations")

        self.metrics["aggregation_orders"] = MongoDBMetrics("aggregation_orders")
        self.metrics["aggregation_portfolio"] = MongoDBMetrics("aggregation_portfolio")
        self.metrics["aggregation_market"] = MongoDBMetrics("aggregation_market")

        # Portfolio aggregation
        def portfolio_agg():
            try:
                start = time.perf_counter()
                pipeline = [
                    {"$match": {"user_id": {"$regex": "user_"}}},
                    {"$group": {
                        "_id": "$symbol",
                        "total_quantity": {"$sum": "$quantity"},
                        "avg_price": {"$avg": "$price"},
                        "count": {"$sum": 1}
                    }},
                    {"$sort": {"count": -1}},
                    {"$limit": 100}
                ]
                list(self.db.orders.aggregate(pipeline))
                latency = (time.perf_counter() - start) * 1000
                self.metrics["aggregation_portfolio"].add(latency)
            except Exception as e:
                self.metrics["aggregation_portfolio"].add(0, error=True)

        # Market data aggregation
        def market_agg():
            try:
                start = time.perf_counter()
                pipeline = [
                    {"$group": {
                        "_id": "$symbol",
                        "avg_price": {"$avg": "$price"},
                        "total_volume": {"$sum": "$volume"},
                        "last_price": {"$last": "$price"}
                    }},
                    {"$sort": {"total_volume": -1}},
                    {"$limit": 50}
                ]
                list(self.db.market_data.aggregate(pipeline))
                latency = (time.perf_counter() - start) * 1000
                self.metrics["aggregation_market"].add(latency)
            except Exception as e:
                self.metrics["aggregation_market"].add(0, error=True)

        # Order status aggregation
        def orders_agg():
            try:
                start = time.perf_counter()
                pipeline = [
                    {"$group": {
                        "_id": "$status",
                        "count": {"$sum": 1},
                        "total_quantity": {"$sum": "$quantity"}
                    }},
                    {"$sort": {"count": -1}}
                ]
                list(self.db.orders.aggregate(pipeline))
                latency = (time.perf_counter() - start) * 1000
                self.metrics["aggregation_orders"].add(latency)
            except Exception as e:
                self.metrics["aggregation_orders"].add(0, error=True)

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = []
            for _ in range(num_operations):
                futures.append(executor.submit(portfolio_agg))
                futures.append(executor.submit(market_agg))
                futures.append(executor.submit(orders_agg))

            for f in as_completed(futures):
                pass

        self._report_metrics("aggregations")

    def connection_pool_test(self, num_connections: int = 100, duration: int = 60):
        """Test connection pool performance"""
        logger.info(f"Testing connection pool: {num_connections} connections for {duration}s")

        self.metrics["connection_pool"] = MongoDBMetrics("connection_pool")

        def connection_worker(worker_id: int):
            client = MongoClient(
                self.connection_string,
                maxPoolSize=10,
                minPoolSize=5
            )
            db = client[self.database_name]

            end_time = time.time() + duration
            while time.time() < end_time:
                try:
                    start = time.perf_counter()
                    db.orders.find_one()
                    latency = (time.perf_counter() - start) * 1000
                    self.metrics["connection_pool"].add(latency)
                except Exception as e:
                    self.metrics["connection_pool"].add(0, error=True)
                time.sleep(0.1)

            client.close()

        threads = []
        for i in range(num_connections):
            t = threading.Thread(target=connection_worker, args=(i,))
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

        self._report_metrics("connection_pool")

    def bulk_operations_test(self, num_docs: int = 100000):
        """Test bulk write operations"""
        logger.info(f"Testing bulk operations: {num_docs} documents")

        self.metrics["bulk_insert"] = MongoDBMetrics("bulk_insert")
        self.metrics["bulk_update"] = MongoDBMetrics("bulk_update")

        # Generate bulk insert
        symbols = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"]
        docs = [
            {
                "order_id": f"BULK_ORD_{i}",
                "symbol": random.choice(symbols),
                "quantity": random.randint(1, 1000),
                "price": random.uniform(100, 5000),
                "created_at": datetime.now()
            }
            for i in range(num_docs)
        ]

        # Bulk insert
        start = time.perf_counter()
        try:
            result = self.db.orders.insert_many(docs, ordered=False)
            latency = (time.perf_counter() - start) * 1000
            self.metrics["bulk_insert"].add(latency)
            logger.info(f"Bulk inserted {len(result.inserted_ids)} documents in {latency:.2f}ms")
        except Exception as e:
            logger.error(f"Bulk insert failed: {e}")

        # Bulk update
        start = time.perf_counter()
        bulk_ops = [
            {"update_one": {
                "filter": {"order_id": f"BULK_ORD_{i}"},
                "update": {"$set": {"status": random.choice(["FILLED", "PENDING"])}}
            }}
            for i in range(0, num_docs, 10)
        ]

        try:
            result = self.db.orders.bulk_write([
                {"update_one": {
                    "filter": {"order_id": f"BULK_ORD_{i}"},
                    "update": {"$set": {"status": "FILLED"}}
                }}
                for i in range(min(1000, num_docs))
            ], ordered=False)
            latency = (time.perf_counter() - start) * 1000
            self.metrics["bulk_update"].add(latency)
            logger.info(f"Bulk updated in {latency:.2f}ms")
        except Exception as e:
            logger.error(f"Bulk update failed: {e}")

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
                logger.info(f"  P99: {stats.get('p99_ms', 0):.2f}ms")
                logger.info(f"  Max: {stats.get('max_ms', 0):.2f}ms")

    def cleanup(self):
        """Cleanup test data"""
        if self.db:
            for coll in ["orders", "market_data", "trades"]:
                try:
                    self.db[coll].drop()
                    logger.info(f"Dropped collection: {coll}")
                except:
                    pass

        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")


if __name__ == "__main__":
    import sys

    mongo_url = sys.argv[1] if len(sys.argv) > 1 else "mongodb://localhost:27017"

    stress = MongoDBStressor(mongo_url, "trading_perf_test")

    if stress.connect():
        stress.setup_collections()

        stress.stress_test_orders(num_operations=10000, num_threads=10)
        stress.stress_test_market_data(writes_per_second=1000, duration_seconds=30)
        stress.stress_test_aggregations(num_operations=500)
        stress.connection_pool_test(num_connections=50, duration=30)
        stress.bulk_operations_test(num_docs=10000)

        stress.cleanup()
    else:
        logger.error("Failed to connect to MongoDB")