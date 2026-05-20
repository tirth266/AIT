import { orderApi } from '../api';
import { AngelOrderRequest } from '../types';
import { withRetry } from '../utils/retry';
import { OrderRejectedError, RateLimitError } from '../utils/errors';

export const angelOrderService = {
  placeOrder: async (order: AngelOrderRequest) => {
    try {
      const response = await withRetry(() => orderApi.placeOrder(order), 2, 500, (error) => error instanceof RateLimitError);
      if (!response.status) {
        throw new OrderRejectedError(response.message || 'Order failed');
      }
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  modifyOrder: async (orderId: string, modifications: Partial<AngelOrderRequest>) => {
    const response = await orderApi.modifyOrder(orderId, modifications);
    if (!response.status) {
      throw new OrderRejectedError(response.message || 'Order modify failed');
    }
    return response.data;
  },

  cancelOrder: async (orderId: string, variety: string) => {
    const response = await orderApi.cancelOrder(orderId, variety);
    if (!response.status) {
      throw new OrderRejectedError(response.message || 'Order cancel failed');
    }
    return response.data;
  },

  getOrderBook: async () => {
    const response = await orderApi.getOrderBook();
    return response.status ? response.data : [];
  },

  getTradeBook: async () => {
    const response = await orderApi.getTradeBook();
    return response.status ? response.data : [];
  }
};
