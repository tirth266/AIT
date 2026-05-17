# PRODUCT REQUIREMENT DOCUMENT (PRD)
## Automated Indicator-Based Personal Trading Platform
**Version:** 1.1 (Improved)
**Document Type:** Personal Use Trading Platform
**Tech Stack:** React (Frontend) + Flask (Backend) + MongoDB (Database) + Redis + Celery
**Deployment:** Render (Backend) + Vercel (Frontend)

---

## TABLE OF CONTENTS
1. [Project Overview](#1-project-overview)
2. [Goals & Objectives](#2-goals--objectives)
3. [User Role](#3-user-role)
4. [Features List](#4-features-list)
5. [User Flow Document](#5-user-flow-document)
6. [Trading Logic Document](#6-trading-logic-document)
7. [Risk Management Document](#7-risk-management-document)
8. [Technical Architecture Document](#8-technical-architecture-document)
9. [API Documentation](#9-api-documentation)
10. [UI/UX Wireframe Document](#10-uiux-wireframe-document)
11. [Database Schema Document](#11-database-schema-document)
12. [DevOps / Deployment Document](#12-devops--deployment-document-render--vercel)
13. [Security Document](#13-security-document)
14. [Testing Document](#14-testing-document)
15. [Celery Task Architecture](#15-celery-task-architecture)
16. [WebSocket Protocol](#16-websocket-protocol)
17. [Paper Trading System](#17-paper-trading-system)
18. [Backtesting Engine](#18-backtesting-engine)
19. [Broker Integration Details](#19-broker-integration-details)
20. [Error Handling & Recovery](#20-error-handling--recovery)
21. [Backup & Disaster Recovery](#21-backup--disaster-recovery)
22. [Future Scope](#22-future-scope)
23. [Recommended Folder Structure](#recommended-folder-structure)
24. [Development Phases](#development-phases)
25. [Tools Used](#tools-used)

---

## 1. PROJECT OVERVIEW

### Platform Name
Personal Automated Trading Platform (PATP)

### Simple Description
An automated trading platform built for personal use only, where the owner can create indicator-based strategies, backtest them on historical data, receive real-time signals, and execute trades automatically through connected broker APIs.

### Problem Statement
Manual trading is time-consuming, emotionally driven, and prone to human error. Traders often miss opportunities due to delayed execution, lack of discipline, or inability to monitor charts 24/7. A personal automated system eliminates these issues by executing predefined strategies with precision.

### Why This Platform Exists
- To automate personal trading strategies without depending on third-party SaaS tools
- To maintain full control over trading logic and broker credentials
- To remove emotional decision-making from trades
- To run backtests before deploying real capital
- To monitor live PnL and risk in a single dashboard

### Main Objective
Build a single-user, secure, fully automated trading system that connects to broker APIs, executes indicator-based strategies, manages risk automatically, and provides real-time alerts and reporting.

---

## 2. GOALS & OBJECTIVES

| Goal | Description |
|------|-------------|
| Auto Trading | Execute trades automatically based on strategy signals |
| Indicator Strategies | Build strategies using RSI, EMA, MACD, Bollinger Bands, etc. |
| Multi Broker Support | Zerodha, Binance, Upstox integration |
| Backtesting | Test strategies on historical data before going live |
| Paper Trading | Test strategies with simulated money before real capital |
| Live Trading | Execute real trades with real money |
| Risk Management | SL, TP, trailing stop, max daily loss limit |
| Real-time Alerts | Telegram and web push notifications |
| Personal Dashboard | View PnL, active trades, running bots in one place |
| Secure Access | Single-owner JWT authentication, no public signup |

---

## 3. USER ROLE

### Single Personal User (Owner Only)
This platform is designed for only one authorized user — the owner.

#### Capabilities
- Login securely with master credentials
- Connect broker APIs (Zerodha, Binance, Upstox)
- Create and manage trading strategies
- Switch between Paper Trading and Live Trading modes
- Start/stop trading bots
- View live trades, PnL, and portfolio
- Configure risk management rules
- View logs, trade history, and reports
- Receive Telegram and push notifications
- Run backtesting on historical data
- Access Control:
  - Only one master account exists in the system
  - No public signup/register page
  - Access is restricted through secure JWT authentication
  - Credentials stored as environment variables (not in DB signup flow)
  - Optional 2FA for added security

#### Removed Features (Not Required)
- ❌ Public signup / registration
- ❌ User management
- ❌ Subscription plans
- ❌ Admin panel
- ❌ Role-based permissions
- ❌ Multi-tenant database
- ❌ Email notifications (replaced with Telegram + Push)

---

## 4. FEATURES LIST

### 4.1 Authentication
- Single owner login (environment variable credentials)
- JWT-based session management
- Forgot password (via secure recovery key)
- Optional 2FA (TOTP)
- Auto logout on inactivity (configurable timeout)

### 4.2 Dashboard
- Account balance (fetched from broker)
- Active trades panel
- Live PnL chart
- Running bots status
- Daily/weekly/monthly performance summary
- Mode indicator (Paper Trading vs Live Trading)

### 4.3 Strategy Builder
- Select indicators (RSI, EMA, MACD, Bollinger Bands, VWAP, Supertrend, ATR, Stochastic)
- Define entry conditions (AND/OR logic)
- Define exit conditions (AND/OR logic)
- Set timeframe (1m, 5m, 15m, 30m, 1h, 4h, 1d)
- Save and edit strategies
- Clone existing strategies
- Test strategies against historical data

### 4.4 Trading Engine
- Real-time candle fetching via WebSocket
- Indicator calculation (TA-Lib / pandas-ta)
- Signal generation based on conditions
- Order execution (market/limit)
- Position management
- Stop loss & target tracking
- Trailing stop implementation
- Auto-exit on signal reversal

### 4.5 Broker Integration
- **Zerodha** (Kite Connect API v3)
- **Binance** (Spot & Futures API - Testnet & Live)
- **Upstox** API
- Secure token storage (encrypted at rest)
- Connection health monitoring
- Automatic reconnection on failure

### 4.6 Trading Modes
- **Paper Trading**: Simulated trades with fake money
- **Live Trading**: Real money trades via broker API

### 4.7 Notifications
- Telegram bot alerts (trade entry, exit, errors)
- Web push notifications
- In-app notification panel
- Alert customization per event type

### 4.8 Backtesting
- Fetch historical data (broker API / CSV upload)
- Run strategy on past candles
- Performance report:
  - Win rate
  - Average profit/loss
  - Maximum drawdown
  - Total trades
  - Sharpe ratio
  - Profit factor
  - Recovery factor

### 4.9 Logs & Reports
- Trade logs (entry, exit, modifications)
- Error logs with stack traces
- Strategy execution logs
- Performance analytics
- Downloadable CSV reports (trades, backtests)

---

## 5. USER FLOW DOCUMENT

### Login Flow
1. User opens website
2. Enters master credentials (stored in environment variables)
3. System validates credentials against env vars + bcrypt
4. (Optional) Enters 2FA code if enabled
5. JWT token issued with 1-hour expiry
6. Redirected to Dashboard

### Strategy Creation Flow
1. Click "Create Strategy"
2. Enter strategy name
3. Select trading mode (Paper/Live)
4. Select broker and symbol
5. Select timeframe
6. Select indicators (e.g., RSI, EMA)
7. Set entry conditions (e.g., Buy when RSI < 30 AND EMA9 crosses above EMA21)
8. Set exit conditions (e.g., Sell when RSI > 70)
9. Configure risk settings (SL %, TP %, position size, trailing SL)
10. Click "Save Strategy"
11. Optionally run backtest to validate

### Bot Activation Flow (Paper Trading)
1. Open saved strategy
2. Click "Start Paper Trading Bot"
3. Backend trading engine begins monitoring market (simulated)
4. Signal generated → Paper trade executed → Notification sent
5. Results tracked separately from live trading

### Bot Activation Flow (Live Trading)
1. Open saved strategy
2. Click "Connect Broker" (if not connected)
3. Authorize broker API (enter API key/secret)
4. System validates broker connection
5. Click "Start Live Trading Bot"
6. Backend trading engine begins monitoring market
7. Risk checks run before each trade
8. Signal generated → Trade executed → Notification sent

### Trade Monitoring Flow
1. Open Dashboard
2. Toggle between Paper/Live view
3. View active trades
4. View live PnL (realized + unrealized)
5. Receive Telegram alerts on entry/exit
6. Stop bot anytime with "Stop Bot" button

### Backtesting Flow
1. Navigate to Backtest page
2. Select strategy
3. Select symbol and timeframe
4. Set date range (start, end)
5. Click "Run Backtest"
6. Celery task executes in background
7. Progress shown in UI
8. Results displayed with charts and metrics

---

## 6. TRADING LOGIC DOCUMENT

### Supported Indicators
| Indicator | Parameters | Calculation |
|-----------|------------|-------------|
| RSI | period (default 14), overbought (70), oversold (30) | Relative Strength Index |
| EMA | period (e.g., 9, 21, 50, 200) | Exponential Moving Average |
| SMA | period | Simple Moving Average |
| MACD | fast, slow, signal | MACD Line, Signal Line, Histogram |
| Bollinger Bands | period, std_dev (default 2) | Upper, Middle, Lower bands |
| VWAP | period | Volume Weighted Average Price |
| Supertrend | period, multiplier | Trend direction + ATR-based bands |
| ATR | period (default 14) | Average True Range |
| Stochastic | k_period, d_period | %K and %D lines |

### Buy Conditions (Example Strategy)
```
RSI < 30
AND EMA9 crosses above EMA21
AND Volume > 20-day average volume
```

### Sell Conditions (Example Strategy)
```
RSI > 70
OR EMA9 crosses below EMA21
OR Price hits trailing stop
```

### Order Execution Logic

**Entry Orders:**
- **Market order**: Instant execution at current price
- **Limit order**: Execute when price reaches specified level

**Exit Orders:**
- **Stop Loss (SL)**: Exit when price moves against position by X%
- **Take Profit (TP)**: Exit when price moves in favor by X%
- **Trailing Stop Loss**: Dynamic SL that moves with price
- **Signal-based exit**: Exit when exit conditions met

### Risk Controls
- Max 2% capital risk per trade
- Max 5 trades per day
- Cooldown after each trade (configurable, default 5 mins)
- Max concurrent open positions: 3
- Circuit breaker after 3 consecutive losses (auto-pause bot)

### Candle Handling
- Real-time candles fetched via broker WebSocket
- Stored in MongoDB for analysis (with TTL - 30 days for intraday)
- Indicator values recalculated on every new candle close
- Partial candle updates for real-time indicators

---

## 7. RISK MANAGEMENT DOCUMENT

### Risk Rules

| Rule | Value | Configurable |
|------|-------|--------------|
| Max Daily Loss | 5% of capital | Yes |
| Risk Per Trade | 1% of capital | Yes |
| Max Open Trades | 3 | Yes |
| Auto Stop Trading | After 3 consecutive losses | Yes |
| Mandatory SL | Yes (every trade must have SL) | No |
| Trade Cooldown | 5 minutes between trades | Yes |
| Max Drawdown | 10% (auto pause bot) | Yes |

### Position Sizing Formula
```
Position Size = (Capital × Risk%) / (Entry Price - Stop Loss Price)
```

### Circuit Breaker Rules
1. **Consecutive Loss Circuit**: Pause bot after 3 consecutive losing trades
2. **Daily Loss Circuit**: Stop trading when daily loss exceeds threshold
3. **Drawdown Circuit**: Pause bot when total drawdown exceeds 10%
4. **Manual Override**: User can always override and restart

### Risk Check Order (Before Trade Execution)
1. Check if bot is active
2. Check if trading is allowed (not paused by circuit)
3. Check max daily loss not exceeded
4. Check max open positions not exceeded
5. Check cooldown period elapsed
6. Check sufficient capital available
7. Check broker connection healthy
8. Execute trade if all checks pass

### Broker-Specific Risk
- **Zerodha**: Check margin available, segment permissions
- **Binance**: Check wallet balance, position limits
- **Upstox**: Check margin, exposure limits

---

## 8. TECHNICAL ARCHITECTURE DOCUMENT

### 8.1 Frontend Architecture

**Stack:**
- React 18+ with Vite
- Zustand (state management - lighter than Redux)
- Tailwind CSS
- Recharts for charts / TradingView Lightweight Charts
- Axios (API calls)
- Socket.IO Client (WebSocket)

**Pages:**
- Login
- Dashboard (Paper/Live toggle)
- Strategy Builder
- Active Bots
- Trade History
- Backtesting
- Settings
- Logs

**Component Structure:**
```
src/
├── components/
│   ├── layout/
│   │   ├── Sidebar.tsx
│   │   ├── Header.tsx
│   │   └── Layout.tsx
│   ├── trading/
│   │   ├── Chart.tsx
│   │   ├── OrderForm.tsx
│   │   └── PositionCard.tsx
│   ├── strategy/
│   │   ├── IndicatorSelector.tsx
│   │   ├── ConditionBuilder.tsx
│   │   └── StrategyCard.tsx
│   └── common/
│       ├── Button.tsx
│       ├── Modal.tsx
│       └── Loader.tsx
├── pages/
├── stores/ (Zustand)
├── hooks/
├── services/
│   ├── api.ts
│   └── socket.ts
└── utils/
```

### 8.2 Backend Architecture

**Stack:**
- Flask 2.x (REST API)
- Flask-SocketIO (WebSocket for real-time updates)
- Flask-CORS, Flask-Limiter
- Celery + Redis (background tasks)
- PyJWT (authentication)
- TA-Lib / pandas-ta (indicator calculations)
- python-dotenv (configuration)

**Module Structure:**
```
backend/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── config.py            # Configuration
│   ├── routes/
│   │   ├── auth.py          # Authentication endpoints
│   │   ├── strategies.py   # Strategy CRUD
│   │   ├── trades.py       # Trade management
│   │   ├── brokers.py      # Broker connection
│   │   ├── backtest.py     # Backtesting endpoints
│   │   ├── market.py       # Market data
│   │   └── websocket.py    # SocketIO events
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── trading_engine.py
│   │   ├── broker_service.py
│   │   ├── notification_service.py
│   │   ├── backtest_engine.py
│   │   ├── risk_manager.py
│   │   └── indicator_service.py
│   ├── models/
│   │   ├── strategy.py
│   │   ├── trade.py
│   │   ├── position.py
│   │   └── candle.py
│   ├── tasks/
│   │   ├── trading_tasks.py
│   │   ├── backtest_tasks.py
│   │   └── maintenance_tasks.py
│   ├── utils/
│   │   ├── indicators.py
│   │   ├── encryption.py
│   │   └── validators.py
│   └── websocket/
│       └── handlers.py
├── requirements.txt
├── celery_worker.py
├── gunicorn.conf.py
└── .env.example
```

### 8.3 Celery Architecture

**Task Categories:**
1. **Trading Tasks** - Real-time strategy evaluation
2. **Backtest Tasks** - Historical strategy testing
3. **Market Data Tasks** - Candle fetching, indicator calculation
4. **Maintenance Tasks** - Database cleanup, logs rotation

**Worker Configuration:**
- 1 worker for trading (CPU-bound for indicator calc)
- 1 worker for backtests (can be longer running)
- 1 worker for maintenance

### 8.4 Database Design

**Database:** MongoDB (MongoDB Atlas)

**Collections:**
- `user` (single document — owner)
- `strategies`
- `trades`
- `positions`
- `logs`
- `brokers`
- `notifications`
- `backtests`
- `candles`
- `settings`

**Indexes (Performance Critical):**
```javascript
// Trades
{ "symbol": 1, "created_at": -1 }
{ "strategy_id": 1, "status": 1 }

// Candles (TTL - 30 days)
{ "symbol": 1, "timeframe": 1, "timestamp": -1 }

// Strategies
{ "is_active": 1 }

// Logs
{ "level": 1, "created_at": -1 }
```

---

## 9. API DOCUMENTATION

### Base URL
```
Production: https://your-backend.onrender.com/api/v1
```

### Authentication Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/auth/login` | Owner login with credentials |
| POST | `/auth/2fa` | Verify 2FA code |
| POST | `/auth/refresh` | Refresh JWT token |
| POST | `/auth/logout` | Invalidate token |

### Strategy Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/strategies` | List all strategies |
| POST | `/strategies` | Create new strategy |
| GET | `/strategies/:id` | Get strategy details |
| PUT | `/strategies/:id` | Update strategy |
| DELETE | `/strategies/:id` | Delete strategy |
| POST | `/strategies/:id/clone` | Clone strategy |

### Trading Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/trades` | Fetch trade history |
| GET | `/trades/active` | Get active positions |
| POST | `/trades/execute` | Manual trade execution |
| POST | `/trades/:id/cancel` | Cancel pending trade |
| POST | `/trades/:id/close` | Close position |

### Bot Control Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/bot/start` | Start trading bot |
| POST | `/bot/stop` | Stop trading bot |
| GET | `/bot/status` | Get bot status |
| POST | `/bot/mode` | Switch Paper/Live mode |

### Broker Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/broker/connect` | Connect broker API |
| GET | `/broker/status` | Check broker connection |
| DELETE | `/broker/disconnect` | Disconnect broker |
| GET | `/broker/balance` | Get account balance |

### Market Data Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/market/candles` | Get OHLCV data |
| GET | `/market/price/:symbol` | Get current price |
| GET | `/market/symbols` | List available symbols |

### Backtest Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/backtest/run` | Run backtest (async) |
| GET | `/backtest/:id` | Get backtest status |
| GET | `/backtest/:id/results` | Get backtest results |
| GET | `/backtest/history` | List past backtests |

### Other Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/dashboard` | Get dashboard data |
| GET | `/logs` | View system logs |
| GET | `/notifications` | List notifications |
| PUT | `/settings` | Update settings |

### WebSocket Events

**Client → Server:**
```json
{ "event": "subscribe", "channel": "prices", "symbols": ["BTCUSDT"] }
{ "event": "subscribe", "channel": "trades" }
{ "event": "ping" }
```

**Server → Client:**
```json
{ "event": "price", "symbol": "BTCUSDT", "price": 45000, "timestamp": 1234567890 }
{ "event": "trade", "trade": { ... } }
{ "event": "signal", "strategy_id": "...", "signal": "BUY" }
{ "event": "balance", "balance": 10000 }
{ "event": "pong" }
```

---

## 10. UI/UX WIREFRAME DOCUMENT

### Layout Structure
- **Sidebar (Left):** Dashboard, Strategies, Bots, Trades, Backtest, Logs, Settings
- **Top Bar:** Mode indicator (Paper/Live), Account balance, Bot status, Notifications icon, Logout
- **Main Content:** Page-specific content
- **Mobile View:** Hamburger menu, responsive cards

### Key Pages

**Login Page:**
- Minimal, centered form
- Logo at top
- Password field with show/hide toggle
- 2FA input (conditional)
- "Login" button

**Dashboard:**
- Mode toggle (Paper/Live) - large, prominent
- Balance card (real/paper based on mode)
- PnL chart (line chart - 7 day, 30 day, all time)
- Active positions table
- Running bots status card
- Recent notifications panel

**Strategy Builder:**
- Strategy name input
- Symbol/timeframe selectors
- Indicator section (add multiple):
  - Dropdown to select indicator
  - Input fields for parameters
  - Enable/disable toggle
- Entry conditions section:
  - Add condition button
  - Dropdown: indicator, operator, value
  - AND/OR group selector
- Exit conditions section: same as entry
- Risk settings section:
  - Stop loss % (input)
  - Take profit % (input)
  - Position size type (fixed/calculated)
  - Trailing stop toggle + %
- Save / Test buttons

**Bots Page:**
- List of strategies with status
- Each card shows:
  - Strategy name
  - Symbol, timeframe
  - Mode (Paper/Live)
  - Status (Running/Stopped)
  - Start/Stop toggle
  - Today's PnL

**Trade History:**
- Filter bar: Date range, symbol, mode (Paper/Live), status
- Table columns: Time, Symbol, Side, Qty, Entry, Exit, PnL, Mode
- Pagination
- Export CSV button

**Backtest Page:**
- Strategy dropdown
- Symbol dropdown
- Timeframe dropdown
- Date range picker (start, end)
- Initial capital input
- "Run Backtest" button
- Results section:
  - Summary cards: Total return, Win rate, Sharpe, Drawdown
  - Equity curve chart
  - Drawdown chart
  - Monthly returns table
  - Trade list table

**Settings:**
- Broker connections section:
  - Add broker button
  - Form: name, API key, secret (masked)
  - Test connection button
- Risk settings section (same as strategy builder)
- Notification settings:
  - Telegram bot token input
  - Toggle: trade alerts, error alerts, daily summary
- Security:
  - Enable 2FA button
  - Change password (if applicable)
- Mode selection: Paper/Live default

**Logs Page:**
- Filter: Level (INFO, ERROR, TRADE), date range
- Table: Timestamp, Level, Message
- Auto-refresh toggle
- Export button

### Design System
- **Colors:**
  - Primary: #2563EB (Blue)
  - Success: #10B981 (Green)
  - Danger: #EF4444 (Red)
  - Warning: #F59E0B (Amber)
  - Background: #F8FAFC
  - Card: #FFFFFF
  - Text: #1E293B
- **Typography:** Inter (Google Fonts)
- **Spacing:** 4px base unit (4, 8, 12, 16, 24, 32, 48)
- **Border Radius:** 8px (cards), 6px (buttons), 4px (inputs)
- **Shadows:** `0 1px 3px rgba(0,0,0,0.1)`

---

## 11. DATABASE SCHEMA DOCUMENT

### User Collection (Single Document)
```json
{
  "_id": "ObjectId",
  "name": "Owner Name",
  "email": "owner@example.com",
  "password_hash": "bcrypt_hash",
  "twofa_secret": "encrypted_secret",
  "twofa_enabled": false,
  "created_at": "ISODate",
  "updated_at": "ISODate"
}
```

*Note: Credentials primarily stored in environment variables, this document for settings only.*

### Strategy Collection
```json
{
  "_id": "ObjectId",
  "strategy_name": "RSI EMA Combo",
  "user_id": "ObjectId (always single user)",
  "symbol": "BTCUSDT",
  "timeframe": "5m",
  "indicators": [
    {
      "name": "RSI",
      "params": { "period": 14 },
      "enabled": true
    },
    {
      "name": "EMA",
      "params": { "period": 9 },
      "enabled": true
    },
    {
      "name": "EMA",
      "params": { "period": 21 },
      "enabled": true
    }
  ],
  "entry_conditions": [
    {
      "indicator": "RSI",
      "operator": "less_than",
      "value": 30,
      "logic": "AND"
    },
    {
      "indicator": "EMA_9",
      "operator": "crosses_above",
      "value": "EMA_21",
      "logic": "AND"
    }
  ],
  "exit_conditions": [
    {
      "indicator": "RSI",
      "operator": "greater_than",
      "value": 70,
      "logic": "OR"
    },
    {
      "indicator": "EMA_9",
      "operator": "crosses_below",
      "value": "EMA_21",
      "logic": "OR"
    }
  ],
  "risk_settings": {
    "stop_loss_percent": 1.0,
    "take_profit_percent": 2.0,
    "trailing_stop_enabled": true,
    "trailing_stop_percent": 0.5,
    "position_size_type": "fixed",
    "position_size": 0.01
  },
  "broker": "binance",
  "mode": "paper",
  "is_active": false,
  "created_at": "ISODate",
  "updated_at": "ISODate"
}
```

### Trades Collection
```json
{
  "_id": "ObjectId",
  "strategy_id": "ObjectId",
  "symbol": "BTCUSDT",
  "side": "BUY",
  "entry_price": 45000.00,
  "exit_price": 45900.00,
  "quantity": 0.01,
  "entry_type": "market",
  "exit_type": "market",
  "pnl": 9.00,
  "pnl_percent": 0.2,
  "commission": 0.10,
  "status": "CLOSED",
  "mode": "paper",
  "broker": "binance",
  "stop_loss": 44550.00,
  "take_profit": 45900.00,
  "entry_time": "ISODate",
  "exit_time": "ISODate",
  "notes": "Optional notes",
  "created_at": "ISODate"
}
```

### Positions Collection (Active)
```json
{
  "_id": "ObjectId",
  "strategy_id": "ObjectId",
  "symbol": "BTCUSDT",
  "side": "BUY",
  "entry_price": 45000.00,
  "quantity": 0.01,
  "current_price": 45500.00,
  "unrealized_pnl": 5.00,
  "unrealized_pnl_percent": 0.11,
  "stop_loss": 44550.00,
  "take_profit": 45900.00,
  "mode": "paper",
  "broker": "binance",
  "opened_at": "ISODate",
  "created_at": "ISODate"
}
```

### Candles Collection (Time-series)
```json
{
  "_id": "ObjectId",
  "symbol": "BTCUSDT",
  "timeframe": "5m",
  "timestamp": "ISODate",
  "open": 45000.00,
  "high": 45500.00,
  "low": 44800.00,
  "close": 45200.00,
  "volume": 1500.5,
  "created_at": "ISODate"
}
```
*Note: Add TTL index on `created_at` with 30 days expiration for intraday data.*

### Brokers Collection
```json
{
  "_id": "ObjectId",
  "broker_name": "binance",
  "broker_type": "spot",
  "api_key_encrypted": "encrypted_string",
  "api_secret_encrypted": "encrypted_string",
  "testnet_enabled": true,
  "is_connected": true,
  "last_connected_at": "ISODate",
  "created_at": "ISODate"
}
```

### Backtests Collection
```json
{
  "_id": "ObjectId",
  "strategy_id": "ObjectId",
  "strategy_name": "RSI EMA Combo",
  "symbol": "BTCUSDT",
  "timeframe": "5m",
  "start_date": "ISODate",
  "end_date": "ISODate",
  "initial_capital": 10000.00,
  "final_capital": 12500.00,
  "total_return": 25.0,
  "total_trades": 150,
  "winning_trades": 90,
  "losing_trades": 60,
  "win_rate": 60.0,
  "sharpe_ratio": 1.5,
  "max_drawdown": 8.5,
  "profit_factor": 1.8,
  "status": "completed",
  "results_json": "detailed trade list",
  "created_at": "ISODate"
}
```

### Logs Collection
```json
{
  "_id": "ObjectId",
  "level": "INFO",
  "category": "TRADE",
  "message": "Buy signal detected for BTCUSDT",
  "metadata": { "strategy_id": "...", "price": 45000 },
  "created_at": "ISODate"
}
```

### Notifications Collection
```json
{
  "_id": "ObjectId",
  "type": "trade_entry",
  "title": "Trade Executed",
  "message": "Bought 0.01 BTCUSDT at 45000",
  "read": false,
  "created_at": "ISODate"
}
```

### Settings Collection
```json
{
  "_id": "ObjectId",
  "key": "telegram_bot_token",
  "value": "encrypted_token",
  "updated_at": "ISODate"
}
```

---

## 12. DEVOPS / DEPLOYMENT DOCUMENT

### 12.1 Local Development (Docker)

**Dockerfile (Backend)**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--worker-class", "eventlet", "-w", "1", "app:app"]
```

**Dockerfile (Frontend)**
```dockerfile
FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host"]
```

**docker-compose.yml**
```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "5000:5000"
    environment:
      - MONGO_URI=mongodb://mongo:27017/trading_db
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/1
    depends_on:
      - mongo
      - redis

  frontend:
    build: ./frontend
    ports:
      - "5173:5173"
    environment:
      - VITE_API_URL=http://localhost:5000
      - VITE_SOCKET_URL=http://localhost:5000

  mongo:
    image: mongo:7
    ports:
      - "27017:27017"
    volumes:
      - mongo_data:/data/db

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  celery:
    build: ./backend
    command: celery -A app.celery worker -l INFO
    environment:
      - MONGO_URI=mongodb://mongo:27017/trading_db
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/1
    depends_on:
      - mongo
      - redis

volumes:
  mongo_data:
```

### 12.2 Frontend Deployment — Vercel

**Steps:**
1. Push React code to GitHub
2. Connect repo to Vercel
3. Configure:
   - Framework Preset: Vite
   - Build Command: `npm run build`
   - Output Directory: `dist`
4. Set environment variables:
   - `VITE_API_URL` = `https://your-backend.onrender.com`
   - `VITE_SOCKET_URL` = `https://your-backend.onrender.com`
5. Deploy → Auto SSL + CDN included

### 12.3 Backend Deployment — Render

**Steps:**
1. Push Flask code to GitHub
2. Create new "Web Service" on Render
3. Connect repo
4. Configure:
   - Runtime: Python 3.11
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app --worker-class eventlet -w 1`
5. Add environment variables:
   - `MONGO_URI` = `mongodb+srv://...`
   - `JWT_SECRET` = `your-secret-key`
   - `REDIS_URL` = `redis://...`
   - `CELERY_BROKER_URL` = `redis://...`
   - `OWNER_PASSWORD_HASH` = `bcrypt-hash`
   - `TELEGRAM_BOT_TOKEN` = `optional`
6. Enable auto-deploy on push

**Background Worker (Celery on Render):**
1. Create new "Background Worker" on Render
2. Command: `celery -A app.celery worker -l INFO`
3. Same environment variables as web service

### 12.4 Database — MongoDB Atlas

- Free tier (M0) for personal use
- Network Access: Add Render's IP or allow 0.0.0.0/0 with strong auth
- Connection via `MONGO_URI` environment variable

### 12.5 Redis — Upstash (Free Tier)

- Create account at upstash.com
- Copy connection string
- Add to `REDIS_URL` and `CELERY_BROKER_URL`

### 12.6 SSL & Domain
- Vercel & Render provide free SSL
- Add custom domain (optional)

### 12.7 Environment Variables Reference

**Backend Required:**
```env
# Required
MONGO_URI=mongodb+srv://...
JWT_SECRET=your-super-secret-jwt-key-min-32-chars
OWNER_PASSWORD_HASH=bcrypt-hash-of-password

# Optional
REDIS_URL=redis://...
CELERY_BROKER_URL=redis://...
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
FLASK_ENV=production
LOG_LEVEL=INFO
SESSION_SECRET=another-secret-key
```

**Frontend Required:**
```env
VITE_API_URL=https://your-backend.onrender.com
VITE_SOCKET_URL=https://your-backend.onrender.com
```

---

## 13. SECURITY DOCUMENT

### Security Measures
- JWT authentication (short-lived tokens + refresh tokens)
- Bcrypt password hashing (12 rounds)
- 2FA (TOTP via Google Authenticator) - optional
- API rate limiting (Flask-Limiter)
- HTTPS only (enforced by Render/Vercel)
- Broker API keys encrypted with AES-256 (fernet)
- Environment variables for all secrets
- CORS restricted to Vercel frontend domain
- No public signup endpoint
- Input validation on all APIs
- MongoDB authentication enabled
- Request validation with marshmallow

### Broker Token Security
- Store encrypted in DB using Fernet (symmetric encryption)
- Decrypt only in memory during trade execution
- Never log API keys
- Rotate keys monthly (manual process)

### Additional Security
- CSRF protection for state-changing operations
- XSS protection headers
- SQL injection prevention (MongoDB uses BSON, no SQL)
- Rate limit per IP: 100 req/min
- Failed login lockout: 5 attempts then 15 min lockout

---

## 14. TESTING DOCUMENT

### Testing Types

| Type | Tool | Purpose |
|------|------|---------|
| Unit Testing | PyTest (backend), Vitest (frontend) | Test individual functions/components |
| API Testing | Postman / Thunder Client | Test REST endpoints |
| Strategy Testing | Custom backtest engine | Validate strategy logic |
| Integration Testing | PyTest + Mock broker APIs | Test broker integration |
| E2E Testing | Playwright | Test full user flows |

### Test Coverage Areas
- Auth flow (login, JWT, 2FA)
- Strategy CRUD operations
- Trade execution logic (paper mode first)
- Risk management triggers
- Indicator calculations accuracy
- WebSocket connections and reconnection
- Broker API integration (sandbox mode first)
- Backtest engine accuracy

### Test Environment
- Use broker testnet/sandbox for testing
- Paper trading for live strategy tests
- Mock data for indicator tests

---

## 15. CELERY TASK ARCHITECTURE

### Task Categories

**1. Trading Engine Tasks**
```python
# tasks/trading_tasks.py
@celery.task
def evaluate_strategy(strategy_id: str, symbol: str):
    """Evaluate strategy on latest candle - called every interval"""
    pass

@celery.task
def check_stop_loss_take_profit(position_id: str):
    """Monitor open positions for SL/TP triggers"""
    pass

@celery.task
def close_position(position_id: str, reason: str):
    """Close position due to signal or manual"""
    pass

@celery.task
def execute_trade(trade_data: dict):
    """Execute trade via broker API"""
    pass
```

**2. Market Data Tasks**
```python
# tasks/market_tasks.py
@celery.task
def fetch_and_store_candles(symbol: str, timeframe: str, limit: int):
    """Fetch latest candles from broker and store"""
    pass

@celery.task
def calculate_indicators(symbol: str, timeframe: str):
    """Calculate all indicators for latest candle"""
    pass
```

**3. Backtest Tasks**
```python
# tasks/backtest_tasks.py
@celery.task
def run_backtest(backtest_id: str, params: dict):
    """Run historical backtest - long running"""
    pass
```

**4. Maintenance Tasks**
```python
# tasks/maintenance_tasks.py
@celery.task
def cleanup_old_candles():
    """Delete candles older than retention period"""
    pass

@celery.task
def send_daily_summary():
    """Send daily PnL summary via Telegram"""
    pass

@celery.task
def health_check():
    """Check broker connections, database, Redis"""
    pass
```

### Celery Schedule (celery beat)
```python
# celery_config.py
beat_schedule = {
    'evaluate-strategies-every-5min': {
        'task': 'tasks.trading_tasks.evaluate_all_strategies',
        'schedule': 300.0,  # 5 minutes
    },
    'check-open-positions-every-1min': {
        'task': 'tasks.trading_tasks.check_all_positions',
        'schedule': 60.0,
    },
    'fetch-candles-every-1min': {
        'task': 'tasks.market_tasks.fetch_live_candles',
        'schedule': 60.0,
    },
    'cleanup-old-data-daily': {
        'task': 'tasks.maintenance_tasks.cleanup_old_candles',
        'schedule': crontab(hour=2, minute=0),  # 2 AM daily
    },
    'daily-summary-evening': {
        'task': 'tasks.maintenance_tasks.send_daily_summary',
        'schedule': crontab(hour=18, minute=0),  # 6 PM daily
    },
}
```

### Task Configuration
- **Trading tasks**: `acks_late=True`, `reject_on_worker_lost=True`
- **Backtest tasks**: `soft_time_limit=3600` (1 hour max)
- **Market data**: `rate_limit=10/m` (avoid rate limits)

---

## 16. WEBSOCKET PROTOCOL

### Connection
- URL: `wss://your-backend.onrender.com/socket.io/`
- Protocol: Socket.IO with JSON messages
- Authentication: JWT in connection params

### Client Events

**Connect:**
```javascript
const socket = io('https://your-backend.onrender.com', {
  auth: { token: 'JWT_TOKEN' }
});
```

**Subscribe to channels:**
```json
{ "event": "subscribe", "channels": ["prices", "trades", "positions"] }
```

**Unsubscribe:**
```json
{ "event": "unsubscribe", "channels": ["prices"] }
```

### Server Events

**Price Update:**
```json
{
  "event": "price",
  "data": {
    "symbol": "BTCUSDT",
    "price": 45000.00,
    "change": 2.5,
    "timestamp": 1704067200000
  }
}
```

**Trade Executed:**
```json
{
  "event": "trade",
  "data": {
    "trade_id": "...",
    "symbol": "BTCUSDT",
    "side": "BUY",
    "quantity": 0.01,
    "price": 45000.00,
    "mode": "paper"
  }
}
```

**Position Update:**
```json
{
  "event": "position",
  "data": {
    "position_id": "...",
    "unrealized_pnl": 50.00,
    "current_price": 45500.00
  }
}
```

**Signal Alert:**
```json
{
  "event": "signal",
  "data": {
    "strategy_id": "...",
    "strategy_name": "RSI Momentum",
    "signal": "BUY",
    "reason": "RSI < 30",
    "symbol": "BTCUSDT",
    "price": 45000.00
  }
}
```

**Bot Status:**
```json
{
  "event": "bot_status",
  "data": {
    "strategy_id": "...",
    "status": "running",
    "mode": "paper",
    "last_signal": "BUY"
  }
}
```

### Reconnection Strategy
- Exponential backoff: 1s, 2s, 4s, 8s, max 30s
- Max retries: unlimited (trading requires persistent connection)
- On reconnect: re-subscribe to all channels

---

## 17. PAPER TRADING SYSTEM

### Overview
Paper trading allows testing strategies with simulated money before risking real capital.

### Modes
- **Paper Trading**: Simulated trades, fake balance
- **Live Trading**: Real trades, real balance

### Switching Modes
- Global mode switch in header affects all bots
- Per-strategy mode override available
- Clear separation of trade history

### Paper Balance
- Initial balance: Configurable (default $10,000)
- Reset balance: Available in settings
- Track virtual P&L separately from real

### Order Execution (Paper)
1. Signal detected
2. Risk checks pass
3. Simulate order placement
4. Update virtual balance
5. Create paper trade record
6. Send notification (noting paper mode)

### Broker Simulation (When No Broker)
- Use real market prices from data feed
- Simulate fills at current price
- No real order placement

### Verification
- All paper trades stored in `trades` collection with `mode: "paper"`
- Separate from live trades in UI
- Backtest results use same schema

---

## 18. BACKTESTING ENGINE

### Data Sources
1. **Broker API**: Fetch historical candles (e.g., Binance `klines`)
2. **CSV Upload**: User uploads OHLCV data
3. **Database**: Use stored historical candles

### Backtest Flow
1. User selects strategy, symbol, timeframe, date range
2. Create backtest record in DB
3. Queue Celery task
4. Task fetches historical candles
5. Iterate through each candle:
   - Calculate indicators
   - Check entry conditions → execute if signal
   - Check exit conditions → close if signal
   - Apply SL/TP if triggered
6. Calculate final metrics
7. Store results
8. Notify user via WebSocket

### Performance Metrics Calculated
- **Total Return**: (Final - Initial) / Initial × 100%
- **Win Rate**: Winning Trades / Total Trades × 100%
- **Sharpe Ratio**: (Return - Risk Free Rate) / Std Dev of Returns
- **Max Drawdown**: Maximum peak-to-trough decline
- **Profit Factor**: Gross Profit / Gross Loss
- **Average Trade**: Total Return / Total Trades
- **Recovery Factor**: Total Return / Max Drawdown

### Trade Execution in Backtest
- Assume market orders fill at candle close price
- Add simulated spread (0.05% for crypto)
- Include commission (configurable, default 0.1%)
- Slippage simulation (optional)

### Results Storage
- Summary metrics in `backtests` collection
- Detailed trade list in `results_json` field
- Equity curve as array of `{timestamp, value}` points

---

## 19. BROKER INTEGRATION DETAILS

### Binance Integration
```python
# services/broker/binance.py
class BinanceBroker:
    def __init__(self, api_key: str, api_secret: str, testnet: bool = True):
        self.client = CCXT_Binance({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
        })
        if testnet:
            self.client.set_sandbox_mode(True)
    
    def get_balance(self) -> dict:
        return self.client.fetch_balance()
    
    def create_order(self, symbol: str, side: str, qty: float, order_type: str = 'market'):
        return self.client.create_order(symbol, order_type, side, qty)
    
    def get_current_price(self, symbol: str) -> float:
        ticker = self.client.fetch_ticker(symbol)
        return ticker['last']
    
    def get_ohlcv(self, symbol: str, timeframe: str, limit: int) -> list:
        return self.client.fetch_ohlcv(symbol, timeframe, limit=limit)
```

### Zerodha Integration
```python
# services/broker/zerodha.py
class ZerodhaBroker:
    def __init__(self, api_key: str, access_token: str):
        self.kite = KiteConnect(api_key)
        self.kite.set_access_token(access_token)
    
    def get_balance(self) -> dict:
        return self.kite.margins()
    
    def place_order(self, symbol: str, qty: int, side: str):
        return self.kite.place_order('BUY' if side == 'buy' else 'SELL', ...)
```

### Broker Interface (Abstract)
```python
# services/broker/base.py
class BrokerInterface(ABC):
    @abstractmethod
    def get_balance(self) -> dict:
        pass
    
    @abstractmethod
    def create_order(self, symbol, side, qty, order_type) -> dict:
        pass
    
    @abstractmethod
    def get_current_price(self, symbol: str) -> float:
        pass
    
    @abstractmethod
    def get_ohlcv(self, symbol: str, timeframe: str, limit: int) -> list:
        pass
    
    @abstractmethod
    def get_positions(self) -> list:
        pass
    
    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        pass
```

### Rate Limit Handling
- Binance: 1200 requests/minute
- Implement exponential backoff on 429
- Cache balance queries for 10 seconds
- Queue order requests

---

## 20. ERROR HANDLING & RECOVERY

### Error Categories

**1. Broker Errors**
- Connection timeout → Retry 3 times with backoff
- Invalid API key → Notify user, disable broker
- Rate limited → Queue request, retry later
- Insufficient balance → Log error, skip trade

**2. Data Errors**
- Missing candle data → Fetch from alternative source
- Indicator calculation error → Log, skip evaluation
- Invalid signal → Validate before execution

**3. System Errors**
- Database connection lost → Retry with exponential backoff
- Redis connection lost → Fail gracefully, use memory fallback
- WebSocket disconnect → Auto-reconnect

### Recovery Procedures

**On Startup:**
1. Load active strategies from DB
2. Check broker connections
3. Resume any incomplete positions from DB

**On Broker Disconnect:**
1. Log error
2. Pause active bots
3. Attempt reconnection every 30 seconds
4. Notify user via Telegram
5. Resume when connected

**On Database Error:**
1. Log error with stack trace
2. Retry operation 3 times
3. Fall back to cached data if available
4. Alert user if persistent

### Circuit Breaker
- After 5 consecutive errors → Pause all bots
- Manual reset required to restart
- Prevents cascade failures

---

## 21. BACKUP & DISASTER RECOVERY

### Backup Strategy

**MongoDB Atlas:**
- Automatic daily backups (M0 free tier)
- Point-in-time recovery available (paid tiers)
- Export critical data weekly via mongodump

**Application:**
- Environment variables documented
- Export strategies/trades periodically
- Store in GitHub (encrypted secrets)

### Disaster Recovery Plan

**Scenario: Complete Data Loss**
1. Restore from MongoDB Atlas backup
2. Redeploy application
3. Reconfigure broker connections
4. Resume trading

**Scenario: Broker Compromise**
1. Immediately revoke API keys
2. Generate new keys
3. Update in application
4. Review recent trades for anomalies

**Scenario: Application Down**
1. Check Render dashboard
2. Review logs for errors
3. Deploy from last working commit
4. If persistent, restore from backup

### Monitoring
- Uptime monitoring via Health Check endpoint
- Error tracking via logs
- Regular manual testing of critical flows

---

## 22. FUTURE SCOPE
- AI-based strategy suggestions
- Multi-asset portfolio management
- Mobile app (React Native)
- Advanced charting with drawing tools
- Strategy marketplace (if expanded later)
- Voice alerts
- Auto-optimization of indicator parameters
- Portfolio rebalancing
- Tax reporting

---

## RECOMMENDED FOLDER STRUCTURE
```
project-root/
├── frontend/                      # React app (deploy to Vercel)
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── stores/
│   │   ├── hooks/
│   │   ├── services/
│   │   └── utils/
│   ├── public/
│   ├── package.json
│   └── vite.config.ts
│
├── backend/                       # Flask app (deploy to Render)
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── routes/
│   │   ├── services/
│   │   ├── models/
│   │   ├── tasks/
│   │   └── utils/
│   ├── requirements.txt
│   ├── celery_worker.py
│   ├── gunicorn.conf.py
│   └── .env.example
│
├── docker-compose.yml
├── docker/
│   ├── backend.Dockerfile
│   └── frontend.Dockerfile
│
└── docs/
    ├── PRD.md
    ├── ARCHITECTURE.md
    ├── SRS.md
    └── API_DOCS.md
```

---

## DEVELOPMENT PHASES

| Phase | Tasks |
|-------|-------|
| Phase 1 — Planning | PRD, Architecture, SRS |
| Phase 2 — Foundation | Flask setup, MongoDB, Docker, basic auth |
| Phase 3 — Core Trading | Strategy model, indicator calculations, signal detection |
| Phase 4 — Broker Integration | Connect to Binance (testnet first) |
| Phase 5 — Paper Trading | Full paper trading loop |
| Phase 6 — Live Trading | Switch to live API after testing |
| Phase 7 — Backtesting | Historical testing engine |
| Phase 8 — Frontend | React dashboard, charts, controls |
| Phase 9 — Notifications | Telegram integration |
| Phase 10 — Deployment | Render + Vercel production setup |

---

## TOOLS USED

| Purpose | Tool |
|---------|------|
| Documentation | Markdown files in repo |
| UI Design | Figma |
| API Testing | Postman |
| Database UI | MongoDB Compass |
| Version Control | GitHub |
| Project Management | Trello / Notion |
| Deployment | Vercel (frontend), Render (backend) |
| Database Hosting | MongoDB Atlas |
| Cache/Queue | Upstash (Redis) |
| Containerization | Docker |

---

*End of Document*