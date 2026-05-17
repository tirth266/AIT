import { useEffect, useCallback } from 'react'
import { wsManager } from '../websocket/websocket.manager'
import { useTradingEngineStore } from '../store'
import type { Order, Position, PnLData, MarketQuote } from '../types'

export function useTradingWebSocket() {
  const store = useTradingEngineStore()
  
  useEffect(() => {
    const unsubscribers = [
      wsManager.on<Order>('order_created', (data) => {
        store.updateOrderFromWS(data)
      }),
      wsManager.on<Order>('order_update', (data) => {
        store.updateOrderFromWS(data)
      }),
      wsManager.on<Order>('order_filled', (data) => {
        store.updateOrderFromWS(data)
      }),
      wsManager.on<Order>('order_cancelled', (data) => {
        store.updateOrderFromWS(data)
      }),
      wsManager.on<Order>('order_rejected', (data) => {
        store.updateOrderFromWS(data)
      }),
      wsManager.on<Position>('position_update', (data) => {
        store.updatePositionFromWS(data)
      }),
      wsManager.on<PnLData>('pnl_update', (data) => {
        store.updatePnLFromWS(data)
      }),
      wsManager.on<MarketQuote>('quote', (data) => {
        store.updateQuoteFromWS(data)
      }),
    ]
    
    return () => {
      unsubscribers.forEach(unsub => unsub())
    }
  }, [store])
  
  const placeOrder = useCallback((orderData: {
    symbol: string
    transaction_type: 'BUY' | 'SELL'
    order_type?: 'MARKET' | 'LIMIT' | 'SL' | 'SL-M'
    quantity: number
    price?: number
    trigger_price?: number
    product_type?: 'MIS' | 'CNC' | 'NRML'
  }) => {
    wsManager.emit('place_order', orderData)
  }, [])
  
  const cancelOrder = useCallback((orderId: string) => {
    wsManager.emit('cancel_order', { order_id: orderId })
  }, [])
  
  const exitPosition = useCallback((positionId: string, exitPrice?: number, quantity?: number) => {
    wsManager.emit('exit_position_ws', {
      position_id: positionId,
      exit_price: exitPrice,
      quantity
    })
  }, [])
  
  const fetchQuote = useCallback((symbol: string) => {
    wsManager.emit('get_quote', { symbol })
  }, [])
  
  const fetchQuotes = useCallback((symbols?: string[]) => {
    wsManager.emit('get_quotes', { symbols })
  }, [])
  
  return {
    isConnected: wsManager.isConnected(),
    subscribe: () => wsManager.subscribeUser(['orders', 'positions', 'pnl']),
    unsubscribe: () => {},
    placeOrder,
    cancelOrder,
    exitPosition,
    fetchQuote,
    fetchQuotes,
  }
}

export default useTradingWebSocket