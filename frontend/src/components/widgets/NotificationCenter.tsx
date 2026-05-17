/**
 * Notification Center
 * ==================
 * Real-time notification system with toasts.
 */

import React, { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Bell, Check, AlertCircle, Info, AlertTriangle, ShoppingCart, TrendingUp, Brain } from 'lucide-react'
import { clsx } from 'clsx'
import { useNotificationStore } from '../../store'
import { wsManager } from '../../websocket/websocket.manager'
import type { NotificationPayload } from '../../websocket/websocket.types'

interface ToastNotification {
  id: string
  type: 'success' | 'error' | 'warning' | 'info' | 'order' | 'signal'
  title: string
  message: string
  duration?: number
}

const TOAST_ICONS = {
  success: Check,
  error: AlertCircle,
  warning: AlertTriangle,
  info: Info,
  order: ShoppingCart,
  signal: Brain,
}

const TOAST_COLORS = {
  success: 'border-[#238636] bg-[#238636]/10',
  error: 'border-[#F85149] bg-[#F85149]/10',
  warning: 'border-[#F0883E] bg-[#F0883E]/10',
  info: 'border-[#58A6FF] bg-[#58A6FF]/10',
  order: 'border-[#238636] bg-[#238636]/10',
  signal: 'border-[#8B5CF6] bg-[#8B5CF6]/10',
}

interface ToastProps {
  toast: ToastNotification
  onDismiss: (id: string) => void
}

function Toast({ toast, onDismiss }: ToastProps) {
  const Icon = TOAST_ICONS[toast.type] || Info
  const colorClass = TOAST_COLORS[toast.type] || TOAST_COLORS.info

  useEffect(() => {
    if (toast.duration !== 0) {
      const timer = setTimeout(() => {
        onDismiss(toast.id)
      }, toast.duration || 5000)
      return () => clearTimeout(timer)
    }
  }, [toast.id, toast.duration, onDismiss])

  return (
    <motion.div
      initial={{ opacity: 0, x: 50, scale: 0.9 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, x: 50, scale: 0.9 }}
      className={clsx(
        'border rounded-lg p-4 shadow-lg backdrop-blur-lg max-w-sm',
        colorClass
      )}
    >
      <div className="flex items-start gap-3">
        <div className={clsx(
          'p-2 rounded-lg',
          toast.type === 'success' && 'bg-[#238636]/20 text-[#3FB950]',
          toast.type === 'error' && 'bg-[#F85149]/20 text-[#F85149]',
          toast.type === 'warning' && 'bg-[#F0883E]/20 text-[#F0883E]',
          toast.type === 'info' && 'bg-[#58A6FF]/20 text-[#58A6FF]',
          toast.type === 'order' && 'bg-[#238636]/20 text-[#3FB950]',
          toast.type === 'signal' && 'bg-[#8B5CF6]/20 text-[#8B5CF6]'
        )}>
          <Icon className="w-4 h-4" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="font-medium text-white text-sm">{toast.title}</p>
          <p className="text-xs text-[#8B949E] mt-0.5 truncate">{toast.message}</p>
        </div>
        <button
          onClick={() => onDismiss(toast.id)}
          className="p-1 hover:bg-[#21262D] rounded text-[#8B949E] hover:text-white transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </motion.div>
  )
}

interface ToastContainerProps {
  toasts: ToastNotification[]
  onDismiss: (id: string) => void
}

function ToastContainer({ toasts, onDismiss }: ToastContainerProps) {
  return (
    <div className="fixed top-4 right-4 z-50 space-y-2 max-h-screen overflow-y-auto">
      <AnimatePresence>
        {toasts.map((toast) => (
          <Toast key={toast.id} toast={toast} onDismiss={onDismiss} />
        ))}
      </AnimatePresence>
    </div>
  )
}

interface NotificationCenterProps {
  className?: string
}

