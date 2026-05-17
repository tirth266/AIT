# Software Requirements Specification (SRS)
# Trading Bot System

---

## 1. FUNCTIONAL REQUIREMENTS

### 1.1 Authentication & Security

| ID | Requirement | Description |
|-----|-------------|-------------|
| FR-1.1 | Single Owner Login | Authenticate using credentials from environment variables |
| FR-1.2 | JWT Token Management | Issue short-lived JWT tokens (1 hour expiry) |
| FR-1.3 | Token Refresh | Allow token refresh for continuous session |
| FR-1.4 | Optional 2FA | TOTP-based two-factor authentication |
| FR-1.5 | Session Timeout | Auto logout after configurable inactivity period |

### 1.2 Strategy Management

| ID | Requirement | Description |
|-----|-------------|-------------|
| FR-2.1 | Create Strategy | Define trading strategies with indicators, entry/exit conditions |
| FR-2.2 | Edit Strategy | Modify existing strategies |
| FR-2.3 | Delete Strategy | Remove strategies from system |
| FR-2.4 | List Strategies | View all created strategies with status |
| FR-2.5 | Clone Strategy | Duplicate existing strategy |
| FR-2.6 | Strategy Validation | Validate parameters before saving |
| FR-2.7 | Indicator Selection | Support RSI, EMA, SMA, MACD, Bollinger Bands, VWAP, Supertrend, ATR, Stochastic |

### 1.3 Trading Modes

| ID | Requirement | Description |
|-----|-------------|-------------|
| FR-3.1 | Paper Trading Mode | Execute simulated trades with virtual balance |
| FR-3.2 | Live Trading Mode | Execute real trades via broker API |
| FR-3.3 | Mode Switching | Toggle between paper/live globally or per strategy |
| FR-3.4 | Mode Indicator | Clear visual indication of current mode in UI |

### 1.4 Trading Execution

| ID | Requirement | Description |
|-----|-------------|-------------|
| FR-4.1 | Auto Trade Execution | Automatically execute trades based on strategy signals |
| FR-4.2 | Manual Trade Execution | User can manually place trades |
| FR-4.3 | Trade Logging | Record all trades with timestamps, prices, quantities |
| FR-4.4 | Trade Cancellation | Cancel pending orders |
| FR-4.5 | Position Management | Track open positions, update P&L in real-time |
| FR-4.6 | Order Types | Support market and limit orders |

### 1.5 Risk Management

| ID | Requirement | Description |
|-----|-------------|-------------|
| FR-5.1 | Stop Loss | Per-trade SL as percentage or absolute |
| FR-5.2 | Take Profit | Per-trade TP as percentage or absolute |
| FR-5.3 | Trailing Stop | Dynamic SL that follows price movement |
| FR-5.4 | Position Limits | Max open positions configurable |
| FR-5.5 | Daily Loss Limit | Auto-pause trading after daily loss threshold |
| FR-5.6 | Consecutive Loss Circuit | Auto-pause after N consecutive losses |
| FR-5.7 | Max Drawdown Circuit | Auto-pause when drawdown exceeds threshold |
| FR-5.8 | Trade Cooldown | Minimum time between trades |
| FR-5.9 | Position Sizing | Calculate position size based on risk percentage |

### 1.6 Market Data

| ID | Requirement | Description |
|-----|-------------|-------------|
| FR-6.1 | Fetch Candle Data | Retrieve OHLCV data from broker API |
| FR-6.2 | Store Candle Data | Persist candle data in MongoDB |
| FR-6.3 | Real-time Price Updates | WebSocket for live price streaming |
| FR-6.4 | Historical Data | Query historical candles by date range |
| FR-6.5 | Multiple Timeframes | Support 1m, 5m, 15m, 30m, 1h, 4h, 1d timeframes |

### 1.7 Broker Integration

| ID | Requirement | Description |
|-----|-------------|-------------|
| FR-7.1 | Binance Integration | Connect to Binance Spot/Futures API |
| FR-7.2 | Zerodha Integration | Connect to Kite Connect API |
| FR-7.3 | Upstox Integration | Connect to Upstox API |
| FR-7.4 | Secure Credential Storage | Encrypt API keys/secrets at rest |
| FR-7.5 | Connection Testing | Validate broker connection before use |
| FR-7.6 | Balance Fetching | Retrieve account balance from broker |
| FR-7.7 | Position Sync | Sync open positions with broker |

