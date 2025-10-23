import React, { useState } from 'react';
import { Plus, Edit, Trash2, BarChart3, Calendar, Target, RotateCcw, Play, Pause } from 'lucide-react';
import { useRebalancingRules, useCreateRebalancingRule } from '../hooks/useRiskApi';
import { useRiskStore } from '../stores/riskStore';
import { RebalancingRule, RebalancingRuleFormData } from '../types';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import { Skeleton } from '@/components/ui/skeleton';
import { useToast } from '@/hooks/use-toast';

const TRIGGER_TYPES = [
  { value: 'PERIODIC', label: 'Periodic' },
  { value: 'THRESHOLD', label: 'Threshold-based' },
  { value: 'EVENT_BASED', label: 'Event-based' },
] as const;

const STRATEGIES = [
  { value: 'EQUAL_WEIGHT', label: 'Equal Weight' },
  { value: 'TARGET_WEIGHTS', label: 'Target Weights' },
  { value: 'RISK_PARITY', label: 'Risk Parity' },
] as const;

const FREQUENCIES = [
  { value: 'DAILY', label: 'Daily' },
  { value: 'WEEKLY', label: 'Weekly' },
  { value: 'MONTHLY', label: 'Monthly' },
] as const;

export const RebalancingRules: React.FC = () => {
  const { data: rules, isLoading } = useRebalancingRules();
  const createRuleMutation = useCreateRebalancingRule();
  const { selectedRule, setSelectedRule } = useRiskStore();
  const { toast } = useToast();

  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [formData, setFormData] = useState<RebalancingRuleFormData>({
    name: '',
    description: '',
    trigger_type: 'PERIODIC',
    trigger_config: {
      frequency: 'MONTHLY',
      threshold_percent: 5,
    },
    rebalancing_strategy: 'EQUAL_WEIGHT',
    target_allocations: {},
    excluded_assets: [],
  });

  const handleCreateRule = async () => {
    try {
      await createRuleMutation.mutateAsync(formData);
      setIsCreateDialogOpen(false);
      setFormData({
        name: '',
        description: '',
        trigger_type: 'PERIODIC',
        trigger_config: {
          frequency: 'MONTHLY',
          threshold_percent: 5,
        },
        rebalancing_strategy: 'EQUAL_WEIGHT',
        target_allocations: {},
        excluded_assets: [],
      });
      toast({
        title: 'Success',
        description: 'Rebalancing rule created successfully',
      });
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to create rebalancing rule',
        variant: 'destructive',
      });
    }
  };

  const getTriggerTypeIcon = (type: RebalancingRule['trigger_type']) => {
    switch (type) {
      case 'PERIODIC':
        return <Calendar className="h-4 w-4" />;
      case 'THRESHOLD':
        return <Target className="h-4 w-4" />;
      case 'EVENT_BASED':
        return <BarChart3 className="h-4 w-4" />;
      default:
        return null;
    }
  };

  const getStrategyIcon = (strategy: RebalancingRule['rebalancing_strategy']) => {
    switch (strategy) {
      case 'EQUAL_WEIGHT':
        return <RotateCcw className="h-4 w-4" />;
      case 'TARGET_WEIGHTS':
        return <Target className="h-4 w-4" />;
      case 'RISK_PARITY':
        return <BarChart3 className="h-4 w-4" />;
      default:
        return null;
    }
  };

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
          <h2 className="text-xl font-semibold text-warmgray-900">Portfolio Rebalancing Rules</h2>
          <p className="text-sm text-warmgray-600">
            Set up portfolio rebalancing rules and thresholds
          </p>
        </div>

        <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Create Rule
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-lg">
            <DialogHeader>
              <DialogTitle>Create Rebalancing Rule</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <Label htmlFor="rule-name">Rule Name</Label>
                <Input
                  id="rule-name"
                  value={formData.name}
                  onChange={(e) =>
                    setFormData({ ...formData, name: e.target.value })
                  }
                  placeholder="e.g., Monthly Equal Weight Rebalancing"
                />
              </div>

              <div>
                <Label htmlFor="rule-description">Description</Label>
                <Textarea
                  id="rule-description"
                  value={formData.description}
                  onChange={(e) =>
                    setFormData({ ...formData, description: e.target.value })
                  }
                  placeholder="Describe the rebalancing strategy"
                  rows={2}
                />
              </div>

              <div>
                <Label htmlFor="trigger-type">Trigger Type</Label>
                <Select
                  value={formData.trigger_type}
                  onValueChange={(value: RebalancingRule['trigger_type']) =>
                    setFormData({ ...formData, trigger_type: value })
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {TRIGGER_TYPES.map((type) => (
                      <SelectItem key={type.value} value={type.value}>
                        {type.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {formData.trigger_type === 'PERIODIC' && (
                <div>
                  <Label htmlFor="frequency">Frequency</Label>
                  <Select
                    value={formData.trigger_config.frequency}
                    onValueChange={(value) =>
                      setFormData({
                        ...formData,
                        trigger_config: { ...formData.trigger_config, frequency: value as any },
                      })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {FREQUENCIES.map((freq) => (
                        <SelectItem key={freq.value} value={freq.value}>
                          {freq.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}

              {formData.trigger_type === 'THRESHOLD' && (
                <div>
                  <Label htmlFor="threshold">Threshold Percentage</Label>
                  <Input
                    id="threshold"
                    type="number"
                    value={formData.trigger_config.threshold_percent || ''}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        trigger_config: {
                          ...formData.trigger_config,
                          threshold_percent: parseFloat(e.target.value) || 5,
                        },
                      })
                    }
                    min="1"
                    max="50"
                  />
                </div>
              )}

              <div>
                <Label htmlFor="strategy">Rebalancing Strategy</Label>
                <Select
                  value={formData.rebalancing_strategy}
                  onValueChange={(value: RebalancingRule['rebalancing_strategy']) =>
                    setFormData({ ...formData, rebalancing_strategy: value })
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {STRATEGIES.map((strategy) => (
                      <SelectItem key={strategy.value} value={strategy.value}>
                        {strategy.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {formData.rebalancing_strategy === 'TARGET_WEIGHTS' && (
                <div>
                  <Label htmlFor="target-allocations">Target Allocations (JSON)</Label>
                  <Textarea
                    id="target-allocations"
                    value={JSON.stringify(formData.target_allocations, null, 2)}
                    onChange={(e) => {
                      try {
                        const allocations = JSON.parse(e.target.value);
                        setFormData({ ...formData, target_allocations: allocations });
                      } catch {
                        // Invalid JSON, keep current value
                      }
                    }}
                    placeholder='{"AAPL": 0.3, "MSFT": 0.2, "GOOGL": 0.5}'
                    rows={3}
                  />
                </div>
              )}

              <div className="flex justify-end gap-2">
                <Button
                  variant="outline"
                  onClick={() => setIsCreateDialogOpen(false)}
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleCreateRule}
                  disabled={createRuleMutation.isPending}
                >
                  {createRuleMutation.isPending ? 'Creating...' : 'Create Rule'}
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {/* Rules Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {rules?.map((rule) => (
          <Card key={rule.id} className="p-4 hover:shadow-md transition-shadow">
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-2">
                {getTriggerTypeIcon(rule.trigger_type)}
                <h3 className="font-semibold text-warmgray-900">{rule.name}</h3>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant={rule.is_active ? 'default' : 'secondary'}>
                  {rule.is_active ? 'Active' : 'Inactive'}
                </Badge>
                {rule.is_active ? (
                  <Play className="h-4 w-4 text-emerald-500" />
                ) : (
                  <Pause className="h-4 w-4 text-warmgray-400" />
                )}
              </div>
            </div>

            <p className="text-sm text-warmgray-600 mb-3">{rule.description}</p>

            <div className="space-y-2 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-warmgray-600">Trigger:</span>
                <div className="flex items-center gap-1">
                  {getTriggerTypeIcon(rule.trigger_type)}
                  <span className="font-medium">
                    {rule.trigger_type === 'PERIODIC'
                      ? rule.trigger_config.frequency
                      : rule.trigger_type === 'THRESHOLD'
                      ? `${rule.trigger_config.threshold_percent}%`
                      : 'Event-based'}
                  </span>
                </div>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-warmgray-600">Strategy:</span>
                <div className="flex items-center gap-1">
                  {getStrategyIcon(rule.rebalancing_strategy)}
                  <span className="font-medium">
                    {STRATEGIES.find(s => s.value === rule.rebalancing_strategy)?.label}
                  </span>
                </div>
              </div>

              {rule.last_executed && (
                <div className="flex items-center justify-between">
                  <span className="text-warmgray-600">Last Executed:</span>
                  <span className="font-medium">
                    {new Date(rule.last_executed).toLocaleDateString()}
                  </span>
                </div>
              )}
            </div>

            <div className="flex items-center justify-between mt-4 pt-3 border-t border-warmgray-200">
              <div className="text-xs text-warmgray-500">
                Created {new Date(rule.created_at).toLocaleDateString()}
              </div>

              <div className="flex items-center gap-2">
                <Button variant="ghost" size="sm">
                  <Edit className="h-4 w-4" />
                </Button>
                <Button variant="ghost" size="sm">
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </Card>
        ))}

        {/* Empty State */}
        {rules?.length === 0 && (
          <Card className="p-8 text-center col-span-full">
            <BarChart3 className="h-12 w-12 text-warmgray-400 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-warmgray-900 mb-2">No Rebalancing Rules</h3>
            <p className="text-warmgray-600 mb-4">
              Create automated rebalancing rules to maintain your target portfolio allocations.
            </p>
            <Button onClick={() => setIsCreateDialogOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Create Rule
            </Button>
          </Card>
        )}
      </div>

      {/* Rules Summary */}
      {rules && rules.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card className="p-4">
            <div className="flex items-center gap-3">
              <Calendar className="h-8 w-8 text-copper-500" />
              <div>
                <div className="text-2xl font-bold text-warmgray-900">
                  {rules.filter(r => r.trigger_type === 'PERIODIC').length}
                </div>
                <div className="text-sm text-warmgray-600">Periodic Rules</div>
              </div>
            </div>
          </Card>

          <Card className="p-4">
            <div className="flex items-center gap-3">
              <Target className="h-8 w-8 text-emerald-500" />
              <div>
                <div className="text-2xl font-bold text-warmgray-900">
                  {rules.filter(r => r.trigger_type === 'THRESHOLD').length}
                </div>
                <div className="text-sm text-warmgray-600">Threshold Rules</div>
              </div>
            </div>
          </Card>

          <Card className="p-4">
            <div className="flex items-center gap-3">
              <RotateCcw className="h-8 w-8 text-blue-500" />
              <div>
                <div className="text-2xl font-bold text-warmgray-900">
                  {rules.filter(r => r.is_active).length}
                </div>
                <div className="text-sm text-warmgray-600">Active Rules</div>
              </div>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
};