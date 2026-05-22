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
    
    Query Parameters:
        - symbol: Trading symbol (e.g., RELIANCE, NIFTY50)
        - timeframe: Timeframe (1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 1d)
        - limit: Number of candles (default 100, max 1000)
    
    Returns:
        List of candles
    """
    symbol = request.args.get('symbol', 'RELIANCE')
    timeframe = request.args.get('timeframe', '1h')
    limit = min(int(request.args.get('limit', 100)), 1000)
    
    try:
        candles = market_data_engine.get_candles(symbol, timeframe, limit)
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
        logger.error(f"Failed to fetch candles: {e}")
        return jsonify({
            'success': False,
            'error': 'market_data_error',
            'message': 'Failed to fetch candle data'
        }), 502


@bp.route('/current-candle', methods=['GET'])
def get_current_candle():
    """
    Get current (in-progress) candle.
    
    Query Parameters:
        - symbol: Trading symbol
        - timeframe: Timeframe
    
    Returns:
        Current candle data
    """
    symbol = request.args.get('symbol', 'RELIANCE')
    timeframe = request.args.get('timeframe', '1m')
    
    try:
        candle = market_data_engine.get_current_candle(symbol.upper(), timeframe)
        return jsonify({
            'success': True,
            'data': candle,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Failed to get current candle: {e}")
        return jsonify({
            'success': False,
            'error': 'market_data_error',
            'message': 'Failed to get current candle'
        }), 502


@bp.route('/quotes', methods=['GET', 'OPTIONS'])
def get_quotes():
    """
    Get current quotes for multiple symbols.
    
    Query Parameters:
        - symbols: Comma-separated symbols (e.g., RELIANCE,TCS,INFY)
    
    Returns:
        List of quote data
    """
    symbols = request.args.get('symbols', 'RELIANCE,TCS,INFY,HDFCBANK,ICICIBANK').split(',')
    symbols = [s.strip().upper() for s in symbols if s.strip()]
    
    try:
        quotes = []
        for symbol in symbols:
            tick = market_data_engine.get_tick(symbol)
            if tick:
                quotes.append(tick)
        
        return jsonify({
            'success': True,
            'data': quotes,
            'count': len(quotes),
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Failed to fetch quotes: {e}")
        return jsonify({
            'success': False,
            'error': 'market_data_error',
            'message': 'Failed to fetch quotes'
        }), 502


@bp.route('/quote/<symbol>', methods=['GET'])
def get_quote(symbol):
    """
    Get current quote for a symbol.
    
    Returns:
        Quote data
    """
    symbol = symbol.upper()
    
    try:
        tick = market_data_engine.get_tick(symbol)
        if not tick:
            return jsonify({
                'success': False,
                'error': 'symbol_not_found',
                'message': f'Symbol {symbol} not found'
            }), 404
        
        return jsonify({
            'success': True,
            'data': tick,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Failed to get quote: {e}")
        return jsonify({
            'success': False,
            'error': 'market_data_error',
            'message': f'Failed to get quote for {symbol}'
        }), 502


@bp.route('/symbols', methods=['GET'])
def list_symbols():
    """
    List available trading symbols.
    
    Query Parameters:
        - type: 'all', 'stocks', or 'indices' (default 'all')
    
    Returns:
        List of symbols
    """
    filter_type = request.args.get('type', 'all')
    
    try:
        symbols = market_data_engine.get_symbols(filter_type)
        return jsonify({
            'success': True,
            'data': symbols,
            'count': len(symbols),
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Failed to list symbols: {e}")
        return jsonify({
            'success': False,
            'error': 'market_data_error',
            'message': 'Failed to list symbols'
        }), 502


@bp.route('/symbol-info/<symbol>', methods=['GET'])
def get_symbol_info(symbol):
    """
    Get symbol information.
    
    Returns:
        Symbol metadata
    """
    symbol = symbol.upper()
    
    try:
        info = market_data_engine.get_symbol_info(symbol)
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
        logger.error(f"Failed to get symbol info: {e}")
        return jsonify({
            'success': False,
            'error': 'market_data_error',
            'message': f'Failed to get info for {symbol}'
        }), 502


@bp.route('/depth/<symbol>', methods=['GET'])
def get_market_depth(symbol):
    """
    Get market depth / order book for a symbol.
    
    Query Parameters:
        - symbol: Trading symbol
        - limit: Depth levels (default 10)
    
    Returns:
        Order book data
    """
    symbol = symbol.upper()
    
    try:
        depth = market_data_engine.get_depth(symbol)
        if not depth:
            return jsonify({
                'success': False,
                'error': 'symbol_not_found',
                'message': f'Symbol {symbol} not found'
            }), 404
        
        return jsonify({
            'success': True,
            'data': depth,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Failed to get depth: {e}")
        return jsonify({
            'success': False,
            'error': 'market_data_error',
            'message': f'Failed to get depth for {symbol}'
        }), 502


@bp.route('/indicators/<symbol>', methods=['GET'])
def get_indicators(symbol):
    """
    Get technical indicators for a symbol.
    
    Query Parameters:
        - symbol: Trading symbol
    
    Returns:
        Technical indicators (EMA, RSI, MACD, VWAP, Supertrend, Bollinger Bands, ATR)
    """
    symbol = symbol.upper()
    
    try:
        indicators = market_data_engine.get_indicators(symbol)
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
        logger.error(f"Failed to get indicators: {e}")
        return jsonify({
            'success': False,
            'error': 'market_data_error',
            'message': f'Failed to get indicators for {symbol}'
        }), 502


@bp.route('/status', methods=['GET'])
def get_market_status():
    """
    Get current market status.
    
    Returns:
        Market status (open, closed, session)
    """
    try:
        status = market_data_engine.get_market_status()
        return jsonify({
            'success': True,
            'data': status,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Failed to get market status: {e}")
        return jsonify({
            'success': False,
            'error': 'market_data_error',
            'message': 'Failed to get market status'
        }), 502


@bp.route('/overview', methods=['GET'])
def get_market_overview():
    """
    Get market overview with indices and top movers.
    
    Returns:
        Market overview data
    """
    try:
        indices_symbols = ['NIFTY50', 'BANKNIFTY', 'SENSEX']
        indices = []
        
        for symbol in indices_symbols:
            tick = market_data_engine.get_tick(symbol)
            if tick:
                indices.append({
                    'symbol': symbol,
                    'value': tick.get('ltp', 0),
                    'change': tick.get('change', 0),
                    'change_percent': tick.get('change_percent', 0)
                })
        
        all_ticks = market_data_engine.get_all_ticks()
        stocks = [t for t in all_ticks if not t.get('symbol', '').endswith(('50', 'BANK', 'SENSEX'))]
        
        sorted_by_change = sorted(stocks, key=lambda x: x.get('change_percent', 0), reverse=True)
        
        gainers = sorted_by_change[:5]
        losers = sorted_by_change[-5:][::-1]
        
        return jsonify({
            'success': True,
            'data': {
                'indices': indices,
                'top_gainers': gainers,
                'top_losers': losers,
                'market_status': market_data_engine.get_market_status()
            },
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Failed to get market overview: {e}")
        return jsonify({
            'success': False,
            'error': 'market_data_error',
            'message': 'Failed to get market overview'
        }), 502


@bp.route('/watchlist', methods=['GET'])
def get_watchlist_quotes():
    """
    Get quotes for default watchlist symbols.
    
    Returns:
        List of watchlist quotes
    """
    default_symbols = ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK', 'SBIN', 'KOTAKBANK', 'LT', 'ITC', 'BHARTIARTL']
    
    try:
        engine = get_market_engine()
        quotes = []
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
        logger.error(f"Failed to get watchlist: {e}")
        return jsonify({
            'success': False,
            'error': 'market_data_error',
            'message': 'Failed to get watchlist'
        }), 502