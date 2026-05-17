import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  Brain,
  TrendingUp,
  BarChart2,
  Zap,
  Target,
  Settings,
  Save,
  Eye,
} from 'lucide-react'
import { clsx } from 'clsx'
import { Card, CardHeader, CardTitle, Button, Input, Select, Badge } from '../../components/ui'
import type { StrategyType, StrategyParameters } from '../../types'

interface StrategyBuilderProps {
  onSave?: (config: StrategyConfig) => void
  initialConfig?: Partial<StrategyConfig>
}

interface StrategyConfig {
  strategy_name: string
  strategy_type: StrategyType
  description: string
  symbol: string
  exchange: string
  timeframe: string
  mode: 'paper' | 'live'
  parameters: StrategyParameters
  risk_settings: {
    stop_loss_percent: number
    target_percent: number
    position_size_percent: number
    max_positions: number
    max_daily_loss: number
  }
}

const strategyTypes: { type: StrategyType; name: string; description: string; icon: React.ReactNode }[] = [
  { type: 'ema_crossover', name: 'EMA Crossover', description: 'Buy when fast EMA crosses above slow EMA', icon: <TrendingUp className="w-5 h-5" /> },
  { type: 'rsi_reversal', name: 'RSI Reversal', description: 'Buy when RSI exits oversold, sell on overbought', icon: <BarChart2 className="w-5 h-5" /> },
  { type: 'breakout', name: 'Breakout', description: 'Trade breakouts from resistance/support levels', icon: <Zap className="w-5 h-5" /> },
  { type: 'scalping', name: 'Scalping', description: 'Fast trades on small price movements', icon: <Target className="w-5 h-5" /> },
  { type: 'supertrend', name: 'Supertrend', description: 'Follow Supertrend indicator direction', icon: <Brain className="w-5 h-5" /> },
  { type: 'ai_strategy', name: 'AI Hybrid', description: 'Combine multiple indicators with weighted scoring', icon: <Brain className="w-5 h-5" /> },
]

const defaultParams: Record<StrategyType, StrategyParameters> = {
  ema_crossover: { fast_period: 9, slow_period: 21 },
  rsi_reversal: { period: 14, oversold: 30, overbought: 70 },
  breakout: { lookback: 20, confirm_bars: 2 },
  scalping: { fast_ema: 9, slow_ema: 21, rsi_period: 14 },
  supertrend: { period: 10, multiplier: 3.0 },
  ai_strategy: { use_ema: true, use_rsi: true, use_macd: true },
  custom: {},
}

const timeframes = [
  { value: '1m', label: '1 Minute' },
  { value: '5m', label: '5 Minutes' },
  { value: '15m', label: '15 Minutes' },
  { value: '30m', label: '30 Minutes' },
  { value: '1h', label: '1 Hour' },
  { value: '4h', label: '4 Hours' },
  { value: '1d', label: '1 Day' },
]

const symbols = [
  { value: 'RELIANCE', label: 'RELIANCE' },
  { value: 'TCS', label: 'TCS' },
  { value: 'INFY', label: 'INFY' },
  { value: 'HDFCBANK', label: 'HDFCBANK' },
  { value: 'ICICIBANK', label: 'ICICIBANK' },
  { value: 'SBIN', label: 'SBIN' },
  { value: 'BHARTIARTL', label: 'BHARTIARTL' },
  { value: 'KOTAKBANK', label: 'KOTAKBANK' },
  { value: 'LT', label: 'LT' },
  { value: 'HINDUNILVR', label: 'HINDUNILVR' },
]

