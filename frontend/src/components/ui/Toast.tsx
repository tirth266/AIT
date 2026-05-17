import { useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, CheckCircle, AlertCircle, AlertTriangle, Info } from 'lucide-react'
import { clsx } from 'clsx'
import { useUIStore, Toast as ToastType } from '../../store'

const icons = {
  success: CheckCircle,
  error: AlertCircle,
  warning: AlertTriangle,
  info: Info,
}

const colors = {
  success: 'border-success bg-success/10',
  error: 'border-danger bg-danger/10',
  warning: 'border-warning bg-warning/10',
  info: 'border-primary bg-primary/10',
}

const iconColors = {
  success: 'text-success',
  error: 'text-danger',
  warning: 'text-warning',
  info: 'text-primary',
}

function ToastItem({ toast, onClose }: { toast: ToastType; onClose: () => void }) {
  const Icon = icons[toast.type]

  useEffect(() => {
    const timer = setTimeout(onClose, toast.duration || 5000)
    return () => clearTimeout(timer)
  }, [toast.duration, onClose])

  return (
    <motion.div
      initial={{ opacity: 0, y: -20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -20, scale: 0.95 }}
      className={clsx(
        'flex items-start gap-3 p-4 rounded-lg border backdrop-blur-xl shadow-lg',
        colors[toast.type]
      )}
    >
      <Icon className={clsx('w-5 h-5 flex-shrink-0', iconColors[toast.type])} />
      <div className="flex-1 min-w-0">
        <p className="font-medium text-text">{toast.title}</p>
        {toast.message && (
          <p className="mt-1 text-sm text-textMuted">{toast.message}</p>
        )}
      </div>
      <button
        onClick={onClose}
        className="p-1 rounded hover:bg-surfaceHover text-textMuted hover:text-text transition-colors"
      >
        <X className="w-4 h-4" />
      </button>
    </motion.div>
  )
}

export function ToastContainer() {
  const { toasts, removeToast } = useUIStore()

  return (
    <div className="fixed top-4 right-4 z-[100] flex flex-col gap-2 w-full max-w-sm">
      <AnimatePresence>
        {toasts.map((toast) => (
          <ToastItem
            key={toast.id}
            toast={toast}
            onClose={() => removeToast(toast.id)}
          />
        ))}
      </AnimatePresence>
    </div>
  )
}

export function useToast() {
  const addToast = useUIStore((state) => state.addToast)

  return {
    success: (title: string, message?: string) =>
      addToast({ type: 'success', title, message }),
    error: (title: string, message?: string) =>
      addToast({ type: 'error', title, message }),
    warning: (title: string, message?: string) =>
      addToast({ type: 'warning', title, message }),
    info: (title: string, message?: string) =>
      addToast({ type: 'info', title, message }),
  }
}