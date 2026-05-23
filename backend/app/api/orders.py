"""
Orders API
==========
Order management endpoints.
"""

import logging
import uuid
from datetime import datetime
from bson import ObjectId
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required

from app.database.connection import get_db
from app.utils.auth import get_current_user_id

logger = logging.getLogger('trading_app')

bp = Blueprint('orders', __name__)


@bp.route('', methods=['GET'])
@jwt_required(optional=True)
def list_orders():
    """
    List orders with filtering options.

    Query Parameters:
        - status: OPEN, FILLED, PARTIALLY_FILLED, CANCELLED, REJECTED
        - order_type: MARKET, LIMIT, SL, SLM
        - transaction_type: BUY, SELL
        - symbol: filter by symbol
        - mode: paper, live
        - limit: number of results (default 50)
        - skip: number to skip (default 0)

    Returns:
        List of orders
    """
    user_id = get_current_user_id()
    status = request.args.get('status')
    order_type = request.args.get('order_type')
    transaction_type = request.args.get('transaction_type')
    symbol = request.args.get('symbol')
    mode = request.args.get('mode', 'paper')
    limit = int(request.args.get('limit', 50))
    skip = int(request.args.get('skip', 0))

    query = {'user_id': user_id}
    if status:
        query['status'] = status.upper()
    if order_type:
        query['order_type'] = order_type.upper()
    if transaction_type:
        query['transaction_type'] = transaction_type.upper()
    if symbol:
        query['symbol'] = symbol.upper()
    if mode:
        query['mode'] = mode

    db = get_db()
    if db is None:
        return jsonify({'error': 'database_error', 'message': 'Database not available'}), 500

    orders = list(db.orders.find(query).sort('created_at', -1).skip(skip).limit(limit))
    total = db.orders.count_documents(query)

    for order in orders:
        order['_id'] = str(order['_id'])
        if 'created_at' in order:
            order['created_at'] = order['created_at'].isoformat()
        if 'updated_at' in order:
            order['updated_at'] = order['updated_at'].isoformat()
        if 'filled_at' in order:
            order['filled_at'] = order['filled_at'].isoformat()

    return jsonify({
        'orders': orders,
        'total': total,
        'limit': limit,
        'skip': skip
    }), 200


@bp.route('', methods=['POST'])
def create_order():
    """
    Create a new order.

    Request Body:
        {
            "symbol": "RELIANCE",
            "exchange": "NSE",
            "transaction_type": "BUY",
            "order_type": "LIMIT",
            "quantity": 10,
            "price": 2450.00,
            "trigger_price": 2448.00,
            "product_type": "INTRADAY",
            "validity": "DAY",
            "mode": "paper",
            "disclosed_quantity": 0
        }

    Returns:
        Created order details
    """
    user_id = get_current_user_id()
    data = request.get_json() or {}

    required_fields = ['symbol', 'transaction_type', 'quantity']
    for field in required_fields:
        if not data.get(field):
            return jsonify({
                'error': 'validation_error',
                'message': f'{field} is required'
            }), 400

    db = get_db()
    if db is None:
        return jsonify({'error': 'database_error', 'message': 'Database not available'}), 500

    order_id = f"ORD{uuid.uuid4().hex[:12].upper()}"

    order = {
        'order_id': order_id,
        'user_id': user_id,
        'symbol': data['symbol'].upper(),
        'exchange': data.get('exchange', 'NSE'),
        'transaction_type': data['transaction_type'].upper(),
        'order_type': data.get('order_type', 'MARKET').upper(),
        'quantity': int(data['quantity']),
        'filled_quantity': 0,
        'price': float(data.get('price', 0)),
        'trigger_price': float(data.get('trigger_price', 0)),
        'product_type': data.get('product_type', 'INTRADAY'),
        'validity': data.get('validity', 'DAY'),
        'mode': data.get('mode', 'paper'),
        'status': 'OPEN',
        'average_price': 0,
        'pnl': 0,
        'disclosed_quantity': data.get('disclosed_quantity', 0),
        'order_tag': data.get('order_tag', ''),
        'strategy_id': data.get('strategy_id'),
        'comments': data.get('comments', ''),
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow(),
        'filled_at': None,
        'cancelled_at': None,
        'rejected_reason': None
    }

    if order['order_type'] in ['SL', 'SL-M'] and not order['trigger_price']:
        return jsonify({
            'error': 'validation_error',
            'message': 'Trigger price is required for SL/SL-M orders'
        }), 400

    result = db.orders.insert_one(order)
    order['_id'] = str(result.inserted_id)
    order['created_at'] = order['created_at'].isoformat()

    logger.info(f"Order created: {order_id} - {order['transaction_type']} {order['quantity']} {order['symbol']}")

    return jsonify(order), 201


