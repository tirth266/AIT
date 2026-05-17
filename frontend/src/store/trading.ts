import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

export interface Position {
  _id: string
  position_id?: string
  strategy_name: string
  symbol: string
  side: 'BUY' | 'SELL'
  entry_price: number
  quantity: number
  current_price: number
  unrealized_pnl: number
  unrealized_pnl_percent: number
  stop_loss?: number
  take_profit?: number
  mode: 'paper' | 'live'
  opened_at: string
}

export interface Trade {
  _id: string
  trade_id?: string
  order_id?: string
  strategy_name: string
  symbol: string
  side: 'BUY' | 'SELL'
  entry_price: number
  exit_price?: number
  quantity: number
  pnl?: number
  pnl_percent?: number
  commission?: number
  mode: 'paper' | 'live'
  status: 'OPEN' | 'CLOSED' | 'CANCELLED'
  entry_time: string
  exit_time?: string
  exit_reason?: string
  duration_minutes?: number
}

export interface Order {
  order_id: string
  order_type: string
  product: string
  symbol: string
  exchange: string
  side: 'BUY' | 'SELL'
  quantity: number
  price?: number
  trigger_price?: number
  status: string
  filled_quantity: number
  average_price?: number
  created_at: string
}

export interface Strategy {
  _id: string
  strategy_name: string
  symbol: string
  timeframe: string
  mode: 'paper' | 'live'
  broker: string
  is_active: boolean
  indicators: Indicator[]
  entry_conditions: Condition[]
  exit_conditions: Condition[]
  risk_settings: RiskSettings
  last_evaluated_at?: string
  created_at: string
  updated_at?: string
  total_trades?: number
  total_pnl?: number
}

export interface Indicator {
  name: string
  params: Record<string, number>
  enabled: boolean
}

export interface Condition {
  indicator_name: string
  operator: string
  value: string | number
  logic: 'AND' | 'OR'
}

export interface RiskSettings {
  stop_loss_percent: number
  take_profit_percent: number
  trailing_stop_enabled: boolean
  trailing_stop_percent: number
  position_size_type: 'fixed' | 'calculated'
  position_size_percent?: number
  position_size?: number
}

export interface Bot {
  strategy_id: string
  strategy_name: string
  symbol?: string
  status: 'starting' | 'running' | 'stopping' | 'stopped' | 'paused' | 'error'
  mode: 'paper' | 'live'
  last_signal?: 'BUY' | 'SELL'
  last_signal_time?: string
  trades_today: number
  pnl_today: number
  uptime_seconds?: number
}

interface TradingState {
  positions: Position[]
  trades: Trade[]
  orders: Order[]
  strategies: Strategy[]
  bots: Bot[]
  selectedStrategy: Strategy | null
  isLoading: boolean
  isInitialized: boolean
  
  setPositions: (positions: Position[]) => void
  setTrades: (trades: Trade[]) => void
  setOrders: (orders: Order[]) => void
  setStrategies: (strategies: Strategy[]) => void
  setBots: (bots: Bot[]) => void
  setSelectedStrategy: (strategy: Strategy | null) => void
  addPosition: (position: Position) => void
  updatePosition: (position: Position) => void
  removePosition: (id: string) => void
  addTrade: (trade: Trade) => void
  updateTrade: (trade: Trade) => void
  addOrder: (order: Order) => void
  updateOrder: (order: Order) => void
  setLoading: (loading: boolean) => void
  setInitialized: (initialized: boolean) => void
  reset: () => void
}

const initialState = {
  positions: [] as Position[],
  trades: [] as Trade[],
  orders: [] as Order[],
  strategies: [] as Strategy[],
  bots: [] as Bot[],
  selectedStrategy: null as Strategy | null,
  isLoading: false,
  isInitialized: false,
}

export const useTradingStore = create<TradingState>()(
  persist(
    (set) => ({
      ...initialState,

      setPositions: (positions) => set({ 
        positions: Array.isArray(positions) ? positions : [] 
      }),
      
      setTrades: (trades) => set({ 
        trades: Array.isArray(trades) ? trades : [] 
      }),
      
      setOrders: (orders) => set({ 
        orders: Array.isArray(orders) ? orders : [] 
      }),
      
      setStrategies: (strategies) => set({ 
        strategies: Array.isArray(strategies) ? strategies : [] 
      }),
      
      setBots: (bots) => set({ 
        bots: Array.isArray(bots) ? bots : [] 
      }),
      
      setSelectedStrategy: (strategy) => set({ 
        selectedStrategy: strategy ?? null 
      }),
      
      addPosition: (position) => set((state) => ({ 
        positions: [position, ...(Array.isArray(state.positions) ? state.positions : [])] 
      })),
      
      updatePosition: (position) => set((state) => ({
        positions: Array.isArray(state.positions)
          ? state.positions.map((p) => 
              p?._id === position?._id || p?.position_id === position?.position_id 
                ? position 
                : p
            )
          : []
      })),
      
      removePosition: (id) => set((state) => ({
        positions: Array.isArray(state.positions)
          ? state.positions.filter((p) => p?._id !== id && p?.position_id !== id)
          : []
      })),
      
      addTrade: (trade) => set((state) => ({ 
        trades: [trade, ...(Array.isArray(state.trades) ? state.trades : [])] 
      })),
      
      updateTrade: (trade) => set((state) => ({
        trades: Array.isArray(state.trades)
          ? state.trades.map((t) => 
              t?._id === trade?._id || t?.trade_id === trade?.trade_id 
                ? trade 
                : t
            )
          : []
      })),
      
      addOrder: (order) => set((state) => ({ 
        orders: [order, ...(Array.isArray(state.orders) ? state.orders : [])] 
      })),
      
      updateOrder: (order) => set((state) => ({
        orders: Array.isArray(state.orders)
          ? state.orders.map((o) => 
              o?.order_id === order?.order_id 
                ? order 
                : o
            )
          : []
      })),
      
      setLoading: (isLoading) => set({ isLoading }),
      
      setInitialized: (isInitialized) => set({ isInitialized }),
      
      reset: () => set(initialState),
    }),
    {
      name: 'trading-storage',
      storage: createJSONStorage(() => sessionStorage),
      partialize: (state) => ({
        selectedStrategy: state.selectedStrategy,
        isInitialized: state.isInitialized,
      }),
    }
  )
)

export default useTradingStore