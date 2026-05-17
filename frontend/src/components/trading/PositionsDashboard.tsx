import { useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  TrendingUp, TrendingDown, X, Clock, 
  Target, Shield, RefreshCw, ExternalLink
} from 'lucide-react'
import { clsx } from 'clsx'
import { useTradingEngineStore } from '../../store'
import type { Position } from '../../types'

interface PositionsDashboardProps {
  onSelectSymbol?: (symbol: string) => void
}

export function PositionsDashboard({ onSelectSymbol }: PositionsDashboardProps) {
  const { 
    positions, 
    pnl, 
    dayPnL, 
    isLoadingPositions, 
    fetchOpenPositions, 
    fetchPnL, 
    fetchDayPnL,
    exitPosition 
  } = useTradingEngineStore()
  
  useEffect(() => {
    fetchOpenPositions({ mode: 'paper' })
    fetchPnL('paper')
    fetchDayPnL('paper')
    
    const interval = setInterval(() => {
      fetchOpenPositions({ mode: 'paper' })
      fetchPnL('paper')
    }, 5000)
    
    return () => clearInterval(interval)
  }, [fetchOpenPositions, fetchPnL, fetchDayPnL])
  
  const handleExit = useCallback(async (positionId: string) => {
    await exitPosition(positionId)
    fetchOpenPositions({ mode: 'paper' })
    fetchPnL('paper')
  }, [exitPosition, fetchOpenPositions, fetchPnL])
  
  const formatPrice = (price: number) => price.toFixed(2)
  const formatPnL = (pnl: number) => {
    const sign = pnl >= 0 ? '+' : ''
    return `${sign}₹${pnl.toFixed(2)}`
  }
  
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-4 gap-3">
        <div className="bg-card border border-border rounded-xl p-4">
          <div className="text-sm text-muted-foreground mb-1">Day P&L</div>
          <div className={clsx(
            'text-2xl font-bold',
            (dayPnL?.day_pnl || 0) >= 0 ? 'text-green-400' : 'text-red-400'
          )}>
            {formatPnL(dayPnL?.day_pnl || 0)}
          </div>
        </div>
        
        <div className="bg-card border border-border rounded-xl p-4">
          <div className="text-sm text-muted-foreground mb-1">Unrealized P&L</div>
          <div className={clsx(
            'text-2xl font-bold',
            (pnl?.unrealized_pnl || 0) >= 0 ? 'text-green-400' : 'text-red-400'
          )}>
            {formatPnL(pnl?.unrealized_pnl || 0)}
          </div>
        </div>
        
        <div className="bg-card border border-border rounded-xl p-4">
          <div className="text-sm text-muted-foreground mb-1">Realized P&L</div>
          <div className={clsx(
            'text-2xl font-bold',
            (pnl?.realized_pnl || 0) >= 0 ? 'text-green-400' : 'text-red-400'
          )}>
            {formatPnL(pnl?.realized_pnl || 0)}
          </div>
        </div>
        
        <div className="bg-card border border-border rounded-xl p-4">
          <div className="text-sm text-muted-foreground mb-1">Total P&L</div>
          <div className={clsx(
            'text-2xl font-bold',
            (pnl?.total_pnl || 0) >= 0 ? 'text-green-400' : 'text-red-400'
          )}>
            {formatPnL(pnl?.total_pnl || 0)}
          </div>
        </div>
      </div>
      
      <div className="bg-card border border-border rounded-xl overflow-hidden">
        <div className="p-4 border-b border-border">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold">Open Positions</h3>
            <button
              onClick={() => fetchOpenPositions({ mode: 'paper' })}
              className="p-2 hover:bg-muted rounded-lg transition-colors"
            >
              <RefreshCw className={clsx(
                'w-4 h-4',
                isLoadingPositions && 'animate-spin'
              )} />
            </button>
          </div>
        </div>
        
        {isLoadingPositions && positions.length === 0 ? (
          <div className="p-8 text-center text-muted-foreground">
            <RefreshCw className="w-8 h-8 mx-auto mb-2 animate-spin" />
            Loading positions...
          </div>
        ) : positions.length === 0 ? (
          <div className="p-8 text-center text-muted-foreground">
            <Target className="w-8 h-8 mx-auto mb-2 opacity-50" />
            No open positions
          </div>
        ) : (
          <div className="divide-y divide-border">
            <AnimatePresence>
              {positions.map((position) => (
                <PositionRow 
                  key={position.position_id} 
                  position={position}
                  onExit={() => handleExit(position.position_id)}
                  onSelectSymbol={() => onSelectSymbol?.(position.symbol)}
                />
              ))}
            </AnimatePresence>
          </div>
        )}
      </div>
    </div>
  )
}

