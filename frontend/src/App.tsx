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

import { ProtectedRoute } from './components/ProtectedRoute';

function App() {
  console.log('[App] Rendering App');
  return (
    <div className="App font-sans antialiased">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LoginPage />} />
          <Route 
            path="/dashboard" 
            element={
              <ProtectedRoute>
                <DashboardPage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/market" 
            element={
              <ProtectedRoute>
                <MarketPage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/notifications" 
            element={
              <ProtectedRoute>
                <NotificationsPage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/settings" 
            element={
              <ProtectedRoute>
                <SettingsPage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/strategies" 
            element={
              <ProtectedRoute>
                <StrategiesPage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/strategies/new" 
            element={
              <ProtectedRoute>
                <StrategyEditorPage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/strategies/:strategyId" 
            element={
              <ProtectedRoute>
                <StrategyEditorPage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/trades" 
            element={
              <ProtectedRoute>
                <TradesPage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/wallet" 
            element={
              <ProtectedRoute>
                <WalletPage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/bots" 
            element={
              <ProtectedRoute>
                <BotsPage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/backtest" 
            element={
              <ProtectedRoute>
                <BacktestPage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/logs" 
            element={
              <ProtectedRoute>
                <LogsPage />
              </ProtectedRoute>
            } 
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;
