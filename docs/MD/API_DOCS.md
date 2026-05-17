# API DOCUMENTATION

## Base URL
```
Production: https://your-backend.onrender.com/api/v1
Development: http://localhost:5000/api/v1
```

## Authentication

All API requests (except login) require a JWT token in the Authorization header.

```
Authorization: Bearer <jwt_token>
```

**Token Expiry**: 1 hour

---

## 1. AUTHENTICATION ENDPOINTS

### POST /auth/login

Login with master password (from environment variables).

**Request**:
```json
{
  "password": "your-master-password"
}
```

**Response** (200):
```json
{
  "success": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 3600,
  "user": {
    "id": "user_123",
    "name": "Trading Owner",
    "twofa_enabled": false
  }
}
```

**Error** (401):
```json
{
  "error": "Invalid credentials"
}
```

---

### POST /auth/2fa

Verify 2FA code (if enabled).

**Request**:
```json
{
  "code": "123456"
}
```

**Response** (200):
```json
{
  "success": true,
  "message": "2FA verified successfully"
}
```

**Error** (401):
```json
{
  "error": "Invalid 2FA code"
}
```

---

### POST /auth/refresh

Refresh JWT token before expiry.

**Headers**: `Authorization: Bearer <current_token>`

**Response** (200):
```json
{
  "success": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 3600
}
```

---

### POST /auth/logout

Invalidate current token.

**Headers**: `Authorization: Bearer <token>`

