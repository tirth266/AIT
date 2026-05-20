import asyncio
from typing import Dict, Any, Optional
from ..utils.logger import get_logger

logger = get_logger(__name__)

class TickParser:
    """
    Parses Angel One raw binary/json ticks into internal standard formats.
    """
    def parse(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        # Angel One SmartWebSocketV2 returns dicts directly if json, or binary strings.
        # Assuming the library decodes binary to dict:
        try:
            # Example response from Angel One V2:
            # {'subscription_mode': 1, 'exchange_type': 1, 'token': '2885', 'sequence_number': 1234, ...}
            if not isinstance(message, dict):
                return None
            
            token = message.get("token")
            if not token:
                return None
                
            parsed = {
                "symboltoken": token,
                "exchange_type": message.get("exchange_type"),
                "ltp": message.get("last_traded_price", 0.0) / 100.0 if message.get("last_traded_price") else None,
                "volume": message.get("volume_trade_for_the_day", 0),
                "timestamp": message.get("exchange_timestamp"),
                # Add depth, open, high, low if present depending on mode
            }
            return parsed
        except Exception as e:
            logger.error(f"Failed to parse tick: {e}")
            return None
