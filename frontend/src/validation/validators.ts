/**
 * Safe Validators & Sanitizers
 * =============================
 * Functions for validating and sanitizing external data.
 * 
 * Pattern: Raw Data → Validate → Sanitize → Normalize → Store
 * 
 * - Validates against Zod schemas
 * - Logs validation failures
 * - Returns safe defaults on failure
 * - Never throws (graceful degradation)
 */

import { z } from 'zod'
import * as Schemas from './schemas'

// ============================================================================
// VALIDATION RESULT TYPE
// ============================================================================

export interface ValidationResult<T> {
  valid: boolean
  data: T | null
  error: string | null
  warnings: string[]
}

// ============================================================================
// BASE VALIDATOR
// ============================================================================

/**
 * Safe validation wrapper - never throws
 * Returns result object with success/failure status
 */
function safeValidate<T>(
  schema: z.ZodSchema<T>,
  data: unknown,
  context: string
): ValidationResult<T> {
  try {
    const parsed = schema.parse(data)
    return {
      valid: true,
      data: parsed,
      error: null,
      warnings: [],
    }
  } catch (err) {
    const zodErr = err as z.ZodError
    const errors = zodErr.errors.map(e => `${e.path.join('.')}: ${e.message}`).join('; ')
    const message = `[${context}] Validation failed: ${errors}`
    
    if (process.env.NODE_ENV === 'development') {
      console.warn(message, { data })
    }
    
    return {
      valid: false,
      data: null,
      error: message,
      warnings: [],
    }
  }
}

// ============================================================================
// DOMAIN VALIDATORS
// ============================================================================

export function validateOrder(data: unknown, context = 'Order'): ValidationResult<Schemas.Order> {
  return safeValidate(Schemas.OrderSchema, data, context)
}

export function validatePosition(data: unknown, context = 'Position'): ValidationResult<Schemas.Position> {
  return safeValidate(Schemas.PositionSchema, data, context)
}

export function validateTrade(data: unknown, context = 'Trade'): ValidationResult<Schemas.Trade> {
  return safeValidate(Schemas.TradeSchema, data, context)
}

export function validateMarketQuote(data: unknown, context = 'MarketQuote'): ValidationResult<Schemas.MarketQuote> {
  return safeValidate(Schemas.MarketQuoteSchema, data, context)
}

export function validateMarginInfo(data: unknown, context = 'MarginInfo'): ValidationResult<Schemas.MarginInfo> {
  return safeValidate(Schemas.MarginInfoSchema, data, context)
}

export function validatePnLData(data: unknown, context = 'PnLData'): ValidationResult<Schemas.PnLData> {
  return safeValidate(Schemas.PnLDataSchema, data, context)
}

export function validateDayPnL(data: unknown, context = 'DayPnL'): ValidationResult<Schemas.DayPnL> {
  return safeValidate(Schemas.DayPnLSchema, data, context)
}

export function validateUser(data: unknown, context = 'User'): ValidationResult<Schemas.User> {
  return safeValidate(Schemas.UserSchema, data, context)
}

export function validateMarketDepth(data: unknown, context = 'MarketDepth'): ValidationResult<Schemas.MarketDepth> {
  return safeValidate(Schemas.MarketDepthSchema, data, context)
}

// ============================================================================

// COLLECTIONS

export function validateOrders(data: unknown, context = 'Orders'): ValidationResult<Schemas.Order[]> {
  return safeValidate(Schemas.OrderArraySchema, data, context)
}

export function validatePositions(data: unknown, context = 'Positions'): ValidationResult<Schemas.Position[]> {
  return safeValidate(Schemas.PositionArraySchema, data, context)
}

export function validateTrades(data: unknown, context = 'Trades'): ValidationResult<Schemas.Trade[]> {
  return safeValidate(Schemas.TradeArraySchema, data, context)
}

export function validateQuoteRecord(data: unknown, context = 'Quotes'): ValidationResult<Record<string, Schemas.MarketQuote>> {
  return safeValidate(Schemas.QuoteRecordSchema, data, context)
}

// ============================================================================

// WEBSOCKET PAYLOADS

export function validateWSUpdatePayload(data: unknown, context = 'WSUpdate'): ValidationResult<Schemas.WSUpdatePayload> {
  return safeValidate(Schemas.WSUpdatePayloadSchema, data, context)
}

// ============================================================================
// SANITIZERS - Remove & Normalize Invalid Data
// ============================================================================

/**
 * Sanitize order array - remove invalid entries, keep valid ones
 * Returns guaranteed valid array (may be empty)
 */
export function sanitizeOrderArray(data: unknown): Schemas.Order[] {
  if (!Array.isArray(data)) {
    console.warn('[Sanitizer] Expected array, got:', typeof data)
    return []
  }

  return data
    .map((item, idx) => {
      const result = validateOrder(item, `Order[${idx}]`)
      return result.valid ? result.data : null
    })
    .filter((item): item is Schemas.Order => item !== null)
}