**Response** (200):
```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

---

### GET /auth/status

Check authentication status.

**Headers**: `Authorization: Bearer <token>`

**Response** (200):
```json
{
  "authenticated": true,
  "user": {
    "id": "user_123",
    "name": "Trading Owner"
  },
  "twofa_enabled": false,
  "token_expires_at": "2024-01-15T11:00:00Z"
}
```

---

## 2. STRATEGY ENDPOINTS

### GET /strategies

List all strategies.

**Headers**: `Authorization: Bearer <token>`

**Query Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| mode | string | Filter by "paper" or "live" |
| is_active | boolean | Filter by active status |
| symbol | string | Filter by symbol |
| page | int | Page number (default: 1) |
| limit | int | Items per page (default: 20) |

**Response** (200):
```json
{
  "success": true,
  "strategies": [
    {
      "_id": "strat_123",
      "strategy_name": "RSI Momentum",
      "symbol": "BTC/USDT",
      "timeframe": "1h",
      "mode": "paper",
      "broker": "binance",
      "is_active": true,
      "last_evaluated_at": "2024-01-15T10:00:00Z",
      "created_at": "2024-01-10T08:00:00Z"
    }
  ],
  "total": 5,
  "page": 1,
  "pages": 1
}
```

---

### POST /strategies

Create a new strategy.

**Headers**: `Authorization: Bearer <token>`

**Request**:
```json
{
  "strategy_name": "RSI EMA Combo",
  "symbol": "BTC/USDT",
  "timeframe": "1h",
  "mode": "paper",
  "broker": "binance",
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
      "indicator_id": "ind_001",
      "indicator_name": "RSI",
      "operator": "less_than",
      "value": 30,
      "logic": "AND"
    },
    {
      "indicator_id": "ind_002",
      "indicator_name": "EMA_9",
      "operator": "crosses_above",
      "value": "EMA_21",
      "logic": "AND"
    }
  ],
  "exit_conditions": [
    {
      "indicator_id": "ind_001",
      "indicator_name": "RSI",
      "operator": "greater_than",
      "value": 70,
      "logic": "OR"
    }
  ],
  "risk_settings": {
    "stop_loss_percent": 1.0,
    "take_profit_percent": 2.0,
    "trailing_stop_enabled": true,
    "trailing_stop_percent": 0.5,
    "position_size_type": "calculated",
    "position_size_percent": 10
  }
}
```

**Response** (201):
```json
{
  "success": true,
  "strategy_id": "strat_456",
  "message": "Strategy created successfully"
}
```

**Error** (400):
```json
{
  "error": "Invalid strategy configuration",
  "details": ["Entry conditions required"]
}
```

---

### GET /strategies/:id

Get strategy details by ID.

**Headers**: `Authorization: Bearer <token>`

**Response** (200):
```json
{
  "success": true,
  "strategy": {
    "_id": "strat_123",
    "strategy_name": "RSI Momentum",
    "symbol": "BTC/USDT",
    "timeframe": "1h",
    "mode": "paper",
    "indicators": [...],
    "entry_conditions": [...],
    "exit_conditions": [...],
    "risk_settings": {...},
    "is_active": true,
    "created_at": "2024-01-10T08:00:00Z",
    "updated_at": "2024-01-15T10:00:00Z"
  }
}
```

---

### PUT /strategies/:id

Update strategy.

**Headers**: `Authorization: Bearer <token>`

**Request**: Same as POST, include fields to update.

**Response** (200):
```json
{
  "success": true,
  "message": "Strategy updated successfully"
}
```

---

### DELETE /strategies/:id

Delete strategy.

**Headers**: `Authorization: Bearer <token>`

**Response** (200):
```json
{
  "success": true,
  "message": "Strategy deleted successfully"
}
```

---

### POST /strategies/:id/clone

Clone an existing strategy.

**Headers**: `Authorization: Bearer <token>`

**Request**:
```json
{
  "new_name": "RSI Momentum Copy"
}
```

**Response** (201):
```json
{
  "success": true,
  "strategy_id": "strat_789",
  "message": "Strategy cloned successfully"
}
```

---

### POST /strategies/:id/test

Test strategy conditions against current data (without executing).

**Headers**: `Authorization: Bearer <token>`

**Response** (200):
```json
{
  "success": true,
  "signal": "BUY",
  "indicators": {
    "RSI_14": 28.5,
    "EMA_9": 44900.00,
    "EMA_21": 44850.00
  },
  "entry_signal": true,
  "exit_signal": false,
  "timestamp": "2024-01-15T10:00:00Z"
}
```

---

## 3. TRADING ENDPOINTS

### GET /trades

Get trade history.

**Headers**: `Authorization: Bearer <token>`

**Query Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| mode | string | "paper" or "live" |
| status | string | "OPEN", "CLOSED", "CANCELLED" |
| symbol | string | Filter by symbol |
| strategy_id | string | Filter by strategy |
| start_date | string | Start date (ISO) |
| end_date | string | End date (ISO) |
| page | int | Page number |
| limit | int | Items per page (default: 50) |

**Response** (200):
```json
{
  "success": true,
  "trades": [
    {
      "_id": "trade_123",
      "strategy_name": "RSI Momentum",
      "symbol": "BTC/USDT",
      "side": "BUY",
      "entry_price": 45000.00,
      "exit_price": 45500.00,
      "quantity": 0.01,
      "pnl": 5.00,
      "pnl_percent": 0.111,
      "commission": 0.10,
      "mode": "paper",
      "status": "CLOSED",
      "entry_time": "2024-01-15T10:00:00Z",
      "exit_time": "2024-01-15T12:00:00Z",
      "duration_minutes": 120,
      "exit_reason": "take_profit"
    }
  ],
  "total": 150,
  "page": 1,
  "pages": 3,
  "summary": {
    "total_pnl": 250.50,
    "winning_trades": 45,
    "losing_trades": 30,
    "win_rate": 60.0
  }
}
```

---

### GET /trades/active

Get open positions.

**Headers**: `Authorization: Bearer <token>`

**Query Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| mode | string | "paper" or "live" |
| symbol | string | Filter by symbol |

**Response** (200):
```json
{
  "success": true,
  "positions": [
    {
      "_id": "pos_123",
      "strategy_name": "RSI Momentum",
      "symbol": "BTC/USDT",
      "side": "BUY",
      "entry_price": 45000.00,
      "quantity": 0.01,
      "current_price": 45500.00,
      "unrealized_pnl": 5.00,
      "unrealized_pnl_percent": 0.111,
      "stop_loss": 44550.00,
      "take_profit": 45900.00,
      "mode": "paper",
      "opened_at": "2024-01-15T10:00:00Z"
    }
  ]
}
```

---

### POST /trades/execute

Execute a manual trade.

**Headers**: `Authorization: Bearer <token>`

**Request**:
```json
{
  "strategy_id": "strat_123",
  "symbol": "BTC/USDT",
  "side": "buy",
  "quantity": 0.01,
  "order_type": "market",
  "limit_price": null,
  "stop_loss": 44500.00,
  "take_profit": 46000.00
}
```

**Response** (201):
```json
{
  "success": true,
  "trade": {
    "_id": "trade_456",
    "status": "filled",
    "entry_price": 45000.00,
    "mode": "paper",
    "entry_time": "2024-01-15T10:05:00Z"
  },
  "message": "Paper trade executed successfully"
}
```

---

### POST /trades/:id/close

Close an open position.

**Headers**: `Authorization: Bearer <token>`

**Request**:
```json
{
  "order_type": "market"
}
```

**Response** (200):
```json
{
  "success": true,
  "trade": {
    "_id": "trade_456",
    "status": "CLOSED",
    "exit_price": 45500.00,
    "pnl": 5.00,
    "exit_time": "2024-01-15T12:00:00Z"
  },
  "message": "Position closed successfully"
}
```

---

### POST /trades/:id/cancel

Cancel a pending order.

**Headers**: `Authorization: Bearer <token>`

**Response** (200):
```json
{
  "success": true,
  "message": "Order cancelled successfully"
}
```

---

## 4. BOT CONTROL ENDPOINTS

### POST /bot/start

Start a trading bot.

**Headers**: `Authorization: Bearer <token>`

**Request**:
```json
{
  "strategy_id": "strat_123"
}
```

**Response** (200):
```json
{
  "success": true,
  "bot": {
    "strategy_id": "strat_123",
    "status": "running",
    "mode": "paper",
    "started_at": "2024-01-15T10:00:00Z"
  },
  "message": "Bot started in paper trading mode"
}
```

---

### POST /bot/stop

Stop a trading bot.

**Headers**: `Authorization: Bearer <token>`

**Request**:
```json
{
  "strategy_id": "strat_123"
}
```

**Response** (200):
```json
{
  "success": true,
  "message": "Bot stopped successfully"
}
```

---

### POST /bot/mode

Switch global trading mode (paper/live).

**Headers**: `Authorization: Bearer <token>`

**Request**:
```json
{
  "mode": "live"
}
```

**Response** (200):
```json
{
  "success": true,
  "current_mode": "live",
  "message": "Switched to live trading mode"
}
```

---

### GET /bot/status

Get status of all bots.

**Headers**: `Authorization: Bearer <token>`

**Response** (200):
```json
{
  "success": true,
  "bots": [
    {
      "strategy_id": "strat_123",
      "strategy_name": "RSI Momentum",
      "status": "running",
      "mode": "paper",
      "last_signal": "BUY",
      "last_signal_time": "2024-01-15T10:30:00Z",
      "trades_today": 3,
      "pnl_today": 15.00
    }
  ],
  "global_mode": "paper"
}
```

---

## 5. BROKER ENDPOINTS

### POST /broker/connect

Connect a broker API.

**Headers**: `Authorization: Bearer <token>`

**Request**:
```json
{
  "broker": "binance",
  "api_key": "your-api-key",
  "api_secret": "your-api-secret",
  "testnet": true
}
```

**Response** (200):
```json
{
  "success": true,
  "broker": {
    "broker_name": "binance",
    "is_connected": true,
    "testnet_enabled": true,
    "connection_tested": true
  },
  "account": {
    "balance": 10000.00,
    "available": 10000.00
  },
  "message": "Broker connected successfully"
}
```

**Error** (400):
```json
{
  "error": "Invalid API credentials",
  "details": "Could not verify API key with broker"
}
```

---

### GET /broker/status

Get broker connection status.

**Headers**: `Authorization: Bearer <token>`

**Query**: `?broker=binance`

**Response** (200):
```json
{
  "success": true,
  "broker": {
    "broker_name": "binance",
    "is_connected": true,
    "testnet_enabled": true,
    "last_connected_at": "2024-01-15T10:00:00Z",
    "connection_status": "healthy",
    "rate_limit_remaining": 1150
  }
}
```

---

### DELETE /broker/disconnect

Disconnect a broker.

**Headers**: `Authorization: Bearer <token>`

**Request**:
```json
{
  "broker": "binance"
}
```

**Response** (200):
```json
{
  "success": true,
  "message": "Broker disconnected successfully"
}
```

---

### GET /broker/balance

Get account balance from broker.

**Headers**: `Authorization: Bearer <token>`

**Query**: `?broker=binance&mode=paper`

**Response** (200):
```json
{
  "success": true,
  "mode": "paper",
  "balance": {
    "total": 10000.00,
    "available": 9850.00,
    "used": 150.00,
    "currency": "USDT"
  }
}
```

---

## 6. MARKET DATA ENDPOINTS

### GET /market/candles

Get OHLCV candle data.

**Headers**: `Authorization: Bearer <token>`

**Query Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| symbol | string | Trading pair (required) |
| timeframe | string | 1m, 5m, 15m, 30m, 1h, 4h, 1d |
| limit | int | Number of candles (default: 100) |
| start | string | Start timestamp |
| end | string | End timestamp |

**Example**: `GET /market/candles?symbol=BTC/USDT&timeframe=1h&limit=100`

**Response** (200):
```json
{
  "success": true,
  "symbol": "BTC/USDT",
  "timeframe": "1h",
  "candles": [
    {
      "timestamp": "2024-01-15T10:00:00Z",
      "open": 45000.00,
      "high": 45500.00,
      "low": 44800.00,
      "close": 45200.00,
      "volume": 1500.5,
      "quote_volume": 67663800.00,
      "trades": 12345
    }
  ],
  "count": 100
}
```

---

### GET /market/price/:symbol

Get current price for a symbol.

**Headers**: `Authorization: Bearer <token>`

**Response** (200):
```json
{
  "success": true,
  "symbol": "BTC/USDT",
  "price": 45200.00,
  "change_24h": 2.5,
  "change_percent_24h": 0.55,
  "high_24h": 45500.00,
  "low_24h": 44800.00,
  "volume_24h": 35000.00,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

### GET /market/symbols

List available trading symbols.

**Headers**: `Authorization: Bearer <token>`

**Query**: `?broker=binance`

**Response** (200):
```json
{
  "success": true,
  "symbols": [
    { "symbol": "BTC/USDT", "base": "BTC", "quote": "USDT", "precision": 8 },
    { "symbol": "ETH/USDT", "base": "ETH", "quote": "USDT", "precision": 8 },
    { "symbol": "SOL/USDT", "base": "SOL", "quote": "USDT", "precision": 8 }
  ],
  "count": 150
}
```

---

## 7. BACKTEST ENDPOINTS

### POST /backtest/run

Start a backtest (async).

**Headers**: `Authorization: Bearer <token>`

**Request**:
```json
{
  "strategy_id": "strat_123",
  "symbol": "BTC/USDT",
  "timeframe": "1h",
  "start_date": "2023-01-01",
  "end_date": "2023-12-31",
  "initial_capital": 10000,
  "commission_percent": 0.1,
  "slippage_percent": 0.05
}
```

**Response** (202):
```json
{
  "success": true,
  "backtest_id": "bt_123",
  "status": "queued",
  "message": "Backtest started in background"
}
```

---

### GET /backtest/:id

Get backtest status.

**Headers**: `Authorization: Bearer <token>`

**Response** (200):
```json
{
  "success": true,
  "backtest": {
    "_id": "bt_123",
    "status": "running",
    "progress": 45,
    "current_candle": 4500,
    "total_candles": 10000,
    "started_at": "2024-01-15T10:00:00Z"
  }
}
```

---

### GET /backtest/:id/results

Get backtest results (when completed).

**Headers**: `Authorization: Bearer <token>`

**Response** (200):
```json
{
  "success": true,
  "results": {
    "total_return": 25.0,
    "annual_return": 25.0,
    "total_trades": 150,
    "winning_trades": 90,
    "losing_trades": 60,
    "win_rate": 60.0,
    "sharpe_ratio": 1.5,
    "max_drawdown": 8.5,
    "profit_factor": 1.8,
    "avg_trade_duration": 240,
    "trades": [...],
    "equity_curve": [...]
  }
}
```

---

### GET /backtest/history

List past backtests.

**Headers**: `Authorization: Bearer <token>`

**Query**: `?strategy_id=strat_123`

**Response** (200):
```json
{
  "success": true,
  "backtests": [
    {
      "_id": "bt_123",
      "strategy_name": "RSI Momentum",
      "symbol": "BTC/USDT",
      "timeframe": "1h",
      "total_return": 25.0,
      "win_rate": 60.0,
      "status": "completed",
      "created_at": "2024-01-15T10:00:00Z"
    }
  ]
}
```

---

## 8. DASHBOARD ENDPOINTS

### GET /dashboard

Get dashboard overview data.

**Headers**: `Authorization: Bearer <token>`

**Response** (200):
```json
{
  "success": true,
  "dashboard": {
    "mode": "paper",
    "global_mode": "paper",
    "account": {
      "paper_balance": 10000.00,
      "live_balance": 5000.00,
      "total_equity": 15000.00
    },
    "today": {
      "pnl": 25.50,
      "pnl_percent": 0.25,
      "trades": 3,
      "win_rate": 66.6
    },
    "positions": 2,
    "active_bots": 1,
    "recent_trades": [...],
    "performance": {
      "daily": [...],
      "weekly": [...],
      "monthly": [...]
    }
  }
}
```

---

## 9. SETTINGS ENDPOINTS

### GET /settings

Get user settings.

**Headers**: `Authorization: Bearer <token>`

**Response** (200):
```json
{
  "success": true,
  "settings": {
    "default_mode": "paper",
    "timezone": "UTC",
    "telegram_enabled": true,
    "telegram_chat_id": "123456789",
    "notifications": {
      "trade_entry": true,
      "trade_exit": true,
      "sl_hit": true,
      "tp_hit": true,
      "errors": true,
      "daily_summary": true
    },
    "risk_defaults": {
      "max_daily_loss_percent": 5.0,
      "risk_per_trade_percent": 1.0,
      "max_open_positions": 3
    }
  }
}
```

---

### PUT /settings

Update user settings.

**Headers**: `Authorization: Bearer <token>`

**Request**:
```json
{
  "default_mode": "live",
  "notifications": {
    "daily_summary": true
  },
  "risk_defaults": {
    "max_daily_loss_percent": 3.0
  }
}
```

**Response** (200):
```json
{
  "success": true,
  "message": "Settings updated successfully"
}
```

---

## 10. NOTIFICATIONS ENDPOINTS

### GET /notifications

Get user notifications.

**Headers**: `Authorization: Bearer <token>`

**Query Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| unread_only | boolean | Only unread notifications |
| type | string | Filter by type |
| limit | int | Items per page |

**Response** (200):
```json
{
  "success": true,
  "notifications": [
    {
      "_id": "notif_123",
      "type": "trade_entry",
      "title": "Buy Order Filled",
      "message": "Bought 0.01 BTCUSDT at $45,000",
      "read": false,
      "created_at": "2024-01-15T10:30:00Z"
    }
  ],
  "unread_count": 3
}
```

---

### PUT /notifications/:id/read

Mark notification as read.

**Headers**: `Authorization: Bearer <token>`

**Response** (200):
```json
{
  "success": true,
  "message": "Notification marked as read"
}
```

---

### PUT /notifications/read-all

Mark all notifications as read.

**Headers**: `Authorization: Bearer <token>`

**Response** (200):
```json
{
  "success": true,
  "message": "All notifications marked as read"
}
```

---

## 11. LOGS ENDPOINTS

### GET /logs

Get application logs.

**Headers**: `Authorization: Bearer <token>`

**Query Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| level | string | INFO, ERROR, WARNING |
| category | string | TRADE, BROKER, SIGNAL |
| start_date | string | Start date |
| end_date | string | End date |
| limit | int | Items per page (default: 100) |

**Response** (200):
```json
{
  "success": true,
  "logs": [
    {
      "_id": "log_123",
      "level": "INFO",
      "category": "TRADE",
      "message": "Buy signal detected for BTC/USDT",
      "metadata": {
        "strategy_id": "strat_123",
        "price": 45000
      },
      "created_at": "2024-01-15T10:30:00Z"
    }
  ],
  "count": 100
}
```

---

## 12. HEALTH CHECK

### GET /health

System health check (no auth required).

**Response** (200):
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "checks": {
    "mongo": "connected",
    "redis": "connected",
    "celery": "running"
  },
  "version": "1.0.0"
}
```

**Response** (503):
```json
{
  "status": "unhealthy",
  "checks": {
    "mongo": "connected",
    "redis": "disconnected",
    "celery": "notresponding"
  }
}
```

---

## ERROR RESPONSE FORMAT

All errors follow this format:

```json
{
  "error": "Error message",
  "code": "ERROR_CODE",
  "details": {} // Optional additional info
}
```

**Common Error Codes**:
| Code | HTTP Status | Description |
|------|-------------|-------------|
| INVALID_CREDENTIALS | 401 | Login failed |
| TOKEN_EXPIRED | 401 | JWT expired |
| UNAUTHORIZED | 403 | Access denied |
| NOT_FOUND | 404 | Resource not found |
| VALIDATION_ERROR | 400 | Invalid input |
| BROKER_ERROR | 502 | Broker API error |
| RATE_LIMITED | 429 | Too many requests |

---

*End of API Documentation*