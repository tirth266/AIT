"""
Funds API
=========
Trading funds and balance management endpoints.
"""

import logging
from datetime import datetime
from bson import ObjectId
from flask import Blueprint, request, jsonify

from app.database.connection import get_db

logger = logging.getLogger('trading_app')

bp = Blueprint('funds', __name__)


@bp.route('', methods=['GET'])
def get_funds():
    """
    Get user's funds and balance information.
    """
    try:
        user_id = "default_user"
        logger.info(f"[Funds] Fetching funds for {user_id}")

        db = get_db()
        if not db:
            logger.error("[Funds] Database connection missing")
            return jsonify({'error': 'database_error', 'message': 'Database not available'}), 500

        funds = db.funds.find_one({'user_id': user_id})

        if not funds:
            initial_balance = 100000.0
            funds = {
                'user_id': user_id,
                'balance': initial_balance,
                'available_balance': initial_balance,
                'used_margin': 0,
                'pending_balance': 0,
                'realized_pnl': 0,
                'unrealized_pnl': 0,
                'total_deposited': initial_balance,
                'total_withdrawn': 0,
                'mode': 'paper',
                'currency': 'INR',
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            db.funds.insert_one(funds)
            funds['_id'] = str(funds['_id'])
        else:
            funds['_id'] = str(funds['_id'])
            if 'created_at' in funds:
                funds['created_at'] = funds['created_at'].isoformat() if hasattr(funds['created_at'], 'isoformat') else str(funds['created_at'])
            if 'updated_at' in funds:
                funds['updated_at'] = funds['updated_at'].isoformat() if hasattr(funds['updated_at'], 'isoformat') else str(funds['updated_at'])

        return jsonify({
            "success": True,
            "data": funds
        }), 200

    except Exception as e:
        import traceback
        logger.error(f"[Funds] Critical failure: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': 'internal_error',
            'message': str(e)
        }), 500


@bp.route('', methods=['POST'])
def add_funds():
    """
    Add funds to trading account.

    Request Body:
        {
            "amount": 10000,
            "mode": "paper" | "live",
            "transaction_type": "deposit",
            "reference": "UTR123456",
            "notes": "Added funds"
        }

    Returns:
        Updated fund details
    """
    user_id = "default_user"
    data = request.get_json() or {}

    amount = data.get('amount')
    if not amount or float(amount) <= 0:
        return jsonify({
            'error': 'validation_error',
            'message': 'Valid amount is required'
        }), 400

    db = get_db()
    if not db:
        return jsonify({'error': 'database_error', 'message': 'Database not available'}), 500

    funds = db.funds.find_one({'user_id': user_id})
    if not funds:
        funds = {
            'user_id': user_id,
            'balance': 0,
            'available_balance': 0,
            'used_margin': 0,
            'mode': data.get('mode', 'paper'),
            'currency': 'INR',
            'total_deposited': 0,
            'total_withdrawn': 0,
            'created_at': datetime.utcnow()
        }

    amount = float(amount)
    new_balance = funds.get('balance', 0) + amount
    new_available = funds.get('available_balance', 0) + amount

    transaction = {
        'user_id': user_id,
        'transaction_type': data.get('transaction_type', 'deposit'),
        'amount': amount,
        'balance_before': funds.get('balance', 0),
        'balance_after': new_balance,
        'mode': data.get('mode', 'paper'),
        'reference': data.get('reference'),
        'notes': data.get('notes', ''),
        'status': 'completed',
        'created_at': datetime.utcnow()
    }

    db.fund_transactions.insert_one(transaction)

    db.funds.update_one(
        {'user_id': user_id},
        {'$set': {
            'balance': new_balance,
            'available_balance': new_available,
            'total_deposited': funds.get('total_deposited', 0) + amount,
            'updated_at': datetime.utcnow()
        }},
        upsert=True
    )

    logger.info(f"Funds added: {amount} for user {user_id}")

    return jsonify({
        'message': 'Funds added successfully',
        'balance': new_balance,
        'transaction_id': str(transaction['_id'])
    }), 201


