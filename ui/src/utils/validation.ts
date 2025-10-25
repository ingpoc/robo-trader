import { z } from 'zod'

export const tradeSchema = z.object({
  symbol: z
    .string()
    .min(1, 'Symbol is required')
    .max(20, 'Symbol too long')
    .regex(/^[A-Z0-9]+$/, 'Symbol must contain only uppercase letters and numbers')
    .transform((val) => val.toUpperCase()),
  side: z.enum(['BUY', 'SELL'], {
    required_error: 'Please select buy or sell',
  }),
  quantity: z
    .number({ required_error: 'Quantity is required' })
    .int('Must be a whole number')
    .positive('Must be greater than 0')
    .max(1000000, 'Quantity too large'),
  order_type: z.enum(['MARKET', 'LIMIT'], {
    required_error: 'Please select order type',
  }),
  price: z.number().positive('Price must be greater than 0').optional(),
  strategy_tag: z.string().optional(),
  stop_loss: z.number().positive('Stop loss must be greater than 0').optional(),
  target_price: z.number().positive('Target price must be greater than 0').optional(),
  rationale: z.string().min(1, 'Trading rationale is required'),
}).refine((data) => {
  // If order type is LIMIT, price is required
  if (data.order_type === 'LIMIT') {
    return data.price !== undefined && data.price > 0
  }
  return true
}, {
  message: 'Price is required for limit orders',
  path: ['price'],
})

export type TradeFormData = z.infer<typeof tradeSchema>

export const chatQuerySchema = z.object({
  query: z.string().min(1, 'Message cannot be empty').max(1000, 'Message too long'),
})

export type ChatQueryData = z.infer<typeof chatQuerySchema>

export const agentConfigSchema = z.object({
  enabled: z.boolean(),
  frequency: z.string(),
})

export type AgentConfigData = z.infer<typeof agentConfigSchema>
