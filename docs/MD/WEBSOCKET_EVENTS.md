# WEBSOCKET EVENTS DOCUMENTATION

## Overview
Real-time communication using Socket.IO protocol. WebSocket provides low-latency updates for prices, trades, positions, and system events.

---

## CONNECTION

### URL
```
Production: wss://your-backend.onrender.com/socket.io/
Development: http://localhost:5000/socket.io/
```

### Connection Parameters

```javascript
import { io } from 'socket.io-client';

const socket = io(import.meta.env.VITE_SOCKET_URL, {
  auth: {
    token: localStorage.getItem('token')  // JWT token
  },
  transports: ['websocket'],              // Use WebSocket only
  reconnection: true,
  reconnectionAttempts: Infinity,
  reconnectionDelay: 1000,
  reconnectionDelayMax: 30000,
  timeout: 20000,
});
```

### Connection Lifecycle

```javascript
socket.on('connect', () => {
  console.log('Connected to WebSocket server');
  // Subscribe to channels after connect
  socket.emit('subscribe', { channels: ['prices', 'trades', 'positions', 'signals'] });
});

socket.on('disconnect', (reason) => {
  console.log('Disconnected:', reason);
  // Will auto-reconnect
});

socket.on('connect_error', (error) => {
  console.error('Connection error:', error.message);
});
```

---

## CLIENT EVENTS (Frontend → Backend)

### 1. Subscribe to Channels

**Event**: `subscribe`

**Payload**:
```json
{
  "channels": ["prices", "trades", "positions", "signals", "bot_status"]
}
```

**Description**: Subscribe to receive updates for specific channels.

**Example**:
```javascript
socket.emit('subscribe', { channels: ['prices', 'trades'] });
```

---

### 2. Unsubscribe from Channels

**Event**: `unsubscribe`

**Payload**:
```json
{
  "channels": ["prices"]
}
```

**Description**: Unsubscribe from specific channels.

**Example**:
```javascript
socket.emit('unsubscribe', { channels: ['prices'] });
```

---

### 3. Ping

**Event**: `ping`

**Description**: Keep connection alive, measure latency.

**Example**:
```javascript
socket.emit('ping');
```

---

### 4. Request Initial Data

**Event**: `request_snapshot`

**Payload**:
```json
{
  "channels": ["positions", "trades"]
}
```

**Description**: Request current state snapshot when connecting.

**Example**:
```javascript
socket.emit('request_snapshot', { channels: ['positions', 'trades'] });
```

---

## SERVER EVENTS (Backend → Frontend)

### 1. Connection Confirmation

**Event**: `connected`

**Payload**:
```json
{
  "status": "ok",
  "server_time": "2024-01-15T10:30:00Z",
  "session_id": "session_abc123"
}
```

**Description**: Sent after successful connection and authentication.

---

### 2. Pong (Latency Response)

**Event**: `pong`

**Payload**:
```json
{
  "timestamp": 1705315800000,
  "latency_ms": 25
}
```

**Description**: Response to ping for latency measurement.

---

### 3. Price Update

**Event**: `price`

**Payload**:
```json
{
  "symbol": "BTC/USDT",
  "price": 45000.00,
  "bid": 44999.50,
  "ask": 45000.50,
  "volume": 1500.5,
  "change_24h": 2.5,
  "change_percent_24h": 0.55,
  "high_24h": 45500.00,
  "low_24h": 44800.00,
  "timestamp": 1705315800000
}
```

**Description**: Real-time price update for a symbol.

**Update Frequency**: Every 1-5 seconds (depending on broker)

**Frontend Handler**:
```javascript
socket.on('price', (data) => {
  // Update price in store
  useMarketStore.getState().updatePrice(data);
  // Update chart if viewing this symbol
  if (currentSymbol === data.symbol) {
    updateChart(data);
  }
});
```

---

### 4. Multiple Prices (Batch)

**Event**: `prices`

**Payload**:
```json
{
  "prices": [
    { "symbol": "BTC/USDT", "price": 45000.00 },
    { "symbol": "ETH/USDT", "price": 2500.00 },
    { "symbol": "SOL/USDT", "price": 100.00 }
  ],
  "timestamp": 1705315800000
}
```

**Description**: Batch price update for multiple symbols.

---

### 5. Trade Executed

**Event**: `trade`

**Payload**:
```json
{
  "trade_id": "trade_123",
  "strategy_id": "strat_456",
  "strategy_name": "RSI Momentum",
  "symbol": "BTC/USDT",
  "side": "BUY",
  "quantity": 0.01,
  "entry_price": 45000.00,
  "order_type": "market",
  "mode": "paper",
  "status": "filled",
  "commission": 0.10,
  "entry_time": "2024-01-15T10:30:00Z"
}
```

**Description**: Notification when a trade is executed.

**Frontend Handler**:
```javascript
socket.on('trade', (data) => {
  // Add to trade list
  useTradingStore.getState().addTrade(data);
  // Show notification
  showNotification(`Trade ${data.side}: ${data.symbol}`);
  // Update balance if needed
  updateBalance();
});
```

