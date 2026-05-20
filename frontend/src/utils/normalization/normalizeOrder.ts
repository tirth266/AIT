import type { Order } from '../../types';
import { safeNumber } from './safeNumber';
import { safeString, normalizeSymbol } from './safeString';
import { safeTimestamp } from './safeTimestamp';
import { 
  normalizeExchange, 
  normalizeProductType, 
  normalizeTradingMode, 
  normalizeOrderStatus,
  normalizeOrderType,
  normalizeTransactionType
} from './enums';

/**
 * Normalizes raw order data from API or WebSockets.
 */
export const normalizeOrder = (raw: any): Order => {
  return {
    order_id: safeString(raw.order_id, 'UNKNOWN'),
    user_id: safeString(raw.user_id, ''),
    strategy_id: raw.strategy_id ? safeString(raw.strategy_id) : undefined,
    
    symbol: normalizeSymbol(raw.symbol),
    exchange: normalizeExchange(raw.exchange),
    order_type: normalizeOrderType(raw.order_type || raw.type),
    product_type: normalizeProductType(raw.product_type || raw.product),
    transaction_type: normalizeTransactionType(raw.transaction_type || raw.side),
    
    quantity: safeNumber(raw.quantity),
    filled_quantity: safeNumber(raw.filled_quantity),
    cancelled_quantity: safeNumber(raw.cancelled_quantity),
    
    price: safeNumber(raw.price),
    trigger_price: safeNumber(raw.trigger_price),
    average_price: safeNumber(raw.average_price),
    
    status: normalizeOrderStatus(raw.status),
    validity: (raw.validity || 'DAY').toUpperCase() as any,
    mode: normalizeTradingMode(raw.mode),
    
    brokerage: safeNumber(raw.brokerage),
    taxes: safeNumber(raw.taxes),
    pnl: safeNumber(raw.pnl),
    
    disclosed_quantity: safeNumber(raw.disclosed_quantity),
    order_tag: safeString(raw.order_tag),
    comments: safeString(raw.comments),
    source: safeString(raw.source),
    
    parent_order_id: raw.parent_order_id ? safeString(raw.parent_order_id) : undefined,
    
    created_at: safeTimestamp(raw.created_at || raw.order_timestamp),
    updated_at: safeTimestamp(raw.updated_at || raw.order_timestamp),
    filled_at: raw.filled_at ? safeTimestamp(raw.filled_at) : undefined,
    cancelled_at: raw.cancelled_at ? safeTimestamp(raw.cancelled_at) : undefined,
    rejected_reason: raw.rejected_reason ? safeString(raw.rejected_reason) : undefined,
  };
};

/**
 * Normalizes an array of orders.
 */
export const normalizeOrders = (rawArray: any): Order[] => {
  if (!Array.isArray(rawArray)) return [];
  return rawArray.map(normalizeOrder);
};
