/**
 * Runtime Validation Schemas
 * ===========================
 * Zod schemas for all external data payloads.
 * ALL websocket/API data MUST pass through these before entering the store.
 * 
 * These schemas enforce:
 * - Type correctness
 * - Enum validity
 * - Required field presence
 * - Numeric bounds
 * - String formats
 * - Structural integrity
 */

import { z } from 'zod'

// ============================================================================
// PRIMITIVE SCHEMAS
// ============================================================================

export const TradingMode = z.enum(['paper', 'live']).default('paper')
export const Exchange = z.enum(['NSE', 'BSE']).default('NSE')
export const OrderType = z.enum(['MARKET', 'LIMIT', 'SL', 'SL-M']).default('MARKET')
export const TransactionType = z.enum(['BUY', 'SELL']).default('BUY')
export const ProductType = z.enum(['MIS', 'CNC', 'NRML']).default('MIS')
export const Validity = z.enum(['DAY', 'IOC', 'GTD', 'GTC']).default('DAY')
export const OrderStatus = z.enum([
  'NEW',
  'VALIDATED',
  'OPEN',
  'PARTIALLY_FILLED',
  'FILLED',
  'CANCELLED',
  'REJECTED',
  'EXPIRED'
]).default('NEW')

export const PositionStatus = z.enum(['OPEN', 'CLOSED']).default('OPEN')
export const KycStatus = z.enum(['pending', 'verified', 'rejected']).default('pending')
export const UserRole = z.enum(['admin', 'trader', 'viewer']).default('trader')

// Numeric constraints
const NonNegativeNumber = z.number().min(0, 'Must be non-negative')
const PositiveNumber = z.number().min(0.01, 'Must be positive')
const IntegerQty = z.number().int().min(1, 'Must be positive integer')
const Price = z.number().min(0, 'Price cannot be negative')

// ISO timestamp
const ISOTimestamp = z.string().datetime().or(z.string().regex(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/))

// ============================================================================
// DOMAIN SCHEMAS
// ============================================================================

// ORDER SCHEMA
export const OrderSchema = z.object({
  order_id: z.string().min(1, 'Order ID required'),
  user_id: z.string().min(1, 'User ID required'),
  strategy_id: z.string().optional(),

  symbol: z.string().min(1, 'Symbol required').toUpperCase(),
  exchange: Exchange,
  order_type: OrderType,
  product_type: ProductType,
  transaction_type: TransactionType,

  quantity: IntegerQty,
  filled_quantity: z.number().int().min(0).default(0),
  cancelled_quantity: z.number().int().min(0).default(0),

  price: Price.default(0),
  trigger_price: Price.default(0),
  average_price: Price.default(0),

  status: OrderStatus,
  validity: Validity,
  mode: TradingMode,

  brokerage: NonNegativeNumber.default(0),
  taxes: NonNegativeNumber.default(0),
  pnl: z.number().default(0),

  disclosed_quantity: z.number().int().min(0).default(0),
  order_tag: z.string().default(''),
  comments: z.string().default(''),
  source: z.string().default('ui'),

  parent_order_id: z.string().optional(),

  created_at: ISOTimestamp,
  updated_at: ISOTimestamp,
  filled_at: ISOTimestamp.optional(),
  cancelled_at: ISOTimestamp.optional(),
  rejected_reason: z.string().optional(),
}).strict()

export type Order = z.infer<typeof OrderSchema>

// ============================================================================

// POSITION SCHEMA
export const PositionSchema = z.object({
  position_id: z.string().min(1, 'Position ID required'),
  user_id: z.string().min(1, 'User ID required'),
  strategy_id: z.string().optional(),

  symbol: z.string().min(1, 'Symbol required').toUpperCase(),
  exchange: Exchange,
  product_type: ProductType,

  quantity: IntegerQty,
  closed_quantity: z.number().int().min(0).default(0),

  entry_price: PositiveNumber,
  average_price: PositiveNumber,
  current_price: PositiveNumber,

  realized_pnl: z.number().default(0),
  unrealized_pnl: z.number().default(0),
  day_pnl: z.number().default(0),

  stop_loss: Price.optional(),
  take_profit: Price.optional(),

  mode: TradingMode,
  status: PositionStatus,

  opened_at: ISOTimestamp.optional(),
  closed_at: ISOTimestamp.optional(),
  mtm_updated_at: ISOTimestamp.optional(),
}).strict()

export type Position = z.infer<typeof PositionSchema>

// ============================================================================

// TRADE SCHEMA
export const TradeSchema = z.object({
  trade_id: z.string().min(1, 'Trade ID required'),
  user_id: z.string().min(1, 'User ID required'),
  order_id: z.string().min(1, 'Order ID required'),
  position_id: z.string().optional(),
  strategy_id: z.string().optional(),

  symbol: z.string().min(1, 'Symbol required').toUpperCase(),
  exchange: Exchange,
  transaction_type: TransactionType,

  quantity: IntegerQty,
  price: PositiveNumber,
  value: NonNegativeNumber,

  brokerage: NonNegativeNumber.default(0),
  stt: NonNegativeNumber.default(0),
  gst: NonNegativeNumber.default(0),
  stamp_duty: NonNegativeNumber.default(0),
  other_charges: NonNegativeNumber.default(0),

  pnl: z.number().default(0),
  pnl_percent: z.number().default(0),

  execution_time: ISOTimestamp.optional(),
  mode: TradingMode,
}).strict()

export type Trade = z.infer<typeof TradeSchema>

// ============================================================================

// MARKET QUOTE SCHEMA
export const MarketQuoteSchema = z.object({
  symbol: z.string().min(1, 'Symbol required').toUpperCase(),
  last_price: NonNegativeNumber,
  bid: NonNegativeNumber,
  ask: NonNegativeNumber,
  bid_quantity: z.number().int().min(0).default(0),
  ask_quantity: z.number().int().min(0).default(0),
  volume: z.number().int().min(0).default(0),
  timestamp: ISOTimestamp,
}).strict()

