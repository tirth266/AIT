"""
Strategy Engine API
==================
API endpoints for strategy execution, backtesting, and management.
"""

import logging
from bson import ObjectId
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.database.connection import get_db
from app.strategy_engine.engine import get_strategy_engine, initialize_engine
from app.strategy_engine.strategy_manager import StrategyManager
from app.strategy_engine.paper_trading import get_paper_engine
from app.strategy_engine.backtesting.engine import get_backtest_engine

logger = logging.getLogger('strategy_engine_api')

bp = Blueprint('strategy_engine', __name__, url_prefix='/api/engine')


@bp.route('/status', methods=['GET'])
@jwt_required()
def get_engine_status():
    """Get strategy engine status and metrics."""
    try:
        engine = get_strategy_engine()
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


@bp.route('/strategies/<strategy_id>/start', methods=['POST'])
@jwt_required()
def start_strategy(strategy_id):
    """Start a strategy."""
    try:
        engine = get_strategy_engine()
        success = engine.strategy_manager.run_strategy(strategy_id)

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
@jwt_required()
def stop_strategy(strategy_id):
    """Stop a strategy."""
    try:
        engine = get_strategy_engine()
        success = engine.strategy_manager.stop_strategy(strategy_id)

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


@bp.route('/signals', methods=['GET'])
@jwt_required()
def get_signals():
    """Get generated signals."""
    try:
        user_id = get_jwt_identity()
        limit = int(request.args.get('limit', 50))

        db = get_db()
        if not db:
            return jsonify({'error': 'database_error', 'message': 'Database not available'}), 500

        signals = list(db.strategy_signals.find(
            {'user_id': user_id}
        ).sort('timestamp', -1).limit(limit))

        for signal in signals:
            signal['_id'] = str(signal['_id'])
            if 'timestamp' in signal and hasattr(signal['timestamp'], 'isoformat'):
                signal['timestamp'] = signal['timestamp'].isoformat()

        return jsonify({'signals': signals}), 200

    except Exception as e:
        logger.error(f"Error getting signals: {e}")
        return jsonify({'error': 'engine_error', 'message': str(e)}), 500


@bp.route('/signals', methods=['POST'])
@jwt_required()
def generate_signal():
    """Generate a signal for a strategy."""
    try:
        data = request.get_json() or {}
        strategy_id = data.get('strategy_id')

        if not strategy_id:
            return jsonify({'error': 'validation_error', 'message': 'strategy_id is required'}), 400

        db = get_db()
        if not db:
            return jsonify({'error': 'database_error', 'message': 'Database not available'}), 500

        strategy = db.strategies.find_one({'_id': ObjectId(strategy_id)})
        if not strategy:
            return jsonify({'error': 'not_found', 'message': 'Strategy not found'}), 404

        engine = get_strategy_engine()
        from app.strategy_engine.signal_generator import SignalGenerator
        generator = SignalGenerator()

        from app.strategy_engine.indicators import IndicatorRegistry
        indicators = IndicatorRegistry()

        candles = indicators.calculate_all([])
        signal = await generator.generate(strategy, candles, strategy.get('symbol'))

        if signal:
            signal['strategy_id'] = strategy_id
            signal['user_id'] = get_jwt_identity()
            signal['timestamp'] = datetime.utcnow()

            db.strategy_signals.insert_one(signal)

            return jsonify({'signal': signal}), 200

        return jsonify({'signal': None, 'message': 'No signal generated'}), 200

    except Exception as e:
        logger.error(f"Error generating signal: {e}")
        return jsonify({'error': 'engine_error', 'message': str(e)}), 500


@bp.route('/backtest', methods=['POST'])
@jwt_required()
def run_backtest():
    """Run a backtest."""
    try:
        data = request.get_json() or {}

        strategy_id = data.get('strategy_id')
        symbol = data.get('symbol')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        initial_capital = data.get('initial_capital', 100000)

        if not all([strategy_id, symbol, start_date, end_date]):
            return jsonify({
                'error': 'validation_error',
                'message': 'strategy_id, symbol, start_date, and end_date are required'
            }), 400

        db = get_db()
        if not db:
            return jsonify({'error': 'database_error', 'message': 'Database not available'}), 500

        strategy = db.strategies.find_one({'_id': ObjectId(strategy_id)})
        if not strategy:
            return jsonify({'error': 'not_found', 'message': 'Strategy not found'}), 404

        start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))

        backtest_engine = get_backtest_engine()

        import asyncio
        result = asyncio.run(backtest_engine.run_backtest(
            strategy,
            symbol,
            start,
            end,
            initial_capital
        ))

        if not result:
            return jsonify({'error': 'backtest_error', 'message': 'Backtest failed'}), 500

        result_dict = {
            'strategy_id': result.strategy_id,
            'symbol': result.symbol,
            'start_date': result.start_date.isoformat(),
            'end_date': result.end_date.isoformat(),
            'initial_capital': result.initial_capital,
            'final_capital': result.final_capital,
            'total_return': result.total_return,
            'total_return_percent': result.total_return_percent,
            'total_trades': result.total_trades,
            'winning_trades': result.winning_trades,
            'losing_trades': result.losing_trades,
            'win_rate': result.win_rate,
            'avg_win': result.avg_win,
            'avg_loss': result.avg_loss,
            'profit_factor': result.profit_factor,
            'max_drawdown': result.max_drawdown,
            'max_drawdown_percent': result.max_drawdown_percent,
            'sharpe_ratio': result.sharpe_ratio
        }

        db.backtest_results.insert_one({
            'strategy_id': strategy_id,
            'user_id': get_jwt_identity(),
            'result': result_dict,
            'created_at': datetime.utcnow()
        })

        return jsonify({'backtest': result_dict}), 200

    except Exception as e:
        logger.error(f"Error running backtest: {e}")
        return jsonify({'error': 'engine_error', 'message': str(e)}), 500


