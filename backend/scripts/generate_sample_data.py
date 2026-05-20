"""
Sample Data Generator
=====================
Generate realistic Indian stock market mock data for testing.
"""

import random
import uuid
from datetime import datetime, timedelta
from bson import ObjectId


INDIAN_STOCKS = {
    'RELIANCE': {'name': 'Reliance Industries', 'base_price': 2450, 'sector': 'Energy'},
    'TCS': {'name': 'Tata Consultancy Services', 'base_price': 3200, 'sector': 'IT'},
    'INFY': {'name': 'Infosys', 'base_price': 1400, 'sector': 'IT'},
    'HDFCBANK': {'name': 'HDFC Bank', 'base_price': 1650, 'sector': 'Banking'},
    'ICICIBANK': {'name': 'ICICI Bank', 'base_price': 950, 'sector': 'Banking'},
    'SBIN': {'name': 'State Bank of India', 'base_price': 580, 'sector': 'Banking'},
    'AXISBANK': {'name': 'Axis Bank', 'base_price': 950, 'sector': 'Banking'},
    'LT': {'name': 'Larsen & Toubro', 'base_price': 2800, 'sector': 'Infrastructure'},
    'WIPRO': {'name': 'Wipro', 'base_price': 420, 'sector': 'IT'},
    'HCLTECH': {'name': 'HCL Technologies', 'base_price': 1150, 'sector': 'IT'},
    'KOTAKBANK': {'name': 'Kotak Mahindra Bank', 'base_price': 1800, 'sector': 'Banking'},
    'MARUTI': {'name': 'Maruti Suzuki', 'base_price': 9500, 'sector': 'Auto'},
    'SUNPHARMA': {'name': 'Sun Pharma', 'base_price': 1050, 'sector': 'Pharma'},
    'TITAN': {'name': 'Titan', 'base_price': 2800, 'sector': 'Retail'},
    'BAJFINANCE': {'name': 'Bajaj Finance', 'base_price': 6500, 'sector': 'Finance'}
}


def generate_user(db, user_id='default_user'):
    """Generate sample user."""
    user = {
        'user_id': user_id,
        'name': 'Demo User',
        'email': 'demo@tradingplatform.com',
        'password_hash': '$2b$12$DummyHashForDemoPurposes',
        'twofa_enabled': False,
        'role': 'user',
        'is_active': True,
        'created_at': datetime.utcnow() - timedelta(days=90),
        'updated_at': datetime.utcnow()
    }
    result = db.users.insert_one(user)
    return str(result.inserted_id)


def generate_watchlists(db, user_id):
    """Generate sample watchlists."""
    watchlists = [
        {
            'user_id': user_id,
            'name': 'Nifty 50',
            'description': 'Top 50 NSE stocks',
            'symbols': ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK', 'SBIN', 'AXISBANK', 'LT', 'WIPRO', 'HCLTECH'],
            'is_default': True,
            'sort_order': 0,
            'created_at': datetime.utcnow() - timedelta(days=30),
            'updated_at': datetime.utcnow()
        },
        {
            'user_id': user_id,
            'name': 'IT Sector',
            'description': 'Indian IT companies',
            'symbols': ['TCS', 'INFY', 'WIPRO', 'HCLTECH'],
            'is_default': False,
            'sort_order': 1,
            'created_at': datetime.utcnow() - timedelta(days=20),
            'updated_at': datetime.utcnow()
        },
        {
            'user_id': user_id,
            'name': 'Banking',
            'description': 'Indian banking stocks',
            'symbols': ['HDFCBANK', 'ICICIBANK', 'SBIN', 'AXISBANK', 'KOTAKBANK'],
            'is_default': False,
            'sort_order': 2,
            'created_at': datetime.utcnow() - timedelta(days=15),
            'updated_at': datetime.utcnow()
        },
        {
            'user_id': user_id,
            'name': 'Favorites',
            'description': 'My favorite stocks',
            'symbols': ['RELIANCE', 'TCS', 'BAJFINANCE'],
            'is_default': False,
            'sort_order': 3,
            'created_at': datetime.utcnow() - timedelta(days=5),
            'updated_at': datetime.utcnow()
        }
    ]
    result = db.watchlists.insert_many(watchlists)
    return [str(id) for id in result.inserted_ids]


