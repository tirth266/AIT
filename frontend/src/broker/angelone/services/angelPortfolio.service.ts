import { portfolioApi } from '../api';

export const angelPortfolioService = {
  getHoldings: async () => {
    const response = await portfolioApi.getHoldings();
    return response.status ? response.data : [];
  },

  getPositions: async () => {
    const response = await portfolioApi.getPositions();
    return response.status ? response.data : [];
  },

  getFunds: async () => {
    const response = await portfolioApi.getFunds();
    return response.status ? response.data : null;
  }
};
