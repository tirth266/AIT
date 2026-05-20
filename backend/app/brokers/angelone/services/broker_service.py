"""
Angel One Broker Service
========================
Implements the BrokerFactory interface for Angel One.
"""

import logging
from typing import Dict, Optional
from ..api.client import get_client
from ..auth.session import session_manager

logger = logging.getLogger('angelone.service')

class AngelOneBroker:
    """Angel One integration matching the internal Broker interface."""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        # Ensure session is active
        session_manager.check_and_restore_session()
        
    def get_balance(self) -> float:
        """Get available balance."""
        client = get_client()
        funds = client.get_funds()
        if funds and funds.get('status') and funds.get('data'):
            try:
                # Use available cash
                return float(funds['data'].get('availablecash', 0))
            except (ValueError, TypeError):
                pass
        return 0.0
        
    def place_order(self, order_data: Dict) -> Dict:
        """Place an order via the internal standardized format."""
        # This would require translating our internal Order model to Angel One's format
        # This is a stub for the BrokerFactory interface.
        client = get_client()
        params = self._translate_order_to_angel(order_data)
        return client.place_order(params)
        
    def _translate_order_to_angel(self, order_data: Dict) -> Dict:
        """Translate internal order dict to Angel One format."""
        # Simple translation for now
        return {
            "variety": order_data.get("variety", "NORMAL"),
            "tradingsymbol": order_data.get("symbol", ""),
            "symboltoken": order_data.get("symbol_token", ""),
            "transactiontype": "BUY" if order_data.get("side", "").upper() == "BUY" else "SELL",
            "exchange": order_data.get("exchange", "NSE"),
            "ordertype": order_data.get("type", "MARKET"),
            "producttype": order_data.get("product", "MIS"),
            "duration": order_data.get("validity", "DAY"),
            "price": str(order_data.get("price", 0)),
            "squareoff": "0",
            "stoploss": str(order_data.get("stop_loss", 0)),
            "quantity": str(order_data.get("quantity", 0))
        }
