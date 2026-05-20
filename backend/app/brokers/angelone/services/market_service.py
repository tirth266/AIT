from typing import Dict, Any
from ..api.client import get_client
from ..models.market_models import LTPRequest, HistoricDataRequest
from ..utils.logger import get_logger
from ..utils.retry import async_retry
from ..utils.rate_limiter import limiter
from ..exceptions import AngelOneException

logger = get_logger(__name__)

class MarketService:
    def __init__(self):
        self.client_wrapper = get_client()

    @async_retry(retries=3, delay=1.0)
    async def get_ltp(self, request: LTPRequest) -> dict:
        await limiter.acquire()
        try:
            data = await self.client_wrapper.execute_async(
                self.client_wrapper.smart_api.ltpData,
                request.exchange,
                request.tradingsymbol,
                request.symboltoken
            )
            if data.get('status') is False:
                raise AngelOneException(data.get('message'))
            return data
        except Exception as e:
            logger.error(f"Failed to fetch LTP: {str(e)}")
            raise AngelOneException(str(e))

    @async_retry(retries=3, delay=1.0)
    async def get_historical_data(self, request: HistoricDataRequest) -> dict:
        await limiter.acquire()
        try:
            data = await self.client_wrapper.execute_async(
                self.client_wrapper.smart_api.getCandleData,
                request.dict()
            )
            if data.get('status') is False:
                raise AngelOneException(data.get('message'))
            return data
        except Exception as e:
            logger.error(f"Failed to fetch historical data: {str(e)}")
            raise AngelOneException(str(e))
