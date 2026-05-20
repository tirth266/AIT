import type { Position } from '../../types';
import { safeNumber } from './safeNumber';
import { safeString, normalizeSymbol } from './safeString';
import { safeTimestamp } from './safeTimestamp';
import { 
  normalizeExchange, 
  normalizeProductType, 
  normalizeTradingMode, 
  normalizePositionStatus 
} from './enums';

/**
 * Normalizes raw position data from API or WebSockets.
 */
export const normalizePosition = (raw: any): Position => {
  return {
    position_id: safeString(raw.position_id || raw._id, 'UNKNOWN'),
    user_id: safeString(raw.user_id, ''),
    strategy_id: raw.strategy_id ? safeString(raw.strategy_id) : undefined,
    
    symbol: normalizeSymbol(raw.symbol),
    exchange: normalizeExchange(raw.exchange),
    product_type: normalizeProductType(raw.product_type || raw.product),
    
    quantity: safeNumber(raw.quantity),
    closed_quantity: safeNumber(raw.closed_quantity),
    
    entry_price: safeNumber(raw.entry_price || raw.avg_price),
    average_price: safeNumber(raw.average_price || raw.avg_price),
    current_price: safeNumber(raw.current_price || raw.ltp),
    
    realized_pnl: safeNumber(raw.realized_pnl || raw.pnl),
    unrealized_pnl: safeNumber(raw.unrealized_pnl),
    day_pnl: safeNumber(raw.day_pnl || raw.m2m),
    
    stop_loss: raw.stop_loss ? safeNumber(raw.stop_loss) : undefined,
    take_profit: raw.take_profit ? safeNumber(raw.take_profit) : undefined,
    
    mode: normalizeTradingMode(raw.mode),
    status: normalizePositionStatus(raw.status),
    
    opened_at: safeTimestamp(raw.opened_at),
    closed_at: raw.closed_at ? safeTimestamp(raw.closed_at) : undefined,
    mtm_updated_at: safeTimestamp(raw.mtm_updated_at || raw.last_updated),
  };
};

/**
 * Normalizes an array of positions.
 */
export const normalizePositions = (rawArray: any): Position[] => {
  if (!Array.isArray(rawArray)) return [];
  return rawArray.map(normalizePosition);
};
