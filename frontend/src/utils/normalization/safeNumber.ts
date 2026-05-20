/**
 * Safely converts any value to a number.
 * Prevents NaN propagation and handles null/undefined/malformed strings.
 */
export const safeNumber = (value: unknown, fallback = 0): number => {
  if (value === null || value === undefined || value === '') {
    return fallback;
  }

  if (typeof value === 'number') {
    return Number.isNaN(value) ? fallback : value;
  }

  const parsed = typeof value === 'string' ? parseFloat(value.replace(/,/g, '')) : Number(value);
  
  return Number.isNaN(parsed) ? fallback : parsed;
};

/**
 * Ensures a number is within a specific precision (useful for prices/quantities).
 */
export const safeFixed = (value: unknown, precision = 2, fallback = 0): number => {
  const num = safeNumber(value, fallback);
  return parseFloat(num.toFixed(precision));
};
