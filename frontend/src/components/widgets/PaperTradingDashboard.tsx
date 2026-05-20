import React, { useEffect, useState, useMemo } from 'react'
import { motion } from 'framer-motion'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import {
  Wallet,
  TrendingUp,
  TrendingDown,
  RefreshCw,
  History,
  AlertCircle,
  RotateCcw,
} from 'lucide-react'
import { clsx } from 'clsx'
import { useShallow } from 'zustand/react/shallow'
import { Card, CardHeader, CardTitle, Button, Badge, Loader, Modal } from '../../components/ui'
import { useEngineStore } from '../../store'

interface PaperTradingDashboardProps {
  compact?: boolean
}

export function PaperTradingDashboard({ compact = false }: PaperTradingDashboardProps) {
  const {
    paperPortfolio,
    paperTrades,
    paperPerformance,
    isLoading,
  } = useEngineStore(useShallow(state => ({
    paperPortfolio: state.paperPortfolio,
    paperTrades: state.paperTrades,
    paperPerformance: state.paperPerformance,
    isLoading: state.isLoading,
  })))

  const fetchPaperPortfolio = useEngineStore(state => state.fetchPaperPortfolio)
  const fetchPaperTrades = useEngineStore(state => state.fetchPaperTrades)
  const fetchPaperPerformance = useEngineStore(state => state.fetchPaperPerformance)
  const resetPaperPortfolio = useEngineStore(state => state.resetPaperPortfolio)

  const [showResetModal, setShowResetModal] = useState(false)

  useEffect(() => {
    fetchPaperPortfolio()
    fetchPaperTrades('all', 20)
    fetchPaperPerformance(30)
  }, [fetchPaperPortfolio, fetchPaperTrades, fetchPaperPerformance])

  const handleReset = async () => {
    await resetPaperPortfolio()
    setShowResetModal(false)
    fetchPaperPortfolio()
    fetchPaperTrades('all', 20)
  }

  const equityCurve = useMemo(() => paperPerformance ? [
    { day: 1, value: paperPortfolio?.initial_capital || 100000 },
    { day: 7, value: (paperPortfolio?.cash || 100000) * (1 + (paperPerformance.return_percent || 0) / 100 * 0.25) },
    { day: 14, value: (paperPortfolio?.cash || 100000) * (1 + (paperPerformance.return_percent || 0) / 100 * 0.5) },
    { day: 21, value: (paperPortfolio?.cash || 100000) * (1 + (paperPerformance.return_percent || 0) / 100 * 0.75) },
    { day: 30, value: paperPortfolio?.cash || 100000 },
  ] : [], [paperPerformance, paperPortfolio])

  if (isLoading && !paperPortfolio) {
    return (
      <Card className="p-6">
        <Loader text="Loading paper trading..." />
      </Card>
    )
  }

  return (
    <div className="space-y-4">
      <Card>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary/10 rounded-lg">
              <Wallet className="w-5 h-5 text-primary" />
            </div>
            <div>
              <h3 className="font-semibold text-text">Paper Trading</h3>
              <p className="text-sm text-textMuted">Virtual trading environment</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" onClick={() => {
              fetchPaperPortfolio()
              fetchPaperTrades('all', 20)
              fetchPaperPerformance(30)
            }}>
              <RefreshCw className="w-4 h-4" />
            </Button>
            <Button variant="ghost" size="sm" onClick={() => setShowResetModal(true)}>
              <RotateCcw className="w-4 h-4" />
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
          <div className="p-3 bg-background rounded-lg">
            <p className="text-xs text-textMuted">Current Capital</p>
            <p className="text-xl font-bold text-text">${(paperPortfolio?.cash || 0).toFixed(2)}</p>
          </div>
          <div className="p-3 bg-background rounded-lg">
            <p className="text-xs text-textMuted">Initial Capital</p>
            <p className="text-xl font-bold text-text">${(paperPortfolio?.initial_capital || 100000).toFixed(2)}</p>
          </div>
          <div className="p-3 bg-background rounded-lg">
            <p className="text-xs text-textMuted">Total P&L</p>
            <p className={clsx(
              'text-xl font-bold',
              (paperPerformance?.total_pnl || 0) >= 0 ? 'text-success' : 'text-danger'
            )}>
              {(paperPerformance?.total_pnl || 0) >= 0 ? '+' : ''}${((paperPerformance?.total_pnl || 0)).toFixed(2)}
            </p>
          </div>
          <div className="p-3 bg-background rounded-lg">
            <p className="text-xs text-textMuted">Return</p>
            <p className={clsx(
              'text-xl font-bold',
              (paperPerformance?.return_percent || 0) >= 0 ? 'text-success' : 'text-danger'
            )}>
              {(paperPerformance?.return_percent || 0) >= 0 ? '+' : ''}{(paperPerformance?.return_percent || 0).toFixed(2)}%
            </p>
          </div>
        </div>
      </Card>

      {!compact && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle>Performance</CardTitle>
              </CardHeader>
              <div className="space-y-3">
                <div className="grid grid-cols-3 gap-2">
                  <div className="p-2 bg-background rounded">
                    <p className="text-xs text-textMuted">Trades</p>
                    <p className="font-semibold text-text">{paperPerformance?.total_trades || 0}</p>
                  </div>
                  <div className="p-2 bg-background rounded">
                    <p className="text-xs text-textMuted">Wins</p>
                    <p className="font-semibold text-success">{paperPerformance?.winning_trades || 0}</p>
                  </div>
                  <div className="p-2 bg-background rounded">
                    <p className="text-xs text-textMuted">Losses</p>
                    <p className="font-semibold text-danger">{paperPerformance?.losing_trades || 0}</p>
                  </div>
                </div>
                <div className="flex items-center justify-between p-3 bg-background rounded-lg">
                  <div>
                    <p className="text-sm text-textMuted">Win Rate</p>
                    <p className="text-lg font-bold text-text">{(paperPerformance?.win_rate || 0).toFixed(1)}%</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-textMuted">Avg P&L</p>
                    <p className={clsx(
                      'text-lg font-bold',
                      (paperPerformance?.avg_pnl || 0) >= 0 ? 'text-success' : 'text-danger'
                    )}>
                      ${(paperPerformance?.avg_pnl || 0).toFixed(2)}
                    </p>
                  </div>
                </div>
              </div>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Equity Curve</CardTitle>
              </CardHeader>
              <div className="h-32">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={equityCurve}>
                    <XAxis dataKey="day" stroke="#6B7280" fontSize={10} />
                    <YAxis stroke="#6B7280" fontSize={10} tickFormatter={(v) => `$${v / 1000}k`} />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#111827', border: '1px solid #374151', borderRadius: '8px' }}
                      formatter={(value: number) => [`$${value.toFixed(2)}`, 'Equity']}
                    />
                    <Line type="monotone" dataKey="value" stroke="#2563EB" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Recent Trades</CardTitle>
            </CardHeader>
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {paperTrades.length > 0 ? (
                paperTrades.slice(0, 10).map((trade) => (
                  <motion.div
                    key={trade.trade_id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex items-center justify-between p-3 bg-background rounded-lg"
                  >
                    <div className="flex items-center gap-3">
                      {trade.side === 'BUY' ? (
                        <TrendingUp className="w-4 h-4 text-success" />
                      ) : (
                        <TrendingDown className="w-4 h-4 text-danger" />
                      )}
                      <div>
                        <p className="font-medium text-text">{trade.symbol}</p>
                        <p className="text-xs text-textMuted">
                          {trade.quantity} @ ${trade.entry_price.toFixed(2)}
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <Badge variant={trade.status === 'open' ? 'warning' : trade.side === 'BUY' ? 'success' : 'danger'}>
                        {trade.status}
                      </Badge>
                      {trade.pnl !== undefined && (
                        <p className={clsx(
                          'text-sm font-medium mt-1',
                          trade.pnl >= 0 ? 'text-success' : 'text-danger'
                        )}>
                          {trade.pnl >= 0 ? '+' : ''}${trade.pnl.toFixed(2)}
                        </p>
                      )}
                    </div>
                  </motion.div>
                ))
              ) : (
                <div className="text-center py-8 text-textMuted">
                  <History className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p>No trades yet</p>
                </div>
              )}
            </div>
          </Card>
        </>
      )}

      <Modal
        isOpen={showResetModal}
        onClose={() => setShowResetModal(false)}
        title="Reset Paper Trading"
        size="sm"
      >
        <div className="space-y-4">
          <div className="flex items-start gap-3 p-3 bg-warning/10 rounded-lg">
            <AlertCircle className="w-5 h-5 text-warning flex-shrink-0 mt-0.5" />
            <p className="text-sm text-textMuted">
              This will reset your paper trading portfolio to the initial capital of $100,000 and delete all trade history. This action cannot be undone.
            </p>
          </div>
          <div className="flex justify-end gap-3">
            <Button variant="ghost" onClick={() => setShowResetModal(false)}>Cancel</Button>
            <Button variant="danger" onClick={handleReset}>Reset Portfolio</Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}

export default PaperTradingDashboard