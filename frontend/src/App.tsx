import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { LoginPage } from './pages/LoginPage';
import DashboardPage from './pages/Dashboard';
import { MarketPage } from './pages/Market';
import { NotificationsPage } from './pages/Notifications';
import { SettingsPage } from './pages/Settings';
import { StrategiesPage } from './pages/Strategies';
import { StrategyEditorPage } from './pages/StrategyEditor';
import { TradesPage } from './pages/Trades';
import { WalletPage } from './pages/Wallet';
import { BotsPage } from './pages/Bots';
import { BacktestPage } from './pages/Backtest';
import { LogsPage } from './pages/Logs';

function App() {
  return (
    <div className="App font-sans antialiased">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LoginPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/market" element={<MarketPage />} />
          <Route path="/notifications" element={<NotificationsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/strategies" element={<StrategiesPage />} />
          <Route path="/strategies/new" element={<StrategyEditorPage />} />
          <Route path="/strategies/:strategyId" element={<StrategyEditorPage />} />
          <Route path="/trades" element={<TradesPage />} />
          <Route path="/wallet" element={<WalletPage />} />
          <Route path="/bots" element={<BotsPage />} />
          <Route path="/backtest" element={<BacktestPage />} />
          <Route path="/logs" element={<LogsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;