@bp.route('/withdraw', methods=['POST'])
def withdraw_funds():
    """
    Withdraw funds from trading account.

    Request Body:
        {
            "amount": 5000,
            "mode": "paper",
            "reference": "Bank transfer",
            "notes": "Withdrawal request"
        }

    Returns:
        Updated fund details
    """
    user_id = "default_user"
    data = request.get_json() or {}

    amount = data.get('amount')
    if not amount or float(amount) <= 0:
        return jsonify({
            'error': 'validation_error',
            'message': 'Valid amount is required'
        }), 400

    db = get_db()
    if not db:
        return jsonify({'error': 'database_error', 'message': 'Database not available'}), 500

    funds = db.funds.find_one({'user_id': user_id})
    if not funds:
        return jsonify({
            'error': 'not_found',
            'message': 'Funds not found'
        }), 404

    amount = float(amount)
    available = funds.get('available_balance', 0)

    if amount > available:
        return jsonify({
            'error': 'insufficient_funds',
            'message': 'Insufficient funds',
            'available': available
        }), 400

    new_balance = funds.get('balance', 0) - amount
    new_available = available - amount

    transaction = {
        'user_id': user_id,
        'transaction_type': 'withdrawal',
        'amount': amount,
        'balance_before': funds.get('balance', 0),
        'balance_after': new_balance,
        'mode': data.get('mode', 'paper'),
        'reference': data.get('reference'),
        'notes': data.get('notes', ''),
        'status': 'completed',
        'created_at': datetime.utcnow()
    }

    db.fund_transactions.insert_one(transaction)

    db.funds.update_one(
        {'user_id': user_id},
        {'$set': {
            'balance': new_balance,
            'available_balance': new_available,
            'total_withdrawn': funds.get('total_withdrawn', 0) + amount,
            'updated_at': datetime.utcnow()
        }}
    )

    logger.info(f"Funds withdrawn: {amount} for user {user_id}")

    return jsonify({
        'message': 'Funds withdrawn successfully',
        'balance': new_balance,
        'transaction_id': str(transaction['_id'])
    }), 200


@bp.route('/transactions', methods=['GET'])
def list_transactions():
    """
    List fund transactions.

    Query Parameters:
        - transaction_type: deposit, withdrawal, pnl
        - mode: paper, live
        - start_date: filter start date
        - end_date: filter end date
        - limit: number of results (default 50)
        - skip: number to skip (default 0)

    Returns:
        List of transactions
    """
    user_id = "default_user"
    transaction_type = request.args.get('transaction_type')
    mode = request.args.get('mode')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    limit = int(request.args.get('limit', 50))
    skip = int(request.args.get('skip', 0))

    query = {'user_id': user_id}
    if transaction_type:
        query['transaction_type'] = transaction_type
    if mode:
        query['mode'] = mode
    if start_date or end_date:
        query['created_at'] = {}
        if start_date:
            query['created_at']['$gte'] = datetime.fromisoformat(start_date)
        if end_date:
            query['created_at']['$lte'] = datetime.fromisoformat(end_date)

    db = get_db()
    if not db:
        return jsonify({'error': 'database_error', 'message': 'Database not available'}), 500

    transactions = list(db.fund_transactions.find(query).sort('created_at', -1).skip(skip).limit(limit))
    total = db.fund_transactions.count_documents(query)

    for txn in transactions:
        txn['_id'] = str(txn['_id'])
        if 'created_at' in txn:
            txn['created_at'] = txn['created_at'].isoformat()

    return jsonify({
        'transactions': transactions,
        'total': total,
        'limit': limit,
        'skip': skip
    }), 200


