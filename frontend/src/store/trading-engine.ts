import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { tradingApi } from '../services/api'
import type { 
  Order, Position, Trade, MarginInfo, PnLData, 
  Portfolio, MarketQuote, CreateOrderRequest, DayPnL 
} from '../types'
import { 
  normalizeOrder, 
  normalizeOrders, 
  normalizePosition, 
  normalizePositions, 
  normalizePnL, 
  normalizeDayPnL, 
  normalizeMargin, 
  normalizePortfolio, 
  normalizeTick, 
  normalizeTicks 
} from '../utils/normalization'
import {
  validateOrdersForStore,
  validatePositionsForStore,
  validatePnLForStore,
  filterValidOrders,
  filterValidPositions,
  ValidationError,
} from '../validation/middleware'

export const DEFAULT_MARGIN: MarginInfo = {
  user_id: '',
  total_margin: 0,
  used_margin: 0,
  available_margin: 0,
  blocked_margin: 0,
  intraday_buying_power: 0,
  cash_balance: 0,
  holdings_value: 0,
  position_margins: {},
  timestamp: new Date(0).toISOString(),
};

export const DEFAULT_PNL: PnLData = {
  total_pnl: 0,
  realized_pnl: 0,
  unrealized_pnl: 0,
  day_pnl: 0,
  mode: 'paper',
  timestamp: new Date(0).toISOString(),
};

export const DEFAULT_DAY_PNL: DayPnL = {
  day_pnl: 0,
  buy_value: 0,
  sell_value: 0,
  brokerage: 0,
  taxes: 0,
  trades_count: 0,
  winning_trades: 0,
  losing_trades: 0,
  win_rate: 0,
};

export const DEFAULT_PORTFOLIO: Portfolio = {
  mode: 'paper',
  cash_balance: 0,
  holdings: {
    holdings: [],
    total_value: 0,
    total_cost: 0,
    total_pnl: 0,
    pnl_percent: 0,
    count: 0,
  },
  intraday: {
    trades_count: 0,
    buy_trades: 0,
    sell_trades: 0,
    total_buy_value: 0,
    total_sell_value: 0,
    brokerage: 0,
    taxes: 0,
    day_pnl: 0,
    symbols_traded: [],
    unique_symbols: 0,
  },
  pnl: DEFAULT_PNL,
  margin: DEFAULT_MARGIN,
  exposure: {
    total_exposure: 0,
    single_stock_exposure: {},
    position_count: 0,
  },
  timestamp: new Date(0).toISOString(),
};

interface TradingState {
  orders: Order[]
  positions: Position[]
  trades: Trade[]
  
  currentQuote: MarketQuote | null
  quotes: Record<string, MarketQuote>
  
  margin: MarginInfo
  pnl: PnLData
  dayPnL: DayPnL
  portfolio: Portfolio
  
  engineStatus: 'stopped' | 'running' | 'loading'
  mode: 'paper' | 'live'
  
  isLoadingOrders: boolean
  isLoadingPositions: boolean
  isLoadingPnL: boolean
  isSubmittingOrder: boolean
  
  isInitialized: boolean
  error: string | null
  
  fetchOrders: (params?: { status?: string; symbol?: string; mode?: string }) => Promise<void>
  createOrder: (order: CreateOrderRequest) => Promise<Order | null>
  cancelOrder: (orderId: string) => Promise<boolean>
  modifyOrder: (orderId: string, data: { price?: number; quantity?: number; trigger_price?: number }) => Promise<boolean>
  
  fetchPositions: (params?: { status?: string; symbol?: string; mode?: string }) => Promise<void>
  fetchOpenPositions: (params?: { mode?: string }) => Promise<void>
  exitPosition: (positionId: string, exitPrice?: number, quantity?: number) => Promise<boolean>
  
  fetchPnL: (mode?: string) => Promise<void>
  fetchDayPnL: (mode?: string) => Promise<void>
  fetchMargin: () => Promise<void>
  fetchPortfolio: (mode?: string) => Promise<void>
  
  fetchQuote: (symbol: string) => Promise<MarketQuote | null>
  fetchQuotes: (symbols?: string) => Promise<void>
  
