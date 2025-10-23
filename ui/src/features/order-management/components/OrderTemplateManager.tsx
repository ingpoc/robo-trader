import React, { useState } from 'react';
import { OrderTemplate, OrderTemplateFormData } from '../types';
import { useOrderStore } from '../stores/orderStore';
import {
  useOrderTemplates,
  useCreateOrderTemplate,
  useUpdateOrderTemplate,
  useDeleteOrderTemplate,
  useApplyOrderTemplate
} from '../hooks/useOrderApi';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import {
  Loader2,
  Plus,
  Edit,
  Trash2,
  Play,
  Star,
  StarOff,
  AlertTriangle,
  CheckCircle
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

interface OrderTemplateManagerProps {
  userId?: string;
  onApplyTemplate?: (template: OrderTemplate) => void;
  className?: string;
}

export const OrderTemplateManager: React.FC<OrderTemplateManagerProps> = ({
  userId,
  onApplyTemplate,
  className = '',
}) => {
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<OrderTemplate | null>(null);
  const [newTag, setNewTag] = useState('');
  const { toast } = useToast();

  const { data: templates, isLoading, error, refetch } = useOrderTemplates(userId);
  const createTemplateMutation = useCreateOrderTemplate();
  const updateTemplateMutation = useUpdateOrderTemplate();
  const deleteTemplateMutation = useDeleteOrderTemplate();
  const applyTemplateMutation = useApplyOrderTemplate();

  const { setTemplateFormData } = useOrderStore();

  const handleCreateTemplate = async (data: OrderTemplateFormData) => {
    try {
      await createTemplateMutation.mutateAsync(data);
      toast({
        title: 'Template Created',
        description: 'Order template has been created successfully.',
      });
      setIsCreateDialogOpen(false);
      setTemplateFormData(null);
    } catch (error: any) {
      toast({
        title: 'Creation Failed',
        description: error.message || 'Failed to create template.',
        variant: 'destructive',
      });
    }
  };

  const handleUpdateTemplate = async (templateId: string, updates: Partial<OrderTemplate>) => {
    try {
      await updateTemplateMutation.mutateAsync({ templateId, updates });
      toast({
        title: 'Template Updated',
        description: 'Order template has been updated successfully.',
      });
      setEditingTemplate(null);
    } catch (error: any) {
      toast({
        title: 'Update Failed',
        description: error.message || 'Failed to update template.',
        variant: 'destructive',
      });
    }
  };

  const handleDeleteTemplate = async (templateId: string) => {
    if (!confirm('Are you sure you want to delete this template?')) return;

    try {
      await deleteTemplateMutation.mutateAsync(templateId);
      toast({
        title: 'Template Deleted',
        description: 'Order template has been deleted successfully.',
      });
    } catch (error: any) {
      toast({
        title: 'Deletion Failed',
        description: error.message || 'Failed to delete template.',
        variant: 'destructive',
      });
    }
  };

  const handleApplyTemplate = async (template: OrderTemplate, overrides?: any) => {
    try {
      const order = await applyTemplateMutation.mutateAsync({
        templateId: template.id,
        overrides,
      });
      toast({
        title: 'Template Applied',
        description: `Order created from template "${template.name}".`,
      });
      onApplyTemplate?.(template);
    } catch (error: any) {
      toast({
        title: 'Application Failed',
        description: error.message || 'Failed to apply template.',
        variant: 'destructive',
      });
    }
  };

  const toggleDefaultTemplate = async (template: OrderTemplate) => {
    await handleUpdateTemplate(template.id, { is_default: !template.is_default });
  };

  if (isLoading) {
    return (
      <Card className={`card-luxury ${className}`}>
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="h-8 w-8 animate-spin text-copper-500" />
          <span className="ml-2 text-body">Loading templates...</span>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className={`card-luxury ${className}`}>
        <CardContent className="py-8">
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>
              Failed to load templates. Please try again.
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-section-title">Order Templates</h2>
          <p className="text-body-muted">Save and reuse your trading strategies</p>
        </div>
        <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
          <DialogTrigger asChild>
            <Button className="btn-luxury-primary">
              <Plus className="mr-2 h-4 w-4" />
              Create Template
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Create Order Template</DialogTitle>
            </DialogHeader>
            <TemplateForm
              onSubmit={handleCreateTemplate}
              onCancel={() => setIsCreateDialogOpen(false)}
            />
          </DialogContent>
        </Dialog>
      </div>

      {/* Templates Grid */}
      {!templates?.length ? (
        <Card className="card-luxury">
          <CardContent className="text-center py-12">
            <div className="text-6xl mb-4">📋</div>
            <h3 className="text-lg font-semibold mb-2">No Templates Yet</h3>
            <p className="text-body-muted mb-4">
              Create your first order template to save time on future trades.
            </p>
            <Button
              onClick={() => setIsCreateDialogOpen(true)}
              className="btn-luxury-primary"
            >
              <Plus className="mr-2 h-4 w-4" />
              Create Your First Template
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {templates.map((template) => (
            <Card key={template.id} className="card-luxury group hover:shadow-copper">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="text-card-title flex items-center gap-2">
                      {template.name}
                      {template.is_default && (
                        <Star className="h-4 w-4 text-copper-500 fill-current" />
                      )}
                    </CardTitle>
                    <p className="text-sm text-body-muted mt-1">{template.description}</p>
                  </div>
                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => toggleDefaultTemplate(template)}
                      className="h-8 w-8 p-0"
                    >
                      {template.is_default ? (
                        <StarOff className="h-4 w-4" />
                      ) : (
                        <Star className="h-4 w-4" />
                      )}
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setEditingTemplate(template)}
                      className="h-8 w-8 p-0"
                    >
                      <Edit className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDeleteTemplate(template.id)}
                      disabled={deleteTemplateMutation.isPending}
                      className="h-8 w-8 p-0 text-rose-600 hover:text-rose-700"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardHeader>

              <CardContent className="space-y-4">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-body-muted">Strategy:</span>
                  <Badge variant="outline">{template.strategy_type}</Badge>
                </div>

                <div className="flex items-center justify-between text-sm">
                  <span className="text-body-muted">Used:</span>
                  <span className="font-medium">{template.usage_count} times</span>
                </div>

                <div className="flex items-center justify-between text-sm">
                  <span className="text-body-muted">Last used:</span>
                  <span className="text-body">
                    {template.last_used
                      ? new Date(template.last_used).toLocaleDateString()
                      : 'Never'
                    }
                  </span>
                </div>

                {template.tags && template.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {template.tags.map((tag) => (
                      <Badge key={tag} variant="secondary" className="text-xs">
                        {tag}
                      </Badge>
                    ))}
                  </div>
                )}

                <div className="flex gap-2 pt-2">
                  <Button
                    onClick={() => handleApplyTemplate(template)}
                    disabled={applyTemplateMutation.isPending}
                    className="btn-luxury-primary flex-1"
                    size="sm"
                  >
                    {applyTemplateMutation.isPending ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <>
                        <Play className="mr-2 h-4 w-4" />
                        Apply
                      </>
                    )}
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Edit Template Dialog */}
      {editingTemplate && (
        <Dialog open={!!editingTemplate} onOpenChange={() => setEditingTemplate(null)}>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Edit Template</DialogTitle>
            </DialogHeader>
            <TemplateForm
              initialData={editingTemplate}
              onSubmit={(data) => handleUpdateTemplate(editingTemplate.id, data)}
              onCancel={() => setEditingTemplate(null)}
            />
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
};

// Template Form Component
interface TemplateFormProps {
  initialData?: Partial<OrderTemplate>;
  onSubmit: (data: OrderTemplateFormData) => void;
  onCancel: () => void;
}

const TemplateForm: React.FC<TemplateFormProps> = ({
  initialData,
  onSubmit,
  onCancel,
}) => {
  const [formData, setFormData] = useState<OrderTemplateFormData>({
    name: initialData?.name || '',
    description: initialData?.description || '',
    strategy_type: initialData?.strategy_type || '',
    order_config: initialData?.order_config || {
      order_type: 'MARKET',
      side: 'BUY',
      quantity_type: 'FIXED',
      quantity_value: 0,
      time_in_force: 'DAY',
    },
    risk_parameters: initialData?.risk_parameters || {},
    tags: initialData?.tags || [],
  });

  const [newTag, setNewTag] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(formData);
  };

  const addTag = () => {
    if (newTag.trim() && !formData.tags.includes(newTag.trim())) {
      setFormData(prev => ({
        ...prev,
        tags: [...prev.tags, newTag.trim()],
      }));
      setNewTag('');
    }
  };

  const removeTag = (tagToRemove: string) => {
    setFormData(prev => ({
      ...prev,
      tags: prev.tags.filter(tag => tag !== tagToRemove),
    }));
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="name">Template Name *</Label>
          <Input
            id="name"
            value={formData.name}
            onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
            placeholder="e.g., Momentum Breakout"
            className="input-luxury"
            required
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="strategy_type">Strategy Type *</Label>
          <Input
            id="strategy_type"
            value={formData.strategy_type}
            onChange={(e) => setFormData(prev => ({ ...prev, strategy_type: e.target.value }))}
            placeholder="e.g., Breakout, Reversal, Scalping"
            className="input-luxury"
            required
          />
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="description">Description</Label>
        <Textarea
          id="description"
          value={formData.description}
          onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
          placeholder="Describe your trading strategy..."
          className="input-luxury min-h-[80px]"
        />
      </div>

      {/* Tags */}
      <div className="space-y-2">
        <Label>Tags</Label>
        <div className="flex flex-wrap gap-2 mb-2">
          {formData.tags.map((tag) => (
            <Badge key={tag} variant="secondary" className="flex items-center gap-1">
              {tag}
              <button
                type="button"
                onClick={() => removeTag(tag)}
                className="ml-1 hover:text-rose-600"
              >
                ×
              </button>
            </Badge>
          ))}
        </div>
        <div className="flex gap-2">
          <Input
            value={newTag}
            onChange={(e) => setNewTag(e.target.value)}
            placeholder="Add tag..."
            className="input-luxury flex-1"
            onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addTag())}
          />
          <Button
            type="button"
            onClick={addTag}
            variant="outline"
            size="sm"
            className="btn-luxury-tertiary"
          >
            <Plus className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <div className="flex gap-3 pt-4">
        <Button type="submit" className="btn-luxury-primary flex-1">
          {initialData ? 'Update Template' : 'Create Template'}
        </Button>
        <Button type="button" variant="outline" onClick={onCancel} className="btn-luxury-secondary">
          Cancel
        </Button>
      </div>
    </form>
  );
};