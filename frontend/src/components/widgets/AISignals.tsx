/**
 * AI Signals Widget
 * =================
 * Real-time AI trading signals display.
 */

import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { TrendingUp, TrendingDown, Zap, Target, Shield, Brain, ChevronRight, X } from 'lucide-react'
import { clsx } from 'clsx'
import { wsManager } from '../../websocket/websocket.manager'
import type { AISignalPayload } from '../../websocket/websocket.types'

interface SignalCardProps {
  signal: AISignalPayload
  onExecute?: (signal: AISignalPayload) => void
  onDismiss?: (signalId: string) => void
}

function SignalCard({ signal, onExecute, onDismiss }: SignalCardProps) {
  const isBuy = signal.action === 'BUY'
  const confidence = signal.confidence

  const confidenceColor = confidence >= 85 ? '#3FB950' : confidence >= 70 ? '#F0883E' : '#F85149'

  return (
    <motion.div
      initial={{ opacity: 0, x: -20, scale: 0.95 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, x: 20, scale: 0.95 }}
      className={clsx(
        'border rounded-lg p-4 transition-all hover:shadow-lg',
        isBuy
          ? 'bg-gradient-to-r from-[#238636]/10 to-transparent border-[#238636]/30 hover:border-[#3FB950]'
          : 'bg-gradient-to-r from-[#F85149]/10 to-transparent border-[#F85149]/30 hover:border-[#F85149]'
      )}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className={clsx(
            'w-8 h-8 rounded-lg flex items-center justify-center',
            isBuy ? 'bg-[#3FB950]/20 text-[#3FB950]' : 'bg-[#F85149]/20 text-[#F85149]'
          )}>
            {isBuy ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
          </div>
          <div>
            <p className="font-semibold text-white">{signal.symbol}</p>
            <p className="text-xs text-[#8B949E]">{signal.action} Signal</p>
          </div>
        </div>

        <div className="flex items-center gap-1.5">
          <Brain className="w-4 h-4 text-[#8B949E]" />
          <span
            className="text-sm font-bold"
            style={{ color: confidenceColor }}
          >
            {confidence.toFixed(0)}%
          </span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 mb-3">
        <div className="bg-[#0D1117]/50 rounded-lg p-2">
          <div className="flex items-center gap-1.5 mb-1">
            <Target className="w-3 h-3 text-[#3FB950]" />
            <span className="text-xs text-[#8B949E]">Target</span>
          </div>
          <p className="text-sm font-medium text-white">₹{signal.target_price.toLocaleString('en-IN')}</p>
        </div>
        <div className="bg-[#0D1117]/50 rounded-lg p-2">
          <div className="flex items-center gap-1.5 mb-1">
            <Shield className="w-3 h-3 text-[#F85149]" />
            <span className="text-xs text-[#8B949E]">Stop Loss</span>
          </div>
          <p className="text-sm font-medium text-white">₹{signal.stop_loss.toLocaleString('en-IN')}</p>
        </div>
      </div>

      <div className="bg-[#0D1117]/50 rounded-lg p-2 mb-3">
        <p className="text-xs text-[#8B949E] mb-1">AI Reasoning</p>
        <p className="text-sm text-white/80 line-clamp-2">{signal.reasoning}</p>
      </div>

      {signal.indicators && (
        <div className="flex items-center gap-2 mb-3">
          {signal.indicators.rsi && (
            <span className="px-2 py-0.5 text-xs bg-[#21262D] rounded text-[#8B949E]">
              RSI: {signal.indicators.rsi}
            </span>
          )}
          {signal.indicators.macd && (
            <span className="px-2 py-0.5 text-xs bg-[#21262D] rounded text-[#8B949E]">
              MACD: {signal.indicators.macd}
            </span>
          )}
          <span className="px-2 py-0.5 text-xs bg-[#21262D] rounded text-[#8B949E]">
            {signal.timeframe}
          </span>
        </div>
      )}

      <div className="flex items-center gap-2">
        <button
          onClick={() => onExecute?.(signal)}
          className={clsx(
            'flex-1 py-2 rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-1.5',
            isBuy
              ? 'bg-[#238636] hover:bg-[#2ea043] text-white'
              : 'bg-[#F85149] hover:bg-[#da3633] text-white'
          )}
        >
          <Zap className="w-4 h-4" />
          Execute Trade
        </button>
        <button
          onClick={() => onDismiss?.(signal.signal_id)}
          className="p-2 hover:bg-[#21262D] rounded-lg text-[#8B949E] hover:text-white transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </motion.div>
  )
}

interface AISignalsWidgetProps {
  className?: string
  maxSignals?: number
}

export function AISignalsWidget({ className, maxSignals = 5 }: AISignalsWidgetProps) {
  const [signals, setSignals] = useState<AISignalPayload[]>([])
  const [isExpanded, setIsExpanded] = useState(true)

  useEffect(() => {
    const unsubscribe = wsManager.on<AISignalPayload>('ai_signal', (signal) => {
      setSignals((prev) => [signal, ...prev.slice(0, maxSignals - 1)])
    })

    return unsubscribe
  }, [maxSignals])

  const handleDismiss = (signalId: string) => {
    setSignals((prev) => prev.filter((s) => s.signal_id !== signalId))
  }

  const handleExecute = (signal: AISignalPayload) => {
    console.log('Executing signal:', signal)
  }

  const buySignals = signals.filter((s) => s.action === 'BUY')
  const sellSignals = signals.filter((s) => s.action === 'SELL')

  return (
    <div className={clsx('bg-[#0D1117] rounded-xl border border-[#21262D] overflow-hidden', className)}>
      <div
        className="flex items-center justify-between px-4 py-3 border-b border-[#21262D] cursor-pointer"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-2">
          <div className="p-1.5 bg-[#8B5CF6]/20 rounded-lg">
            <Brain className="w-4 h-4 text-[#8B5CF6]" />
          </div>
          <h3 className="font-semibold text-white">AI Trading Signals</h3>
          {signals.length > 0 && (
            <span className="px-2 py-0.5 text-xs bg-[#8B5CF6]/20 text-[#8B5CF6] rounded-full">
              {signals.length} new
            </span>
          )}
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="text-xs text-[#3FB950]">{buySignals.length} BUY</span>
            <span className="text-xs text-[#F85149]">{sellSignals.length} SELL</span>
          </div>
          <ChevronRight className={clsx(
            'w-4 h-4 text-[#8B949E] transition-transform',
            isExpanded && 'rotate-90'
          )} />
        </div>
      </div>

      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="p-3 space-y-3 max-h-[500px] overflow-y-auto"
          >
            {signals.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-8 text-[#8B949E]">
                <Brain className="w-8 h-8 mb-2 opacity-50" />
                <p className="text-sm">Waiting for AI signals...</p>
                <p className="text-xs mt-1">Signals will appear here in real-time</p>
              </div>
            ) : (
              signals.map((signal) => (
                <SignalCard
                  key={signal.signal_id}
                  signal={signal}
                  onExecute={handleExecute}
                  onDismiss={handleDismiss}
                />
              ))
            )}
          </motion.div>
        )}
      </AnimatePresence>

      <div className="px-4 py-2 border-t border-[#21262D] bg-[#0D1117]/50">
        <div className="flex items-center justify-between text-xs text-[#8B949E]">
          <span>Powered by AI Trading Engine</span>
          <span className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-[#8B5CF6] animate-pulse" />
            Live
          </span>
        </div>
      </div>
    </div>
  )
}

export default AISignalsWidget