import type { Funds } from '../../types';
import { safeNumber } from './safeNumber';
import { safeString } from './safeString';
import { safeTimestamp } from './safeTimestamp';

/**
 * Normalizes raw funds data.
 */
export const normalizeFunds = (raw: any): Funds => {
  return {
    account_id: safeString(raw.account_id),
    broker: safeString(raw.broker),
    balance: {
      available_cash: safeNumber(raw.balance?.available_cash),
      used_margin: safeNumber(raw.balance?.used_margin),
      total_balance: safeNumber(raw.balance?.total_balance),
      currency: safeString(raw.balance?.currency, 'INR'),
    },
    margin: {
      available_margin: safeNumber(raw.margin?.available_margin),
      used_margin: safeNumber(raw.margin?.used_margin),
      span_margin: safeNumber(raw.margin?.span_margin),
      exposure_margin: safeNumber(raw.margin?.exposure_margin),
      total_margin_used: safeNumber(raw.margin?.total_margin_used),
    },
    limits: {
      daily_buy_power: safeNumber(raw.limits?.daily_buy_power),
      daily_sell_power: safeNumber(raw.limits?.daily_sell_power),
    },
    last_updated: safeTimestamp(raw.last_updated),
  };
};
