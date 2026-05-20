export type OrderStatus = 'NEW' | 'VALIDATED' | 'OPEN' | 'PARTIALLY_FILLED' | 'FILLED' | 'CANCELLED' | 'REJECTED' | 'EXPIRED';
export type OrderType = 'MARKET' | 'LIMIT' | 'SL' | 'SL-M';
export type TransactionType = 'BUY' | 'SELL';
export type ProductType = 'MIS' | 'CNC' | 'NRML';
export type Exchange = 'NSE' | 'BSE';
export type TradingMode = 'paper' | 'live';
export type Validity = 'DAY' | 'IOC' | 'GTD' | 'GTC';

export interface Order {
  order_id: string;
  user_id: string;
  strategy_id?: string;
  
  symbol: string;
  exchange: Exchange;
  order_type: OrderType;
  product_type: ProductType;
  transaction_type: TransactionType;
  
  quantity: number;
  filled_quantity: number;
  cancelled_quantity: number;
  
  price: number;
  trigger_price: number;
  average_price: number;
  
  status: OrderStatus;
  validity: Validity;
  mode: TradingMode;
  
  brokerage: number;
  taxes: number;
  pnl: number;
  
  disclosed_quantity: number;
  order_tag: string;
  comments: string;
  source: string;
  
  parent_order_id?: string;
  
  created_at: string;
  updated_at: string;
  filled_at?: string;
  cancelled_at?: string;
  rejected_reason?: string;
}

export interface CreateOrderRequest {
  symbol: string;
  exchange?: Exchange;
  transaction_type: TransactionType;
  order_type?: OrderType;
  quantity: number;
  price?: number;
  trigger_price?: number;
  product_type?: ProductType;
  validity?: Validity;
  mode?: TradingMode;
  disclosed_quantity?: number;
  strategy_id?: string;
  order_tag?: string;
  comments?: string;
}

export type PositionStatus = 'OPEN' | 'CLOSED';

export interface Position {
  position_id: string;
  user_id: string;
  strategy_id?: string;
  
  symbol: string;
  exchange: Exchange;
  product_type: ProductType;
  
  quantity: number;
  closed_quantity: number;
  
  entry_price: number;
  average_price: number;
  current_price: number;
  
  realized_pnl: number;
  unrealized_pnl: number;
  day_pnl: number;
  
  stop_loss?: number;
  take_profit?: number;
  
  mode: TradingMode;
  status: PositionStatus;
  
  opened_at?: string;
  closed_at?: string;
  mtm_updated_at?: string;
}

export interface Trade {
  trade_id: string;
  user_id: string;
  order_id: string;
  position_id?: string;
  strategy_id?: string;
  
  symbol: string;
  exchange: Exchange;
  transaction_type: TransactionType;
  
  quantity: number;
  price: number;
  value: number;
  
  brokerage: number;
  stt: number;
  gst: number;
  stamp_duty: number;
  other_charges: number;
  
  pnl: number;
  pnl_percent: number;
  
  execution_time?: string;
  mode: TradingMode;
}

export interface MarginInfo {
  user_id: string;
  total_margin: number;
  used_margin: number;
  available_margin: number;
  blocked_margin: number;
  intraday_buying_power: number;
  cash_balance: number;
  holdings_value: number;
  position_margins: Record<string, number>;
  timestamp: string;
}

export interface PnLData {
  total_pnl: number;
  realized_pnl: number;
  unrealized_pnl: number;
  day_pnl: number;
  mode: TradingMode;
  timestamp: string;
}

export interface DayPnL {
  day_pnl: number;
  buy_value: number;
  sell_value: number;
  brokerage: number;
  taxes: number;
  trades_count: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
}

export interface Portfolio {
  mode: TradingMode;
  cash_balance: number;
  holdings: HoldingsSummary;
  intraday: IntradaySummary;
  pnl: PnLData;
  margin: MarginInfo;
  exposure: ExposureData;
  timestamp: string;
}

export interface HoldingsSummary {
  holdings?: Holding[];
  total_invested: number;
  total_current_value: number;
  total_value: number;
  total_cost: number;
  total_pnl: number;
  total_pnl_percent: number;
  pnl_percent: number;
  count: number;
}

export interface Holding {
  symbol: string;
  exchange?: Exchange;
  quantity: number;
  average_price: number;
  avg_buy_price: number;
  current_price: number;
  ltp: number;
  value: number;
  current_value: number;
  cost: number;
  pnl: number;
  pnl_percent: number;
  day_change: number;
  day_change_percent: number;
}

export interface IntradaySummary {
  trades_count: number;
  buy_trades: number;
  sell_trades: number;
  total_buy_value: number;
  total_sell_value: number;
  brokerage: number;
  taxes: number;
  day_pnl: number;
  symbols_traded: string[];
  unique_symbols: number;
}

export interface ExposureData {
  total_exposure: number;
  single_stock_exposure: Record<string, number>;
  position_count: number;
}

export interface MarketQuote {
  symbol: string;
  last_price: number;
  bid: number;
  ask: number;
  bid_quantity: number;
  ask_quantity: number;
  volume: number;
  timestamp: string;
}

export interface MarketDepth {
  symbol: string;
  bid_prices: number[];
  bid_quantities: number[];
  ask_prices: number[];
  ask_quantities: number[];
  last_price: number;
  volume: number;
  timestamp: string;
}

export interface RiskCheckResult {
  check_type: string;
  action: 'ALLOW' | 'WARN' | 'BLOCK';
  message: string;
  details: Record<string, unknown>;
}

export interface OrderValidationResponse {
  allowed: boolean;
  checks: RiskCheckResult[];
}

export interface ReconciliationResult {
  user_id: string;
  is_balanced: boolean;
  trade_reconciliation: {
    is_balanced: boolean;
    discrepancies: Array<{ type: string; [key: string]: unknown }>;
  };
  pnl_reconciliation: {
    is_balained: boolean;
    discrepancies: Array<{ type: string; [key: string]: unknown }>;
  };
  margin_reconciliation: {
    is_balanced: boolean;
    discrepancies: Array<{ type: string; [key: string]: unknown }>;
  };
  total_discrepancies: number;
  timestamp: string;
}

export interface ExecutionEvent {
  event: 'order_created' | 'order_filled' | 'order_cancelled' | 'order_rejected' | 'position_update' | 'pnl_update' | 'margin_update' | 'trade_executed';
  data: unknown;
  timestamp: string;
}