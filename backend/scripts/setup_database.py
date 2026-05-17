"""
Database Setup Script
=====================
Create indexes and validation rules for MongoDB collections.
"""

import logging
from datetime import datetime
from pymongo import ASCENDING, DESCENDING

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('database_setup')


INDEXES = {
    'users': [
        {'keys': [('email', ASCENDING)], 'name': 'email_idx', 'unique': True},
        {'keys': [('mobile', ASCENDING)], 'name': 'mobile_idx'},
        {'keys': [('created_at', DESCENDING)], 'name': 'created_at_idx'}
    ],

    'watchlists': [
        {'keys': [('user_id', ASCENDING), ('created_at', DESCENDING)], 'name': 'user_watchlists_idx'},
        {'keys': [('user_id', ASCENDING), ('is_default', ASCENDING)], 'name': 'default_watchlist_idx'},
        {'keys': [('user_id', ASCENDING), ('name', ASCENDING)], 'name': 'unique_name_idx', 'unique': True}
    ],

    'strategies': [
        {'keys': [('user_id', ASCENDING), ('_id', ASCENDING)], 'name': 'user_strategies_idx'},
        {'keys': [('is_active', ASCENDING)], 'name': 'active_strategies_idx'},
        {'keys': [('symbol', ASCENDING), ('mode', ASCENDING)], 'name': 'symbol_mode_idx'},
        {'keys': [('broker', ASCENDING)], 'name': 'broker_idx'}
    ],

    'orders': [
        {'keys': [('user_id', ASCENDING), ('created_at', DESCENDING)], 'name': 'user_orders_idx'},
        {'keys': [('order_id', ASCENDING)], 'name': 'order_id_idx', 'unique': True},
        {'keys': [('symbol', ASCENDING), ('status', ASCENDING)], 'name': 'symbol_status_idx'},
        {'keys': [('status', ASCENDING), ('created_at', DESCENDING)], 'name': 'status_orders_idx'},
        {'keys': [('strategy_id', ASCENDING)], 'name': 'strategy_orders_idx'},
        {'keys': [('mode', ASCENDING), ('created_at', DESCENDING)], 'name': 'mode_orders_idx'}
    ],

    'trades': [
        {'keys': [('user_id', ASCENDING), ('created_at', DESCENDING)], 'name': 'user_trades_idx'},
        {'keys': [('strategy_id', ASCENDING), ('created_at', DESCENDING)], 'name': 'strategy_trades_idx'},
        {'keys': [('symbol', ASCENDING), ('mode', ASCENDING)], 'name': 'symbol_trades_idx'},
        {'keys': [('status', ASCENDING)], 'name': 'status_trades_idx'},
        {'keys': [('entry_time', ASCENDING)], 'name': 'entry_time_idx'},
        {'keys': [('mode', ASCENDING), ('created_at', DESCENDING)], 'name': 'mode_trades_idx'},
        {'keys': [('signal_id', ASCENDING)], 'name': 'signal_trades_idx'}
    ],

    'positions': [
        {'keys': [('user_id', ASCENDING), ('status', ASCENDING)], 'name': 'open_positions_idx'},
        {'keys': [('strategy_id', ASCENDING)], 'name': 'strategy_positions_idx'},
        {'keys': [('symbol', ASCENDING), ('mode', ASCENDING)], 'name': 'symbol_positions_idx'},
        {'keys': [('opened_at', DESCENDING)], 'name': 'opened_at_idx'},
        {'keys': [('trade_id', ASCENDING)], 'name': 'trade_position_idx'}
    ],

    'ai_signals': [
        {'keys': [('symbol', ASCENDING), ('generated_at', DESCENDING)], 'name': 'symbol_signals_idx'},
        {'keys': [('signal_type', ASCENDING), ('generated_at', DESCENDING)], 'name': 'type_signals_idx'},
        {'keys': [('confidence', DESCENDING)], 'name': 'confidence_idx'},
        {'keys': [('is_executed', ASCENDING), ('generated_at', DESCENDING)], 'name': 'unexecuted_signals_idx'},
        {'keys': [('generated_at', DESCENDING)], 'name': 'generated_at_idx'}
    ],

    'funds': [
        {'keys': [('user_id', ASCENDING)], 'name': 'user_funds_idx', 'unique': True},
        {'keys': [('mode', ASCENDING)], 'name': 'mode_funds_idx'}
    ],

    'fund_transactions': [
        {'keys': [('user_id', ASCENDING), ('created_at', DESCENDING)], 'name': 'user_transactions_idx'},
        {'keys': [('transaction_type', ASCENDING)], 'name': 'transaction_type_idx'},
        {'keys': [('mode', ASCENDING), ('created_at', DESCENDING)], 'name': 'mode_transactions_idx'}
    ],

    'notifications': [
        {'keys': [('user_id', ASCENDING), ('created_at', DESCENDING)], 'name': 'user_notifications_idx'},
        {'keys': [('is_read', ASCENDING), ('created_at', DESCENDING)], 'name': 'unread_notifications_idx'},
        {'keys': [('type', ASCENDING)], 'name': 'type_notifications_idx'},
        {'keys': [('priority', ASCENDING)], 'name': 'priority_notifications_idx'}
    ],

    'activity_logs': [
        {'keys': [('user_id', ASCENDING), ('created_at', DESCENDING)], 'name': 'user_activity_idx'},
        {'keys': [('activity_type', ASCENDING), ('created_at', DESCENDING)], 'name': 'activity_type_idx'}
    ],

    'websocket_connections': [
        {'keys': [('session_id', ASCENDING)], 'name': 'session_idx', 'unique': True},
        {'keys': [('user_id', ASCENDING), ('is_active', ASCENDING)], 'name': 'active_connections_idx'},
        {'keys': [('connected_at', DESCENDING)], 'name': 'connected_at_idx'}
    ],

    'candles': [
        {'keys': [('symbol', ASCENDING), ('timeframe', ASCENDING), ('timestamp', DESCENDING)], 'name': 'candle_lookup_idx'},
        {'keys': [('timestamp', ASCENDING)], 'name': 'timestamp_idx'}
    ],

    'brokers': [
        {'keys': [('user_id', ASCENDING), ('broker_name', ASCENDING)], 'name': 'user_brokers_idx'},
        {'keys': [('is_connected', ASCENDING)], 'name': 'connected_brokers_idx'}
    ],

    'backtests': [
        {'keys': [('user_id', ASCENDING), ('created_at', DESCENDING)], 'name': 'user_backtests_idx'},
        {'keys': [('strategy_id', ASCENDING)], 'name': 'strategy_backtests_idx'},
        {'keys': [('status', ASCENDING)], 'name': 'status_backtests_idx'}
    ],

    'logs': [
        {'keys': [('level', ASCENDING), ('created_at', DESCENDING)], 'name': 'level_logs_idx'},
        {'keys': [('category', ASCENDING), ('created_at', DESCENDING)], 'name': 'category_logs_idx'},
        {'keys': [('user_id', ASCENDING), ('created_at', DESCENDING)], 'name': 'user_logs_idx'}
    ],

    'settings': [
        {'keys': [('key', ASCENDING)], 'name': 'key_idx', 'unique': True},
        {'keys': [('category', ASCENDING)], 'name': 'category_idx'}
    ],

    'indicator_values': [
        {'keys': [('symbol', ASCENDING), ('timeframe', ASCENDING), ('timestamp', DESCENDING)], 'name': 'indicator_lookup_idx'},
        {'keys': [('timestamp', ASCENDING)], 'name': 'timestamp_idx'}
    ],

    'paper_portfolios': [
        {'keys': [('user_id', ASCENDING)], 'name': 'user_portfolio_idx', 'unique': True},
    ],

    'paper_trades': [
        {'keys': [('user_id', ASCENDING), ('executed_at', DESCENDING)], 'name': 'user_paper_trades_idx'},
        {'keys': [('strategy_id', ASCENDING)], 'name': 'strategy_paper_trades_idx'},
        {'keys': [('symbol', ASCENDING), ('status', ASCENDING)], 'name': 'symbol_status_paper_idx'},
    ],

    'paper_positions': [
        {'keys': [('user_id', ASCENDING), ('status', ASCENDING)], 'name': 'user_paper_positions_idx'},
        {'keys': [('status', ASCENDING)], 'name': 'status_paper_positions_idx'},
    ],

    'strategy_signals': [
        {'keys': [('user_id', ASCENDING), ('timestamp', DESCENDING)], 'name': 'user_signals_idx'},
        {'keys': [('strategy_id', ASCENDING), ('timestamp', DESCENDING)], 'name': 'strategy_signals_idx'},
        {'keys': [('symbol', ASCENDING)], 'name': 'symbol_signals_idx'},
    ],

    'strategy_executions': [
        {'keys': [('user_id', ASCENDING), ('created_at', DESCENDING)], 'name': 'user_executions_idx'},
        {'keys': [('strategy_id', ASCENDING)], 'name': 'strategy_executions_idx'},
    ],

    'backtest_results': [
        {'keys': [('user_id', ASCENDING), ('created_at', DESCENDING)], 'name': 'user_backtest_results_idx'},
        {'keys': [('strategy_id', ASCENDING)], 'name': 'strategy_backtest_results_idx'},
    ],

    'risk_logs': [
        {'keys': [('user_id', ASCENDING), ('timestamp', DESCENDING)], 'name': 'user_risk_logs_idx'},
        {'keys': [('event_type', ASCENDING)], 'name': 'event_type_risk_logs_idx'},
    ]
}


