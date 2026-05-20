from fastapi import APIRouter, HTTPException
from ..services.order_service import OrderService
from ..models.order_models import PlaceOrderRequest, ModifyOrderRequest, CancelOrderRequest, OrderResponse

router = APIRouter(prefix="/api/broker/angel/orders", tags=["AngelOne Orders"])
order_service = OrderService()

@router.post("/", response_model=OrderResponse)
async def place_order(request: PlaceOrderRequest):
    try:
        data = await order_service.place_order(request)
        return {"orderid": data['data']['orderid'], "script": data['data'].get('script'), "message": data.get('message')}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/", response_model=OrderResponse)
async def modify_order(request: ModifyOrderRequest):
    try:
        data = await order_service.modify_order(request)
        return {"orderid": data['data']['orderid'], "message": data.get('message')}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/", response_model=OrderResponse)
async def cancel_order(request: CancelOrderRequest):
    try:
        data = await order_service.cancel_order(request)
        return {"orderid": data['data']['orderid'], "message": data.get('message')}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/")
async def get_order_book():
    try:
        data = await order_service.get_order_book()
        return data['data']
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/trades")
async def get_trade_book():
    try:
        data = await order_service.get_trade_book()
        return data['data']
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
