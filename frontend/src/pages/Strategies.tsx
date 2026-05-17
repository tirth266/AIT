import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Plus,
  Search,
  Filter,
  Edit,
  Copy,
  Trash2,
  Play,
  Pause,
  MoreVertical,
  Brain,
} from 'lucide-react'
import { clsx } from 'clsx'
import { useTradingStore } from '../store'
import { Card, Button, Input, Badge, StatusBadge, Select, Modal } from '../components/ui'
import { mockStrategies } from '../services/mockData'

export function StrategiesPage() {
  const navigate = useNavigate()
  const { strategies, setStrategies } = useTradingStore()
  const [searchQuery, setSearchQuery] = useState('')
  const [filterMode, setFilterMode] = useState('all')
  const [deleteModal, setDeleteModal] = useState<string | null>(null)

  const displayStrategies = strategies.length > 0 ? strategies : mockStrategies

  const filteredStrategies = displayStrategies.filter((s) => {
    const matchesSearch = s.strategy_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.symbol.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesMode = filterMode === 'all' || s.mode === filterMode
    return matchesSearch && matchesMode
  })

  const handleDelete = (id: string) => {
    setStrategies(displayStrategies.filter((s) => s._id !== id))
    setDeleteModal(null)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text">Strategies</h1>
          <p className="text-textMuted">Create and manage your trading strategies</p>
        </div>
        <Button onClick={() => navigate('/strategies/new')}>
          <Plus className="w-4 h-4 mr-2" />
          New Strategy
        </Button>
      </div>

      <Card>
        <div className="flex flex-col md:flex-row gap-4 mb-6">
          <div className="flex-1">
            <Input
              placeholder="Search strategies..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              icon={<Search className="w-4 h-4" />}
            />
          </div>
          <Select
            value={filterMode}
            onChange={(e) => setFilterMode(e.target.value)}
            options={[
              { value: 'all', label: 'All Modes' },
              { value: 'paper', label: 'Paper Trading' },
              { value: 'live', label: 'Live Trading' },
            ]}
          />
        </div>

        <div className="space-y-4">
          {filteredStrategies.map((strategy, index) => (
            <motion.div
              key={strategy._id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
              className="p-4 bg-background rounded-lg border border-border hover:border-primary/30 transition-all"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-4">
                  <div className="p-3 bg-primary/10 rounded-lg">
                    <Brain className="w-5 h-5 text-primary" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-text">{strategy.strategy_name}</h3>
                    <p className="text-sm text-textMuted mt-1">
                      {strategy.symbol} • {strategy.timeframe} • {strategy.broker}
                    </p>
                    <div className="flex items-center gap-2 mt-2">
                      <Badge variant={strategy.mode === 'paper' ? 'primary' : 'success'} size="sm">
                        {strategy.mode}
                      </Badge>
                      <StatusBadge status={strategy.is_active ? 'running' : 'stopped'} />
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {strategy.total_trades !== undefined && (
                    <div className="text-right mr-4">
                      <p className="text-sm text-textMuted">{strategy.total_trades} trades</p>
                      <p className={clsx(
                        'text-sm font-medium',
                        (strategy.total_pnl || 0) >= 0 ? 'text-success' : 'text-danger'
                      )}>
                        {(strategy.total_pnl || 0) >= 0 ? '+' : ''}${strategy.total_pnl?.toFixed(2) || '0.00'}
                      </p>
                    </div>
                  )}
                  <Button variant="ghost" size="sm" onClick={() => navigate(`/strategies/${strategy._id}`)}>
                    <Edit className="w-4 h-4" />
                  </Button>
                  <Button variant="ghost" size="sm">
                    <Copy className="w-4 h-4" />
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => setDeleteModal(strategy._id)}>
                    <Trash2 className="w-4 h-4 text-danger" />
                  </Button>
                </div>
              </div>
            </motion.div>
          ))}
        </div>

        {filteredStrategies.length === 0 && (
          <div className="text-center py-12">
            <p className="text-textMuted">No strategies found</p>
            <Button className="mt-4" onClick={() => navigate('/strategies/new')}>
              Create your first strategy
            </Button>
          </div>
        )}
      </Card>

      <Modal
        isOpen={!!deleteModal}
        onClose={() => setDeleteModal(null)}
        title="Delete Strategy"
        size="sm"
      >
        <p className="text-textMuted mb-6">Are you sure you want to delete this strategy? This action cannot be undone.</p>
        <div className="flex justify-end gap-3">
          <Button variant="ghost" onClick={() => setDeleteModal(null)}>Cancel</Button>
          <Button variant="danger" onClick={() => deleteModal && handleDelete(deleteModal)}>Delete</Button>
        </div>
      </Modal>
    </div>
  )
}