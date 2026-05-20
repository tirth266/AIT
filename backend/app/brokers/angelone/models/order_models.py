from pydantic import BaseModel
from typing import Optional, Literal

class PlaceOrderRequest(BaseModel):
    variety: Literal["NORMAL", "STOPLOSS", "AMO", "ROBO"]
    tradingsymbol: str
    symboltoken: str
    transactiontype: Literal["BUY", "SELL"]
    exchange: Literal["NSE", "BSE", "NFO", "BFO", "CDS", "MCX"]
    ordertype: Literal["MARKET", "LIMIT", "STOPLOSS_LIMIT", "STOPLOSS_MARKET"]
    producttype: Literal["DELIVERY", "CARRYFORWARD", "MARGIN", "INTRADAY", "BO"]
    duration: Literal["DAY", "IOC"]
    price: Optional[float] = None
    squareoff: Optional[float] = None
    stoploss: Optional[float] = None
    quantity: int
    triggerprice: Optional[float] = None

class ModifyOrderRequest(BaseModel):
    orderid: str
    variety: Literal["NORMAL", "STOPLOSS", "AMO", "ROBO"]
    tradingsymbol: str
    symboltoken: str
    exchange: Literal["NSE", "BSE", "NFO", "BFO", "CDS", "MCX"]
    ordertype: Literal["MARKET", "LIMIT", "STOPLOSS_LIMIT", "STOPLOSS_MARKET"]
    producttype: Literal["DELIVERY", "CARRYFORWARD", "MARGIN", "INTRADAY", "BO"]
    duration: Literal["DAY", "IOC"]
    price: Optional[float] = None
    quantity: Optional[int] = None
    triggerprice: Optional[float] = None

class CancelOrderRequest(BaseModel):
    orderid: str
    variety: Literal["NORMAL", "STOPLOSS", "AMO", "ROBO"]

class OrderResponse(BaseModel):
    orderid: str
    script: Optional[str] = None
    message: Optional[str] = None
