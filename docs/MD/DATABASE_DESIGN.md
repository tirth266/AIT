# DATABASE DESIGN DOCUMENT

## Overview
MongoDB database design for single-user automated trading platform. All collections include `user_id` field for future multi-user support, though currently restricted to single owner.

---

## DATABASE: trading_db

---

## 1. USER COLLECTION

**Collection Name**: `user`

**Purpose**: Store owner configuration and preferences. Only one document exists.

```json
{
  "_id": "ObjectId",
  "name": "Trading Owner",
  "email": "owner@example.com",
  "password_hash": "$2b$12$...",
  "twofa_secret_encrypted": "encrypted_base64_string",
  "twofa_enabled": false,
  "created_at": "ISODate",
  "updated_at": "ISODate"
}
```

**Indexes**:
```javascript
{ "_id": 1 }  // Primary
```

**Notes**:
- Master credentials primarily stored in environment variables
- This document stores 2FA settings and preferences
- Password hash for backup authentication

---

## 2. STRATEGIES COLLECTION

**Collection Name**: `strategies`

**Purpose**: Store trading strategy configurations with indicators and conditions.

```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId",
  "strategy_name": "RSI EMA Momentum",
  "symbol": "BTC/USDT",
  "timeframe": "1h",
  "mode": "paper",
  "broker": "binance",
  "indicators": [
    {
      "id": "ind_001",
      "name": "RSI",
      "params": { "period": 14 },
      "enabled": true
    },
    {
      "id": "ind_002",
      "name": "EMA",
      "params": { "period": 9 },
      "enabled": true
    },
    {
      "id": "ind_003",
      "name": "EMA",
      "params": { "period": 21 },
      "enabled": true
    }
  ],
  "entry_conditions": [
    {
      "id": "cond_001",
      "indicator_id": "ind_001",
      "indicator_name": "RSI",
      "operator": "less_than",
      "value": 30,
      "logic": "AND"
    },
    {
      "id": "cond_002",
      "indicator_id": "ind_002",
      "indicator_name": "EMA_9",
      "operator": "crosses_above",
      "value": "EMA_21",
      "logic": "AND"
    }
  ],
  "exit_conditions": [
    {
      "id": "cond_003",
      "indicator_id": "ind_001",
      "indicator_name": "RSI",
      "operator": "greater_than",
      "value": 70,
      "logic": "OR"
    },
    {
      "id": "cond_004",
      "indicator_id": "ind_002",
      "indicator_name": "EMA_9",
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
    "position_size_type": "calculated",
    "position_size_percent": 10.0,
    "max_positions": 1
  },
  "execution_settings": {
    "order_type": "market",
    "allow_partial_fills": false,
    "retry_on_failure": true,
    "max_retries": 3
  },
  "is_active": false,
  "last_evaluated_at": "ISODate",
  "created_at": "ISODate",
  "updated_at": "ISODate"
}
```

**Indexes**:
```javascript
{ "user_id": 1, "_id": 1 }                    // Primary user queries
{ "is_active": 1 }                             // Find active strategies
{ "symbol": 1, "mode": 1 }                     // Filter by symbol/mode
{ "broker": 1 }                                // Filter by broker
```

**Field Descriptions**:

| Field | Type | Description |
|-------|------|-------------|
| strategy_name | string | User-defined name |
| symbol | string | Trading pair (e.g., BTC/USDT) |
| timeframe | string | 1m, 5m, 15m, 30m, 1h, 4h, 1d |
| mode | string | "paper" or "live" |
| broker | string | "binance", "zerodha", "upstox" |
| indicators | array | List of indicator configs |
| entry_conditions | array | Buy condition rules |
| exit_conditions | array | Sell condition rules |
| risk_settings | object | SL, TP, position sizing |
| is_active | boolean | Bot running status |

---

## 3. TRADES COLLECTION

**Collection Name**: `trades`

**Purpose**: Record of all executed trades (paper and live).