  updateOrderFromWS: (order: Order) => void
  updateBatchedOrdersFromWS: (orders: Order[]) => void
  updatePositionFromWS: (position: Position) => void
  updateBatchedPositionsFromWS: (positions: Position[]) => void
  updatePnLFromWS: (pnl: PnLData) => void
  updateQuoteFromWS: (quote: MarketQuote) => void
  
  clearError: () => void
  setMode: (mode: 'paper' | 'live') => void
  setInitialized: (initialized: boolean) => void
  reset: () => void
}

const initialState: Omit<TradingState, 'fetchOrders' | 'createOrder' | 'cancelOrder' | 'modifyOrder' | 'fetchPositions' | 'fetchOpenPositions' | 'exitPosition' | 'fetchPnL' | 'fetchDayPnL' | 'fetchMargin' | 'fetchPortfolio' | 'fetchQuote' | 'fetchQuotes' | 'updateOrderFromWS' | 'updatePositionFromWS' | 'updatePnLFromWS' | 'updateQuoteFromWS' | 'clearError' | 'setMode' | 'setInitialized' | 'reset'> = {
  orders: [],
  positions: [],
  trades: [],
  currentQuote: null,
  quotes: {},
  margin: DEFAULT_MARGIN,
  pnl: DEFAULT_PNL,
  dayPnL: DEFAULT_DAY_PNL,
  portfolio: DEFAULT_PORTFOLIO,
  engineStatus: 'stopped',
  mode: 'paper',
  isLoadingOrders: false,
  isLoadingPositions: false,
  isLoadingPnL: false,
  isSubmittingOrder: false,
  isInitialized: false,
  error: null,
}

