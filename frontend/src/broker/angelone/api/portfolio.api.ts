import { angelClient } from './apiClient';
import { AngelHolding, AngelPosition, AngelFunds } from '../types';

export const portfolioApi = {
  getHoldings: () => 
    angelClient.get<{ data: AngelHolding[] }>('/portfolio/holdings'),
    
  getPositions: () => 
    angelClient.get<{ data: AngelPosition[] }>('/portfolio/positions'),
    
  getFunds: () => 
    angelClient.get<{ data: AngelFunds }>('/portfolio/funds'),
};
