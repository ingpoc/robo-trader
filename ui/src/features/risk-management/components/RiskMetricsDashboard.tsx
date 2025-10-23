import React from 'react';
import { BarChart3, TrendingUp, TrendingDown, Activity, Shield, AlertTriangle } from 'lucide-react';
import { usePortfolioRiskMetrics, useRiskMonitoringStatus } from '../hooks/useRiskApi';
import { useRiskWebSocket, usePortfolioRiskMonitoring } from '../hooks/useRiskWebSocket';
import { Card } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';

export const RiskMetricsDashboard: React.FC = () => {
  const [selectedPortfolioId] = React.useState('portfolio_123'); // This would come from user context
  const [selectedPeriod, setSelectedPeriod] = React.useState<'1D' | '1W' | '1M' | '3M' | '6M' | '1Y'>('1M');

  const { data: riskMetrics, isLoading: metricsLoading } = usePortfolioRiskMetrics(selectedPortfolioId, selectedPeriod);
  const { data: monitoringStatus, isLoading: monitoringLoading } = useRiskMonitoringStatus();

  // WebSocket for real-time updates
  const { isConnected } = useRiskWebSocket();
  const { riskMetrics: realtimeMetrics } = usePortfolioRiskMonitoring(selectedPortfolioId);

  // Use real-time metrics if available, otherwise use polled data
  const displayMetrics = realtimeMetrics || riskMetrics;

  const periods = [
    { value: '1D', label: '1 Day' },
    { value: '1W', label: '1 Week' },
    { value: '1M', label: '1 Month' },
    { value: '3M', label: '3 Months' },
    { value: '6M', label: '6 Months' },
    { value: '1Y', label: '1 Year' },
  ] as const;

  const getRiskLevelColor = (level: string) => {
    switch (level) {
      case 'LOW':
        return 'text-emerald-600 bg-emerald-100';
      case 'MODERATE':
        return 'text-copper-600 bg-copper-100';
      case 'HIGH':
        return 'text-orange-600 bg-orange-100';
      case 'CRITICAL':
        return 'text-red-600 bg-red-100';
      default:
        return 'text-warmgray-600 bg-warmgray-100';
    }
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const formatPercent = (value: number) => {
    return `${value.toFixed(2)}%`;
  };

  if (metricsLoading || monitoringLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <Card key={i} className="p-4">
              <Skeleton className="h-4 w-full mb-2" />
              <Skeleton className="h-8 w-3/4" />
            </Card>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-warmgray-900">Real-time Risk Metrics</h2>
          <p className="text-sm text-warmgray-600">
            Monitor real-time risk metrics and VaR calculations
          </p>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-500' : 'bg-warmgray-400'}`} />
            <span className="text-sm text-warmgray-600">
              {isConnected ? 'Live' : 'Offline'}
            </span>
          </div>

          <div className="flex gap-1">
            {periods.map((period) => (
              <button
                key={period.value}
                onClick={() => setSelectedPeriod(period.value)}
                className={`px-3 py-1 text-sm rounded-md transition-colors ${
                  selectedPeriod === period.value
                    ? 'bg-copper-500 text-white'
                    : 'bg-warmgray-100 text-warmgray-700 hover:bg-warmgray-200'
                }`}
              >
                {period.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Risk Overview */}
      {displayMetrics && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-warmgray-600">Risk Score</p>
                <p className="text-2xl font-bold text-warmgray-900">
                  {displayMetrics.basic_metrics.total_risk_score.toFixed(1)}
                </p>
              </div>
              <Shield className="h-8 w-8 text-copper-500" />
            </div>
            <div className="mt-2">
              <Badge className={getRiskLevelColor(displayMetrics.basic_metrics.risk_level)}>
                {displayMetrics.basic_metrics.risk_level}
              </Badge>
            </div>
          </Card>

          <Card className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-warmgray-600">VaR (1-day 95%)</p>
                <p className="text-2xl font-bold text-warmgray-900">
                  {formatCurrency(displayMetrics.value_at_risk.var_1day_95)}
                </p>
              </div>
              <TrendingDown className="h-8 w-8 text-red-500" />
            </div>
          </Card>

          <Card className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-warmgray-600">Max Drawdown</p>
                <p className="text-2xl font-bold text-warmgray-900">
                  {formatPercent(displayMetrics.basic_metrics.max_drawdown)}
                </p>
              </div>
              <BarChart3 className="h-8 w-8 text-orange-500" />
            </div>
          </Card>

          <Card className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-warmgray-600">Sharpe Ratio</p>
                <p className="text-2xl font-bold text-warmgray-900">
                  {displayMetrics.risk_adjusted_returns.sharpe_ratio.toFixed(2)}
                </p>
              </div>
              <TrendingUp className="h-8 w-8 text-emerald-500" />
            </div>
          </Card>
        </div>
      )}

      {/* Detailed Metrics */}
      {displayMetrics && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Risk Factors */}
          <Card className="p-6">
            <h3 className="text-lg font-semibold text-warmgray-900 mb-4">Risk Factors</h3>
            <div className="space-y-4">
              <div>
                <div className="flex justify-between items-center mb-2">
                  <span className="text-sm text-warmgray-600">Concentration Risk</span>
                  <span className="text-sm font-medium">{displayMetrics.risk_factors.concentration_risk.toFixed(1)}%</span>
                </div>
                <Progress value={displayMetrics.risk_factors.concentration_risk} className="h-2" />
              </div>

              <div>
                <div className="flex justify-between items-center mb-2">
                  <span className="text-sm text-warmgray-600">Liquidity Risk</span>
                  <span className="text-sm font-medium">{displayMetrics.risk_factors.liquidity_risk.toFixed(1)}%</span>
                </div>
                <Progress value={displayMetrics.risk_factors.liquidity_risk} className="h-2" />
              </div>

              <div>
                <div className="flex justify-between items-center mb-2">
                  <span className="text-sm text-warmgray-600">Market Risk</span>
                  <span className="text-sm font-medium">{displayMetrics.risk_factors.market_risk.toFixed(1)}%</span>
                </div>
                <Progress value={displayMetrics.risk_factors.market_risk} className="h-2" />
              </div>

              <div>
                <div className="flex justify-between items-center mb-2">
                  <span className="text-sm text-warmgray-600">Volatility Risk</span>
                  <span className="text-sm font-medium">{displayMetrics.risk_factors.volatility_risk.toFixed(1)}%</span>
                </div>
                <Progress value={displayMetrics.risk_factors.volatility_risk} className="h-2" />
              </div>

              <div>
                <div className="flex justify-between items-center mb-2">
                  <span className="text-sm text-warmgray-600">Sector Risk</span>
                  <span className="text-sm font-medium">{displayMetrics.risk_factors.sector_risk.toFixed(1)}%</span>
                </div>
                <Progress value={displayMetrics.risk_factors.sector_risk} className="h-2" />
              </div>
            </div>
          </Card>

          {/* Portfolio Characteristics */}
          <Card className="p-6">
            <h3 className="text-lg font-semibold text-warmgray-900 mb-4">Portfolio Characteristics</h3>
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-sm text-warmgray-600">Beta</span>
                <span className="text-sm font-medium">{displayMetrics.portfolio_characteristics.beta.toFixed(2)}</span>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-sm text-warmgray-600">Volatility</span>
                <span className="text-sm font-medium">{formatPercent(displayMetrics.portfolio_characteristics.volatility)}</span>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-sm text-warmgray-600">Market Correlation</span>
                <span className="text-sm font-medium">{displayMetrics.portfolio_characteristics.correlation_to_market.toFixed(2)}</span>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-sm text-warmgray-600">Diversification Ratio</span>
                <span className="text-sm font-medium">{displayMetrics.portfolio_characteristics.diversification_ratio.toFixed(2)}</span>
              </div>
            </div>
          </Card>

          {/* VaR Analysis */}
          <Card className="p-6">
            <h3 className="text-lg font-semibold text-warmgray-900 mb-4">Value at Risk (VaR)</h3>
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-sm text-warmgray-600">1-Day VaR (95%)</span>
                <span className="text-sm font-medium text-red-600">
                  {formatCurrency(displayMetrics.value_at_risk.var_1day_95)}
                </span>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-sm text-warmgray-600">1-Day VaR (99%)</span>
                <span className="text-sm font-medium text-red-600">
                  {formatCurrency(displayMetrics.value_at_risk.var_1day_99)}
                </span>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-sm text-warmgray-600">10-Day VaR (95%)</span>
                <span className="text-sm font-medium text-red-600">
                  {formatCurrency(displayMetrics.value_at_risk.var_10day_95)}
                </span>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-sm text-warmgray-600">CVaR (95%)</span>
                <span className="text-sm font-medium text-red-600">
                  {formatCurrency(displayMetrics.value_at_risk.cvar_1day_95)}
                </span>
              </div>
            </div>
          </Card>

          {/* Risk-Adjusted Returns */}
          <Card className="p-6">
            <h3 className="text-lg font-semibold text-warmgray-900 mb-4">Risk-Adjusted Returns</h3>
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-sm text-warmgray-600">Sharpe Ratio</span>
                <span className="text-sm font-medium">{displayMetrics.risk_adjusted_returns.sharpe_ratio.toFixed(2)}</span>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-sm text-warmgray-600">Sortino Ratio</span>
                <span className="text-sm font-medium">{displayMetrics.risk_adjusted_returns.sortino_ratio.toFixed(2)}</span>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-sm text-warmgray-600">Information Ratio</span>
                <span className="text-sm font-medium">{displayMetrics.risk_adjusted_returns.information_ratio.toFixed(2)}</span>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-sm text-warmgray-600">Treynor Ratio</span>
                <span className="text-sm font-medium">{displayMetrics.risk_adjusted_returns.treynor_ratio.toFixed(2)}</span>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* Sector Concentration */}
      {displayMetrics && (
        <Card className="p-6">
          <h3 className="text-lg font-semibold text-warmgray-900 mb-4">Sector Concentration</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
            {Object.entries(displayMetrics.concentration_analysis.sector_concentration).map(([sector, percentage]) => (
              <div key={sector} className="text-center">
                <div className="text-2xl font-bold text-warmgray-900">{percentage.toFixed(1)}%</div>
                <div className="text-sm text-warmgray-600 capitalize">{sector}</div>
                <div className="mt-2">
                  <Progress value={percentage} className="h-2" />
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Monitoring Status */}
      {monitoringStatus && (
        <Card className="p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Activity className="h-5 w-5 text-copper-500" />
              <div>
                <h4 className="font-semibold text-warmgray-900">Risk Monitoring Status</h4>
                <p className="text-sm text-warmgray-600">
                  Last updated: {new Date(monitoringStatus.last_update).toLocaleString()}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-4">
              <div className="text-center">
                <div className="text-lg font-bold text-warmgray-900">{monitoringStatus.positions_monitored}</div>
                <div className="text-xs text-warmgray-600">Positions</div>
              </div>

              <div className="text-center">
                <div className="text-lg font-bold text-warmgray-900">{monitoringStatus.active_stop_losses}</div>
                <div className="text-xs text-warmgray-600">Stop Losses</div>
              </div>

              <div className="text-center">
                <div className="text-lg font-bold text-warmgray-900">{monitoringStatus.risk_summary.warnings_active}</div>
                <div className="text-xs text-warmgray-600">Warnings</div>
              </div>

              <div className="text-center">
                <div className="text-lg font-bold text-warmgray-900">{monitoringStatus.risk_summary.critical_alerts}</div>
                <div className="text-xs text-warmgray-600">Critical</div>
              </div>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
};