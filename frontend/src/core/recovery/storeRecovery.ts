import { 
  useTradingEngineStore, 
  useMarketStore, 
  useDashboardStore, 
  useUIStore,
  useNotificationStore,
  useSettingsStore
} from '../../store';

export class StoreRecovery {
  /**
   * Performs a surgical reset of stores.
   * Purges runtime data but attempts to preserve user configuration.
   */
  public static async recover(): Promise<boolean> {
    console.log('[RECOVERY] Initiating store recovery sequence...');

    try {
      // 1. Clear runtime transactional data
      useTradingEngineStore.getState().reset();
      useMarketStore.getState().reset();
      useDashboardStore.getState().reset();
      
      // 2. Clear volatile UI state but keep toasts
      const uiStore = useUIStore.getState();
      uiStore.setLoading(false);
      
      // 3. Clear error states
      useNotificationStore.getState().clearNotifications('read');
      
      // 4. Re-initialize essential data
      await Promise.all([
        useSettingsStore.getState().fetchSettings(),
        useMarketStore.getState().initializeMarketData()
      ]);

      console.log('[RECOVERY] Store state re-synchronized.');
      return true;
    } catch (error) {
      console.error('[RECOVERY] Store recovery failed:', error);
      // Hard fallback: total reset
      this.hardReset();
      return false;
    }
  }

  /**
   * Destructive reset for critical corruption.
   */
  public static hardReset(): void {
    console.warn('[RECOVERY] Executing HARD RESET of all local state.');
    sessionStorage.clear();
    localStorage.removeItem('trading-engine-storage');
    localStorage.removeItem('market-storage');
    window.location.reload();
  }
}
