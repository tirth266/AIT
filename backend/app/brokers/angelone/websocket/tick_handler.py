import asyncio
from typing import Dict, Any
from ..utils.logger import get_logger
from .parser import TickParser

logger = get_logger(__name__)

class TickHandler:
    """
    Parses and routes raw tick data from Angel One WebSocket.
    """
    def __init__(self):
        self.parser = TickParser()
        self.subscribers = []  # List of internal async queues or callback functions

    def add_subscriber(self, callback):
        self.subscribers.append(callback)

    async def handle(self, raw_message: Dict[str, Any]):
        try:
            parsed_data = self.parser.parse(raw_message)
            if parsed_data:
                # Distribute parsed data to all internal systems (e.g., redis, kafka, or direct callbacks)
                for subscriber in self.subscribers:
                    await subscriber(parsed_data)
        except Exception as e:
            logger.error(f"Error handling tick: {e}", exc_info=True)
