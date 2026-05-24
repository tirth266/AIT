import { useNavigate } from 'react-router-dom'
import React, { useEffect, useMemo } from 'react'
import { motion } from 'framer-motion'
import { XAxis, YAxis, Tooltip, ResponsiveContainer, AreaChart, Area, BarChart, Bar } from 'recharts'
import {
  Wallet,
  TrendingUp,
  TrendingDown,
  Activity,
  ArrowRight,
  Clock,
  Zap,
  Bot,
  LineChart,
} from 'lucide-react'
import { clsx } from 'clsx'
import { useShallow } from 'zustand/react/shallow'
import { 
  useTradingStore, 
  useMarketStore, 
  useDashboardStore, 
  useFundsStore, 
  useWatchlistStore 
} from '../store'
import { Card, CardHeader, CardTitle, Badge, StatusBadge, Button } from '../components/ui'
import { RealtimeWatchlist, RealtimePositions, AISignalsWidget } from '../components/widgets'
import { 
  mockDashboardData, 
  mockPositions, 
  mockBots, 
  mockTrades, 
  mockWatchlist, 
  mockOrders, 
  mockIndices 
} from '../services/mockData'
import type { Bot as BotType } from '../store/trading'
import { 
  useRealtimeConnection, 
  useRealtimeMarketData, 
  useRealtimePositions, 
  useRealtimeNotifications, 
  useRealtimeAISignals 
} from '../hooks'
import { useAngelOne } from '../broker/angelone'

const chartColors = {
  primary: '#238636',
  success: '#3FB950',
  danger: '#F85149',
  grid: '#21262D',
  text: '#8B949E',
}

interface StatCardProps {
  title: string
  value: string | number
  change?: string
  changeType?: 'positive' | 'negative' | 'neutral'
  icon: React.ElementType
  delay: number
}

const StatCard = React.memo(({ title, value, change, changeType, icon: Icon, delay }: StatCardProps) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
    >
      <Card hover className="relative overflow-hidden">
        <div className="absolute top-0 right-0 w-24 h-24 -mr-8 -mt-8 bg-[#238636]/5 rounded-full" />
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm text-[#8B949E] mb-1">{title}</p>
            <p className="text-2xl font-bold text-white">{value}</p>
            {change && (
              <p className={clsx(
                'text-sm mt-1',
                changeType === 'positive' && 'text-[#3FB950]',
                changeType === 'negative' && 'text-[#F85149]',
                changeType === 'neutral' && 'text-[#8B949E]'
              )}>
                {change}
              </p>
            )}
          </div>
          <div className="p-3 bg-[#238636]/10 rounded-lg">
            <Icon className="w-6 h-6 text-[#3FB950]" />
          </div>
        </div>
      </Card>
    </motion.div>
  )
})

interface PositionItemProps {
  position: typeof mockPositions[0]
}

