import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  Bell,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Info,
  Trash2,
  Check,
  TrendingUp,
  TrendingDown,
  Bot,
  Settings,
} from 'lucide-react'
import { clsx } from 'clsx'
import { Card, CardHeader, CardTitle, Button, Badge, Select } from '../components/ui'
import { mockNotifications } from '../services/mockData'

const typeIcons = {
  trade_entry: TrendingUp,
  trade_exit: TrendingDown,
  signal: Bell,
  error: AlertTriangle,
  system: Settings,
}

const typeColors = {
  trade_entry: 'text-success',
  trade_exit: 'text-danger',
  signal: 'text-warning',
  error: 'text-danger',
  system: 'text-primary',
}

export function NotificationsPage() {
  const [filter, setFilter] = useState('all')
  const [notifications, setNotifications] = useState(mockNotifications)

  const filteredNotifications = notifications.filter(n => {
    if (filter === 'unread') return !n.read
    if (filter === 'read') return n.read
    return true
  })

  const unreadCount = notifications.filter(n => !n.read).length

  const handleMarkAllRead = () => {
    setNotifications(notifications.map(n => ({ ...n, read: true })))
  }

  const handleMarkRead = (id: string) => {
    setNotifications(notifications.map(n => 
      n._id === id ? { ...n, read: true } : n
    ))
  }

  const handleDelete = (id: string) => {
    setNotifications(notifications.filter(n => n._id !== id))
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text">Notifications</h1>
          <p className="text-textMuted">Stay updated on your trading activity</p>
        </div>
        <div className="flex items-center gap-3">
          {unreadCount > 0 && (
            <Button variant="outline" onClick={handleMarkAllRead}>
              <Check className="w-4 h-4 mr-2" />
              Mark all as read
            </Button>
          )}
          <Badge variant="primary">{unreadCount} unread</Badge>
        </div>
      </div>

      <div className="flex gap-3">
        <Select
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          options={[
            { value: 'all', label: 'All' },
            { value: 'unread', label: 'Unread' },
            { value: 'read', label: 'Read' },
          ]}
        />
      </div>

      <Card>
        <div className="space-y-2">
          {filteredNotifications.length === 0 ? (
            <div className="text-center py-12">
              <Bell className="w-12 h-12 text-textMuted mx-auto mb-4" />
              <p className="text-textMuted">No notifications</p>
            </div>
          ) : (
            filteredNotifications.map((notification, index) => {
              const Icon = typeIcons[notification.type as keyof typeof typeIcons] || Info
              const colorClass = typeColors[notification.type as keyof typeof typeColors] || 'text-textMuted'

              return (
                <motion.div
                  key={notification._id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.03 }}
                  className={clsx(
                    'flex items-start gap-4 p-4 rounded-lg transition-colors',
                    notification.read ? 'bg-background' : 'bg-primary/5 border border-primary/20'
                  )}
                >
                  <div className={clsx('p-2 rounded-lg bg-surfaceHover', colorClass)}>
                    <Icon className="w-5 h-5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <p className="font-medium text-text">{notification.title}</p>
                      {!notification.read && (
                        <span className="w-2 h-2 bg-primary rounded-full" />
                      )}
                    </div>
                    <p className="text-sm text-textMuted">{notification.message}</p>
                    <p className="text-xs text-textMuted mt-2">
                      {new Date(notification.created_at).toLocaleString()}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    {!notification.read && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleMarkRead(notification._id)}
                      >
                        <Check className="w-4 h-4" />
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDelete(notification._id)}
                    >
                      <Trash2 className="w-4 h-4 text-danger" />
                    </Button>
                  </div>
                </motion.div>
              )
            })
          )}
        </div>
      </Card>
    </div>
  )
}