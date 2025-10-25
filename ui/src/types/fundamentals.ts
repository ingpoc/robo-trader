/**
 * Fundamental Analysis Type Definitions
 */

export interface FundamentalMetrics {
  id?: number;
  symbol: string;
  analysis_date: string;
  revenue_growth_yoy?: number;
  revenue_growth_qoq?: number;
  earnings_growth_yoy?: number;
  earnings_growth_qoq?: number;
  gross_margin?: number;
  operating_margin?: number;
  net_margin?: number;
  roe?: number;
  roa?: number;
  debt_to_equity?: number;
  current_ratio?: number;
  cash_to_debt?: number;
  pe_ratio?: number;
  peg_ratio?: number;
  pb_ratio?: number;
  ps_ratio?: number;
  fundamental_score?: number;
  investment_recommendation?: string;
  recommendation_confidence?: number;
  fair_value_estimate?: number;
  growth_sustainable?: boolean;
  competitive_advantage?: string;
  created_at?: string;
  updated_at?: string;
}

export interface FundamentalDetails {
  id?: number;
  fundamental_metrics_id?: number;
  symbol: string;
  analysis_date: string;
  revenue_trend?: string;
  earnings_trend?: string;
  margin_trend?: string;
  debt_assessment?: string;
  liquidity_assessment?: string;
  valuation_assessment?: string;
  growth_catalysts?: string[];
  industry_tailwinds?: string[];
  industry_headwinds?: string[];
  key_risks?: string[];
  execution_risks?: string;
  market_risks?: string;
  regulatory_risks?: string;
  key_strengths?: string[];
  key_concerns?: string[];
  investment_thesis?: string;
  created_at?: string;
  updated_at?: string;
}

export interface InvestmentAnalysis {
  symbol: string;
  fundamental_score: number;
  investment_recommendation: string;
  recommendation_confidence: number;
  fair_value_estimate: number;
  key_strengths: string[];
  key_concerns: string[];
  investment_thesis: string;
  revenue_growth_yoy?: number;
  earnings_growth_yoy?: number;
  roe?: number;
  pe_ratio?: number;
}

export interface GrowthMetrics {
  revenue_growth_yoy?: number;
  revenue_growth_qoq?: number;
  earnings_growth_yoy?: number;
  earnings_growth_qoq?: number;
  revenue_trend?: string;
  earnings_trend?: string;
  growth_trajectory?: string;
}

export interface ProfitabilityMetrics {
  gross_margin?: number;
  operating_margin?: number;
  net_margin?: number;
  margin_trend?: string;
  roe?: number;
  roa?: number;
}

export interface ValuationMetrics {
  pe_ratio?: number;
  industry_avg_pe?: number;
  peg_ratio?: number;
  pb_ratio?: number;
  ps_ratio?: number;
  valuation_assessment?: string;
  fair_value_estimate?: number;
}

export interface FinancialHealth {
  debt_to_equity?: number;
  debt_assessment?: string;
  current_ratio?: number;
  liquidity_assessment?: string;
  cash_to_debt?: number;
}

export interface SustainabilityAnalysis {
  growth_sustainable?: boolean;
  growth_catalysts?: string[];
  industry_tailwinds?: string[];
  industry_headwinds?: string[];
  competitive_advantage?: string;
}

export interface RiskAssessment {
  key_risks?: string[];
  execution_risks?: string;
  market_risks?: string;
  regulatory_risks?: string;
}

export interface ComprehensiveScore {
  total_score: number;
  growth_score: number;
  profitability_score: number;
  valuation_score: number;
  health_score: number;
}

export interface PortfolioFundamentalSummary {
  symbol: string;
  fundamental_score?: number;
  investment_recommendation?: string;
  revenue_growth_yoy?: number;
  earnings_growth_yoy?: number;
}
