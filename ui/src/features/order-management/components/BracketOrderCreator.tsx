import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { BracketOrderFormData } from '../types';
import { useCreateBracketOrder } from '../hooks/useOrderApi';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Loader2,
  Plus,
  Minus,
  Target,
  TrendingDown,
  TrendingUp,
  AlertTriangle,
  CheckCircle
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

// Form validation schema
const bracketOrderSchema = z.object({
  symbol: z.string().min(1, 'Symbol is required').max(10, 'Symbol too long'),
  side: z.enum(['BUY', 'SELL']),
  quantity: z.number().min(0.01, 'Quantity must be greater than 0'),
  entry_price: z.number().optional(),
  stop_loss_price: z.number().optional(),
  stop_loss_percentage: z.number().min(0.1).max(50).optional(),
  take_profit_levels: z.array(z.object({
    percentage: z.number().min(0.1).max(500),
    quantity_percentage: z.number().min(1).max(100),
  })).min(1, 'At least one take profit level required'),
  time_in_force: z.enum(['DAY', 'GTC', 'GTD', 'IOC', 'FOK', 'GTX']),
});

type BracketOrderFormValues = z.infer<typeof bracketOrderSchema>;

interface BracketOrderCreatorProps {
  onSuccess?: (bracket: any) => void;
  onCancel?: () => void;
  initialData?: Partial<BracketOrderFormData>;
  className?: string;
}

