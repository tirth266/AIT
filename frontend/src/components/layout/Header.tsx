import { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Bell,
  ChevronDown,
  Wallet,
  TrendingUp,
  TrendingDown,
  Settings as SettingsIcon,
} from 'lucide-react'
import { clsx } from 'clsx'
import { useTradingStore, useMarketStore } from '../../store'
import { ConnectionStatus } from '../ui/ConnectionStatus'

interface HeaderProps {
  unreadCount?: number
}

const DEFAULT_INDEX_DATA = {
  price: 24500,
  change_percent_24h: 0.5,
}

const DEFAULT_WALLET_BALANCE = {
  paper: 500000,
  live: 250000,
}

export function Header({ unreadCount = 0 }: HeaderProps) {
  const navigate = useNavigate()
  const [mode, setMode] = useState<'paper' | 'live'>('paper')
  const positions = useTradingStore((state) => state.positions ?? [])
  const prices = useMarketStore((state) => state.prices ?? {})
  const [showDropdown, setShowDropdown] = useState(false)

  const user = { full_name: 'Admin' }

  const totalUnrealizedPnL = useMemo(() => {
    if (!Array.isArray(positions)) return 0
    return positions.reduce((sum, p) => sum + (p?.unrealized_pnl ?? 0), 0)
  }, [positions])

  const niftyData = useMemo(() => {
    const data = prices?.['NIFTY']
    return data ?? DEFAULT_INDEX_DATA
  }, [prices])

  const sensexData = useMemo(() => {
    const data = prices?.['SENSEX']
    return data ?? { ...DEFAULT_INDEX_DATA, price: 82000, change_percent_24h: 0.3 }
  }, [prices])

  const niftyChange = niftyData?.change_percent_24h ?? 0
  const sensexChange = sensexData?.change_percent_24h ?? 0

  const walletBalance = mode === 'paper' 
    ? DEFAULT_WALLET_BALANCE.paper 
    : DEFAULT_WALLET_BALANCE.live

  return (
    <header className="h-14 bg-[#0D1117]/80 backdrop-blur-lg border-b border-[#21262D] flex items-center justify-between px-4 sticky top-0 z-30">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-3 text-sm">
          <div className="flex items-center gap-2 px-2.5 py-1.5 bg-[#21262D] rounded-md">
            <span className="text-[#8B949E] text-xs">NIFTY</span>
            <span className="text-white font-medium text-sm">
              {(niftyData?.price ?? 24500).toLocaleString()}
            </span>
            <span className={clsx('text-xs', niftyChange >= 0 ? 'text-[#3FB950]' : 'text-[#F85149]')}>
              {niftyChange >= 0 ? '+' : ''}{niftyChange.toFixed(2)}%
            </span>
          </div>
          <div className="flex items-center gap-2 px-2.5 py-1.5 bg-[#21262D] rounded-md">
            <span className="text-[#8B949E] text-xs">SENSEX</span>
            <span className="text-white font-medium text-sm">
              {(sensexData?.price ?? 82000).toLocaleString()}
            </span>
            <span className={clsx('text-xs', sensexChange >= 0 ? 'text-[#3FB950]' : 'text-[#F85149]')}>
              {sensexChange >= 0 ? '+' : ''}{sensexChange.toFixed(2)}%
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3 text-sm">
          <div className="flex items-center gap-1.5 text-[#8B949E]">
            <Wallet className="w-3.5 h-3.5" />
            <span className="text-xs">₹{walletBalance.toLocaleString()}</span>
          </div>
          <div className={clsx('flex items-center gap-1.5', totalUnrealizedPnL >= 0 ? 'text-[#3FB950]' : 'text-[#F85149]')}>
            {totalUnrealizedPnL >= 0 ? <TrendingUp className="w-3.5 h-3.5" /> : <TrendingDown className="w-3.5 h-3.5" />}
            <span className="text-xs">
              ₹{totalUnrealizedPnL >= 0 ? '+' : ''}{totalUnrealizedPnL.toFixed(2)}
            </span>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <ConnectionStatus />

        <div className="flex items-center gap-1 mr-2">
          <button
            onClick={() => setMode('paper')}
            className={clsx(
              'px-2.5 py-1 text-xs font-medium rounded-md transition-colors',
              mode === 'paper'
                ? 'bg-[#238636]/20 text-[#3FB950]'
                : 'text-[#8B949E] hover:text-white'
            )}
          >
            PAPER
          </button>
          <button
            onClick={() => setMode('live')}
            className={clsx(
              'px-2.5 py-1 text-xs font-medium rounded-md transition-colors',
              mode === 'live'
                ? 'bg-[#F85149]/20 text-[#F85149]'
                : 'text-[#8B949E] hover:text-white'
            )}
          >
            LIVE
          </button>
        </div>

        <button
          onClick={() => navigate('/notifications')}
          className="relative p-2 rounded-md hover:bg-[#21262D] text-[#8B949E] hover:text-white transition-colors"
        >
          <Bell className="w-4.5 h-4.5" />
          {unreadCount > 0 && (
            <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-[#F85149] rounded-full" />
          )}
        </button>

        <div className="relative">
          <button
            onClick={() => setShowDropdown(!showDropdown)}
            className="flex items-center gap-2 px-2 py-1.5 rounded-md hover:bg-[#21262D] transition-colors"
          >
            <div className="w-7 h-7 rounded-md bg-gradient-to-br from-[#238636] to-[#2EA043] flex items-center justify-center">
              <span className="text-xs font-medium text-white">
                {user?.full_name?.charAt(0) || 'A'}
              </span>
            </div>
            <span className="text-sm text-white">{user?.full_name || 'Admin'}</span>
            <ChevronDown className="w-3.5 h-3.5 text-[#8B949E]" />
          </button>

          {showDropdown && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="absolute right-0 mt-2 w-44 bg-[#161B22] border border-[#30363D] rounded-lg shadow-xl overflow-hidden"
            >
              <button
                onClick={() => {
                  setShowDropdown(false)
                  navigate('/funds')
                }}
                className="w-full px-3 py-2 text-left text-sm text-white hover:bg-[#21262D] flex items-center gap-2"
              >
                <Wallet className="w-4 h-4" />
                Funds
              </button>
              <button
                onClick={() => {
                  setShowDropdown(false)
                  navigate('/settings')
                }}
                className="w-full px-3 py-2 text-left text-sm text-white hover:bg-[#21262D] flex items-center gap-2"
              >
                <SettingsIcon className="w-4 h-4" />
                Settings
              </button>
            </motion.div>
          )}
        </div>
      </div>
    </header>
  )
}

export default Header