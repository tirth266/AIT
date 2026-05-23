"""
Watchlist API
=============
Stock watchlist management endpoints.
"""

import logging
from datetime import datetime
from bson import ObjectId
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required

from app.database.connection import get_db
from app.utils.auth import get_current_user_id

logger = logging.getLogger('trading_app')

bp = Blueprint('watchlist', __name__)


@bp.route('', methods=['GET'])
@jwt_required(optional=True)
def get_watchlist():
    """
    List all watchlists for the user.
    """
    try:
        user_id = get_current_user_id()
        logger.info(f"[Watchlist] Listing watchlists for {user_id}")

        db = get_db()
        if not db:
            logger.error("[Watchlist] Database connection missing")
            return jsonify({'error': 'database_error', 'message': 'Database not available'}), 500

        watchlists = list(db.watchlists.find({'user_id': user_id}).sort('created_at', -1))

        for wl in watchlists:
            wl['_id'] = str(wl['_id'])
            if 'created_at' in wl:
                wl['created_at'] = wl['created_at'].isoformat() if hasattr(wl['created_at'], 'isoformat') else str(wl['created_at'])
            if 'updated_at' in wl:
                wl['updated_at'] = wl['updated_at'].isoformat() if hasattr(wl['updated_at'], 'isoformat') else str(wl['updated_at'])

        return jsonify({
            "success": True,
            "data": watchlists,
            "total": len(watchlists)
        }), 200

    except Exception as e:
        import traceback
        logger.error(f"[Watchlist] Critical failure: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': 'internal_error',
            'message': str(e)
        }), 500


@bp.route('', methods=['POST'])
def create_watchlist():
    """
    Create a new watchlist.

    Request Body:
        {
            "name": "Tech Stocks",
            "symbols": ["RELIANCE", "TCS", "INFY"],
            "description": "My tech stock watchlist"
        }

    Returns:
        Created watchlist details
    """
    user_id = get_current_user_id()
    data = request.get_json() or {}

    name = data.get('name')
    if not name:
        return jsonify({
            'error': 'validation_error',
            'message': 'Watchlist name is required'
        }), 400

    db = get_db()
    if not db:
        return jsonify({'error': 'database_error', 'message': 'Database not available'}), 500

    existing = db.watchlists.find_one({'user_id': user_id, 'name': name})
    if existing:
        return jsonify({
            'error': 'conflict',
            'message': 'Watchlist with this name already exists'
        }), 409

    watchlist = {
        'user_id': user_id,
        'name': name,
        'description': data.get('description', ''),
        'symbols': data.get('symbols', []),
        'is_default': data.get('is_default', False),
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow()
    }

    if watchlist['is_default']:
        db.watchlists.update_many(
            {'user_id': user_id, 'is_default': True},
            {'$set': {'is_default': False}}
        )

    result = db.watchlists.insert_one(watchlist)
    logger.info(f"Watchlist created: {result.inserted_id}")

    return jsonify({
        'id': str(result.inserted_id),
        'name': name,
        'created_at': watchlist['created_at'].isoformat()
    }), 201


@bp.route('/<watchlist_id>', methods=['GET'])
def get_watchlist_by_id(watchlist_id):
    """
    Get a specific watchlist with symbol details.

    Returns:
        Watchlist details
    """
    user_id = get_current_user_id()

    db = get_db()
    if not db:
        return jsonify({'error': 'database_error', 'message': 'Database not available'}), 500

    try:
        watchlist = db.watchlists.find_one({
            '_id': ObjectId(watchlist_id),
            'user_id': user_id
        })
    except Exception:
        return jsonify({
            'error': 'validation_error',
            'message': 'Invalid watchlist ID'
        }), 400

    if not watchlist:
        return jsonify({
            'error': 'not_found',
            'message': 'Watchlist not found'
        }), 404

    watchlist['_id'] = str(watchlist['_id'])
    if 'created_at' in watchlist:
        watchlist['created_at'] = watchlist['created_at'].isoformat()
    if 'updated_at' in watchlist:
        watchlist['updated_at'] = watchlist['updated_at'].isoformat()

    return jsonify(watchlist), 200


@bp.route('/<watchlist_id>', methods=['PUT'])
def update_watchlist(watchlist_id):
    """
    Update a watchlist.

    Request Body:
        {
            "name": "New Name",
            "description": "Updated description",
            "symbols": ["RELIANCE", "TCS"]
        }

    Returns:
        Success message
    """
    user_id = get_current_user_id()
    data = request.get_json() or {}

    db = get_db()
    if not db:
        return jsonify({'error': 'database_error', 'message': 'Database not available'}), 500

    try:
        result = db.watchlists.update_one(
            {'_id': ObjectId(watchlist_id), 'user_id': user_id},
            {'$set': {
                'name': data.get('name'),
                'description': data.get('description'),
                'symbols': data.get('symbols'),
                'updated_at': datetime.utcnow()
            }}
        )
    except Exception:
        return jsonify({
            'error': 'validation_error',
            'message': 'Invalid watchlist ID'
        }), 400

    if result.matched_count == 0:
        return jsonify({
            'error': 'not_found',
            'message': 'Watchlist not found'
        }), 404

    logger.info(f"Watchlist updated: {watchlist_id}")

    return jsonify({
        'message': 'Watchlist updated successfully'
    }), 200


