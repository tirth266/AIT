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
    """
    Login to Angel One using SmartAPI.
    Uses provided clientcode, password and totp (secret) to generate a session.
    """
    import traceback
    import os
    import pyotp
    from SmartApi import SmartConnect

    print("==== ANGEL LOGIN START ====")

    if request.method == 'GET':
        return jsonify({
            'status': 'available',
            'endpoint': '/api/v1/broker/angelone/login',
            'methods': ['POST'],
            'message': 'Use POST to perform login with clientcode, password, and totp secret'
        }), 200

    try:
        # 1. Parse and Validate Request Payload
        data = request.get_json(silent=True) or {}
        print("Incoming Data:", {k: (v if k != 'password' else '***') for k, v in data.items()})
        
        clientcode = data.get("clientcode") or data.get("client_code")
        password = data.get("password")
        totp_secret = data.get("totp")

        print("Client Code:", clientcode)

        if not clientcode or not password or not totp_secret:
            print("[AngelOne] Validation Error: Missing credentials")
            return jsonify({
                "success": False,
                "message": "Missing credentials (clientcode, password, totp)"
            }), 400

        # 2. Generate current 6-digit TOTP from secret
        try:
            current_totp = pyotp.TOTP(totp_secret).now()
            print("Generated TOTP:", current_totp)
        except Exception as totp_err:
            print(f"[AngelOne] TOTP Generation Error: {totp_err}")
            return jsonify({
                "success": False,
                "error": "TOTP_GEN_FAILED",
                "message": "Invalid TOTP secret provided"
            }), 400

        # 3. Check Environment Configuration
        api_key = os.getenv("ANGEL_API_KEY")
        print("API KEY EXISTS:", bool(api_key))
        
        if not api_key:
            print("[AngelOne] Configuration Error: Missing ANGEL_API_KEY")
            return jsonify({
                "success": False,
                "error": "CONFIG_ERROR",
                "message": "Server configuration error: Missing API Key"
            }), 500

        # 4. Initialize SmartConnect and Generate Session
        print(f"[AngelOne] Initializing SmartConnect for client: {clientcode}")
        smartApi = SmartConnect(api_key)
        
        try:
            print(f"[AngelOne] Calling generateSession for {clientcode}...")
            session = smartApi.generateSession(clientcode, password, current_totp)
            print("SESSION RESPONSE:", session)
            
            if not session.get("status"):
                print(f"[AngelOne] SmartAPI login failed: {session}")
                return jsonify({
                    "success": False,
                    "message": session
                }), 401

            session_data = session.get('data', {})
            jwt_token = session_data.get('jwtToken')
            refresh_token = session_data.get('refreshToken')
            feed_token = session_data.get('feedToken')

            if not jwt_token:
                print('[AngelOne] Login succeeded but no JWT token returned')
                return jsonify({
                    "success": False,
                    "error": "TOKEN_ERROR",
                    "message": "Failed to retrieve session tokens from broker"
                }), 500

            # 5. Save Session and return success
            session_manager.set_tokens(jwt_token, refresh_token, feed_token)
            
            # Sync with singleton if possible
            try:
                client = get_client()
                client.smart_api = smartApi
                client.smart_api.setAccessToken(jwt_token)
                client.smart_api.setRefreshToken(refresh_token)
            except Exception:
                pass

            print(f"[AngelOne] Login successful for user: {clientcode}")

            return jsonify({
                'success': True,
                'message': 'Logged in successfully',
                'token': jwt_token,
                'data': session,
                'tokens': {
                    'jwt_token': jwt_token,
                    'refresh_token': refresh_token,
                    'feed_token': feed_token,
                    'client_code': clientcode
                }
            }), 200

        except Exception as api_err:
            print(f"[AngelOne] SmartAPI Exception: {str(api_err)}")
            return jsonify({
                "success": False,
                "error": "API_CONNECTION_ERROR",
                "message": f"Broker connection failed: {str(api_err)}"
            }), 500

    except Exception as e:
        print("==== LOGIN ERROR ====")
        print(str(e))
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
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

@bp.route('/profile', methods=['GET', 'OPTIONS'])
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

@bp.route('/funds', methods=['GET', 'OPTIONS'])
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

@bp.route('/positions', methods=['GET', 'OPTIONS'])
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

@bp.route('/orders', methods=['GET', 'OPTIONS'])
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

@bp.route('/holdings', methods=['GET', 'OPTIONS'])
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

@bp.route('/order/place', methods=['POST', 'OPTIONS'])
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

@bp.route('/order/modify', methods=['POST', 'OPTIONS'])
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

@bp.route('/order/cancel', methods=['POST', 'OPTIONS'])
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

@bp.route('/ltp', methods=['GET', 'OPTIONS'])
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

@bp.route('/history', methods=['GET', 'OPTIONS'])
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
