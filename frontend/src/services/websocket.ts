import { wsManager } from '../websocket/websocket.manager'

const emit = (event: string, data?: unknown) => {
  if (wsManager.isConnected()) {
    wsManager.emit(event, data)
  }
}

export const socketService = {
  connect: (token?: string) => wsManager.connect(token),
  disconnect: () => wsManager.disconnect(),
  authenticate: (token: string) => wsManager.authenticate(token),
  subscribeMarket: (symbols: string[]) => wsManager.subscribeMarket(symbols),
  unsubscribeMarket: (symbols: string[]) => wsManager.unsubscribeMarket(symbols),
  subscribeWatchlist: (watchlistId: string) => wsManager.subscribeWatchlist(watchlistId),
  subscribeUser: (channels?: string[]) => wsManager.subscribeUser(channels),
  placeOrder: (order: unknown) => wsManager.placeOrder(order as Parameters<typeof wsManager.placeOrder>[0]),
  cancelOrder: (orderId: string) => wsManager.cancelOrder(orderId),
  startStrategy: (strategyId: string) => wsManager.startStrategy(strategyId),
  stopStrategy: (strategyId: string) => wsManager.stopStrategy(strategyId),
  getSubscribedSymbols: () => wsManager.getSubscribedSymbols(),
  getConnectionStatus: () => wsManager.getStatus(),
  isConnected: () => wsManager.isConnected(),
  emit,
  on: <T = unknown>(event: string, handler: (data: T) => void) => wsManager.on(event, handler),
  off: (event: string, handler: unknown) => wsManager.off(event, handler as never),
}

export const wsService = socketService

export default socketService