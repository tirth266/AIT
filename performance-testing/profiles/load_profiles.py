"""
Load Testing Profiles
Defines various load patterns for different test scenarios
"""

from typing import Dict, List, Any
from dataclasses import dataclass
import json


@dataclass
class LoadProfile:
    """Load profile configuration"""
    name: str
    description: str
    duration_minutes: int
    users: int
    spawn_rate: int
    operations_per_user: int
    operations: Dict[str, float]


class LoadProfileLibrary:
    """Library of predefined load profiles"""

    @staticmethod
    def smoke_test() -> LoadProfile:
        """Basic smoke test - verify system functions"""
        return LoadProfile(
            name="smoke_test",
            description="Basic smoke test to verify system functionality",
            duration_minutes=5,
            users=10,
            spawn_rate=5,
            operations_per_user=10,
            operations={
                "get_market_data": 0.4,
                "place_order": 0.2,
                "get_positions": 0.2,
                "get_portfolio": 0.2
            }
        )

    @staticmethod
    def load_test() -> LoadProfile:
        """Normal load test - expected production load"""
        return LoadProfile(
            name="load_test",
            description="Normal production load simulation",
            duration_minutes=30,
            users=200,
            spawn_rate=20,
            operations_per_user=50,
            operations={
                "get_market_data": 0.5,
                "get_order_book": 0.15,
                "place_order": 0.15,
                "get_positions": 0.1,
                "get_portfolio": 0.1
            }
        )

    @staticmethod
    def stress_test() -> LoadProfile:
        """Stress test - push system to breaking point"""
        return LoadProfile(
            name="stress_test",
            description="Stress test to find system limits",
            duration_minutes=60,
            users=1000,
            spawn_rate=50,
            operations_per_user=200,
            operations={
                "get_market_data": 0.4,
                "get_order_book": 0.2,
                "place_order": 0.2,
                "cancel_order": 0.05,
                "get_positions": 0.1,
                "get_portfolio": 0.05
            }
        )

    @staticmethod
    def spike_test() -> LoadProfile:
        """Spike test - sudden burst of traffic"""
        return LoadProfile(
            name="spike_test",
            description="Sudden spike in user load",
            duration_minutes=10,
            users=1500,
            spawn_rate=200,
            operations_per_user=30,
            operations={
                "get_market_data": 0.6,
                "place_order": 0.3,
                "get_positions": 0.1
            }
        )

    @staticmethod
    def soak_test() -> LoadProfile:
        """Soak test - extended duration at moderate load"""
        return LoadProfile(
            name="soak_test",
            description="Long duration stress to find memory leaks",
            duration_minutes=240,
            users=300,
            spawn_rate=10,
            operations_per_user=500,
            operations={
                "get_market_data": 0.4,
                "get_order_book": 0.15,
                "place_order": 0.25,
                "get_positions": 0.1,
                "get_portfolio": 0.1
            }
        )

    @staticmethod
    def websocket_concurrency_test() -> LoadProfile:
        """WebSocket concurrent connections test"""
        return LoadProfile(
            name="websocket_concurrency",
            description="Test WebSocket handling of concurrent connections",
            duration_minutes=20,
            users=1000,
            spawn_rate=100,
            operations_per_user=100,
            operations={
                "ws_subscribe": 0.3,
                "ws_market_data": 0.5,
                "ws_place_order": 0.1,
                "ws_heartbeat": 0.1
            }
        )

    @staticmethod
    def high_frequency_trading_test() -> LoadProfile:
        """HFT simulation - very high message rate"""
        return LoadProfile(
            name="hft_test",
            description="High-frequency trading workload",
            duration_minutes=15,
            users=100,
            spawn_rate=20,
            operations_per_user=1000,
            operations={
                "get_market_data": 0.6,
                "get_order_book": 0.2,
                "place_order": 0.2
            }
        )

    @staticmethod
    def mixed_workload_test() -> LoadProfile:
        """Mixed workload - realistic trading patterns"""
        return LoadProfile(
            name="mixed_workload",
            description="Mixed realistic trading patterns",
            duration_minutes=45,
            users=500,
            spawn_rate=30,
            operations_per_user=100,
            operations={
                "get_market_data": 0.3,
                "get_order_book": 0.15,
                "place_order": 0.2,
                "cancel_order": 0.05,
                "get_positions": 0.1,
                "get_portfolio": 0.1,
                "get_watchlist": 0.05,
                "get_history": 0.05
            }
        )

    @staticmethod
    def get_all_profiles() -> Dict[str, LoadProfile]:
        """Get all predefined profiles"""
        return {
            "smoke": LoadProfileLibrary.smoke_test(),
            "load": LoadProfileLibrary.load_test(),
            "stress": LoadProfileLibrary.stress_test(),
            "spike": LoadProfileLibrary.spike_test(),
            "soak": LoadProfileLibrary.soak_test(),
            "websocket": LoadProfileLibrary.websocket_concurrency_test(),
            "hft": LoadProfileLibrary.high_frequency_trading_test(),
            "mixed": LoadProfileLibrary.mixed_workload_test()
        }


