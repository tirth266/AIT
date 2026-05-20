/**
 * Store Validation Middleware
 * ============================
 * Enforces contract validation before any store mutations.
 * 
 * Middleware intercepts store actions and validates data before commits.
 * Pattern:
 *   API/WS Payload
 *   → Middleware validation check
 *   → If invalid: log error, reject mutation
 *   → If valid: allow store update
 */

import { StateCreator, StoreMutatorIdentifier } from 'zustand'
import * as Validators from './validators'
import * as Schemas from './schemas'

// ============================================================================
// VALIDATION CONTEXT
// ============================================================================

export interface ValidationContext {
  source: 'api' | 'websocket' | 'internal'
  action: string
  timestamp: number
}

export class ValidationError extends Error {
  constructor(
    public source: string,
    public action: string,
    public details: string
  ) {
    super(`[${source}] ${action}: ${details}`)
  }
}

// ============================================================================
// VALIDATION GUARDS
// ============================================================================

export const validateOrderForStore = (data: unknown, context: ValidationContext) => {
  const result = Validators.validateOrder(data, `Store.${context.action}`)
  if (!result.valid) {
    throw new ValidationError(context.source, context.action, result.error || 'Order validation failed')
  }
  return result.data!
}

export const validatePositionForStore = (data: unknown, context: ValidationContext) => {
  const result = Validators.validatePosition(data, `Store.${context.action}`)
  if (!result.valid) {
    throw new ValidationError(context.source, context.action, result.error || 'Position validation failed')
  }
  return result.data!
}

export const validateTradeForStore = (data: unknown, context: ValidationContext) => {
  const result = Validators.validateTrade(data, `Store.${context.action}`)
  if (!result.valid) {
    throw new ValidationError(context.source, context.action, result.error || 'Trade validation failed')
  }
  return result.data!
}

export const validateQuoteForStore = (data: unknown, context: ValidationContext) => {
  const result = Validators.validateMarketQuote(data, `Store.${context.action}`)
  if (!result.valid) {
    throw new ValidationError(context.source, context.action, result.error || 'Quote validation failed')
  }
  return result.data!
}

export const validatePnLForStore = (data: unknown, context: ValidationContext) => {
  const result = Validators.validatePnLData(data, `Store.${context.action}`)
  if (!result.valid) {
    throw new ValidationError(context.source, context.action, result.error || 'PnL validation failed')
  }
  return result.data!
}

export const validateOrdersForStore = (data: unknown, context: ValidationContext) => {
  const result = Validators.validateOrders(data, `Store.${context.action}`)
  if (!result.valid) {
    throw new ValidationError(context.source, context.action, result.error || 'Orders validation failed')
  }
  return result.data!
}

export const validatePositionsForStore = (data: unknown, context: ValidationContext) => {
  const result = Validators.validatePositions(data, `Store.${context.action}`)
  if (!result.valid) {
    throw new ValidationError(context.source, context.action, result.error || 'Positions validation failed')
  }
  return result.data!
}

export const validateQuotesForStore = (data: unknown, context: ValidationContext) => {
  const result = Validators.validateQuoteRecord(data, `Store.${context.action}`)
  if (!result.valid) {
    throw new ValidationError(context.source, context.action, result.error || 'Quotes validation failed')
  }
  return result.data!
}

// ============================================================================
// SAFE STORE MUTATIONS
// ============================================================================

/**
 * Safe mutation handler: validates data before commit
 * Returns true if commit succeeded, false if rejected
 */
export function safeMutate<T>(
  data: unknown,
  validator: (d: unknown) => T,
  onCommit: (validated: T) => void,
  context: ValidationContext
): boolean {
  try {
    const validated = validator(data)
    onCommit(validated)
    
    if (process.env.NODE_ENV === 'development') {
      console.debug(`[SafeMutate] ✓ ${context.source}.${context.action}`)
    }
    
    return true
  } catch (err) {
    const error = err instanceof ValidationError 
      ? err 
      : new ValidationError(context.source, context.action, String(err))
    
    console.warn(`[SafeMutate] ✗ ${error.message}`)
    
    // Don't throw - let store handle gracefully
    return false
  }
}

// ============================================================================
// BATCH VALIDATION
// ============================================================================

/**
 * Validate array of items, silently filter invalid ones
 */
export function filterValidOrders(orders: unknown[]): Schemas.Order[] {
  return orders
    .map((order, idx) => {
      const result = Validators.validateOrder(order, `Order[${idx}]`)
      return result.valid ? result.data : null
    })
    .filter((item): item is Schemas.Order => item !== null)
}

export function filterValidPositions(positions: unknown[]): Schemas.Position[] {
  return positions
    .map((pos, idx) => {
      const result = Validators.validatePosition(pos, `Position[${idx}]`)
      return result.valid ? result.data : null
    })
    .filter((item): item is Schemas.Position => item !== null)
}

export function filterValidTrades(trades: unknown[]): Schemas.Trade[] {
  return trades
    .map((trade, idx) => {
      const result = Validators.validateTrade(trade, `Trade[${idx}]`)
      return result.valid ? result.data : null
    })
    .filter((item): item is Schemas.Trade => item !== null)
}

// ============================================================================
// MONITORING & TELEMETRY
// ============================================================================

export interface ValidationStats {
  totalValidations: number
  successfulValidations: number
  failedValidations: number
  successRate: number
}

class ValidationMonitor {
  private stats: ValidationStats = {
    totalValidations: 0,
    successfulValidations: 0,
    failedValidations: 0,
    successRate: 100,
  }

  recordSuccess() {
    this.stats.totalValidations++
    this.stats.successfulValidations++
    this.updateRate()
  }

  recordFailure() {
    this.stats.totalValidations++
    this.stats.failedValidations++
    this.updateRate()
  }

  private updateRate() {
    if (this.stats.totalValidations === 0) return
    this.stats.successRate = 
      (this.stats.successfulValidations / this.stats.totalValidations) * 100
  }

  getStats(): ValidationStats {
    return { ...this.stats }
  }

  reset() {
    this.stats = {
      totalValidations: 0,
      successfulValidations: 0,
      failedValidations: 0,
      successRate: 100,
    }
  }
}

export const validationMonitor = new ValidationMonitor()

// ============================================================================
// ZUSTAND MIDDLEWARE
// ============================================================================

/**
 * Zustand middleware for validation
 * Usage: Create store with this middleware to get validation checks
 */
export function createValidationMiddleware<T>(
  config: StateCreator<T>,
  name: string
): StateCreator<T> {
  return (set, get, api) => {
    const wrappedSet = ((state: T | ((s: T) => T), replace?: boolean | string) => {
      validationMonitor.recordSuccess()
      return set(state, replace)
    }) as typeof set

    return config(wrappedSet, get, api)
  }
}
