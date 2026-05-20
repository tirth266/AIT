/**
 * WebSocket React Hooks
 * =====================
 * React hooks for consuming WebSocket events.
 */

import { useEffect, useCallback, useRef } from 'react'
import { wsManager, WebSocketManager } from './websocket.manager'
import { useMarketStore } from '../store/market'
import { useTradingStore } from '../store/trading'
import { useNotificationStore } from '../store/notifications'
import type {
  MarketTickPayload,
  OrderUpdatePayload,
  PositionUpdatePayload,
  PnLUpdatePayload,
  AISignalPayload,
  NotificationPayload,
  StrategyUpdatePayload,
} from './websocket.types'

export function useWebSocket() {
  const initialized = useRef(false)

  useEffect(() => {
    if (!initialized.current) {
      console.log('[Hook] Connecting WebSocket')
      wsManager.connect()
      initialized.current = true
    }

    return () => {
      wsManager.disconnect()
      initialized.current = false
    }
  }, [])

  return wsManager
}

export function useMarketEvents() {
  const ws = useWebSocket()
  const { updatePrice } = useMarketStore()

  useEffect(() => {
    const unsubscribe = ws.on<MarketTickPayload>('market_tick', (data) => {
      updatePrice(data.symbol, data.last_price, data.change, data.change_percent)
    })

    return unsubscribe
  }, [ws, updatePrice])
}

export function useTradingEvents() {
  const ws = useWebSocket()
  const { updateOrder, addOrder, updatePosition, addPosition, removePosition, addTrade } = useTradingStore()

  useEffect(() => {
    const unsubscribers = [
      ws.on<OrderUpdatePayload>('order_update', (data) => {
        updateOrder(data as unknown as { _id: string; order_type: string; symbol: string; side: 'BUY' | 'SELL'; quantity: number; entry_price: number; exit_price?: number; pnl?: number; pnl_percent?: number; mode: 'paper' | 'live'; status: 'OPEN' | 'CLOSED' | 'CANCELLED'; entry_time: string })
      }),
      ws.on<OrderUpdatePayload>('order_created', (data) => {
        addOrder(data as unknown as { _id: string; order_type: string; symbol: string; side: 'BUY' | 'SELL'; quantity: number; entry_price: number; status: string; created_at: string })
      }),
      ws.on<PositionUpdatePayload>('position_update', (data) => {
        updatePosition(data as unknown as { _id: string; strategy_name: string; symbol: string; side: 'BUY' | 'SELL'; entry_price: number; quantity: number; current_price: number; unrealized_pnl: number; unrealized_pnl_percent: number; mode: 'paper' | 'live'; opened_at: string })
      }),
      ws.on<PositionUpdatePayload>('position_closed', (data) => {
        removePosition(data.position_id)
      }),
    ]

    return () => {
      unsubscribers.forEach(unsub => unsub())
    }
  }, [ws, updateOrder, addOrder, updatePosition, addPosition, removePosition, addTrade])
}

export function useNotificationEvents() {
  const ws = useWebSocket()
  const { addNotification } = useNotificationStore()

  useEffect(() => {
    const unsubscribe = ws.on<NotificationPayload>('notification', (data) => {
      addNotification({
        _id: data.notification_id,
        type: data.type,
        title: data.title,
        message: data.message,
        priority: data.priority,
        is_read: false,
        is_dismissed: false,
        created_at: data.timestamp,
      })
    })

    return unsubscribe
  }, [ws, addNotification])
}

export function useAISignalEvents() {
  const ws = useWebSocket()

  useEffect(() => {
    const unsubscribe = ws.on<AISignalPayload>('ai_signal', (data) => {
      console.log('[AI Signal] New signal received:', data)
    })

    return unsubscribe
  }, [ws])
}

export function useStrategyEvents() {
  const ws = useWebSocket()

  useEffect(() => {
    const unsubscribe = ws.on<StrategyUpdatePayload>('strategy_update', (data) => {
      console.log('[Strategy Update]', data)
    })

    return unsubscribe
  }, [ws])
}

export function usePnLEvents() {
  const ws = useWebSocket()
  const { positions } = useTradingStore()

  useEffect(() => {
    const unsubscribe = ws.on<PnLUpdatePayload>('pnl_update', (data) => {
      console.log('[PnL Update]', data)
    })

    return unsubscribe
  }, [ws, positions])
}

export function useMarketSubscription() {
  const ws = useWebSocket()

  const subscribe = useCallback((symbols: string[]) => {
    ws.subscribeMarket(symbols)
  }, [ws])

  const unsubscribe = useCallback((symbols: string[]) => {
    ws.unsubscribeMarket(symbols)
  }, [ws])

  return { subscribe, unsubscribe }
}

export function useConnectionStatus() {
  const ws = useWebSocket()

  return ws.getStatus()
}