### 1.8 Backtesting

| ID | Requirement | Description |
|-----|-------------|-------------|
| FR-8.1 | Historical Backtest | Run strategy on historical data |
| FR-8.2 | Date Range Selection | Configure start and end dates |
| FR-8.3 | Performance Metrics | Calculate returns, win rate, Sharpe, drawdown |
| FR-8.4 | Trade-by-Trade Results | Detailed list of all trades in backtest |
| FR-8.5 | Equity Curve | Chart showing portfolio value over time |
| FR-8.6 | CSV Data Import | Upload custom OHLCV data for backtesting |
| FR-8.7 | Async Execution | Run backtest as background Celery task |

### 1.9 Notifications

| ID | Requirement | Description |
|-----|-------------|-------------|
| FR-9.1 | Telegram Alerts | Send trade signals via Telegram bot |
| FR-9.2 | In-app Notifications | Display notifications in web app |
| FR-9.3 | Trade Entry Alerts | Notify on each trade entry |
| FR-9.4 | Trade Exit Alerts | Notify on each trade exit |
| FR-9.5 | Error Alerts | Notify on critical errors |
| FR-9.6 | Daily Summary | Send daily PnL summary |

### 1.10 Reporting & Analytics

| ID | Requirement | Description |
|-----|-------------|-------------|
| FR-10.1 | Performance Dashboard | View trading performance metrics |
| FR-10.2 | P&L Report | Generate profit/loss reports |
| FR-10.3 | Trade Statistics | Calculate win rate, Sharpe ratio, etc. |
| FR-10.4 | Export Reports | Export trade history as CSV |
| FR-10.5 | Paper/Live Split | Separate reporting for paper vs live |
| FR-10.6 | Trade History | Searchable, filterable trade history |

---

## 2. NON-FUNCTIONAL REQUIREMENTS

### 2.1 Performance

| ID | Requirement | Acceptance Criteria |
|-----|-------------|---------------------|
| NFR-1.1 | API Response Time | API responses < 200ms (p95) |
| NFR-1.2 | Database Queries | Queries < 100ms (p95) |
| NFR-1.3 | Candle Processing | Process 100 candles/second minimum |
| NFR-1.4 | Indicator Calculation | Calculate indicators < 50ms per candle |
| NFR-1.5 | Backtest Speed | Process 10,000 candles < 30 seconds |

### 2.2 Reliability & Availability

| ID | Requirement | Acceptance Criteria |
|-----|-------------|---------------------|
| NFR-2.1 | Uptime SLA | 99.5% availability |
| NFR-2.2 | Data Persistence | All trades saved to database |
| NFR-2.3 | Graceful Degradation | System continues on non-critical failures |
| NFR-2.4 | Error Recovery | Auto-retry failed operations 3 times |

### 2.3 Scalability

| ID | Requirement | Acceptance Criteria |
|-----|-------------|---------------------|
| NFR-3.1 | Single User Scale | Optimized for single user |
| NFR-3.2 | Concurrent Strategies | Support up to 10 active strategies |
| NFR-3.3 | Data Retention | 30-day candle retention, indefinite trade history |
| NFR-3.4 | Redis Caching | Cache frequent queries |

### 2.4 Security

| ID | Requirement | Acceptance Criteria |
|-----|-------------|---------------------|
| NFR-4.1 | Authentication | JWT-based authentication with 1-hour expiry |
| NFR-4.2 | Credential Storage | Environment variables for master credentials |
| NFR-4.3 | Broker Key Encryption | AES-256 encryption for API keys |
| NFR-4.4 | HTTPS Only | TLS 1.2+ for all connections |
| NFR-4.5 | Rate Limiting | 100 requests/minute per IP |
| NFR-4.6 | Input Validation | Validate all API inputs |
| NFR-4.7 | CORS | Restrict to frontend domain only |

### 2.5 Usability

| ID | Requirement | Acceptance Criteria |
|-----|-------------|---------------------|
| NFR-5.1 | Responsive UI | Mobile-friendly design |
| NFR-5.2 | Real-time Updates | WebSocket for live data |
| NFR-5.3 | Clear Mode Indicator | Paper/Live mode clearly visible |
| NFR-5.4 | Error Messages | User-friendly error messages |

