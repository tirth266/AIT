import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  Save,
  Link,
  Unlink,
  Shield,
  Bell,
  TrendingUp,
  Key,
  CheckCircle,
  XCircle,
  AlertTriangle,
} from 'lucide-react'
import { clsx } from 'clsx'
import { Card, CardHeader, CardTitle, Button, Input, Select, Badge } from '../components/ui'
import { mockSettings } from '../services/mockData'

export function SettingsPage() {
  const [settings, setSettings] = useState(mockSettings)
  const [saved, setSaved] = useState(false)

  const handleSave = () => {
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  const brokers = [
    { name: 'Binance', id: 'binance', icon: '📊' },
    { name: 'Zerodha', id: 'zerodha', icon: '📈' },
    { name: 'Upstox', id: 'upstox', icon: '💹' },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text">Settings</h1>
          <p className="text-textMuted">Configure your trading platform</p>
        </div>
        <Button onClick={handleSave}>
          <Save className="w-4 h-4 mr-2" />
          {saved ? 'Saved!' : 'Save Changes'}
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Broker Connections</CardTitle>
            </CardHeader>
            <div className="space-y-4">
              {brokers.map((broker) => {
                const isConnected = settings.brokers[broker.id as keyof typeof settings.brokers]?.is_connected

                return (
                  <div key={broker.id} className="flex items-center justify-between p-4 bg-background rounded-lg">
                    <div className="flex items-center gap-3">
                      <span className="text-2xl">{broker.icon}</span>
                      <div>
                        <p className="font-medium text-text">{broker.name}</p>
                        {isConnected && (
                          <p className="text-xs text-success flex items-center gap-1">
                            <CheckCircle className="w-3 h-3" /> Connected
                          </p>
                        )}
                      </div>
                    </div>
                    {isConnected ? (
                      <div className="flex items-center gap-3">
                        <Badge variant="success">Connected</Badge>
                        {settings.brokers[broker.id as keyof typeof settings.brokers]?.testnet_enabled && (
                          <Badge variant="primary" size="sm">Testnet</Badge>
                        )}
                        <Button variant="ghost" size="sm">
                          <Unlink className="w-4 h-4" />
                        </Button>
                      </div>
                    ) : (
                      <Button variant="outline" size="sm">
                        <Link className="w-4 h-4 mr-2" />
                        Connect
                      </Button>
                    )}
                  </div>
                )
              })}
            </div>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Risk Defaults</CardTitle>
            </CardHeader>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <Input
                  label="Max Daily Loss (%)"
                  type="number"
                  value={settings.risk_defaults.max_daily_loss_percent}
                  onChange={(e) => setSettings({
                    ...settings,
                    risk_defaults: { ...settings.risk_defaults, max_daily_loss_percent: Number(e.target.value) }
                  })}
                />
                <Input
                  label="Risk Per Trade (%)"
                  type="number"
                  value={settings.risk_defaults.risk_per_trade_percent}
                  onChange={(e) => setSettings({
                    ...settings,
                    risk_defaults: { ...settings.risk_defaults, risk_per_trade_percent: Number(e.target.value) }
                  })}
                />
                <Input
                  label="Max Open Positions"
                  type="number"
                  value={settings.risk_defaults.max_open_positions}
                  onChange={(e) => setSettings({
                    ...settings,
                    risk_defaults: { ...settings.risk_defaults, max_open_positions: Number(e.target.value) }
                  })}
                />
                <Input
                  label="Trade Cooldown (min)"
                  type="number"
                  value={settings.risk_defaults.trade_cooldown_minutes}
                  onChange={(e) => setSettings({
                    ...settings,
                    risk_defaults: { ...settings.risk_defaults, trade_cooldown_minutes: Number(e.target.value) }
                  })}
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <Input
                  label="Max Consecutive Losses"
                  type="number"
                  value={settings.risk_defaults.max_consecutive_losses}
                  onChange={(e) => setSettings({
                    ...settings,
                    risk_defaults: { ...settings.risk_defaults, max_consecutive_losses: Number(e.target.value) }
                  })}
                />
                <Input
                  label="Max Drawdown (%)"
                  type="number"
                  value={settings.risk_defaults.max_drawdown_percent}
                  onChange={(e) => setSettings({
                    ...settings,
                    risk_defaults: { ...settings.risk_defaults, max_drawdown_percent: Number(e.target.value) }
                  })}
                />
              </div>
            </div>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Notifications</CardTitle>
            </CardHeader>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Bell className="w-5 h-5 text-textMuted" />
                  <div>
                    <p className="font-medium text-text">Telegram Alerts</p>
                    <p className="text-sm text-textMuted">Receive alerts via Telegram</p>
                  </div>
                </div>
                <button
                  onClick={() => setSettings({ ...settings, telegram_enabled: !settings.telegram_enabled })}
                  className={clsx(
                    'w-12 h-6 rounded-full transition-colors',
                    settings.telegram_enabled ? 'bg-primary' : 'bg-surfaceHover'
                  )}
                >
                  <div className={clsx(
                    'w-5 h-5 bg-white rounded-full shadow transition-transform',
                    settings.telegram_enabled ? 'translate-x-6' : 'translate-x-0.5'
                  )} />
                </button>
              </div>

              {settings.telegram_enabled && (
                <div className="space-y-3 pl-8">
                  <Input
                    label="Bot Token"
                    value="••••••••••••••••"
                    disabled
                  />
                  <Input
                    label="Chat ID"
                    value={settings.telegram_chat_id}
                    disabled
                  />
                </div>
              )}

              <div className="space-y-3 pt-4 border-t border-border">
                {Object.entries(settings.notifications).map(([key, value]) => (
                  <div key={key} className="flex items-center justify-between">
                    <span className="text-textMuted capitalize">
                      {key.replace('_', ' ')}
                    </span>
                    <button
                      onClick={() => setSettings({
                        ...settings,
                        notifications: { ...settings.notifications, [key]: !value }
                      })}
                      className={clsx(
                        'w-10 h-5 rounded-full transition-colors',
                        value ? 'bg-success' : 'bg-surfaceHover'
                      )}
                    >
                      <div className={clsx(
                        'w-4 h-4 bg-white rounded-full shadow transition-transform',
                        value ? 'translate-x-5' : 'translate-x-0.5'
                      )} />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Trading Preferences</CardTitle>
            </CardHeader>
            <div className="space-y-4">
              <Select
                label="Default Mode"
                value={settings.default_mode}
                onChange={(e) => setSettings({ ...settings, default_mode: e.target.value })}
                options={[
                  { value: 'paper', label: 'Paper Trading' },
                  { value: 'live', label: 'Live Trading' },
                ]}
              />
              <Select
                label="Timezone"
                value={settings.timezone}
                onChange={(e) => setSettings({ ...settings, timezone: e.target.value })}
                options={[
                  { value: 'UTC', label: 'UTC' },
                  { value: 'Asia/Kolkata', label: 'Asia/Kolkata (IST)' },
                  { value: 'America/New_York', label: 'America/New_York (EST)' },
                ]}
              />
            </div>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Security</CardTitle>
            </CardHeader>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Shield className="w-5 h-5 text-textMuted" />
                  <div>
                    <p className="font-medium text-text">Two-Factor Authentication</p>
                    <p className="text-sm text-textMuted">Add an extra layer of security</p>
                  </div>
                </div>
                <Badge variant={false ? 'success' : 'warning'}>
                  {false ? 'Enabled' : 'Disabled'}
                </Badge>
              </div>
              <Button variant="outline" className="w-full">
                <Key className="w-4 h-4 mr-2" />
                {false ? 'Disable 2FA' : 'Enable 2FA'}
              </Button>
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}