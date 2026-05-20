/**
 * Market Ticker
 * ============
 * Scrolling market ticker with live prices.
 */

import React, { useState, useEffect, useMemo } from 'react'
import { motion } from 'framer-motion'
import { TrendingUp, TrendingDown, Activity } from 'lucide-react'
import { clsx } from 'clsx'
import { useShallow } from 'zustand/react/shallow'
import { useMarketStore, useTradingStore } from '../../store'
import { wsManager } from '../../websocket/websocket.manager'
import type { MarketStatusPayload } from '../../websocket/websocket.types'

const INDICES = [
  { symbol: 'NIFTY', name: 'Nifty 50', base: 22500 },
  { symbol: 'SENSEX', name: 'Sensex', base: 75000 },
  { symbol: 'BANKNIFTY', name: 'Bank Nifty', base: 48000 },
  { symbol: 'FINNIFTY', name: 'Fin Nifty', base: 20000 },
]

const TOP_STOCKS = ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK', 'SBIN', 'BHARTIARTL', 'HINDUNILVR']

interface TickerItemProps {
  symbol: string
  price: number
  change: number
  changePercent: number
  isIndex?: boolean
}

const TickerItem = React.memo(({ symbol, price, change, changePercent, isIndex }: TickerItemProps) => {
  const isPositive = change >= 0

  return (
    <div className="flex items-center gap-2 px-4 border-r border-[#21262D]/50">
      <span className="text-xs font-medium text-[#8B949E]">{symbol}</span>
      <span className="text-sm font-semibold text-white">
        {isIndex ? price.toLocaleString('en-IN', { maximumFractionDigits: 0 }) : price.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
      </span>
      <span className={clsx(
        'text-xs font-medium flex items-center gap-0.5',
        isPositive ? 'text-[#3FB950]' : 'text-[#F85149]'
      )}>
        {isPositive ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
        {change >= 0 ? '+' : ''}{changePercent.toFixed(2)}%
      </span>
    </div>
  )
})

export function MarketTicker() {
  const prices = useMarketStore(useShallow(state => state.prices))
  const mode = useTradingStore(state => state.mode)
  const [marketStatus, setMarketStatus] = useState<MarketStatusPayload | null>(null)

  useEffect(() => {
    const unsubscribe = wsManager.on<MarketStatusPayload>('market_status', (data) => {
      setMarketStatus(data)
    })

    wsManager.subscribeMarket(TOP_STOCKS)

    return () => {
      unsubscribe()
    }
  }, [])

  const allItems = useMemo(() => {
    const items: TickerItemProps[] = []

    INDICES.forEach((index) => {
      const priceData = prices[index.symbol] || { price: index.base, change_percent_24h: 0.5 + Math.random() * 0.5 }
      items.push({
        symbol: index.symbol,
        price: priceData.price,
        change: (priceData.price * (priceData.change_percent_24h || 0.5)) / 100,
        changePercent: priceData.change_percent_24h || 0.5,
        isIndex: true,
      })
    })

    TOP_STOCKS.forEach((symbol) => {
      const priceData = prices[symbol]
      if (priceData) {
        items.push({
          symbol,
          price: priceData.price,
          change: (priceData.price * (priceData.change_percent_24h || 0)) / 100,
          changePercent: priceData.change_percent_24h || 0,
        })
      }
    })

    return items
  }, [prices])

  return (
    <div className="w-full bg-[#0D1117] border-b border-[#21262D] overflow-hidden">
      <div className="flex items-center">
        <motion.div
          animate={{ x: [0, -1000] }}
          transition={{
            duration: 30,
            repeat: Infinity,
            ease: 'linear',
          }}
          className="flex items-center whitespace-nowrap"
        >
          {[...allItems, ...allItems].map((item, index) => (
            <TickerItem key={`${item.symbol}-${index}`} {...item} />
          ))}
        </motion.div>
      </div>

      <div className="flex items-center justify-between px-4 py-2 bg-[#0D1117]/50 border-t border-[#21262D]/50">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <Activity className="w-3.5 h-3.5 text-[#3FB950] animate-pulse" />
            <span className="text-xs font-medium text-[#3FB950]">NSE</span>
          </div>
          <span className={clsx(
            'text-xs px-2 py-0.5 rounded-full',
            marketStatus?.status === 'OPEN'
              ? 'bg-[#238636]/20 text-[#3FB950]'
              : 'bg-[#F85149]/20 text-[#F85149]'
          )}>
            {marketStatus?.status === 'OPEN' ? 'Live' : marketStatus?.session || 'CLOSED'}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-[#8B949E]">Mode:</span>
          <span className={clsx(
            'text-xs font-medium',
            mode === 'live' ? 'text-[#F85149]' : 'text-[#8B949E]'
          )}>
            {mode.toUpperCase()}
          </span>
        </div>
      </div>
    </div>
  )
}

export default MarketTicker