/**
 * Comprehensive WebSocket Integration Hook
 * ==========================================
 * Connects WebSocket events to all Zustand stores for realtime sync.
 */

import { useEffect, useCallback, useRef } from 'react'
import { wsManager } from '../websocket/websocket.manager'
import { useMarketStore } from '../store/market'
import { useTradingStore } from '../store/trading'
import { useTradingEngineStore } from '../store/trading-engine'
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
  const initialized = useRef(false)

  useEffect(() => {
    if (!initialized.current) {
      console.log('[Realtime] Connecting to WebSocket...')
      wsManager.connect()
      initialized.current = true
    }

    return () => {
      wsManager.disconnect()
      initialized.current = false
    }
  }, [])

  return {
    isConnected: wsManager.isConnected(),
    status: wsManager.getStatus(),
  }
}

export function useRealtimeMarketData() {
  const updateBatchedTicks = useMarketStore(state => state.updateBatchedTicks)

  useEffect(() => {
    const unsubscribe = wsManager.on<MarketTickPayload[]>('batched_ticks', (ticks) => {
      updateBatchedTicks(ticks as any)
    })

    wsManager.subscribeMarket(INDIAN_SYMBOLS)

    return () => {
      unsubscribe()
      wsManager.unsubscribeMarket(INDIAN_SYMBOLS)
    }
  }, [updateBatchedTicks])
}

export function useRealtimeOrders() {
  const updateBatchedOrders = useTradingEngineStore(state => state.updateBatchedOrdersFromWS)

  useEffect(() => {
    const unsubscribe = wsManager.on<OrderUpdatePayload[]>('batched_orders', (orders) => {
      updateBatchedOrders(orders as any)
    })

    wsManager.subscribeUser(['orders'])

    return () => {
      unsubscribe()
    }
  }, [updateBatchedOrders])
}

export function useRealtimePositions() {
  const updateBatchedPositions = useTradingEngineStore(state => state.updateBatchedPositionsFromWS)

  useEffect(() => {
    const unsubscribe = wsManager.on<PositionUpdatePayload[]>('batched_positions', (positions) => {
      updateBatchedPositions(positions as any)
    })

    wsManager.subscribeUser(['positions'])

    return () => {
      unsubscribe()
    }
  }, [updateBatchedPositions])
}

export function useRealtimePnL() {
  const updatePnLFromWS = useTradingEngineStore(state => state.updatePnLFromWS)

  useEffect(() => {
    const unsubscribe = wsManager.on<PnLUpdatePayload>('pnl_update', (data) => {
      updatePnLFromWS(data)
    })

    wsManager.subscribeUser(['pnl'])

    return unsubscribe
  }, [updatePnLFromWS])
}

export function useRealtimeNotifications() {
  const addNotification = useNotificationStore(state => state.addNotification)

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