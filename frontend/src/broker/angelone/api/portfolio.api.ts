import { angelClient } from './apiClient';
import { AngelHolding, AngelPosition, AngelFunds } from '../types';

export const portfolioApi = {
  getHoldings: () => 
    angelClient.get<{ data: AngelHolding[] }>('/holdings'),
    
  getPositions: () => 
    angelClient.get<{ data: AngelPosition[] }>('/positions'),
    
  getFunds: () => 
    angelClient.get<{ data: AngelFunds }>('/funds'),
};
