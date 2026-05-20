import asyncio
from ..utils.logger import get_logger

logger = get_logger(__name__)

class ReconnectManager:
    """
    Handles exponential backoff reconnection logic.
    """
    def __init__(self, ws_manager, max_attempts=10, base_delay=2.0, max_delay=60.0):
        self.ws_manager = ws_manager
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.attempts = 0
        self._task = None
        self._active = False

    def trigger_reconnect(self):
        if self._active:
            return
        logger.info("Triggering automatic reconnection sequence.")
        self._active = True
        self._task = asyncio.create_task(self._reconnect_loop())

    async def _reconnect_loop(self):
        while self.attempts < self.max_attempts and self._active and not self.ws_manager.is_connected:
            delay = min(self.base_delay * (2 ** self.attempts), self.max_delay)
            logger.info(f"Reconnecting in {delay} seconds (Attempt {self.attempts + 1}/{self.max_attempts})...")
            await asyncio.sleep(delay)
            
            self.attempts += 1
            try:
                # Re-fetch session / auth if needed here, or just connect
                self.ws_manager.connect()
                # Wait briefly to let connection establish
                await asyncio.sleep(5)
                if self.ws_manager.is_connected:
                    logger.info("Reconnection successful.")
                    self.reset()
                    break
            except Exception as e:
                logger.error(f"Reconnection attempt failed: {e}")

        if not self.ws_manager.is_connected and self.attempts >= self.max_attempts:
            logger.error("Max reconnection attempts reached. WebSocket remains disconnected.")
            self._active = False

    def reset(self):
        self.attempts = 0
        self._active = False
        if self._task and not self._task.done():
            self._task.cancel()

    def stop(self):
        self._active = False
        if self._task and not self._task.done():
            self._task.cancel()
