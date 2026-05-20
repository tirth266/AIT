"""
Notifications API
=================
User notification management endpoints.
"""

import logging
from datetime import datetime
from bson import ObjectId
from flask import Blueprint, request, jsonify

from app.database.connection import get_db

logger = logging.getLogger('trading_app')

bp = Blueprint('notifications', __name__)


@bp.route('', methods=['GET'])
def list_notifications():
    """
    List notifications for the user.

    Query Parameters:
        - type: filter by type (trade, signal, system, alert)
        - is_read: filter by read status
        - priority: filter by priority (low, medium, high, critical)
        - limit: number of results (default 50)
        - skip: number to skip (default 0)

    Returns:
        List of notifications
    """
    user_id = "default_user"
    notification_type = request.args.get('type')
    is_read = request.args.get('is_read')
    priority = request.args.get('priority')
    limit = int(request.args.get('limit', 50))
    skip = int(request.args.get('skip', 0))

    query = {'user_id': user_id}
    if notification_type:
        query['type'] = notification_type
    if is_read is not None:
        query['is_read'] = is_read.lower() == 'true'
    if priority:
        query['priority'] = priority.lower()

    db = get_db()
    if not db:
        return jsonify({'error': 'database_error', 'message': 'Database not available'}), 500

    notifications = list(db.notifications.find(query).sort('created_at', -1).skip(skip).limit(limit))
    total = db.notifications.count_documents(query)
    unread_count = db.notifications.count_documents({**query, 'is_read': False})

    for notif in notifications:
        notif['_id'] = str(notif['_id'])
        if 'created_at' in notif:
            notif['created_at'] = notif['created_at'].isoformat()
        if 'read_at' in notif:
            notif['read_at'] = notif['read_at'].isoformat()

    return jsonify({
        'notifications': notifications,
        'total': total,
        'unread_count': unread_count,
        'limit': limit,
        'skip': skip
    }), 200


@bp.route('', methods=['POST'])
def create_notification():
    """
    Create a new notification.

    Request Body:
        {
            "type": "trade",
            "title": "Order Executed",
            "message": "BUY order for RELIANCE executed",
            "priority": "high",
            "metadata": {...}
        }

    Returns:
        Created notification details
    """
    user_id = "default_user"
    data = request.get_json() or {}

    title = data.get('title')
    if not title:
        return jsonify({
            'error': 'validation_error',
            'message': 'Title is required'
        }), 400

    db = get_db()
    if not db:
        return jsonify({'error': 'database_error', 'message': 'Database not available'}), 500

    notification = {
        'user_id': user_id,
        'type': data.get('type', 'system'),
        'title': title,
        'message': data.get('message', ''),
        'priority': data.get('priority', 'medium'),
        'is_read': False,
        'is_dismissed': False,
        'metadata': data.get('metadata', {}),
        'action_url': data.get('action_url'),
        'created_at': datetime.utcnow(),
        'read_at': None
    }

    result = db.notifications.insert_one(notification)
    logger.info(f"Notification created: {result.inserted_id}")

    notification['_id'] = str(result.inserted_id)
    notification['created_at'] = notification['created_at'].isoformat()

    return jsonify(notification), 201


@bp.route('/<notification_id>', methods=['GET'])
def get_notification(notification_id):
    """
    Get a specific notification.

    Returns:
        Notification details
    """
    user_id = "default_user"

    db = get_db()
    if not db:
        return jsonify({'error': 'database_error', 'message': 'Database not available'}), 500

    try:
        notification = db.notifications.find_one({
            '_id': ObjectId(notification_id),
            'user_id': user_id
        })
    except Exception:
        return jsonify({
            'error': 'validation_error',
            'message': 'Invalid notification ID'
        }), 400

    if not notification:
        return jsonify({
            'error': 'not_found',
            'message': 'Notification not found'
        }), 404

    notification['_id'] = str(notification['_id'])
    if 'created_at' in notification:
        notification['created_at'] = notification['created_at'].isoformat()
    if 'read_at' in notification and notification['read_at']:
        notification['read_at'] = notification['read_at'].isoformat()

    return jsonify(notification), 200