---

### 6. Trade Closed

**Event**: `trade_closed`

**Payload**:
```json
{
  "trade_id": "trade_123",
  "strategy_id": "strat_456",
  "symbol": "BTC/USDT",
  "side": "BUY",
  "quantity": 0.01,
  "entry_price": 45000.00,
  "exit_price": 45500.00,
  "pnl": 5.00,
  "pnl_percent": 0.111,
  "commission": 0.10,
  "mode": "paper",
  "exit_reason": "take_profit",
  "exit_time": "2024-01-15T12:00:00Z",
  "duration_minutes": 90
}
```

**Description**: Notification when a trade is closed (SL, TP, or manual).

**Frontend Handler**:
```javascript
socket.on('trade_closed', (data) => {
  useTradingStore.getState().updateTrade(data);
  showNotification(`Trade closed: ${data.exit_reason}, P&L: $${data.pnl}`);
});
```

---

### 7. Position Update

**Event**: `position`

**Payload**:
```json
{
  "position_id": "pos_123",
  "strategy_id": "strat_456",
  "symbol": "BTC/USDT",
  "side": "BUY",
  "quantity": 0.01,
  "entry_price": 45000.00,
  "current_price": 45500.00,
  "unrealized_pnl": 5.00,
  "unrealized_pnl_percent": 0.111,
  "stop_loss": 44550.00,
  "take_profit": 45900.00,
  "mode": "paper",
  "updated_at": "2024-01-15T10:35:00Z"
}
```

**Description**: Real-time update of open position P&L.

**Update Frequency**: Every price update

**Frontend Handler**:
```javascript
socket.on('position', (data) => {
  useTradingStore.getState().updatePosition(data);
});
```

---

### 8. Position Opened (New Position)

**Event**: `position_opened`

**Payload**:
```json
{
  "position_id": "pos_123",
  "strategy_id": "strat_456",
  "symbol": "BTC/USDT",
  "side": "BUY",
  "quantity": 0.01,
  "entry_price": 45000.00,
  "current_price": 45000.00,
  "unrealized_pnl": 0.00,
  "unrealized_pnl_percent": 0.0,
  "stop_loss": 44550.00,
  "take_profit": 45900.00,
  "mode": "paper",
  "opened_at": "2024-01-15T10:30:00Z"
}
```

**Description**: New position opened.

---

### 9. Position Closed

**Event**: `position_closed`

**Payload**:
```json
{
  "position_id": "pos_123",
  "symbol": "BTC/USDT",
  "exit_price": 45500.00,
  "realized_pnl": 5.00,
  "exit_reason": "take_profit",
  "closed_at": "2024-01-15T12:00:00Z"
}
```

**Description**: Position closed, no longer active.

---

### 10. Signal Generated

**Event**: `signal`

**Payload**:
```json
{
  "strategy_id": "strat_456",
  "strategy_name": "RSI Momentum",
  "symbol": "BTC/USDT",
  "signal": "BUY",
  "signal_type": "entry",
  "reason": "RSI < 30",
  "price": 45000.00,
  "timestamp": "2024-01-15T10:30:00Z",
  "indicators": {
    "RSI_14": 28.5,
    "EMA_9": 44900.00,
    "EMA_21": 44850.00
  }
}
```

**Description**: Trading signal generated by strategy.

**Frontend Handler**:
```javascript
socket.on('signal', (data) => {
  // Add to signal log
  useSignalStore.getState().addSignal(data);
  // Show prominent notification for entry signals
  if (data.signal_type === 'entry') {
    showAlert(`${data.signal} signal for ${data.symbol}: ${data.reason}`);
  }
});
```

---

### 11. Bot Status Change

**Event**: `bot_status`

**Payload**:
```json
{
  "strategy_id": "strat_456",
  "strategy_name": "RSI Momentum",
  "status": "running",
  "mode": "paper",
  "last_signal": "BUY",
  "last_signal_time": "2024-01-15T10:30:00Z",
  "trades_today": 3,
  "pnl_today": 15.00,
  "uptime_seconds": 3600
}
```

**Description**: Bot status change notification.

**Status Values**: `starting`, `running`, `stopping`, `stopped`, `paused`, `error`

**Frontend Handler**:
```javascript
socket.on('bot_status', (data) => {
  useBotStore.getState().updateBotStatus(data);
  // Show notification on status change
  if (data.status === 'stopped' || data.status === 'error') {
    showNotification(`Bot ${data.strategy_name}: ${data.status}`);
  }
});
```

---

### 12. Stop Loss Hit

**Event**: `sl_hit`

**Payload**:
```json
{
  "position_id": "pos_123",
  "symbol": "BTC/USDT",
  "entry_price": 45000.00,
  "exit_price": 44550.00,
  "quantity": 0.01,
  "loss": -4.50,
  "loss_percent": -1.0,
  "mode": "paper",
  "trigger_price": 44550.00,
  "timestamp": "2024-01-15T11:00:00Z"
}
```

