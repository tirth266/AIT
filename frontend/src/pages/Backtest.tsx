import { useState } from 'react'
import { motion } from 'framer-motion'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts'
import {
  Play,
  Clock,
  TrendingUp,
  TrendingDown,
  Target,
  BarChart3,
  Download,
  RefreshCw,
} from 'lucide-react'
import { clsx } from 'clsx'
import { Card, CardHeader, CardTitle, Button, Select, Input, Badge, Loader } from '../components/ui'
import { mockStrategies, mockBacktestResults } from '../services/mockData'

export function BacktestPage() {
  const [formData, setFormData] = useState({
    strategy_id: '',
    symbol: 'BTC/USDT',
    timeframe: '1h',
    start_date: '2023-01-01',
    end_date: '2023-12-31',
    initial_capital: 10000,
  })
  const [isRunning, setIsRunning] = useState(false)
  const [progress, setProgress] = useState(0)
  const [results, setResults] = useState<typeof mockBacktestResults | null>(null)

  const handleRunBacktest = () => {
    if (!formData.strategy_id) return

    setIsRunning(true)
    setProgress(0)
    setResults(null)

    const interval = setInterval(() => {
      setProgress(p => {
        if (p >= 100) {
          clearInterval(interval)
          setIsRunning(false)
          setResults(mockBacktestResults)
          return 100
        }
        return p + 10
      })
    }, 300)
  }

  const pastBacktests = [
    { _id: 'bt_001', strategy_name: 'RSI Momentum', symbol: 'BTC/USDT', timeframe: '1h', total_return: 25.0, win_rate: 60.0, status: 'completed', created_at: '2024-01-15T10:00:00Z' },
    { _id: 'bt_002', strategy_name: 'EMA Crossover', symbol: 'ETH/USDT', timeframe: '15m', total_return: 15.0, win_rate: 55.0, status: 'completed', created_at: '2024-01-14T10:00:00Z' },
    { _id: 'bt_003', strategy_name: 'RSI Momentum', symbol: 'BTC/USDT', timeframe: '1h', total_return: 0, win_rate: 0, status: 'running', created_at: '2024-01-15T12:00:00Z' },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text">Backtest</h1>
          <p className="text-textMuted">Test your strategies on historical data</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <Card>
            <CardHeader>
              <CardTitle>Run New Backtest</CardTitle>
            </CardHeader>
            <div className="space-y-4">
              <Select
                label="Strategy"
                value={formData.strategy_id}
                onChange={(e) => setFormData({ ...formData, strategy_id: e.target.value })}
                options={[
                  { value: '', label: 'Select Strategy' },
                  ...mockStrategies.map(s => ({ value: s._id, label: s.strategy_name }))
                ]}
              />
              <Select
                label="Symbol"
                value={formData.symbol}
                onChange={(e) => setFormData({ ...formData, symbol: e.target.value })}
                options={[
                  { value: 'BTC/USDT', label: 'BTC/USDT' },
                  { value: 'ETH/USDT', label: 'ETH/USDT' },
                  { value: 'SOL/USDT', label: 'SOL/USDT' },
                ]}
              />
              <Select
                label="Timeframe"
                value={formData.timeframe}
                onChange={(e) => setFormData({ ...formData, timeframe: e.target.value })}
                options={[
                  { value: '1m', label: '1 Minute' },
                  { value: '5m', label: '5 Minutes' },
                  { value: '15m', label: '15 Minutes' },
                  { value: '1h', label: '1 Hour' },
                  { value: '4h', label: '4 Hours' },
                ]}
              />
              <div className="grid grid-cols-2 gap-4">
                <Input
                  label="Start Date"
                  type="date"
                  value={formData.start_date}
                  onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
                />
                <Input
                  label="End Date"
                  type="date"
                  value={formData.end_date}
                  onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
                />
              </div>
              <Input
                label="Initial Capital ($)"
                type="number"
                value={formData.initial_capital}
                onChange={(e) => setFormData({ ...formData, initial_capital: Number(e.target.value) })}
              />
              <Button
                className="w-full"
                onClick={handleRunBacktest}
                isLoading={isRunning}
                disabled={!formData.strategy_id}
              >
                <Play className="w-4 h-4 mr-2" />
                Run Backtest
              </Button>
            </div>
          </Card>

          {isRunning && (
            <Card className="mt-4">
              <div className="text-center py-4">
                <Loader text="Running backtest..." />
                <div className="mt-4">
                  <div className="h-2 bg-surfaceHover rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary transition-all duration-300"
                      style={{ width: `${progress}%` }}
                    />
                  </div>
                  <p className="text-sm text-textMuted mt-2">{progress}% complete</p>
                </div>
              </div>
            </Card>
          )}
        </div>

        <div className="lg:col-span-2 space-y-6">
          {results && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                  <CardTitle>Results</CardTitle>
                  <Button variant="outline" size="sm">
                    <Download className="w-4 h-4 mr-2" />
                    Export
                  </Button>
                </CardHeader>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                  <div className="p-4 bg-background rounded-lg">
                    <p className="text-sm text-textMuted">Total Return</p>
                    <p className={clsx(
                      'text-2xl font-bold',
                      results.total_return >= 0 ? 'text-success' : 'text-danger'
                    )}>
                      {results.total_return >= 0 ? '+' : ''}{results.total_return.toFixed(1)}%
                    </p>
                  </div>
                  <div className="p-4 bg-background rounded-lg">
                    <p className="text-sm text-textMuted">Win Rate</p>
                    <p className="text-2xl font-bold text-text">{results.win_rate.toFixed(1)}%</p>
                  </div>
                  <div className="p-4 bg-background rounded-lg">
                    <p className="text-sm text-textMuted">Sharpe Ratio</p>
                    <p className="text-2xl font-bold text-text">{results.sharpe_ratio.toFixed(2)}</p>
                  </div>
                  <div className="p-4 bg-background rounded-lg">
                    <p className="text-sm text-textMuted">Max Drawdown</p>
                    <p className="text-2xl font-bold text-danger">-{results.max_drawdown.toFixed(1)}%</p>
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <p className="text-sm text-textMuted">Total Trades</p>
                      <p className="text-lg font-semibold text-text">{results.total_trades}</p>
                    </div>
                    <div>
                      <p className="text-sm text-textMuted">Winning Trades</p>
                      <p className="text-lg font-semibold text-success">{results.winning_trades}</p>
                    </div>
                    <div>
                      <p className="text-sm text-textMuted">Losing Trades</p>
                      <p className="text-lg font-semibold text-danger">{results.losing_trades}</p>
                    </div>
                  </div>

                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={results.equity_curve}>
                        <defs>
                          <linearGradient id="colorEquity" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#2563EB" stopOpacity={0.3} />
                            <stop offset="95%" stopColor="#2563EB" stopOpacity={0} />
                          </linearGradient>
                        </defs>
                        <XAxis dataKey="date" stroke="#9CA3AF" fontSize={12} />
                        <YAxis stroke="#9CA3AF" fontSize={12} tickFormatter={(v) => `$${v}`} />
                        <Tooltip
                          contentStyle={{ backgroundColor: '#111827', border: '1px solid #374151', borderRadius: '8px' }}
                          formatter={(value: number) => [`$${value.toFixed(2)}`, 'Equity']}
                        />
                        <Area type="monotone" dataKey="value" stroke="#2563EB" fillOpacity={1} fill="url(#colorEquity)" />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </Card>
            </motion.div>
          )}

          <Card>
            <CardHeader>
              <CardTitle>Past Backtests</CardTitle>
            </CardHeader>
            <div className="space-y-3">
              {pastBacktests.map((bt) => (
                <div
                  key={bt._id}
                  className="flex items-center justify-between p-4 bg-background rounded-lg hover:bg-surfaceHover/50 cursor-pointer transition-colors"
                >
                  <div>
                    <p className="font-medium text-text">{bt.strategy_name}</p>
                    <p className="text-sm text-textMuted">{bt.symbol} • {bt.timeframe}</p>
                    <p className="text-xs text-textMuted mt-1">
                      {new Date(bt.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <div className="text-right">
                    {bt.status === 'completed' ? (
                      <>
                        <p className={clsx(
                          'font-semibold',
                          bt.total_return >= 0 ? 'text-success' : 'text-danger'
                        )}>
                          {bt.total_return >= 0 ? '+' : ''}{bt.total_return.toFixed(1)}%
                        </p>
                        <p className="text-sm text-textMuted">Win: {bt.win_rate.toFixed(0)}%</p>
                      </>
                    ) : (
                      <div className="flex items-center gap-2">
                        <RefreshCw className="w-4 h-4 text-primary animate-spin" />
                        <span className="text-textMuted">Running</span>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}