@bp.route('/<order_id>', methods=['GET'])
def get_order(order_id):
    """
    Get a specific order.

    Returns:
        Order details
    """
    user_id = get_current_user_id()

    db = get_db()
    if db is None:
        return jsonify({'error': 'database_error', 'message': 'Database not available'}), 500

    order = db.orders.find_one({
        'order_id': order_id,
        'user_id': user_id
    })

    if not order:
        try:
            order = db.orders.find_one({
                '_id': ObjectId(order_id),
                'user_id': user_id
            })
        except Exception:
            pass

    if not order:
        return jsonify({
            'error': 'not_found',
            'message': 'Order not found'
        }), 404

    order['_id'] = str(order['_id'])
    if 'created_at' in order:
        order['created_at'] = order['created_at'].isoformat()
    if 'updated_at' in order:
        order['updated_at'] = order['updated_at'].isoformat()

    return jsonify(order), 200


@bp.route('/<order_id>/cancel', methods=['POST'])
def cancel_order(order_id):
    """
    Cancel an open order.

    Request Body:
        {
            "reason": "User requested cancellation"
        }

    Returns:
        Cancelled order details
    """
    user_id = get_current_user_id()

    db = get_db()
    if db is None:
        return jsonify({'error': 'database_error', 'message': 'Database not available'}), 500

    order = db.orders.find_one({
        'order_id': order_id,
        'user_id': user_id
    })

    if not order:
        try:
            order = db.orders.find_one({
                '_id': ObjectId(order_id),
                'user_id': user_id
            })
        except Exception:
            pass

    if not order:
        return jsonify({
            'error': 'not_found',
            'message': 'Order not found'
        }), 404

    if order['status'] not in ['OPEN', 'PARTIALLY_FILLED']:
        return jsonify({
            'error': 'conflict',
            'message': f'Cannot cancel order with status {order["status"]}'
        }), 409

    data = request.get_json() or {}

    db.orders.update_one(
        {'_id': order['_id']},
        {'$set': {
            'status': 'CANCELLED',
            'cancelled_at': datetime.utcnow(),
            'cancelled_reason': data.get('reason', 'User requested'),
            'updated_at': datetime.utcnow()
        }}
    )

    logger.info(f"Order cancelled: {order_id}")

    return jsonify({
        'message': 'Order cancelled successfully',
        'order_id': order_id
    }), 200


@bp.route('/<order_id>/modify', methods=['PUT'])
def modify_order(order_id):
    """
    Modify an open order.

    Request Body:
        {
            "price": 2450.00,
            "trigger_price": 2448.00,
            "quantity": 15,
            "validity": "GTC"
        }

    Returns:
        Modified order details
    """
    user_id = get_current_user_id()
    data = request.get_json() or {}

    db = get_db()
    if db is None:
        return jsonify({'error': 'database_error', 'message': 'Database not available'}), 500

    order = db.orders.find_one({
        'order_id': order_id,
        'user_id': user_id
    })

    if not order:
        try:
            order = db.orders.find_one({
                '_id': ObjectId(order_id),
                'user_id': user_id
            })
        except Exception:
            pass

    if not order:
        return jsonify({
            'error': 'not_found',
            'message': 'Order not found'
        }), 404

    if order['status'] != 'OPEN':
        return jsonify({
            'error': 'conflict',
            'message': f'Cannot modify order with status {order["status"]}'
        }), 409

    update_data = {'updated_at': datetime.utcnow()}

    if 'price' in data:
        update_data['price'] = float(data['price'])
    if 'trigger_price' in data:
        update_data['trigger_price'] = float(data['trigger_price'])
    if 'quantity' in data:
        update_data['quantity'] = int(data['quantity'])
    if 'validity' in data:
        update_data['validity'] = data['validity']

    db.orders.update_one(
        {'_id': order['_id']},
        {'$set': update_data}
    )

    logger.info(f"Order modified: {order_id}")

    return jsonify({
        'message': 'Order modified successfully'
    }), 200


