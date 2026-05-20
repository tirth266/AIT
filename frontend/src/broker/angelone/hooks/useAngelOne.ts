import { useEffect, useCallback } from 'react';
import { useAngelAuthStore } from '../store/angelAuth.store';
import { useAngelOrdersStore } from '../store/angelOrders.store';
import { useAngelMarketStore } from '../store/angelMarket.store';
import { AngelWebsocketManager } from '../websocket';

export function useAngelOne() {
  const { isAuthenticated, profile, fetchProfile } = useAngelAuthStore();
  const { fetchOrders, fetchPortfolio, fetchFunds } = useAngelOrdersStore();
  const { updateTick } = useAngelMarketStore();

  useEffect(() => {
    if (isAuthenticated && !profile) {
      fetchProfile();
    }
  }, [isAuthenticated, profile, fetchProfile]);

  const refreshAll = useCallback(async () => {
    if (isAuthenticated) {
      await Promise.all([
        fetchOrders(),
        fetchPortfolio(),
        fetchFunds()
      ]);
    }
  }, [isAuthenticated, fetchOrders, fetchPortfolio, fetchFunds]);

  return {
    isAuthenticated,
    profile,
    refreshAll
  };
}

export function useAngelOneSocket() {
  const { updateTick } = useAngelMarketStore();
  
  useEffect(() => {
    const wsManager = new AngelWebsocketManager(updateTick);
    wsManager.connect();
    
    return () => {
      wsManager.disconnect();
    };
  }, [updateTick]);
}
