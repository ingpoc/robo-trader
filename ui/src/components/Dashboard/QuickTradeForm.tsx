import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { tradingAPI } from '@/api/endpoints'
import { tradeSchema, type TradeFormData } from '@/utils/validation'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { Button } from '@/components/ui/Button'
import { useDashboardStore } from '@/store/dashboardStore'

export function QuickTradeForm() {
  const queryClient = useQueryClient()
  const addToast = useDashboardStore((state) => state.addToast)

  const {
    register,
    handleSubmit,
    watch,
    reset,
    formState: { errors },
  } = useForm<TradeFormData>({
    resolver: zodResolver(tradeSchema),
    defaultValues: {
      symbol: '',
      side: undefined,
      quantity: undefined,
      order_type: undefined,
      price: undefined,
    },
  })

  const orderType = watch('order_type')

  const executeTrade = useMutation({
    mutationFn: tradingAPI.executeTrade,
    onMutate: async (trade) => {
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
      if (data.status === 'Trade executed') {
        addToast({
          title: 'Trade Executed',
          description: `Intent ${data.intent_id} executed successfully`,
          variant: 'success',
        })
        reset()
      } else {
        addToast({
          title: 'Trade Rejected',
          description: data.reasons?.join(', ') || 'Risk manager rejected trade',
          variant: 'error',
        })
        // Revert optimistic update on rejection
        queryClient.setQueryData(['dashboard'], context?.previousData)
      }
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    },
    onError: (error, trade, context) => {
      // Revert optimistic update on error
      queryClient.setQueryData(['dashboard'], context?.previousData)

      addToast({
        title: 'Trade Failed',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'error',
      })
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })

  const onSubmit = (data: TradeFormData) => {
    executeTrade.mutate(data)
  }

  return (
    <div className="flex flex-col gap-3 p-4 bg-white border border-gray-200 rounded">
      <h3 className="text-lg font-semibold text-gray-900">Quick Trade</h3>

      <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-3">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label htmlFor="symbol" className="block text-sm font-medium text-gray-700 mb-1">
              Symbol
            </label>
            <Input
              id="symbol"
              {...register('symbol')}
              placeholder="RELIANCE"
              error={errors.symbol?.message}
            />
          </div>

          <div>
            <label htmlFor="side" className="block text-sm font-medium text-gray-700 mb-1">
              Side
            </label>
            <Select id="side" {...register('side')} error={errors.side?.message}>
              <option value="">Select</option>
              <option value="BUY">Buy</option>
              <option value="SELL">Sell</option>
            </Select>
          </div>

          <div>
            <label htmlFor="quantity" className="block text-sm font-medium text-gray-700 mb-1">
              Quantity
            </label>
            <Input
              id="quantity"
              type="number"
              {...register('quantity', { valueAsNumber: true })}
              placeholder="100"
              error={errors.quantity?.message}
            />
          </div>

          <div>
            <label htmlFor="order_type" className="block text-sm font-medium text-gray-700 mb-1">
              Order Type
            </label>
            <Select
              id="order_type"
              {...register('order_type')}
              error={errors.order_type?.message}
            >
              <option value="">Select</option>
              <option value="MARKET">Market</option>
              <option value="LIMIT">Limit</option>
            </Select>
          </div>

          {orderType === 'LIMIT' && (
            <div className="col-span-2">
              <label htmlFor="price" className="block text-sm font-medium text-gray-700 mb-1">
                Price
              </label>
              <Input
                id="price"
                type="number"
                step="0.01"
                {...register('price', { valueAsNumber: true })}
                placeholder="0.00"
                error={errors.price?.message}
              />
            </div>
          )}
        </div>

        <Button type="submit" disabled={executeTrade.isPending}>
          {executeTrade.isPending ? 'Executing...' : 'Execute Trade'}
        </Button>
      </form>
    </div>
  )
}
