"""
Async Strategy Engine API
=========================
API endpoints for async strategy engine management.
"""

import asyncio
import logging
from bson import ObjectId
from datetime import datetime
from flask import Blueprint, request, jsonify

from app.async_engine import (
    get_async_engine,
    get_task_manager,
    get_scheduler,
    get_rate_limiter,
    get_backpressure_handler,
    get_event_bus
)

logger = logging.getLogger('async_engine_api')

bp = Blueprint('async_engine', __name__, url_prefix='/api/async')


@bp.route('/status', methods=['GET'])
def get_engine_status():
    """Get async strategy engine status and metrics."""
    try:
        engine = get_async_engine()
        metrics = engine.get_metrics()
        
        strategies = engine.get_all_strategies()
        
        return jsonify({
            'status': metrics['status'],
            'metrics': metrics,
            'strategies': strategies
        }), 200

    except Exception as e:
        logger.error(f"Error getting engine status: {e}")
        return jsonify({'error': 'engine_error', 'message': str(e)}), 500


@bp.route('/strategies', methods=['POST'])
def add_strategy():
    """Add a new strategy to the engine."""
    try:
        data = request.get_json() or {}
        user_id = "default_user"
        
        data['user_id'] = user_id
        
        engine = get_async_engine()
        strategy_id = asyncio.run(engine.add_strategy(data))
        
        return jsonify({
            'strategy_id': strategy_id,
            'message': 'Strategy added successfully'
        }), 201

    except Exception as e:
        logger.error(f"Error adding strategy: {e}")
        return jsonify({'error': 'engine_error', 'message': str(e)}), 500


@bp.route('/strategies/<strategy_id>/start', methods=['POST'])
def start_strategy(strategy_id):
    """Start a specific strategy."""
    try:
        engine = get_async_engine()
        success = asyncio.run(engine.start_strategy(strategy_id))

        if success:
            return jsonify({
                'message': 'Strategy started',
                'strategy_id': strategy_id
            }), 200
        else:
            return jsonify({'error': 'strategy_error', 'message': 'Failed to start strategy'}), 400

    except Exception as e:
        logger.error(f"Error starting strategy: {e}")
        return jsonify({'error': 'engine_error', 'message': str(e)}), 500


@bp.route('/strategies/<strategy_id>/stop', methods=['POST'])
def stop_strategy(strategy_id):
    """Stop a specific strategy."""
    try:
        engine = get_async_engine()
        success = asyncio.run(engine.stop_strategy(strategy_id))

        if success:
            return jsonify({
                'message': 'Strategy stopped',
                'strategy_id': strategy_id
            }), 200
        else:
            return jsonify({'error': 'strategy_error', 'message': 'Failed to stop strategy'}), 400

    except Exception as e:
        logger.error(f"Error stopping strategy: {e}")
        return jsonify({'error': 'engine_error', 'message': str(e)}), 500


@bp.route('/strategies/<strategy_id>/pause', methods=['POST'])
def pause_strategy(strategy_id):
    """Pause a specific strategy."""
    try:
        engine = get_async_engine()
        success = asyncio.run(engine.pause_strategy(strategy_id))

        if success:
            return jsonify({
                'message': 'Strategy paused',
                'strategy_id': strategy_id
            }), 200
        else:
            return jsonify({'error': 'strategy_error', 'message': 'Failed to pause strategy'}), 400

    except Exception as e:
        logger.error(f"Error pausing strategy: {e}")
        return jsonify({'error': 'engine_error', 'message': str(e)}), 500


@bp.route('/strategies/<strategy_id>/status', methods=['GET'])
def get_strategy_status(strategy_id):
    """Get status of a specific strategy."""
    try:
        engine = get_async_engine()
        status = engine.get_strategy_status(strategy_id)

        if status:
            return jsonify({'status': status}), 200
        else:
            return jsonify({'error': 'not_found', 'message': 'Strategy not found'}), 404

    except Exception as e:
        logger.error(f"Error getting strategy status: {e}")
        return jsonify({'error': 'engine_error', 'message': str(e)}), 500


@bp.route('/tasks/status', methods=['GET'])
def get_task_status():
    """Get task manager status."""
    try:
        task_manager = get_task_manager()
        metrics = task_manager.get_metrics()

        return jsonify({'tasks': metrics}), 200

    except Exception as e:
        logger.error(f"Error getting task status: {e}")
        return jsonify({'error': 'engine_error', 'message': str(e)}), 500


