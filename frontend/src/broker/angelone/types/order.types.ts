export type AngelTransactionType = 'BUY' | 'SELL';
export type AngelOrderType = 'MARKET' | 'LIMIT' | 'STOPLOSS_LIMIT' | 'STOPLOSS_MARKET';
export type AngelProductType = 'DELIVERY' | 'CARRYFORWARD' | 'MARGIN' | 'INTRADAY' | 'BO' | 'CO';
export type AngelDuration = 'DAY' | 'IOC';
export type AngelExchange = 'NSE' | 'BSE' | 'NFO' | 'MCX' | 'NCDEX' | 'CDS';
export type AngelOrderStatus = 'COMPLETE' | 'REJECTED' | 'CANCELLED' | 'OPEN' | 'AFTER MARKET ORDER RECEIVED' | 'TRIGGER PENDING';

export interface AngelOrderRequest {
  variety: 'NORMAL' | 'STOPLOSS' | 'AMO' | 'ROBO';
  tradingsymbol: string;
  symboltoken: string;
  transactiontype: AngelTransactionType;
  exchange: AngelExchange;
  ordertype: AngelOrderType;
  producttype: AngelProductType;
  duration: AngelDuration;
  price: string;
  squareoff: string;
  stoploss: string;
  quantity: string;
  disclosedquantity: string;
  triggerprice: string;
}

export interface AngelOrderResponse {
  orderid: string;
  uniqueorderid: string;
}

export interface AngelOrderDetails {
  variety: string;
  ordertype: string;
  producttype: string;
  duration: string;
  price: number;
  triggerprice: number;
  quantity: string;
  disclosedquantity: string;
  squrroff: number;
  stoploss: number;
  trailingstoploss: number;
  tradingsymbol: string;
  transactiontype: string;
  exchange: string;
  symboltoken: string;
  instrumenttype: string;
  strikeprice: number;
  optiontype: string;
  expirydate: string;
  lotsize: string;
  cancelsize: string;
  averageprice: number;
  filledshares: string;
  unfilledshares: string;
  orderid: string;
  status: AngelOrderStatus;
  updatetime: string;
  exchtime: string;
  exchorderid: string;
  text: string;
}
