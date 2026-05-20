import type { WSEvent } from '../../types';
import { safeTimestamp } from './safeTimestamp';
import { safeString } from './safeString';

/**
 * Normalizes raw websocket events.
 */
export const normalizeWebsocketEvent = (raw: any): WSEvent => {
  return {
    event: safeString(raw.event, 'UNKNOWN'),
    data: raw.data || {},
    timestamp: safeTimestamp(raw.timestamp),
  };
};
