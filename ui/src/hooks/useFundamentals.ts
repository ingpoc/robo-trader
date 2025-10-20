import { useQuery } from '@tanstack/react-query';
import { api } from '@/api/client';
import { API_ENDPOINTS, REFRESH_INTERVALS } from '@/lib/constants';
import type { FundamentalMetrics, InvestmentAnalysis } from '@/types/fundamentals';

export interface UseFundamentalsOptions {
  symbol?: string;
  enabled?: boolean;
  refetchInterval?: number;
}

export const useFundamentals = (
  symbol?: string,
  options: UseFundamentalsOptions = {}
) => {
  const { enabled = true, refetchInterval = REFRESH_INTERVALS.fundamentals } = options;

  const { data, isLoading, error, refetch } = useQuery<FundamentalMetrics>({
    queryKey: ['fundamentals', symbol],
    queryFn: () => api.get(`/api/fundamentals/${symbol}`),
    enabled: enabled && !!symbol,
    refetchInterval,
  });

  return {
    fundamentals: data || null,
    isLoading,
    error: error?.message || null,
    refetch,
  };
};

export const useInvestmentAnalysis = (
  symbol?: string,
  options: UseFundamentalsOptions = {}
) => {
  const { enabled = true, refetchInterval = REFRESH_INTERVALS.fundamentals } = options;

  const { data, isLoading, error, refetch } = useQuery<InvestmentAnalysis>({
    queryKey: ['investment-analysis', symbol],
    queryFn: () => api.get(`/api/investment-analysis/${symbol}`),
    enabled: enabled && !!symbol,
    refetchInterval,
  });

  return {
    analysis: data || null,
    isLoading,
    error: error?.message || null,
    refetch,
  };
};

export const usePortfolioFundamentals = (options: UseFundamentalsOptions = {}) => {
  const { enabled = true, refetchInterval = REFRESH_INTERVALS.portfolio } = options;

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['portfolio-fundamentals'],
    queryFn: () => api.get('/api/portfolio-fundamentals'),
    enabled,
    refetchInterval,
  });

  return {
    portfolioFundamentals: data?.fundamentals || [],
    isLoading,
    error: error?.message || null,
    refetch,
  };
};