interface PositionRowProps {
  position: Position
  onExit: () => void
  onSelectSymbol: () => void
}

function PositionRow({ position, onExit, onSelectSymbol }: PositionRowProps) {
  const [isExiting, setIsExiting] = useState(false)
  
  const pnlPercent = position.average_price > 0
    ? ((position.current_price - position.average_price) / position.average_price * 100)
    : 0
  
  const isProfit = position.unrealized_pnl >= 0
  
  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 20 }}
      className="p-4 hover:bg-muted/30 transition-colors"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={onSelectSymbol}
            className="flex items-center gap-2 group"
          >
            <span className={clsx(
              'w-8 h-8 rounded-lg flex items-center justify-center font-bold text-sm',
              position.product_type === 'CNC' 
                ? 'bg-blue-500/20 text-blue-400' 
                : 'bg-orange-500/20 text-orange-400'
            )}>
              {position.product_type === 'CNC' ? 'CNC' : 'MIS'}
            </span>
            <div>
              <div className="font-medium">{position.symbol}</div>
              <div className="text-sm text-muted-foreground">
                {position.quantity} qty @ ₹{position.average_price.toFixed(2)}
              </div>
            </div>
            <ExternalLink className="w-4 h-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
          </button>
        </div>
        
        <div className="flex items-center gap-6">
          <div className="text-right">
            <div className="font-bold text-lg">₹{position.current_price.toFixed(2)}</div>
            <div className="text-sm text-muted-foreground">LTP</div>
          </div>
          
          <div className="text-right min-w-[100px]">
            <div className={clsx(
              'font-bold text-lg flex items-center gap-1',
              isProfit ? 'text-green-400' : 'text-red-400'
            )}>
              {isProfit ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
              {formatPnL(position.unrealized_pnl)}
            </div>
            <div className={clsx(
              'text-sm',
              isProfit ? 'text-green-400' : 'text-red-400'
            )}>
              {pnlPercent >= 0 ? '+' : ''}{pnlPercent.toFixed(2)}%
            </div>
          </div>
          
          <div className="text-right">
            <div className={clsx(
              'font-bold text-lg flex items-center gap-1',
              position.realized_pnl >= 0 ? 'text-green-400' : 'text-red-400'
            )}>
              {formatPnL(position.realized_pnl)}
            </div>
            <div className="text-sm text-muted-foreground">Realized</div>
          </div>
          
          <button
            onClick={() => {
              setIsExiting(true)
              onExit()
              setTimeout(() => setIsExiting(false), 2000)
            }}
            disabled={isExiting}
            className={clsx(
              'p-2 rounded-lg transition-all',
              isExiting 
                ? 'bg-red-600 text-white' 
                : 'bg-red-500/10 text-red-400 hover:bg-red-500/20'
            )}
          >
            {isExiting ? <Clock className="w-5 h-5 animate-spin" /> : <X className="w-5 h-5" />}
          </button>
        </div>
      </div>
      
      {position.stop_loss && position.take_profit && (
        <div className="flex gap-4 mt-2 text-sm text-muted-foreground">
          <span className="flex items-center gap-1">
            <Shield className="w-3 h-3" />
            SL: ₹{position.stop_loss.toFixed(2)}
          </span>
          <span className="flex items-center gap-1">
            <Target className="w-3 h-3" />
            TP: ₹{position.take_profit.toFixed(2)}
          </span>
        </div>
      )}
    </motion.div>
  )
}

import { useState } from 'react'

export default PositionsDashboard