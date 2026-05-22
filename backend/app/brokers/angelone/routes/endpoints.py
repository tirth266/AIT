"""
Angel One REST API Routes
==========================
Endpoints for interacting with Angel One.
"""

import logging
import asyncio
from flask import Blueprint, jsonify, request, Response
from ..auth.session import session_manager
from ..api.client import get_client

logger = logging.getLogger('angelone')

bp = Blueprint('angelone_broker', __name__)

def get_api_client():
    """Helper to get initialized client with session restoration."""
    try:
        # Restore session from Redis/Persistence if needed
        success = session_manager.check_and_restore_session()
        if not success:
            logger.warning("Failed to restore AngelOne session")
            return None
            
        client = get_client()
        # Sync the internal smart_api state with the session_manager tokens
        if session_manager.jwt_token:
            client.smart_api.setAccessToken(session_manager.jwt_token)
            client.smart_api.setRefreshToken(session_manager.refresh_token)
            
        return client
    except Exception as e:
        logger.error(f"Failed to initialize AngelOne client: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

@bp.route('/login', methods=['GET', 'POST', 'OPTIONS'])
def login():
    """Login to Angel One using environment credentials."""
    logger.info(f'[AngelOne] Login request: {request.method}')
    # ... rest of login implementation stays same but with logging ...

    if request.method == 'GET':
        return jsonify({
            'status': 'available',
            'endpoint': '/api/v1/broker/angelone/login',
            'methods': ['POST'],
            'message': 'Use POST to perform login'
        }), 200

    client = get_api_client()
    if not client:
        return jsonify({'success': False, 'error': 'CLIENT_INIT_FAILED', 'message': 'Client initialization failed'}), 500

    try:
        payload = request.get_json(silent=True) or {}
        client_code = payload.get('client_code') or payload.get('clientcode')
        password = payload.get('password')
        totp = payload.get('totp')

        logger.info(f'Login attempt - client_code provided: {bool(client_code)}, password provided: {bool(password)}, totp provided: {bool(totp)}')

        if not client_code or not password:
            return jsonify({
                "success": False,
                "error": "VALIDATION_ERROR",
                "message": "client_code and password are required"
            }), 400

        from ..services.auth_service import AuthService
        
        try:
            auth_service = AuthService()
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                data = loop.run_until_complete(auth_service.login(client_code=client_code, password=password, totp=totp))
            finally:
                loop.close()
        except Exception as login_inner:
            logger.error(f'Login execution failed: {login_inner}')
            return jsonify({
                'success': False,
                'error': 'LOGIN_FAILED',
                'message': str(login_inner)
            }), 401

        if data:
            session_manager.set_tokens(
                jwt_token=data.get('jwtToken'),
                refresh_token=data.get('refreshToken'),
                feed_token=data.get('feedToken')
            )

            logger.info('Angel One login successful')

            return jsonify({
                'success': True,
                'message': 'Logged in successfully',
                'data': {
                    'jwt_token': data.get('jwtToken'),
                    'refresh_token': data.get('refreshToken'),
                    'feed_token': data.get('feedToken')
                }
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Login failed'
            }), 401

    except Exception as e:
        logger.error(f'Angel One login error: {e}')
        import traceback
        logger.error(f'Full traceback:\n{traceback.format_exc()}')
        return jsonify({
            'success': False,
            'error': 'LOGIN_ERROR',
            'message': str(e),
            'traceback': traceback.format_exc().splitlines()
        }), 500

@bp.route('/connect', methods=['POST'])
def connect():
    success = session_manager.check_and_restore_session()
    if success:
        return jsonify({'success': True, 'message': 'Connected to Angel One'})
    return jsonify({'success': False, 'message': 'Failed to connect'}), 401

@bp.route('/session/status', methods=['GET'])
def session_status():
    is_valid = session_manager.is_connected
    return jsonify({
        'is_valid': is_valid,
        'has_jwt': bool(session_manager.jwt_token),
        'has_refresh': bool(session_manager.refresh_token),
        'has_feed': bool(session_manager.feed_token)
    })

@bp.route('/session/refresh', methods=['POST'])
def session_refresh():
    success = session_manager.renew_token()
    return jsonify({'success': success, 'message': 'Token renewed' if success else 'Refresh failed'})

@bp.route('/disconnect', methods=['POST'])
def disconnect():
    success = session_manager.disconnect()
    return jsonify({'success': success, 'message': 'Disconnected' if success else 'Failed'})

@bp.route('/profile', methods=['GET'])
def get_profile():
    client = get_api_client()
    if not client: return jsonify({'status': False, 'message': 'Client error'}), 500
    return jsonify(client.get_profile())

@bp.route('/funds', methods=['GET'])
def get_funds():
    client = get_api_client()
    if not client: return jsonify({'status': False, 'message': 'Client error'}), 500
    return jsonify(client.get_funds())

@bp.route('/positions', methods=['GET', 'OPTIONS'])
def get_positions():
    client = get_api_client()
    if not client: return jsonify({'status': False, 'message': 'Client error'}), 500
    return jsonify(client.get_positions())

@bp.route('/orders', methods=['GET'])
def get_orders():
    client = get_api_client()
    if not client: return jsonify({'status': False, 'message': 'Client error'}), 500
    return jsonify(client.get_order_book())

@bp.route('/holdings', methods=['GET', 'OPTIONS'])
def get_holdings():
    client = get_api_client()
    if not client: return jsonify({'status': False, 'message': 'Client error'}), 500
    return jsonify(client.get_holdings())

@bp.route('/order/place', methods=['POST'])
def place_order():
    client = get_api_client()
    if not client: return jsonify({'status': False, 'message': 'Client error'}), 500
    data = request.json
    required = ['variety', 'tradingsymbol', 'symboltoken', 'transactiontype', 
                'exchange', 'ordertype', 'producttype', 'duration', 'price', 
                'squareoff', 'stoploss', 'quantity']
    params = {k: data.get(k, "") for k in required}
    
    # Validation
    if not all([params['tradingsymbol'], params['symboltoken'], params['transactiontype'], params['quantity']]):
        return jsonify({'status': False, 'message': 'Missing required fields'}), 400
        
    return jsonify(client.place_order(params))

@bp.route('/order/modify', methods=['POST'])
def modify_order():
    client = get_api_client()
    if not client: return jsonify({'status': False, 'message': 'Client error'}), 500
    data = request.json
    if not data or 'orderid' not in data:
        return jsonify({'status': False, 'message': 'orderid is required'}), 400
    return jsonify(client.modify_order(data))

@bp.route('/order/cancel', methods=['POST'])
def cancel_order():
    client = get_api_client()
    if not client: return jsonify({'status': False, 'message': 'Client error'}), 500
    data = request.json
    if not data or 'orderid' not in data:
        return jsonify({'status': False, 'message': 'orderid is required'}), 400
    return jsonify(client.cancel_order(data['orderid'], data.get('variety', 'NORMAL')))

@bp.route('/ltp', methods=['GET'])
def get_ltp():
    client = get_api_client()
    if not client: return jsonify({'status': False, 'message': 'Client error'}), 500
    exchange = request.args.get('exchange', 'NSE')
    symbol = request.args.get('symbol')
    token = request.args.get('token')
    
    if not symbol or not token:
        return jsonify({'status': False, 'message': 'symbol and token are required'}), 400
        
    return jsonify(client.get_ltp(exchange, symbol, token))

@bp.route('/history', methods=['GET'])
def get_history():
    client = get_api_client()
    if not client: return jsonify({'status': False, 'message': 'Client error'}), 500
    params = {
        'exchange': request.args.get('exchange', 'NSE'),
        'symboltoken': request.args.get('token'),
        'interval': request.args.get('interval', 'ONE_MINUTE'),
        'fromdate': request.args.get('fromdate'),
        'todate': request.args.get('todate')
    }
    if not params['symboltoken'] or not params['fromdate'] or not params['todate']:
        return jsonify({'status': False, 'message': 'token, fromdate, todate are required'}), 400
        
    return jsonify(client.get_historical_data(params))