TTL_INDEXES = {
    'candles': {'field': 'created_at', 'expire_after_seconds': 2592000},
    'logs': {'field': 'created_at', 'expire_after_seconds': 7776000},
    'indicator_values': {'field': 'created_at', 'expire_after_seconds': 3600},
    'activity_logs': {'field': 'created_at', 'expire_after_seconds': 2592000}
}


def create_indexes(db):
    """Create all indexes for collections."""
    logger.info("Creating indexes...")

    for collection_name, indexes in INDEXES.items():
        if collection_name not in db.list_collection_names():
            logger.info(f"  Creating collection: {collection_name}")
            db.create_collection(collection_name)

        collection = db[collection_name]

        for idx in indexes:
            try:
                existing = collection.index_information()
                if idx['name'] not in existing:
                    result = collection.create_index(
                        idx['keys'],
                        name=idx['name'],
                        unique=idx.get('unique', False)
                    )
                    logger.info(f"  Created index: {idx['name']} on {collection_name}")
                else:
                    logger.info(f"  Index already exists: {idx['name']} on {collection_name}")
            except Exception as e:
                logger.error(f"  Error creating index {idx['name']}: {e}")

    logger.info("Index creation complete!")


def create_ttl_indexes(db):
    """Create TTL (Time-To-Live) indexes for auto-cleanup."""
    logger.info("\nCreating TTL indexes...")

    for collection_name, ttl_config in TTL_INDEXES.items():
        collection = db[collection_name]
        field = ttl_config['field']
        expire_after = ttl_config['expire_after_seconds']

        try:
            result = collection.create_index(
                [(field, ASCENDING)],
                expireAfterSeconds=expire_after,
                name=f'{field}_ttl_idx'
            )
            logger.info(f"  Created TTL index on {collection_name}.{field}")
        except Exception as e:
            logger.warning(f"  TTL index for {collection_name}: {e}")

    logger.info("TTL index creation complete!")


