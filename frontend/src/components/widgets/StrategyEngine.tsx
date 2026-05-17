import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import {
  Activity,
  Play,
  Pause,
  RefreshCw,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  Zap,
} from 'lucide-react'
import { clsx } from 'clsx'
import { Card, CardHeader, CardTitle, Button, Badge, Loader } from '../../components/ui'
import { useEngineStore, useStrategiesStore } from '../../store'
import type { EngineStatus, StrategySignal } from '../../types'

interface StrategyEngineProps {
  compact?: boolean
}

export function StrategyEngineDashboard({ compact = false }: StrategyEngineProps) {
  const {
    status,
    signals,
    riskSummary,
    fetchEngineStatus,
    fetchSignals,
    fetchRiskSummary,
    isLoading,
  } = useEngineStore()

  const { strategies, fetchStrategies } = useStrategiesStore()
  const [activeTab, setActiveTab] = useState<'signals' | 'strategies' | 'risk'>('signals')

  useEffect(() => {
    fetchEngineStatus()
    fetchSignals(20)
    fetchRiskSummary()
    fetchStrategies({ is_active: 'true' })

    const interval = setInterval(() => {
      fetchEngineStatus()
      fetchSignals(10)
    }, 10000)

    return () => clearInterval(interval)
  }, [])

  const getStatusColor = (status?: string) => {
    switch (status) {
      case 'running':
        return 'text-success'
      case 'error':
        return 'text-danger'
      default:
        return 'text-textMuted'
    }
  }

  if (isLoading && !status) {
    return (
      <Card className="p-6">
        <Loader text="Loading strategy engine..." />
      </Card>
    )
  }

  const metrics = status?.metrics

  return (
    <div className="space-y-4">
      <Card>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={clsx(
              'p-2 rounded-lg',
              status?.status === 'running' ? 'bg-success/10' : 'bg-surfaceHover'
            )}>
              <Activity className={clsx(
                'w-5 h-5',
                getStatusColor(status?.status)
              )} />
            </div>
            <div>
              <h3 className="font-semibold text-text">Strategy Engine</h3>
              <p className={clsx(
                'text-sm capitalize',
                getStatusColor(status?.status)
              )}>
                {status?.status || 'Stopped'}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" onClick={() => fetchEngineStatus()}>
              <RefreshCw className="w-4 h-4" />
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
          <div className="p-3 bg-background rounded-lg">
            <p className="text-xs text-textMuted">Active Strategies</p>
            <p className="text-xl font-bold text-text">{metrics?.active_strategies || 0}</p>
          </div>
          <div className="p-3 bg-background rounded-lg">
            <p className="text-xs text-textMuted">Signals Generated</p>
            <p className="text-xl font-bold text-text">{metrics?.signals_generated || 0}</p>
          </div>
          <div className="p-3 bg-background rounded-lg">
            <p className="text-xs text-textMuted">Executed</p>
            <p className="text-xl font-bold text-text">{metrics?.signals_executed || 0}</p>
          </div>
          <div className="p-3 bg-background rounded-lg">
            <p className="text-xs text-textMuted">Uptime</p>
            <p className="text-xl font-bold text-text">
              {metrics?.uptime_seconds
                ? `${Math.floor(metrics.uptime_seconds / 3600)}h`
                : '0h'}
            </p>
          </div>
        </div>
      </Card>

      {!compact && (
        <>
          <div className="flex gap-2">
            <Button
              variant={activeTab === 'signals' ? 'primary' : 'ghost'}
              size="sm"
              onClick={() => setActiveTab('signals')}
            >
              <Zap className="w-4 h-4 mr-1" />
              Signals
            </Button>
            <Button
              variant={activeTab === 'strategies' ? 'primary' : 'ghost'}
              size="sm"
              onClick={() => setActiveTab('strategies')}
            >
              <Activity className="w-4 h-4 mr-1" />
              Active
            </Button>
            <Button
              variant={activeTab === 'risk' ? 'primary' : 'ghost'}
              size="sm"
              onClick={() => setActiveTab('risk')}
            >
              <AlertTriangle className="w-4 h-4 mr-1" />
              Risk
            </Button>
          </div>

          {activeTab === 'signals' && (
            <Card>
              <CardHeader>
                <CardTitle>Recent Signals</CardTitle>
              </CardHeader>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {signals.length > 0 ? (
                  signals.slice(0, 10).map((signal) => (
                    <motion.div
                      key={signal.signal_id}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      className="flex items-center justify-between p-3 bg-background rounded-lg"
                    >
                      <div className="flex items-center gap-3">
                        {signal.action === 'BUY' ? (
                          <TrendingUp className="w-4 h-4 text-success" />
                        ) : signal.action === 'SELL' ? (
                          <TrendingDown className="w-4 h-4 text-danger" />
                        ) : (
                          <Activity className="w-4 h-4 text-textMuted" />
                        )}
                        <div>
                          <p className="font-medium text-text">{signal.symbol}</p>
                          <p className="text-xs text-textMuted">{signal.reasoning}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <Badge variant={signal.action === 'BUY' ? 'success' : signal.action === 'SELL' ? 'danger' : 'default'}>
                          {signal.action}
                        </Badge>
                        <p className="text-xs text-textMuted mt-1">
                          {Math.round(signal.confidence)}% confidence
                        </p>
                      </div>
                    </motion.div>
                  ))
                ) : (
                  <p className="text-center text-textMuted py-4">No signals generated yet</p>
                )}
              </div>
            </Card>
          )}

          {activeTab === 'strategies' && (
            <Card>
              <CardHeader>
                <CardTitle>Running Strategies</CardTitle>
              </CardHeader>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {strategies.filter(s => s.is_active).length > 0 ? (
                  strategies.filter(s => s.is_active).map((strategy) => (
                    <div
                      key={strategy._id}
                      className="flex items-center justify-between p-3 bg-background rounded-lg"
                    >
                      <div>
                        <p className="font-medium text-text">{strategy.strategy_name}</p>
                        <p className="text-xs text-textMuted">
                          {strategy.symbol} • {strategy.timeframe}
                        </p>
                      </div>
                      <Badge variant="success">Running</Badge>
                    </div>
                  ))
                ) : (
                  <p className="text-center text-textMuted py-4">No active strategies</p>
                )}
              </div>
            </Card>
          )}

          {activeTab === 'risk' && (
            <Card>
              <CardHeader>
                <CardTitle>Risk Summary</CardTitle>
              </CardHeader>
              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 bg-background rounded-lg">
                  <p className="text-sm text-textMuted">Daily P&L</p>
                  <p className={clsx(
                    'text-xl font-bold',
                    (riskSummary?.daily_pnl || 0) >= 0 ? 'text-success' : 'text-danger'
                  )}>
                    {(riskSummary?.daily_pnl || 0) >= 0 ? '+' : ''}
                    ${(riskSummary?.daily_pnl || 0).toFixed(2)}
                  </p>
                </div>
                <div className="p-4 bg-background rounded-lg">
                  <p className="text-sm text-textMuted">Open Positions</p>
                  <p className="text-xl font-bold text-text">
                    {riskSummary?.open_positions || 0}
                  </p>
                </div>
                <div className="p-4 bg-background rounded-lg">
                  <p className="text-sm text-textMuted">Trades Today</p>
                  <p className="text-xl font-bold text-text">
                    {riskSummary?.trades_today || 0}
                  </p>
                </div>
                <div className="p-4 bg-background rounded-lg">
                  <p className="text-sm text-textMuted">Risk Status</p>
                  <Badge variant={
                    riskSummary?.risk_status === 'danger' ? 'danger' :
                    riskSummary?.risk_status === 'warning' ? 'warning' : 'success'
                  }>
                    {riskSummary?.risk_status || 'Normal'}
                  </Badge>
                </div>
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  )
}

export default StrategyEngineDashboard