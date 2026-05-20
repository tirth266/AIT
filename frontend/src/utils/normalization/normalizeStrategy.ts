import type { Strategy } from '../../types';
import { safeNumber } from './safeNumber';
import { safeString, normalizeSymbol } from './safeString';
import { safeTimestamp } from './safeTimestamp';

/**
 * Normalizes raw strategy data from API.
 */
export const normalizeStrategy = (raw: any): Strategy => {
  return {
    strategy_id: safeString(raw?.strategy_id || raw?._id),
    name: safeString(raw?.name || raw?.strategy_name),
    symbol: normalizeSymbol(raw?.symbol),
    exchange: safeString(raw?.exchange, 'NSE'),
    timeframe: safeString(raw?.timeframe, '5m'),
    mode: (raw?.mode || 'PAPER').toUpperCase() as any,
    status: (raw?.status || 'PAUSED').toUpperCase() as any,
    parameters: raw?.parameters || {},
    risk_settings: {
      max_position_size: safeNumber(raw?.risk_settings?.max_position_size),
      stop_loss_percent: safeNumber(raw?.risk_settings?.stop_loss_percent),
      target_percent: safeNumber(raw?.risk_settings?.target_percent),
      max_daily_loss: safeNumber(raw?.risk_settings?.max_daily_loss),
    },
    last_run: raw?.last_run || (raw?.last_run_at ? safeTimestamp(raw.last_run_at) : undefined),
    created_at: safeTimestamp(raw?.created_at),
    updated_at: raw?.updated_at ? safeTimestamp(raw.updated_at) : undefined,
  };
};

/**
 * Normalizes an array of strategies.
 */
export const normalizeStrategies = (rawArray: any): Strategy[] => {
  if (!Array.isArray(rawArray)) return [];
  return rawArray.map(normalizeStrategy);
};
