import type { Trade } from '../../types';
import { safeNumber } from './safeNumber';
import { safeString, normalizeSymbol } from './safeString';
import { safeTimestamp } from './safeTimestamp';
import { 
  normalizeExchange, 
  normalizeTradingMode, 
  normalizeTransactionType
} from './enums';

/**
 * Normalizes raw trade data.
 */
export const normalizeTrade = (raw: any): Trade => {
  return {
    trade_id: safeString(raw.trade_id || raw._id, 'UNKNOWN'),
    user_id: safeString(raw.user_id, ''),
    order_id: safeString(raw.order_id, ''),
    position_id: raw.position_id ? safeString(raw.position_id) : undefined,
    strategy_id: raw.strategy_id ? safeString(raw.strategy_id) : undefined,
    
    symbol: normalizeSymbol(raw.symbol),
    exchange: normalizeExchange(raw.exchange),
    transaction_type: normalizeTransactionType(raw.transaction_type || raw.side),
    
    quantity: safeNumber(raw.quantity),
    price: safeNumber(raw.price || raw.entry_price),
    value: safeNumber(raw.value),
    
    brokerage: safeNumber(raw.brokerage),
    stt: safeNumber(raw.stt),
    gst: safeNumber(raw.gst),
    stamp_duty: safeNumber(raw.stamp_duty),
    other_charges: safeNumber(raw.other_charges || raw.total_charges),
    
    pnl: safeNumber(raw.pnl),
    pnl_percent: safeNumber(raw.pnl_percent),
    
    execution_time: safeTimestamp(raw.execution_time || raw.trade_timestamp || raw.entry_time),
    mode: normalizeTradingMode(raw.mode),
  };
};

/**
 * Normalizes an array of trades.
 */
export const normalizeTrades = (rawArray: any): Trade[] => {
  if (!Array.isArray(rawArray)) return [];
  return rawArray.map(normalizeTrade);
};