@bp.route('/<watchlist_id>', methods=['DELETE'])
def delete_watchlist(watchlist_id):
    """
    Delete a watchlist.

    Returns:
        Success message
    """
    user_id = get_current_user_id()

    db = get_db()
    if not db:
        return jsonify({'error': 'database_error', 'message': 'Database not available'}), 500

    try:
        result = db.watchlists.delete_one({
            '_id': ObjectId(watchlist_id),
            'user_id': user_id
        })
    except Exception:
        return jsonify({
            'error': 'validation_error',
            'message': 'Invalid watchlist ID'
        }), 400

    if result.deleted_count == 0:
        return jsonify({
            'error': 'not_found',
            'message': 'Watchlist not found'
        }), 404

    logger.info(f"Watchlist deleted: {watchlist_id}")

    return jsonify({
        'message': 'Watchlist deleted successfully'
    }), 200


@bp.route('/<watchlist_id>/symbols', methods=['POST'])
def add_symbol(watchlist_id):
    """
    Add symbol to watchlist.

    Request Body:
        {
            "symbol": "RELIANCE"
        }

    Returns:
        Updated watchlist
    """
    user_id = get_current_user_id()
    data = request.get_json() or {}

    symbol = data.get('symbol', '').upper()
    if not symbol:
        return jsonify({
            'error': 'validation_error',
            'message': 'Symbol is required'
        }), 400

    db = get_db()
    if not db:
        return jsonify({'error': 'database_error', 'message': 'Database not available'}), 500

    try:
        watchlist = db.watchlists.find_one({
            '_id': ObjectId(watchlist_id),
            'user_id': user_id
        })
    except Exception:
        return jsonify({
            'error': 'validation_error',
            'message': 'Invalid watchlist ID'
        }), 400

    if not watchlist:
        return jsonify({
            'error': 'not_found',
            'message': 'Watchlist not found'
        }), 404

    symbols = watchlist.get('symbols', [])
    if symbol in symbols:
        return jsonify({
            'error': 'conflict',
            'message': 'Symbol already in watchlist'
        }), 409

    symbols.append(symbol)
    db.watchlists.update_one(
        {'_id': ObjectId(watchlist_id)},
        {'$set': {'symbols': symbols, 'updated_at': datetime.utcnow()}}
    )

    return jsonify({
        'message': 'Symbol added successfully',
        'symbols': symbols
    }), 200


@bp.route('/<watchlist_id>/symbols/<symbol>', methods=['DELETE'])
def remove_symbol(watchlist_id, symbol):
    """
    Remove symbol from watchlist.

    Returns:
        Updated watchlist
    """
    user_id = get_current_user_id()
    symbol = symbol.upper()

    db = get_db()
    if not db:
        return jsonify({'error': 'database_error', 'message': 'Database not available'}), 500

    try:
        watchlist = db.watchlists.find_one({
            '_id': ObjectId(watchlist_id),
            'user_id': user_id
        })
    except Exception:
        return jsonify({
            'error': 'validation_error',
            'message': 'Invalid watchlist ID'
        }), 400

    if not watchlist:
        return jsonify({
            'error': 'not_found',
            'message': 'Watchlist not found'
        }), 404

    symbols = [s for s in watchlist.get('symbols', []) if s != symbol]
    db.watchlists.update_one(
        {'_id': ObjectId(watchlist_id)},
        {'$set': {'symbols': symbols, 'updated_at': datetime.utcnow()}}
    )

    return jsonify({
        'message': 'Symbol removed successfully',
        'symbols': symbols
    }), 200


@bp.route('/reorder', methods=['POST'])
def reorder_watchlists():
    """
    Reorder watchlists (set default, sort order).

    Request Body:
        {
            "watchlist_ids": ["id1", "id2", "id3"],
            "default_id": "id1"
        }

    Returns:
        Success message
    """
    user_id = get_current_user_id()
    data = request.get_json() or {}

    watchlist_ids = data.get('watchlist_ids', [])
    default_id = data.get('default_id')

    db = get_db()
    if not db:
        return jsonify({'error': 'database_error', 'message': 'Database not available'}), 500

    for idx, wl_id in enumerate(watchlist_ids):
        try:
            db.watchlists.update_one(
                {'_id': ObjectId(wl_id), 'user_id': user_id},
                {'$set': {'sort_order': idx}}
            )
        except Exception:
            continue

    if default_id:
        db.watchlists.update_many(
            {'user_id': user_id, 'is_default': True},
            {'$set': {'is_default': False}}
        )
        try:
            db.watchlists.update_one(
                {'_id': ObjectId(default_id), 'user_id': user_id},
                {'$set': {'is_default': True}}
            )
        except Exception:
            pass

    return jsonify({
        'message': 'Watchlists reordered successfully'
    }), 200