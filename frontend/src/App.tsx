import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { useEffect, useRef, useState, createContext, useContext } from 'react'
import { useAuthStore } from './store/auth'
import { AuthProvider } from './auth/auth.provider'
import { AppLayout } from './components/layout/AppLayout'
import { LoginPage } from './pages/Login'
import { RegisterPage } from './pages/Register'
import { DashboardPage } from './pages/Dashboard'
import { StrategiesPage } from './pages/Strategies'
import { StrategyEditorPage } from './pages/StrategyEditor'
import { BotsPage } from './pages/Bots'
import { TradesPage } from './pages/Trades'
import { BacktestPage } from './pages/Backtest'
import { SettingsPage } from './pages/Settings'
import { LogsPage } from './pages/Logs'
import { MarketPage } from './pages/Market'
import { WalletPage } from './pages/Wallet'
import { NotificationsPage } from './pages/Notifications'
import { useWebSocket } from './hooks'
import { ErrorBoundary } from './components/ui/ErrorBoundary'
import { SafeSuspense } from './components/ui/SafeSuspense'

interface ProtectedRouteProps {
  children: React.ReactNode
}

const LoadingContext = createContext<{
  setGlobalLoading: (loading: boolean) => void
}>({
  setGlobalLoading: () => {},
})

export const useGlobalLoading = () => useContext(LoadingContext)

function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { isAuthenticated } = useAuthStore()
  const location = useLocation()
  const [isVerifying, setIsVerifying] = useState(true)
  const verifyToken = useAuthStore((state) => state.verifyToken)
  const initialized = useRef(false)

  useEffect(() => {
    if (!initialized.current) {
      initialized.current = true
      verifyToken().finally(() => setIsVerifying(false))
    }
  }, [verifyToken])

  if (isVerifying) {
    return (
      <div className="min-h-screen bg-[#0D1117] flex items-center justify-center">
        <div className="animate-pulse flex flex-col items-center gap-4">
          <div className="w-12 h-12 rounded-full bg-[#238636]/20" />
          <p className="text-[#8B949E]">Verifying session...</p>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />
  }

  return <>{children}</>
}

function PublicRoute({ children }: ProtectedRouteProps) {
  const { isAuthenticated } = useAuthStore()
  const location = useLocation()
  const from = (location.state as { from?: string })?.from || '/dashboard'

  if (isAuthenticated) {
    return <Navigate to={from} replace />
  }

  return <>{children}</>
}

function AppContent() {
  useWebSocket()
  
  return (
    <SafeSuspense>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/watchlist" element={<MarketPage />} />
        <Route path="/positions" element={<TradesPage />} />
        <Route path="/orders" element={<TradesPage />} />
        <Route path="/funds" element={<WalletPage />} />
        <Route path="/strategies" element={<StrategiesPage />} />
        <Route path="/strategies/new" element={<StrategyEditorPage />} />
        <Route path="/strategies/:id" element={<StrategyEditorPage />} />
        <Route path="/bots" element={<BotsPage />} />
        <Route path="/trades" element={<TradesPage />} />
        <Route path="/backtest" element={<BacktestPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/logs" element={<LogsPage />} />
        <Route path="/market" element={<MarketPage />} />
        <Route path="/wallet" element={<WalletPage />} />
        <Route path="/notifications" element={<NotificationsPage />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </SafeSuspense>
  )
}

function AppLayoutWithSuspense() {
  return (
    <ErrorBoundary
      fallback={
        <div className="min-h-screen bg-[#0D1117] flex items-center justify-center">
          <div className="text-center">
            <h1 className="text-2xl font-bold text-white mb-2">Something went wrong</h1>
            <p className="text-[#8B949E] mb-4">The application encountered an error</p>
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 bg-[#238636] text-white rounded-md hover:bg-[#2EA043] transition-colors"
            >
              Reload Page
            </button>
          </div>
        </div>
      }
    >
      <AppLayout>
        <AppContent />
      </AppLayout>
    </ErrorBoundary>
  )
}

function App() {
  return (
    <ErrorBoundary
      fallback={
        <div className="min-h-screen bg-[#0D1117] flex items-center justify-center p-4">
          <div className="max-w-lg w-full bg-[#161B22] border border-[#30363D] rounded-lg p-6 text-center">
            <h1 className="text-2xl font-bold text-white mb-2">Application Error</h1>
            <p className="text-[#8B949E] mb-4">
              The application failed to initialize. Please try refreshing the page.
            </p>
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 bg-[#238636] text-white rounded-md hover:bg-[#2EA043] transition-colors"
            >
              Reload Page
            </button>
          </div>
        </div>
      }
    >
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route
              path="/login"
              element={
                <PublicRoute>
                  <LoginPage />
                </PublicRoute>
              }
            />
            <Route
              path="/register"
              element={
                <PublicRoute>
                  <RegisterPage />
                </PublicRoute>
              }
            />
            <Route
              path="/*"
              element={
                <ProtectedRoute>
                  <AppLayoutWithSuspense />
                </ProtectedRoute>
              }
            />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </ErrorBoundary>
  )
}

export default App