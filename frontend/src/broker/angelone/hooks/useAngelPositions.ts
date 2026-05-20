import { useCallback } from 'react';
import { useAngelMarketStore } from '../store';
import { angelPortfolioService } from '../services';

export const useAngelPositions = () => {
  const { holdings, positions, funds, isLoading, error, setHoldings, setPositions, setFunds, setLoading, setError } = useAngelMarketStore();

  const fetchHoldings = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await angelPortfolioService.getHoldings();
      setHoldings(data);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch holdings');
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchPositions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await angelPortfolioService.getPositions();
      setPositions(data);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch positions');
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchFunds = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await angelPortfolioService.getFunds();
      setFunds(data);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch funds');
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchAll = useCallback(async () => {
    await Promise.all([fetchHoldings(), fetchPositions(), fetchFunds()]);
  }, [fetchHoldings, fetchPositions, fetchFunds]);

  return {
    holdings,
    positions,
    funds,
    isLoading,
    error,
    fetchHoldings,
    fetchPositions,
    fetchFunds,
    fetchAll
  };
};
