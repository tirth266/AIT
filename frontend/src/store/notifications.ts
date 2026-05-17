import { create } from 'zustand'
import { notificationsApi } from '../services/api'

export interface Notification {
  _id: string
  type: string
  title: string
  message: string
  priority: 'low' | 'medium' | 'high' | 'critical'
  is_read: boolean
  is_dismissed: boolean
  metadata?: Record<string, unknown>
  action_url?: string
  created_at: string
  read_at?: string
}

interface NotificationState {
  notifications: Notification[]
  unreadCount: number
  isLoading: boolean
  error: string | null
  setNotifications: (notifications: Notification[]) => void
  addNotification: (notification: Notification) => void
  setUnreadCount: (count: number) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  fetchNotifications: (params?: { type?: string; is_read?: boolean; limit?: number }) => Promise<void>
  fetchUnreadCount: () => Promise<void>
  markAsRead: (id: string) => Promise<void>
  markAllAsRead: () => Promise<void>
  deleteNotification: (id: string) => Promise<void>
  clearNotifications: (clearType?: 'read' | 'all') => Promise<void>
}

export const useNotificationStore = create<NotificationState>((set, get) => ({
  notifications: [],
  unreadCount: 0,
  isLoading: false,
  error: null,

  setNotifications: (notifications) => set({ notifications }),

  addNotification: (notification) => set((state) => ({
    notifications: [notification, ...state.notifications],
    unreadCount: state.unreadCount + 1,
  })),

  setUnreadCount: (count) => set({ unreadCount: count }),

  setLoading: (isLoading) => set({ isLoading }),

  setError: (error) => set({ error }),

  fetchNotifications: async (params) => {
    set({ isLoading: true, error: null })
    try {
      const response = await notificationsApi.list(params)
      set({
        notifications: response.data.notifications || [],
        unreadCount: response.data.unread_count || 0,
        isLoading: false,
      })
    } catch (error) {
      set({ error: 'Failed to fetch notifications', isLoading: false })
      console.error('Failed to fetch notifications:', error)
    }
  },

  fetchUnreadCount: async () => {
    try {
      const response = await notificationsApi.unreadCount()
      set({ unreadCount: response.data.unread_count || 0 })
    } catch (error) {
      console.error('Failed to fetch unread count:', error)
    }
  },

  markAsRead: async (id: string) => {
    try {
      await notificationsApi.markRead(id)
      set((state) => ({
        notifications: state.notifications.map((n) =>
          n._id === id ? { ...n, is_read: true, read_at: new Date().toISOString() } : n
        ),
        unreadCount: Math.max(0, state.unreadCount - 1),
      }))
    } catch (error) {
      console.error('Failed to mark notification as read:', error)
    }
  },

  markAllAsRead: async () => {
    try {
      await notificationsApi.markAllRead()
      set((state) => ({
        notifications: state.notifications.map((n) => ({ ...n, is_read: true })),
        unreadCount: 0,
      }))
    } catch (error) {
      console.error('Failed to mark all as read:', error)
    }
  },

  deleteNotification: async (id: string) => {
    try {
      await notificationsApi.delete(id)
      set((state) => ({
        notifications: state.notifications.filter((n) => n._id !== id),
      }))
    } catch (error) {
      console.error('Failed to delete notification:', error)
    }
  },

  clearNotifications: async (clearType = 'read') => {
    try {
      await notificationsApi.clear(clearType)
      await get().fetchNotifications()
    } catch (error) {
      console.error('Failed to clear notifications:', error)
    }
  },
}))