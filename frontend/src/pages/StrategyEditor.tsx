import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Save,
  Play,
  Plus,
  Trash2,
  ArrowLeft,
  AlertCircle,
  CheckCircle,
} from 'lucide-react'
import { clsx } from 'clsx'
import { useTradingStore, useUIStore } from '../store'
import { Card, CardHeader, CardTitle, Button, Input, Select, Badge } from '../components/ui'
import { mockStrategies } from '../services/mockData'

const indicators = [
  { name: 'RSI', params: [{ key: 'period', label: 'Period', default: 14 }] },
  { name: 'EMA', params: [{ key: 'period', label: 'Period', default: 9 }] },
  { name: 'SMA', params: [{ key: 'period', label: 'Period', default: 20 }] },
  { name: 'MACD', params: [
    { key: 'fast', label: 'Fast', default: 12 },
    { key: 'slow', label: 'Slow', default: 26 },
    { key: 'signal', label: 'Signal', default: 9 },
  ] },
  { name: 'Bollinger_Bands', params: [
    { key: 'period', label: 'Period', default: 20 },
    { key: 'std_dev', label: 'Std Dev', default: 2 },
  ] },
  { name: 'ATR', params: [{ key: 'period', label: 'Period', default: 14 }] },
  { name: 'VWAP', params: [] },
  { name: 'Supertrend', params: [
    { key: 'period', label: 'Period', default: 10 },
    { key: 'multiplier', label: 'Multiplier', default: 3 },
  ] },
]

const operators = [
  { value: 'greater_than', label: '>' },
  { value: 'less_than', label: '<' },
  { value: 'equals', label: '=' },
  { value: 'crosses_above', label: 'Crosses Above' },
  { value: 'crosses_below', label: 'Crosses Below' },
]

