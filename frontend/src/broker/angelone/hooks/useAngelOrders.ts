import { useCallback } from 'react';
import { useAngelOrdersStore } from '../store';
import { angelOrderService } from '../services';
import { AngelOrderRequest } from '../types';

export const useAngelOrders = () => {
  const { orders, isLoading, error, setOrders, setLoading, setError } = useAngelOrdersStore();

  const fetchOrders = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await angelOrderService.getOrderBook();
      setOrders(data);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch orders');
    } finally {
      setLoading(false);
    }
  }, []);

  const placeOrder = useCallback(async (order: AngelOrderRequest) => {
    setLoading(true);
    setError(null);
    try {
      const response = await angelOrderService.placeOrder(order);
      await fetchOrders(); // refresh order book
      return response;
    } catch (err: any) {
      setError(err.message || 'Failed to place order');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [fetchOrders]);

  const cancelOrder = useCallback(async (orderId: string, variety: string) => {
    setLoading(true);
    setError(null);
    try {
      const response = await angelOrderService.cancelOrder(orderId, variety);
      await fetchOrders();
      return response;
    } catch (err: any) {
      setError(err.message || 'Failed to cancel order');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [fetchOrders]);

  return {
    orders,
    isLoading,
    error,
    fetchOrders,
    placeOrder,
    cancelOrder
  };
};
