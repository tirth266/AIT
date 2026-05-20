import { angelClient } from './apiClient';
import { 
  AngelOrderRequest, 
  AngelOrderResponse, 
  AngelOrderDetails 
} from '../types';

export const orderApi = {
  placeOrder: (order: AngelOrderRequest) => 
    angelClient.post<{ data: AngelOrderResponse }>('/orders', order),
    
  modifyOrder: (orderId: string, updates: Partial<AngelOrderRequest>) => 
    angelClient.put<{ data: AngelOrderResponse }>(`/orders/${orderId}`, updates),
    
  cancelOrder: (orderId: string, variety: string) => 
    angelClient.delete(`/orders/${orderId}`, { data: { variety } }),
    
  getOrderBook: () => 
    angelClient.get<{ data: AngelOrderDetails[] }>('/orders'),
    
  getTradeBook: () => 
    angelClient.get<{ data: any[] }>('/trades'),
};
