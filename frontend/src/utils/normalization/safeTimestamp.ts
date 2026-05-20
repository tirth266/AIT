/**
 * Safely normalizes timestamps to ISO strings.
 * Handles Date objects, numbers (ms), and strings.
 */
export const safeTimestamp = (value: unknown, fallback = new Date().toISOString()): string => {
  if (!value) return fallback;

  try {
    const date = new Date(value as any);
    if (isNaN(date.getTime())) {
      return fallback;
    }
    return date.toISOString();
  } catch {
    return fallback;
  }
};

/**
 * Returns a Unix timestamp (ms) safely.
 */
export const safeUnixTimestamp = (value: unknown, fallback = Date.now()): number => {
  if (!value) return fallback;

  try {
    const date = new Date(value as any);
    if (isNaN(date.getTime())) {
      return fallback;
    }
    return date.getTime();
  } catch {
    return fallback;
  }
};
