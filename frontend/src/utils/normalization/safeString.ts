/**
 * Safely converts any value to a string.
 * Handles null/undefined and provides a fallback.
 */
export const safeString = (value: unknown, fallback = ''): string => {
  if (value === null || value === undefined) {
    return fallback;
  }

  if (typeof value === 'string') {
    return value.trim();
  }

  return String(value).trim();
};

/**
 * Standardizes symbols (usually uppercase, trimmed).
 */
export const normalizeSymbol = (symbol: unknown, fallback = 'UNKNOWN'): string => {
  return safeString(symbol, fallback).toUpperCase();
};
