"""
Market Data API
================
Indian stock market data, candles, quotes, depth, and indicators.
"""

import logging
from datetime import datetime
from flask import Blueprint, request, jsonify

from app.market_data.engine import get_market_engine

logger = logging.getLogger('trading_app')

bp = Blueprint('market', __name__)


@bp.route('/candles', methods=['GET', 'OPTIONS'])
def get_candles():
    """
    Get OHLCV candle data.
    """
    symbol = request.args.get('symbol', 'RELIANCE')
    timeframe = request.args.get('timeframe', '1h')
    limit = min(int(request.args.get('limit', 100)), 1000)
    
    try:
        engine = get_market_engine()
        candles = engine.get_candles(symbol, timeframe, limit) if engine else []
        return jsonify({
            'success': True,
            'data': {
                'symbol': symbol.upper(),
                'timeframe': timeframe,
                'candles': candles,
                'count': len(candles)
            },
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        import traceback
        logger.error(f"Failed to fetch candles: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': 'market_data_error',
            'message': str(e)
        }), 500


@bp.route('/current-candle', methods=['GET'])
def get_current_candle():
    """
    Get current (in-progress) candle.
    """
    symbol = request.args.get('symbol', 'RELIANCE')
    timeframe = request.args.get('timeframe', '1m')
    
    try:
        engine = get_market_engine()
        candle = engine.get_current_candle(symbol.upper(), timeframe) if engine else None
        return jsonify({
            'success': True,
            'data': candle,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        import traceback
        logger.error(f"Failed to get current candle: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': 'market_data_error',
            'message': str(e)
        }), 500


@bp.route('/quotes', methods=['GET', 'OPTIONS'])
def get_quotes():
    """
    Get current quotes for multiple symbols.
    """
    symbols = request.args.get('symbols', 'RELIANCE,TCS,INFY,HDFCBANK,ICICIBANK').split(',')
    symbols = [s.strip().upper() for s in symbols if s.strip()]
    
    try:
        engine = get_market_engine()
        quotes = []
        if engine:
            for symbol in symbols:
                tick = engine.get_tick(symbol)
                if tick:
                    quotes.append(tick)
        
        return jsonify({
            'success': True,
            'data': quotes,
            'count': len(quotes),
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        import traceback
        logger.error(f"Failed to fetch quotes: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': 'market_data_error',
            'message': str(e)
        }), 500


@bp.route('/quote/<symbol>', methods=['GET'])
def get_quote(symbol):
    """
    Get current quote for a symbol.
    """
    symbol = symbol.upper()
    
    try:
        engine = get_market_engine()
        tick = engine.get_tick(symbol) if engine else None
        if not tick:
            return jsonify({
                'success': False,
                'error': 'symbol_not_found',
                'message': f'Symbol {symbol} not found or no data available'
            }), 404
        
        return jsonify({
            'success': True,
            'data': tick,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        import traceback
        logger.error(f"Failed to get quote: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': 'market_data_error',
            'message': str(e)
        }), 500


@bp.route('/symbols', methods=['GET'])
def list_symbols():
    """
    List available trading symbols.
    """
    filter_type = request.args.get('type', 'all')
    
    try:
        engine = get_market_engine()
        symbols = engine.get_symbols(filter_type) if engine else []
        return jsonify({
            'success': True,
            'data': symbols,
            'count': len(symbols),
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        import traceback
        logger.error(f"Failed to list symbols: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': 'market_data_error',
            'message': str(e)
        }), 500


@bp.route('/symbol-info/<symbol>', methods=['GET'])
def get_symbol_info(symbol):
    """
    Get symbol information.
    """
    symbol = symbol.upper()
    
    try:
        engine = get_market_engine()
        info = engine.get_symbol_info(symbol) if engine else None
        if not info:
            return jsonify({
                'success': False,
                'error': 'symbol_not_found',
                'message': f'Symbol {symbol} not found'
            }), 404
        
        return jsonify({
            'success': True,
            'data': info,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        import traceback
        logger.error(f"Failed to get symbol info: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': 'market_data_error',
            'message': str(e)
        }), 500


@bp.route('/depth/<symbol>', methods=['GET'])
def get_market_depth(symbol):
    """
    Get market depth / order book for a symbol.
    """
    symbol = symbol.upper()
    
    try:
        engine = get_market_engine()
        depth = engine.get_depth(symbol) if engine else None
        if not depth:
            return jsonify({
                'success': False,
                'error': 'symbol_not_found',
                'message': f'Symbol {symbol} depth not found'
            }), 404
        
        return jsonify({
            'success': True,
            'data': depth,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        import traceback
        logger.error(f"Failed to get depth: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': 'market_data_error',
            'message': str(e)
        }), 500


@bp.route('/indicators/<symbol>', methods=['GET'])
def get_indicators(symbol):
    """
    Get technical indicators for a symbol.
    """
    symbol = symbol.upper()
    
    try:
        engine = get_market_engine()
        indicators = engine.get_indicators(symbol) if engine else None
        if not indicators:
            return jsonify({
                'success': False,
                'error': 'symbol_not_found',
                'message': f'Symbol {symbol} not found or no data'
            }), 404
        
        return jsonify({
            'success': True,
            'data': indicators,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        import traceback
        logger.error(f"Failed to get indicators: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': 'market_data_error',
            'message': str(e)
        }), 500


@bp.route('/status', methods=['GET'])
def get_market_status():
    """
    Get current market status.
    """
    try:
        engine = get_market_engine()
        status = engine.get_market_status() if engine else {}
        return jsonify({
            'success': True,
            'data': status,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        import traceback
        logger.error(f"Failed to get market status: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': 'market_data_error',
            'message': str(e)
        }), 500


@bp.route('/overview', methods=['GET'])
def get_market_overview():
    """
    Get market overview with indices and top movers.
    """
    try:
        engine = get_market_engine()
        indices = []
        gainers = []
        losers = []
        status = {}
        
        if engine:
            indices_symbols = ['NIFTY50', 'BANKNIFTY', 'SENSEX']
            
            for symbol in indices_symbols:
                tick = engine.get_tick(symbol)
                if tick:
                    indices.append({
                        'symbol': symbol,
                        'value': tick.get('ltp', 0),
                        'change': tick.get('change', 0),
                        'change_percent': tick.get('change_percent', 0)
                    })
            
            all_ticks = engine.get_all_ticks()
            stocks = [t for t in all_ticks if not t.get('symbol', '').endswith(('50', 'BANK', 'SENSEX'))]
            
            sorted_by_change = sorted(stocks, key=lambda x: x.get('change_percent', 0), reverse=True)
            
            gainers = sorted_by_change[:5]
            losers = sorted_by_change[-5:][::-1]
            status = engine.get_market_status()
            
        return jsonify({
            'success': True,
            'data': {
                'indices': indices,
                'top_gainers': gainers,
                'top_losers': losers,
                'market_status': status
            },
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        import traceback
        logger.error(f"Failed to get market overview: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': 'market_data_error',
            'message': str(e)
        }), 500


@bp.route('/watchlist', methods=['GET'])
def get_watchlist_quotes():
    """
    Get quotes for default watchlist symbols.
    """
    default_symbols = ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK', 'SBIN', 'KOTAKBANK', 'LT', 'ITC', 'BHARTIARTL']
    
    try:
        engine = get_market_engine()
        quotes = []
        if engine:
            for symbol in default_symbols:
                tick = engine.get_tick(symbol)
                if tick:
                    quotes.append(tick)
        
        return jsonify({
            'success': True,
            'data': quotes,
            'count': len(quotes),
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        import traceback
        logger.error(f"Failed to get watchlist: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': 'market_data_error',
            'message': str(e)
        }), 500