### 2.6 Maintainability

| ID | Requirement | Acceptance Criteria |
|-----|-------------|---------------------|
| NFR-6.1 | Code Structure | Modular Flask Blueprints |
| NFR-6.2 | Logging | Structured logging (JSON format) |
| NFR-6.3 | Configuration | Environment-based config |
| NFR-6.4 | Docker Support | Docker Compose for local dev |

---

## 3. TECHNICAL STACK SPECIFICATIONS

### 3.1 Technology Stack (Aligned with PRD)

| Layer | Technology | Notes |
|-------|------------|-------|
| Frontend | React 18 + Vite | Zustand for state |
| Backend | Flask 2.x | Python 3.11 |
| Database | MongoDB | MongoDB Atlas |
| Cache/Queue | Redis | Upstash (free tier) |
| Task Queue | Celery | Background tasks |
| WebSocket | Flask-SocketIO | Real-time updates |
| Deployment | Docker | Docker Compose |
| Hosting | Render + Vercel | Backend + Frontend |

### 3.2 Backend Architecture (Flask Blueprint Pattern)

```
app/
├── __init__.py          # Flask app factory
├── config.py            # Configuration
├── extensions.py        # Flask extensions init
├── routes/
│   ├── __init__.py
│   ├── auth.py          # /api/auth/*
│   ├── strategies.py    # /api/strategies/*
│   ├── trades.py        # /api/trades/*
│   ├── bot.py           # /api/bot/*
│   ├── broker.py        # /api/broker/*
│   ├── backtest.py      # /api/backtest/*
│   ├── market.py        # /api/market/*
│   └── settings.py      # /api/settings/*
├── services/
│   ├── auth_service.py
│   ├── trading_engine.py
│   ├── broker_factory.py
│   ├── notification_service.py
│   ├── backtest_engine.py
│   └── risk_manager.py
├── models/
│   ├── strategy.py
│   ├── trade.py
│   ├── candle.py
│   └── user.py
├── tasks/               # Celery tasks
│   ├── trading_tasks.py
│   ├── backtest_tasks.py
│   └── maintenance_tasks.py
└── utils/
    ├── indicators.py
    ├── encryption.py
    └── helpers.py
```

### 3.3 Celery Task Architecture

**Broker**: Redis (Upstash)
**Backend**: MongoDB (Celery backend result)

**Task Types:**
1. **Real-time Strategy Evaluation** (every 1-5 min)
2. **Position Monitoring** (every 1 min)
3. **Backtest Execution** (on-demand, long-running)
4. **Data Fetching** (every 1-5 min)
5. **Maintenance** (daily/weekly)

**Beat Schedule:**
- Evaluate strategies: Every 5 minutes
- Check positions: Every 1 minute
- Fetch candles: Every 1 minute
- Cleanup: Daily at 2 AM
- Daily summary: Daily at 6 PM

### 3.4 WebSocket Architecture

**Technology**: Flask-SocketIO

**Channels:**
- `prices` - Real-time price updates
- `trades` - Trade execution notifications
- `positions` - Position P&L updates
- `signals` - Strategy signal alerts
- `bot_status` - Bot status changes
- `logs` - Real-time log streaming

**Authentication**: JWT token passed in connection handshake

### 3.5 Database Schema (MongoDB)

**Collections with Indexes:**

```javascript
// strategies
{ "is_active": 1 }
{ "user_id": 1 }

// trades
{ "strategy_id": 1, "created_at": -1 }
{ "symbol": 1, "status": 1 }
{ "mode": 1 } // paper/live

// candles (TTL - 30 days)
{ "symbol": 1, "timeframe": 1, "timestamp": -1 }

// logs
{ "level": 1, "created_at": -1 }
```

---

## 4. API BEHAVIOR SPECIFICATIONS

### 4.1 Authentication Endpoints

#### POST /api/v1/auth/login
```json
Request:
{
  "password": "your-password"
}

Response (200):
{
  "token": "eyJhbGc...",
  "expires_in": 3600,
  "user": { "id": "...", "name": "Owner" }
}

Error (401):
{ "error": "Invalid credentials" }
```

