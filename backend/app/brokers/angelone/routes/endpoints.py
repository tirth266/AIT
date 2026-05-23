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

@bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Login to Angel One using SmartAPI.
    Uses provided clientcode, password and totp (secret) to generate a session.
    """
    import traceback
    import os
    import pyotp
    from SmartApi import SmartConnect
    from loguru import logger

    logger.info("=== ANGEL ONE LOGIN REQUEST ===")

    if request.method == 'GET':
        return jsonify({
            'status': 'available',
            'endpoint': '/api/v1/broker/angelone/login',
            'methods': ['POST'],
            'message': 'Use POST to perform login with clientcode, password, and totp secret'
        }), 200

    try:
        # 1. Parse and Validate Request Payload
        data = request.get_json(silent=True)
        
        if data is None:
            logger.error("Login failed: No JSON payload received")
            return jsonify({
                "success": False,
                "error": "MISSING_PAYLOAD",
                "message": "No JSON payload received. Ensure Content-Type is application/json"
            }), 400

        # Log keys for debugging (omit password/totp values)
        logger.debug(f"Received payload keys: {list(data.keys())}")
        
        # Support both camelCase and snake_case
        clientcode = data.get("clientcode") or data.get("client_code")
        password = data.get("password")
        totp_secret = data.get("totp") or data.get("totp_secret")

        # Detailed validation logging
        missing_fields = []
        if not clientcode: missing_fields.append("clientcode")
        if not password: missing_fields.append("password")
        if not totp_secret: missing_fields.append("totp")

        if missing_fields:
            logger.warning(f"Validation Error: Missing fields: {missing_fields}")
            return jsonify({
                "success": False,
                "error": "VALIDATION_FAILED",
                "message": f"Missing required fields: {', '.join(missing_fields)}",
                "missing_fields": missing_fields
            }), 400

        logger.info(f"Attempting login for client: {clientcode}")

        # 2. Generate current 6-digit TOTP from secret
        try:
            current_totp = pyotp.TOTP(totp_secret.replace(" ", "")).now()
            logger.debug(f"Generated TOTP for {clientcode}")
        except Exception as totp_err:
            logger.error(f"TOTP Generation Error: {totp_err}")
            return jsonify({
                "success": False,
                "error": "TOTP_GEN_FAILED",
                "message": "Invalid TOTP secret format. Please check your broker security settings."
            }), 400

        # 3. Check Environment Configuration
        api_key = os.getenv("ANGEL_API_KEY")
        if not api_key:
            logger.error("Configuration Error: ANGEL_API_KEY environment variable is not set")
            return jsonify({
                "success": False,
                "error": "CONFIG_ERROR",
                "message": "Server-side configuration error. Please contact administrator."
            }), 500

        # 4. Initialize SmartConnect and Generate Session
        logger.info(f"Initializing SmartConnect for client: {clientcode}")
        smartApi = SmartConnect(api_key)
        
        try:
            logger.info(f"Calling SmartAPI generateSession for {clientcode}...")
            session = smartApi.generateSession(clientcode, password, current_totp)
            
            if not session or not session.get("status"):
                logger.error(f"SmartAPI login failed for {clientcode}: {session}")
                return jsonify({
                    "success": False,
                    "error": "BROKER_AUTHENTICATION_FAILED",
                    "message": session.get("message", "Invalid credentials or session expired"),
                    "details": session
                }), 401

            session_data = session.get('data', {})
            jwt_token = session_data.get('jwtToken')
            refresh_token = session_data.get('refreshToken')
            feed_token = session_data.get('feedToken')

            if not jwt_token:
                logger.error(f"SmartAPI returned success status but missing jwtToken for {clientcode}")
                return jsonify({
                    "success": False,
                    "error": "TOKEN_RETRIEVAL_FAILED",
                    "message": "Broker authentication succeeded but failed to retrieve session tokens."
                }), 500

            # 5. Save Session and return success
            session_manager.set_tokens(jwt_token, refresh_token, feed_token)
            
            # Sync with singleton if possible
            try:
                client = get_client()
                client.smart_api = smartApi
                client.smart_api.setAccessToken(jwt_token)
                client.smart_api.setRefreshToken(refresh_token)
            except Exception as sync_err:
                logger.warning(f"Failed to sync client singleton: {sync_err}")

            logger.info(f"Login successful for client: {clientcode}")

            return jsonify({
                'success': True,
                'message': 'Logged in successfully',
                'data': {
                    'client_code': clientcode,
                    'jwt_token': jwt_token,
                    'refresh_token': refresh_token,
                    'feed_token': feed_token
                }
            }), 200

        except Exception as api_err:
            logger.exception(f"SmartAPI Exception during generateSession: {api_err}")
            return jsonify({
                "success": False,
                "error": "BROKER_CONNECTION_ERROR",
                "message": f"Could not connect to broker: {str(api_err)}"
            }), 500

    except Exception as e:
        logger.exception(f"Unexpected error in login route: {e}")
        return jsonify({
            'success': False,
            'error': 'INTERNAL_SERVER_ERROR',
            'message': 'An unexpected error occurred processing your login request'
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
    try:
        client = get_api_client()
        if not client: 
            return jsonify({'success': False, 'error': 'auth_error', 'message': 'Broker session expired'}), 401
        
        response = client.get_profile()
        return jsonify(response)
    except Exception as e:
        logger.error(f"Error fetching profile: {e}")
        return jsonify({'success': False, 'message': 'Failed to fetch profile', 'data': {}}), 500

@bp.route('/funds', methods=['GET'])
def get_funds():
    try:
        client = get_api_client()
        if not client: 
            return jsonify({'success': False, 'error': 'auth_error', 'message': 'Broker session expired'}), 401
        
        response = client.get_funds()
        return jsonify(response)
    except Exception as e:
        logger.error(f"Error fetching funds: {e}")
        return jsonify({'success': False, 'message': 'Failed to fetch funds', 'data': {}}), 500

@bp.route('/positions', methods=['GET'])
def get_positions():
    try:
        client = get_api_client()
        if not client: 
            return jsonify({'success': False, 'error': 'auth_error', 'message': 'Broker session expired'}), 401
        
        response = client.get_positions()
        return jsonify(response)
    except Exception as e:
        logger.error(f"Error fetching positions: {e}")
        return jsonify({'success': False, 'message': 'Failed to fetch positions', 'data': []}), 500

@bp.route('/orders', methods=['GET'])
def get_orders():
    try:
        client = get_api_client()
        if not client: 
            return jsonify({'success': False, 'error': 'auth_error', 'message': 'Broker session expired'}), 401
        
        response = client.get_order_book()
        return jsonify(response)
    except Exception as e:
        logger.error(f"Error fetching orders: {e}")
        return jsonify({'success': False, 'message': 'Failed to fetch orders', 'data': []}), 500

@bp.route('/holdings', methods=['GET'])
def get_holdings():
    try:
        client = get_api_client()
        if not client: 
            return jsonify({'success': False, 'error': 'auth_error', 'message': 'Broker session expired'}), 401
        
        response = client.get_holdings()
        return jsonify(response)
    except Exception as e:
        logger.error(f"Error fetching holdings: {e}")
        return jsonify({'success': False, 'message': 'Failed to fetch holdings', 'data': []}), 500

@bp.route('/order/place', methods=['POST'])
def place_order():
    try:
        client = get_api_client()
        if not client: 
            return jsonify({'success': False, 'error': 'auth_error', 'message': 'Broker session expired'}), 401
            
        data = request.json or {}
        required = ['variety', 'tradingsymbol', 'symboltoken', 'transactiontype', 
                    'exchange', 'ordertype', 'producttype', 'duration', 'price', 
                    'squareoff', 'stoploss', 'quantity']
        params = {k: data.get(k, "") for k in required}
        
        if not all([params['tradingsymbol'], params['symboltoken'], params['transactiontype'], params['quantity']]):
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
            
        response = client.place_order(params)
        return jsonify(response)
    except Exception as e:
        logger.error(f"Error placing order: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/order/modify', methods=['POST'])
def modify_order():
    try:
        client = get_api_client()
        if not client: 
            return jsonify({'success': False, 'error': 'auth_error', 'message': 'Broker session expired'}), 401
            
        data = request.json or {}
        if 'orderid' not in data:
            return jsonify({'success': False, 'message': 'orderid is required'}), 400
            
        response = client.modify_order(data)
        return jsonify(response)
    except Exception as e:
        logger.error(f"Error modifying order: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/order/cancel', methods=['POST'])
def cancel_order():
    try:
        client = get_api_client()
        if not client: 
            return jsonify({'success': False, 'error': 'auth_error', 'message': 'Broker session expired'}), 401
            
        data = request.json or {}
        if 'orderid' not in data:
            return jsonify({'success': False, 'message': 'orderid is required'}), 400
            
        response = client.cancel_order(data['orderid'], data.get('variety', 'NORMAL'))
        return jsonify(response)
    except Exception as e:
        logger.error(f"Error cancelling order: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/ltp', methods=['GET'])
def get_ltp():
    try:
        client = get_api_client()
        if not client: 
            return jsonify({'success': False, 'error': 'auth_error', 'message': 'Broker session expired'}), 401
            
        exchange = request.args.get('exchange', 'NSE')
        symbol = request.args.get('symbol')
        token = request.args.get('token')
        
        if not symbol or not token:
            return jsonify({'success': False, 'message': 'symbol and token are required'}), 400
            
        response = client.get_ltp(exchange, symbol, token)
        return jsonify(response)
    except Exception as e:
        logger.error(f"Error fetching LTP: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/history', methods=['GET'])
def get_history():
    try:
        client = get_api_client()
        if not client: 
            return jsonify({'success': False, 'error': 'auth_error', 'message': 'Broker session expired'}), 401
            
        params = {
            'exchange': request.args.get('exchange', 'NSE'),
            'symboltoken': request.args.get('token'),
            'interval': request.args.get('interval', 'ONE_MINUTE'),
            'fromdate': request.args.get('fromdate'),
            'todate': request.args.get('todate')
        }
        if not params['symboltoken'] or not params['fromdate'] or not params['todate']:
            return jsonify({'success': False, 'message': 'token, fromdate, todate are required'}), 400
            
        response = client.get_historical_data(params)
        return jsonify(response)
    except Exception as e:
        logger.error(f"Error fetching history: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
