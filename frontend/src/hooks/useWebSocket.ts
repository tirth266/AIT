import { useEffect, useCallback, useMemo } from 'react'
import { useAuthStore, useTradingStore, useMarketStore, useNotificationStore } from '../store'
import { wsManager } from '../websocket/websocket.manager'
import type { MarketTickPayload, OrderUpdatePayload, PositionUpdatePayload, PnLUpdatePayload, NotificationPayload, AISignalPayload } from '../websocket/websocket.types'

export function useWebSocket() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  const token = useAuthStore((state) => state.accessToken)
  const updatePrice = useMarketStore((state) => state.updatePrice)
  const addNotification = useNotificationStore((state) => state.addNotification)
  const positions = useTradingStore((state) => state.positions)

  const priorityMap = useMemo(() => ({
    'LOW': 'low', 'MEDIUM': 'medium', 'HIGH': 'high', 'CRITICAL': 'critical'
  }), [])

  useEffect(() => {
    if (isAuthenticated && token) {
      console.log('[WebSocket] Connecting...')
      wsManager.connect(token)
      wsManager.subscribeUser(['orders', 'positions', 'pnl'])
    }

    return () => {
      if (!isAuthenticated) {
        wsManager.disconnect()
      }
    }
  }, [isAuthenticated, token])

  useEffect(() => {
    const unsubscribers = [
      wsManager.on<MarketTickPayload>('market_tick', (data) => {
        if (data?.symbol) {
          updatePrice(data.symbol, data.last_price ?? 0, data.change ?? 0, data.change_percent ?? 0)
        }
      }),
      wsManager.on<OrderUpdatePayload>('order_update', (data) => {
        if (data?.order_id) {
          useTradingStore.getState()?.updateOrder?.(data as never)
        }
      }),
      wsManager.on<PositionUpdatePayload>('position_update', (data) => {
        if (data?.position_id) {
          useTradingStore.getState()?.updatePosition?.(data as never)
        }
      }),
      wsManager.on<NotificationPayload>('notification', (data) => {
        if (data?.notification_id) {
          addNotification({
            _id: data.notification_id,
            type: data.type ?? 'info',
            title: data.title ?? 'Notification',
            message: data.message ?? '',
            priority: priorityMap[data.priority ?? 'MEDIUM'] ?? 'medium',
            is_read: false,
            is_dismissed: false,
            created_at: data.timestamp ?? new Date().toISOString(),
          })
        }
      }),
    ]

    return () => {
      unsubscribers.forEach(unsub => {
        if (typeof unsub === 'function') {
          unsub()
        }
      })
    }
  }, [updatePrice, addNotification, priorityMap])

  const subscribeMarket = useCallback((symbols: string[]) => {
    if (Array.isArray(symbols) && symbols.length > 0) {
      wsManager.subscribeMarket(symbols)
    }
  }, [])

  const unsubscribeMarket = useCallback((symbols: string[]) => {
    if (Array.isArray(symbols) && symbols.length > 0) {
      wsManager.unsubscribeMarket(symbols)
    }
  }, [])

  return {
    subscribeMarket,
    unsubscribeMarket,
    isConnected: wsManager.isConnected(),
    getStatus: wsManager.getStatus,
  }
}

export default useWebSocket