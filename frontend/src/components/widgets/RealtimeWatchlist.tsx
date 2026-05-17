/**
 * Realtime Watchlist Component
 * ==============================
 * Premium Indian trading watchlist with live price updates.
 */

import React, { useState, useEffect, useMemo, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { TrendingUp, TrendingDown, Star, X, RefreshCw, Plus } from 'lucide-react'
import { clsx } from 'clsx'
import { useMarketStore, useAuthStore } from '../../store'
import type { Quote } from '../../types'

interface WatchlistItemProps {
  symbol: string
  quote?: Quote
  onRemove?: (symbol: string) => void
  onAddFavorite?: (symbol: string) => void
  isFavorite?: boolean
}

function WatchlistItem({ symbol, quote, onRemove, onAddFavorite, isFavorite }: WatchlistItemProps) {
  const [flash, setFlash] = useState<'up' | 'down' | null>(null)
  const [prevPrice, setPrevPrice] = useState(quote?.last_price)

  useEffect(() => {
    if (quote?.last_price && prevPrice && quote.last_price !== prevPrice) {
      const direction = quote.last_price > prevPrice ? 'up' : 'down'
      setFlash(direction)
      setTimeout(() => setFlash(null), 500)
      setPrevPrice(quote.last_price)
    } else if (quote?.last_price) {
      setPrevPrice(quote.last_price)
    }
  }, [quote?.last_price, prevPrice])

  const price = quote?.last_price || 0
  const change = quote?.change || 0
  const changePercent = quote?.change_percent || 0
  const isPositive = change >= 0

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 20 }}
      className={clsx(
        'flex items-center justify-between py-3 px-3 hover:bg-[#21262D]/50 rounded-lg transition-all cursor-pointer group',
        flash === 'up' && 'bg-green-500/10',
        flash === 'down' && 'bg-red-500/10'
      )}
    >
      <div className="flex items-center gap-3">
        <button
          onClick={(e) => {
            e.stopPropagation()
            onAddFavorite?.(symbol)
          }}
          className={clsx(
            'p-1 rounded hover:bg-[#21262D] transition-colors',
            isFavorite && 'text-yellow-400'
          )}
        >
          <Star className={clsx('w-4 h-4', isFavorite && 'fill-yellow-400')} />
        </button>
        <div>
          <p className="font-medium text-white text-sm">{symbol}</p>
          <p className="text-xs text-[#8B949E]">{quote?.exchange || 'NSE'}</p>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <div className="text-right">
          <motion.p
            key={price}
            animate={flash ? { scale: [1, 1.02, 1] } : {}}
            className="font-medium text-white text-sm"
          >
            ₹{price.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </motion.p>
          <p className={clsx('text-xs', isPositive ? 'text-[#3FB950]' : 'text-[#F85149]')}>
            {isPositive ? '+' : ''}₹{Math.abs(change).toFixed(2)} ({changePercent.toFixed(2)}%)
          </p>
        </div>

        <button
          onClick={(e) => {
            e.stopPropagation()
            onRemove?.(symbol)
          }}
          className="opacity-0 group-hover:opacity-100 p-1 hover:bg-[#F85149]/20 rounded text-[#F85149] transition-all"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    </motion.div>
  )
}

interface RealtimeWatchlistProps {
  className?: string
  onSymbolSelect?: (symbol: string) => void
}

export function RealtimeWatchlist({ className, onSymbolSelect }: RealtimeWatchlistProps) {
  const { quotes, fetchQuotes, prices } = useMarketStore()
  const { mode } = useAuthStore()
  const [showAddModal, setShowAddModal] = useState(false)

  const symbols = useMemo(() => {
    return Object.keys(quotes).length > 0
      ? Object.keys(quotes)
      : ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK', 'SBIN', 'BHARTIARTL', 'HINDUNILVR']
  }, [quotes])

  useEffect(() => {
    if (symbols.length > 0) {
      fetchQuotes(symbols)
    }
  }, [])

  const watchlistQuotes = useMemo(() => {
    return symbols.map((symbol) => {
      const quote = quotes.get(symbol)
      return {
        symbol,
        quote: quote || null,
      }
    })
  }, [symbols, quotes])

  return (
    <div className={clsx('bg-[#0D1117] rounded-xl border border-[#21262D] overflow-hidden', className)}>
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#21262D]">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
          <h3 className="font-semibold text-white">Live Watchlist</h3>
          <span className="text-xs text-[#8B949E]">• {symbols.length} symbols</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => fetchQuotes(symbols)}
            className="p-1.5 hover:bg-[#21262D] rounded-lg transition-colors text-[#8B949E] hover:text-white"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={() => setShowAddModal(true)}
            className="p-1.5 hover:bg-[#238636]/20 rounded-lg transition-colors text-[#238636]"
          >
            <Plus className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="max-h-[400px] overflow-y-auto">
        <AnimatePresence>
          {watchlistQuotes.map(({ symbol, quote }) => (
            <div
              key={symbol}
              onClick={() => onSymbolSelect?.(symbol)}
              className="border-b border-[#21262D]/50 last:border-0"
            >
              <WatchlistItem symbol={symbol} quote={quote || undefined} />
            </div>
          ))}
        </AnimatePresence>
      </div>

      <div className="px-4 py-2 border-t border-[#21262D] bg-[#0D1117]/50">
        <div className="flex items-center justify-between text-xs text-[#8B949E]">
          <span>Mode: {mode.toUpperCase()}</span>
          <span className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
            Live
          </span>
        </div>
      </div>
    </div>
  )
}

export default RealtimeWatchlist