export function StrategyEditorPage() {
  const navigate = useNavigate()
  const { id } = useParams()
  const { strategies } = useTradingStore()
  const { addToast } = useUIStore()

  const existingStrategy = id ? (strategies.find(s => s._id === id) || mockStrategies.find(s => s._id === id)) : null

  const [formData, setFormData] = useState({
    strategy_name: existingStrategy?.strategy_name || '',
    symbol: existingStrategy?.symbol || 'BTC/USDT',
    timeframe: existingStrategy?.timeframe || '1h',
    mode: existingStrategy?.mode || 'paper' as 'paper' | 'live',
    broker: existingStrategy?.broker || 'binance',
    indicators: existingStrategy?.indicators || [],
    entry_conditions: existingStrategy?.entry_conditions || [],
    exit_conditions: existingStrategy?.exit_conditions || [],
    risk_settings: existingStrategy?.risk_settings || {
      stop_loss_percent: 1.0,
      take_profit_percent: 2.0,
      trailing_stop_enabled: false,
      trailing_stop_percent: 0.5,
      position_size_type: 'calculated',
      position_size_percent: 10,
    },
  })

  const [showTestResult, setShowTestResult] = useState(false)
  const [testResult, setTestResult] = useState<{
    signal: string
    indicators: Record<string, number>
    entrySignal: boolean
    exitSignal: boolean
  } | null>(null)

  const handleSave = () => {
    addToast({ type: 'success', title: 'Strategy saved', message: `${formData.strategy_name} has been saved` })
    navigate('/strategies')
  }

  const handleTest = () => {
    setTestResult({
      signal: 'BUY',
      indicators: { RSI_14: 28.5, EMA_9: 44900, EMA_21: 44850 },
      entrySignal: true,
      exitSignal: false,
    })
    setShowTestResult(true)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" onClick={() => navigate('/strategies')}>
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back
          </Button>
          <div>
            <h1 className="text-2xl font-bold text-text">
              {id ? 'Edit Strategy' : 'Create Strategy'}
            </h1>
            <p className="text-textMuted">Configure your trading strategy</p>
          </div>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" onClick={handleTest}>
            <Play className="w-4 h-4 mr-2" />
            Test
          </Button>
          <Button onClick={handleSave}>
            <Save className="w-4 h-4 mr-2" />
            Save
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Basic Information</CardTitle>
            </CardHeader>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Input
                label="Strategy Name"
                value={formData.strategy_name}
                onChange={(e) => setFormData({ ...formData, strategy_name: e.target.value })}
                placeholder="My Strategy"
              />
              <Select
                label="Symbol"
                value={formData.symbol}
                onChange={(e) => setFormData({ ...formData, symbol: e.target.value })}
                options={[
                  { value: 'BTC/USDT', label: 'BTC/USDT' },
                  { value: 'ETH/USDT', label: 'ETH/USDT' },
                  { value: 'SOL/USDT', label: 'SOL/USDT' },
                  { value: 'BNB/USDT', label: 'BNB/USDT' },
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
                  { value: '30m', label: '30 Minutes' },
                  { value: '1h', label: '1 Hour' },
                  { value: '4h', label: '4 Hours' },
                  { value: '1d', label: '1 Day' },
                ]}
              />
              <Select
                label="Mode"
                value={formData.mode}
                onChange={(e) => setFormData({ ...formData, mode: e.target.value as 'paper' | 'live' })}
                options={[
                  { value: 'paper', label: 'Paper Trading' },
                  { value: 'live', label: 'Live Trading' },
                ]}
              />
              <Select
                label="Broker"
                value={formData.broker}
                onChange={(e) => setFormData({ ...formData, broker: e.target.value })}
                options={[
                  { value: 'binance', label: 'Binance' },
                  { value: 'zerodha', label: 'Zerodha' },
                  { value: 'upstox', label: 'Upstox' },
                ]}
              />
            </div>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Indicators</CardTitle>
              <Button variant="ghost" size="sm">
                <Plus className="w-4 h-4 mr-1" />
                Add
              </Button>
            </CardHeader>
            <div className="space-y-3">
              {formData.indicators.length === 0 ? (
                <p className="text-center text-textMuted py-4">No indicators added</p>
              ) : (
                formData.indicators.map((indicator, index) => (
                  <div key={index} className="flex items-center gap-4 p-3 bg-background rounded-lg">
                    <Badge variant="primary">{indicator.name}</Badge>
                    <div className="flex-1">
                      {Object.entries(indicator.params).map(([key, value]) => (
                        <span key={key} className="text-sm text-textMuted mr-3">
                          {key}: {value}
                        </span>
                      ))}
                    </div>
                    <Button variant="ghost" size="sm">
                      <Trash2 className="w-4 h-4 text-danger" />
                    </Button>
                  </div>
                ))
              )}
            </div>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Entry Conditions</CardTitle>
            </CardHeader>
            <div className="space-y-3">
              {formData.entry_conditions.length === 0 ? (
                <p className="text-center text-textMuted py-4">No entry conditions defined</p>
              ) : (
                formData.entry_conditions.map((condition, index) => (
                  <div key={index} className="flex items-center gap-4 p-3 bg-background rounded-lg">
                    <Badge variant="success">{condition.indicator_name}</Badge>
                    <span className="text-textMuted">{condition.operator}</span>
                    <span className="text-text">{condition.value}</span>
                    <Badge variant="default">{condition.logic}</Badge>
                  </div>
                ))
              )}
              <Button variant="ghost" size="sm" className="w-full">
                <Plus className="w-4 h-4 mr-1" />
                Add Condition
              </Button>
            </div>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Exit Conditions</CardTitle>
            </CardHeader>
            <div className="space-y-3">
              {formData.exit_conditions.length === 0 ? (
                <p className="text-center text-textMuted py-4">No exit conditions defined</p>
              ) : (
                formData.exit_conditions.map((condition, index) => (
                  <div key={index} className="flex items-center gap-4 p-3 bg-background rounded-lg">
                    <Badge variant="danger">{condition.indicator_name}</Badge>
                    <span className="text-textMuted">{condition.operator}</span>
                    <span className="text-text">{condition.value}</span>
                    <Badge variant="default">{condition.logic}</Badge>
                  </div>
                ))
              )}
              <Button variant="ghost" size="sm" className="w-full">
                <Plus className="w-4 h-4 mr-1" />
                Add Condition
              </Button>
            </div>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Risk Settings</CardTitle>
            </CardHeader>
            <div className="space-y-4">
              <Input
                label="Stop Loss (%)"
                type="number"
                value={formData.risk_settings.stop_loss_percent}
                onChange={(e) => setFormData({
                  ...formData,
                  risk_settings: { ...formData.risk_settings, stop_loss_percent: Number(e.target.value) }
                })}
              />
              <Input
                label="Take Profit (%)"
                type="number"
                value={formData.risk_settings.take_profit_percent}
                onChange={(e) => setFormData({
                  ...formData,
                  risk_settings: { ...formData.risk_settings, take_profit_percent: Number(e.target.value) }
                })}
              />
              <Select
                label="Position Size Type"
                value={formData.risk_settings.position_size_type}
                onChange={(e) => setFormData({
                  ...formData,
                  risk_settings: { ...formData.risk_settings, position_size_type: e.target.value as 'fixed' | 'calculated' }
                })}
                options={[
                  { value: 'calculated', label: 'Calculated (Risk-based)' },
                  { value: 'fixed', label: 'Fixed Amount' },
                ]}
              />
              {formData.risk_settings.position_size_type === 'calculated' && (
                <Input
                  label="Position Size (%)"
                  type="number"
                  value={formData.risk_settings.position_size_percent}
                  onChange={(e) => setFormData({
                    ...formData,
                    risk_settings: { ...formData.risk_settings, position_size_percent: Number(e.target.value) }
                  })}
                />
              )}
            </div>
          </Card>

          {showTestResult && testResult && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <Card className="border-primary/30">
                <CardHeader>
                  <CardTitle>Test Results</CardTitle>
                </CardHeader>
                <div className="space-y-4">
                  <div className={clsx(
                    'p-4 rounded-lg text-center',
                    testResult.signal === 'BUY' ? 'bg-success/10' : testResult.signal === 'SELL' ? 'bg-danger/10' : 'bg-surfaceHover'
                  )}>
                    <p className="text-2xl font-bold">{testResult.signal}</p>
                    <p className="text-textMuted">Signal</p>
                  </div>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-textMuted flex items-center gap-2">
                        <CheckCircle className="w-4 h-4 text-success" /> Entry Signal
                      </span>
                      <Badge variant={testResult.entrySignal ? 'success' : 'danger'}>
                        {testResult.entrySignal ? 'Active' : 'Inactive'}
                      </Badge>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-textMuted flex items-center gap-2">
                        <AlertCircle className="w-4 h-4 text-warning" /> Exit Signal
                      </span>
                      <Badge variant={testResult.exitSignal ? 'danger' : 'success'}>
                        {testResult.exitSignal ? 'Active' : 'Inactive'}
                      </Badge>
                    </div>
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm font-medium text-textMuted">Indicators</p>
                    {Object.entries(testResult.indicators).map(([key, value]) => (
                      <div key={key} className="flex justify-between text-sm">
                        <span className="text-textMuted">{key}</span>
                        <span className="text-text">{typeof value === 'number' ? value.toFixed(2) : value}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </Card>
            </motion.div>
          )}
        </div>
      </div>
    </div>
  )
}