export const BracketOrderCreator: React.FC<BracketOrderCreatorProps> = ({
  onSuccess,
  onCancel,
  initialData,
  className = '',
}) => {
  const [activeTab, setActiveTab] = useState<'simple' | 'advanced'>('simple');
  const { toast } = useToast();

  const createBracketMutation = useCreateBracketOrder();

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors, isDirty },
    reset,
  } = useForm<BracketOrderFormValues>({
    resolver: zodResolver(bracketOrderSchema),
    defaultValues: {
      symbol: initialData?.symbol || '',
      side: initialData?.side || 'BUY',
      quantity: initialData?.quantity || 0,
      entry_price: initialData?.entry_price,
      stop_loss_price: initialData?.stop_loss_price,
      stop_loss_percentage: initialData?.stop_loss_percentage,
      take_profit_levels: initialData?.take_profit_levels || [{ percentage: 5, quantity_percentage: 100 }],
      time_in_force: initialData?.time_in_force || 'DAY',
    },
  });

  const watchedSide = watch('side');
  const watchedQuantity = watch('quantity');
  const watchedEntryPrice = watch('entry_price');
  const watchedStopLossPrice = watch('stop_loss_price');
  const watchedStopLossPercentage = watch('stop_loss_percentage');
  const watchedTakeProfitLevels = watch('take_profit_levels') || [];

  const onSubmit = async (data: BracketOrderFormValues) => {
    try {
      const bracket = await createBracketMutation.mutateAsync(data);
      toast({
        title: 'Bracket Order Created',
        description: `Bracket order for ${data.symbol} has been created successfully.`,
      });
      reset();
      onSuccess?.(bracket);
    } catch (error: any) {
      toast({
        title: 'Bracket Order Failed',
        description: error.message || 'Failed to create bracket order. Please try again.',
        variant: 'destructive',
      });
    }
  };

  const addTakeProfitLevel = () => {
    const newLevels = [...watchedTakeProfitLevels, { percentage: 5, quantity_percentage: 50 }];
    setValue('take_profit_levels', newLevels);
  };

  const removeTakeProfitLevel = (index: number) => {
    if (watchedTakeProfitLevels.length > 1) {
      const newLevels = watchedTakeProfitLevels.filter((_, i) => i !== index);
      setValue('take_profit_levels', newLevels);
    }
  };

  const updateTakeProfitLevel = (index: number, field: 'percentage' | 'quantity_percentage', value: number) => {
    const newLevels = [...watchedTakeProfitLevels];
    newLevels[index] = { ...newLevels[index], [field]: value };
    setValue('take_profit_levels', newLevels);
  };

  const calculateStopLossPrice = (entryPrice: number, percentage: number, side: 'BUY' | 'SELL') => {
    if (side === 'BUY') {
      return entryPrice * (1 - percentage / 100);
    } else {
      return entryPrice * (1 + percentage / 100);
    }
  };

  const calculateTakeProfitPrice = (entryPrice: number, percentage: number, side: 'BUY' | 'SELL') => {
    if (side === 'BUY') {
      return entryPrice * (1 + percentage / 100);
    } else {
      return entryPrice * (1 - percentage / 100);
    }
  };

  const handleCancel = () => {
    reset();
    onCancel?.();
  };

  // Calculate potential P&L
  const calculatePotentialPnL = () => {
    if (!watchedEntryPrice || !watchedQuantity) return null;

    const stopLoss = watchedStopLossPrice || (watchedStopLossPercentage
      ? calculateStopLossPrice(watchedEntryPrice, watchedStopLossPercentage, watchedSide)
      : null);

    if (!stopLoss) return null;

    const riskAmount = Math.abs(watchedEntryPrice - stopLoss) * watchedQuantity;
    const totalReward = watchedTakeProfitLevels.reduce((total, level) => {
      const tpPrice = calculateTakeProfitPrice(watchedEntryPrice, level.percentage, watchedSide);
      const reward = Math.abs(tpPrice - watchedEntryPrice) * watchedQuantity * (level.quantity_percentage / 100);
      return total + reward;
    }, 0);

    const riskRewardRatio = totalReward / riskAmount;

    return {
      riskAmount,
      totalReward,
      riskRewardRatio,
      stopLoss,
      takeProfitPrices: watchedTakeProfitLevels.map(level =>
        calculateTakeProfitPrice(watchedEntryPrice, level.percentage, watchedSide)
      ),
    };
  };

  const pnlData = calculatePotentialPnL();

  return (
    <Card className={`card-luxury ${className}`}>
      <CardHeader>
        <CardTitle className="text-card-title flex items-center gap-2">
          <Target className="h-5 w-5" />
          Bracket Order Creator
        </CardTitle>
        <p className="text-body-muted">
          Create entry order with automatic stop loss and take profit levels
        </p>
      </CardHeader>
      <CardContent>
        <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as 'simple' | 'advanced')}>
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="simple">Simple</TabsTrigger>
            <TabsTrigger value="advanced">Advanced</TabsTrigger>
          </TabsList>

          <TabsContent value="simple" className="space-y-6">
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
              {/* Basic Order Info */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
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
                  <div className="flex gap-2">
                    <Button
                      type="button"
                      variant={watchedSide === 'BUY' ? 'default' : 'outline'}
                      onClick={() => setValue('side', 'BUY')}
                      className="flex-1"
                    >
                      Buy
                    </Button>
                    <Button
                      type="button"
                      variant={watchedSide === 'SELL' ? 'default' : 'outline'}
                      onClick={() => setValue('side', 'SELL')}
                      className="flex-1"
                    >
                      Sell
                    </Button>
                  </div>
                </div>

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
              </div>

              {/* Entry Price */}
              <div className="space-y-2">
                <Label htmlFor="entry_price">Entry Price (Optional - Market if empty)</Label>
                <Input
                  id="entry_price"
                  type="number"
                  step="0.01"
                  {...register('entry_price', { valueAsNumber: true })}
                  className="input-luxury"
                  placeholder="Leave empty for market order"
                />
              </div>

              {/* Stop Loss */}
              <Card className="card-compact">
                <CardHeader className="pb-3">
                  <CardTitle className="text-card-title flex items-center gap-2">
                    <TrendingDown className="h-4 w-4 text-rose-500" />
                    Stop Loss
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="stop_loss_percentage">Stop Loss %</Label>
                      <Input
                        id="stop_loss_percentage"
                        type="number"
                        step="0.1"
                        min="0.1"
                        max="50"
                        {...register('stop_loss_percentage', { valueAsNumber: true })}
                        className="input-luxury"
                        placeholder="5.0"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="stop_loss_price">Or Fixed Price</Label>
                      <Input
                        id="stop_loss_price"
                        type="number"
                        step="0.01"
                        {...register('stop_loss_price', { valueAsNumber: true })}
                        className="input-luxury"
                        placeholder="Fixed stop price"
                      />
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Take Profit */}
              <Card className="card-compact">
                <CardHeader className="pb-3">
                  <CardTitle className="text-card-title flex items-center gap-2">
                    <TrendingUp className="h-4 w-4 text-emerald-500" />
                    Take Profit Levels
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {watchedTakeProfitLevels.map((level, index) => (
                    <div key={index} className="flex items-center gap-4 p-3 bg-warmgray-50 dark:bg-warmgray-800/50 rounded-lg">
                      <div className="flex-1">
                        <Label>Target {index + 1}</Label>
                        <div className="flex gap-2 mt-1">
                          <Input
                            type="number"
                            step="0.1"
                            min="0.1"
                            value={level.percentage}
                            onChange={(e) => updateTakeProfitLevel(index, 'percentage', parseFloat(e.target.value))}
                            className="input-luxury flex-1"
                            placeholder="Profit %"
                          />
                          <Input
                            type="number"
                            step="1"
                            min="1"
                            max="100"
                            value={level.quantity_percentage}
                            onChange={(e) => updateTakeProfitLevel(index, 'quantity_percentage', parseFloat(e.target.value))}
                            className="input-luxury flex-1"
                            placeholder="Qty %"
                          />
                        </div>
                      </div>
                      {watchedTakeProfitLevels.length > 1 && (
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => removeTakeProfitLevel(index)}
                          className="text-rose-600 hover:text-rose-700"
                        >
                          <Minus className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                  ))}

                  <Button
                    type="button"
                    variant="outline"
                    onClick={addTakeProfitLevel}
                    className="btn-luxury-tertiary w-full"
                  >
                    <Plus className="mr-2 h-4 w-4" />
                    Add Take Profit Level
                  </Button>
                </CardContent>
              </Card>

              {/* Risk/Reward Preview */}
              {pnlData && (
                <Card className="card-compact border-copper-500/30">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-card-title">Risk/Reward Analysis</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
                      <div>
                        <p className="text-sm text-body-muted">Risk Amount</p>
                        <p className="text-lg font-semibold text-rose-600">
                          ${pnlData.riskAmount.toFixed(2)}
                        </p>
                      </div>
                      <div>
                        <p className="text-sm text-body-muted">Reward Amount</p>
                        <p className="text-lg font-semibold text-emerald-600">
                          ${pnlData.totalReward.toFixed(2)}
                        </p>
                      </div>
                      <div>
                        <p className="text-sm text-body-muted">R:R Ratio</p>
                        <p className="text-lg font-semibold text-copper-600">
                          1:{pnlData.riskRewardRatio.toFixed(1)}
                        </p>
                      </div>
                      <div>
                        <p className="text-sm text-body-muted">Break Even</p>
                        <p className="text-lg font-semibold">
                          ${watchedEntryPrice?.toFixed(2) || 'Market'}
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Error Display */}
              {createBracketMutation.isError && (
                <Alert variant="destructive">
                  <AlertTriangle className="h-4 w-4" />
                  <AlertDescription>
                    {createBracketMutation.error?.message || 'Failed to create bracket order'}
                  </AlertDescription>
                </Alert>
              )}

              {/* Action Buttons */}
              <div className="flex gap-3 pt-4">
                <Button
                  type="submit"
                  disabled={createBracketMutation.isPending || !isDirty}
                  className="btn-luxury-primary flex-1"
                >
                  {createBracketMutation.isPending ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Creating Bracket Order...
                    </>
                  ) : (
                    'Create Bracket Order'
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
          </TabsContent>

          <TabsContent value="advanced" className="space-y-6">
            <Alert>
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                Advanced bracket order features coming soon. Use the Simple tab for now.
              </AlertDescription>
            </Alert>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
};