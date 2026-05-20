import { AppError } from './AppError';
import { ErrorCode } from './ErrorCodes';
import { WebSocketRecovery } from '../recovery/websocketRecovery';
import { StoreRecovery } from '../recovery/storeRecovery';
import { RouteRecovery } from '../recovery/routeRecovery';
import { ChunkRecovery } from '../recovery/chunkRecovery';

export class ErrorRecovery {
  private static recoveryAttempts: Record<string, number> = {};
  private static MAX_ATTEMPTS = 3;

  public static async recover(error: AppError): Promise<boolean> {
    const key = `${error.code}_${error.message}`;
    const attempts = this.recoveryAttempts[key] || 0;

    if (attempts >= this.MAX_ATTEMPTS) {
      console.error(`Recovery failed after ${attempts} attempts for ${error.code}`);
      return false;
    }

    this.recoveryAttempts[key] = attempts + 1;

    try {
      switch (error.code) {
        case ErrorCode.CHUNCK_LOAD_FAILURE:
          return await ChunkRecovery.recover();
        
        case ErrorCode.WEBSOCKET_DISCONNECTED:
        case ErrorCode.WEBSOCKET_CONNECTION_FAILED:
          return await WebSocketRecovery.recover();
        
        case ErrorCode.STORE_CORRUPTION:
        case ErrorCode.STATE_TRANSITION_ERROR:
          return await StoreRecovery.recover();
        
        case ErrorCode.ROUTE_ERROR:
          return await RouteRecovery.recover();
        
        case ErrorCode.NETWORK_ERROR:
          return await this.recoverNetwork();
        
        case ErrorCode.RENDER_FAILURE:
        case ErrorCode.WIDGET_CRASH:
          // Localized reset might be enough, but we can try a state purge if persistent
          if (attempts > 1) return await StoreRecovery.recover();
          return true;

        default:
          return false;
      }
    } catch (e) {
      console.error(`Exception during recovery execution:`, e);
      return false;
    }
  }

  private static async recoverNetwork(): Promise<boolean> {
    console.log('Waiting for network restoration...');
    return new Promise((resolve) => {
      if (window.navigator.onLine) return resolve(true);

      const handleOnline = () => {
        window.removeEventListener('online', handleOnline);
        resolve(true);
      };
      window.addEventListener('online', handleOnline);
      
      // Timeout after 10s if still offline
      setTimeout(() => {
        window.removeEventListener('online', handleOnline);
        resolve(false);
      }, 10000);
    });
  }
}
