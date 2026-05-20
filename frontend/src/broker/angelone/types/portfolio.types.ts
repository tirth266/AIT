export interface AngelHolding {
  tradingsymbol: string;
  exchange: string;
  isin: string;
  t1quantity: number;
  realisedpnl: number;
  unrealisedpnl: number;
  quantity: number;
  authorisedquantity: number;
  product: string;
  collateralquantity: number;
  collateraltype: string;
  haircut: number;
  averageprice: number;
  ltp: number;
  symboltoken: string;
  close: number;
  profitandloss: number;
  pnlpercentage: number;
}

export interface AngelPosition {
  exchange: string;
  symboltoken: string;
  tradingsymbol: string;
  symbolname: string;
  instrumenttype: string;
  pricedenominator: string;
  pricenumerator: string;
  strikeprice: string;
  optiontype: string;
  expirydate: string;
  lotsize: string;
  cfbuyqty: string;
  cfsellqty: string;
  cfbuyamount: string;
  cfsellamount: string;
  buyqty: string;
  sellqty: string;
  buyamount: string;
  sellamount: string;
  pnl: string;
  realisedpnl: string;
  unrealisedpnl: string;
  ltp: string;
  close: string;
  avgprice: string;
  buyavgprice: string;
  sellavgprice: string;
  netqty: string;
  netamount: string;
  totalbuyvalue: string;
  totalsellvalue: string;
  netvalue: string;
  totalbuyavgprice: string;
  totalsellavgprice: string;
}

export interface AngelFunds {
  net: string;
  availablecash: string;
  availableintradaypayin: string;
  availablelimitmargin: string;
  collateral: string;
  m2munrealized: string;
  m2mrealized: string;
  utiliseddebits: string;
  utilisedspan: string;
  utilisedoptionpremium: string;
  utilisedholdingsales: string;
  utilisedexposure: string;
  utilisedturnover: string;
  utilisedpayout: string;
}