```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId",
  "strategy_id": "ObjectId",
  "strategy_name": "RSI EMA Momentum",
  "symbol": "BTC/USDT",
  "side": "BUY",
  "entry_price": 45000.00,
  "exit_price": 45500.00,
  "quantity": 0.01,
  "entry_type": "market",
  "exit_type": "market",
  "entry_order_id": "binance_order_123",
  "exit_order_id": "binance_order_456",
  "pnl": 5.00,
  "pnl_percent": 0.111,
  "commission": 0.10,
  "sl_hit": false,
  "tp_hit": true,
  "mode": "paper",
  "broker": "binance",
  "stop_loss": 44550.00,
  "take_profit": 45900.00,
  "notes": "Optional trade notes",
  "status": "CLOSED",
  "entry_time": "ISODate",
  "exit_time": "ISODate",
  "duration_minutes": 120,
  "created_at": "ISODate"
}
```

**Indexes**:
```javascript
{ "user_id": 1, "created_at": -1 }             // User trade history
{ "strategy_id": 1, "created_at": -1 }        // Strategy trades
{ "symbol": 1, "mode": 1 }                    // Filter by symbol/mode
{ "status": 1 }                               // Open/closed trades
{ "entry_time": 1 }                           // Time-based queries
{ "mode": 1, "created_at": -1 }              // Paper vs live history
```

**Field Descriptions**:

| Field | Type | Description |
|-------|------|-------------|
| strategy_id | ObjectId | Reference to strategy |
| side | string | "BUY" or "SELL" |
| entry_price | float | Price at entry |
| exit_price | float | Price at exit (null if open) |
| quantity | float | Trade quantity |
| pnl | float | Profit/Loss in quote currency |
| pnl_percent | float | P&L as percentage |
| commission | float | Total fees paid |
| mode | string | "paper" or "live" |
| status | string | "OPEN", "CLOSED", "CANCELLED" |

---

## 4. POSITIONS COLLECTION

**Collection Name**: `positions`

**Purpose**: Track open positions in real-time.

```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId",
  "strategy_id": "ObjectId",
  "strategy_name": "RSI EMA Momentum",
  "symbol": "BTC/USDT",
  "side": "BUY",
  "entry_price": 45000.00,
  "quantity": 0.01,
  "current_price": 45500.00,
  "market_value": 455.00,
  "unrealized_pnl": 5.00,
  "unrealized_pnl_percent": 0.111,
  "stop_loss": 44550.00,
  "take_profit": 45900.00,
  "trailing_stop_active": true,
  "trailing_stop_price": 44750.00,
  "mode": "paper",
  "broker": "binance",
  "broker_position_id": "binance_position_123",
  "opened_at": "ISODate",
  "created_at": "ISODate",
  "updated_at": "ISODate"
}
```

**Indexes**:
```javascript
{ "user_id": 1, "status": 1 }                // User open positions
{ "strategy_id": 1 }                          // Strategy positions
{ "symbol": 1, "mode": 1 }                   // By symbol/mode
{ "opened_at": -1 }                          // Sort by opening time
```

---

## 5. CANDLES COLLECTION

**Collection Name**: `candles`

**Purpose**: Store OHLCV data for analysis and backtesting.

```json
{
  "_id": "ObjectId",
  "symbol": "BTC/USDT",
  "timeframe": "5m",
  "timestamp": "ISODate",
  "open": 45000.00,
  "high": 45500.00,
  "low": 44800.00,
  "close": 45200.00,
  "volume": 1500.5,
  "quote_volume": 67663800.00,
  "trades": 12345,
  "is_closed": true,
  "created_at": "ISODate"
}
```

**Indexes**:
```javascript
{ "symbol": 1, "timeframe": 1, "timestamp": -1 },  // Primary - query by symbol/timeframe
{ "timestamp": 1 },                                // Time-based queries
// TTL Index - auto-delete after 30 days
{ "created_at": 1 }, { expireAfterSeconds: 2592000 }
```

**TTL Policy**:
- Intraday (1m, 5m, 15m, 30m, 1h): 30 days
- Higher timeframes (4h, 1d): 90 days (longer retention for backtesting)

---

## 6. BROKERS COLLECTION

**Collection Name**: `brokers`

**Purpose**: Store encrypted broker API credentials.