export function NotificationCenter({ className }: NotificationCenterProps) {
  const [toasts, setToasts] = useState<ToastNotification[]>([])
  const { notifications, fetchNotifications, unreadCount, markAsRead, markAllAsRead } = useNotificationStore()

  useEffect(() => {
    fetchNotifications({ limit: 20 })
  }, [fetchNotifications])

  useEffect(() => {
    const unsubscribe = wsManager.on<NotificationPayload>('notification', (data) => {
      const toastType = getToastType(data.type)
      addToast({
        id: data.notification_id,
        type: toastType,
        title: data.title,
        message: data.message,
        duration: 5000,
      })
    })

    return unsubscribe
  }, [])

  const addToast = useCallback((toast: Omit<ToastNotification, 'id'>) => {
    const id = `toast_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    setToasts((prev) => [...prev, { ...toast, id }])
  }, [])

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const getToastType = (notificationType: string): ToastNotification['type'] => {
    const map: Record<string, ToastNotification['type']> = {
      'ORDER_FILLED': 'order',
      'ORDER_CANCELLED': 'warning',
      'ORDER_REJECTED': 'error',
      'POSITION_OPENED': 'order',
      'POSITION_CLOSED': 'success',
      'SIGNAL': 'signal',
      'ALERT': 'warning',
      'ERROR': 'error',
      'SYSTEM': 'info',
    }
    return map[notificationType] || 'info'
  }

  return (
    <>
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />

      <div className={clsx('bg-[#0D1117] rounded-xl border border-[#21262D] overflow-hidden', className)}>
        <div className="flex items-center justify-between px-4 py-3 border-b border-[#21262D]">
          <div className="flex items-center gap-2">
            <div className="p-1.5 bg-[#F0883E]/20 rounded-lg">
              <Bell className="w-4 h-4 text-[#F0883E]" />
            </div>
            <h3 className="font-semibold text-white">Notifications</h3>
            {unreadCount > 0 && (
              <span className="px-2 py-0.5 text-xs bg-[#F0883E]/20 text-[#F0883E] rounded-full">
                {unreadCount} unread
              </span>
            )}
          </div>
          {unreadCount > 0 && (
            <button
              onClick={() => markAllAsRead()}
              className="text-xs text-[#58A6FF] hover:underline"
            >
              Mark all read
            </button>
          )}
        </div>

        <div className="max-h-[400px] overflow-y-auto">
          {notifications.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 text-[#8B949E]">
              <Bell className="w-8 h-8 mb-2 opacity-50" />
              <p className="text-sm">No notifications</p>
            </div>
          ) : (
            notifications.map((notification) => (
              <div
                key={notification._id}
                className={clsx(
                  'flex items-start gap-3 p-4 border-b border-[#21262D]/50 hover:bg-[#21262D]/30 cursor-pointer transition-colors',
                  !notification.is_read && 'bg-[#F0883E]/5'
                )}
                onClick={() => !notification.is_read && markAsRead(notification._id)}
              >
                <div className={clsx(
                  'w-2 h-2 rounded-full mt-2',
                  notification.priority === 'critical' && 'bg-[#F85149]',
                  notification.priority === 'high' && 'bg-[#F0883E]',
                  notification.priority === 'medium' && 'bg-[#58A6FF]',
                  notification.priority === 'low' && 'bg-[#8B949E]'
                )} />
                <div className="flex-1 min-w-0">
                  <p className={clsx(
                    'text-sm',
                    !notification.is_read ? 'text-white font-medium' : 'text-[#8B949E]'
                  )}>
                    {notification.title}
                  </p>
                  <p className="text-xs text-[#8B949E] mt-0.5 line-clamp-2">{notification.message}</p>
                  <p className="text-xs text-[#8B949E]/60 mt-1">
                    {new Date(notification.created_at).toLocaleTimeString()}
                  </p>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      <NotificationToaster addToast={addToast} />
    </>
  )
}

export function NotificationToaster({ addToast }: { addToast: (toast: Omit<ToastNotification, 'id'>) => void }) {
  return null
}

export default NotificationCenter