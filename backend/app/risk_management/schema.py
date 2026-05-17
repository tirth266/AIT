"""
Risk Management Database Schema
================================
MongoDB collections and indexes for institutional-grade risk management.
"""

from typing import Dict, List, Any
from datetime import datetime, timezone


RISK_POSITIONS_SCHEMA = {
    "collection": "risk_positions",
    "indexes": [
        {"keys": [("user_id", 1), ("symbol", 1)], "name": "user_symbol_idx"},
        {"keys": [("user_id", 1), ("updated_at", -1)], "name": "user_time_idx"},
        {"keys": [("strategy_id", 1)], "name": "strategy_idx"},
        {"keys": [("status", 1)], "name": "status_idx"}
    ],
    "validator": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["user_id", "symbol", "side", "quantity"],
            "properties": {
                "user_id": {"bsonType": "string"},
                "strategy_id": {"bsonType": "string"},
                "symbol": {"bsonType": "string"},
                "side": {"enum": ["BUY", "SELL"]},
                "quantity": {"bsonType": "int"},
                "average_price": {"bsonType": "double"},
                "current_price": {"bsonType": "double"},
                "value": {"bsonType": "double"},
                "unrealized_pnl": {"bsonType": "double"},
                "realized_pnl": {"bsonType": "double"},
                "sector": {"bsonType": "string"},
                "product_type": {"bsonType": "string"},
                "exchange": {"bsonType": "string"},
                "status": {"enum": ["OPEN", "CLOSED", "PENDING"]},
                "created_at": {"bsonType": "date"},
                "updated_at": {"bsonType": "date"}
            }
        }
    }
}


RISK_METRICS_SCHEMA = {
    "collection": "risk_metrics",
    "indexes": [
        {"keys": [("user_id", 1), ("metric_type", 1), ("timestamp", -1)], "name": "user_metric_time_idx"},
        {"keys": [("timestamp", -1)], "name": "time_idx"}
    ],
    "validator": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["user_id", "metric_type", "value", "timestamp"],
            "properties": {
                "user_id": {"bsonType": "string"},
                "metric_type": {
                    "enum": ["var", "var_99", "expected_shortfall", "drawdown", "margin", "greeks"]
                },
                "value": {"bsonType": "double"},
                "confidence_level": {"bsonType": "double"},
                "horizon_days": {"bsonType": "int"},
                "component_values": {"bsonType": "object"},
                "timestamp": {"bsonType": "date"},
                "calculation_method": {"bsonType": "string"}
            }
        }
    }
}


RISK_LIMITS_SCHEMA = {
    "collection": "risk_limits",
    "indexes": [
        {"keys": [("user_id", 1), ("limit_type", 1)], "name": "user_limit_idx"},
        {"keys": [("strategy_id", 1)], "name": "strategy_idx"},
        {"keys": [("is_active", 1)], "name": "active_idx"}
    ],
    "validator": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["user_id", "limit_type", "value", "created_at"],
            "properties": {
                "user_id": {"bsonType": "string"},
                "strategy_id": {"bsonType": "string"},
                "limit_type": {
                    "enum": [
                        "position_value", "sector_exposure", "daily_loss",
                        "margin_utilization", "drawdown", "order_rate",
                        "order_value", "var_limit", "greeks_delta", "greeks_gamma"
                    ]
                },
                "value": {"bsonType": "double"},
                "soft_limit": {"bsonType": "double"},
                "hard_limit": {"bsonType": "double"},
                "window_seconds": {"bsonType": "int"},
                "is_active": {"bsonType": "bool"},
                "created_at": {"bsonType": "date"},
                "updated_at": {"bsonType": "date"},
                "created_by": {"bsonType": "string"}
            }
        }
    }
}


RISK_ALERTS_SCHEMA = {
    "collection": "risk_alerts",
    "indexes": [
        {"keys": [("user_id", 1), ("alert_type", 1), ("timestamp", -1)], "name": "user_alert_idx"},
        {"keys": [("severity", 1), ("is_resolved", 1)], "name": "severity_resolved_idx"},
        {"keys": [("timestamp", -1)], "name": "time_idx"}
    ],
    "validator": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["user_id", "alert_type", "severity", "timestamp"],
            "properties": {
                "user_id": {"bsonType": "string"},
                "strategy_id": {"bsonType": "string"},
                "alert_type": {
                    "enum": [
                        "limit_breach", "margin_call", "drawdown_alert",
                        "var_breach", "circuit_breaker", "fat_finger",
                        "correlation_breach", "greeks_limit", "stress_test"
                    ]
                },
                "severity": {"enum": ["info", "warning", "critical", "emergency"]},
                "message": {"bsonType": "string"},
                "current_value": {"bsonType": "double"},
                "limit_value": {"bsonType": "double"},
                "is_resolved": {"bsonType": "bool"},
                "resolved_at": {"bsonType": "date"},
                "resolved_by": {"bsonType": "string"},
                "timestamp": {"bsonType": "date"},
                "metadata": {"bsonType": "object"}
            }
        }
    }
}