```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId",
  "broker_name": "binance",
  "broker_type": "spot",
  "api_key_encrypted": "fernet_encrypted_string",
  "api_secret_encrypted": "fernet_encrypted_string",
  "testnet_enabled": true,
  "is_connected": true,
  "last_connection_test": "ISODate",
  "last_connected_at": "ISODate",
  "connection_status": "healthy",
  "rate_limit_remaining": 1000,
  "created_at": "ISODate",
  "updated_at": "ISODate"
}
```

**Indexes**:
```javascript
{ "user_id": 1, "broker_name": 1 },  // User's brokers
{ "is_connected": 1 }                // Find active connections
```

**Security**:
- API keys encrypted using Fernet (AES 128)
- Encryption key from environment variable
- Never log raw credentials

---

## 7. BACKTESTS COLLECTION

**Collection Name**: `backtests`

**Purpose**: Store backtest configurations and results.

```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId",
  "strategy_id": "ObjectId",
  "strategy_name": "RSI EMA Momentum",
  "symbol": "BTC/USDT",
  "timeframe": "1h",
  "start_date": "ISODate",
  "end_date": "ISODate",
  "initial_capital": 10000.00,
  "final_capital": 12500.00,
  "total_return": 25.0,
  "annual_return": 25.0,
  "total_trades": 150,
  "winning_trades": 90,
  "losing_trades": 60,
  "win_rate": 60.0,
  "sharpe_ratio": 1.5,
  "sortino_ratio": 2.1,
  "max_drawdown": 8.5,
  "max_drawdown_duration": 72,
  "profit_factor": 1.8,
  "avg_trade_duration": 240,
  "avg_win": 150.00,
  "avg_loss": -100.00,
  "largest_win": 500.00,
  "largest_loss": -200.00,
  "calmar_ratio": 2.94,
  "equity_curve": [
    { "timestamp": "ISODate", "value": 10000 },
    { "timestamp": "ISODate", "value": 10150 }
  ],
  "drawdown_curve": [
    { "timestamp": "ISODate", "drawdown": 0 }
  ],
  "trades": [
    {
      "entry_time": "ISODate",
      "exit_time": "ISODate",
      "symbol": "BTC/USDT",
      "side": "BUY",
      "entry_price": 45000,
      "exit_price": 45500,
      "quantity": 0.01,
      "pnl": 5.00,
      "pnl_percent": 0.11,
      "duration_minutes": 60,
      "exit_reason": "take_profit"
    }
  ],
  "monthly_returns": {
    "2024-01": 5.2,
    "2024-02": -2.1,
    "2024-03": 8.5
  },
  "status": "completed",
  "progress": 100,
  "error_message": null,
  "completed_at": "ISODate",
  "created_at": "ISODate"
}
```

**Indexes**:
```javascript
{ "user_id": 1, "created_at": -1 }      // User backtests
{ "strategy_id": 1 }                    // Strategy backtests
{ "status": 1 }                         // Running/completed
```

---

## 8. NOTIFICATIONS COLLECTION

**Collection Name**: `notifications`

**Purpose**: Store user notifications (trade alerts, errors, etc.).

```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId",
  "type": "trade_entry",
  "title": "Buy Order Filled",
  "message": "Bought 0.01 BTCUSDT at $45,000",
  "metadata": {
    "trade_id": "ObjectId",
    "symbol": "BTC/USDT",
    "mode": "paper"
  },
  "read": false,
  "telegram_sent": true,
  "push_sent": false,
  "created_at": "ISODate"
}
```

**Indexes**:
```javascript
{ "user_id": 1, "created_at": -1 }      // User notifications
{ "read": 1, "created_at": -1 }         // Unread notifications
{ "type": 1 }                           // Filter by type
```

**Notification Types**:
- `trade_entry` - Trade opened
- `trade_exit` - Trade closed
- `sl_hit` - Stop loss triggered
- `tp_hit` - Take profit triggered
- `signal` - Strategy signal generated
- `error` - System error
- `system` - System notifications

---

## 9. LOGS COLLECTION

**Collection Name**: `logs`

**Purpose**: Application logs for debugging and audit.

