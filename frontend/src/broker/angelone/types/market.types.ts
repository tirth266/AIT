export interface AngelLTPResponse {
  exchange: string;
  tradingsymbol: string;
  symboltoken: string;
  ltp: number;
}

export interface AngelCandleRequest {
  exchange: string;
  symboltoken: string;
  interval: 'ONE_MINUTE' | 'THREE_MINUTE' | 'FIVE_MINUTE' | 'TEN_MINUTE' | 'FIFTEEN_MINUTE' | 'THIRTY_MINUTE' | 'ONE_HOUR' | 'ONE_DAY';
  fromdate: string;
  todate: string;
}

export type AngelCandleData = [string, number, number, number, number, number];

export interface AngelTick {
  t: string; // type
  e: string; // exchange
  tk: string; // token
  ltp?: string;
  ltq?: string;
  ltt?: string;
  v?: string;
  atp?: string;
  bp?: string;
  bq?: string;
  sp?: string;
  sq?: string;
  c?: string;
  h?: string;
  lo?: string;
}

export interface AngelWebsocketRequest {
  action: 'subscribe' | 'unsubscribe';
  params: {
    mode: 1 | 2 | 3;
    tokenList: Array<{
      exchangeType: number;
      tokens: string[];
    }>;
  };
}
