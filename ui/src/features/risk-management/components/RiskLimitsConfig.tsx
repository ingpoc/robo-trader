import React, { useState } from 'react';
import { Plus, Edit, Trash2, AlertTriangle, CheckCircle, Clock, Settings } from 'lucide-react';
import { useRiskLimits, useUpdateRiskLimit, useCreateRiskLimit } from '../hooks/useRiskApi';
import { useRiskStore } from '../stores/riskStore';
import { RiskLimit, RiskLimitFormData } from '../types';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Progress } from '@/components/ui/progress';
import { Skeleton } from '@/components/ui/skeleton';
import { useToast } from '@/hooks/use-toast';

const LIMIT_TYPES = [
  { value: 'POSITION_SIZE', label: 'Position Size Limit' },
  { value: 'SECTOR_CONCENTRATION', label: 'Sector Concentration' },
  { value: 'STOP_LOSS_PERCENTAGE', label: 'Stop Loss Percentage' },
  { value: 'DAILY_LOSS_LIMIT', label: 'Daily Loss Limit' },
  { value: 'PORTFOLIO_BETA', label: 'Portfolio Beta' },
] as const;

export const RiskLimitsConfig: React.FC = () => {
  const { data: riskLimits, isLoading } = useRiskLimits();
  const updateLimitMutation = useUpdateRiskLimit();
  const createLimitMutation = useCreateRiskLimit();
  const { selectedLimit, setSelectedLimit } = useRiskStore();
  const { toast } = useToast();

  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [formData, setFormData] = useState<RiskLimitFormData>({
    limit_type: 'POSITION_SIZE',
    limit_value: 10,
    warning_threshold: 80,
    description: '',
    is_active: true,
  });

  const handleCreateLimit = async () => {
    try {
      await createLimitMutation.mutateAsync(formData);
      setIsCreateDialogOpen(false);
      setFormData({
        limit_type: 'POSITION_SIZE',
        limit_value: 10,
        warning_threshold: 80,
        description: '',
        is_active: true,
      });
      toast({
        title: 'Success',
        description: 'Risk limit created successfully',
      });
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to create risk limit',
        variant: 'destructive',
      });
    }
  };

  const handleUpdateLimit = async () => {
    if (!selectedLimit) return;

    try {
      await updateLimitMutation.mutateAsync({
        limitId: selectedLimit.id,
        updates: formData,
      });
      setIsEditDialogOpen(false);
      setSelectedLimit(null);
      toast({
        title: 'Success',
        description: 'Risk limit updated successfully',
      });
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to update risk limit',
        variant: 'destructive',
      });
    }
  };

  const openEditDialog = (limit: RiskLimit) => {
    setSelectedLimit(limit);
    setFormData({
      limit_type: limit.limit_type,
      limit_value: limit.limit_value,
      warning_threshold: limit.warning_threshold,
      description: limit.description,
      is_active: limit.is_active,
    });
    setIsEditDialogOpen(true);
  };

  const getStatusIcon = (status: RiskLimit['status']) => {
    switch (status) {
      case 'NORMAL':
        return <CheckCircle className="h-4 w-4 text-emerald-500" />;
      case 'WARNING':
        return <Clock className="h-4 w-4 text-copper-500" />;
      case 'CRITICAL':
        return <AlertTriangle className="h-4 w-4 text-rose-500" />;
      default:
        return null;
    }
  };

  const getStatusBadge = (status: RiskLimit['status']) => {
    switch (status) {
      case 'NORMAL':
        return <Badge variant="default" className="bg-emerald-100 text-emerald-800">Normal</Badge>;
      case 'WARNING':
        return <Badge variant="secondary" className="bg-copper-100 text-copper-800">Warning</Badge>;
      case 'CRITICAL':
        return <Badge variant="destructive">Critical</Badge>;
      default:
        return null;
    }
  };

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
          <h2 className="text-xl font-semibold text-warmgray-900">Risk Limits Configuration</h2>
          <p className="text-sm text-warmgray-600">
            Configure dynamic risk limits per sector, symbol, and position size
          </p>
        </div>

        <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Add Limit
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>Create Risk Limit</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <Label htmlFor="limit-type">Limit Type</Label>
                <Select
                  value={formData.limit_type}
                  onValueChange={(value: RiskLimit['limit_type']) =>
                    setFormData({ ...formData, limit_type: value })
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {LIMIT_TYPES.map((type) => (
                      <SelectItem key={type.value} value={type.value}>
                        {type.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label htmlFor="limit-value">Limit Value</Label>
                <Input
                  id="limit-value"
                  type="number"
                  value={formData.limit_value}
                  onChange={(e) =>
                    setFormData({ ...formData, limit_value: parseFloat(e.target.value) })
                  }
                />
              </div>

              <div>
                <Label htmlFor="warning-threshold">Warning Threshold (%)</Label>
                <Input
                  id="warning-threshold"
                  type="number"
                  value={formData.warning_threshold}
                  onChange={(e) =>
                    setFormData({ ...formData, warning_threshold: parseFloat(e.target.value) })
                  }
                />
              </div>

              <div>
                <Label htmlFor="description">Description</Label>
                <Input
                  id="description"
                  value={formData.description}
                  onChange={(e) =>
                    setFormData({ ...formData, description: e.target.value })
                  }
                  placeholder="Describe this risk limit"
                />
              </div>

              <div className="flex items-center space-x-2">
                <Switch
                  id="is-active"
                  checked={formData.is_active}
                  onCheckedChange={(checked) =>
                    setFormData({ ...formData, is_active: checked })
                  }
                />
                <Label htmlFor="is-active">Active</Label>
              </div>

              <div className="flex justify-end gap-2">
                <Button
                  variant="outline"
                  onClick={() => setIsCreateDialogOpen(false)}
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleCreateLimit}
                  disabled={createLimitMutation.isPending}
                >
                  {createLimitMutation.isPending ? 'Creating...' : 'Create'}
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {/* Risk Limits Table */}
      <Card>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Type</TableHead>
              <TableHead>Limit Value</TableHead>
              <TableHead>Current Usage</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Description</TableHead>
              <TableHead>Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {riskLimits?.map((limit) => (
              <TableRow key={limit.id}>
                <TableCell className="font-medium">
                  {LIMIT_TYPES.find(t => t.value === limit.limit_type)?.label}
                </TableCell>
                <TableCell>{limit.limit_value}%</TableCell>
                <TableCell>
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm">{limit.utilization_percent.toFixed(1)}%</span>
                      {getStatusIcon(limit.status)}
                    </div>
                    <Progress
                      value={limit.utilization_percent}
                      className="w-20 h-2"
                    />
                  </div>
                </TableCell>
                <TableCell>{getStatusBadge(limit.status)}</TableCell>
                <TableCell className="max-w-xs truncate">{limit.description}</TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => openEditDialog(limit)}
                    >
                      <Edit className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="sm">
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>

      {/* Edit Dialog */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Edit Risk Limit</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label htmlFor="edit-limit-value">Limit Value</Label>
              <Input
                id="edit-limit-value"
                type="number"
                value={formData.limit_value}
                onChange={(e) =>
                  setFormData({ ...formData, limit_value: parseFloat(e.target.value) })
                }
              />
            </div>

            <div>
              <Label htmlFor="edit-warning-threshold">Warning Threshold (%)</Label>
              <Input
                id="edit-warning-threshold"
                type="number"
                value={formData.warning_threshold}
                onChange={(e) =>
                  setFormData({ ...formData, warning_threshold: parseFloat(e.target.value) })
                }
              />
            </div>

            <div>
              <Label htmlFor="edit-description">Description</Label>
              <Input
                id="edit-description"
                value={formData.description}
                onChange={(e) =>
                  setFormData({ ...formData, description: e.target.value })
                }
              />
            </div>

            <div className="flex items-center space-x-2">
              <Switch
                id="edit-is-active"
                checked={formData.is_active}
                onCheckedChange={(checked) =>
                  setFormData({ ...formData, is_active: checked })
                }
              />
              <Label htmlFor="edit-is-active">Active</Label>
            </div>

            <div className="flex justify-end gap-2">
              <Button
                variant="outline"
                onClick={() => setIsEditDialogOpen(false)}
              >
                Cancel
              </Button>
              <Button
                onClick={handleUpdateLimit}
                disabled={updateLimitMutation.isPending}
              >
                {updateLimitMutation.isPending ? 'Updating...' : 'Update'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};