const PositionItem = React.memo(({ position }: PositionItemProps) => {
  const isPositive = position.unrealized_pnl >= 0
  
  return (
    <div className="flex items-center justify-between py-3 border-b border-[#21262D] last:border-0">
      <div className="flex items-center gap-3">
        <div className={clsx(
          'w-8 h-8 rounded-lg flex items-center justify-center',
          position.side === 'BUY' ? 'bg-[#3FB950]/20 text-[#3FB950]' : 'bg-[#F85149]/20 text-[#F85149]'
        )}>
          {position.side === 'BUY' ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
        </div>
        <div>
          <p className="font-medium text-white">{position.symbol}</p>
          <p className="text-sm text-[#8B949E]">{position.strategy_name}</p>
        </div>
      </div>
      <div className="text-right">
        <p className="font-medium text-white">₹{position.current_price.toLocaleString()}</p>
        <p className={clsx('text-sm', isPositive ? 'text-[#3FB950]' : 'text-[#F85149]')}>
          {isPositive ? '+' : ''}₹{position.unrealized_pnl.toLocaleString()} ({position.unrealized_pnl_percent.toFixed(2)}%)
        </p>
      </div>
    </div>
  )
})

interface BotItemProps {
  bot: BotType
}

const BotItem = React.memo(({ bot }: BotItemProps) => {
  return (
    <div className="flex items-center justify-between py-3 border-b border-[#21262D] last:border-0">
      <div className="flex items-center gap-3">
        <div className="p-2 bg-[#238636]/10 rounded-lg">
          <Bot className="w-4 h-4 text-[#3FB950]" />
        </div>
        <div>
          <p className="font-medium text-white">{bot.strategy_name}</p>
          <p className="text-sm text-[#8B949E]">NSE • {bot.mode.toUpperCase()}</p>
        </div>
      </div>
      <div className="text-right">
        <StatusBadge status={bot.status} />
        <p className="text-sm text-[#8B949E] mt-1">
          {bot.trades_today} trades • {bot.pnl_today >= 0 ? '+' : ''}₹{bot.pnl_today.toLocaleString()}
        </p>
      </div>
    </div>
  )
})

interface OrderItemProps {
  order: typeof mockOrders[0]
}

const OrderItem = React.memo(({ order }: OrderItemProps) => {
  const isBuy = order.side === 'BUY'
  const statusColors: Record<string, string> = {
    COMPLETED: 'bg-[#238636]/20 text-[#3FB950]',
    PENDING: 'bg-[#F0883E]/20 text-[#F0883E]',
    CANCELLED: 'bg-[#F85149]/20 text-[#F85149]',
    REJECTED: 'bg-[#F85149]/20 text-[#F85149]',
  }

  return (
    <div className="flex items-center justify-between py-3 border-b border-[#21262D] last:border-0">
      <div className="flex items-center gap-3">
        <div className={clsx(
          'w-8 h-8 rounded-lg flex items-center justify-center',
          isBuy ? 'bg-[#3FB950]/20 text-[#3FB950]' : 'bg-[#F85149]/20 text-[#F85149]'
        )}>
          {isBuy ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
        </div>
        <div>
          <p className="font-medium text-white">{order.symbol}</p>
          <p className="text-sm text-[#8B949E]">
            {order.order_type} • {order.quantity} @ ₹{order.price?.toLocaleString()}
          </p>
        </div>
      </div>
      <div className="text-right">
        <span className={clsx('px-2 py-1 rounded text-xs font-medium', statusColors[order.status] || 'bg-[#8B949E]/20 text-[#8B949E]')}>
          {order.status}
        </span>
        <p className="text-sm text-[#8B949E] mt-1">
          {new Date(order.created_at).toLocaleTimeString()}
        </p>
      </div>
    </div>
  )
})

interface TradeItemProps {
  trade: typeof mockTrades[0]
}

const TradeItem = React.memo(({ trade }: TradeItemProps) => {
  const isPositive = (trade.pnl || 0) >= 0
  
  return (
    <div 
      className="flex items-center justify-between py-3 border-b border-[#21262D] last:border-0 cursor-pointer hover:bg-[#21262D]/50 rounded-lg px-2 -mx-2 transition-colors"
    >
      <div className="flex items-center gap-3">
        <div className={clsx(
          'w-8 h-8 rounded-lg flex items-center justify-center',
          trade.side === 'BUY' ? 'bg-[#3FB950]/20 text-[#3FB950]' : 'bg-[#F85149]/20 text-[#F85149]'
        )}>
          {trade.side === 'BUY' ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
        </div>
        <div>
          <p className="font-medium text-white">{trade.symbol}</p>
          <p className="text-sm text-[#8B949E] flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {new Date(trade.entry_time).toLocaleTimeString()}
          </p>
        </div>
      </div>
      <div className="text-right">
        <Badge variant={trade.mode === 'paper' ? 'default' : 'success'} size="sm">
          {trade.mode.toUpperCase()}
        </Badge>
        <p className={clsx('text-sm mt-1', isPositive ? 'text-[#3FB950]' : 'text-[#F85149]')}>
          {isPositive ? '+' : ''}₹{trade.pnl?.toLocaleString() || '0.00'}
        </p>
      </div>
    </div>
  )
})

interface IndexCardProps {
  name: string
  data: typeof mockIndices.NIFTY
}

const IndexCard = React.memo(({ name, data }: IndexCardProps) => {
  const isPositive = data.change >= 0
  return (
    <div className="p-3 bg-[#0D1117] rounded-lg border border-[#21262D]">
      <p className="text-xs text-[#8B949E] mb-1">{name}</p>
      <p className="text-lg font-bold text-white">{data.value.toLocaleString()}</p>
      <p className={clsx('text-xs', isPositive ? 'text-[#3FB950]' : 'text-[#F85149]')}>
        {isPositive ? '+' : ''}{data.change.toLocaleString()} ({isPositive ? '+' : ''}{data.change_percent.toFixed(2)}%)
      </p>
    </div>
  )
})

export function DashboardPage() {
  const navigate = useNavigate()
  const { isAuthenticated, refreshAll } = useAngelOne()
  
  console.log('[Dashboard] Rendering. Authenticated:', isAuthenticated);

  // Granular store selectors
  const mode = useTradingStore(state => state.mode)
  const { positions, bots, trades } = useTradingStore(useShallow(state => ({
    positions: state.positions || [],
    bots: state.bots || [],
    trades: state.trades || [],
  })))
  
  const { summary, funds, isLoading, error } = useDashboardStore(useShallow(state => ({
    summary: state.summary,
    funds: state.funds,
    isLoading: state.isLoading,
    error: state.error,
  })))
  const fetchSummary = useDashboardStore(state => state.fetchSummary)
  const fetchFunds = useDashboardStore(state => state.fetchFunds)
  const fetchPositions = useDashboardStore(state => state.fetchPositions)

  const { activeWatchlist, watchlistQuotes } = useWatchlistStore(useShallow(state => ({
    activeWatchlist: state.activeWatchlist,
    watchlistQuotes: state.quotes || {},
  })))
  const fetchWatchlists = useWatchlistStore(state => state.fetchWatchlists)

  useRealtimeConnection()
  useRealtimeMarketData()
  useRealtimePositions()
  useRealtimeNotifications()
  useRealtimeAISignals()

  const data = mockDashboardData

  useEffect(() => {
    // Get token to check if we are ready to fetch
    const token = useAuthStore.getState().jwtToken || 
                  JSON.parse(localStorage.getItem('angel-one-auth-storage') || '{}')?.state?.jwtToken;

    if (!token) {
      console.log('[Dashboard] No token available yet, skipping initialization');
      return;
    }

    console.log('[Dashboard] Mounting. Fetching data...');
    
    const initDashboard = async () => {
      try {
        await Promise.all([
          fetchSummary(),
          fetchFunds(),
          fetchPositions(),
          fetchWatchlists()
        ]);
        
        if (isAuthenticated) {
          console.log('[Dashboard] Authenticated, refreshing broker data');
          await refreshAll();
        }
      } catch (err) {
        console.error('[Dashboard] Error during initialization:', err);
      }
    };

    initDashboard();
  }, [fetchSummary, fetchFunds, fetchPositions, fetchWatchlists, isAuthenticated, refreshAll])

  const modeData = useMemo(() => funds?.balance?.total_balance || data.account.paper_balance, [funds, data.account.paper_balance])
  const indices = mockIndices

  const watchlistData = useMemo(() => activeWatchlist?.symbols?.map(symbol => {
    const quote = watchlistQuotes[symbol]
    return {
      symbol,
      price: quote?.last_price || 0,
      change: quote?.change_percent || 0,
      name: symbol
    }
  }) || mockWatchlist, [activeWatchlist, watchlistQuotes])

  const displayPositions = useMemo(() => (positions && positions.length > 0) ? positions : mockPositions, [positions])
  const displayBots = useMemo(() => (bots && bots.length > 0) ? bots : mockBots, [bots])
  const displayTrades = useMemo(() => (trades && trades.length > 0) ? trades.slice(0, 10) : mockTrades.slice(0, 10), [trades])

  if (isLoading && !summary?.account?.total_balance) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
        <p className="text-[#8B949E] animate-pulse">Initializing trading dashboard...</p>
      </div>
    );
  }

  if (error && !summary?.account?.total_balance) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4 text-center">
        <div className="p-4 bg-red-900/20 text-red-400 rounded-lg border border-red-900/50 max-w-md">
          <h3 className="text-lg font-bold mb-2">Dashboard Error</h3>
          <p>{error}</p>
          <Button 
            className="mt-4" 
            variant="outline" 
            onClick={() => window.location.reload()}
          >
            Retry Connection
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className="text-[#8B949E] mt-1">Real-time trading overview</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 bg-[#238636]/10 rounded-lg border border-[#238636]/20">
            <div className="w-2 h-2 rounded-full bg-[#3FB950] animate-pulse" />
            <span className="text-sm text-[#3FB950] font-medium">NSE Live</span>
          </div>
          <Badge variant={mode === 'paper' ? 'default' : 'success'}>
            {mode.toUpperCase()}
          </Badge>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        <StatCard
          title="Portfolio Value"
          value={`₹${(modeData + (summary?.today.pnl || data.today.pnl)).toLocaleString()}`}
          change={`Available: ₹${funds?.balance.available_cash?.toLocaleString() || data.account.available_margin.toLocaleString()}`}
          changeType="neutral"
          icon={Wallet}
          delay={0}
        />
        <StatCard
          title="Today's P&L"
          value={`${(summary?.today.pnl || data.today.pnl) >= 0 ? '+' : ''}₹${(summary?.today.pnl || data.today.pnl).toLocaleString()}`}
          change={`${(summary?.today.pnl_percent || data.today.pnl_percent) >= 0 ? '+' : ''}${(summary?.today.pnl_percent || data.today.pnl_percent).toFixed(2)}%`}
          changeType={(summary?.today.pnl || data.today.pnl) >= 0 ? 'positive' : 'negative'}
          icon={TrendingUp}
          delay={0.1}
        />
        <StatCard
          title="Available Margin"
          value={`₹${funds?.balance.available_cash?.toLocaleString() || data.account.available_margin.toLocaleString()}`}
          change={`Used: ₹${funds?.balance.used_margin?.toLocaleString() || data.account.used_margin.toLocaleString()}`}
          changeType="neutral"
          icon={Activity}
          delay={0.2}
        />
        <StatCard
          title="Open Positions"
          value={displayPositions.length.toString()}
          change={`Win rate: ${(summary?.today.win_rate || data.today.win_rate).toFixed(1)}%`}
          changeType="neutral"
          icon={LineChart}
          delay={0.3}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.35 }}
          className="lg:col-span-3"
        >
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-0">
              <CardTitle>Market Overview</CardTitle>
              <div className="flex gap-2">
                {['1D', '1W', '1M', '3M'].map((period) => (
                  <button
                    key={period}
                    className="px-3 py-1 text-xs font-medium rounded-md bg-[#21262D] text-[#8B949E] hover:text-white transition-colors"
                  >
                    {period}
                  </button>
                ))}
              </div>
            </CardHeader>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6 mt-4">
              <IndexCard name="NIFTY 50" data={indices.NIFTY} />
              <IndexCard name="SENSEX" data={indices.SENSEX} />
              <IndexCard name="BANKNIFTY" data={indices.BANKNIFTY} />
              <IndexCard name="FINNIFTY" data={indices.FINNIFTY} />
              <IndexCard name="INDIA VIX" data={indices.INDIAVIX} />
            </div>
            <div className="h-40">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={data.performance.daily}>
                  <defs>
                    <linearGradient id="colorPnL" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={chartColors.primary} stopOpacity={0.3} />
                      <stop offset="95%" stopColor={chartColors.primary} stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis 
                    dataKey="date" 
                    stroke={chartColors.text} 
                    fontSize={11}
                    tickFormatter={(value) => value.split('-')[2] || value}
                  />
                  <YAxis 
                    stroke={chartColors.text} 
                    fontSize={11}
                    tickFormatter={(value) => `₹${value/1000}k`}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#0D1117',
                      border: '1px solid #21262D',
                      borderRadius: '8px',
                    }}
                    labelStyle={{ color: '#8B949E' }}
                    itemStyle={{ color: '#F8FAFC' }}
                    formatter={(value: number) => [`₹${value.toLocaleString()}`, 'P&L']}
                  />
                  <Area
                    type="monotone"
                    dataKey="pnl"
                    stroke={chartColors.primary}
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#colorPnL)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
        >
          <RealtimeWatchlist onSymbolSelect={(symbol) => navigate(`/market?symbol=${symbol}`)} />
        </motion.div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
        >
          <RealtimePositions />
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
        >
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Recent Orders</CardTitle>
              <Button variant="ghost" size="sm" onClick={() => navigate('/orders')}>
                View All <ArrowRight className="w-4 h-4 ml-1" />
              </Button>
            </CardHeader>
            <div className="space-y-0">
              {mockOrders.slice(0, 4).map((order) => (
                <OrderItem key={order._id} order={order} />
              ))}
            </div>
          </Card>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7 }}
        >
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Active Bots</CardTitle>
              <Button variant="ghost" size="sm" onClick={() => navigate('/bots')}>
                View All <ArrowRight className="w-4 h-4 ml-1" />
              </Button>
            </CardHeader>
            <div className="space-y-0">
              {displayBots.map((bot) => (
                <BotItem key={bot.strategy_id} bot={bot} />
              ))}
              {displayBots.length === 0 && (
                <div className="text-center py-8">
                  <Zap className="w-8 h-8 text-[#8B949E] mx-auto mb-2" />
                  <p className="text-[#8B949E]">No active bots</p>
                  <Button variant="outline" size="sm" className="mt-2" onClick={() => navigate('/strategies')}>
                    Create Strategy
                  </Button>
                </div>
              )}
            </div>
          </Card>
        </motion.div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.8 }}
        >
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Recent Trades</CardTitle>
              <Button variant="ghost" size="sm" onClick={() => navigate('/trades')}>
                View All <ArrowRight className="w-4 h-4 ml-1" />
              </Button>
            </CardHeader>
            <div className="space-y-0">
              {displayTrades.map((trade) => (
                <TradeItem key={trade._id} trade={trade} />
              ))}
            </div>
          </Card>
        </motion.div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1.0 }}
        >
          <AISignalsWidget maxSignals={3} />
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1.1 }}
        >
          <Card>
            <CardHeader>
              <CardTitle>Trading Performance</CardTitle>
            </CardHeader>
            <div className="h-48">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data.performance.daily.slice(-7)}>
                  <XAxis
                    dataKey="date"
                    stroke={chartColors.text}
                    fontSize={11}
                    tickFormatter={(value) => value.split('-')[2] || value}
                  />
                  <YAxis
                    stroke={chartColors.text}
                    fontSize={11}
                    tickFormatter={(value) => `₹${value/1000}k`}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#0D1117',
                      border: '1px solid #21262D',
                      borderRadius: '8px',
                    }}
                    labelStyle={{ color: '#8B949E' }}
                    itemStyle={{ color: '#F8FAFC' }}
                    formatter={(value: number) => [`₹${value.toLocaleString()}`, 'P&L']}
                  />
                  <Bar dataKey="pnl" fill={chartColors.primary} radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </motion.div>
      </div>
      </div>
    </div>
  )
}

export default DashboardPage