/**
 * Sanitize position array
 */
export function sanitizePositionArray(data: unknown): Schemas.Position[] {
  if (!Array.isArray(data)) {
    console.warn('[Sanitizer] Expected array, got:', typeof data)
    return []
  }

  return data
    .map((item, idx) => {
      const result = validatePosition(item, `Position[${idx}]`)
      return result.valid ? result.data : null
    })
    .filter((item): item is Schemas.Position => item !== null)
}

/**
 * Sanitize trade array
 */
export function sanitizeTradeArray(data: unknown): Schemas.Trade[] {
  if (!Array.isArray(data)) {
    console.warn('[Sanitizer] Expected array, got:', typeof data)
    return []
  }

  return data
    .map((item, idx) => {
      const result = validateTrade(item, `Trade[${idx}]`)
      return result.valid ? result.data : null
    })
    .filter((item): item is Schemas.Trade => item !== null)
}

/**
 * Sanitize quote record - remove invalid quotes, keep valid ones
 */
export function sanitizeQuoteRecord(data: unknown): Record<string, Schemas.MarketQuote> {
  if (!data || typeof data !== 'object' || Array.isArray(data)) {
    console.warn('[Sanitizer] Expected object, got:', typeof data)
    return {}
  }

  const result: Record<string, Schemas.MarketQuote> = {}
  for (const [key, value] of Object.entries(data)) {
    const validation = validateMarketQuote(value, `Quote[${key}]`)
    if (validation.valid && validation.data) {
      result[key] = validation.data
    }
  }
  return result
}

/**
 * Sanitize single order - use defaults for invalid fields
 */
export function sanitizeOrder(data: unknown): Schemas.Order | null {
  const result = validateOrder(data, 'SanitizeOrder')
  return result.valid ? result.data : null
}

/**
 * Sanitize single position
 */
export function sanitizePosition(data: unknown): Schemas.Position | null {
  const result = validatePosition(data, 'SanitizePosition')
  return result.valid ? result.data : null
}

/**
 * Sanitize single quote
 */
export function sanitizeMarketQuote(data: unknown): Schemas.MarketQuote | null {
  const result = validateMarketQuote(data, 'SanitizeQuote')
  return result.valid ? result.data : null
}

/**
 * Sanitize WebSocket update payload
 * Validates structure AND wrapped data
 */
export function sanitizeWSUpdatePayload(data: unknown): Schemas.WSUpdatePayload | null {
  const result = validateWSUpdatePayload(data, 'SanitizeWSPayload')
  if (!result.valid) {
    console.warn('[WS Sanitizer] Invalid payload structure:', result.error)
    return null
  }
  
  // Additional per-type validation if needed
  const payload = result.data as Schemas.WSUpdatePayload
  
  switch (payload.type) {
    case 'ORDER_UPDATE': {
      const orderCheck = validateOrder((payload as any).data, 'WSOrder')
      return orderCheck.valid ? payload : null
    }
    case 'POSITION_UPDATE': {
      const posCheck = validatePosition((payload as any).data, 'WSPosition')
      return posCheck.valid ? payload : null
    }
    case 'TRADE_UPDATE': {
      const tradeCheck = validateTrade((payload as any).data, 'WSTrade')
      return tradeCheck.valid ? payload : null
    }
    case 'QUOTE_UPDATE': {
      const quoteCheck = validateMarketQuote((payload as any).data, 'WSQuote')
      return quoteCheck.valid ? payload : null
    }
    case 'PnL_UPDATE': {
      const pnlCheck = validatePnLData((payload as any).data, 'WSPnL')
      return pnlCheck.valid ? payload : null
    }
    case 'DEPTH_UPDATE': {
      const depthCheck = validateMarketDepth((payload as any).data, 'WSDepth')
      return depthCheck.valid ? payload : null
    }
    default:
      return null
  }
}

// ============================================================================
// GUARD FUNCTIONS - For use in conditions
// ============================================================================

export function isValidOrder(data: unknown): data is Schemas.Order {
  return validateOrder(data).valid
}

export function isValidPosition(data: unknown): data is Schemas.Position {
  return validatePosition(data).valid
}

export function isValidTrade(data: unknown): data is Schemas.Trade {
  return validateTrade(data).valid
}

export function isValidMarketQuote(data: unknown): data is Schemas.MarketQuote {
  return validateMarketQuote(data).valid
}

export function isValidWSPayload(data: unknown): data is Schemas.WSUpdatePayload {
  return validateWSUpdatePayload(data).valid
}

// ============================================================================
// ERROR REPORTING
// ============================================================================

export function logValidationError(result: ValidationResult<any>, source: string) {
  if (!result.valid) {
    console.error(`[ValidationError] ${source}:`, result.error)
  }
}

export function throwOnValidationError<T>(
  result: ValidationResult<T>,
  source: string
): T {
  if (!result.valid) {
    throw new Error(`[ValidationError] ${source}: ${result.error}`)
  }
  return result.data!
}