def generate_strategies(db, user_id):
    """Generate sample trading strategies."""
    strategies = [
        {
            'user_id': user_id,
            'strategy_name': 'RSI Momentum',
            'symbol': 'RELIANCE',
            'timeframe': '1h',
            'mode': 'paper',
            'broker': 'paper',
            'indicators': [
                {'id': 'rsi', 'name': 'RSI', 'params': {'period': 14}, 'enabled': True},
                {'id': 'sma_20', 'name': 'SMA', 'params': {'period': 20}, 'enabled': True}
            ],
            'entry_conditions': [
                {'indicator_name': 'RSI', 'operator': 'less_than', 'value': 30, 'logic': 'AND'}
            ],
            'exit_conditions': [
                {'indicator_name': 'RSI', 'operator': 'greater_than', 'value': 70, 'logic': 'OR'}
            ],
            'risk_settings': {
                'stop_loss_percent': 1.5,
                'take_profit_percent': 3.0,
                'trailing_stop_enabled': True,
                'position_size_percent': 10.0
            },
            'is_active': True,
            'created_at': datetime.utcnow() - timedelta(days=30),
            'updated_at': datetime.utcnow()
        },
        {
            'user_id': user_id,
            'strategy_name': 'MACD Crossover',
            'symbol': 'TCS',
            'timeframe': '15m',
            'mode': 'paper',
            'broker': 'paper',
            'indicators': [
                {'id': 'macd', 'name': 'MACD', 'params': {'fast': 12, 'slow': 26, 'signal': 9}, 'enabled': True},
                {'id': 'ema_50', 'name': 'EMA', 'params': {'period': 50}, 'enabled': True}
            ],
            'entry_conditions': [
                {'indicator_name': 'MACD', 'operator': 'crosses_above', 'value': 'signal', 'logic': 'AND'}
            ],
            'exit_conditions': [
                {'indicator_name': 'MACD', 'operator': 'crosses_below', 'value': 'signal', 'logic': 'OR'}
            ],
            'risk_settings': {
                'stop_loss_percent': 1.0,
                'take_profit_percent': 2.0,
                'trailing_stop_enabled': False,
                'position_size_percent': 15.0
            },
            'is_active': False,
            'created_at': datetime.utcnow() - timedelta(days=20),
            'updated_at': datetime.utcnow()
        }
    ]
    result = db.strategies.insert_many(strategies)
    return [str(id) for id in result.inserted_ids]


