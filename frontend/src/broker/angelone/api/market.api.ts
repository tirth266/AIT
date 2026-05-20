import { angelClient } from './apiClient';
import { AngelLTPResponse, AngelCandleRequest, AngelCandleData } from '../types';

export const marketApi = {
  getLTP: (exchange: string, symboltoken: string, tradingsymbol: string) => 
    angelClient.get<{ data: AngelLTPResponse }>('/market/ltp', {
      params: { exchange, symboltoken, tradingsymbol }
    }),
    
  getHistoricalData: (params: AngelCandleRequest) => 
    angelClient.post<{ data: AngelCandleData[] }>('/market/candles', params),
    
  getSearchScrip: (searchString: string) =>
    angelClient.get('/market/search', { params: { q: searchString } }),
};
