import { create } from 'zustand';
import { AngelOrderDetails, AngelPosition, AngelHolding, AngelFunds } from '../types';
import { orderApi, portfolioApi } from '../api';

interface AngelOrdersState {
  orders: AngelOrderDetails[];
  positions: AngelPosition[];
  holdings: AngelHolding[];
  funds: AngelFunds | null;
  isLoading: boolean;
  
  fetchOrders: () => Promise<void>;
  fetchPortfolio: () => Promise<void>;
  fetchFunds: () => Promise<void>;
}

export const useAngelOrdersStore = create<AngelOrdersState>((set) => ({
  orders: [],
  positions: [],
  holdings: [],
  funds: null,
  isLoading: false,

  fetchOrders: async () => {
    set({ isLoading: true });
    try {
      const response = await orderApi.getOrderBook();
      set({ orders: response.data.data, isLoading: false });
    } catch (error) {
      console.error('Failed to fetch orders', error);
      set({ isLoading: false });
    }
  },

  fetchPortfolio: async () => {
    set({ isLoading: true });
    try {
      const [posRes, holdRes] = await Promise.all([
        portfolioApi.getPositions(),
        portfolioApi.getHoldings()
      ]);
      set({ 
        positions: posRes.data.data, 
        holdings: holdRes.data.data, 
        isLoading: false 
      });
    } catch (error) {
      console.error('Failed to fetch portfolio', error);
      set({ isLoading: false });
    }
  },

  fetchFunds: async () => {
    try {
      const response = await portfolioApi.getFunds();
      set({ funds: response.data.data });
    } catch (error) {
      console.error('Failed to fetch funds', error);
    }
  }
}));
