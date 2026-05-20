import { useEffect, useCallback } from 'react';
import { angelMarketService } from '../services';
import { useAngelMarketStore } from '../store';
import { websocketApi } from '../api';

export const useAngelWebSocket = () => {
  const { liveTicks, updateTick } = useAngelMarketStore();

  useEffect(() => {
    let unsubscribe: (() => void) | null = null;

    const initWs = async () => {
      try {
        await angelMarketService.connectWebsocket();
        unsubscribe = websocketApi.onTick((data) => {
          updateTick(data);
        });
      } catch (error) {
        console.error('Failed to connect to Angel One WebSocket', error);
      }
    };

    initWs();

    return () => {
      if (unsubscribe) {
        unsubscribe();
      }
      angelMarketService.disconnectWebsocket();
    };
  }, []);

  const subscribe = useCallback((tokens: string[], mode?: number, exchangeType?: number) => {
    angelMarketService.subscribeTokens(tokens, mode, exchangeType);
  }, []);

  const unsubscribe = useCallback((tokens: string[], mode?: number, exchangeType?: number) => {
    angelMarketService.unsubscribeTokens(tokens, mode, exchangeType);
  }, []);

  return {
    liveTicks,
    subscribe,
    unsubscribe
  };
};