export const useTradingEngineStore = create<TradingState>()(
  persist(
    (set, get) => ({
      ...initialState,

      fetchOrders: async (params = {}) => {
        set({ isLoadingOrders: true, error: null })
        try {
          const response = await tradingApi.listOrders(params)
          
          // PHASE 3: Runtime validation before normalization
          let orders: Order[] = []
          try {
            const rawOrders = response?.data?.orders ?? []
            orders = filterValidOrders(rawOrders)
            
            if (process.env.NODE_ENV === 'development' && rawOrders.length !== orders.length) {
              console.warn(`[Orders] Filtered ${rawOrders.length - orders.length} invalid orders`)
            }
          } catch (validationErr) {
            console.error('[Orders] Validation error:', validationErr)
            orders = []
          }
          
          // Then normalize validated data
          set({ 
            orders: normalizeOrders(orders),
            isLoadingOrders: false 
          })
        } catch (error) {
          console.error('Failed to fetch orders:', error)
          set({ error: 'Failed to fetch orders', isLoadingOrders: false })
        }
      },
      
      createOrder: async (orderData) => {
        set({ isSubmittingOrder: true, error: null })
        try {
          const response = await tradingApi.createOrder(orderData)
          const rawOrder = response?.data?.order
          if (rawOrder) {
            const newOrder = normalizeOrder(rawOrder)
            set((state) => ({
              orders: [newOrder, ...(Array.isArray(state.orders) ? state.orders : [])],
              isSubmittingOrder: false,
            }))
            return newOrder
          }
          set({ isSubmittingOrder: false })
          return null
        } catch (error: unknown) {
          const err = error as { response?: { data?: { message?: string } } }
          const errorMessage = err?.response?.data?.message || 'Failed to place order'
          console.error('Failed to create order:', error)
          set({ error: errorMessage, isSubmittingOrder: false })
          return null
        }
      },
      
      cancelOrder: async (orderId) => {
        set({ isLoadingOrders: true })
        try {
          await tradingApi.cancelOrder(orderId)
          set((state) => ({
            orders: Array.isArray(state.orders)
              ? state.orders.map((o) =>
                  o?.order_id === orderId ? { ...o, status: 'CANCELLED' as const } : o
                )
              : [],
            isLoadingOrders: false,
          }))
          return true
        } catch (error) {
          console.error('Failed to cancel order:', error)
          set({ error: 'Failed to cancel order', isLoadingOrders: false })
          return false
        }
      },
      
      modifyOrder: async (orderId, data) => {
        set({ isLoadingOrders: true })
        try {
          await tradingApi.modifyOrder(orderId, data)
          set((state) => ({
            orders: Array.isArray(state.orders)
              ? state.orders.map((o) =>
                  o?.order_id === orderId ? { ...o, ...data } : o
                )
              : [],
            isLoadingOrders: false,
          }))
          return true
        } catch (error) {
          console.error('Failed to modify order:', error)
          set({ error: 'Failed to modify order', isLoadingOrders: false })
          return false
        }
      },
      
      fetchPositions: async (params = {}) => {
        set({ isLoadingPositions: true, error: null })
        try {
          const response = await tradingApi.listPositions(params)
          
          // PHASE 3: Runtime validation
          let positions: Position[] = []
          try {
            const rawPositions = response?.data?.positions ?? []
            positions = filterValidPositions(rawPositions)
            
            if (process.env.NODE_ENV === 'development' && rawPositions.length !== positions.length) {
              console.warn(`[Positions] Filtered ${rawPositions.length - positions.length} invalid positions`)
            }
          } catch (validationErr) {
            console.error('[Positions] Validation error:', validationErr)
            positions = []
          }
          
          set({ 
            positions: normalizePositions(positions),
            isLoadingPositions: false 
          })
        } catch (error) {
          console.error('Failed to fetch positions:', error)
          set({ error: 'Failed to fetch positions', isLoadingPositions: false })
        }
      },
      
      fetchOpenPositions: async (params = {}) => {
        set({ isLoadingPositions: true, error: null })
        try {
          const response = await tradingApi.getOpenPositions(params)
          
          // PHASE 3: Runtime validation
          let positions: Position[] = []
          try {
            const rawPositions = response?.data?.positions ?? []
            positions = filterValidPositions(rawPositions)
            
            if (process.env.NODE_ENV === 'development' && rawPositions.length !== positions.length) {
              console.warn(`[OpenPositions] Filtered ${rawPositions.length - positions.length} invalid positions`)
            }
          } catch (validationErr) {
            console.error('[OpenPositions] Validation error:', validationErr)
            positions = []
          }
          
          set({ 
            positions: normalizePositions(positions),
            isLoadingPositions: false 
          })
        } catch (error) {
          console.error('Failed to fetch open positions:', error)
          set({ error: 'Failed to fetch open positions', isLoadingPositions: false })
        }
      },
      
      exitPosition: async (positionId, exitPrice, quantity) => {
        set({ isLoadingPositions: true })
        try {
          await tradingApi.exitPosition(positionId, { exit_price: exitPrice, quantity })
          set((state) => ({
            positions: Array.isArray(state.positions)
              ? state.positions.filter((p) => p?.position_id !== positionId)
              : [],
            isLoadingPositions: false,
          }))
          return true
        } catch (error) {
          console.error('Failed to exit position:', error)
          set({ error: 'Failed to exit position', isLoadingPositions: false })
          return false
        }
      },
      
      fetchPnL: async (mode = 'paper') => {
        set({ isLoadingPnL: true })
        try {
          const response = await tradingApi.getPnL({ mode })
          set({ pnl: normalizePnL(response?.data) || DEFAULT_PNL, isLoadingPnL: false })
        } catch (error) {
          console.error('Failed to fetch P&L:', error)
          set({ isLoadingPnL: false })
        }
      },
      
      fetchDayPnL: async (mode = 'paper') => {
        try {
          const response = await tradingApi.getDayPnL({ mode })
          set({ dayPnL: normalizeDayPnL(response?.data) || DEFAULT_DAY_PNL })
        } catch (error) {
          console.error('Failed to fetch day P&L:', error)
        }
      },
      
      fetchMargin: async () => {
        try {
          const response = await tradingApi.getMargin()
          set({ margin: normalizeMargin(response?.data) || DEFAULT_MARGIN })
        } catch (error) {
          console.error('Failed to fetch margin:', error)
        }
      },
      
      fetchPortfolio: async (mode = 'paper') => {
        try {
          const response = await tradingApi.getPortfolio({ mode })
          set({ portfolio: normalizePortfolio(response?.data) || DEFAULT_PORTFOLIO })
        } catch (error) {
          console.error('Failed to fetch portfolio:', error)
        }
      },
      
      fetchQuote: async (symbol) => {
        try {
          const response = await tradingApi.getMarketQuotes(symbol)
          const quote = response?.data?.quotes?.[symbol]
          if (quote) {
            const normalizedQuote = normalizeTick(quote)
            set((state) => ({
              currentQuote: normalizedQuote,
              quotes: { ...state.quotes, [symbol]: normalizedQuote }
            }))
            return normalizedQuote
          }
          return null
        } catch (error) {
          console.error('Failed to fetch quote:', error)
          return null
        }
      },
      
      fetchQuotes: async (symbols) => {
        try {
          const response = await tradingApi.getMarketQuotes(symbols)
          set((state) => ({
            quotes: { ...state.quotes, ...normalizeTicks(response?.data?.quotes) }
          }))
        } catch (error) {
          console.error('Failed to fetch quotes:', error)
        }
      },
      
      updateOrderFromWS: (order) => {
        if (!order?.order_id) return
        const normalizedOrder = normalizeOrder(order)
        set((state) => ({
          orders: Array.isArray(state.orders)
            ? state.orders.map((o) => o?.order_id === normalizedOrder.order_id ? normalizedOrder : o)
            : []
        }))
      },

      updateBatchedOrdersFromWS: (orders) => {
        if (!Array.isArray(orders) || orders.length === 0) return
        set((state) => {
          const newOrders = [...(Array.isArray(state.orders) ? state.orders : [])]
          orders.forEach(order => {
            const normalized = normalizeOrder(order)
            const idx = newOrders.findIndex(o => o.order_id === normalized.order_id)
            if (idx !== -1) {
              newOrders[idx] = normalized
            } else {
              newOrders.unshift(normalized)
            }
          })
          return { orders: newOrders }
        })
      },
      
      updatePositionFromWS: (position) => {
        if (!position?.position_id) return
        const normalizedPosition = normalizePosition(position)
        set((state) => ({
          positions: Array.isArray(state.positions)
            ? state.positions.some(p => p?.position_id === normalizedPosition.position_id)
              ? state.positions.map((p) => p?.position_id === normalizedPosition.position_id ? normalizedPosition : p)
              : [...state.positions, normalizedPosition]
            : [normalizedPosition]
        }))
      },

      updateBatchedPositionsFromWS: (positions) => {
        if (!Array.isArray(positions) || positions.length === 0) return
        set((state) => {
          const newPositions = [...(Array.isArray(state.positions) ? state.positions : [])]
          positions.forEach(position => {
            const normalized = normalizePosition(position)
            const idx = newPositions.findIndex(p => p.position_id === normalized.position_id)
            if (idx !== -1) {
              newPositions[idx] = normalized
            } else {
              newPositions.push(normalized)
            }
          })
          return { positions: newPositions }
        })
      },
      
      updatePnLFromWS: (pnl) => {
        set({ pnl: normalizePnL(pnl) || DEFAULT_PNL })
      },
      
      updateQuoteFromWS: (quote) => {
        if (!quote?.symbol) return
        const normalizedQuote = normalizeTick(quote)
        set((state) => ({
          currentQuote: normalizedQuote,
          quotes: { ...state.quotes, [normalizedQuote.symbol]: normalizedQuote }
        }))
      },
      
      clearError: () => set({ error: null }),
      
      setMode: (mode: 'paper' | 'live') => set({ mode }),
      
      setInitialized: (initialized) => set({ isInitialized: initialized }),
      
      reset: () => set(initialState),
    }),
    {
      name: 'trading-engine-storage',
      storage: createJSONStorage(() => sessionStorage),
      partialize: (state) => ({
        engineStatus: state.engineStatus,
        mode: state.mode,
        isInitialized: state.isInitialized,
      }),
    }
  )
)

export default useTradingEngineStore