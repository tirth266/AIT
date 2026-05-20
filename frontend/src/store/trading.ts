import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { 
  normalizeOrder, 
  normalizePosition, 
  normalizeTrade, 
  normalizeStrategy,
  safeNumber,
  safeString,
  normalizeSymbol
} from '../utils/normalization'

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

export const DEFAULT_RISK_SETTINGS: RiskSettings = {
  stop_loss_percent: 0,
  take_profit_percent: 0,
  trailing_stop_enabled: false,
  trailing_stop_percent: 0,
  position_size_type: 'fixed',
  position_size: 0,
};

export const DEFAULT_STRATEGY: Strategy = {
  _id: '',
  strategy_name: '',
  symbol: '',
  timeframe: '',
  mode: 'paper',
  broker: '',
  is_active: false,
  indicators: [],
  entry_conditions: [],
  exit_conditions: [],
  risk_settings: DEFAULT_RISK_SETTINGS,
  created_at: new Date(0).toISOString(),
};

export const normalizeBot = (raw: any): Bot => {
  return {
    strategy_id: safeString(raw?.strategy_id),
    strategy_name: safeString(raw?.strategy_name),
    symbol: raw?.symbol ? normalizeSymbol(raw.symbol) : undefined,
    status: (raw?.status || 'stopped') as any,
    mode: (raw?.mode || 'paper') as any,
    last_signal: raw?.last_signal as any,
    last_signal_time: raw?.last_signal_time,
    trades_today: safeNumber(raw?.trades_today),
    pnl_today: safeNumber(raw?.pnl_today),
    uptime_seconds: safeNumber(raw?.uptime_seconds),
  };
};

interface TradingState {
  mode: 'paper' | 'live'
  positions: Position[]
  trades: Trade[]
  orders: Order[]
  strategies: Strategy[]
  bots: Bot[]
  selectedStrategy: Strategy
  isLoading: boolean
  isInitialized: boolean
  
  setMode: (mode: 'paper' | 'live') => void
  setPositions: (positions: Position[]) => void
  setTrades: (trades: Trade[]) => void
  setOrders: (orders: Order[]) => void
  setStrategies: (strategies: Strategy[]) => void
  setBots: (bots: Bot[]) => void
  setSelectedStrategy: (strategy: Strategy) => void
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
  mode: 'paper' as const,
  positions: [] as Position[],
  trades: [] as Trade[],
  orders: [] as Order[],
  strategies: [] as Strategy[],
  bots: [] as Bot[],
  selectedStrategy: DEFAULT_STRATEGY,
  isLoading: false,
  isInitialized: false,
}

export const useTradingStore = create<TradingState>()(
  persist(
    (set) => ({
      ...initialState,

      setMode: (mode) => set({ mode }),

      setPositions: (positions) => set({ 
        positions: Array.isArray(positions) ? positions.map(p => normalizePosition(p) as any) : [] 
      }),
      
      setTrades: (trades) => set({ 
        trades: Array.isArray(trades) ? trades.map(t => normalizeTrade(t) as any) : [] 
      }),
      
      setOrders: (orders) => set({ 
        orders: Array.isArray(orders) ? orders.map(o => normalizeOrder(o) as any) : [] 
      }),
      
      setStrategies: (strategies) => set({ 
        strategies: Array.isArray(strategies) ? strategies.map(s => normalizeStrategy(s) as any) : [] 
      }),
      
      setBots: (bots) => set({ 
        bots: Array.isArray(bots) ? bots.map(normalizeBot) : [] 
      }),
      
      setSelectedStrategy: (strategy) => set({ 
        selectedStrategy: strategy ? normalizeStrategy(strategy) as any : DEFAULT_STRATEGY 
      }),
      
      addPosition: (position) => {
        const normalized = normalizePosition(position) as any;
        set((state) => ({ 
          positions: [normalized, ...(Array.isArray(state.positions) ? state.positions : [])] 
        }));
      },
      
      updatePosition: (position) => {
        const normalized = normalizePosition(position) as any;
        set((state) => ({
          positions: Array.isArray(state.positions)
            ? state.positions.map((p) => 
                p?._id === normalized?._id || p?.position_id === normalized?.position_id 
                  ? normalized 
                  : p
              )
            : []
        }));
      },
      
      removePosition: (id) => set((state) => ({
        positions: Array.isArray(state.positions)
          ? state.positions.filter((p) => p?._id !== id && p?.position_id !== id)
          : []
      })),
      
      addTrade: (trade) => {
        const normalized = normalizeTrade(trade) as any;
        set((state) => ({ 
          trades: [normalized, ...(Array.isArray(state.trades) ? state.trades : [])] 
        }));
      },
      
      updateTrade: (trade) => {
        const normalized = normalizeTrade(trade) as any;
        set((state) => ({
          trades: Array.isArray(state.trades)
            ? state.trades.map((t) => 
                t?._id === normalized?._id || t?.trade_id === normalized?.trade_id 
                  ? normalized 
                  : t
              )
            : []
        }));
      },
      
      addOrder: (order) => {
        const normalized = normalizeOrder(order) as any;
        set((state) => ({ 
          orders: [normalized, ...(Array.isArray(state.orders) ? state.orders : [])] 
        }));
      },
      
      updateOrder: (order) => {
        const normalized = normalizeOrder(order) as any;
        set((state) => ({
          orders: Array.isArray(state.orders)
            ? state.orders.map((o) => 
                o?.order_id === normalized?.order_id 
                  ? normalized 
                  : o
              )
            : []
        }));
      },
      
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
