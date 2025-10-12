import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { tradingAPI } from '@/api/endpoints'
import { tradeSchema, type TradeFormData } from '@/utils/validation'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { SymbolCombobox } from '@/components/ui/SymbolCombobox'
import { Button } from '@/components/ui/Button'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { TradeConfirmationDialog } from '@/components/ui/TradeConfirmationDialog'
import { Progress } from '@/components/ui/progress'
import { StepIndicator, type Step } from '@/components/ui/step-indicator'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { useToast } from '@/hooks/use-toast'
import { toastUtils } from '@/lib/toast-utils'
import { Tooltip, TooltipTrigger, TooltipContent } from '@/components/ui/tooltip'
import { cn } from '@/lib/utils'
import { TrendingUp } from 'lucide-react'

export function QuickTradeForm() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const [showConfirmation, setShowConfirmation] = useState(false)
  const [pendingTrade, setPendingTrade] = useState<TradeFormData | null>(null)
  const [tradeProgress, setTradeProgress] = useState(0)
  const [tradeSteps, setTradeSteps] = useState<Step[]>([])

  const {
    register,
    handleSubmit,
    watch,
    reset,
    setValue,
    formState: { errors, isValid, touchedFields },
  } = useForm<TradeFormData>({
    resolver: zodResolver(tradeSchema),
    mode: 'onChange',
    defaultValues: {
      symbol: '',
      side: undefined,
      quantity: undefined,
      order_type: undefined,
      price: undefined,
    },
  })

  const orderType = watch('order_type')
  const symbol = watch('symbol')
  const quantity = watch('quantity')
  const price = watch('price')
  const side = watch('side')

  // Real-time validation feedback
  const getFieldValidation = (fieldName: keyof TradeFormData) => {
    const field = touchedFields[fieldName]
    const error = errors[fieldName]
    if (field && !error) return { success: true }
    return { error: error?.message }
  }

  const executeTrade = useMutation({
    mutationFn: tradingAPI.executeTrade,
    onMutate: async (trade) => {
      // Initialize trade progress steps
      const steps: Step[] = [
        { id: 'validation', title: 'Validating Trade', description: 'Checking trade parameters', status: 'active' },
        { id: 'risk-check', title: 'Risk Assessment', description: 'Evaluating risk factors', status: 'pending' },
        { id: 'execution', title: 'Executing Trade', description: 'Submitting to broker', status: 'pending' },
        { id: 'confirmation', title: 'Confirmation', description: 'Waiting for confirmation', status: 'pending' }
      ]
      setTradeSteps(steps)
      setTradeProgress(25)

      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: ['dashboard'] })

      // Snapshot previous value
      const previousData = queryClient.getQueryData(['dashboard'])

      // Optimistically update with pending trade
      queryClient.setQueryData(['dashboard'], (old: any) => {
        if (!old) return old
        return {
          ...old,
          intents: [
            ...(old.intents || []),
            {
              id: `temp-${Date.now()}`,
              symbol: trade.symbol,
              status: 'pending',
              created_at: new Date().toISOString(),
            }
          ]
        }
      })

      return { previousData }
    },
    onSuccess: (data, trade, context) => {
      // Update progress steps to completed
      setTradeSteps(prev => prev.map(step => ({ ...step, status: 'completed' })))
      setTradeProgress(100)

      if (data.status === 'Trade executed') {
        toastUtils.success(
          'Trade Executed',
          `Intent ${data.intent_id} executed successfully`
        )
        reset()
        // Reset progress after a delay
        setTimeout(() => {
          setTradeProgress(0)
          setTradeSteps([])
        }, 2000)
      } else {
        // Update steps to show error
        setTradeSteps(prev => prev.map(step =>
          step.id === 'execution' ? { ...step, status: 'error' } : step
        ))
        toastUtils.error(
          'Trade Rejected',
          data.reasons?.join(', ') || 'Risk manager rejected trade'
        )
        // Revert optimistic update on rejection
        queryClient.setQueryData(['dashboard'], context?.previousData)
        // Reset progress after error
        setTimeout(() => {
          setTradeProgress(0)
          setTradeSteps([])
        }, 3000)
      }
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    },
    onError: (error, trade, context) => {
      // Update steps to show error
      setTradeSteps(prev => prev.map(step =>
        step.id === 'execution' ? { ...step, status: 'error' } : step
      ))

      // Revert optimistic update on error
      queryClient.setQueryData(['dashboard'], context?.previousData)

      toastUtils.error(
        'Trade Failed',
        error instanceof Error ? error.message : 'Unknown error'
      )

      // Reset progress after error
      setTimeout(() => {
        setTradeProgress(0)
        setTradeSteps([])
      }, 3000)
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })

  const onSubmit = (data: TradeFormData) => {
    setPendingTrade(data)
    setShowConfirmation(true)
  }

  const handleConfirmTrade = () => {
    if (pendingTrade) {
      executeTrade.mutate(pendingTrade)
      setShowConfirmation(false)
      setPendingTrade(null)
    }
  }

  const handleCancelTrade = () => {
    setShowConfirmation(false)
    setPendingTrade(null)
  }

  // Mock risk assessment - in real app this would come from backend
  const getRiskAssessment = (trade: TradeFormData) => {
    const totalValue = trade.price && trade.quantity ? trade.price * trade.quantity : trade.quantity || 0

    if (totalValue > 10000) {
      return {
        level: 'high' as const,
        warnings: [
          'Large position size may impact portfolio significantly',
          'Consider market volatility before execution',
          'Ensure sufficient margin requirements are met'
        ]
      }
    } else if (totalValue > 5000) {
      return {
        level: 'medium' as const,
        warnings: [
          'Moderate position size - monitor closely',
          'Check current market conditions'
        ]
      }
    }
    return {
      level: 'low' as const,
      warnings: []
    }
  }

  return (
    <Card className="shadow-professional border-0 bg-gradient-to-br from-white/95 to-blue-50/70 backdrop-blur-sm hover:shadow-professional-hover transition-all duration-300 ring-1 ring-blue-100/50 animate-scale-in">
      <CardHeader className="pb-4">
        <CardTitle className="text-xl flex items-center gap-3 font-bold">
          <div className="p-3 bg-gradient-to-br from-blue-100 to-blue-200 rounded-xl shadow-sm">
            <TrendingUp className="w-6 h-6 text-blue-700" />
          </div>
          <span className="bg-gradient-to-r from-blue-700 to-blue-600 bg-clip-text text-transparent">
            Quick Trade
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">

      {/* Trade Progress Indicator */}
      {executeTrade.isPending && tradeSteps.length > 0 && (
        <div className="space-y-4 p-4 bg-gradient-to-r from-blue-50/80 to-indigo-50/80 rounded-xl border border-blue-200/50 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-sm font-bold text-blue-800">Trade Execution Progress</span>
            <span className="text-sm font-semibold text-blue-700 tabular-nums">{tradeProgress}%</span>
          </div>
          <Progress value={tradeProgress} className="w-full h-3 bg-blue-100 [&>div]:bg-gradient-to-r [&>div]:from-blue-500 [&>div]:to-blue-600" />
          <StepIndicator steps={tradeSteps} orientation="horizontal" className="mt-4" />
        </div>
      )}

        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label htmlFor="symbol" className="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-2">
              Symbol
            </label>
            <Tooltip>
              <TooltipTrigger asChild>
                <div>
                  <SymbolCombobox
                    value={symbol}
                    onValueChange={(value: string) => setValue('symbol', value)}
                    placeholder="Search symbols..."
                    className={cn(
                      "input-professional",
                      getFieldValidation('symbol').error && "border-red-500 focus:ring-red-500",
                      getFieldValidation('symbol').success && "border-green-500 focus:ring-green-500"
                    )}
                  />
                </div>
              </TooltipTrigger>
              <TooltipContent>
                <p>Enter the stock symbol (e.g., AAPL, GOOGL) you want to trade</p>
              </TooltipContent>
            </Tooltip>
          </div>

          <div>
            <label htmlFor="side" className="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-2">
              Side
            </label>
            <Tooltip>
              <TooltipTrigger asChild>
                <div>
                  <Select id="side" {...register('side')} error={errors.side?.message} className="input-professional">
                    <option value="">Select</option>
                    <option value="BUY">Buy</option>
                    <option value="SELL">Sell</option>
                  </Select>
                </div>
              </TooltipTrigger>
              <TooltipContent>
                <p>Choose whether to buy or sell the selected security</p>
              </TooltipContent>
            </Tooltip>
          </div>

          <div>
            <label htmlFor="quantity" className="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-2">
              Quantity
            </label>
            <Tooltip>
              <TooltipTrigger asChild>
                <div>
                  <Input
                    id="quantity"
                    type="number"
                    {...register('quantity', { valueAsNumber: true })}
                    placeholder="100"
                    showValidation={true}
                    className="input-professional"
                    {...getFieldValidation('quantity')}
                  />
                </div>
              </TooltipTrigger>
              <TooltipContent>
                <p>Number of shares to buy or sell</p>
              </TooltipContent>
            </Tooltip>
          </div>

          <div>
            <label htmlFor="order_type" className="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-2">
              Order Type
            </label>
            <Tooltip>
              <TooltipTrigger asChild>
                <div>
                  <Select
                    id="order_type"
                    {...register('order_type')}
                    error={errors.order_type?.message}
                    className="input-professional"
                  >
                    <option value="">Select</option>
                    <option value="MARKET">Market</option>
                    <option value="LIMIT">Limit</option>
                  </Select>
                </div>
              </TooltipTrigger>
              <TooltipContent>
                <p>Market orders execute immediately at current price. Limit orders execute at your specified price or better.</p>
              </TooltipContent>
            </Tooltip>
          </div>

          {orderType === 'LIMIT' && (
            <div className="col-span-1 md:col-span-2 animate-slide-in-up">
              <label htmlFor="price" className="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-2">
                Price
              </label>
              <Tooltip>
                <TooltipTrigger asChild>
                  <div>
                    <Input
                      id="price"
                      type="number"
                      step="0.01"
                      {...register('price', { valueAsNumber: true })}
                      placeholder="0.00"
                      showValidation={true}
                      className="input-professional"
                      {...getFieldValidation('price')}
                    />
                  </div>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Specify the maximum price to pay (for buy orders) or minimum price to receive (for sell orders)</p>
                </TooltipContent>
              </Tooltip>
            </div>
          )}
        </div>

        <div className="flex items-center gap-4 pt-2">
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="flex-1">
                <Button
                  type="submit"
                  disabled={executeTrade.isPending || !isValid}
                  className="w-full btn-professional font-bold text-lg py-4 shadow-professional hover:shadow-professional-hover transition-all duration-300"
                >
                  {executeTrade.isPending ? (
                    <div className="flex items-center gap-3">
                      <LoadingSpinner size="sm" variant="default" />
                      <span>Executing Trade...</span>
                    </div>
                  ) : (
                    'Execute Trade'
                  )}
                </Button>
              </div>
            </TooltipTrigger>
            <TooltipContent>
              <p>Submit the trade order for execution. This will be reviewed by the risk management system before processing.</p>
            </TooltipContent>
          </Tooltip>

          {!isValid && Object.keys(touchedFields).length > 0 && (
            <div className="text-sm text-red-600 font-medium bg-red-50 px-3 py-2 rounded-lg border border-red-200">
              Please complete all required fields
            </div>
          )}
        </div>
        </form>
      </CardContent>

      {pendingTrade && (
        <TradeConfirmationDialog
          open={showConfirmation}
          onOpenChange={setShowConfirmation}
          tradeData={pendingTrade}
          onConfirm={handleConfirmTrade}
          onCancel={handleCancelTrade}
          isExecuting={executeTrade.isPending}
          riskLevel={getRiskAssessment(pendingTrade).level}
          riskWarnings={getRiskAssessment(pendingTrade).warnings}
        />
      )}
    </Card>
  )
}