export function StrategyBuilder({ onSave, initialConfig }: StrategyBuilderProps) {
  const [activeStep, setActiveStep] = useState<'type' | 'params' | 'risk' | 'review'>('type')
  const [config, setConfig] = useState<StrategyConfig>({
    strategy_name: initialConfig?.strategy_name || '',
    strategy_type: initialConfig?.strategy_type || 'ema_crossover',
    description: initialConfig?.description || '',
    symbol: initialConfig?.symbol || 'RELIANCE',
    exchange: initialConfig?.exchange || 'NSE',
    timeframe: initialConfig?.timeframe || '1m',
    mode: initialConfig?.mode || 'paper',
    parameters: initialConfig?.parameters || defaultParams.ema_crossover,
    risk_settings: initialConfig?.risk_settings || {
      stop_loss_percent: 1.0,
      target_percent: 2.0,
      position_size_percent: 10,
      max_positions: 5,
      max_daily_loss: 5000,
    },
  })

  const handleTypeSelect = (type: StrategyType) => {
    setConfig({
      ...config,
      strategy_type: type,
      parameters: defaultParams[type] || {},
    })
    setActiveStep('params')
  }

  const handleSave = () => {
    if (onSave) {
      onSave(config)
    }
  }

  const renderStepContent = () => {
    switch (activeStep) {
      case 'type':
        return (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {strategyTypes.map((st) => (
              <motion.button
                key={st.type}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => handleTypeSelect(st.type)}
                className={clsx(
                  'p-4 text-left rounded-lg border transition-all',
                  config.strategy_type === st.type
                    ? 'border-primary bg-primary/10'
                    : 'border-border bg-background hover:border-primary/50'
                )}
              >
                <div className="flex items-center gap-3 mb-2">
                  <div className={clsx(
                    'p-2 rounded-lg',
                    config.strategy_type === st.type ? 'bg-primary/20' : 'bg-surfaceHover'
                  )}>
                    {st.icon}
                  </div>
                  <div>
                    <h4 className="font-medium text-text">{st.name}</h4>
                  </div>
                </div>
                <p className="text-sm text-textMuted">{st.description}</p>
              </motion.button>
            ))}
          </div>
        )

      case 'params':
        return (
          <div className="space-y-6">
            <div className="grid grid-cols-2 gap-4">
              <Input
                label="Strategy Name"
                value={config.strategy_name}
                onChange={(e) => setConfig({ ...config, strategy_name: e.target.value })}
                placeholder="My Strategy"
              />
              <Select
                label="Symbol"
                value={config.symbol}
                onChange={(e) => setConfig({ ...config, symbol: e.target.value })}
                options={symbols}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <Select
                label="Timeframe"
                value={config.timeframe}
                onChange={(e) => setConfig({ ...config, timeframe: e.target.value })}
                options={timeframes}
              />
              <Select
                label="Mode"
                value={config.mode}
                onChange={(e) => setConfig({ ...config, mode: e.target.value as 'paper' | 'live' })}
                options={[
                  { value: 'paper', label: 'Paper Trading' },
                  { value: 'live', label: 'Live Trading' },
                ]}
              />
            </div>

            <Card className="bg-surfaceHover/50">
              <div className="flex items-center gap-2 mb-4">
                <Settings className="w-4 h-4 text-primary" />
                <h4 className="font-medium text-text">Strategy Parameters</h4>
              </div>

              {config.strategy_type === 'ema_crossover' && (
                <div className="grid grid-cols-2 gap-4">
                  <Input
                    label="Fast EMA Period"
                    type="number"
                    value={config.parameters.fast_period || 9}
                    onChange={(e) => setConfig({
                      ...config,
                      parameters: { ...config.parameters, fast_period: Number(e.target.value) }
                    })}
                  />
                  <Input
                    label="Slow EMA Period"
                    type="number"
                    value={config.parameters.slow_period || 21}
                    onChange={(e) => setConfig({
                      ...config,
                      parameters: { ...config.parameters, slow_period: Number(e.target.value) }
                    })}
                  />
                </div>
              )}

              {config.strategy_type === 'rsi_reversal' && (
                <div className="grid grid-cols-3 gap-4">
                  <Input
                    label="RSI Period"
                    type="number"
                    value={config.parameters.period || 14}
                    onChange={(e) => setConfig({
                      ...config,
                      parameters: { ...config.parameters, period: Number(e.target.value) }
                    })}
                  />
                  <Input
                    label="Oversold"
                    type="number"
                    value={config.parameters.oversold || 30}
                    onChange={(e) => setConfig({
                      ...config,
                      parameters: { ...config.parameters, oversold: Number(e.target.value) }
                    })}
                  />
                  <Input
                    label="Overbought"
                    type="number"
                    value={config.parameters.overbought || 70}
                    onChange={(e) => setConfig({
                      ...config,
                      parameters: { ...config.parameters, overbought: Number(e.target.value) }
                    })}
                  />
                </div>
              )}

              {config.strategy_type === 'breakout' && (
                <div className="grid grid-cols-2 gap-4">
                  <Input
                    label="Lookback Period"
                    type="number"
                    value={config.parameters.lookback || 20}
                    onChange={(e) => setConfig({
                      ...config,
                      parameters: { ...config.parameters, lookback: Number(e.target.value) }
                    })}
                  />
                  <Input
                    label="Confirm Bars"
                    type="number"
                    value={config.parameters.confirm_bars || 2}
                    onChange={(e) => setConfig({
                      ...config,
                      parameters: { ...config.parameters, confirm_bars: Number(e.target.value) }
                    })}
                  />
                </div>
              )}

              {config.strategy_type === 'supertrend' && (
                <div className="grid grid-cols-2 gap-4">
                  <Input
                    label="ATR Period"
                    type="number"
                    value={config.parameters.period || 10}
                    onChange={(e) => setConfig({
                      ...config,
                      parameters: { ...config.parameters, period: Number(e.target.value) }
                    })}
                  />
                  <Input
                    label="Multiplier"
                    type="number"
                    step="0.1"
                    value={config.parameters.multiplier || 3}
                    onChange={(e) => setConfig({
                      ...config,
                      parameters: { ...config.parameters, multiplier: Number(e.target.value) }
                    })}
                  />
                </div>
              )}
            </Card>
          </div>
        )

      case 'risk':
        return (
          <div className="space-y-6">
            <Card className="bg-surfaceHover/50">
              <div className="flex items-center gap-2 mb-4">
                <Target className="w-4 h-4 text-primary" />
                <h4 className="font-medium text-text">Risk Management</h4>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <Input
                  label="Stop Loss (%)"
                  type="number"
                  step="0.1"
                  value={config.risk_settings.stop_loss_percent}
                  onChange={(e) => setConfig({
                    ...config,
                    risk_settings: { ...config.risk_settings, stop_loss_percent: Number(e.target.value) }
                  })}
                />
                <Input
                  label="Target (%)"
                  type="number"
                  step="0.1"
                  value={config.risk_settings.target_percent}
                  onChange={(e) => setConfig({
                    ...config,
                    risk_settings: { ...config.risk_settings, target_percent: Number(e.target.value) }
                  })}
                />
                <Input
                  label="Position Size (%)"
                  type="number"
                  value={config.risk_settings.position_size_percent}
                  onChange={(e) => setConfig({
                    ...config,
                    risk_settings: { ...config.risk_settings, position_size_percent: Number(e.target.value) }
                  })}
                />
                <Input
                  label="Max Positions"
                  type="number"
                  value={config.risk_settings.max_positions}
                  onChange={(e) => setConfig({
                    ...config,
                    risk_settings: { ...config.risk_settings, max_positions: Number(e.target.value) }
                  })}
                />
                <Input
                  label="Max Daily Loss ($)"
                  type="number"
                  value={config.risk_settings.max_daily_loss}
                  onChange={(e) => setConfig({
                    ...config,
                    risk_settings: { ...config.risk_settings, max_daily_loss: Number(e.target.value) }
                  })}
                  className="col-span-2"
                />
              </div>
            </Card>
          </div>
        )

      case 'review':
        return (
          <div className="space-y-4">
            <div className="p-4 bg-background rounded-lg">
              <h4 className="font-medium text-text mb-2">{config.strategy_name || 'Unnamed Strategy'}</h4>
              <p className="text-sm text-textMuted">{config.description}</p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="p-3 bg-background rounded-lg">
                <p className="text-xs text-textMuted">Type</p>
                <Badge variant="primary">{config.strategy_type}</Badge>
              </div>
              <div className="p-3 bg-background rounded-lg">
                <p className="text-xs text-textMuted">Mode</p>
                <Badge variant={config.mode === 'paper' ? 'default' : 'success'}>
                  {config.mode}
                </Badge>
              </div>
              <div className="p-3 bg-background rounded-lg">
                <p className="text-xs text-textMuted">Symbol</p>
                <p className="font-medium text-text">{config.symbol}</p>
              </div>
              <div className="p-3 bg-background rounded-lg">
                <p className="text-xs text-textMuted">Timeframe</p>
                <p className="font-medium text-text">{config.timeframe}</p>
              </div>
            </div>

            <div className="p-4 bg-surfaceHover/50 rounded-lg">
              <h5 className="font-medium text-text mb-2">Parameters</h5>
              <pre className="text-xs text-textMuted overflow-x-auto">
                {JSON.stringify(config.parameters, null, 2)}
              </pre>
            </div>

            <div className="p-4 bg-surfaceHover/50 rounded-lg">
              <h5 className="font-medium text-text mb-2">Risk Settings</h5>
              <pre className="text-xs text-textMuted overflow-x-auto">
                {JSON.stringify(config.risk_settings, null, 2)}
              </pre>
            </div>
          </div>
        )

      default:
        return null
    }
  }

  const steps = [
    { key: 'type', label: 'Strategy Type', icon: <Brain className="w-4 h-4" /> },
    { key: 'params', label: 'Parameters', icon: <Settings className="w-4 h-4" /> },
    { key: 'risk', label: 'Risk', icon: <Target className="w-4 h-4" /> },
    { key: 'review', label: 'Review', icon: <Eye className="w-4 h-4" /> },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {steps.map((step, index) => (
            <div key={step.key} className="flex items-center">
              <button
                onClick={() => setActiveStep(step.key as typeof activeStep)}
                className={clsx(
                  'flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-all',
                  activeStep === step.key
                    ? 'bg-primary text-white'
                    : 'bg-surfaceHover text-textMuted hover:text-text'
                )}
              >
                {step.icon}
                <span className="hidden md:inline">{step.label}</span>
              </button>
              {index < steps.length - 1 && (
                <div className="w-4 h-px bg-border mx-2" />
              )}
            </div>
          ))}
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>
            {activeStep === 'type' && 'Select Strategy Type'}
            {activeStep === 'params' && 'Configure Parameters'}
            {activeStep === 'risk' && 'Risk Settings'}
            {activeStep === 'review' && 'Review & Save'}
          </CardTitle>
        </CardHeader>

        {renderStepContent()}

        <div className="flex justify-between mt-6 pt-4 border-t border-border">
          <Button
            variant="ghost"
            onClick={() => {
              const currentIndex = steps.findIndex(s => s.key === activeStep)
              if (currentIndex > 0) {
                setActiveStep(steps[currentIndex - 1].key as typeof activeStep)
              }
            }}
            disabled={activeStep === 'type'}
          >
            Back
          </Button>

          {activeStep !== 'review' ? (
            <Button
              onClick={() => {
                const currentIndex = steps.findIndex(s => s.key === activeStep)
                if (currentIndex < steps.length - 1) {
                  setActiveStep(steps[currentIndex + 1].key as typeof activeStep)
                }
              }}
            >
              {activeStep === 'risk' ? 'Review' : 'Next'}
            </Button>
          ) : (
            <Button onClick={handleSave}>
              <Save className="w-4 h-4 mr-2" />
              Create Strategy
            </Button>
          )}
        </div>
      </Card>
    </div>
  )
}

export default StrategyBuilder