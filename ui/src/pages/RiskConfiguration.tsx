import React, { useState, useEffect } from 'react';
import { Shield, AlertTriangle, TrendingDown, BarChart3, Settings, Zap } from 'lucide-react';
import { useRiskStore } from '@/features/risk-management/stores/riskStore';
import { useRiskLimits, useRiskAlerts, usePortfolioRiskMetrics, useRiskMonitoringStatus } from '@/features/risk-management/hooks/useRiskApi';
import { useRiskWebSocket } from '@/features/risk-management/hooks/useRiskWebSocket';
import { RiskLimitsConfig } from '@/features/risk-management/components/RiskLimitsConfig';
import { StopLossTemplates } from '@/features/risk-management/components/StopLossTemplates';
import { RebalancingRules } from '@/features/risk-management/components/RebalancingRules';
import { RiskAlertsPanel } from '@/features/risk-management/components/RiskAlertsPanel';
import { RiskMetricsDashboard } from '@/features/risk-management/components/RiskMetricsDashboard';
import { EmergencyOverrides } from '@/features/risk-management/components/EmergencyOverrides';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';

const RiskConfiguration: React.FC = () => {
  const { activeTab, setActiveTab, isLoading, error } = useRiskStore();
  const [selectedPortfolioId] = useState('portfolio_123'); // This would come from user context

  // API hooks
  const { data: riskLimits, isLoading: limitsLoading } = useRiskLimits();
  const { data: alerts, isLoading: alertsLoading } = useRiskAlerts();
  const { data: riskMetrics, isLoading: metricsLoading } = usePortfolioRiskMetrics(selectedPortfolioId);
  const { data: monitoringStatus, isLoading: monitoringLoading } = useRiskMonitoringStatus();

  // WebSocket for real-time updates
  const { isConnected: wsConnected } = useRiskWebSocket();

  const tabs = [
    {
      id: 'limits',
      label: 'Risk Limits',
      icon: Shield,
      component: RiskLimitsConfig,
      badge: riskLimits?.filter(l => l.status === 'CRITICAL').length || 0,
    },
    {
      id: 'stop-loss',
      label: 'Stop Loss',
      icon: TrendingDown,
      component: StopLossTemplates,
    },
    {
      id: 'rebalancing',
      label: 'Rebalancing',
      icon: BarChart3,
      component: RebalancingRules,
    },
    {
      id: 'alerts',
      label: 'Alerts',
      icon: AlertTriangle,
      component: RiskAlertsPanel,
      badge: alerts?.data.filter(a => !a.is_acknowledged).length || 0,
    },
    {
      id: 'metrics',
      label: 'Risk Metrics',
      icon: BarChart3,
      component: RiskMetricsDashboard,
    },
    {
      id: 'overrides',
      label: 'Emergency',
      icon: Zap,
      component: EmergencyOverrides,
    },
  ];

  const activeTabData = tabs.find(tab => tab.id === activeTab);
  const ActiveComponent = activeTabData?.component || RiskLimitsConfig;

  if (error) {
    return (
      <div className="page-wrapper">
        <div className="flex items-center justify-center min-h-[400px]">
          <Card className="p-6 max-w-md">
            <div className="text-center">
              <AlertTriangle className="h-12 w-12 text-rose-500 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-warmgray-900 mb-2">
                Risk Management Error
              </h3>
              <p className="text-warmgray-600 mb-4">{error}</p>
              <Button onClick={() => window.location.reload()}>
                Retry
              </Button>
            </div>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="page-wrapper">
      {/* Header */}
      <div className="page-header">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="page-title flex items-center gap-3">
              <Shield className="h-8 w-8 text-copper-500" />
              Risk Configuration
            </h1>
            <p className="page-subtitle">
              Comprehensive risk management and monitoring for your trading activities
            </p>
          </div>

          {/* Connection Status */}
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-emerald-500' : 'bg-warmgray-400'}`} />
              <span className="text-sm text-warmgray-600">
                {wsConnected ? 'Live' : 'Offline'}
              </span>
            </div>

            {monitoringStatus && (
              <Badge
                variant={
                  monitoringStatus.risk_summary.overall_risk_level === 'CRITICAL' ? 'destructive' :
                  monitoringStatus.risk_summary.overall_risk_level === 'HIGH' ? 'secondary' :
                  'default'
                }
              >
                {monitoringStatus.risk_summary.overall_risk_level} Risk
              </Badge>
            )}
          </div>
        </div>
      </div>

      {/* Risk Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <Card className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-warmgray-600">Active Limits</p>
              {limitsLoading ? (
                <Skeleton className="h-8 w-16 mt-1" />
              ) : (
                <p className="text-2xl font-bold text-warmgray-900">
                  {riskLimits?.filter(l => l.is_active).length || 0}
                </p>
              )}
            </div>
            <Shield className="h-8 w-8 text-copper-500" />
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-warmgray-600">Unacknowledged Alerts</p>
              {alertsLoading ? (
                <Skeleton className="h-8 w-16 mt-1" />
              ) : (
                <p className="text-2xl font-bold text-warmgray-900">
                  {alerts?.data.filter(a => !a.is_acknowledged).length || 0}
                </p>
              )}
            </div>
            <AlertTriangle className="h-8 w-8 text-rose-500" />
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-warmgray-600">Risk Score</p>
              {metricsLoading ? (
                <Skeleton className="h-8 w-16 mt-1" />
              ) : (
                <p className="text-2xl font-bold text-warmgray-900">
                  {riskMetrics?.basic_metrics.total_risk_score.toFixed(1) || 'N/A'}
                </p>
              )}
            </div>
            <BarChart3 className="h-8 w-8 text-blue-500" />
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-warmgray-600">VaR (1-day 95%)</p>
              {metricsLoading ? (
                <Skeleton className="h-8 w-20 mt-1" />
              ) : (
                <p className="text-2xl font-bold text-warmgray-900">
                  ${riskMetrics?.value_at_risk.var_1day_95.toLocaleString() || 'N/A'}
                </p>
              )}
            </div>
            <TrendingDown className="h-8 w-8 text-emerald-500" />
          </div>
        </Card>
      </div>

      {/* Main Content */}
      <Card className="flex-1">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="h-full">
          <div className="border-b border-warmgray-200 px-6 py-4">
            <TabsList className="grid w-full grid-cols-6">
              {tabs.map((tab) => {
                const Icon = tab.icon;
                return (
                  <TabsTrigger
                    key={tab.id}
                    value={tab.id}
                    className="flex items-center gap-2 relative"
                  >
                    <Icon className="h-4 w-4" />
                    <span className="hidden sm:inline">{tab.label}</span>
                    {tab.badge && tab.badge > 0 && (
                      <Badge
                        variant="destructive"
                        className="absolute -top-1 -right-1 h-5 w-5 p-0 flex items-center justify-center text-xs"
                      >
                        {tab.badge}
                      </Badge>
                    )}
                  </TabsTrigger>
                );
              })}
            </TabsList>
          </div>

          <div className="flex-1 overflow-hidden">
            <TabsContent value={activeTab} className="h-full m-0">
              <div className="p-6 h-full overflow-y-auto">
                <ActiveComponent />
              </div>
            </TabsContent>
          </div>
        </Tabs>
      </Card>
    </div>
  );
};

export default RiskConfiguration;