#### POST /api/v1/auth/2fa
```json
Request:
{
  "code": "123456"
}

Response (200):
{ "message": "2FA verified" }
```

### 4.2 Strategy Endpoints

#### POST /api/v1/strategies
```json
Request:
{
  "strategy_name": "RSI Momentum",
  "symbol": "BTC/USDT",
  "timeframe": "1h",
  "indicators": [
    { "name": "RSI", "params": { "period": 14 } },
    { "name": "EMA", "params": { "period": 9 } }
  ],
  "entry_conditions": [
    { "indicator": "RSI", "operator": "less_than", "value": 30 }
  ],
  "exit_conditions": [
    { "indicator": "RSI", "operator": "greater_than", "value": 70 }
  ],
  "risk_settings": {
    "stop_loss_percent": 1.0,
    "take_profit_percent": 2.0,
    "trailing_stop_enabled": true
  },
  "mode": "paper"
}

Response (201):
{
  "id": "strat_456def",
  "created_at": "2024-01-15T10:30:00Z"
}
```

#### GET /api/v1/strategies
```json
Response (200):
{
  "strategies": [
    {
      "id": "strat_456def",
      "strategy_name": "RSI Momentum",
      "symbol": "BTC/USDT",
      "mode": "paper",
      "is_active": true,
      "created_at": "2024-01-15T10:30:00Z"
    }
  ],
  "total": 5
}
```

### 4.3 Trading Endpoints

#### POST /api/v1/trades/execute
```json
Request:
{
  "strategy_id": "strat_456def",
  "symbol": "BTC/USDT",
  "side": "buy",
  "quantity": 0.01,
  "order_type": "market",
  "stop_loss": 44500,
  "take_profit": 46000
}

Response (201):
{
  "id": "trade_789ghi",
  "status": "filled",
  "mode": "paper",
  "entry_price": 45000,
  "created_at": "2024-01-15T10:35:00Z"
}
```

#### GET /api/v1/trades
```json
Query: ?mode=paper&symbol=BTC/USDT&limit=50

Response (200):
{
  "trades": [
    {
      "id": "trade_789ghi",
      "symbol": "BTC/USDT",
      "side": "buy",
      "status": "closed",
      "mode": "paper",
      "entry_price": 45000,
      "exit_price": 45500,
      "quantity": 0.01,
      "pnl": 5.00,
      "pnl_percent": 0.11,
      "entry_time": "2024-01-15T10:35:00Z",
      "exit_time": "2024-01-15T12:00:00Z"
    }
  ],
  "total": 100,
  "page": 1
}
```

### 4.4 Bot Control Endpoints

#### POST /api/v1/bot/start
```json
Request:
{
  "strategy_id": "strat_456def"
}

Response (200):
{
  "status": "started",
  "mode": "paper",
  "message": "Bot started in paper trading mode"
}
```

#### POST /api/v1/bot/stop
```json
Request:
{
  "strategy_id": "strat_456def"
}

Response (200):
{
  "status": "stopped",
  "message": "Bot stopped"
}
```

#### POST /api/v1/bot/mode
```json
Request:
{
  "mode": "live"  // or "paper"
}

Response (200):
{
  "current_mode": "live",
  "message": "Switched to live trading mode"
}
```

### 4.5 Broker Endpoints

#### POST /api/v1/broker/connect
```json
Request:
{
  "broker": "binance",
  "api_key": "your-api-key",
  "api_secret": "your-api-secret",
  "testnet": true
}

Response (200):
{
  "broker": "binance",
  "is_connected": true,
  "balance": { "total": 10000.00, "available": 10000.00 }
}
```

### 4.6 Market Data Endpoints

#### GET /api/v1/market/candles
```json
Query: ?symbol=BTC/USDT&timeframe=1h&limit=100&start=2024-01-01&end=2024-01-15

Response (200):
{
  "symbol": "BTC/USDT",
  "timeframe": "1h",
  "candles": [
    {
      "timestamp": "2024-01-15T10:00:00Z",
      "open": 45000,
      "high": 45500,
      "low": 44800,
      "close": 45200,
      "volume": 1500.5
    }
  ]
}
```

### 4.7 Backtest Endpoints