**Description**: Stop loss triggered.

---

### 13. Take Profit Hit

**Event**: `tp_hit`

**Payload**:
```json
{
  "position_id": "pos_123",
  "symbol": "BTC/USDT",
  "entry_price": 45000.00,
  "exit_price": 45900.00,
  "quantity": 0.01,
  "profit": 9.00,
  "profit_percent": 2.0,
  "mode": "paper",
  "trigger_price": 45900.00,
  "timestamp": "2024-01-15T12:00:00Z"
}
```

**Description**: Take profit triggered.

---

### 14. Balance Update

**Event**: `balance`

**Payload**:
```json
{
  "mode": "paper",
  "balance": 10000.00,
  "available": 9850.00,
  "equity": 10050.00,
  "unrealized_pnl": 50.00,
  "currency": "USDT",
  "updated_at": "2024-01-15T10:35:00Z"
}
```

**Description**: Account balance update.

---

### 15. Notification

**Event**: `notification`

**Payload**:
```json
{
  "id": "notif_123",
  "type": "error",
  "title": "Connection Lost",
  "message": "Lost connection to broker API. Attempting to reconnect...",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Description**: System notification (errors, warnings, info).

---

### 16. Backtest Progress

**Event**: `backtest_progress`

**Payload**:
```json
{
  "backtest_id": "bt_123",
  "status": "running",
  "progress": 45,
  "processed_candles": 4500,
  "total_candles": 10000,
  "current_date": "2023-06-15",
  "estimated_completion": "2023-06-15T10:35:00Z"
}
```

**Description**: Backtest execution progress.

---

### 17. Backtest Complete

**Event**: `backtest_complete`

**Payload**:
```json
{
  "backtest_id": "bt_123",
  "status": "completed",
  "total_return": 25.0,
  "win_rate": 60.0,
  "sharpe_ratio": 1.5,
  "max_drawdown": 8.5
}
```

**Description**: Backtest finished.

---

### 18. Snapshot Response

**Event**: `snapshot`

**Payload**:
```json
{
  "positions": [...],
  "trades": [...],
  "bots": [...],
  "balance": {...}
}
```

**Description**: Response to `request_snapshot` event with current state.

---

## CHANNEL SUBSCRIPTIONS

### Recommended Subscription Sets

**Full Trading Dashboard**:
```javascript
socket.emit('subscribe', {
  channels: ['prices', 'trades', 'positions', 'signals', 'bot_status', 'balance']
});
```

**Price Only (Chart View)**:
```javascript
socket.emit('subscribe', {
  channels: ['prices']
});
```

**Bot Monitoring Only**:
```javascript
socket.emit('subscribe', {
  channels: ['bot_status', 'signals']
});
```

---

## RECONNECTION STRATEGY

### Automatic Reconnection

```javascript
const socket = io(url, {
  reconnection: true,
  reconnectionAttempts: Infinity,  // Keep trying forever
  reconnectionDelay: 1000,           // Start with 1 second
  reconnectionDelayMax: 30000,      // Max 30 seconds between attempts
  reconnectionDelayMultiplier: 2,  // Double delay each time
});
```

### Reconnection Flow

1. Connection lost
2. Wait 1 second, attempt reconnect
3. If fails, wait 2 seconds, attempt reconnect
4. If fails, wait 4 seconds...
5. Continue until max delay (30 seconds)
6. Continue forever (trading requires persistent connection)

### On Reconnect

```javascript
socket.on('reconnect', (attemptNumber) => {
  console.log(`Reconnected after ${attemptNumber} attempts`);
  // Re-subscribe to all channels
  socket.emit('subscribe', {
    channels: ['prices', 'trades', 'positions', 'signals', 'bot_status']
  });
  // Request fresh data snapshot
  socket.emit('request_snapshot', {
    channels: ['positions', 'trades', 'balance']
  });
});
```

---

## RATE LIMITING

### Client-Side Rate Limiting

Avoid overwhelming the server with subscription requests:

```javascript
// Debounce subscription changes
const debouncedSubscribe = _.debounce((channels) => {
  socket.emit('subscribe', { channels });
}, 100);

// Only call when channels actually change
debouncedSubscribe(['prices', 'trades']);
```

---

## ERROR HANDLING

### Connection Errors

```javascript
socket.on('connect_error', (error) => {
  console.error('Connection error:', error.message);
  // Possible errors:
  // - "invalid token" -> Re-authenticate
  // - "connection refused" -> Server down
  // - "timeout" -> Network issues
});

socket.on('error', (error) => {
  console.error('Socket error:', error);
});
```

---

## TESTING

### Test Events with cURL

```bash
# Test WebSocket connection (via Socket.IO test tool)
# Not directly testable with cURL, use socket.io-test-tool or browser dev tools
```

### Browser DevTools

1. Open Chrome DevTools → Network tab
2. Filter by "webSocket" or "socket.io"
3. View Frames for messages

---

*End of WebSocket Events Documentation*