export type MarketQuote = z.infer<typeof MarketQuoteSchema>

// ============================================================================

// MARGIN INFO SCHEMA
export const MarginInfoSchema = z.object({
  user_id: z.string().min(1, 'User ID required'),
  total_margin: NonNegativeNumber,
  used_margin: NonNegativeNumber,
  available_margin: NonNegativeNumber,
  blocked_margin: NonNegativeNumber.default(0),
  intraday_buying_power: NonNegativeNumber,
  cash_balance: z.number(),
  holdings_value: NonNegativeNumber,
  position_margins: z.record(z.string(), z.number()).default({}),
  timestamp: ISOTimestamp,
}).strict()

export type MarginInfo = z.infer<typeof MarginInfoSchema>

// ============================================================================

// PnL DATA SCHEMA
export const PnLDataSchema = z.object({
  total_pnl: z.number(),
  realized_pnl: z.number(),
  unrealized_pnl: z.number(),
  day_pnl: z.number(),
  mode: TradingMode,
  timestamp: ISOTimestamp,
}).strict()

export type PnLData = z.infer<typeof PnLDataSchema>

// ============================================================================

// DAY PnL SCHEMA
export const DayPnLSchema = z.object({
  day_pnl: z.number(),
  buy_value: NonNegativeNumber,
  sell_value: NonNegativeNumber,
  brokerage: NonNegativeNumber.default(0),
  taxes: NonNegativeNumber.default(0),
  trades_count: z.number().int().min(0).default(0),
  winning_trades: z.number().int().min(0).default(0),
  losing_trades: z.number().int().min(0).default(0),
  win_rate: z.number().min(0).max(100).default(0),
}).strict()

export type DayPnL = z.infer<typeof DayPnLSchema>

// ============================================================================

// USER SCHEMA
export const UserSchema = z.object({
  user_id: z.string().min(1, 'User ID required'),
  email: z.string().email('Invalid email'),
  full_name: z.string().min(1, 'Name required'),
  phone: z.string().optional(),
  role: UserRole,
  broker: z.string().optional(),
  twofa_enabled: z.boolean().default(false),
  email_verified: z.boolean().default(false),
  kyc_status: KycStatus,
  created_at: ISOTimestamp,
  last_login: ISOTimestamp.optional(),
}).strict()

export type User = z.infer<typeof UserSchema>

// ============================================================================

// MARKET DEPTH SCHEMA
export const MarketDepthSchema = z.object({
  symbol: z.string().min(1, 'Symbol required').toUpperCase(),
  bid_prices: z.array(Price).default([]),
  bid_quantities: z.array(z.number().int().min(0)).default([]),
  ask_prices: z.array(Price).default([]),
  ask_quantities: z.array(z.number().int().min(0)).default([]),
  last_price: NonNegativeNumber,
  volume: z.number().int().min(0).default(0),
  timestamp: ISOTimestamp,
}).strict()

export type MarketDepth = z.infer<typeof MarketDepthSchema>

// ============================================================================

// COLLECTIONS
// ============================================================================

export const OrderArraySchema = z.array(OrderSchema)
export const PositionArraySchema = z.array(PositionSchema)
export const TradeArraySchema = z.array(TradeSchema)
export const QuoteRecordSchema = z.record(z.string(), MarketQuoteSchema)

// ============================================================================

// WEBSOCKET UPDATE SCHEMAS
// ============================================================================

export const OrderUpdatePayloadSchema = z.object({
  type: z.literal('ORDER_UPDATE'),
  data: OrderSchema,
  timestamp: ISOTimestamp,
}).strict()

export const PositionUpdatePayloadSchema = z.object({
  type: z.literal('POSITION_UPDATE'),
  data: PositionSchema,
  timestamp: ISOTimestamp,
}).strict()

export const TradeUpdatePayloadSchema = z.object({
  type: z.literal('TRADE_UPDATE'),
  data: TradeSchema,
  timestamp: ISOTimestamp,
}).strict()

export const PnLUpdatePayloadSchema = z.object({
  type: z.literal('PnL_UPDATE'),
  data: PnLDataSchema,
  timestamp: ISOTimestamp,
}).strict()

export const QuoteUpdatePayloadSchema = z.object({
  type: z.literal('QUOTE_UPDATE'),
  data: MarketQuoteSchema,
  timestamp: ISOTimestamp,
}).strict()

export const DepthUpdatePayloadSchema = z.object({
  type: z.literal('DEPTH_UPDATE'),
  data: MarketDepthSchema,
  timestamp: ISOTimestamp,
}).strict()

// Union of all update types
export const WSUpdatePayloadSchema = z.discriminatedUnion('type', [
  OrderUpdatePayloadSchema,
  PositionUpdatePayloadSchema,
  TradeUpdatePayloadSchema,
  PnLUpdatePayloadSchema,
  QuoteUpdatePayloadSchema,
  DepthUpdatePayloadSchema,
])

export type WSUpdatePayload = z.infer<typeof WSUpdatePayloadSchema>

// ============================================================================

// API RESPONSE SCHEMAS
// ============================================================================

export const ApiResponseSchema = z.object({
  success: z.boolean(),
  message: z.string(),
  data: z.unknown(),
  timestamp: ISOTimestamp,
  pagination: z.object({
    page: z.number().int().min(1),
    limit: z.number().int().min(1),
    total: z.number().int().min(0),
    pages: z.number().int().min(0),
  }).optional(),
})

export type ApiResponse<T> = z.infer<typeof ApiResponseSchema> & { data: T }
