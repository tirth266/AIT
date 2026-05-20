from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class LTPRequest(BaseModel):
    exchange: str
    tradingsymbol: str
    symboltoken: str

class LTPResponse(BaseModel):
    exchange: str
    tradingsymbol: str
    symboltoken: str
    open: float
    high: float
    low: float
    close: float
    ltp: float

class HistoricDataRequest(BaseModel):
    exchange: str
    symboltoken: str
    interval: str
    fromdate: str
    todate: str

class HistoricDataResponse(BaseModel):
    data: List[List[Any]]  # [timestamp, open, high, low, close, volume]
