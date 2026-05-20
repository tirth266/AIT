import { marketApi, websocketApi } from '../api';
import { AngelMarketDataRequest } from '../types';

export const angelMarketService = {
  getMarketData: async (request: AngelMarketDataRequest) => {
    return await marketApi.getMarketData(request);
  },

  connectWebsocket: async () => {
    await websocketApi.connect();
  },

  disconnectWebsocket: () => {
    websocketApi.disconnect();
  },

  subscribeTokens: (tokens: string[], mode?: number, exchangeType?: number) => {
    websocketApi.subscribe(tokens, mode, exchangeType);
  },

  unsubscribeTokens: (tokens: string[], mode?: number, exchangeType?: number) => {
    websocketApi.unsubscribe(tokens, mode, exchangeType);
  }
};
