from fastapi import APIRouter, HTTPException
from ..services.portfolio_service import PortfolioService

router = APIRouter(prefix="/api/broker/angel/portfolio", tags=["AngelOne Portfolio"])
portfolio_service = PortfolioService()

@router.get("/holdings")
async def get_holdings():
    try:
        data = await portfolio_service.get_holdings()
        return data.get('data') or []
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/positions")
async def get_positions():
    try:
        data = await portfolio_service.get_positions()
        return data.get('data') or []
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/funds")
async def get_rms():
    try:
        data = await portfolio_service.get_rms()
        return data.get('data') or {}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