@bp.route('/<order_id>/execute', methods=['POST'])
def execute_order(order_id):
    """
    Execute/fill an order (for paper trading).

    Request Body:
        {
            "filled_price": 2450.00,
            "filled_quantity": 10
        }

    Returns:
        Executed order details
    """
    user_id = get_current_user_id()
    data = request.get_json() or {}

    db = get_db()
    if db is None:
        return jsonify({'error': 'database_error', 'message': 'Database not available'}), 500

    order = db.orders.find_one({
        'order_id': order_id,
        'user_id': user_id
    })

    if not order:
        try:
            order = db.orders.find_one({
                '_id': ObjectId(order_id),
                'user_id': user_id
            })
        except Exception:
            pass

    if not order:
        return jsonify({
            'error': 'not_found',
            'message': 'Order not found'
        }), 404

    if order['status'] == 'FILLED':
        return jsonify({
            'error': 'conflict',
            'message': 'Order already filled'
        }), 409

    filled_price = data.get('filled_price', order.get('price', 0))
    filled_quantity = data.get('filled_quantity', order['quantity'] - order.get('filled_quantity', 0))

    total_value = (order.get('average_price', 0) * order.get('filled_quantity', 0)) + (filled_price * filled_quantity)
    new_filled = order.get('filled_quantity', 0) + filled_quantity
    avg_price = total_value / new_filled if new_filled > 0 else filled_price

    new_status = 'FILLED' if new_filled >= order['quantity'] else 'PARTIALLY_FILLED'

    db.orders.update_one(
        {'_id': order['_id']},
        {'$set': {
            'status': new_status,
            'filled_quantity': new_filled,
            'average_price': avg_price,
            'filled_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }}
    )

    logger.info(f"Order executed: {order_id} - {filled_quantity} @ {filled_price}")

    return jsonify({
        'message': 'Order executed',
        'order_id': order_id,
        'status': new_status,
        'filled_quantity': new_filled,
        'average_price': avg_price
    }), 200


@bp.route('/cancel-all', methods=['POST'])
def cancel_all_orders():
    """
    Cancel all open orders for a symbol or all.

    Request Body:
        {
            "symbol": "RELIANCE"
        }

    Returns:
        Number of cancelled orders
    """
    user_id = get_current_user_id()
    data = request.get_json() or {}

    db = get_db()
    if db is None:
        return jsonify({'error': 'database_error', 'message': 'Database not available'}), 500

    query = {
        'user_id': user_id,
        'status': 'OPEN'
    }

    if data.get('symbol'):
        query['symbol'] = data['symbol'].upper()

    result = db.orders.update_many(
        query,
        {'$set': {
            'status': 'CANCELLED',
            'cancelled_at': datetime.utcnow(),
            'cancelled_reason': 'Bulk cancellation',
            'updated_at': datetime.utcnow()
        }}
    )

    logger.info(f"Cancelled {result.modified_count} orders")

    return jsonify({
        'message': 'Orders cancelled',
        'count': result.modified_count
    }), 200


@bp.route('/stats', methods=['GET'])
def get_order_stats():
    """
    Get order statistics.

    Query Parameters:
        - mode: paper, live
        - symbol: filter by symbol
        - period: today, week, month, all

    Returns:
        Order statistics
    """
    user_id = get_current_user_id()
    mode = request.args.get('mode', 'paper')
    symbol = request.args.get('symbol')
    period = request.args.get('period', 'all')

    db = get_db()
    if db is None:
        return jsonify({'error': 'database_error', 'message': 'Database not available'}), 500

    query = {'user_id': user_id, 'mode': mode}

    if symbol:
        query['symbol'] = symbol.upper()

    if period != 'all':
        from datetime import timedelta
        start_date = datetime.utcnow()
        if period == 'today':
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == 'week':
            start_date -= timedelta(days=7)
        elif period == 'month':
            start_date -= timedelta(days=30)
        query['created_at'] = {'$gte': start_date}

    orders = list(db.orders.find(query))

    total_orders = len(orders)
    open_orders = len([o for o in orders if o['status'] in ['OPEN', 'PARTIALLY_FILLED']])
    filled_orders = len([o for o in orders if o['status'] == 'FILLED'])
    cancelled_orders = len([o for o in orders if o['status'] == 'CANCELLED'])
    rejected_orders = len([o for o in orders if o['status'] == 'REJECTED'])

    buy_orders = len([o for o in orders if o['transaction_type'] == 'BUY'])
    sell_orders = len([o for o in orders if o['transaction_type'] == 'SELL'])

    return jsonify({
        'total_orders': total_orders,
        'open_orders': open_orders,
        'filled_orders': filled_orders,
        'cancelled_orders': cancelled_orders,
        'rejected_orders': rejected_orders,
        'buy_orders': buy_orders,
        'sell_orders': sell_orders,
        'fill_rate': round((filled_orders / total_orders * 100) if total_orders > 0 else 0, 2),
        'period': period
    }), 200