class ProfileExecutor:
    """Execute load profiles and generate configuration"""

    def __init__(self, profile: LoadProfile):
        self.profile = profile

    def to_locust_config(self) -> Dict[str, Any]:
        """Generate Locust configuration"""
        return {
            "users": self.profile.users,
            "spawn_rate": self.profile.spawn_rate,
            "run_time": f"{self.profile.duration_minutes}m",
            "host": "${BASE_URL}",
            "headless": True,
            "html": "report.html",
            "csv": "results"
        }

    def to_k6_options(self) -> Dict[str, Any]:
        """Generate k6 configuration"""
        stages = []
        if self.profile.spawn_rate > 0:
            stages = [
                {"duration": "1m", "target": self.profile.users // 4},
                {"duration": "2m", "target": self.profile.users // 2},
                {"duration": f"{self.profile.duration_minutes - 3}m", "target": self.profile.users},
                {"duration": "1m", "target": 0}
            ]

        return {
            "stages": stages,
            "vus": self.profile.users,
            "duration": f"{self.profile.duration_minutes}m"
        }

    def to_json(self) -> str:
        """Export profile as JSON"""
        return json.dumps({
            "name": self.profile.name,
            "description": self.profile.description,
            "duration_minutes": self.profile.duration_minutes,
            "users": self.profile.users,
            "spawn_rate": self.profile.spawn_rate,
            "operations_per_user": self.profile.operations_per_user,
            "operations": self.profile.operations
        }, indent=2)


def generate_locustfile(profile: LoadProfile) -> str:
    """Generate a Locust file from a profile"""
    return f'''"""
Auto-generated Locust file for {profile.name}
"""

from locust import HttpUser, task, between, constant
import random

class TradingUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        self.client.post("/api/auth/login", json={{
            "username": "test_user",
            "password": "test_password"
        }})

    @task({profile.operations.get("get_market_data", 0.5)})
    def get_market_data(self):
        symbols = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"]
        self.client.get(f"/api/market/{{random.choice(symbols)}}")

    @task({profile.operations.get("place_order", 0.2)})
    def place_order(self):
        symbols = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"]
        self.client.post("/api/orders", json={{
            "symbol": random.choice(symbols),
            "quantity": random.randint(1, 100),
            "side": random.choice(["BUY", "SELL"]),
            "order_type": "MARKET"
        }})

    @task({profile.operations.get("get_positions", 0.1)})
    def get_positions(self):
        self.client.get("/api/positions")

    @task({profile.operations.get("get_portfolio", 0.1)})
    def get_portfolio(self):
        self.client.get("/api/portfolio")
'''


if __name__ == "__main__":
    profiles = LoadProfileLibrary.get_all_profiles()

    print("=== Load Testing Profiles ===\n")
    for name, profile in profiles.items():
        print(f"\n{name.upper()}:")
        print(f"  Description: {profile.description}")
        print(f"  Duration: {profile.duration_minutes} minutes")
        print(f"  Users: {profile.users}")
        print(f"  Spawn Rate: {profile.spawn_rate} users/sec")
        print(f"  Operations: {profile.operations}")

    # Export to JSON
    profiles_json = {name: {
        "name": p.name,
        "description": p.description,
        "duration_minutes": p.duration_minutes,
        "users": p.users,
        "spawn_rate": p.spawn_rate,
        "operations": p.operations
    } for name, p in profiles.items()}

    with open("load_profiles.json", "w") as f:
        json.dump(profiles_json, f, indent=2)

    print("\n\nProfiles exported to load_profiles.json")