#### POST /api/v1/backtest/run
```json
Request:
{
  "strategy_id": "strat_456def",
  "symbol": "BTC/USDT",
  "timeframe": "1h",
  "start_date": "2023-01-01",
  "end_date": "2023-12-31",
  "initial_capital": 10000
}

Response (202):
{
  "backtest_id": "bt_123",
  "status": "queued",
  "message": "Backtest started in background"
}
```

#### GET /api/v1/backtest/:id
```json
Response (200):
{
  "id": "bt_123",
  "status": "completed",
  "progress": 100
}
```

#### GET /api/v1/backtest/:id/results
```json
Response (200):
{
  "total_return": 25.5,
  "total_trades": 150,
  "winning_trades": 90,
  "losing_trades": 60,
  "win_rate": 60.0,
  "sharpe_ratio": 1.5,
  "max_drawdown": 8.2,
  "profit_factor": 1.8,
  "equity_curve": [...],
  "trades": [...]
}
```

---

## 5. WEBSOCKET PROTOCOL

### 5.1 Connection
- URL: `wss://your-backend.onrender.com/socket.io/`
- Auth: JWT token in handshake
- Reconnection: Exponential backoff

### 5.2 Client → Server Messages

```json
{ "event": "subscribe", "channels": ["prices", "trades"] }
{ "event": "unsubscribe", "channels": ["prices"] }
{ "event": "ping" }
```

### 5.3 Server → Client Messages

```json
// Price update
{
  "event": "price",
  "data": { "symbol": "BTC/USDT", "price": 45000, "timestamp": 1704067200000 }
}

// Trade executed
{
  "event": "trade",
  "data": { "trade_id": "...", "mode": "paper", "side": "BUY", "pnl": 5.00 }
}

// Position update
{
  "event": "position",
  "data": { "position_id": "...", "unrealized_pnl": 50.00 }
}

// Signal alert
{
  "event": "signal",
  "data": { "strategy_id": "...", "signal": "BUY", "reason": "RSI < 30" }
}

// Bot status
{
  "event": "bot_status",
  "data": { "strategy_id": "...", "status": "running", "mode": "paper" }
}
```

---

## 6. SECURITY REQUIREMENTS

### 6.1 Authentication
- JWT tokens with HS256 algorithm
- Token expiry: 1 hour access
- Master credentials from environment variables (not database)
- Optional 2FA via TOTP

### 6.2 Data Protection
- Fernet (AES) encryption for broker API keys
- Environment variables for secrets
- TLS 1.2+ for all communications
- CORS restricted to frontend domain

### 6.3 API Security
- Rate limiting: 100 req/min per IP
- Input validation using Marshmallow
- No public registration endpoints

### 6.4 Logging & Audit
- All trade actions logged
- Error logs with stack traces
- Access logs for security monitoring

---

## 7. PERFORMANCE REQUIREMENTS

### 7.1 Response Time SLA

| Endpoint | p95 Target |
|----------|------------|
| Login | < 150ms |
| Get Strategies | < 100ms |
| Execute Trade (paper) | < 200ms |
| Get Candles | < 150ms |
| WebSocket price | < 50ms |

### 7.2 Throughput

| Metric | Target |
|--------|--------|
| Active strategies | 10 |
| Trades per day | 100 |
| Candles processed/min | 1000 |
| Concurrent WebSocket connections | 5 |

### 7.3 Resource Usage

| Resource | Limit |
|----------|-------|
| API Server CPU | < 70% |
| API Server Memory | < 512MB |
| Celery Worker Memory | < 1GB |
| MongoDB Storage | < 1GB |

### 7.4 Caching Strategy
- Redis: Cache balance (10s TTL), cache prices (1s TTL)
- In-memory: Cache strategy configs
- CDN: Static assets (frontend)

---

## 8. BROKER INTEGRATION SPECIFICATIONS

### 8.1 Binance
- **API**: CCXT library
- **Endpoints**: Spot and Futures (testnet available)
- **Rate Limit**: 1200 requests/minute
- **Data**: OHLCV, order book, balance

### 8.2 Zerodha
- **API**: Kite Connect v3
- **Endpoints**: Orders, margins, positions
- **Rate Limit**: 3 requests/second
- **Data**: NSE, BSE instruments

