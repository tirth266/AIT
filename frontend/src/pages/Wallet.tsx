import { motion } from 'framer-motion'
import {
  Wallet,
  ArrowUpRight,
  ArrowDownLeft,
  TrendingUp,
  TrendingDown,
  RefreshCw,
  CreditCard,
  Building,
} from 'lucide-react'
import { clsx } from 'clsx'
import { useAuthStore } from '../store'
import { Card, CardHeader, CardTitle, Button, Badge } from '../components/ui'

export function WalletPage() {
  const { mode } = useAuthStore()

  const paperBalance = {
    total: 10250.00,
    available: 9850.00,
    used: 400.00,
    unrealized_pnl: 150.50,
  }

  const liveBalance = {
    total: 5000.00,
    available: 4500.00,
    used: 500.00,
    unrealized_pnl: -50.25,
  }

  const currentBalance = mode === 'paper' ? paperBalance : liveBalance

  const transactions = [
    { _id: 'tx_001', type: 'deposit', amount: 1000, description: 'Added funds', date: '2024-01-15T10:00:00Z' },
    { _id: 'tx_002', type: 'trade', amount: -15.50, description: 'Trade P&L', date: '2024-01-15T09:30:00Z' },
    { _id: 'tx_003', type: 'trade', amount: 25.00, description: 'Trade P&L', date: '2024-01-14T16:00:00Z' },
    { _id: 'tx_004', type: 'withdrawal', amount: -500, description: 'Withdrawal', date: '2024-01-14T10:00:00Z' },
    { _id: 'tx_005', type: 'deposit', amount: 5000, description: 'Initial deposit', date: '2024-01-10T08:00:00Z' },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text">Wallet</h1>
          <p className="text-textMuted">Manage your trading account balance</p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant={mode === 'paper' ? 'primary' : 'success'}>
            {mode.toUpperCase()} MODE
          </Badge>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0 }}
        >
          <Card className="bg-gradient-to-br from-primary/20 to-cyan-400/20 border-primary/30">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-3 bg-primary/20 rounded-lg">
                <Wallet className="w-6 h-6 text-primary" />
              </div>
              <div>
                <p className="text-sm text-textMuted">Total Balance</p>
                <p className="text-3xl font-bold text-text">${currentBalance.total.toLocaleString()}</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant={currentBalance.unrealized_pnl >= 0 ? 'success' : 'danger'}>
                {currentBalance.unrealized_pnl >= 0 ? '+' : ''}${currentBalance.unrealized_pnl.toFixed(2)} unrealized
              </Badge>
            </div>
          </Card>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          <Card>
            <p className="text-sm text-textMuted mb-2">Available</p>
            <p className="text-2xl font-bold text-text">${currentBalance.available.toLocaleString()}</p>
            <p className="text-xs text-textMuted mt-1">For trading</p>
          </Card>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <Card>
            <p className="text-sm text-textMuted mb-2">Used</p>
            <p className="text-2xl font-bold text-text">${currentBalance.used.toLocaleString()}</p>
            <p className="text-xs text-textMuted mt-1">In positions</p>
          </Card>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          <Card>
            <p className="text-sm text-textMuted mb-2">Total P&L</p>
            <p className={clsx(
              'text-2xl font-bold',
              currentBalance.unrealized_pnl >= 0 ? 'text-success' : 'text-danger'
            )}>
              {currentBalance.unrealized_pnl >= 0 ? '+' : ''}${currentBalance.unrealized_pnl.toFixed(2)}
            </p>
            <p className="text-xs text-textMuted mt-1">All time</p>
          </Card>
        </motion.div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Quick Actions</CardTitle>
          </CardHeader>
          <div className="grid grid-cols-2 gap-4">
            <Button variant="outline" className="h-20 flex-col">
              <ArrowUpRight className="w-5 h-5 mb-2" />
              <span>Deposit</span>
            </Button>
            <Button variant="outline" className="h-20 flex-col">
              <ArrowDownLeft className="w-5 h-5 mb-2" />
              <span>Withdraw</span>
            </Button>
            <Button variant="outline" className="h-20 flex-col">
              <RefreshCw className="w-5 h-5 mb-2" />
              <span>Transfer</span>
            </Button>
            <Button variant="outline" className="h-20 flex-col">
              <CreditCard className="w-5 h-5 mb-2" />
              <span>History</span>
            </Button>
          </div>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Broker Accounts</CardTitle>
          </CardHeader>
          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 bg-background rounded-lg">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-yellow-400/20 rounded-lg">
                  <Building className="w-5 h-5 text-yellow-400" />
                </div>
                <div>
                  <p className="font-medium text-text">Binance</p>
                  <p className="text-sm text-textMuted">Connected (Testnet)</p>
                </div>
              </div>
              <Badge variant="success">Active</Badge>
            </div>
            <div className="flex items-center justify-between p-4 bg-background rounded-lg">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-purple-400/20 rounded-lg">
                  <Building className="w-5 h-5 text-purple-400" />
                </div>
                <div>
                  <p className="font-medium text-text">Zerodha</p>
                  <p className="text-sm text-textMuted">Not connected</p>
                </div>
              </div>
              <Button variant="ghost" size="sm">Connect</Button>
            </div>
          </div>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Recent Transactions</CardTitle>
        </CardHeader>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left py-3 px-4 text-sm font-medium text-textMuted">Date</th>
                <th className="text-left py-3 px-4 text-sm font-medium text-textMuted">Type</th>
                <th className="text-left py-3 px-4 text-sm font-medium text-textMuted">Description</th>
                <th className="text-right py-3 px-4 text-sm font-medium text-textMuted">Amount</th>
              </tr>
            </thead>
            <tbody>
              {transactions.map((tx, index) => (
                <motion.tr
                  key={tx._id}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: index * 0.05 }}
                  className="border-b border-border hover:bg-surfaceHover/50"
                >
                  <td className="py-4 px-4 text-textMuted">
                    {new Date(tx.date).toLocaleDateString()}
                  </td>
                  <td className="py-4 px-4">
                    <div className="flex items-center gap-2">
                      {tx.type === 'deposit' || (tx.type === 'trade' && tx.amount > 0) ? (
                        <ArrowUpRight className="w-4 h-4 text-success" />
                      ) : (
                        <ArrowDownLeft className="w-4 h-4 text-danger" />
                      )}
                      <span className="capitalize text-text">{tx.type}</span>
                    </div>
                  </td>
                  <td className="py-4 px-4 text-text">{tx.description}</td>
                  <td className={clsx(
                    'py-4 px-4 text-right font-medium',
                    tx.amount >= 0 ? 'text-success' : 'text-danger'
                  )}>
                    {tx.amount >= 0 ? '+' : ''}${tx.amount.toLocaleString()}
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}