import React, { useState } from 'react';
import { AlertTriangle, CheckCircle, Bell, BellOff, Clock, Filter, Search } from 'lucide-react';
import { useRiskAlerts, useAcknowledgeAlert } from '../hooks/useRiskApi';
import { RiskAlert } from '../types';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Skeleton } from '@/components/ui/skeleton';
import { useToast } from '@/hooks/use-toast';

const SEVERITY_LEVELS = [
  { value: 'LOW', label: 'Low', color: 'bg-blue-100 text-blue-800' },
  { value: 'MEDIUM', label: 'Medium', color: 'bg-copper-100 text-copper-800' },
  { value: 'HIGH', label: 'High', color: 'bg-orange-100 text-orange-800' },
  { value: 'CRITICAL', label: 'Critical', color: 'bg-red-100 text-red-800' },
] as const;

export const RiskAlertsPanel: React.FC = () => {
  const [filters, setFilters] = useState({
    severity: '',
    type: '',
    search: '',
  });

  const { data: alertsData, isLoading } = useRiskAlerts(undefined, {
    severity: filters.severity || undefined,
    type: filters.type || undefined,
  });

  const acknowledgeMutation = useAcknowledgeAlert();
  const { toast } = useToast();

  const handleAcknowledgeAlert = async (alertId: string) => {
    try {
      await acknowledgeMutation.mutateAsync({
        alertId,
        acknowledgedBy: 'user_123', // This would come from auth context
        notes: 'Acknowledged via UI',
      });
      toast({
        title: 'Success',
        description: 'Alert acknowledged successfully',
      });
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to acknowledge alert',
        variant: 'destructive',
      });
    }
  };

  const getSeverityBadge = (severity: RiskAlert['severity']) => {
    const level = SEVERITY_LEVELS.find(l => l.value === severity);
    return (
      <Badge className={level?.color || 'bg-gray-100 text-gray-800'}>
        {level?.label || severity}
      </Badge>
    );
  };

  const getSeverityIcon = (severity: RiskAlert['severity']) => {
    switch (severity) {
      case 'CRITICAL':
        return <AlertTriangle className="h-4 w-4 text-red-500" />;
      case 'HIGH':
        return <AlertTriangle className="h-4 w-4 text-orange-500" />;
      case 'MEDIUM':
        return <Clock className="h-4 w-4 text-copper-500" />;
      case 'LOW':
        return <Bell className="h-4 w-4 text-blue-500" />;
      default:
        return <Bell className="h-4 w-4 text-gray-500" />;
    }
  };

  const filteredAlerts = alertsData?.data.filter(alert => {
    const matchesSearch = !filters.search ||
      alert.title.toLowerCase().includes(filters.search.toLowerCase()) ||
      alert.message.toLowerCase().includes(filters.search.toLowerCase());
    return matchesSearch;
  }) || [];

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <div className="grid gap-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <Card key={i} className="p-4">
              <Skeleton className="h-4 w-full mb-2" />
              <Skeleton className="h-4 w-3/4" />
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
          <h2 className="text-xl font-semibold text-warmgray-900">Risk Alerts & Notifications</h2>
          <p className="text-sm text-warmgray-600">
            Monitor and manage risk alerts and notifications
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Badge variant="outline" className="px-3 py-1">
            {filteredAlerts.filter(a => !a.is_acknowledged).length} Unacknowledged
          </Badge>
        </div>
      </div>

      {/* Filters */}
      <Card className="p-4">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-warmgray-400" />
              <Input
                placeholder="Search alerts..."
                value={filters.search}
                onChange={(e) => setFilters({ ...filters, search: e.target.value })}
                className="pl-10"
              />
            </div>
          </div>

          <Select
            value={filters.severity}
            onValueChange={(value) => setFilters({ ...filters, severity: value })}
          >
            <SelectTrigger className="w-full sm:w-40">
              <SelectValue placeholder="All Severities" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">All Severities</SelectItem>
              {SEVERITY_LEVELS.map((level) => (
                <SelectItem key={level.value} value={level.value}>
                  {level.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select
            value={filters.type}
            onValueChange={(value) => setFilters({ ...filters, type: value })}
          >
            <SelectTrigger className="w-full sm:w-48">
              <SelectValue placeholder="All Types" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">All Types</SelectItem>
              <SelectItem value="LIMIT_BREACH_WARNING">Limit Breach</SelectItem>
              <SelectItem value="STOP_LOSS_TRIGGERED">Stop Loss Triggered</SelectItem>
              <SelectItem value="HIGH_VOLATILITY">High Volatility</SelectItem>
              <SelectItem value="SECTOR_RISK_SPIKE">Sector Risk Spike</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </Card>

      {/* Alerts Table */}
      <Card>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Status</TableHead>
              <TableHead>Severity</TableHead>
              <TableHead>Title</TableHead>
              <TableHead>Message</TableHead>
              <TableHead>Created</TableHead>
              <TableHead>Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredAlerts.map((alert) => (
              <TableRow key={alert.id} className={!alert.is_acknowledged ? 'bg-copper-50/50' : ''}>
                <TableCell>
                  <div className="flex items-center gap-2">
                    {alert.is_acknowledged ? (
                      <CheckCircle className="h-4 w-4 text-emerald-500" />
                    ) : (
                      <Bell className="h-4 w-4 text-copper-500" />
                    )}
                    <span className="text-sm">
                      {alert.is_acknowledged ? 'Acknowledged' : 'Active'}
                    </span>
                  </div>
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    {getSeverityIcon(alert.severity)}
                    {getSeverityBadge(alert.severity)}
                  </div>
                </TableCell>
                <TableCell className="font-medium">{alert.title}</TableCell>
                <TableCell className="max-w-xs truncate">{alert.message}</TableCell>
                <TableCell className="text-sm text-warmgray-600">
                  {new Date(alert.created_at).toLocaleString()}
                </TableCell>
                <TableCell>
                  {!alert.is_acknowledged && (
                    <Button
                      size="sm"
                      onClick={() => handleAcknowledgeAlert(alert.id)}
                      disabled={acknowledgeMutation.isPending}
                    >
                      {acknowledgeMutation.isPending ? 'Acknowledging...' : 'Acknowledge'}
                    </Button>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>

        {filteredAlerts.length === 0 && (
          <div className="text-center py-8">
            <BellOff className="h-12 w-12 text-warmgray-400 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-warmgray-900 mb-2">No Alerts Found</h3>
            <p className="text-warmgray-600">
              {alertsData?.data.length === 0
                ? 'No risk alerts have been generated yet.'
                : 'No alerts match your current filters.'}
            </p>
          </div>
        )}
      </Card>

      {/* Alert Summary */}
      {alertsData && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card className="p-4">
            <div className="flex items-center gap-3">
              <AlertTriangle className="h-8 w-8 text-red-500" />
              <div>
                <div className="text-2xl font-bold text-warmgray-900">
                  {alertsData.summary.critical_count}
                </div>
                <div className="text-sm text-warmgray-600">Critical</div>
              </div>
            </div>
          </Card>

          <Card className="p-4">
            <div className="flex items-center gap-3">
              <AlertTriangle className="h-8 w-8 text-orange-500" />
              <div>
                <div className="text-2xl font-bold text-warmgray-900">
                  {alertsData.summary.high_count}
                </div>
                <div className="text-sm text-warmgray-600">High</div>
              </div>
            </div>
          </Card>

          <Card className="p-4">
            <div className="flex items-center gap-3">
              <Clock className="h-8 w-8 text-copper-500" />
              <div>
                <div className="text-2xl font-bold text-warmgray-900">
                  {alertsData.summary.medium_count}
                </div>
                <div className="text-sm text-warmgray-600">Medium</div>
              </div>
            </div>
          </Card>

          <Card className="p-4">
            <div className="flex items-center gap-3">
              <Bell className="h-8 w-8 text-blue-500" />
              <div>
                <div className="text-2xl font-bold text-warmgray-900">
                  {alertsData.summary.low_count}
                </div>
                <div className="text-sm text-warmgray-600">Low</div>
              </div>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
};