### 8.3 Upstox
- **API**: Upstox Pro API
- **Endpoints**: Order placement, portfolio
- **Data**: Equity, F&O

### 8.4 Broker Interface (Abstract)

```python
class BrokerInterface(ABC):
    @abstractmethod
    def get_balance(self) -> dict
    @abstractmethod
    def create_order(self, symbol, side, qty, order_type) -> dict
    @abstractmethod
    def get_current_price(self, symbol: str) -> float
    @abstractmethod
    def get_ohlcv(self, symbol, timeframe, limit) -> list
    @abstractmethod
    def get_positions(self) -> list
```

---

## 9. BACKTESTING ENGINE SPECIFICATIONS

### 9.1 Data Sources
1. Broker API historical data (Binance klines)
2. CSV file upload
3. MongoDB stored candles

### 9.2 Execution
- Run as Celery task (async)
- Iterate candle-by-candle
- Calculate indicators at each step
- Apply entry/exit conditions
- Track positions and P&L

### 9.3 Performance Metrics
- Total Return (%)
- Annual Return (%)
- Sharpe Ratio
- Max Drawdown (%)
- Win Rate (%)
- Profit Factor
- Total Trades
- Average Trade Duration

### 9.4 Results Storage
- Summary in `backtests` collection
- Detailed trade list in JSON
- Equity curve as time-series

---

## 10. SYSTEM CONSTRAINTS

### 10.1 Technical Constraints
- Single-user system (no multi-tenancy)
- Flask with synchronous handlers (eventlet for WebSocket)
- MongoDB for all data storage
- Redis for caching and Celery broker

### 10.2 Business Constraints
- Operating hours: 24/7
- Data retention: 30 days candles, indefinite trades
- Broker availability depends on external APIs

### 10.3 Deployment Constraints
- Render: Web service + Background worker
- Vercel: Frontend only
- MongoDB Atlas: Free tier (M0)
- Redis: Upstash free tier

---

## 11. ACCEPTANCE CRITERIA

### Functional
- [ ] User can login with environment credentials
- [ ] User can create/edit/delete strategies
- [ ] User can start/stop trading bots
- [ ] Paper trading executes without real money
- [ ] Live trading executes via broker API
- [ ] Stop loss and take profit work correctly
- [ ] Backtest runs and produces metrics
- [ ] WebSocket delivers real-time updates
- [ ] Telegram notifications sent on trades
- [ ] Trade history filterable by date/mode

### Non-Functional
- [ ] API response time < 200ms (p95)
- [ ] No data loss on system restart
- [ ] Broker credentials encrypted
- [ ] HTTPS enforced
- [ ] Docker Compose works for local dev

### Security
- [ ] JWT tokens expire after 1 hour
- [ ] API keys stored encrypted
- [ ] Rate limiting enabled
- [ ] No public signup endpoint

---

## 12. ASSUMPTIONS & DEPENDENCIES

### Assumptions
- Single user system (owner only)
- No need for user management
- Broker APIs remain stable
- Network connectivity reliable
- Market data feeds accurate

### Dependencies
- Binance API (CCXT library)
- Zerodha Kite Connect
- Upstox API
- Telegram Bot API
- MongoDB Atlas
- Upstash Redis

### External Services
- **MongoDB Atlas**: Database hosting
- **Upstash**: Redis for caching and Celery
- **Render**: Backend hosting
- **Vercel**: Frontend hosting

---

## 13. RISK MANAGEMENT RULES

| Rule | Default Value | Configurable |
|------|--------------|--------------|
| Max Daily Loss | 5% | Yes |
| Risk Per Trade | 1% | Yes |
| Max Open Positions | 3 | Yes |
| Auto Stop (Consecutive Losses) | 3 | Yes |
| Max Drawdown | 10% | Yes |
| Trade Cooldown | 5 min | Yes |
| Mandatory SL | Yes | No |

### Risk Check Sequence
1. Is bot active?
2. Is trading allowed (not circuit broken)?
3. Daily loss limit not exceeded?
4. Max open positions not exceeded?
5. Cooldown elapsed?
6. Sufficient capital available?
7. Broker connected?
8. Execute trade

---

*This SRS provides a comprehensive technical blueprint aligned with your Flask + MongoDB + React stack.*