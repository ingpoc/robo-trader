import React, { useState } from 'react';
import { Plus, Edit, Trash2, TrendingDown, Target, Percent, Clock } from 'lucide-react';
import { useStopLossTemplates, useCreateStopLossTemplate } from '../hooks/useRiskApi';
import { useRiskStore } from '../stores/riskStore';
import { StopLossTemplate, StopLossTemplateFormData } from '../types';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Skeleton } from '@/components/ui/skeleton';
import { useToast } from '@/hooks/use-toast';

const TRIGGER_TYPES = [
  { value: 'FIXED', label: 'Fixed Price' },
  { value: 'TRAILING', label: 'Trailing Stop' },
  { value: 'VOLATILITY_ADJUSTED', label: 'Volatility Adjusted' },
] as const;

export const StopLossTemplates: React.FC = () => {
  const { data: templates, isLoading } = useStopLossTemplates();
  const createTemplateMutation = useCreateStopLossTemplate();
  const { selectedTemplate, setSelectedTemplate } = useRiskStore();
  const { toast } = useToast();

  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [formData, setFormData] = useState<StopLossTemplateFormData>({
    name: '',
    description: '',
    trigger_type: 'TRAILING',
    default_trigger_percent: 15,
    activation_conditions: {
      min_position_size: 1000,
      max_volatility: 0.5,
      sector_restrictions: [],
    },
  });

  const handleCreateTemplate = async () => {
    try {
      await createTemplateMutation.mutateAsync(formData);
      setIsCreateDialogOpen(false);
      setFormData({
        name: '',
        description: '',
        trigger_type: 'TRAILING',
        default_trigger_percent: 15,
        activation_conditions: {
          min_position_size: 1000,
          max_volatility: 0.5,
          sector_restrictions: [],
        },
      });
      toast({
        title: 'Success',
        description: 'Stop-loss template created successfully',
      });
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to create stop-loss template',
        variant: 'destructive',
      });
    }
  };

  const getTriggerTypeIcon = (type: StopLossTemplate['trigger_type']) => {
    switch (type) {
      case 'FIXED':
        return <Target className="h-4 w-4" />;
      case 'TRAILING':
        return <TrendingDown className="h-4 w-4" />;
      case 'VOLATILITY_ADJUSTED':
        return <Percent className="h-4 w-4" />;
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
          <h2 className="text-xl font-semibold text-warmgray-900">Stop-Loss Templates</h2>
          <p className="text-sm text-warmgray-600">
            Create and manage stop-loss templates (fixed, trailing, volatility-adjusted)
          </p>
        </div>

        <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Create Template
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-lg">
            <DialogHeader>
              <DialogTitle>Create Stop-Loss Template</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <Label htmlFor="template-name">Template Name</Label>
                <Input
                  id="template-name"
                  value={formData.name}
                  onChange={(e) =>
                    setFormData({ ...formData, name: e.target.value })
                  }
                  placeholder="e.g., Conservative Trailing Stop"
                />
              </div>

              <div>
                <Label htmlFor="template-description">Description</Label>
                <Input
                  id="template-description"
                  value={formData.description}
                  onChange={(e) =>
                    setFormData({ ...formData, description: e.target.value })
                  }
                  placeholder="Describe when to use this template"
                />
              </div>

              <div>
                <Label htmlFor="trigger-type">Trigger Type</Label>
                <Select
                  value={formData.trigger_type}
                  onValueChange={(value: StopLossTemplate['trigger_type']) =>
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

              <div>
                <Label htmlFor="trigger-percent">Default Trigger Percentage</Label>
                <Input
                  id="trigger-percent"
                  type="number"
                  value={formData.default_trigger_percent}
                  onChange={(e) =>
                    setFormData({ ...formData, default_trigger_percent: parseFloat(e.target.value) })
                  }
                  min="1"
                  max="50"
                />
              </div>

              <div className="space-y-3">
                <Label>Activation Conditions</Label>

                <div>
                  <Label htmlFor="min-position-size" className="text-sm">Minimum Position Size ($)</Label>
                  <Input
                    id="min-position-size"
                    type="number"
                    value={formData.activation_conditions.min_position_size || ''}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        activation_conditions: {
                          ...formData.activation_conditions,
                          min_position_size: parseFloat(e.target.value) || undefined,
                        },
                      })
                    }
                  />
                </div>

                <div>
                  <Label htmlFor="max-volatility" className="text-sm">Maximum Volatility</Label>
                  <Input
                    id="max-volatility"
                    type="number"
                    step="0.01"
                    value={formData.activation_conditions.max_volatility || ''}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        activation_conditions: {
                          ...formData.activation_conditions,
                          max_volatility: parseFloat(e.target.value) || undefined,
                        },
                      })
                    }
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2">
                <Button
                  variant="outline"
                  onClick={() => setIsCreateDialogOpen(false)}
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleCreateTemplate}
                  disabled={createTemplateMutation.isPending}
                >
                  {createTemplateMutation.isPending ? 'Creating...' : 'Create Template'}
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {/* Templates Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {templates?.map((template) => (
          <Card key={template.id} className="p-4 hover:shadow-md transition-shadow">
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-2">
                {getTriggerTypeIcon(template.trigger_type)}
                <h3 className="font-semibold text-warmgray-900">{template.name}</h3>
              </div>
              <Badge variant={template.is_active ? 'default' : 'secondary'}>
                {template.is_active ? 'Active' : 'Inactive'}
              </Badge>
            </div>

            <p className="text-sm text-warmgray-600 mb-3">{template.description}</p>

            <div className="space-y-2 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-warmgray-600">Type:</span>
                <span className="font-medium">
                  {TRIGGER_TYPES.find(t => t.value === template.trigger_type)?.label}
                </span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-warmgray-600">Trigger:</span>
                <span className="font-medium">{template.default_trigger_percent}%</span>
              </div>

              {template.activation_conditions.min_position_size && (
                <div className="flex items-center justify-between">
                  <span className="text-warmgray-600">Min Position:</span>
                  <span className="font-medium">
                    ${template.activation_conditions.min_position_size.toLocaleString()}
                  </span>
                </div>
              )}
            </div>

            <div className="flex items-center justify-between mt-4 pt-3 border-t border-warmgray-200">
              <div className="flex items-center gap-1 text-xs text-warmgray-500">
                <Clock className="h-3 w-3" />
                {new Date(template.updated_at).toLocaleDateString()}
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
        {templates?.length === 0 && (
          <Card className="p-8 text-center col-span-full">
            <TrendingDown className="h-12 w-12 text-warmgray-400 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-warmgray-900 mb-2">No Stop-Loss Templates</h3>
            <p className="text-warmgray-600 mb-4">
              Create your first stop-loss template to automate risk management.
            </p>
            <Button onClick={() => setIsCreateDialogOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Create Template
            </Button>
          </Card>
        )}
      </div>

      {/* Template Usage Stats */}
      {templates && templates.length > 0 && (
        <Card className="p-4">
          <h3 className="font-semibold text-warmgray-900 mb-3">Template Usage Statistics</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-copper-600">{templates.length}</div>
              <div className="text-sm text-warmgray-600">Total Templates</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-emerald-600">
                {templates.filter(t => t.is_active).length}
              </div>
              <div className="text-sm text-warmgray-600">Active Templates</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">
                {templates.filter(t => t.trigger_type === 'TRAILING').length}
              </div>
              <div className="text-sm text-warmgray-600">Trailing Stops</div>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
};