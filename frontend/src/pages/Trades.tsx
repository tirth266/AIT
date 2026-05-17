import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  Download,
  Filter,
  TrendingUp,
  TrendingDown,
  Clock,
  X,
  ChevronLeft,
  ChevronRight,
  Eye,
} from 'lucide-react'
import { clsx } from 'clsx'
import { useTradingStore } from '../store'
import { Card, CardHeader, CardTitle, Button, Badge, Select, Input, Modal } from '../components/ui'
import { mockTrades } from '../services/mockData'

export function TradesPage() {
  const { trades } = useTradingStore()
  const [filterMode, setFilterMode] = useState('all')
  const [filterStatus, setFilterStatus] = useState('all')
  const [selectedTrade, setSelectedTrade] = useState<typeof mockTrades[0] | null>(null)
  const [currentPage, setCurrentPage] = useState(1)
  const itemsPerPage = 10

  const displayTrades = trades.length > 0 ? trades : mockTrades

  const filteredTrades = displayTrades.filter(t => {
    const matchesMode = filterMode === 'all' || t.mode === filterMode
    const matchesStatus = filterStatus === 'all' || t.status === filterStatus
    return matchesMode && matchesStatus
  })

  const totalPages = Math.ceil(filteredTrades.length / itemsPerPage)
  const paginatedTrades = filteredTrades.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  )

  const summary = {
    total: filteredTrades.length,
    wins: filteredTrades.filter(t => (t.pnl || 0) >= 0).length,
    losses: filteredTrades.filter(t => (t.pnl || 0) < 0).length,
    totalPnL: filteredTrades.reduce((sum, t) => sum + (t.pnl || 0), 0),
  }

  const winRate = summary.total > 0 ? (summary.wins / summary.total) * 100 : 0

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text">Trade History</h1>
          <p className="text-textMuted">View and manage your trading history</p>
        </div>
        <Button variant="outline">
          <Download className="w-4 h-4 mr-2" />
          Export CSV
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <p className="text-sm text-textMuted">Total Trades</p>
          <p className="text-2xl font-bold text-text">{summary.total}</p>
        </Card>
        <Card>
          <p className="text-sm text-textMuted">Win Rate</p>
          <p className="text-2xl font-bold text-text">{winRate.toFixed(1)}%</p>
        </Card>
        <Card>
          <p className="text-sm text-textMuted">Wins / Losses</p>
          <p className="text-2xl font-bold text-text">
            {summary.wins} / {summary.losses}
          </p>
        </Card>
        <Card>
          <p className="text-sm text-textMuted">Total P&L</p>
          <p className={clsx(
            'text-2xl font-bold',
            summary.totalPnL >= 0 ? 'text-success' : 'text-danger'
          )}>
            {summary.totalPnL >= 0 ? '+' : ''}${summary.totalPnL.toFixed(2)}
          </p>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Trades</CardTitle>
          <div className="flex gap-3">
            <Select
              value={filterMode}
              onChange={(e) => setFilterMode(e.target.value)}
              options={[
                { value: 'all', label: 'All Modes' },
                { value: 'paper', label: 'Paper' },
                { value: 'live', label: 'Live' },
              ]}
            />
            <Select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              options={[
                { value: 'all', label: 'All Status' },
                { value: 'OPEN', label: 'Open' },
                { value: 'CLOSED', label: 'Closed' },
              ]}
            />
          </div>
        </CardHeader>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left py-3 px-4 text-sm font-medium text-textMuted">Time</th>
                <th className="text-left py-3 px-4 text-sm font-medium text-textMuted">Symbol</th>
                <th className="text-left py-3 px-4 text-sm font-medium text-textMuted">Side</th>
                <th className="text-right py-3 px-4 text-sm font-medium text-textMuted">Qty</th>
                <th className="text-right py-3 px-4 text-sm font-medium text-textMuted">Entry</th>
                <th className="text-right py-3 px-4 text-sm font-medium text-textMuted">Exit</th>
                <th className="text-right py-3 px-4 text-sm font-medium text-textMuted">P&L</th>
                <th className="text-center py-3 px-4 text-sm font-medium text-textMuted">Mode</th>
                <th className="text-center py-3 px-4 text-sm font-medium text-textMuted">Actions</th>
              </tr>
            </thead>
            <tbody>
              {paginatedTrades.map((trade, index) => {
                const isPositive = (trade.pnl || 0) >= 0

                return (
                  <motion.tr
                    key={trade._id}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: index * 0.02 }}
                    className="border-b border-border hover:bg-surfaceHover/50"
                  >
                    <td className="py-4 px-4">
                      <div>
                        <p className="text-sm text-text">
                          {new Date(trade.entry_time).toLocaleDateString()}
                        </p>
                        <p className="text-xs text-textMuted">
                          {new Date(trade.entry_time).toLocaleTimeString()}
                        </p>
                      </div>
                    </td>
                    <td className="py-4 px-4">
                      <span className="font-medium text-text">{trade.symbol}</span>
                    </td>
                    <td className="py-4 px-4">
                      <Badge variant={trade.side === 'BUY' ? 'success' : 'danger'}>
                        <span className="flex items-center gap-1">
                          {trade.side === 'BUY' ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                          {trade.side}
                        </span>
                      </Badge>
                    </td>
                    <td className="py-4 px-4 text-right text-text">
                      {trade.quantity}
                    </td>
                    <td className="py-4 px-4 text-right text-text">
                      ${trade.entry_price.toLocaleString()}
                    </td>
                    <td className="py-4 px-4 text-right text-text">
                      {trade.exit_price ? `$${trade.exit_price.toLocaleString()}` : '-'}
                    </td>
                    <td className="py-4 px-4 text-right">
                      <span className={clsx(
                        'font-medium',
                        isPositive ? 'text-success' : 'text-danger'
                      )}>
                        {isPositive ? '+' : ''}{trade.pnl?.toFixed(2) || '0.00'}
                      </span>
                    </td>
                    <td className="py-4 px-4 text-center">
                      <Badge variant={trade.mode === 'paper' ? 'primary' : 'success'} size="sm">
                        {trade.mode}
                      </Badge>
                    </td>
                    <td className="py-4 px-4 text-center">
                      <Button variant="ghost" size="sm" onClick={() => setSelectedTrade(trade)}>
                        <Eye className="w-4 h-4" />
                      </Button>
                    </td>
                  </motion.tr>
                )
              })}
            </tbody>
          </table>
        </div>

        {filteredTrades.length > itemsPerPage && (
          <div className="flex items-center justify-between mt-4 pt-4 border-t border-border">
            <p className="text-sm text-textMuted">
              Showing {(currentPage - 1) * itemsPerPage + 1} to {Math.min(currentPage * itemsPerPage, filteredTrades.length)} of {filteredTrades.length}
            </p>
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                disabled={currentPage === 1}
              >
                <ChevronLeft className="w-4 h-4" />
              </Button>
              <span className="text-sm text-text">
                Page {currentPage} of {totalPages}
              </span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
              >
                <ChevronRight className="w-4 h-4" />
              </Button>
            </div>
          </div>
        )}
      </Card>

      <Modal
        isOpen={!!selectedTrade}
        onClose={() => setSelectedTrade(null)}
        title="Trade Details"
        size="md"
      >
        {selectedTrade && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-textMuted">Strategy</p>
                <p className="text-text font-medium">{selectedTrade.strategy_name}</p>
              </div>
              <div>
                <p className="text-sm text-textMuted">Status</p>
                <Badge variant={selectedTrade.status === 'CLOSED' ? 'default' : 'primary'}>
                  {selectedTrade.status}
                </Badge>
              </div>
              <div>
                <p className="text-sm text-textMuted">Symbol</p>
                <p className="text-text font-medium">{selectedTrade.symbol}</p>
              </div>
              <div>
                <p className="text-sm text-textMuted">Mode</p>
                <Badge variant={selectedTrade.mode === 'paper' ? 'primary' : 'success'}>
                  {selectedTrade.mode}
                </Badge>
              </div>
            </div>

            <div className="p-4 bg-background rounded-lg space-y-3">
              <div className="flex justify-between">
                <span className="text-textMuted">Side</span>
                <Badge variant={selectedTrade.side === 'BUY' ? 'success' : 'danger'}>
                  {selectedTrade.side}
                </Badge>
              </div>
              <div className="flex justify-between">
                <span className="text-textMuted">Quantity</span>
                <span className="text-text">{selectedTrade.quantity}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-textMuted">Entry Price</span>
                <span className="text-text">${selectedTrade.entry_price.toLocaleString()}</span>
              </div>
              {selectedTrade.exit_price && (
                <div className="flex justify-between">
                  <span className="text-textMuted">Exit Price</span>
                  <span className="text-text">${selectedTrade.exit_price.toLocaleString()}</span>
                </div>
              )}
              {selectedTrade.pnl && (
                <div className="flex justify-between pt-3 border-t border-border">
                  <span className="text-textMuted">P&L</span>
                  <span className={clsx(
                    'font-bold',
                    selectedTrade.pnl >= 0 ? 'text-success' : 'text-danger'
                  )}>
                    {selectedTrade.pnl >= 0 ? '+' : ''}${selectedTrade.pnl.toFixed(2)} ({selectedTrade.pnl_percent?.toFixed(2)}%)
                  </span>
                </div>
              )}
            </div>

            {selectedTrade.exit_reason && (
              <div>
                <p className="text-sm text-textMuted">Exit Reason</p>
                <p className="text-text capitalize">{selectedTrade.exit_reason.replace('_', ' ')}</p>
              </div>
            )}

            {selectedTrade.duration_minutes && (
              <div>
                <p className="text-sm text-textMuted">Duration</p>
                <p className="text-text">{Math.floor(selectedTrade.duration_minutes / 60)}h {selectedTrade.duration_minutes % 60}m</p>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  )
}