```json
{
  "_id": "ObjectId",
  "level": "INFO",
  "category": "TRADE",
  "message": "Buy signal detected for BTC/USDT",
  "metadata": {
    "strategy_id": "ObjectId",
    "symbol": "BTC/USDT",
    "price": 45000,
    "indicators": { "rsi": 28, "ema_9": 44900, "ema_21": 44850 }
  },
  "source": "trading_engine",
  "user_id": "ObjectId",
  "created_at": "ISODate"
}
```

**Indexes**:
```javascript
{ "level": 1, "created_at": -1 }        // Log level queries
{ "category": 1, "created_at": -1 }     // Category queries
{ "user_id": 1, "created_at": -1 }      // User-specific logs
{ "created_at": 1 }, { expireAfterSeconds: 7776000 }  // 90-day TTL
```

**Log Levels**:
- `DEBUG` - Detailed debug info
- `INFO` - General information
- `WARNING` - Warning messages
- `ERROR` - Error messages
- `CRITICAL` - Critical issues

**Categories**:
- `TRADE` - Trading operations
- `SIGNAL` - Signal detection
- `BROKER` - Broker API calls
- `SYSTEM` - System operations
- `BACKTEST` - Backtest operations

---

## 10. SETTINGS COLLECTION

**Collection Name**: `settings`

**Purpose**: Store user preferences and system settings.

```json
{
  "_id": "ObjectId",
  "key": "telegram_bot_token",
  "value_encrypted": "encrypted_value",
  "category": "notifications",
  "updated_at": "ISODate"
}
```

**Indexes**:
```javascript
{ "key": 1 }                            // Direct key lookup
{ "category": 1 }                       // Settings by category
```

**Setting Keys**:
- `telegram_bot_token` - Telegram bot API token
- `telegram_chat_id` - Telegram chat ID for alerts
- `default_mode` - "paper" or "live"
- `timezone` - User timezone
- `dashboard_refresh_rate` - WebSocket refresh rate
- `log_level` - Logging level

---

## 11. INDICATOR_VALUES COLLECTION

**Collection Name**: `indicator_values`

**Purpose**: Cache calculated indicator values for performance.

```json
{
  "_id": "ObjectId",
  "symbol": "BTC/USDT",
  "timeframe": "5m",
  "timestamp": "ISODate",
  "indicators": {
    "RSI_14": 45.5,
    "EMA_9": 45000.00,
    "EMA_21": 44950.00,
    "EMA_50": 44800.00,
    "MACD": {
      "macd": 150.00,
      "signal": 100.00,
      "histogram": 50.00
    },
    "BB": {
      "upper": 45500,
      "middle": 45200,
      "lower": 44900
    }
  },
  "created_at": "ISODate"
}
```

**Indexes**:
```javascript
{ "symbol": 1, "timeframe": 1, "timestamp": -1 },  // Latest indicators
{ "timestamp": 1 }                                 // Time queries
// TTL: 1 hour (real-time only)
{ "created_at": 1 }, { expireAfterSeconds: 3600 }
```

---

## 12. RELATIONSHIPS DIAGRAM

