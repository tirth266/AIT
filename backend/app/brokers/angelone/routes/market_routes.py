from fastapi import APIRouter, HTTPException
from ..services.market_service import MarketService
from ..models.market_models import LTPRequest, HistoricDataRequest

router = APIRouter(prefix="/api/broker/angel/market", tags=["AngelOne Market"])
market_service = MarketService()

@router.post("/ltp")
async def get_ltp(request: LTPRequest):
    try:
        data = await market_service.get_ltp(request)
        return data['data']
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/historical")
async def get_historical_data(request: HistoricDataRequest):
    try:
        data = await market_service.get_historical_data(request)
        return data['data']
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
