import { NavLink, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { clsx } from 'clsx'
import {
  LayoutDashboard,
  Eye,
  TrendingUp,
  FileText,
  Wallet,
  Bell,
  Settings,
  ChevronLeft,
  ChevronRight,
  Bot,
  Cog,
  History,
} from 'lucide-react'
import { useUIStore } from '../../store'

const navItems = [
  { path: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { path: '/watchlist', icon: Eye, label: 'Watchlist' },
  { path: '/positions', icon: TrendingUp, label: 'Positions' },
  { path: '/orders', icon: FileText, label: 'Orders' },
  { path: '/bots', icon: Bot, label: 'Algo Bots' },
  { path: '/strategies', icon: Cog, label: 'Strategies' },
  { path: '/trades', icon: History, label: 'Trade History' },
  { path: '/funds', icon: Wallet, label: 'Funds' },
  { path: '/notifications', icon: Bell, label: 'Notifications' },
  { path: '/settings', icon: Settings, label: 'Settings' },
]

export function Sidebar() {
  const location = useLocation()
  const { sidebarCollapsed, toggleSidebarCollapse } = useUIStore()

  return (
    <motion.aside
      initial={false}
      animate={{ width: sidebarCollapsed ? 72 : 240 }}
      className="fixed left-0 top-0 h-screen bg-[#0D1117] border-r border-[#21262D] z-40 flex flex-col"
    >
      <div className="h-16 flex items-center justify-between px-3 border-b border-[#21262D]">
        {!sidebarCollapsed && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex items-center gap-2"
          >
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#238636] to-[#2EA043] flex items-center justify-center">
              <TrendingUp className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-white text-lg">TradeAI</span>
          </motion.div>
        )}
        <button
          onClick={toggleSidebarCollapse}
          className="p-1.5 rounded-md hover:bg-[#21262D] text-[#8B949E] hover:text-white transition-colors"
        >
          {sidebarCollapsed ? (
            <ChevronRight className="w-5 h-5" />
          ) : (
            <ChevronLeft className="w-5 h-5" />
          )}
        </button>
      </div>

      <nav className="flex-1 py-4 px-2 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const isActive = location.pathname === item.path || 
            (item.path !== '/dashboard' && location.pathname.startsWith(item.path))

          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={clsx(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200',
                isActive
                  ? 'bg-[#238636]/10 text-[#3FB950] border border-[#238636]/20'
                  : 'text-[#8B949E] hover:text-white hover:bg-[#21262D]'
              )}
            >
              <item.icon className={clsx('w-5 h-5 flex-shrink-0', isActive && 'text-[#3FB950]')} />
              <AnimatePresence>
                {!sidebarCollapsed && (
                  <motion.span
                    initial={{ opacity: 0, width: 0 }}
                    animate={{ opacity: 1, width: 'auto' }}
                    exit={{ opacity: 0, width: 0 }}
                    className="text-sm font-medium whitespace-nowrap overflow-hidden"
                  >
                    {item.label}
                  </motion.span>
                )}
              </AnimatePresence>
            </NavLink>
          )
        })}
      </nav>

      <div className="p-4 border-t border-[#21262D]">
        {!sidebarCollapsed && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-xs text-[#8B949E] text-center"
          >
            v2.0 • NSE Live
          </motion.div>
        )}
      </div>
    </motion.aside>
  )
}