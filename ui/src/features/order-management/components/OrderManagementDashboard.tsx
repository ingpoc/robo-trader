import React, { useState } from 'react';
import { Order, OrderMonitoringStatus, OrderStatistics } from '../types';
import { useOrderStore } from '../stores/orderStore';
import { useOrderMonitoringStatus, useOrderStatistics } from '../hooks/useOrderApi';
import { useOrderWebSocket, useOrderMonitoringWebSocket } from '../hooks/useOrderWebSocket';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Activity,
  TrendingUp,
  TrendingDown,
  DollarSign,
  BarChart3,
  AlertTriangle,
  CheckCircle,
  Clock,
  XCircle,
  RefreshCw,
  Zap
} from 'lucide-react';

interface OrderManagementDashboardProps {
  userId?: string;
  className?: string;
}

export const OrderManagementDashboard: React.FC<OrderManagementDashboardProps> = ({
  userId,
  className = '',
}) => {
  const [activeTab, setActiveTab] = useState('overview');
  const { monitoringStatus, orderStatistics } = useOrderStore();

  // WebSocket connections
  const { isConnected: ordersConnected } = useOrderWebSocket(userId);
  const { isConnected: monitoringConnected } = useOrderMonitoringWebSocket(userId);

  // API queries
  const { data: monitoringData, isLoading: monitoringLoading, refetch: refetchMonitoring } = useOrderMonitoringStatus(userId);
  const { data: statisticsData, isLoading: statisticsLoading, refetch: refetchStatistics } = useOrderStatistics(userId);

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(value);
  };

  const formatPercentage = (value: number) => {
    return `${(value * 100).toFixed(2)}%`;
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'online':
      case 'active':
        return 'text-emerald-600';
      case 'warning':
        return 'text-copper-600';
      case 'error':
      case 'offline':
        return 'text-rose-600';
      default:
        return 'text-warmgray-600';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'online':
      case 'active':
        return <CheckCircle className="h-4 w-4" />;
      case 'warning':
        return <AlertTriangle className="h-4 w-4" />;
      case 'error':
      case 'offline':
        return <XCircle className="h-4 w-4" />;
      default:
        return <Clock className="h-4 w-4" />;
    }
  };

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Connection Status */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${ordersConnected ? 'bg-emerald-500' : 'bg-rose-500'}`} />
          <span className="text-sm text-body">Orders: {ordersConnected ? 'Connected' : 'Disconnected'}</span>
        </div>
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${monitoringConnected ? 'bg-emerald-500' : 'bg-rose-500'}`} />
          <span className="text-sm text-body">Monitoring: {monitoringConnected ? 'Connected' : 'Disconnected'}</span>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            refetchMonitoring();
            refetchStatistics();
          }}
          className="btn-luxury-tertiary"
        >
          <RefreshCw className="h-4 w-4 mr-1" />
          Refresh
        </Button>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="performance">Performance</TabsTrigger>
          <TabsTrigger value="risk">Risk</TabsTrigger>
          <TabsTrigger value="activity">Activity</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          {/* Key Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <Card className="card-luxury">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-body-muted">Active Orders</p>
                    <p className="text-3xl font-bold text-copper-600">
                      {monitoringData?.active_orders || 0}
                    </p>
                  </div>
                  <Activity className="h-8 w-8 text-copper-500" />
                </div>
              </CardContent>
            </Card>

            <Card className="card-luxury">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-body-muted">Total Value</p>
                    <p className="text-3xl font-bold text-emerald-600">
                      {formatCurrency(monitoringData?.total_value || 0)}
                    </p>
                  </div>
                  <DollarSign className="h-8 w-8 text-emerald-500" />
                </div>
              </CardContent>
            </Card>

            <Card className="card-luxury">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-body-muted">Unrealized P&L</p>
                    <p className={`text-3xl font-bold ${
                      (monitoringData?.unrealized_pnl || 0) >= 0
                        ? 'text-emerald-600'
                        : 'text-rose-600'
                    }`}>
                      {formatCurrency(monitoringData?.unrealized_pnl || 0)}
                    </p>
                  </div>
                  {(monitoringData?.unrealized_pnl || 0) >= 0 ? (
                    <TrendingUp className="h-8 w-8 text-emerald-500" />
                  ) : (
                    <TrendingDown className="h-8 w-8 text-rose-500" />
                  )}
                </div>
              </CardContent>
            </Card>

            <Card className="card-luxury">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-body-muted">Buying Power</p>
                    <p className="text-3xl font-bold text-warmgray-900 dark:text-warmgray-100">
                      {formatCurrency(monitoringData?.buying_power || 0)}
                    </p>
                  </div>
                  <BarChart3 className="h-8 w-8 text-warmgray-500" />
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Order Status Breakdown */}
          <Card className="card-luxury">
            <CardHeader>
              <CardTitle className="text-card-title">Order Status</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="text-center p-4 bg-emerald-50 dark:bg-emerald-950/20 rounded-lg">
                  <div className="text-2xl font-bold text-emerald-600">
                    {statisticsData?.orders_by_status?.FILLED || 0}
                  </div>
                  <div className="text-sm text-body-muted">Filled</div>
                </div>
                <div className="text-center p-4 bg-copper-50 dark:bg-copper-950/20 rounded-lg">
                  <div className="text-2xl font-bold text-copper-600">
                    {statisticsData?.orders_by_status?.PENDING || 0}
                  </div>
                  <div className="text-sm text-body-muted">Pending</div>
                </div>
                <div className="text-center p-4 bg-rose-50 dark:bg-rose-950/20 rounded-lg">
                  <div className="text-2xl font-bold text-rose-600">
                    {statisticsData?.orders_by_status?.CANCELLED || 0}
                  </div>
                  <div className="text-sm text-body-muted">Cancelled</div>
                </div>
                <div className="text-center p-4 bg-warmgray-100 dark:bg-warmgray-800 rounded-lg">
                  <div className="text-2xl font-bold text-warmgray-600">
                    {statisticsData?.orders_by_status?.REJECTED || 0}
                  </div>
                  <div className="text-sm text-body-muted">Rejected</div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="performance" className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card className="card-luxury">
              <CardHeader>
                <CardTitle className="text-card-title">Trading Performance</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-body">Win Rate</span>
                  <span className="font-semibold text-emerald-600">
                    {formatPercentage(statisticsData?.win_rate || 0)}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-body">Profit Factor</span>
                  <span className="font-semibold">
                    {(statisticsData?.profit_factor || 0).toFixed(2)}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-body">Avg Win</span>
                  <span className="font-semibold text-emerald-600">
                    {formatCurrency(statisticsData?.average_win || 0)}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-body">Avg Loss</span>
                  <span className="font-semibold text-rose-600">
                    {formatCurrency(statisticsData?.average_loss || 0)}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-body">Max Drawdown</span>
                  <span className="font-semibold text-rose-600">
                    {formatPercentage(statisticsData?.max_drawdown || 0)}
                  </span>
                </div>
              </CardContent>
            </Card>

            <Card className="card-luxury">
              <CardHeader>
                <CardTitle className="text-card-title">Risk Metrics</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-body">Sharpe Ratio</span>
                  <span className="font-semibold">
                    {(statisticsData?.sharpe_ratio || 0).toFixed(2)}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-body">Sortino Ratio</span>
                  <span className="font-semibold">
                    {(statisticsData?.sortino_ratio || 0).toFixed(2)}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-body">Total Return</span>
                  <span className="font-semibold text-emerald-600">
                    {formatCurrency(statisticsData?.total_return || 0)}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-body">Total Commission</span>
                  <span className="font-semibold text-rose-600">
                    {formatCurrency(statisticsData?.total_commission || 0)}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-body">Best Trade</span>
                  <span className="font-semibold text-emerald-600">
                    {formatCurrency(statisticsData?.best_trade || 0)}
                  </span>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="risk" className="space-y-6">
          <Card className="card-luxury">
            <CardHeader>
              <CardTitle className="text-card-title">Risk Exposure</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="text-center p-6 bg-warmgray-50 dark:bg-warmgray-800/50 rounded-lg">
                  <div className="text-3xl font-bold text-copper-600 mb-2">
                    {formatCurrency(monitoringData?.risk_exposure || 0)}
                  </div>
                  <div className="text-sm text-body-muted">Risk Exposure</div>
                </div>
                <div className="text-center p-6 bg-warmgray-50 dark:bg-warmgray-800/50 rounded-lg">
                  <div className="text-3xl font-bold text-warmgray-600 mb-2">
                    {formatCurrency(monitoringData?.margin_used || 0)}
                  </div>
                  <div className="text-sm text-body-muted">Margin Used</div>
                </div>
                <div className="text-center p-6 bg-emerald-50 dark:bg-emerald-950/20 rounded-lg">
                  <div className="text-3xl font-bold text-emerald-600 mb-2">
                    {formatCurrency((monitoringData?.buying_power || 0) - (monitoringData?.margin_used || 0))}
                  </div>
                  <div className="text-sm text-body-muted">Available Margin</div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="activity" className="space-y-6">
          <Card className="card-luxury">
            <CardHeader>
              <CardTitle className="text-card-title">Recent Activity</CardTitle>
            </CardHeader>
            <CardContent>
              {monitoringData?.last_update ? (
                <div className="text-center py-8">
                  <Zap className="h-12 w-12 text-copper-500 mx-auto mb-4" />
                  <p className="text-body-muted">
                    Last updated: {new Date(monitoringData.last_update).toLocaleString()}
                  </p>
                  <p className="text-sm text-body-muted mt-2">
                    Real-time order monitoring active
                  </p>
                </div>
              ) : (
                <div className="text-center py-8">
                  <AlertTriangle className="h-12 w-12 text-warmgray-400 mx-auto mb-4" />
                  <p className="text-body-muted">No recent activity data available</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};