```
┌─────────────────────────────────────────────────────────────────────┐
│                         COLLECTION RELATIONSHIPS                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐                                                  │
│  │    user      │  (1) ──────► (N) strategies                       │
│  └──────────────┘                                                  │
│       │                                                            │
│       │         (1) ──────► (N) trades                            │
│       │                                                            │
│       │         (1) ──────► (N) positions                         │
│       │                                                            │
│       │         (1) ──────► (N) backtests                         │
│       │                                                            │
│       │         (1) ──────► (N) brokers                            │
│       │                                                            │
│       │         (1) ──────► (N) logs                               │
│       │                                                            │
│       │         (1) ──────► (N) notifications                     │
│       │                                                            │
│       │                                                            │
│  ┌──────────────┐       ┌──────────────┐                          │
│  │  strategies  │       │   candles   │                          │
│  └──────┬───────┘       └──────────────┘                          │
│         │                                                            │
│         │  (1) ──────► (N) trades                                  │
│         │                                                            │
│         │  (1) ──────► (N) positions                               │
│         │                                                            │
│         │  (1) ──────► (N) backtests                              │
│         │                                                            │
│  ┌──────────────┐                                                  │
│  │    trades    │                                                  │
│  └──────────────┘                                                  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 13. QUERY PATTERNS & PERFORMANCE

### Common Queries & Index Usage

| Query | Index Used | Expected Performance |
|-------|------------|---------------------|
| Get user's all trades | `{user_id: 1, created_at: -1}` | < 50ms |
| Get strategy trades | `{strategy_id: 1, created_at: -1}` | < 30ms |
| Get active strategies | `{is_active: 1}` | < 20ms |
| Get candles for symbol | `{symbol: 1, timeframe: 1, timestamp: -1}` | < 100ms |
| Get open positions | `{user_id: 1, status: 1}` | < 20ms |
| Get unread notifications | `{read: 1, created_at: -1}` | < 10ms |

### Aggregation Examples

**Daily P&L Calculation**:
```javascript
db.trades.aggregate([
  {
    $match: {
      user_id: ObjectId("..."),
      mode: "paper",
      status: "CLOSED",
      entry_time: { $gte: startOfDay, $lt: endOfDay }
    }
  },
  {
    $group: {
      _id: null,
      total_pnl: { $sum: "$pnl" },
      total_trades: { $sum: 1 },
      winning_trades: { $sum: { $cond: [{ $gt: ["$pnl", 0] }, 1, 0] } }
    }
  }
])
```

**Strategy Performance**:
```javascript
db.trades.aggregate([
  { $match: { strategy_id: ObjectId("...") } },
  { $group: {
    _id: null,
    total_pnl: { $sum: "$pnl" },
    win_rate: { $avg: { $cond: [{ $gt: ["$pnl", 0] }, 1, 0] } },
    avg_pnl: { $avg: "$pnl" }
  }}
])
```

---

## 14. DATA RETENTION POLICY

| Collection | Retention | Reason |
|------------|-----------|--------|
| candles | 30-90 days | Historical data, TTL auto-cleanup |
| logs | 90 days | Debugging, TTL auto-cleanup |
| indicator_values | 1 hour | Real-time only, TTL auto-cleanup |
| trades | Indefinite | Trade history, manual cleanup |
| backtests | Indefinite | Performance records |
| notifications | 30 days | Old notifications cleanup |
| positions | Indefinite (until closed) | Active position tracking |

---

## 15. MONGODB ATLAS CONFIGURATION

### Free Tier (M0) Settings

**Cluster Tier**: M0 Sandbox (Shared RAM, 512 MB Storage)

**Network Access**:
- IP Whitelist: 0.0.0.0/0 (allow all) OR Render's IP
- Authentication: SCRAM-SHA-1

**Backup**:
- Automatic daily backups
- Point-in-time recovery: Not available on M0 (upgrade for this)

**Connection**:
```bash
mongodb+srv://<username>:<password>@cluster0.xxxx.mongodb.net/trading_db?retryWrites=true&w=majority
```

---

## 16. WATCHLISTS COLLECTION

**Collection Name**: `watchlists`

**Purpose**: Store user's stock watchlists with symbols for quick access.

```json
{
  "_id": "ObjectId",
  "user_id": "string",
  "name": "Tech Stocks",
  "description": "Indian tech sector stocks",
  "symbols": ["RELIANCE", "TCS", "INFY", "HDFCBANK"],
  "is_default": true,
  "sort_order": 0,
  "created_at": "ISODate",
  "updated_at": "ISODate"
}
```

**Indexes**:
```javascript
{ "user_id": 1, "created_at": -1 }      // User watchlists
{ "user_id": 1, "is_default": 1 }      // Default watchlist
{ "name": 1, "user_id": 1 }             // Unique name per user
```

---

## 17. AI_SIGNALS COLLECTION

**Collection Name**: `ai_signals`

**Purpose**: Store AI-generated trading signals with confidence scores.

```json
{
  "_id": "ObjectId",
  "signal_type": "BUY",
  "symbol": "RELIANCE",
  "exchange": "NSE",
  "timeframe": "1h",
  "confidence": 85.5,
  "entry_price": 2450.00,
  "target_price": 2500.00,
  "stop_loss": 2420.00,
  "ai_reasoning": "RSI oversold, MACD bullish crossover detected",
  "indicators": {
    "rsi": 28.5,
    "macd": 45.2,
    "sma_20": 2430.00,
    "sma_50": 2410.00
  },
  "risk_reward_ratio": 2.5,
  "strategy_name": "AI Signal Generator",
  "is_executed": false,
  "is_expired": false,
  "generated_at": "ISODate",
  "expires_at": "ISODate",
  "executed_at": null,
  "executed_trade_id": null,
  "created_at": "ISODate",
  "metadata": {}
}
```

**Indexes**:
```javascript
{ "symbol": 1, "generated_at": -1 }    // Symbol history
{ "signal_type": 1, "generated_at": -1 }  // Signal type queries
{ "confidence": -1 }                    // Sort by confidence
{ "is_executed": 1, "generated_at": -1 }   // Unexecuted signals
{ "generated_at": -1 }                 // Time-based queries
```

**Signal Types**: BUY, SELL, HOLD

---

## 18. ORDERS COLLECTION

**Collection Name**: `orders`

**Purpose**: Store order details for order management system.

```json
{
  "_id": "ObjectId",
  "order_id": "ORD123456789ABC",
  "user_id": "string",
  "symbol": "RELIANCE",
  "exchange": "NSE",
  "transaction_type": "BUY",
  "order_type": "LIMIT",
  "quantity": 10,
  "filled_quantity": 0,
  "price": 2450.00,
  "trigger_price": 2448.00,
  "product_type": "INTRADAY",
  "validity": "DAY",
  "mode": "paper",
  "status": "OPEN",
  "average_price": 0,
  "pnl": 0,
  "disclosed_quantity": 0,
  "order_tag": "",
  "strategy_id": null,
  "comments": "",
  "created_at": "ISODate",
  "updated_at": "ISODate",
  "filled_at": null,
  "cancelled_at": null,
  "rejected_reason": null
}
```

**Indexes**:
```javascript
{ "user_id": 1, "created_at": -1 }      // User orders
{ "order_id": 1 }                      // Direct order lookup
{ "symbol": 1, "status": 1 }           // Symbol status queries
{ "status": 1, "created_at": -1 }      // Order status queries
{ "strategy_id": 1 }                  // Strategy orders
```

**Order Types**: MARKET, LIMIT, SL (Stop Loss), SL-M (Stop Loss Market)

**Order Status**: OPEN, FILLED, PARTIALLY_FILLED, CANCELLED, REJECTED

---

## 19. FUNDS COLLECTION

**Collection Name**: `funds`

**Purpose**: Store user's trading funds and balance information.

```json
{
  "_id": "ObjectId",
  "user_id": "string",
  "balance": 100000.00,
  "available_balance": 95000.00,
  "used_margin": 5000.00,
  "pending_balance": 0,
  "realized_pnl": 2500.00,
  "unrealized_pnl": 450.00,
  "total_deposited": 100000.00,
  "total_withdrawn": 0,
  "mode": "paper",
  "currency": "INR",
  "created_at": "ISODate",
  "updated_at": "ISODate"
}
```

**Indexes**:
```javascript
{ "user_id": 1 }                       // User funds lookup
{ "mode": 1 }                          // Mode-based queries
```

---

## 20. FUND_TRANSACTIONS COLLECTION

**Collection Name**: `fund_transactions`

**Purpose**: Record all fund deposits and withdrawals.

```json
{
  "_id": "ObjectId",
  "user_id": "string",
  "transaction_type": "deposit",
  "amount": 10000.00,
  "balance_before": 90000.00,
  "balance_after": 100000.00,
  "mode": "paper",
  "reference": "UTR123456789",
  "notes": "Added funds for trading",
  "status": "completed",
  "created_at": "ISODate"
}
```

**Indexes**:
```javascript
{ "user_id": 1, "created_at": -1 }      // User transactions
{ "transaction_type": 1 }              // Transaction type
{ "mode": 1, "created_at": -1 }        // Mode-based queries
```

---

## 21. ACTIVITY_LOGS COLLECTION

**Collection Name**: `activity_logs`

**Purpose**: Track user activities for audit and security.

```json
{
  "_id": "ObjectId",
  "user_id": "string",
  "activity_type": "login",
  "ip_address": "192.168.1.1",
  "user_agent": "Mozilla/5.0...",
  "metadata": {
    "browser": "Chrome",
    "os": "Windows"
  },
  "description": "User logged in successfully",
  "created_at": "ISODate"
}
```

**Indexes**:
```javascript
{ "user_id": 1, "created_at": -1 }      // User activity
{ "activity_type": 1, "created_at": -1 }  // Activity type queries
{ "created_at": 1 }, { expireAfterSeconds: 2592000 }  // 30-day TTL
```

**Activity Types**: login, logout, password_change, order_placed, order_cancelled, trade_executed, settings_changed

---

## 22. WEBSOCKET_CONNECTIONS COLLECTION

**Collection Name**: `websocket_connections`

**Purpose**: Track active WebSocket connections for real-time updates.

```json
{
  "_id": "ObjectId",
  "session_id": "ws_session_123456",
  "user_id": "string",
  "connection_type": "dashboard",
  "ip_address": "192.168.1.1",
  "user_agent": "Mozilla/5.0...",
  "is_active": true,
  "subscribed_symbols": ["RELIANCE", "TCS", "INFY"],
  "connected_at": "ISODate",
  "last_ping": "ISODate",
  "disconnected_at": null
}
```

**Indexes**:
```javascript
{ "session_id": 1 }                    // Session lookup
{ "user_id": 1, "is_active": 1 }       // User active connections
{ "connected_at": -1 }                 // Connection time queries
{ "is_active": 1 }                    // Active connections
```

---

## 23. UPDATED RELATIONSHIPS DIAGRAM

```
┌─────────────────────────────────────────────────────────────────────┐
│                         COLLECTION RELATIONSHIPS                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐                                                  │
│  │    user      │  (1) ──────► (N) strategies                       │
│  └──────────────┘                                                  │
│       │                                                            │
│       │         (1) ──────► (N) trades                            │
│       │                                                            │
│       │         (1) ──────► (N) positions                         │
│       │                                                            │
│       │         (1) ──────► (N) orders                             │
│       │                                                            │
│       │         (1) ──────► (N) ai_signals                         │
│       │                                                            │
│       │         (1) ──────► (N) watchlists                        │
│       │                                                            │
│       │         (1) ──────► (N) funds                              │
│       │                   └─► (N) fund_transactions               │
│       │                                                            │
│       │         (1) ──────► (N) notifications                     │
│       │                                                            │
│       │         (1) ──────► (N) activity_logs                     │
│       │                                                            │
│       │         (1) ──────► (N) websocket_connections             │
│       │                                                            │
│       │         (1) ──────► (N) backtests                         │
│       │                                                            │
│       │         (1) ──────► (N) brokers                            │
│       │                                                            │
│       │         (1) ──────► (N) logs                               │
│       │                                                            │
│  ┌──────────────┐       ┌──────────────┐                          │
│  │  strategies  │       │   candles   │                          │
│  └──────┬───────┘       └──────────────┘                          │
│         │                                                            │
│         │  (1) ──────► (N) trades                                  │
│         │                                                            │
│         │  (1) ──────► (N) positions                               │
│         │                                                            │
│         │  (1) ──────► (N) orders                                  │
│         │                                                            │
│         │  (1) ──────► (N) ai_signals                              │
│         │                                                            │
│         │  (1) ──────► (N) backtests                               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 24. INDIAN STOCK MARKET SYMBOLS

The platform is designed for Indian stock market trading with NSE/BSE exchanges:

| Symbol | Company Name | Sector |
|--------|--------------|--------|
| RELIANCE | Reliance Industries | Energy |
| TCS | Tata Consultancy Services | IT |
| INFY | Infosys | IT |
| HDFCBANK | HDFC Bank | Banking |
| ICICIBANK | ICICI Bank | Banking |
| SBIN | State Bank of India | Banking |
| AXISBANK | Axis Bank | Banking |
| LT | Larsen & Toubro | Infrastructure |
| WIPRO | Wipro | IT |
| HCLTECH | HCL Technologies | IT |
| KOTAKBANK | Kotak Mahindra Bank | Banking |
| MARUTI | Maruti Suzuki | Auto |
| SUNPHARMA | Sun Pharma | Pharma |
| TITAN | Titan | Retail |
| BAJFINANCE | Bajaj Finance | Finance |

---

*End of Database Design Document*