def validate_collections(db):
    """Validate that all required collections exist."""
    logger.info("\nValidating collections...")

    required_collections = [
        'users', 'watchlists', 'strategies', 'orders', 'trades',
        'positions', 'ai_signals', 'funds', 'fund_transactions',
        'notifications', 'activity_logs', 'websocket_connections',
        'candles', 'brokers', 'backtests', 'logs', 'settings',
        'paper_portfolios', 'paper_trades', 'paper_positions',
        'strategy_signals', 'strategy_executions', 'backtest_results',
        'risk_logs'
    ]

    existing = db.list_collection_names()
    missing = [c for c in required_collections if c not in existing]

    if missing:
        logger.warning(f"  Missing collections: {missing}")
        for coll in missing:
            db.create_collection(coll)
            logger.info(f"  Created collection: {coll}")
    else:
        logger.info("  All required collections exist!")

    logger.info(f"  Total collections: {len(existing)}")


def get_collection_stats(db):
    """Get statistics for all collections."""
    logger.info("\nCollection Statistics:")

    for collection_name in db.list_collection_names():
        try:
            count = db[collection_name].count_documents({})
            logger.info(f"  {collection_name}: {count} documents")
        except Exception as e:
            logger.warning(f"  {collection_name}: Error - {e}")


def run(db):
    """Run complete database setup."""
    logger.info("=" * 50)
    logger.info("Starting Database Setup")
    logger.info("=" * 50)

    validate_collections(db)
    create_indexes(db)
    create_ttl_indexes(db)
    get_collection_stats(db)

    logger.info("=" * 50)
    logger.info("Database Setup Complete!")
    logger.info("=" * 50)


if __name__ == '__main__':
    import os
    from dotenv import load_dotenv
    from pymongo import MongoClient

    load_dotenv()

    mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/trading_db')
    db_name = os.getenv('MONGO_DB_NAME', 'trading_db')

    print(f"Connecting to: {mongo_uri.replace(os.getenv('MONGO_PASSWORD', 'password'), '****')}")

    client = MongoClient(mongo_uri)
    db = client[db_name]

    run(db)