RISK_SCENARIOS_SCHEMA = {
    "collection": "risk_scenarios",
    "indexes": [
        {"keys": [("user_id", 1), ("scenario_type", 1), ("timestamp", -1)], "name": "user_scenario_idx"},
        {"keys": [("scenario_id", 1)], "name": "scenario_idx"}
    ],
    "validator": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["user_id", "scenario_id", "scenario_name", "timestamp"],
            "properties": {
                "user_id": {"bsonType": "string"},
                "scenario_id": {"bsonType": "string"},
                "scenario_name": {"bsonType": "string"},
                "scenario_type": {"enum": ["historical", "hypothetical", "custom", "reverse"]},
                "severity": {"enum": ["low", "medium", "high", "severe", "extreme"]},
                "portfolio_before": {"bsonType": "double"},
                "portfolio_after": {"bsonType": "double"},
                "loss_amount": {"bsonType": "double"},
                "loss_percent": {"bsonType": "double"},
                "position_impacts": {"bsonType": "object"},
                "var_before": {"bsonType": "double"},
                "var_after": {"bsonType": "double"},
                "timestamp": {"bsonType": "date"}
            }
        }
    }
}


RISK_BREACHES_SCHEMA = {
    "collection": "risk_breaches",
    "indexes": [
        {"keys": [("user_id", 1), ("breach_type", 1), ("timestamp", -1)], "name": "user_breach_idx"},
        {"keys": [("is_resolved", 1), ("timestamp", -1)], "name": "resolved_time_idx"}
    ],
    "validator": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["user_id", "breach_type", "limit_value", "actual_value", "timestamp"],
            "properties": {
                "user_id": {"bsonType": "string"},
                "strategy_id": {"bsonType": "string"},
                "breach_type": {"bsonType": "string"},
                "limit_value": {"bsonType": "double"},
                "actual_value": {"bsonType": "double"},
                "breach_percent": {"bsonType": "double"},
                "action_taken": {"enum": ["blocked", "warned", "cooldown", "halted"]},
                "is_resolved": {"bsonType": "bool"},
                "resolved_at": {"bsonType": "date"},
                "timestamp": {"bsonType": "date"}
            }
        }
    }
}


RISK_CONFIG_SCHEMA = {
    "collection": "risk_config",
    "indexes": [
        {"keys": [("user_id", 1)], "name": "user_idx"},
        {"keys": [("config_type", 1)], "name": "type_idx"}
    ],
    "validator": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["user_id", "config_type", "settings"],
            "properties": {
                "user_id": {"bsonType": "string"},
                "config_type": {
                    "enum": [
                        "global", "position_limits", "strategy_limits",
                        "throttle", "circuit_breaker", "alerting"
                    ]
                },
                "settings": {"bsonType": "object"},
                "is_active": {"bsonType": "bool"},
                "created_at": {"bsonType": "date"},
                "updated_at": {"bsonType": "date"}
            }
        }
    }
}


ALL_SCHEMAS = [
    RISK_POSITIONS_SCHEMA,
    RISK_METRICS_SCHEMA,
    RISK_LIMITS_SCHEMA,
    RISK_ALERTS_SCHEMA,
    RISK_SCENARIOS_SCHEMA,
    RISK_BREACHES_SCHEMA,
    RISK_CONFIG_SCHEMA
]


def get_schema_for_collection(collection_name: str) -> Dict:
    """Get schema definition for a specific collection."""
    for schema in ALL_SCHEMAS:
        if schema["collection"] == collection_name:
            return schema
    return {}


def create_indexes(db):
    """Create all indexes for risk collections."""
    for schema in ALL_SCHEMAS:
        collection = db[schema["collection"]]
        for index_def in schema["indexes"]:
            try:
                collection.create_index(index_def["keys"], name=index_def["name"])
                print(f"Created index {index_def['name']} on {schema['collection']}")
            except Exception as e:
                print(f"Index {index_def['name']} may already exist: {e}")


def setup_collections(db):
    """Setup all risk management collections with validation."""
    for schema in ALL_SCHEMAS:
        collection_name = schema["collection"]

        if collection_name not in db.list_collection_names():
            db.create_collection(
                collection_name,
                validator=schema.get("validator", {})
            )
            print(f"Created collection: {collection_name}")
        else:
            collection = db[collection_name]
            try:
                collection.update(
                    {},
                    {"$set": {"validator": schema.get("validator", {})}},
                    upsert=False
                )
                print(f"Updated validator for: {collection_name}")
            except Exception as e:
                print(f"Could not update validator: {e}")

    create_indexes(db)
    print("Risk management collections initialized")