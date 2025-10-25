import React from 'react';
import { useInvestmentAnalysis } from '@/hooks/useFundamentals';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Skeleton } from '@/components/ui/Skeleton';
import type { InvestmentAnalysis } from '@/types/fundamentals';

export interface InvestmentRecommendationPanelProps {
  symbol: string;
  onRefresh?: () => void;
}

export const InvestmentRecommendationPanel: React.FC<InvestmentRecommendationPanelProps> = ({
  symbol,
  onRefresh,
}) => {
  const { analysis, isLoading, error } = useInvestmentAnalysis(symbol);

  if (error) {
    return (
      <Card className="p-4 bg-red-50 border border-red-200">
        <p className="text-red-800">Failed to load investment analysis</p>
      </Card>
    );
  }

  if (isLoading || !analysis) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-40" />
        <Skeleton className="h-32" />
      </div>
    );
  }

  const recommendationColor = getRecommendationColor(analysis.investment_recommendation);

  return (
    <div className="space-y-4">
      {/* Main Recommendation */}
      <Card className={`p-6 border-l-4 ${recommendationColor.border}`}>
        <div className="flex items-start justify-between mb-4">
          <h2 className="text-2xl font-bold text-gray-900">Investment Recommendation</h2>
          {onRefresh && (
            <button
              onClick={onRefresh}
              className="text-sm text-blue-600 hover:text-blue-800"
            >
              Refresh
            </button>
          )}
        </div>

        <div className="flex items-baseline gap-3 mb-4">
          <Badge className={`text-lg px-4 py-2 ${recommendationColor.bg} ${recommendationColor.text}`}>
            {analysis.investment_recommendation}
          </Badge>
          <span className="text-sm text-gray-600">
            Confidence: <span className="font-semibold">{analysis.recommendation_confidence}%</span>
          </span>
        </div>

        {analysis.fair_value_estimate && (
          <div className="bg-blue-50 rounded-lg p-3 mb-4">
            <p className="text-sm text-gray-600">Fair Value Estimate</p>
            <p className="text-2xl font-bold text-blue-600">₹{analysis.fair_value_estimate.toFixed(2)}</p>
          </div>
        )}

        {analysis.fundamental_score && (
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-600">Fundamental Score:</span>
            <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden max-w-xs">
              <div
                className="h-full bg-blue-600"
                style={{ width: `${Math.min(analysis.fundamental_score, 100)}%` }}
              />
            </div>
            <span className="text-sm font-semibold">{analysis.fundamental_score}/100</span>
          </div>
        )}
      </Card>

      {/* Key Metrics Summary */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Key Metrics</h3>
        <div className="grid grid-cols-2 gap-4">
          {analysis.revenue_growth_yoy !== undefined && (
            <MetricItem
              label="Revenue Growth YoY"
              value={`${analysis.revenue_growth_yoy.toFixed(2)}%`}
            />
          )}
          {analysis.earnings_growth_yoy !== undefined && (
            <MetricItem
              label="Earnings Growth YoY"
              value={`${analysis.earnings_growth_yoy.toFixed(2)}%`}
            />
          )}
          {analysis.roe !== undefined && (
            <MetricItem label="ROE" value={`${analysis.roe.toFixed(2)}%`} />
          )}
          {analysis.pe_ratio !== undefined && (
            <MetricItem label="P/E Ratio" value={analysis.pe_ratio.toFixed(2)} />
          )}
        </div>
      </Card>

      {/* Key Strengths */}
      {analysis.key_strengths && analysis.key_strengths.length > 0 && (
        <Card className="p-6 border-l-4 border-green-500">
          <h3 className="text-lg font-semibold text-green-900 mb-3">Key Strengths</h3>
          <ul className="space-y-2">
            {analysis.key_strengths.map((strength, idx) => (
              <li key={idx} className="flex items-start gap-2">
                <span className="text-green-600 font-bold mt-0.5">✓</span>
                <span className="text-gray-700">{strength}</span>
              </li>
            ))}
          </ul>
        </Card>
      )}

      {/* Key Concerns */}
      {analysis.key_concerns && analysis.key_concerns.length > 0 && (
        <Card className="p-6 border-l-4 border-red-500">
          <h3 className="text-lg font-semibold text-red-900 mb-3">Key Concerns</h3>
          <ul className="space-y-2">
            {analysis.key_concerns.map((concern, idx) => (
              <li key={idx} className="flex items-start gap-2">
                <span className="text-red-600 font-bold mt-0.5">⚠</span>
                <span className="text-gray-700">{concern}</span>
              </li>
            ))}
          </ul>
        </Card>
      )}

      {/* Investment Thesis */}
      {analysis.investment_thesis && (
        <Card className="p-6 bg-gray-50">
          <h3 className="text-lg font-semibold text-gray-900 mb-3">Investment Thesis</h3>
          <p className="text-gray-700 leading-relaxed">{analysis.investment_thesis}</p>
        </Card>
      )}

      {/* Disclaimer */}
      <div className="text-xs text-gray-500 text-center">
        <p>This analysis is for informational purposes only and should not be considered as financial advice.</p>
      </div>
    </div>
  );
};

interface MetricItemProps {
  label: string;
  value: string;
}

const MetricItem: React.FC<MetricItemProps> = ({ label, value }) => (
  <div className="p-3 bg-gray-50 rounded-lg">
    <p className="text-xs text-gray-600 mb-1">{label}</p>
    <p className="text-lg font-semibold text-gray-900">{value}</p>
  </div>
);

function getRecommendationColor(recommendation?: string): {
  bg: string;
  text: string;
  border: string;
} {
  const rec = (recommendation || '').toLowerCase();

  if (rec.includes('strong buy') || rec.includes('buy')) {
    return {
      bg: 'bg-green-100',
      text: 'text-green-800',
      border: 'border-green-500',
    };
  }

  if (rec.includes('hold') || rec.includes('neutral')) {
    return {
      bg: 'bg-yellow-100',
      text: 'text-yellow-800',
      border: 'border-yellow-500',
    };
  }

  if (rec.includes('sell') || rec.includes('reduce')) {
    return {
      bg: 'bg-red-100',
      text: 'text-red-800',
      border: 'border-red-500',
    };
  }

  return {
    bg: 'bg-blue-100',
    text: 'text-blue-800',
    border: 'border-blue-500',
  };
}

export default InvestmentRecommendationPanel;
