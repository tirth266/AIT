import { create } from 'zustand'
import { ordersApi } from '../services/api'
import type { Order, CreateOrderRequest } from '../types'

interface OrdersState {
  orders: Order[]
  selectedOrder: Order | null
  isLoading: boolean
  isSubmitting: boolean
  error: string | null
  pagination: {
    page: number
    limit: number
    total: number
    pages: number
  }

  fetchOrders: (params?: { status?: string; product?: string; symbol?: string; page?: number; limit?: number }) => Promise<void>
  fetchOrder: (id: string) => Promise<void>
  createOrder: (order: CreateOrderRequest) => Promise<Order | null>
  cancelOrder: (id: string) => Promise<void>
  modifyOrder: (id: string, data: { price?: number; quantity?: number; trigger_price?: number }) => Promise<void>
  fetchHistory: (params?: { from_date?: string; to_date?: string; page?: number; limit?: number }) => Promise<void>
  updateOrderFromWS: (order: Order) => void
  setSelectedOrder: (order: Order | null) => void
  clearError: () => void
}

export const useOrdersStore = create<OrdersState>((set, get) => ({
  orders: [],
  selectedOrder: null,
  isLoading: false,
  isSubmitting: false,
  error: null,
  pagination: { page: 1, limit: 50, total: 0, pages: 0 },

  fetchOrders: async (params = {}) => {
    set({ isLoading: true, error: null })
    try {
      const response = await ordersApi.list(params)
      set({
        orders: response.data.data,
        pagination: response.data.pagination || { page: 1, limit: 50, total: 0, pages: 0 },
        isLoading: false,
      })
    } catch (error) {
      console.error('Failed to fetch orders:', error)
      set({ error: 'Failed to fetch orders', isLoading: false })
    }
  },

  fetchOrder: async (id) => {
    set({ isLoading: true })
    try {
      const response = await ordersApi.get(id)
      set({ selectedOrder: response.data.data, isLoading: false })
    } catch (error) {
      console.error('Failed to fetch order:', error)
      set({ error: 'Failed to fetch order details', isLoading: false })
    }
  },

  createOrder: async (orderData) => {
    set({ isSubmitting: true, error: null })
    try {
      const response = await ordersApi.create(orderData)
      const newOrder = response.data.data
      set((state) => ({
        orders: [newOrder, ...state.orders],
        isSubmitting: false,
      }))
      return newOrder
    } catch (error: unknown) {
      const err = error as { response?: { data?: { message?: string } } }
      const errorMessage = err.response?.data?.message || 'Failed to place order'
      console.error('Failed to create order:', error)
      set({ error: errorMessage, isSubmitting: false })
      return null
    }
  },

  cancelOrder: async (id) => {
    set({ isSubmitting: true })
    try {
      await ordersApi.cancel(id)
      set((state) => ({
        orders: state.orders.map((o) =>
          o.order_id === id ? { ...o, status: 'CANCELLED' as const } : o
        ),
        isSubmitting: false,
      }))
    } catch (error) {
      console.error('Failed to cancel order:', error)
      set({ error: 'Failed to cancel order', isSubmitting: false })
    }
  },

  modifyOrder: async (id, data) => {
    set({ isSubmitting: true })
    try {
      await ordersApi.modify(id, data)
      set((state) => ({
        orders: state.orders.map((o) =>
          o.order_id === id ? { ...o, ...data } : o
        ),
        isSubmitting: false,
      }))
    } catch (error) {
      console.error('Failed to modify order:', error)
      set({ error: 'Failed to modify order', isSubmitting: false })
    }
  },

  fetchHistory: async (params = {}) => {
    set({ isLoading: true })
    try {
      const response = await ordersApi.history(params)
      set({ orders: response.data.data, isLoading: false })
    } catch (error) {
      console.error('Failed to fetch order history:', error)
      set({ error: 'Failed to fetch order history', isLoading: false })
    }
  },

  updateOrderFromWS: (order) => {
    set((state) => ({
      orders: state.orders.map((o) => (o.order_id === order.order_id ? order : o)),
      selectedOrder: state.selectedOrder?.order_id === order.order_id ? order : state.selectedOrder,
    }))
  },

  setSelectedOrder: (order) => set({ selectedOrder: order }),

  clearError: () => set({ error: null }),
}))

export default useOrdersStore