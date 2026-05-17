/**
 * Comprehensive WebSocket Integration Hook
 * ==========================================
 * Connects WebSocket events to all Zustand stores for realtime sync.
 */

import { useEffect, useCallback, useRef } from 'react'
import { wsManager } from '../websocket/websocket.manager'
import { useAuthStore } from '../store/auth'
import { useMarketStore } from '../store/market'
import { useTradingStore } from '../store/trading'
import { useNotificationStore } from '../store/notifications'
import { useFundsStore } from '../store/funds'
import type {
  MarketTickPayload,
  OrderUpdatePayload,
  PositionUpdatePayload,
  PnLUpdatePayload,
  AISignalPayload,
  NotificationPayload,
  MarketStatusPayload
} from '../websocket/websocket.types'

const INDIAN_SYMBOLS = [
  'RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK',
  'SBIN', 'BHARTIARTL', 'HINDUNILVR', 'KOTAKBANK', 'ITC',
  'AXISBANK', 'BAJFINANCE', 'MARUTI', 'HCLTECH', 'WIPRO'
]

export function useRealtimeConnection() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  const token = useAuthStore((state) => state.accessToken)
  const initialized = useRef(false)

  useEffect(() => {
    if (isAuthenticated && token && !initialized.current) {
      console.log('[Realtime] Connecting to WebSocket...')
      wsManager.connect(token)
      initialized.current = true
    }

    return () => {
      if (!isAuthenticated) {
        wsManager.disconnect()
        initialized.current = false
      }
    }
  }, [isAuthenticated, token])

  return {
    isConnected: wsManager.isConnected(),
    status: wsManager.getStatus(),
  }
}

export function useRealtimeMarketData() {
  const { updatePrice, quotes } = useMarketStore()

  useEffect(() => {
    const unsubscribe = wsManager.on<MarketTickPayload>('market_tick', (data) => {
      updatePrice(data.symbol, data.last_price, data.change, data.change_percent)
    })

    wsManager.subscribeMarket(INDIAN_SYMBOLS)

    return () => {
      unsubscribe()
      wsManager.unsubscribeMarket(INDIAN_SYMBOLS)
    }
  }, [updatePrice])

  return { quotes }
}

export function useRealtimeOrders() {
  const { orders, addOrder, updateOrder } = useTradingStore()

  useEffect(() => {
    const unsubscribers = [
      wsManager.on<OrderUpdatePayload>('order_update', (data) => {
        updateOrder({
          _id: data.order_id,
          order_id: data.order_id,
          order_type: data.status,
          symbol: '',
          side: 'BUY' as const,
          quantity: data.filled_quantity,
          entry_price: data.average_price || 0,
          status: data.status,
          created_at: data.timestamp,
        })
      }),
      wsManager.on<OrderUpdatePayload>('order_created', (data) => {
        addOrder({
          _id: data.order_id,
          order_id: data.order_id,
          order_type: data.status,
          symbol: '',
          side: 'BUY' as const,
          quantity: data.filled_quantity,
          entry_price: data.average_price || 0,
          status: 'OPEN',
          created_at: data.timestamp,
        })
      }),
      wsManager.on<OrderUpdatePayload>('order_executed', (data) => {
        updateOrder({
          _id: data.order_id,
          order_id: data.order_id,
          order_type: 'FILLED',
          symbol: '',
          side: 'BUY' as const,
          quantity: data.filled_quantity,
          entry_price: data.average_price || 0,
          status: 'FILLED',
          created_at: data.timestamp,
        })
      }),
    ]

    wsManager.subscribeUser(['orders'])

    return () => {
      unsubscribers.forEach((unsub) => unsub())
    }
  }, [addOrder, updateOrder])

  return { orders }
}