@bp.route('/paper-trading/portfolio', methods=['GET'])
@jwt_required()
def get_paper_portfolio():
    """Get paper trading portfolio."""
    try:
        user_id = get_jwt_identity()

        paper_engine = get_paper_engine()
        portfolio = asyncio.run(paper_engine.get_portfolio(user_id))

        if not portfolio:
            portfolio = asyncio.run(paper_engine.initialize_portfolio(user_id))

        if '_id' in portfolio:
            portfolio['_id'] = str(portfolio['_id'])

        return jsonify({'portfolio': portfolio}), 200

    except Exception as e:
        logger.error(f"Error getting portfolio: {e}")
        return jsonify({'error': 'engine_error', 'message': str(e)}), 500


@bp.route('/paper-trading/trades', methods=['GET'])
@jwt_required()
def get_paper_trades():
    """Get paper trading trades."""
    try:
        user_id = get_jwt_identity()
        status = request.args.get('status', 'all')
        limit = int(request.args.get('limit', 50))

        paper_engine = get_paper_engine()

        if status == 'open':
            trades = asyncio.run(paper_engine.get_open_trades(user_id))
        else:
            trades = asyncio.run(paper_engine.get_trade_history(user_id, limit))

        return jsonify({'trades': trades}), 200

    except Exception as e:
        logger.error(f"Error getting trades: {e}")
        return jsonify({'error': 'engine_error', 'message': str(e)}), 500


@bp.route('/paper-trading/performance', methods=['GET'])
@jwt_required()
def get_paper_performance():
    """Get paper trading performance."""
    try:
        user_id = get_jwt_identity()
        days = int(request.args.get('days', 30))

        paper_engine = get_paper_engine()
        performance = asyncio.run(paper_engine.calculate_performance(user_id, days))

        return jsonify({'performance': performance}), 200

    except Exception as e:
        logger.error(f"Error getting performance: {e}")
        return jsonify({'error': 'engine_error', 'message': str(e)}), 500


@bp.route('/paper-trading/reset', methods=['POST'])
@jwt_required()
def reset_paper_portfolio():
    """Reset paper trading portfolio."""
    try:
        user_id = get_jwt_identity()

        paper_engine = get_paper_engine()
        success = asyncio.run(paper_engine.reset_portfolio(user_id))

        if success:
            return jsonify({'message': 'Portfolio reset successfully'}), 200
        else:
            return jsonify({'error': 'reset_error', 'message': 'Failed to reset portfolio'}), 400

    except Exception as e:
        logger.error(f"Error resetting portfolio: {e}")
        return jsonify({'error': 'engine_error', 'message': str(e)}), 500


@bp.route('/strategies/list', methods=['GET'])
@jwt_required()
def list_managed_strategies():
    """List strategies being managed by the engine."""
    try:
        engine = get_strategy_engine()
        strategies = engine.get_all_strategies()

        return jsonify({'strategies': strategies}), 200

    except Exception as e:
        logger.error(f"Error listing strategies: {e}")
        return jsonify({'error': 'engine_error', 'message': str(e)}), 500


@bp.route('/risk/summary', methods=['GET'])
@jwt_required()
def get_risk_summary():
    """Get risk management summary."""
    try:
        user_id = get_jwt_identity()

        from app.strategy_engine.risk_manager import RiskManager
        risk_manager = RiskManager()

        import asyncio
        summary = asyncio.run(risk_manager.get_risk_summary(user_id))

        return jsonify({'risk': summary}), 200

    except Exception as e:
        logger.error(f"Error getting risk summary: {e}")
        return jsonify({'error': 'engine_error', 'message': str(e)}), 500


import asyncio


def register_engine_routes(app):
    """Register engine routes with the Flask app."""
    app.register_blueprint(bp)
    logger.info("Strategy engine routes registered")