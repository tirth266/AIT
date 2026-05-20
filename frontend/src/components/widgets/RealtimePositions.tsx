/**
 * Realtime Positions Panel
 * ========================
 * Live positions with real-time P&L updates.
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { TrendingUp, TrendingDown, X, ChevronDown, ChevronUp, AlertCircle } from 'lucide-react'
import { clsx } from 'clsx'
import { useShallow } from 'zustand/react/shallow'
import { useTradingEngineStore } from '../../store'

interface PositionItemProps {
  position: {
    position_id?: string
    symbol: string
    side?: 'BUY' | 'SELL'
    quantity: number
    entry_price?: number
    current_price: number
    unrealized_pnl?: number
    unrealized_pnl_percent?: number
    mode?: 'paper' | 'live'
  }
  onExit: (positionId: string) => void
}

const PositionCard = React.memo(({ position, onExit }: PositionItemProps) => {
  const [flash, setFlash] = useState<'up' | 'down' | null>(null)
  const [isExpanded, setIsExpanded] = useState(false)
  const [prevPnl, setPrevPnl] = useState(position.unrealized_pnl ?? 0)

  const isBuy = position.side === 'BUY'
  const isPositive = (position.unrealized_pnl ?? 0) >= 0

  useEffect(() => {
    const currentPnl = position.unrealized_pnl ?? 0
    if (currentPnl !== prevPnl) {
      const direction = currentPnl > prevPnl ? 'up' : 'down'
      setFlash(direction)
      setTimeout(() => setFlash(null), 600)
      setPrevPnl(currentPnl)
    }
  }, [position.unrealized_pnl, prevPnl])

  const value = position.quantity * position.current_price

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className={clsx(
        'border rounded-lg overflow-hidden transition-all',
        flash === 'up' && 'border-[#3FB950] shadow-lg shadow-[#3FB950]/10',
        flash === 'down' && 'border-[#F85149] shadow-lg shadow-[#F85149]/10',
        !flash && 'border-[#21262D]'
      )}
    >
      <div
        className="flex items-center justify-between p-3 cursor-pointer hover:bg-[#21262D]/30"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-3">
          <div className={clsx(
            'w-8 h-8 rounded-lg flex items-center justify-center',
            isBuy ? 'bg-[#3FB950]/20 text-[#3FB950]' : 'bg-[#F85149]/20 text-[#F85149]'
          )}>
            {isBuy ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
          </div>
          <div>
            <p className="font-medium text-white">{position.symbol}</p>
            <p className="text-xs text-[#8B949E]">
              {position.quantity} @ ₹{(position.entry_price ?? 0).toFixed(2)}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="text-right">
            <p className="font-medium text-white">
              ₹{position.current_price.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </p>
            <motion.p
              key={position.unrealized_pnl}
              animate={flash ? { scale: [1, 1.1, 1] } : {}}
              className={clsx(
                'text-sm font-medium',
                isPositive ? 'text-[#3FB950]' : 'text-[#F85149]'
              )}
            >
              {isPositive ? '+' : ''}₹{(position.unrealized_pnl ?? 0).toFixed(2)}
              <span className="text-xs ml-1">
                ({(position.unrealized_pnl_percent ?? 0) >= 0 ? '+' : ''}{(position.unrealized_pnl_percent ?? 0).toFixed(2)}%)
              </span>
            </motion.p>
          </div>

          <button
            onClick={(e) => {
              e.stopPropagation()
              onExit(position.position_id || '')
            }}
            className="p-1.5 bg-[#F85149]/10 hover:bg-[#F85149]/20 text-[#F85149] rounded-lg transition-colors"
          >
            <X className="w-4 h-4" />
          </button>

          {isExpanded ? (
            <ChevronUp className="w-4 h-4 text-[#8B949E]" />
          ) : (
            <ChevronDown className="w-4 h-4 text-[#8B949E]" />
          )}
        </div>
      </div>

      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="border-t border-[#21262D] bg-[#0D1117]/50"
          >
            <div className="grid grid-cols-2 gap-4 p-3 text-sm">
              <div>
                <p className="text-[#8B949E] text-xs mb-1">Current Value</p>
                <p className="text-white font-medium">₹{value.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</p>
              </div>
              <div>
                <p className="text-[#8B949E] text-xs mb-1">Entry Value</p>
                <p className="text-white font-medium">₹{(position.quantity * (position.entry_price ?? 0)).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</p>
              </div>
              <div>
                <p className="text-[#8B949E] text-xs mb-1">Quantity</p>
                <p className="text-white font-medium">{position.quantity}</p>
              </div>
              <div>
                <p className="text-[#8B949E] text-xs mb-1">Mode</p>
                <span className={clsx(
                  'px-2 py-0.5 text-xs rounded-full',
                  position.mode === 'live' ? 'bg-[#F85149]/20 text-[#F85149]' : 'bg-[#8B949E]/20 text-[#8B949E]'
                )}>
                  {typeof position.mode === 'string' ? position.mode.toUpperCase() : 'PAPER'}
                </span>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
})

interface RealtimePositionsProps {
  className?: string
}

export function RealtimePositions({ className }: RealtimePositionsProps) {
  const positions = useTradingEngineStore(useShallow(state => state.positions))
  const mode = useTradingEngineStore(state => state.mode)
  const exitPosition = useTradingEngineStore(state => state.exitPosition)
  const fetchOpenPositions = useTradingEngineStore(state => state.fetchOpenPositions)

  useEffect(() => {
    fetchOpenPositions()
  }, [fetchOpenPositions])

  const metrics = useMemo(() => {
    const totalUnrealizedPnl = positions.reduce((sum, p) => sum + (p.unrealized_pnl ?? 0), 0)
    const totalValue = positions.reduce((sum, p) => sum + (p.quantity * p.current_price), 0)
    const winningPositions = positions.filter(p => (p.unrealized_pnl ?? 0) >= 0).length
    const winRate = positions.length > 0 ? (winningPositions / positions.length) * 100 : 0

    return { totalUnrealizedPnl, totalValue, winRate }
  }, [positions])

  const { totalUnrealizedPnl, totalValue, winRate } = metrics

  const handleExit = useCallback(async (positionId: string) => {
    try {
      await exitPosition(positionId)
    } catch (error) {
      console.error('Failed to exit position:', error)
    }
  }, [exitPosition])

  return (
    <div className={clsx('bg-[#0D1117] rounded-xl border border-[#21262D] overflow-hidden', className)}>
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#21262D]">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
          <h3 className="font-semibold text-white">Open Positions</h3>
          <span className="text-xs text-[#8B949E]">• {positions.length}</span>
        </div>
        <div className="flex items-center gap-3">
          <div className="text-right">
            <p className={clsx('text-sm font-medium', totalUnrealizedPnl >= 0 ? 'text-[#3FB950]' : 'text-[#F85149]')}>
              {totalUnrealizedPnl >= 0 ? '+' : ''}₹{totalUnrealizedPnl.toFixed(2)}
            </p>
            <p className="text-xs text-[#8B949E]">Unrealized P&L</p>
          </div>
        </div>
      </div>

      <div className="p-3 space-y-2 max-h-[400px] overflow-y-auto">
        {positions.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-[#8B949E]">
            <AlertCircle className="w-8 h-8 mb-2 opacity-50" />
            <p className="text-sm">No open positions</p>
            <p className="text-xs mt-1">Place an order to start trading</p>
          </div>
        ) : (
          <AnimatePresence>
            {positions.map((position) => (
              <PositionCard
                key={position.position_id || Math.random().toString()}
                position={position}
                onExit={handleExit}
              />
            ))}
          </AnimatePresence>
        )}
      </div>

      <div className="grid grid-cols-3 gap-4 px-4 py-3 border-t border-[#21262D] bg-[#0D1117]/50">
        <div>
          <p className="text-xs text-[#8B949E]">Total Value</p>
          <p className="text-sm font-medium text-white">₹{totalValue.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</p>
        </div>
        <div>
          <p className="text-xs text-[#8B949E]">Win Rate</p>
          <p className="text-sm font-medium text-white">{winRate.toFixed(1)}%</p>
        </div>
        <div>
          <p className="text-xs text-[#8B949E]">Mode</p>
          <span className={clsx(
            'text-sm font-medium',
            mode === 'live' ? 'text-[#F85149]' : 'text-[#8B949E]'
          )}>
            {typeof mode === 'string' ? mode.toUpperCase() : 'PAPER'}
          </span>
        </div>
      </div>
    </div>
  )
}

export default RealtimePositions