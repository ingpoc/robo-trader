import React from 'react';
import { useFundamentals } from '@/hooks/useFundamentals';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Skeleton } from '@/components/ui/Skeleton';
import type { FundamentalMetrics } from '@/types/fundamentals';

export interface FundamentalsDashboardProps {
  symbol: string;
  onRefresh?: () => void;
}

export const FundamentalsDashboard: React.FC<FundamentalsDashboardProps> = ({
  symbol,
  onRefresh,
}) => {
  const { fundamentals, isLoading, error } = useFundamentals(symbol);

  if (error) {
    return (
      <Card className="p-4 bg-red-50 border border-red-200">
        <p className="text-red-800">Failed to load fundamentals</p>
      </Card>
    );
  }

  if (isLoading || !fundamentals) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-48" />
        <Skeleton className="h-32" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Score Card */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">Fundamental Score</h3>
          {onRefresh && (
            <button
              onClick={onRefresh}
              className="text-sm text-blue-600 hover:text-blue-800"
            >
              Refresh
            </button>
          )}
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-5xl font-bold text-blue-600">
            {fundamentals.fundamental_score ?? '-'}
          </span>
          <span className="text-gray-500">/100</span>
          {fundamentals.recommendation_confidence && (
            <Badge variant="secondary" className="ml-2">
              {fundamentals.recommendation_confidence}% confidence
            </Badge>
          )}
        </div>
        {fundamentals.investment_recommendation && (
          <p className="mt-2 text-sm text-gray-600">
            Recommendation: <span className="font-semibold">{fundamentals.investment_recommendation}</span>
          </p>
        )}
      </Card>

      {/* Growth Metrics */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Growth Metrics</h3>
        <div className="grid grid-cols-2 gap-4">
          <MetricRow
            label="Revenue Growth YoY"
            value={fundamentals.revenue_growth_yoy}
            format="percent"
          />
          <MetricRow
            label="Earnings Growth YoY"
            value={fundamentals.earnings_growth_yoy}
            format="percent"
          />
          <MetricRow
            label="Revenue Growth QoQ"
            value={fundamentals.revenue_growth_qoq}
            format="percent"
          />
          <MetricRow
            label="Earnings Growth QoQ"
            value={fundamentals.earnings_growth_qoq}
            format="percent"
          />
        </div>
      </Card>

      {/* Profitability Metrics */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Profitability</h3>
        <div className="grid grid-cols-2 gap-4">
          <MetricRow
            label="Gross Margin"
            value={fundamentals.gross_margin}
            format="percent"
          />
          <MetricRow
            label="Operating Margin"
            value={fundamentals.operating_margin}
            format="percent"
          />
          <MetricRow label="Net Margin" value={fundamentals.net_margin} format="percent" />
          <MetricRow label="ROE" value={fundamentals.roe} format="percent" />
        </div>
      </Card>

      {/* Valuation Metrics */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Valuation</h3>
        <div className="grid grid-cols-2 gap-4">
          <MetricRow label="P/E Ratio" value={fundamentals.pe_ratio} format="number" />
          <MetricRow label="PEG Ratio" value={fundamentals.peg_ratio} format="number" />
          <MetricRow label="P/B Ratio" value={fundamentals.pb_ratio} format="number" />
          <MetricRow label="P/S Ratio" value={fundamentals.ps_ratio} format="number" />
        </div>
        {fundamentals.fair_value_estimate && (
          <div className="mt-4 pt-4 border-t border-gray-200">
            <p className="text-sm text-gray-600">
              Fair Value Estimate: <span className="font-semibold">₹{fundamentals.fair_value_estimate.toFixed(2)}</span>
            </p>
          </div>
        )}
      </Card>

      {/* Financial Health */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Financial Health</h3>
        <div className="grid grid-cols-2 gap-4">
          <MetricRow
            label="Debt-to-Equity"
            value={fundamentals.debt_to_equity}
            format="number"
          />
          <MetricRow
            label="Current Ratio"
            value={fundamentals.current_ratio}
            format="number"
          />
          <MetricRow label="Cash-to-Debt" value={fundamentals.cash_to_debt} format="number" />
          <MetricRow label="ROA" value={fundamentals.roa} format="percent" />
        </div>
      </Card>

      {/* Additional Info */}
      <Card className="p-6">
        <div className="space-y-3">
          {fundamentals.growth_sustainable !== undefined && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Growth Sustainable</span>
              <Badge variant={fundamentals.growth_sustainable ? 'default' : 'outline'}>
                {fundamentals.growth_sustainable ? 'Yes' : 'No'}
              </Badge>
            </div>
          )}
          {fundamentals.competitive_advantage && (
            <div>
              <p className="text-sm text-gray-600">Competitive Advantage</p>
              <p className="text-sm text-gray-900">{fundamentals.competitive_advantage}</p>
            </div>
          )}
          {fundamentals.analysis_date && (
            <p className="text-xs text-gray-500">
              Analysis Date: {new Date(fundamentals.analysis_date).toLocaleDateString()}
            </p>
          )}
        </div>
      </Card>
    </div>
  );
};

interface MetricRowProps {
  label: string;
  value?: number | null;
  format: 'percent' | 'number';
}

const MetricRow: React.FC<MetricRowProps> = ({ label, value, format }) => {
  if (value === null || value === undefined) {
    return (
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600">{label}</span>
        <span className="text-sm text-gray-400">—</span>
      </div>
    );
  }

  const formattedValue =
    format === 'percent' ? `${value.toFixed(2)}%` : value.toFixed(2);

  const color = getValueColor(value, format);

  return (
    <div className="flex justify-between items-center">
      <span className="text-sm text-gray-600">{label}</span>
      <span className={`text-sm font-medium ${color}`}>{formattedValue}</span>
    </div>
  );
};

function getValueColor(value: number, format: string): string {
  if (format === 'percent') {
    if (value > 10) return 'text-green-600';
    if (value > 0) return 'text-blue-600';
    return 'text-red-600';
  }

  // For ratios like P/E, lower is often better, but depends on context
  return 'text-gray-900';
}

export default FundamentalsDashboard;
