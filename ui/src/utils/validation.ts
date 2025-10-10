import { z } from 'zod'

export const tradeSchema = z.object({
  symbol: z
    .string()
    .min(1, 'Symbol is required')
    .max(20, 'Symbol too long')
    .transform((val) => val.toUpperCase()),
  side: z.enum(['BUY', 'SELL'], {
    required_error: 'Please select buy or sell',
  }),
  quantity: z
    .number({ required_error: 'Quantity is required' })
    .int('Must be a whole number')
    .positive('Must be greater than 0'),
  order_type: z.enum(['MARKET', 'LIMIT'], {
    required_error: 'Please select order type',
  }),
  price: z.number().positive().optional(),
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
