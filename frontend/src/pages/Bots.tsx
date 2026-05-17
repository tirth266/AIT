import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  Play,
  Square,
  RefreshCw,
  Clock,
  TrendingUp,
  TrendingDown,
  Activity,
  AlertTriangle,
} from 'lucide-react'
import { clsx } from 'clsx'
import { useTradingStore, useAuthStore } from '../store'
import { Card, CardHeader, CardTitle, Button, Badge, StatusBadge, Select } from '../components/ui'
import { mockBots, mockStrategies } from '../services/mockData'

export function BotsPage() {
  const { mode } = useAuthStore()
  const { bots, setBots, strategies } = useTradingStore()
  const [isLoading, setIsLoading] = useState<string | null>(null)

  const displayBots = bots.length > 0 ? bots : mockBots
  const displayStrategies = strategies.length > 0 ? strategies : mockStrategies

  const handleStartBot = (strategyId: string) => {
    setIsLoading(strategyId)
    setTimeout(() => {
      setBots(displayBots.map(b => 
        b.strategy_id === strategyId 
          ? { ...b, status: 'running' as const, last_signal_time: new Date().toISOString() }
          : b
      ))
      setIsLoading(null)
    }, 1000)
  }

  const handleStopBot = (strategyId: string) => {
    setIsLoading(strategyId)
    setTimeout(() => {
      setBots(displayBots.map(b => 
        b.strategy_id === strategyId 
          ? { ...b, status: 'stopped' as const }
          : b
      ))
      setIsLoading(null)
    }, 1000)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text">Trading Bots</h1>
          <p className="text-textMuted">Manage and monitor your automated trading bots</p>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex bg-background rounded-lg p-1 border border-border">
            <button
              onClick={() => {}}
              className={clsx(
                'px-3 py-1.5 text-sm font-medium rounded-md transition-all',
                mode === 'paper'
                  ? 'bg-success/20 text-success'
                  : 'text-textMuted hover:text-text'
              )}
            >
              Paper
            </button>
            <button
              onClick={() => {}}
              className={clsx(
                'px-3 py-1.5 text-sm font-medium rounded-md transition-all',
                mode === 'live'
                  ? 'bg-primary/20 text-primary'
                  : 'text-textMuted hover:text-text'
              )}
            >
              Live
            </button>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <div className="flex items-center gap-3">
            <div className="p-3 bg-success/10 rounded-lg">
              <Activity className="w-5 h-5 text-success" />
            </div>
            <div>
              <p className="text-2xl font-bold text-text">
                {displayBots.filter(b => b.status === 'running').length}
              </p>
              <p className="text-sm text-textMuted">Running</p>
            </div>
          </div>
        </Card>
        <Card>
          <div className="flex items-center gap-3">
            <div className="p-3 bg-danger/10 rounded-lg">
              <Square className="w-5 h-5 text-danger" />
            </div>
            <div>
              <p className="text-2xl font-bold text-text">
                {displayBots.filter(b => b.status === 'stopped').length}
              </p>
              <p className="text-sm text-textMuted">Stopped</p>
            </div>
          </div>
        </Card>
        <Card>
          <div className="flex items-center gap-3">
            <div className="p-3 bg-primary/10 rounded-lg">
              <TrendingUp className="w-5 h-5 text-primary" />
            </div>
            <div>
              <p className="text-2xl font-bold text-text">
                ${displayBots.reduce((sum, b) => sum + b.pnl_today, 0).toFixed(2)}
              </p>
              <p className="text-sm text-textMuted">Today's P&L</p>
            </div>
          </div>
        </Card>
        <Card>
          <div className="flex items-center gap-3">
            <div className="p-3 bg-warning/10 rounded-lg">
              <Clock className="w-5 h-5 text-warning" />
            </div>
            <div>
              <p className="text-2xl font-bold text-text">
                {displayBots.reduce((sum, b) => sum + b.trades_today, 0)}
              </p>
              <p className="text-sm text-textMuted">Today's Trades</p>
            </div>
          </div>
        </Card>
      </div>

      <div className="space-y-4">
        {displayStrategies.map((strategy, index) => {
          const bot = displayBots.find(b => b.strategy_id === strategy._id)
          const isRunning = bot?.status === 'running'

          return (
            <motion.div
              key={strategy._id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
            >
              <Card className={clsx(isRunning && 'border-success/30')}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className={clsx(
                      'w-12 h-12 rounded-lg flex items-center justify-center',
                      isRunning ? 'bg-success/10' : 'bg-surfaceHover'
                    )}>
                      <RefreshCw className={clsx(
                        'w-6 h-6',
                        isRunning ? 'text-success animate-spin' : 'text-textMuted'
                      )} />
                    </div>
                    <div>
                      <h3 className="font-semibold text-text">{strategy.strategy_name}</h3>
                      <p className="text-sm text-textMuted">
                        {strategy.symbol} • {strategy.timeframe} • {strategy.broker}
                      </p>
                      <div className="flex items-center gap-2 mt-2">
                        <Badge variant={strategy.mode === 'paper' ? 'primary' : 'success'} size="sm">
                          {strategy.mode}
                        </Badge>
                        <StatusBadge status={bot?.status || 'stopped'} />
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-8">
                    {isRunning && bot && (
                      <div className="text-right">
                        <p className="text-sm text-textMuted">Today's P&L</p>
                        <p className={clsx(
                          'text-lg font-semibold',
                          bot.pnl_today >= 0 ? 'text-success' : 'text-danger'
                        )}>
                          {bot.pnl_today >= 0 ? '+' : ''}${bot.pnl_today.toFixed(2)}
                        </p>
                        <p className="text-sm text-textMuted">{bot.trades_today} trades</p>
                      </div>
                    )}

                    {isRunning && (
                      <div className="text-right">
                        <p className="text-sm text-textMuted">Last Signal</p>
                        {bot?.last_signal ? (
                          <Badge variant={bot.last_signal === 'BUY' ? 'success' : 'danger'}>
                            {bot.last_signal}
                          </Badge>
                        ) : (
                          <span className="text-textMuted">-</span>
                        )}
                        {bot?.last_signal_time && (
                          <p className="text-xs text-textMuted mt-1">
                            {new Date(bot.last_signal_time).toLocaleTimeString()}
                          </p>
                        )}
                      </div>
                    )}

                    {isRunning ? (
                      <Button
                        variant="danger"
                        onClick={() => handleStopBot(strategy._id)}
                        isLoading={isLoading === strategy._id}
                      >
                        <Square className="w-4 h-4 mr-2" />
                        Stop
                      </Button>
                    ) : (
                      <Button
                        variant="success"
                        onClick={() => handleStartBot(strategy._id)}
                        isLoading={isLoading === strategy._id}
                      >
                        <Play className="w-4 h-4 mr-2" />
                        Start
                      </Button>
                    )}
                  </div>
                </div>
              </Card>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}