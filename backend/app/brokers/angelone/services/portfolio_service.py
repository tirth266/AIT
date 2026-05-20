from typing import Dict, Any
from ..api.client import get_client
from ..utils.logger import get_logger
from ..utils.retry import async_retry
from ..utils.rate_limiter import limiter
from ..exceptions import AngelOneException

logger = get_logger(__name__)

class PortfolioService:
    def __init__(self):
        self.client_wrapper = get_client()

    @async_retry(retries=3, delay=1.0)
    async def get_holdings(self) -> dict:
        await limiter.acquire()
        try:
            data = await self.client_wrapper.execute_async(
                self.client_wrapper.smart_api.holding
            )
            if data.get('status') is False:
                raise AngelOneException(data.get('message'))
            return data
        except Exception as e:
            logger.error(f"Failed to fetch holdings: {str(e)}")
            raise AngelOneException(str(e))

    @async_retry(retries=3, delay=1.0)
    async def get_positions(self) -> dict:
        await limiter.acquire()
        try:
            data = await self.client_wrapper.execute_async(
                self.client_wrapper.smart_api.position
            )
            if data.get('status') is False:
                raise AngelOneException(data.get('message'))
            return data
        except Exception as e:
            logger.error(f"Failed to fetch positions: {str(e)}")
            raise AngelOneException(str(e))

    @async_retry(retries=3, delay=1.0)
    async def get_rms(self) -> dict:
        await limiter.acquire()
        try:
            data = await self.client_wrapper.execute_async(
                self.client_wrapper.smart_api.rmsLimit
            )
            if data.get('status') is False:
                raise AngelOneException(data.get('message'))
            return data
        except Exception as e:
            logger.error(f"Failed to fetch RMS: {str(e)}")
            raise AngelOneException(str(e))
