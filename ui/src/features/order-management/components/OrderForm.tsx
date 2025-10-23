import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { OrderFormData, OrderType, TimeInForce } from '../types';
import { useOrderStore } from '../stores/orderStore';
import { useCreateOrder } from '../hooks/useOrderApi';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, Plus, X } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

// Form validation schema
const orderFormSchema = z.object({
  symbol: z.string().min(1, 'Symbol is required').max(10, 'Symbol too long'),
  side: z.enum(['BUY', 'SELL']),
  quantity: z.number().min(0.01, 'Quantity must be greater than 0'),
  order_type: z.enum(['MARKET', 'LIMIT', 'STOP', 'STOP_LIMIT', 'TRAILING_STOP', 'BRACKET', 'OCO', 'CONDITIONAL', 'ICEBERG', 'TWAP', 'VWAP']),
  price: z.number().optional(),
  stop_price: z.number().optional(),
  limit_price: z.number().optional(),
  trail_percent: z.number().optional(),
  time_in_force: z.enum(['DAY', 'GTC', 'GTD', 'IOC', 'FOK', 'GTX']),
  expiration_date: z.string().optional(),
  notes: z.string().optional(),
  tags: z.array(z.string()).optional(),
});

type OrderFormValues = z.infer<typeof orderFormSchema>;

interface OrderFormProps {
  onSuccess?: (order: any) => void;
  onCancel?: () => void;
  initialData?: Partial<OrderFormData>;
  className?: string;
}

