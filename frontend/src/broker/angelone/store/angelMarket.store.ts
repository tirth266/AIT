import { create } from 'zustand';
import { AngelTick, AngelCandleData } from '../types';
import { marketApi } from '../api';

interface AngelMarketState {
  ticks: Record<string, AngelTick>;
  candles: Record<string, AngelCandleData[]>;
  isLoading: boolean;
  
  updateTick: (tick: AngelTick) => void;
  fetchCandles: (params: any) => Promise<void>;
  clearMarketData: () => void;
}

export const useAngelMarketStore = create<AngelMarketState>((set) => ({
  ticks: {},
  candles: {},
  isLoading: false,

  updateTick: (tick) => set((state) => ({
    ticks: {
      ...state.ticks,
      [tick.tk]: tick
    }
  })),

  fetchCandles: async (params) => {
    set({ isLoading: true });
    try {
      const response = await marketApi.getHistoricalData(params);
      set((state) => ({
        candles: {
          ...state.candles,
          [params.symboltoken]: response.data.data
        },
        isLoading: false
      }));
    } catch (error) {
      console.error('Failed to fetch candles', error);
      set({ isLoading: false });
    }
  },

  clearMarketData: () => set({ ticks: {}, candles: {} })
}));
