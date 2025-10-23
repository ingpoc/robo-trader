import React, { useState } from 'react';
import { Zap, AlertTriangle, Shield, Clock, User, FileText, Power, PowerOff } from 'lucide-react';
import { useEmergencyOverrides, useCreateEmergencyOverride } from '../hooks/useRiskApi';
import { useRiskStore } from '../stores/riskStore';
import { EmergencyOverride, EmergencyOverrideFormData } from '../types';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { useToast } from '@/hooks/use-toast';

const OVERRIDE_TYPES = [
  {
    value: 'DISABLE_ALL_LIMITS',
    label: 'Disable All Risk Limits',
    description: 'Temporarily disable all risk limits for emergency trading',
    severity: 'CRITICAL',
  },
  {
    value: 'INCREASE_POSITION_LIMITS',
    label: 'Increase Position Limits',
    description: 'Temporarily increase position size limits',
    severity: 'HIGH',
  },
  {
    value: 'DISABLE_STOP_LOSSES',
    label: 'Disable Stop Losses',
    description: 'Temporarily disable all stop-loss orders',
    severity: 'CRITICAL',
  },
  {
    value: 'ALLOW_HIGH_RISK_TRADES',
    label: 'Allow High Risk Trades',
    description: 'Allow trades that exceed normal risk thresholds',
    severity: 'HIGH',
  },
] as const;

