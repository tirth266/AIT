import { wsManager } from '../../websocket/websocket.manager';

export class WebSocketRecovery {
  private static recoveryInProgress = false;

  public static async recover(): Promise<boolean> {
    if (this.recoveryInProgress) return true;

    console.log('[RECOVERY] Initializing WebSocket recovery sequence...');
    this.recoveryInProgress = true;

    try {
      // 1. Force disconnect if currently hanging
      wsManager.disconnect();

      // 2. Wait for short cooldown
      await new Promise(resolve => setTimeout(resolve, 500));

      // 3. Trigger new connection
      // Token management should be handled by the auth layer or passed here
      wsManager.connect();

      // 4. Wait for connection or timeout
      const connected = await this.waitForConnection(5000);
      
      if (connected) {
        console.log('[RECOVERY] WebSocket connection restored successfully.');
        return true;
      }
      
      console.error('[RECOVERY] WebSocket restoration timed out.');
      return false;
    } catch (error) {
      console.error('[RECOVERY] Critical failure during WS restoration:', error);
      return false;
    } finally {
      this.recoveryInProgress = false;
    }
  }

  private static waitForConnection(timeout: number): Promise<boolean> {
    return new Promise((resolve) => {
      if (wsManager.isConnected()) return resolve(true);

      const checkInterval = setInterval(() => {
        if (wsManager.isConnected()) {
          clearInterval(checkInterval);
          clearTimeout(failTimeout);
          resolve(true);
        }
      }, 100);

      const failTimeout = setTimeout(() => {
        clearInterval(checkInterval);
        resolve(false);
      }, timeout);
    });
  }
}