export function useRealtimePositions() {
  const { positions, addPosition, updatePosition, removePosition } = useTradingStore()

  useEffect(() => {
    const unsubscribers = [
      wsManager.on<PositionUpdatePayload>('position_update', (data) => {
        const existingPosition = positions.find(
          (p) => p._id === data.position_id || p.position_id === data.position_id
        )

        if (existingPosition) {
          updatePosition({
            ...existingPosition,
            current_price: data.current_price,
            unrealized_pnl: data.unrealized_pnl,
            unrealized_pnl_percent: data.pnl_percent,
          })
        }
      }),
      wsManager.on<PositionUpdatePayload>('position_opened', (data) => {
        addPosition({
          _id: data.position_id,
          position_id: data.position_id,
          strategy_name: '',
          symbol: data.symbol,
          side: 'BUY' as const,
          entry_price: data.current_price,
          quantity: data.quantity,
          current_price: data.current_price,
          unrealized_pnl: data.unrealized_pnl,
          unrealized_pnl_percent: data.pnl_percent,
          mode: 'paper' as const,
          opened_at: data.timestamp,
        })
      }),
      wsManager.on<PositionUpdatePayload>('position_closed', (data) => {
        removePosition(data.position_id)
      }),
    ]

    wsManager.subscribeUser(['positions'])

    return () => {
      unsubscribers.forEach((unsub) => unsub())
    }
  }, [positions, addPosition, updatePosition, removePosition])

  return { positions }
}

export function useRealtimePnL() {
  const { positions } = useTradingStore()
  const { funds } = useFundsStore()

  useEffect(() => {
    const unsubscribe = wsManager.on<PnLUpdatePayload>('pnl_update', (data) => {
      console.log('[PnL Update]', data)
    })

    wsManager.subscribeUser(['pnl'])

    return unsubscribe
  }, [positions, funds])

  return { funds }
}

export function useRealtimeNotifications() {
  const { addNotification } = useNotificationStore()

  useEffect(() => {
    const unsubscribe = wsManager.on<NotificationPayload>('notification', (data) => {
      addNotification({
        _id: data.notification_id,
        type: data.type,
        title: data.title,
        message: data.message,
        priority: mapPriority(data.priority),
        is_read: false,
        is_dismissed: false,
        created_at: data.timestamp,
      })
    })

    return unsubscribe
  }, [addNotification])
}

function mapPriority(priority: string): 'low' | 'medium' | 'high' | 'critical' {
  const map: Record<string, 'low' | 'medium' | 'high' | 'critical'> = {
    'LOW': 'low',
    'MEDIUM': 'medium',
    'HIGH': 'high',
    'CRITICAL': 'critical',
  }
  return map[priority] || 'medium'
}

export function useRealtimeAISignals() {
  const [signals, setSignals] = React.useState<AISignalPayload[]>([])

  useEffect(() => {
    const unsubscribe = wsManager.on<AISignalPayload>('ai_signal', (data) => {
      setSignals((prev) => [data, ...prev.slice(0, 9)])
    })

    return unsubscribe
  }, [])

  return { signals }
}

export function useRealtimeMarketStatus() {
  const [status, setStatus] = React.useState<MarketStatusPayload | null>(null)

  useEffect(() => {
    const unsubscribe = wsManager.on<MarketStatusPayload>('market_status', (data) => {
      setStatus(data)
    })

    wsManager.emitCustomEvent('get_market_status', {})

    return unsubscribe
  }, [])

  return { status }
}

export function useMarketSubscription() {
  const subscribe = useCallback((symbols: string[]) => {
    wsManager.subscribeMarket(symbols)
  }, [])

  const unsubscribe = useCallback((symbols: string[]) => {
    wsManager.unsubscribeMarket(symbols)
  }, [])

  return { subscribe, unsubscribe }
}

export function useOrderPlacement() {
  const placeOrder = useCallback((order: {
    order_type: string
    product: string
    symbol: string
    exchange: string
    side: string
    quantity: number
    price?: number
    trigger_price?: number
  }) => {
    wsManager.placeOrder(order)
  }, [])

  const cancelOrder = useCallback((orderId: string) => {
    wsManager.cancelOrder(orderId)
  }, [])

  return { placeOrder, cancelOrder }
}

export function useStrategyControl() {
  const startStrategy = useCallback((strategyId: string) => {
    wsManager.startStrategy(strategyId)
  }, [])

  const stopStrategy = useCallback((strategyId: string) => {
    wsManager.stopStrategy(strategyId)
  }, [])

  return { startStrategy, stopStrategy }
}

import React from 'react'

export default {
  useRealtimeConnection,
  useRealtimeMarketData,
  useRealtimeOrders,
  useRealtimePositions,
  useRealtimePnL,
  useRealtimeNotifications,
  useRealtimeAISignals,
  useRealtimeMarketStatus,
  useMarketSubscription,
  useOrderPlacement,
  useStrategyControl,
}