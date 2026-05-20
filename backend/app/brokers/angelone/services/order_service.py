from typing import Dict, Any
from ..api.client import get_client
from ..models.order_models import PlaceOrderRequest, ModifyOrderRequest, CancelOrderRequest
from ..utils.logger import get_logger
from ..utils.retry import async_retry
from ..utils.rate_limiter import limiter
from ..exceptions import OrderException

logger = get_logger(__name__)

class OrderService:
    def __init__(self):
        self.client_wrapper = get_client()

    @async_retry(retries=3, delay=1.0)
    async def place_order(self, request: PlaceOrderRequest) -> dict:
        await limiter.acquire()
        try:
            # Drop None values to avoid API errors
            order_params = {k: v for k, v in request.dict().items() if v is not None}
            data = await self.client_wrapper.execute_async(
                self.client_wrapper.smart_api.placeOrder,
                order_params
            )
            if data.get('status') is False:
                raise OrderException(data.get('message'))
            return data
        except Exception as e:
            logger.error(f"Failed to place order: {str(e)}")
            raise OrderException(str(e))

    @async_retry(retries=3, delay=1.0)
    async def modify_order(self, request: ModifyOrderRequest) -> dict:
        await limiter.acquire()
        try:
            order_params = {k: v for k, v in request.dict().items() if v is not None}
            data = await self.client_wrapper.execute_async(
                self.client_wrapper.smart_api.modifyOrder,
                order_params
            )
            if data.get('status') is False:
                raise OrderException(data.get('message'))
            return data
        except Exception as e:
            logger.error(f"Failed to modify order: {str(e)}")
            raise OrderException(str(e))

    @async_retry(retries=3, delay=1.0)
    async def cancel_order(self, request: CancelOrderRequest) -> dict:
        await limiter.acquire()
        try:
            data = await self.client_wrapper.execute_async(
                self.client_wrapper.smart_api.cancelOrder,
                request.orderid,
                request.variety
            )
            if data.get('status') is False:
                raise OrderException(data.get('message'))
            return data
        except Exception as e:
            logger.error(f"Failed to cancel order: {str(e)}")
            raise OrderException(str(e))

    @async_retry(retries=3, delay=1.0)
    async def get_order_book(self) -> dict:
        await limiter.acquire()
        try:
            data = await self.client_wrapper.execute_async(
                self.client_wrapper.smart_api.orderBook
            )
            return data
        except Exception as e:
            logger.error(f"Failed to fetch order book: {str(e)}")
            raise OrderException(str(e))

    @async_retry(retries=3, delay=1.0)
    async def get_trade_book(self) -> dict:
        await limiter.acquire()
        try:
            data = await self.client_wrapper.execute_async(
                self.client_wrapper.smart_api.tradeBook
            )
            return data
        except Exception as e:
            logger.error(f"Failed to fetch trade book: {str(e)}")
            raise OrderException(str(e))
