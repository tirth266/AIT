import type { 
  OrderStatus, 
  OrderType, 
  TransactionType, 
  ProductType, 
  Exchange, 
  TradingMode, 
  PositionStatus 
} from '../../types';

export const normalizeOrderStatus = (status: unknown): OrderStatus => {
  const s = String(status).toUpperCase();
  const valid: OrderStatus[] = ['NEW', 'VALIDATED', 'OPEN', 'PARTIALLY_FILLED', 'FILLED', 'CANCELLED', 'REJECTED', 'EXPIRED'];
  return valid.includes(s as OrderStatus) ? (s as OrderStatus) : 'REJECTED';
};

export const normalizeOrderType = (type: unknown): OrderType => {
  const t = String(type).toUpperCase();
  const valid: OrderType[] = ['MARKET', 'LIMIT', 'SL', 'SL-M'];
  return valid.includes(t as OrderType) ? (t as OrderType) : 'MARKET';
};

export const normalizeTransactionType = (side: unknown): TransactionType => {
  const s = String(side).toUpperCase();
  if (s === 'BUY' || s === 'SELL') return s;
  return 'BUY';
};

export const normalizeProductType = (product: unknown): ProductType => {
  const p = String(product).toUpperCase();
  const valid: ProductType[] = ['MIS', 'CNC', 'NRML'];
  return valid.includes(p as ProductType) ? (p as ProductType) : 'MIS';
};

export const normalizeExchange = (exchange: unknown): Exchange => {
  const e = String(exchange).toUpperCase();
  if (e === 'NSE' || e === 'BSE') return e;
  return 'NSE';
};

export const normalizeTradingMode = (mode: unknown): TradingMode => {
  const m = String(mode).toLowerCase();
  if (m === 'paper' || m === 'live') return m;
  return 'paper';
};

export const normalizePositionStatus = (status: unknown): PositionStatus => {
  const s = String(status).toUpperCase();
  if (s === 'OPEN' || s === 'CLOSED') return s;
  return 'CLOSED';
};
