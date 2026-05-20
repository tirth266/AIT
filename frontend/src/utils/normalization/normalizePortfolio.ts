import type { Portfolio, PnLData, MarginInfo, DayPnL } from '../../types';
import { safeNumber } from './safeNumber';
import { safeString } from './safeString';
import { safeTimestamp } from './safeTimestamp';
import { normalizeTradingMode } from './enums';

/**
 * Normalizes raw P&L data.
 */
export const normalizePnL = (raw: any): PnLData => {
  return {
    total_pnl: safeNumber(raw?.total_pnl),
    realized_pnl: safeNumber(raw?.realized_pnl),
    unrealized_pnl: safeNumber(raw?.unrealized_pnl),
    day_pnl: safeNumber(raw?.day_pnl),
    mode: normalizeTradingMode(raw?.mode),
    timestamp: safeTimestamp(raw?.timestamp),
  };
};

/**
 * Normalizes raw Margin data.
 */
export const normalizeMargin = (raw: any): MarginInfo => {
  return {
    user_id: safeString(raw?.user_id || ''),
    total_margin: safeNumber(raw?.total_margin),
    used_margin: safeNumber(raw?.used_margin),
    available_margin: safeNumber(raw?.available_margin),
    blocked_margin: safeNumber(raw?.blocked_margin),
    intraday_buying_power: safeNumber(raw?.intraday_buying_power),
    cash_balance: safeNumber(raw?.cash_balance),
    holdings_value: safeNumber(raw?.holdings_value),
    position_margins: raw?.position_margins || {},
    timestamp: safeTimestamp(raw?.timestamp),
  };
};

/**
 * Normalizes raw Day P&L data.
 */
export const normalizeDayPnL = (raw: any): DayPnL => {
  return {
    day_pnl: safeNumber(raw?.day_pnl),
    buy_value: safeNumber(raw?.buy_value),
    sell_value: safeNumber(raw?.sell_value),
    brokerage: safeNumber(raw?.brokerage),
    taxes: safeNumber(raw?.taxes),
    trades_count: safeNumber(raw?.trades_count),
    winning_trades: safeNumber(raw?.winning_trades),
    losing_trades: safeNumber(raw?.losing_trades),
    win_rate: safeNumber(raw?.win_rate),
  };
};

/**
 * Normalizes raw portfolio data.
 */
export const normalizePortfolio = (raw: any): Portfolio => {
  return {
    mode: normalizeTradingMode(raw?.mode),
    cash_balance: safeNumber(raw?.cash_balance || raw?.cash),
    holdings: {
      holdings: Array.isArray(raw?.holdings?.holdings) ? raw.holdings.holdings : [],
      total_value: safeNumber(raw?.holdings?.total_value),
      total_cost: safeNumber(raw?.holdings?.total_cost),
      total_pnl: safeNumber(raw?.holdings?.total_pnl),
      pnl_percent: safeNumber(raw?.holdings?.pnl_percent),
      count: safeNumber(raw?.holdings?.count),
    },
    intraday: {
      trades_count: safeNumber(raw?.intraday?.trades_count),
      buy_trades: safeNumber(raw?.intraday?.buy_trades),
      sell_trades: safeNumber(raw?.intraday?.sell_trades),
      total_buy_value: safeNumber(raw?.intraday?.total_buy_value),
      total_sell_value: safeNumber(raw?.intraday?.total_sell_value),
      brokerage: safeNumber(raw?.intraday?.brokerage),
      taxes: safeNumber(raw?.intraday?.taxes),
      day_pnl: safeNumber(raw?.intraday?.day_pnl),
      symbols_traded: Array.isArray(raw?.intraday?.symbols_traded) ? raw.intraday.symbols_traded : [],
      unique_symbols: safeNumber(raw?.intraday?.unique_symbols),
    },
    pnl: normalizePnL(raw?.pnl),
    margin: normalizeMargin(raw?.margin),
    exposure: {
      total_exposure: safeNumber(raw?.exposure?.total_exposure),
      single_stock_exposure: raw?.exposure?.single_stock_exposure || {},
      position_count: safeNumber(raw?.exposure?.position_count),
    },
    timestamp: safeTimestamp(raw?.timestamp),
  };
};
