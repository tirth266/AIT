import { useEffect, useCallback, useMemo, useRef, useState } from 'react'
import { useTradingStore, useMarketStore, useNotificationStore } from '../store'
import { wsManager } from '../websocket/websocket.manager'
import type { MarketTickPayload, OrderUpdatePayload, PositionUpdatePayload, PnLUpdatePayload, NotificationPayload } from '../websocket/websocket.types'

export function useWebSocket() {
  const updatePrice = useMarketStore((state) => state.updatePrice)
  const addNotification = useNotificationStore((state) => state.addNotification)
  const [isConnected, setIsConnected] = useState(false)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const cleanupRef = useRef<(() => void) | null>(null)
  const hasConnectedRef = useRef(false)

  const priorityMap = useMemo(() => ({
    'LOW': 'low', 'MEDIUM': 'medium', 'HIGH': 'high', 'CRITICAL': 'critical'
  }), [])

  useEffect(() => {
    if (cleanupRef.current) return
    if (hasConnectedRef.current) return

    hasConnectedRef.current = true
    console.log('[WebSocket] Initializing...')

    wsManager.connect()

    const unsubConnect = wsManager.on('connected', () => {
      console.log('[WebSocket] Transport connected')
      setIsConnected(true)
    })

    const unsubDisconnect = wsManager.on('disconnected', () => {
      console.log('[WebSocket] Transport disconnected')
      setIsConnected(false)
      setIsAuthenticated(false)
      hasConnectedRef.current = false
    })

    const unsubAuthSuccess = wsManager.on('auth_success', (data: { user_id: string }) => {
      console.log('[WebSocket] Authenticated:', data.user_id)
      setIsAuthenticated(true)
      wsManager.subscribeUser(['orders', 'positions', 'pnl'])
    })

    const unsubAuthError = wsManager.on('auth_error', (data: { message: string }) => {
      console.error('[WebSocket] Auth error:', data.message)
      setIsAuthenticated(false)
    })

    const unsubTick = wsManager.on<MarketTickPayload>('market_tick', (data) => {
      if (data?.symbol) {
        updatePrice(data.symbol, data.last_price ?? 0, data.change ?? 0, data.change_percent ?? 0)
      }
    })

    const unsubOrder = wsManager.on<OrderUpdatePayload>('order_update', (data) => {
      if (data?.order_id) {
        useTradingStore.getState()?.updateOrder?.(data as never)
      }
    })

    const unsubPosition = wsManager.on<PositionUpdatePayload>('position_update', (data) => {
      if (data?.position_id) {
        useTradingStore.getState()?.updatePosition?.(data as never)
      }
    })

    const unsubNotification = wsManager.on<NotificationPayload>('notification', (data) => {
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
    })

    cleanupRef.current = () => {
      unsubConnect()
      unsubDisconnect()
      unsubAuthSuccess()
      unsubAuthError()
      unsubTick()
      unsubOrder()
      unsubPosition()
      unsubNotification()
    }

    return () => {
      if (cleanupRef.current) {
        cleanupRef.current()
        cleanupRef.current = null
      }
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
    isConnected: (isConnected || wsManager.isConnected()) && isAuthenticated,
    getStatus: wsManager.getStatus,
    isAuthenticated,
  }
}

export default useWebSocket