@bp.route('/<notification_id>/read', methods=['POST'])
def mark_as_read(notification_id):
    """
    Mark a notification as read.

    Returns:
        Success message
    """
    user_id = "default_user"

    db = get_db()
    if not db:
        return jsonify({'error': 'database_error', 'message': 'Database not available'}), 500

    try:
        result = db.notifications.update_one(
            {'_id': ObjectId(notification_id), 'user_id': user_id},
            {'$set': {
                'is_read': True,
                'read_at': datetime.utcnow()
            }}
        )
    except Exception:
        return jsonify({
            'error': 'validation_error',
            'message': 'Invalid notification ID'
        }), 400

    if result.matched_count == 0:
        return jsonify({
            'error': 'not_found',
            'message': 'Notification not found'
        }), 404

    return jsonify({
        'message': 'Notification marked as read'
    }), 200


@bp.route('/read-all', methods=['POST'])
def mark_all_as_read():
    """
    Mark all notifications as read for the user.

    Returns:
        Success message with count
    """
    user_id = "default_user"

    db = get_db()
    if not db:
        return jsonify({'error': 'database_error', 'message': 'Database not available'}), 500

    result = db.notifications.update_many(
        {'user_id': user_id, 'is_read': False},
        {'$set': {
            'is_read': True,
            'read_at': datetime.utcnow()
        }}
    )

    logger.info(f"Marked {result.modified_count} notifications as read")

    return jsonify({
        'message': 'All notifications marked as read',
        'count': result.modified_count
    }), 200


@bp.route('/<notification_id>', methods=['DELETE'])
def delete_notification(notification_id):
    """
    Delete a notification.

    Returns:
        Success message
    """
    user_id = "default_user"

    db = get_db()
    if not db:
        return jsonify({'error': 'database_error', 'message': 'Database not available'}), 500

    try:
        result = db.notifications.delete_one({
            '_id': ObjectId(notification_id),
            'user_id': user_id
        })
    except Exception:
        return jsonify({
            'error': 'validation_error',
            'message': 'Invalid notification ID'
        }), 400

    if result.deleted_count == 0:
        return jsonify({
            'error': 'not_found',
            'message': 'Notification not found'
        }), 404

    logger.info(f"Notification deleted: {notification_id}")

    return jsonify({
        'message': 'Notification deleted successfully'
    }), 200


@bp.route('/clear', methods=['DELETE'])
def clear_notifications():
    """
    Clear all read notifications or all notifications.

    Request Body:
        {
            "clear_type": "read" | "all"
        }

    Returns:
        Success message with count
    """
    user_id = "default_user"
    data = request.get_json() or {}
    clear_type = data.get('clear_type', 'read')

    db = get_db()
    if not db:
        return jsonify({'error': 'database_error', 'message': 'Database not available'}), 500

    query = {'user_id': user_id}
    if clear_type == 'read':
        query['is_read'] = True

    result = db.notifications.delete_many(query)

    logger.info(f"Cleared {result.deleted_count} notifications")

    return jsonify({
        'message': 'Notifications cleared',
        'count': result.deleted_count
    }), 200


@bp.route('/unread-count', methods=['GET'])
def get_unread_count():
    """
    Get count of unread notifications.

    Returns:
        Unread count
    """
    user_id = "default_user"

    db = get_db()
    if not db:
        return jsonify({'error': 'database_error', 'message': 'Database not available'}), 500

    count = db.notifications.count_documents({
        'user_id': user_id,
        'is_read': False
    })

    return jsonify({
        'unread_count': count
    }), 200


@bp.route('/broadcast', methods=['POST'])
def broadcast_notification():
    """
    Broadcast a notification to all users (admin endpoint).

    Request Body:
        {
            "type": "system",
            "title": "System Update",
            "message": "...",
            "priority": "high"
        }

    Returns:
        Broadcast result
    """
    data = request.get_json() or {}

    title = data.get('title')
    if not title:
        return jsonify({
            'error': 'validation_error',
            'message': 'Title is required'
        }), 400

    db = get_db()
    if not db:
        return jsonify({'error': 'database_error', 'message': 'Database not available'}), 500

    users = list(db.users.find({}, {'_id': 1}))
    notifications = []

    for user in users:
        notifications.append({
            'user_id': str(user['_id']),
            'type': data.get('type', 'system'),
            'title': title,
            'message': data.get('message', ''),
            'priority': data.get('priority', 'medium'),
            'is_read': False,
            'is_dismissed': False,
            'metadata': data.get('metadata', {}),
            'created_at': datetime.utcnow(),
            'read_at': None
        })

    if notifications:
        db.notifications.insert_many(notifications)

    logger.info(f"Broadcast notification to {len(notifications)} users")

    return jsonify({
        'message': 'Notification broadcast',
        'recipients': len(notifications)
    }), 201