@bp.route('/scheduler/schedules', methods=['GET'])
def get_schedules():
    """Get scheduler schedules."""
    try:
        scheduler = get_scheduler()
        schedules = scheduler.get_all_schedules()

        return jsonify({'schedules': schedules}), 200

    except Exception as e:
        logger.error(f"Error getting schedules: {e}")
        return jsonify({'error': 'engine_error', 'message': str(e)}), 500


@bp.route('/backpressure/status', methods=['GET'])
def get_backpressure_status():
    """Get backpressure handler status."""
    try:
        backpressure = get_backpressure_handler()
        metrics = backpressure.get_metrics()

        return jsonify({'backpressure': metrics}), 200

    except Exception as e:
        logger.error(f"Error getting backpressure status: {e}")
        return jsonify({'error': 'engine_error', 'message': str(e)}), 500


@bp.route('/rate-limiter/stats', methods=['GET'])
def get_rate_limiter_stats():
    """Get rate limiter statistics."""
    try:
        rate_limiter = get_rate_limiter()
        stats = rate_limiter.get_stats()

        return jsonify({'rate_limiter': stats}), 200

    except Exception as e:
        logger.error(f"Error getting rate limiter stats: {e}")
        return jsonify({'error': 'engine_error', 'message': str(e)}), 500


@bp.route('/events', methods=['GET'])
def get_events():
    """Get recent events from event bus."""
    try:
        limit = int(request.args.get('limit', 100))
        event_type = request.args.get('type')
        
        event_bus = get_event_bus()
        events = event_bus.get_recent_events(event_type, limit)

        return jsonify({'events': events}), 200

    except Exception as e:
        logger.error(f"Error getting events: {e}")
        return jsonify({'error': 'engine_error', 'message': str(e)}), 500


@bp.route('/events/dead-letter', methods=['GET'])
def get_dead_letter():
    """Get dead letter events."""
    try:
        event_bus = get_event_bus()
        events = event_bus.get_dead_letter()

        return jsonify({'dead_letter': events}), 200

    except Exception as e:
        logger.error(f"Error getting dead letter: {e}")
        return jsonify({'error': 'engine_error', 'message': str(e)}), 500


@bp.route('/engine/start', methods=['POST'])
def start_engine():
    """Start the async engine."""
    try:
        engine = get_async_engine()
        success = asyncio.run(engine.start())

        if success:
            return jsonify({'message': 'Engine started successfully'}), 200
        else:
            return jsonify({'error': 'engine_error', 'message': 'Failed to start engine'}), 500

    except Exception as e:
        logger.error(f"Error starting engine: {e}")
        return jsonify({'error': 'engine_error', 'message': str(e)}), 500


@bp.route('/engine/stop', methods=['POST'])
def stop_engine():
    """Stop the async engine."""
    try:
        engine = get_async_engine()
        timeout = float(request.json.get('timeout', 30.0)) if request.json else 30.0
        success = asyncio.run(engine.stop(timeout))

        if success:
            return jsonify({'message': 'Engine stopped successfully'}), 200
        else:
            return jsonify({'error': 'engine_error', 'message': 'Failed to stop engine'}), 500

    except Exception as e:
        logger.error(f"Error stopping engine: {e}")
        return jsonify({'error': 'engine_error', 'message': str(e)}), 500


@bp.route('/engine/metrics', methods=['GET'])
def get_all_metrics():
    """Get comprehensive engine metrics."""
    try:
        engine = get_async_engine()
        task_manager = get_task_manager()
        scheduler = get_scheduler()
        backpressure = get_backpressure_handler()
        rate_limiter = get_rate_limiter()
        event_bus = get_event_bus()

        return jsonify({
            'engine': engine.get_metrics(),
            'tasks': task_manager.get_metrics(),
            'scheduler': scheduler.get_metrics(),
            'backpressure': backpressure.get_metrics(),
            'rate_limiter': rate_limiter.get_stats(),
            'events': event_bus.get_stats()
        }), 200

    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        return jsonify({'error': 'engine_error', 'message': str(e)}), 500


def register_async_engine_routes(app):
    """Register async engine routes with the Flask app."""
    app.register_blueprint(bp)
    logger.info("Async engine routes registered")