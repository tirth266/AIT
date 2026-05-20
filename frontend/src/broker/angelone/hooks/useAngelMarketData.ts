import { useCallback, useState } from 'react';
import { angelMarketService } from '../services';
import { AngelMarketDataRequest } from '../types';

export const useAngelMarketData = () => {
  const [isLoading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const getMarketData = useCallback(async (request: AngelMarketDataRequest) => {
    setLoading(true);
    setError(null);
    try {
      const response = await angelMarketService.getMarketData(request);
      if (response.status) {
        return response.data;
      } else {
        throw new Error(response.message || 'Failed to fetch market data');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to fetch market data');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    getMarketData,
    isLoading,
    error
  };
};