export const OrderForm: React.FC<OrderFormProps> = ({
  onSuccess,
  onCancel,
  initialData,
  className = '',
}) => {
  const [newTag, setNewTag] = useState('');
  const { setOrderFormData } = useOrderStore();
  const { toast } = useToast();

  const createOrderMutation = useCreateOrder();

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors, isDirty },
    reset,
  } = useForm<OrderFormValues>({
    resolver: zodResolver(orderFormSchema),
    defaultValues: {
      symbol: initialData?.symbol || '',
      side: initialData?.side || 'BUY',
      quantity: initialData?.quantity || 0,
      order_type: initialData?.order_type || 'MARKET',
      price: initialData?.price,
      stop_price: initialData?.stop_price,
      limit_price: initialData?.limit_price,
      trail_percent: initialData?.trail_percent,
      time_in_force: initialData?.time_in_force || 'DAY',
      expiration_date: initialData?.expiration_date,
      notes: initialData?.notes,
      tags: initialData?.tags || [],
    },
  });

  const watchedOrderType = watch('order_type');
  const watchedTags = watch('tags') || [];

  // Update store when form data changes
  useEffect(() => {
    const subscription = watch((data) => {
      setOrderFormData(data as OrderFormData);
    });
    return () => subscription.unsubscribe();
  }, [watch, setOrderFormData]);

  const onSubmit = async (data: OrderFormValues) => {
    try {
      const order = await createOrderMutation.mutateAsync(data);
      toast({
        title: 'Order Created',
        description: `Order ${order.id} has been created successfully.`,
      });
      reset();
      onSuccess?.(order);
    } catch (error: any) {
      toast({
        title: 'Order Creation Failed',
        description: error.message || 'Failed to create order. Please try again.',
        variant: 'destructive',
      });
    }
  };

  const addTag = () => {
    if (newTag.trim() && !watchedTags.includes(newTag.trim())) {
      setValue('tags', [...watchedTags, newTag.trim()]);
      setNewTag('');
    }
  };

  const removeTag = (tagToRemove: string) => {
    setValue('tags', watchedTags.filter(tag => tag !== tagToRemove));
  };

  const handleCancel = () => {
    reset();
    setOrderFormData(null);
    onCancel?.();
  };

  // Dynamic field requirements based on order type
  const getRequiredFields = (orderType: OrderType) => {
    const fields = {
      price: ['LIMIT', 'STOP_LIMIT'].includes(orderType),
      stop_price: ['STOP', 'STOP_LIMIT', 'TRAILING_STOP'].includes(orderType),
      limit_price: ['STOP_LIMIT'].includes(orderType),
      trail_percent: ['TRAILING_STOP'].includes(orderType),
    };
    return fields;
  };

  const requiredFields = getRequiredFields(watchedOrderType);

  return (
    <Card className={`card-luxury ${className}`}>
      <CardHeader>
        <CardTitle className="text-card-title">Create Order</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          {/* Basic Order Information */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="symbol">Symbol *</Label>
              <Input
                id="symbol"
                {...register('symbol')}
                placeholder="AAPL"
                className="input-luxury"
              />
              {errors.symbol && (
                <p className="text-sm text-rose-600">{errors.symbol.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="side">Side *</Label>
              <Select
                value={watch('side')}
                onValueChange={(value: 'BUY' | 'SELL') => setValue('side', value)}
              >
                <SelectTrigger className="input-luxury">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="BUY">Buy</SelectItem>
                  <SelectItem value="SELL">Sell</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="quantity">Quantity *</Label>
              <Input
                id="quantity"
                type="number"
                step="0.01"
                {...register('quantity', { valueAsNumber: true })}
                className="input-luxury"
              />
              {errors.quantity && (
                <p className="text-sm text-rose-600">{errors.quantity.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="order_type">Order Type *</Label>
              <Select
                value={watch('order_type')}
                onValueChange={(value: OrderType) => setValue('order_type', value)}
              >
                <SelectTrigger className="input-luxury">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="MARKET">Market</SelectItem>
                  <SelectItem value="LIMIT">Limit</SelectItem>
                  <SelectItem value="STOP">Stop</SelectItem>
                  <SelectItem value="STOP_LIMIT">Stop Limit</SelectItem>
                  <SelectItem value="TRAILING_STOP">Trailing Stop</SelectItem>
                  <SelectItem value="BRACKET">Bracket</SelectItem>
                  <SelectItem value="OCO">OCO</SelectItem>
                  <SelectItem value="CONDITIONAL">Conditional</SelectItem>
                  <SelectItem value="ICEBERG">Iceberg</SelectItem>
                  <SelectItem value="TWAP">TWAP</SelectItem>
                  <SelectItem value="VWAP">VWAP</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Conditional Fields Based on Order Type */}
          {requiredFields.price && (
            <div className="space-y-2">
              <Label htmlFor="price">Price *</Label>
              <Input
                id="price"
                type="number"
                step="0.01"
                {...register('price', { valueAsNumber: true })}
                className="input-luxury"
              />
              {errors.price && (
                <p className="text-sm text-rose-600">{errors.price.message}</p>
              )}
            </div>
          )}

          {requiredFields.stop_price && (
            <div className="space-y-2">
              <Label htmlFor="stop_price">Stop Price *</Label>
              <Input
                id="stop_price"
                type="number"
                step="0.01"
                {...register('stop_price', { valueAsNumber: true })}
                className="input-luxury"
              />
              {errors.stop_price && (
                <p className="text-sm text-rose-600">{errors.stop_price.message}</p>
              )}
            </div>
          )}

          {requiredFields.limit_price && (
            <div className="space-y-2">
              <Label htmlFor="limit_price">Limit Price *</Label>
              <Input
                id="limit_price"
                type="number"
                step="0.01"
                {...register('limit_price', { valueAsNumber: true })}
                className="input-luxury"
              />
              {errors.limit_price && (
                <p className="text-sm text-rose-600">{errors.limit_price.message}</p>
              )}
            </div>
          )}

          {requiredFields.trail_percent && (
            <div className="space-y-2">
              <Label htmlFor="trail_percent">Trail Percent *</Label>
              <Input
                id="trail_percent"
                type="number"
                step="0.01"
                {...register('trail_percent', { valueAsNumber: true })}
                className="input-luxury"
                placeholder="5.0"
              />
              {errors.trail_percent && (
                <p className="text-sm text-rose-600">{errors.trail_percent.message}</p>
              )}
            </div>
          )}

          {/* Time in Force */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="time_in_force">Time in Force *</Label>
              <Select
                value={watch('time_in_force')}
                onValueChange={(value: TimeInForce) => setValue('time_in_force', value)}
              >
                <SelectTrigger className="input-luxury">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="DAY">Day</SelectItem>
                  <SelectItem value="GTC">Good Till Cancelled</SelectItem>
                  <SelectItem value="GTD">Good Till Date</SelectItem>
                  <SelectItem value="IOC">Immediate or Cancel</SelectItem>
                  <SelectItem value="FOK">Fill or Kill</SelectItem>
                  <SelectItem value="GTX">Good Till Crossing</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {watch('time_in_force') === 'GTD' && (
              <div className="space-y-2">
                <Label htmlFor="expiration_date">Expiration Date</Label>
                <Input
                  id="expiration_date"
                  type="datetime-local"
                  {...register('expiration_date')}
                  className="input-luxury"
                />
              </div>
            )}
          </div>

          {/* Tags */}
          <div className="space-y-2">
            <Label>Tags</Label>
            <div className="flex flex-wrap gap-2 mb-2">
              {watchedTags.map((tag) => (
                <Badge key={tag} variant="secondary" className="flex items-center gap-1">
                  {tag}
                  <button
                    type="button"
                    onClick={() => removeTag(tag)}
                    className="ml-1 hover:text-rose-600"
                  >
                    <X className="h-3 w-3" />
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

          {/* Notes */}
          <div className="space-y-2">
            <Label htmlFor="notes">Notes</Label>
            <Textarea
              id="notes"
              {...register('notes')}
              placeholder="Optional notes about this order..."
              className="input-luxury min-h-[80px]"
            />
          </div>

          {/* Error Display */}
          {createOrderMutation.isError && (
            <Alert variant="destructive">
              <AlertDescription>
                {createOrderMutation.error?.message || 'Failed to create order'}
              </AlertDescription>
            </Alert>
          )}

          {/* Action Buttons */}
          <div className="flex gap-3 pt-4">
            <Button
              type="submit"
              disabled={createOrderMutation.isPending || !isDirty}
              className="btn-luxury-primary flex-1"
            >
              {createOrderMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Creating Order...
                </>
              ) : (
                'Create Order'
              )}
            </Button>

            <Button
              type="button"
              variant="outline"
              onClick={handleCancel}
              className="btn-luxury-secondary"
            >
              Cancel
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
};