export const EmergencyOverrides: React.FC = () => {
  const { data: overrides, isLoading } = useEmergencyOverrides();
  const createOverrideMutation = useCreateEmergencyOverride();
  const { toast } = useToast();

  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [formData, setFormData] = useState<EmergencyOverrideFormData>({
    override_type: 'DISABLE_ALL_LIMITS',
    reason: '',
    justification: '',
    duration_minutes: 60,
  });

  const handleCreateOverride = async () => {
    try {
      await createOverrideMutation.mutateAsync(formData);
      setIsCreateDialogOpen(false);
      setFormData({
        override_type: 'DISABLE_ALL_LIMITS',
        reason: '',
        justification: '',
        duration_minutes: 60,
      });
      toast({
        title: 'Emergency Override Created',
        description: 'The override has been activated. Monitor closely.',
        variant: 'destructive',
      });
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to create emergency override',
        variant: 'destructive',
      });
    }
  };

  const getOverrideTypeInfo = (type: EmergencyOverride['override_type']) => {
    return OVERRIDE_TYPES.find(t => t.value === type);
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'CRITICAL':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'HIGH':
        return 'bg-orange-100 text-orange-800 border-orange-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const activeOverrides = overrides?.filter(o => o.is_active) || [];
  const inactiveOverrides = overrides?.filter(o => !o.is_active) || [];

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <div className="grid gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
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
          <h2 className="text-xl font-semibold text-warmgray-900">Emergency Risk Overrides</h2>
          <p className="text-sm text-warmgray-600">
            Emergency risk override controls for experienced users
          </p>
        </div>

        <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
          <DialogTrigger asChild>
            <Button variant="destructive">
              <Zap className="h-4 w-4 mr-2" />
              Emergency Override
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-lg">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-red-500" />
                Create Emergency Override
              </DialogTitle>
            </DialogHeader>

            <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
              <div className="flex items-start gap-3">
                <AlertTriangle className="h-5 w-5 text-red-500 mt-0.5" />
                <div>
                  <h4 className="font-semibold text-red-800">Warning</h4>
                  <p className="text-sm text-red-700 mt-1">
                    Emergency overrides bypass critical risk controls. Use only in extreme circumstances
                    and monitor positions closely. This action will be logged and may require approval.
                  </p>
                </div>
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <Label htmlFor="override-type">Override Type</Label>
                <Select
                  value={formData.override_type}
                  onValueChange={(value: EmergencyOverride['override_type']) =>
                    setFormData({ ...formData, override_type: value })
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {OVERRIDE_TYPES.map((type) => (
                      <SelectItem key={type.value} value={type.value}>
                        <div className="flex flex-col">
                          <span className="font-medium">{type.label}</span>
                          <span className="text-xs text-warmgray-600">{type.description}</span>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label htmlFor="reason">Reason</Label>
                <Input
                  id="reason"
                  value={formData.reason}
                  onChange={(e) =>
                    setFormData({ ...formData, reason: e.target.value })
                  }
                  placeholder="Brief reason for override"
                />
              </div>

              <div>
                <Label htmlFor="justification">Detailed Justification</Label>
                <Textarea
                  id="justification"
                  value={formData.justification}
                  onChange={(e) =>
                    setFormData({ ...formData, justification: e.target.value })
                  }
                  placeholder="Provide detailed justification for this emergency override"
                  rows={3}
                />
              </div>

              <div>
                <Label htmlFor="duration">Duration (minutes)</Label>
                <Input
                  id="duration"
                  type="number"
                  value={formData.duration_minutes}
                  onChange={(e) =>
                    setFormData({ ...formData, duration_minutes: parseInt(e.target.value) })
                  }
                  min="15"
                  max="480"
                />
                <p className="text-xs text-warmgray-600 mt-1">
                  Maximum 8 hours (480 minutes)
                </p>
              </div>

              <div className="flex justify-end gap-2">
                <Button
                  variant="outline"
                  onClick={() => setIsCreateDialogOpen(false)}
                >
                  Cancel
                </Button>
                <Button
                  variant="destructive"
                  onClick={handleCreateOverride}
                  disabled={createOverrideMutation.isPending}
                >
                  {createOverrideMutation.isPending ? 'Creating...' : 'Activate Override'}
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {/* Active Overrides Warning */}
      {activeOverrides.length > 0 && (
        <Card className="border-red-200 bg-red-50">
          <div className="p-4">
            <div className="flex items-center gap-3">
              <AlertTriangle className="h-6 w-6 text-red-500" />
              <div>
                <h3 className="font-semibold text-red-800">Active Emergency Overrides</h3>
                <p className="text-sm text-red-700">
                  {activeOverrides.length} emergency override{activeOverrides.length > 1 ? 's' : ''} currently active.
                  Risk controls are bypassed. Monitor positions closely.
                </p>
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* Active Overrides */}
      {activeOverrides.length > 0 && (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-warmgray-900">Active Overrides</h3>
          {activeOverrides.map((override) => {
            const typeInfo = getOverrideTypeInfo(override.override_type);
            const expiresAt = new Date(override.expires_at!);
            const now = new Date();
            const timeLeft = Math.max(0, expiresAt.getTime() - now.getTime());
            const minutesLeft = Math.floor(timeLeft / (1000 * 60));

            return (
              <Card key={override.id} className="border-red-200 bg-red-50">
                <div className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-3">
                      <div className="p-2 bg-red-100 rounded-lg">
                        <Zap className="h-5 w-5 text-red-600" />
                      </div>
                      <div>
                        <h4 className="font-semibold text-red-800">{typeInfo?.label}</h4>
                        <p className="text-sm text-red-700 mt-1">{override.reason}</p>
                        <div className="flex items-center gap-4 mt-2 text-xs text-red-600">
                          <div className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {minutesLeft} minutes remaining
                          </div>
                          <div className="flex items-center gap-1">
                            <User className="h-3 w-3" />
                            {override.approved_by || 'Auto-approved'}
                          </div>
                        </div>
                      </div>
                    </div>

                    <Badge className={getSeverityColor(typeInfo?.severity || 'CRITICAL')}>
                      {typeInfo?.severity}
                    </Badge>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {/* Override History */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-warmgray-900">Override History</h3>

        {inactiveOverrides.length === 0 ? (
          <Card className="p-8 text-center">
            <Shield className="h-12 w-12 text-warmgray-400 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-warmgray-900 mb-2">No Override History</h3>
            <p className="text-warmgray-600">
              Emergency overrides will appear here when activated.
            </p>
          </Card>
        ) : (
          <div className="space-y-3">
            {inactiveOverrides.map((override) => {
              const typeInfo = getOverrideTypeInfo(override.override_type);

              return (
                <Card key={override.id} className="p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className={`p-2 rounded-lg ${
                        override.is_active ? 'bg-red-100' : 'bg-warmgray-100'
                      }`}>
                        {override.is_active ? (
                          <Power className="h-4 w-4 text-red-600" />
                        ) : (
                          <PowerOff className="h-4 w-4 text-warmgray-600" />
                        )}
                      </div>
                      <div>
                        <h4 className="font-semibold text-warmgray-900">{typeInfo?.label}</h4>
                        <p className="text-sm text-warmgray-600">{override.reason}</p>
                        <div className="flex items-center gap-4 mt-1 text-xs text-warmgray-500">
                          <span>Activated: {new Date(override.activated_at!).toLocaleString()}</span>
                          <span>By: {override.approved_by || 'System'}</span>
                        </div>
                      </div>
                    </div>

                    <div className="text-right">
                      <Badge variant="outline" className="mb-2">
                        {Math.floor((new Date(override.expires_at!).getTime() - new Date(override.activated_at!).getTime()) / (1000 * 60))} min duration
                      </Badge>
                      <div className="text-xs text-warmgray-500">
                        {new Date(override.created_at).toLocaleDateString()}
                      </div>
                    </div>
                  </div>
                </Card>
              );
            })}
          </div>
        )}
      </div>

      {/* Override Types Reference */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold text-warmgray-900 mb-4">Available Override Types</h3>
        <div className="grid gap-4">
          {OVERRIDE_TYPES.map((type) => (
            <div key={type.value} className="flex items-start gap-3 p-3 border border-warmgray-200 rounded-lg">
              <div className={`p-2 rounded-lg ${
                type.severity === 'CRITICAL' ? 'bg-red-100' : 'bg-orange-100'
              }`}>
                <Zap className={`h-4 w-4 ${
                  type.severity === 'CRITICAL' ? 'text-red-600' : 'text-orange-600'
                }`} />
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <h4 className="font-semibold text-warmgray-900">{type.label}</h4>
                  <Badge className={getSeverityColor(type.severity)}>
                    {type.severity}
                  </Badge>
                </div>
                <p className="text-sm text-warmgray-600">{type.description}</p>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
};