@bp.route('/reset', methods=['POST'])
def reset_funds():
    """
    Reset paper trading funds to initial balance.

    Request Body:
        {
            "amount": 100000
        }

    Returns:
        Reset fund details
    """
    user_id = "default_user"
    data = request.get_json() or {}

    initial_amount = data.get('amount', 100000)

    db = get_db()
    if not db:
        return jsonify({'error': 'database_error', 'message': 'Database not available'}), 500

    funds = db.funds.find_one({'user_id': user_id})

    reset_record = {
        'user_id': user_id,
        'previous_balance': funds.get('balance', 0) if funds else 0,
        'new_balance': initial_amount,
        'mode': 'paper',
        'created_at': datetime.utcnow()
    }
    db.fund_resets.insert_one(reset_record)

    db.funds.update_one(
        {'user_id': user_id},
        {'$set': {
            'balance': initial_amount,
            'available_balance': initial_amount,
            'used_margin': 0,
            'realized_pnl': 0,
            'unrealized_pnl': 0,
            'updated_at': datetime.utcnow()
        }},
        upsert=True
    )

    db.trades.update_many(
        {'user_id': user_id, 'mode': 'paper', 'status': 'OPEN'},
        {'$set': {'status': 'CANCELLED', 'exit_reason': 'funds_reset'}}
    )
    db.positions.delete_many({'user_id': user_id, 'mode': 'paper', 'status': 'open'})

    logger.info(f"Funds reset to {initial_amount} for user {user_id}")

    return jsonify({
        'message': 'Funds reset successfully',
        'balance': initial_amount
    }), 200


@bp.route('/update-pnl', methods=['POST'])
def update_pnl():
    """
    Update PnL values (called by trading engine).

    Request Body:
        {
            "realized_pnl": 1500,
            "unrealized_pnl": 250
        }

    Returns:
        Updated fund details
    """
    user_id = "default_user"
    data = request.get_json() or {}

    db = get_db()
    if not db:
        return jsonify({'error': 'database_error', 'message': 'Database not available'}), 500

    update_data = {'updated_at': datetime.utcnow()}
    if 'realized_pnl' in data:
        update_data['realized_pnl'] = float(data['realized_pnl'])
    if 'unrealized_pnl' in data:
        update_data['unrealized_pnl'] = float(data['unrealized_pnl'])

    funds = db.funds.find_one({'user_id': user_id})
    if funds:
        db.funds.update_one(
            {'user_id': user_id},
            {'$set': update_data}
        )

        new_available = funds.get('available_balance', 0) + data.get('realized_pnl', 0)
        db.funds.update_one(
            {'user_id': user_id},
            {'$set': {'available_balance': new_available}}
        )

    return jsonify({
        'message': 'PnL updated successfully'
    }), 200


@bp.route('/summary', methods=['GET'])
def get_funds_summary():
    """
    Get comprehensive funds summary.

    Returns:
        Fund summary with statistics
    """
    user_id = "default_user"

    db = get_db()
    if not db:
        return jsonify({'error': 'database_error', 'message': 'Database not available'}), 500

    funds = db.funds.find_one({'user_id': user_id})

    if not funds:
        return jsonify({
            'error': 'not_found',
            'message': 'Funds not found'
        }), 404

    total_deposited = funds.get('total_deposited', 0)
    total_withdrawn = funds.get('total_withdrawn', 0)
    realized_pnl = funds.get('realized_pnl', 0)

    summary = {
        'current_balance': funds.get('balance', 0),
        'available_balance': funds.get('available_balance', 0),
        'used_margin': funds.get('used_margin', 0),
        'realized_pnl': realized_pnl,
        'unrealized_pnl': funds.get('unrealized_pnl', 0),
        'total_deposited': total_deposited,
        'total_withdrawn': total_withdrawn,
        'net_profit': realized_pnl + (funds.get('balance', 0) - total_deposited),
        'roi_percent': ((funds.get('balance', 0) - total_deposited) / total_deposited * 100) if total_deposited > 0 else 0,
        'currency': funds.get('currency', 'INR')
    }

    return jsonify(summary), 200