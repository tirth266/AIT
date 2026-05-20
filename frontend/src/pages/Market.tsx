import { useState } from 'react'
import { motion } from 'framer-motion'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts'
import {
  TrendingUp,
  TrendingDown,
  Star,
  StarOff,
  Search,
  RefreshCw,
  Activity,
} from 'lucide-react'
import { clsx } from 'clsx'
import { useMarketStore } from '../store'
import { Card, CardHeader, CardTitle, Input, Button, Badge, Select } from '../components/ui'
import { mockPrices, generateCandleData } from '../services/mockData'

export function MarketPage() {
  const { prices, watchlist, selectedSymbol, setSelectedSymbol, addToWatchlist, removeFromWatchlist } = useMarketStore()
  const [searchQuery, setSearchQuery] = useState('')
  const [timeframe, setTimeframe] = useState('1h')
  const [candles, setCandles] = useState(generateCandleData(selectedSymbol || 'RELIANCE'))

  const displayPrices = Object.keys(prices).length > 0 ? prices : mockPrices

  const symbolList = Object.values(displayPrices).filter(p => 
    p.symbol.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const selectedPrice = selectedSymbol ? displayPrices[selectedSymbol] : undefined

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text">Market Overview</h1>
          <p className="text-textMuted">Real-time market data and prices</p>
        </div>
        <Button variant="outline">
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-3 space-y-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div className="flex items-center gap-4">
                <h2 className="text-xl font-bold text-text">{selectedSymbol}</h2>
                {selectedPrice && (
                  <div className="flex items-center gap-2">
                    <span className="text-2xl font-bold text-text">
                      ${selectedPrice.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </span>
                    <Badge variant={selectedPrice.change_percent_24h! >= 0 ? 'success' : 'danger'}>
                      {selectedPrice.change_percent_24h! >= 0 ? '+' : ''}{selectedPrice.change_percent_24h!.toFixed(2)}%
                    </Badge>
                  </div>
                )}
              </div>
              <div className="flex gap-2">
                {['1m', '5m', '15m', '1h', '4h', '1d'].map((tf) => (
                  <button
                    key={tf}
                    onClick={() => {
                      setTimeframe(tf)
                      setCandles(generateCandleData(selectedSymbol || 'RELIANCE', 100))
                    }}
                    className={clsx(
                      'px-3 py-1.5 text-sm font-medium rounded-md transition-colors',
                      timeframe === tf
                        ? 'bg-primary text-white'
                        : 'bg-surfaceHover text-textMuted hover:text-text'
                    )}
                  >
                    {tf}
                  </button>
                ))}
              </div>
            </CardHeader>

            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={candles}>
                  <defs>
                    <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#2563EB" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#2563EB" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis 
                    dataKey="timestamp" 
                    stroke="#9CA3AF" 
                    fontSize={12}
                    tickFormatter={(value) => new Date(value).toLocaleTimeString()}
                  />
                  <YAxis 
                    stroke="#9CA3AF" 
                    fontSize={12}
                    domain={['auto', 'auto']}
                    tickFormatter={(value) => `$${value.toLocaleString()}`}
                  />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#111827', border: '1px solid #374151', borderRadius: '8px' }}
                    labelFormatter={(label) => new Date(label).toLocaleString()}
                    formatter={(value: number) => [`$${value.toFixed(2)}`, 'Price']}
                  />
                  <Area 
                    type="monotone" 
                    dataKey="close" 
                    stroke="#2563EB" 
                    fillOpacity={1} 
                    fill="url(#colorPrice)" 
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </Card>

          {selectedPrice && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Card>
                <p className="text-sm text-textMuted">24h Change</p>
                <p className={clsx(
                  'text-xl font-bold',
                  selectedPrice.change_24h! >= 0 ? 'text-success' : 'text-danger'
                )}>
                  {selectedPrice.change_24h! >= 0 ? '+' : ''}${selectedPrice.change_24h!.toFixed(2)}
                </p>
              </Card>
              <Card>
                <p className="text-sm text-textMuted">24h High</p>
                <p className="text-xl font-bold text-text">
                  ${selectedPrice.high_24h?.toLocaleString()}
                </p>
              </Card>
              <Card>
                <p className="text-sm text-textMuted">24h Low</p>
                <p className="text-xl font-bold text-text">
                  ${selectedPrice.low_24h?.toLocaleString()}
                </p>
              </Card>
              <Card>
                <p className="text-sm text-textMuted">24h Volume</p>
                <p className="text-xl font-bold text-text">
                  {selectedPrice.volume_24h?.toLocaleString()}
                </p>
              </Card>
            </div>
          )}
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Watchlist</CardTitle>
            </CardHeader>
            <div className="space-y-2">
              {watchlist.map((symbol) => {
                const price = displayPrices[symbol]
                const isSelected = selectedSymbol === symbol

                return (
                  <motion.div
                    key={symbol}
                    whileHover={{ scale: 1.02 }}
                    className={clsx(
                      'flex items-center justify-between p-3 rounded-lg cursor-pointer transition-colors',
                      isSelected ? 'bg-primary/10 border border-primary/30' : 'bg-background hover:bg-surfaceHover'
                    )}
                    onClick={() => {
                      setSelectedSymbol(symbol)
                      setCandles(generateCandleData(symbol))
                    }}
                  >
                    <div className="flex items-center gap-2">
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          removeFromWatchlist(symbol)
                        }}
                        className="text-warning hover:text-yellow-400"
                      >
                        <Star className="w-4 h-4 fill-current" />
                      </button>
                      <span className="font-medium text-text">{symbol}</span>
                    </div>
                    {price && (
                      <div className="text-right">
                        <p className="text-text font-medium">
                          ${price.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </p>
                        <p className={clsx(
                          'text-xs',
                          price.change_percent_24h! >= 0 ? 'text-success' : 'text-danger'
                        )}>
                          {price.change_percent_24h! >= 0 ? '+' : ''}{price.change_percent_24h!.toFixed(2)}%
                        </p>
                      </div>
                    )}
                  </motion.div>
                )
              })}
            </div>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>All Markets</CardTitle>
            </CardHeader>
            <div className="mb-4">
              <Input
                placeholder="Search markets..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                icon={<Search className="w-4 h-4" />}
              />
            </div>
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {symbolList.map((price) => (
                <div
                  key={price.symbol}
                  className="flex items-center justify-between p-3 bg-background rounded-lg hover:bg-surfaceHover cursor-pointer"
                  onClick={() => {
                    setSelectedSymbol(price.symbol)
                    setCandles(generateCandleData(price.symbol))
                  }}
                >
                  <div className="flex items-center gap-2">
                    {watchlist.includes(price.symbol) ? (
                      <Star className="w-4 h-4 text-warning fill-current" />
                    ) : (
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          addToWatchlist(price.symbol)
                        }}
                      >
                        <StarOff className="w-4 h-4 text-textMuted hover:text-warning" />
                      </button>
                    )}
                    <span className="font-medium text-text">{price.symbol}</span>
                  </div>
                  <div className="text-right">
                    <p className="text-text font-medium">
                      ${price.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </p>
                    <p className={clsx(
                      'text-xs',
                      price.change_percent_24h! >= 0 ? 'text-success' : 'text-danger'
                    )}>
                      {price.change_percent_24h! >= 0 ? '+' : ''}{price.change_percent_24h!.toFixed(2)}%
                    </p>
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