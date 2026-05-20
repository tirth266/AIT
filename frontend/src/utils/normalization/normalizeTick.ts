import type { MarketTickData } from '../../types';
import { safeNumber } from './safeNumber';
import { safeString, normalizeSymbol } from './safeString';
import { safeTimestamp } from './safeTimestamp';

/**
 * Normalizes raw tick data from WebSockets or API.
 */
export const normalizeTick = (raw: any): MarketTickData => {
  return {
    symbol: normalizeSymbol(raw.symbol),
    last_price: safeNumber(raw.last_price || raw.ltp),
    bid: safeNumber(raw.bid),
    ask: safeNumber(raw.ask),
    bid_quantity: safeNumber(raw.bid_quantity),
    ask_quantity: safeNumber(raw.ask_quantity),
    volume: safeNumber(raw.volume),
    timestamp: safeTimestamp(raw.timestamp),
    
    // Optional/Extended fields
    change: safeNumber(raw.change),
    change_percent: safeNumber(raw.change_percent),
    open: safeNumber(raw.open),
    high: safeNumber(raw.high),
    low: safeNumber(raw.low),
    close: safeNumber(raw.close || raw.prev_close),
  };
};

/**
 * Normalizes a record of ticks.
 */
export const normalizeTicks = (rawMap: any): Record<string, MarketTickData> => {
  const result: Record<string, MarketTickData> = {};
  if (!rawMap || typeof rawMap !== 'object') return result;

  Object.entries(rawMap).forEach(([symbol, tick]) => {
    result[normalizeSymbol(symbol)] = normalizeTick(tick);
  });

  return result;
};