def generate_orders(db, user_id, count=20):
    """Generate sample orders."""
    orders = []
    statuses = ['OPEN', 'FILLED', 'CANCELLED', 'REJECTED']
    order_types = ['MARKET', 'LIMIT', 'SL', 'SL-M']
    transaction_types = ['BUY', 'SELL']

    for i in range(count):
        symbol = random.choice(list(INDIAN_STOCKS.keys()))
        stock = INDIAN_STOCKS[symbol]
        base_price = stock['base_price']
        price_variation = random.uniform(-0.05, 0.05)
        price = round(base_price * (1 + price_variation), 2)

        status = random.choices(statuses, weights=[30, 40, 20, 10])[0]
        quantity = random.choice([5, 10, 15, 20, 25, 50])
        filled_qty = quantity if status == 'FILLED' else (quantity // 2 if status == 'PARTIALLY_FILLED' else 0)

        created_at = datetime.utcnow() - timedelta(days=random.randint(1, 30))

        order = {
            'order_id': f"ORD{uuid.uuid4().hex[:12].upper()}",
            'user_id': user_id,
            'symbol': symbol,
            'exchange': 'NSE',
            'transaction_type': random.choice(transaction_types),
            'order_type': random.choice(order_types),
            'quantity': quantity,
            'filled_quantity': filled_qty,
            'price': price,
            'trigger_price': round(price * 0.995, 2) if random.random() > 0.5 else 0,
            'product_type': 'INTRADAY',
            'validity': 'DAY',
            'mode': 'paper',
            'status': status,
            'average_price': round(price * random.uniform(0.99, 1.01), 2) if status == 'FILLED' else 0,
            'pnl': round(random.uniform(-500, 800), 2) if status == 'FILLED' else 0,
            'created_at': created_at,
            'updated_at': created_at + timedelta(minutes=random.randint(1, 60))
        }

        if status == 'FILLED':
            order['filled_at'] = order['updated_at']
        elif status == 'CANCELLED':
            order['cancelled_at'] = order['updated_at']
            order['cancelled_reason'] = 'User cancelled'

        orders.append(order)

    result = db.orders.insert_many(orders)
    return [str(id) for id in result.inserted_ids]


def generate_trades(db, user_id, strategy_ids, count=30):
    """Generate sample trades."""
    trades = []
    sides = ['BUY', 'SELL']

    for i in range(count):
        symbol = random.choice(list(INDIAN_STOCKS.keys()))
        stock = INDIAN_STOCKS[symbol]
        base_price = stock['base_price']

        side = random.choice(sides)
        quantity = random.choice([10, 20, 30, 50])
        entry_price = round(base_price * random.uniform(0.98, 1.02), 2)

        is_profitable = random.random() > 0.4
        if is_profitable:
            exit_price = round(entry_price * random.uniform(1.01, 1.05), 2)
        else:
            exit_price = round(entry_price * random.uniform(0.95, 0.99), 2)

        if side == 'BUY':
            pnl = (exit_price - entry_price) * quantity
        else:
            pnl = (entry_price - exit_price) * quantity

        pnl_percent = (pnl / (entry_price * quantity)) * 100

        is_closed = random.random() > 0.3
        entry_time = datetime.utcnow() - timedelta(days=random.randint(1, 30))

        trade = {
            'user_id': user_id,
            'strategy_id': ObjectId(random.choice(strategy_ids)) if strategy_ids and random.random() > 0.3 else None,
            'symbol': symbol,
            'side': side,
            'entry_price': entry_price,
            'exit_price': exit_price if is_closed else None,
            'quantity': quantity,
            'entry_type': 'market',
            'exit_type': 'market' if is_closed else None,
            'pnl': round(pnl, 2),
            'pnl_percent': round(pnl_percent, 2),
            'commission': round(random.uniform(10, 50), 2),
            'mode': 'paper',
            'status': 'CLOSED' if is_closed else 'OPEN',
            'stop_loss': round(entry_price * 0.98, 2),
            'take_profit': round(entry_price * 1.02, 2),
            'entry_time': entry_time,
            'exit_time': entry_time + timedelta(hours=random.randint(1, 48)) if is_closed else None,
            'created_at': entry_time
        }

        trades.append(trade)

    result = db.trades.insert_many(trades)
    return [str(id) for id in result.inserted_ids]


def generate_ai_signals(db, user_id, count=15):
    """Generate sample AI signals."""
    signals = []
    signal_types = ['BUY', 'SELL', 'HOLD']
    timeframes = ['1m', '5m', '15m', '1h', '4h', '1d']

    for i in range(count):
        symbol = random.choice(list(INDIAN_STOCKS.keys()))
        stock = INDIAN_STOCKS[symbol]
        base_price = stock['base_price']

        signal_type = random.choice(signal_types)
        confidence = random.uniform(55, 95)

        entry_price = round(base_price * random.uniform(0.98, 1.02), 2)

        if signal_type == 'BUY':
            target = round(entry_price * random.uniform(1.02, 1.06), 2)
            stop_loss = round(entry_price * random.uniform(0.96, 0.98), 2)
        elif signal_type == 'SELL':
            target = round(entry_price * random.uniform(0.94, 0.98), 2)
            stop_loss = round(entry_price * random.uniform(1.02, 1.04), 2)
        else:
            target = entry_price
            stop_loss = round(entry_price * random.uniform(0.99, 1.01), 2)

        is_executed = random.random() > 0.7
        generated_at = datetime.utcnow() - timedelta(hours=random.randint(1, 72))

        signal = {
            'signal_type': signal_type,
            'symbol': symbol,
            'exchange': 'NSE',
            'timeframe': random.choice(timeframes),
            'confidence': round(confidence, 1),
            'entry_price': entry_price,
            'target_price': target,
            'stop_loss': stop_loss,
            'ai_reasoning': f'AI analysis: {signal_type} signal for {symbol}. RSI: {random.uniform(20, 80):.1f}, MACD: {random.uniform(-50, 50):.1f}',
            'indicators': {
                'rsi': round(random.uniform(20, 80), 1),
                'macd': round(random.uniform(-50, 50), 2),
                'sma_20': round(base_price * random.uniform(0.98, 1.02), 2),
                'sma_50': round(base_price * random.uniform(0.95, 1.05), 2)
            },
            'risk_reward_ratio': round(random.uniform(1.5, 3.0), 2),
            'strategy_name': 'AI Signal Generator',
            'is_executed': is_executed,
            'is_expired': generated_at + timedelta(hours=2) < datetime.utcnow(),
            'generated_at': generated_at,
            'expires_at': generated_at + timedelta(hours=1),
            'created_at': generated_at,
            'metadata': {}
        }

        signals.append(signal)

    result = db.ai_signals.insert_many(signals)
    return [str(id) for id in result.inserted_ids]


def generate_funds(db, user_id):
    """Generate sample funds."""
    funds = {
        'user_id': user_id,
        'balance': 100000.00,
        'available_balance': 85000.00,
        'used_margin': 15000.00,
        'pending_balance': 0,
        'realized_pnl': 12500.00,
        'unrealized_pnl': 2500.00,
        'total_deposited': 100000.00,
        'total_withdrawn': 0,
        'mode': 'paper',
        'currency': 'INR',
        'created_at': datetime.utcnow() - timedelta(days=90),
        'updated_at': datetime.utcnow()
    }
    result = db.funds.insert_one(funds)
    return str(result.inserted_id)


def generate_fund_transactions(db, user_id, count=10):
    """Generate sample fund transactions."""
    transactions = []
    types = ['deposit', 'withdrawal', 'realized_pnl']

    for i in range(count):
        txn_type = random.choice(types)
        amount = random.uniform(1000, 50000)

        if txn_type == 'deposit':
            balance_before = 50000 + (i * 5000)
            balance_after = balance_before + amount
        elif txn_type == 'withdrawal':
            balance_before = 80000 + (i * 5000)
            balance_after = balance_before - amount
        else:
            balance_before = 70000 + (i * 5000)
            balance_after = balance_before + amount

        txn = {
            'user_id': user_id,
            'transaction_type': txn_type,
            'amount': round(amount, 2),
            'balance_before': round(balance_before, 2),
            'balance_after': round(balance_after, 2),
            'mode': 'paper',
            'reference': f'REF{uuid.uuid4().hex[:8].upper()}',
            'notes': f'{txn_type.capitalize()} transaction',
            'status': 'completed',
            'created_at': datetime.utcnow() - timedelta(days=random.randint(1, 60))
        }
        transactions.append(txn)

    result = db.fund_transactions.insert_many(transactions)
    return [str(id) for id in result.inserted_ids]


def generate_notifications(db, user_id, count=20):
    """Generate sample notifications."""
    notifications = []
    types = ['trade', 'signal', 'system', 'alert']
    priorities = ['low', 'medium', 'high', 'critical']

    notifications_data = [
        {'type': 'trade', 'title': 'Order Executed', 'message': 'BUY order for RELIANCE executed at ₹2450'},
        {'type': 'trade', 'title': 'Order Filled', 'message': 'Your limit order for TCS was filled'},
        {'type': 'signal', 'title': 'New Buy Signal', 'message': 'AI detected BUY signal for INFY with 85% confidence'},
        {'type': 'alert', 'title': 'Stop Loss Hit', 'message': 'Stop loss triggered for HDFCBANK at ₹1620'},
        {'type': 'alert', 'title': 'Take Profit Hit', 'message': 'Target achieved for ICICIBANK, Profit: ₹450'},
        {'type': 'system', 'title': 'Market Closed', 'message': 'NSE market closed for the day'},
        {'type': 'system', 'title': 'Connection Restored', 'message': 'WebSocket connection re-established'},
        {'type': 'trade', 'title': 'Position Closed', 'message': 'Position in SBIN closed with profit of ₹280'},
        {'type': 'signal', 'title': 'Sell Signal', 'message': 'SELL signal generated for AXISBANK due to RSI overbought'},
        {'type': 'alert', 'title': 'Price Alert', 'message': 'RELIANCE crossed your target price of ₹2500'}
    ]

    for i in range(count):
        notif_data = random.choice(notifications_data)
        is_read = random.random() > 0.4

        notif = {
            'user_id': user_id,
            'type': notif_data['type'],
            'title': notif_data['title'],
            'message': notif_data['message'],
            'priority': random.choice(priorities),
            'is_read': is_read,
            'is_dismissed': False,
            'metadata': {'source': 'system'},
            'created_at': datetime.utcnow() - timedelta(hours=random.randint(1, 168)),
            'read_at': datetime.utcnow() - timedelta(hours=random.randint(0, 24)) if is_read else None
        }
        notifications.append(notif)

    result = db.notifications.insert_many(notifications)
    return [str(id) for id in result.inserted_ids]


def generate_positions(db, user_id, trade_ids):
    """Generate sample positions from open trades."""
    positions = []

    open_trades = list(db.trades.find({'user_id': user_id, 'status': 'OPEN'}))

    for trade in open_trades:
        stock = INDIAN_STOCKS.get(trade['symbol'], {'base_price': 1000})
        current_price = stock['base_price'] * random.uniform(0.98, 1.02)

        unrealized_pnl = (current_price - trade['entry_price']) * trade['quantity'] if trade['side'] == 'BUY' else (trade['entry_price'] - current_price) * trade['quantity']

        position = {
            'user_id': user_id,
            'strategy_id': trade.get('strategy_id'),
            'symbol': trade['symbol'],
            'side': trade['side'],
            'entry_price': trade['entry_price'],
            'quantity': trade['quantity'],
            'current_price': round(current_price, 2),
            'market_value': round(current_price * trade['quantity'], 2),
            'unrealized_pnl': round(unrealized_pnl, 2),
            'unrealized_pnl_percent': round((unrealized_pnl / (trade['entry_price'] * trade['quantity'])) * 100, 2),
            'stop_loss': trade.get('stop_loss'),
            'take_profit': trade.get('take_profit'),
            'mode': trade['mode'],
            'status': 'open',
            'opened_at': trade['entry_time'],
            'created_at': trade['created_at'],
            'updated_at': datetime.utcnow()
        }
        positions.append(position)

    if positions:
        result = db.positions.insert_many(positions)
        return [str(id) for id in result.inserted_ids]
    return []


def run(db, user_id='default_user'):
    """Run the complete sample data generation."""
    print("Generating sample data...")

    print("  - Creating user...")
    user_object_id = generate_user(db, user_id)

    print("  - Creating watchlists...")
    watchlist_ids = generate_watchlists(db, user_id)

    print("  - Creating strategies...")
    strategy_ids = generate_strategies(db, user_id)

    print("  - Creating orders...")
    order_ids = generate_orders(db, user_id, count=25)

    print("  - Creating trades...")
    trade_ids = generate_trades(db, user_id, strategy_ids, count=40)

    print("  - Creating AI signals...")
    signal_ids = generate_ai_signals(db, user_id, count=20)

    print("  - Creating funds...")
    fund_id = generate_funds(db, user_id)

    print("  - Creating fund transactions...")
    txn_ids = generate_fund_transactions(db, user_id, count=15)

    print("  - Creating notifications...")
    notif_ids = generate_notifications(db, user_id, count=25)

    print("  - Creating positions...")
    position_ids = generate_positions(db, user_id, trade_ids)

    print("\nSample data generation complete!")
    print(f"  User: {user_id}")
    print(f"  Watchlists: {len(watchlist_ids)}")
    print(f"  Strategies: {len(strategy_ids)}")
    print(f"  Orders: {len(order_ids)}")
    print(f"  Trades: {len(trade_ids)}")
    print(f"  AI Signals: {len(signal_ids)}")
    print(f"  Fund Transactions: {len(txn_ids)}")
    print(f"  Notifications: {len(notif_ids)}")
    print(f"  Positions: {len(position_ids)}")

    return {
        'user_id': user_id,
        'watchlists': len(watchlist_ids),
        'strategies': len(strategy_ids),
        'orders': len(order_ids),
        'trades': len(trade_ids),
        'signals': len(signal_ids),
        'notifications': len(notif_ids),
        'positions': len(position_ids)
    }


if __name__ == '__main__':
    import os
    import sys
    from dotenv import load_dotenv
    from pymongo import MongoClient

    # Add backend directory to sys.path to import build_mongo_uri
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from app.config import build_mongo_uri

    load_dotenv()

    mongo_uri = build_mongo_uri()
    db_name = os.getenv('MONGO_DB_NAME', 'trading_platform')

    print(f"Connecting to MongoDB...")

    client = MongoClient(mongo_uri)
    db = client[db_name]

    result = run(db, user_id='demo_user')

    print("\nDone!")