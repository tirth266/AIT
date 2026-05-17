import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  RefreshCw,
  Download,
  Search,
  AlertCircle,
  Info,
  AlertTriangle,
  Bug,
} from 'lucide-react'
import { clsx } from 'clsx'
import { Card, CardHeader, CardTitle, Button, Input, Select, Badge } from '../components/ui'
import { mockLogs } from '../services/mockData'

const levelIcons = {
  INFO: Info,
  WARNING: AlertTriangle,
  ERROR: AlertCircle,
  DEBUG: Bug,
}

const levelColors = {
  INFO: 'text-primary',
  WARNING: 'text-warning',
  ERROR: 'text-danger',
  DEBUG: 'text-textMuted',
}

export function LogsPage() {
  const [filterLevel, setFilterLevel] = useState('all')
  const [filterCategory, setFilterCategory] = useState('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [autoRefresh, setAutoRefresh] = useState(false)

  const filteredLogs = mockLogs.filter(log => {
    const matchesLevel = filterLevel === 'all' || log.level === filterLevel
    const matchesCategory = filterCategory === 'all' || log.category === filterCategory
    const matchesSearch = log.message.toLowerCase().includes(searchQuery.toLowerCase())
    return matchesLevel && matchesCategory && matchesSearch
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text">Logs</h1>
          <p className="text-textMuted">View application logs and system events</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="autoRefresh"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="w-4 h-4 rounded border-border bg-background"
            />
            <label htmlFor="autoRefresh" className="text-sm text-textMuted">
              Auto-refresh
            </label>
          </div>
          <Button variant="outline">
            <Download className="w-4 h-4 mr-2" />
            Export
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div className="flex gap-3">
            <div className="w-64">
              <Input
                placeholder="Search logs..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                icon={<Search className="w-4 h-4" />}
              />
            </div>
            <Select
              value={filterLevel}
              onChange={(e) => setFilterLevel(e.target.value)}
              options={[
                { value: 'all', label: 'All Levels' },
                { value: 'INFO', label: 'INFO' },
                { value: 'WARNING', label: 'WARNING' },
                { value: 'ERROR', label: 'ERROR' },
              ]}
            />
            <Select
              value={filterCategory}
              onChange={(e) => setFilterCategory(e.target.value)}
              options={[
                { value: 'all', label: 'All Categories' },
                { value: 'TRADE', label: 'Trade' },
                { value: 'BROKER', label: 'Broker' },
                { value: 'SIGNAL', label: 'Signal' },
                { value: 'SYSTEM', label: 'System' },
              ]}
            />
          </div>
          <Button variant="ghost" size="sm">
            <RefreshCw className="w-4 h-4" />
          </Button>
        </CardHeader>

        <div className="space-y-2">
          {filteredLogs.map((log, index) => {
            const Icon = levelIcons[log.level as keyof typeof levelIcons] || Info

            return (
              <motion.div
                key={log._id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.02 }}
                className="flex items-start gap-4 p-4 bg-background rounded-lg hover:bg-surfaceHover/50 transition-colors"
              >
                <div className={clsx('p-2 rounded-lg', `bg-${log.level.toLowerCase()}/10`)}>
                  <Icon className={clsx('w-4 h-4', levelColors[log.level as keyof typeof levelColors])} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 mb-1">
                    <Badge variant={
                      log.level === 'ERROR' ? 'danger' :
                      log.level === 'WARNING' ? 'warning' :
                      log.level === 'INFO' ? 'primary' : 'default'
                    } size="sm">
                      {log.level}
                    </Badge>
                    <Badge variant="default" size="sm">{log.category}</Badge>
                    <span className="text-sm text-textMuted">
                      {new Date(log.created_at).toLocaleString()}
                    </span>
                  </div>
                  <p className="text-text">{log.message}</p>
                  {log.metadata && (
                    <div className="mt-2 text-xs text-textMuted font-mono bg-surface rounded p-2">
                      {JSON.stringify(log.metadata, null, 2)}
                    </div>
                  )}
                </div>
              </motion.div>
            )
          })}
        </div>

        {filteredLogs.length === 0 && (
          <div className="text-center py-12">
            <p className="text-textMuted">No logs found</p>
          </div>
        )}
      </Card>
    </div>
  )
}