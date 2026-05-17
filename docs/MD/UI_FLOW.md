# UI FLOW DOCUMENTATION

## Overview
User interface flow and navigation for the automated trading platform. This document describes the pages, navigation, and user interactions.

---

## NAVIGATION STRUCTURE

### Layout Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              TOP HEADER                                  │
│  [Logo]  Paper/Live Toggle    $Balance    [Bot Status] [🔔] [⚙️] [Logout]│
├─────────────┬───────────────────────────────────────────────────────────┤
│             │                                                            │
│  SIDEBAR    │                    MAIN CONTENT                           │
│             │                                                            │
│  Dashboard  │   (Content changes based on selected page)               │
│  Strategies │                                                            │
│  Bots       │                                                            │
│  Trades     │                                                            │
│  Backtest   │                                                            │
│  Logs       │                                                            │
│  Settings   │                                                            │
│             │                                                            │
└─────────────┴───────────────────────────────────────────────────────────┘
```

### Responsive Breakpoints
- **Desktop**: ≥ 1024px (full sidebar)
- **Tablet**: 768px - 1023px (collapsible sidebar)
- **Mobile**: < 768px (hamburger menu, stacked layout)

---

## PAGE FLOWS

---

## 1. LOGIN PAGE

### Route: `/login`

### Flow
```
1. User opens application
2. System checks for existing token
   ├── Valid token → Redirect to Dashboard
   └── No token → Show Login page

3. User enters password
4. System validates credentials
   ├── Success → Store JWT, Redirect to Dashboard
   └── Failure → Show error message

5. (Optional) If 2FA enabled → Show 2FA input
6. User enters 2FA code
7. System validates → Redirect to Dashboard
```

### UI Elements
- Logo/Brand name
- Password input field
- "Login" button
- Error message area (hidden by default)
- (Conditional) 2FA code input

### States
- Default: Empty form
- Loading: "Logging in..." spinner
- Error: Red error message below input
- 2FA: Show 2FA input field

---

## 2. DASHBOARD PAGE

### Route: `/dashboard`

### Purpose
Overview of trading account, positions, and performance.

### UI Sections

```
┌─────────────────────────────────────────────────────────────────────┐
│  MODE TOGGLE: [ Paper ● ] [ ○ Live ]     Last updated: 10:30:00    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐   │
│  │   BALANCE       │  │   TODAY'S P&L    │  │   ACTIVE        │   │
│  │   $10,000.00    │  │   +$25.50 (0.25%)|  │   POSITIONS: 2  │   │
│  │   (Paper)       │  │   WIN: 66.6%     │  │   BOTS: 1       │   │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘   │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │                    EQUITY CURVE CHART                         │ │
│  │  (Recharts line chart - 7 day, 30 day, All time toggle)      │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌─────────────────────────────┐  ┌─────────────────────────────┐│
│  │    ACTIVE POSITIONS         │  │   RECENT TRADES             ││
│  │  BTC/USDT  BUY  +$5.00      │  │  BTC/USDT  BUY  +$5.00      ││
│  │  ETH/USDT  SELL -$2.00      │  │  ETH/USDT  SELL -$2.00      ││
│  └─────────────────────────────┘  └─────────────────────────────┘│
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │                    RUNNING BOTS STATUS                       │ │
│  │  RSI Momentum: Running | Last signal: BUY (5 min ago)       │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Interactions
- **Mode Toggle**: Switch between paper/live view
- **Chart**: Hover for date/value tooltips
- **Position Click**: Navigate to trade details
- **Trade Click**: Navigate to trade history with filter

### Data Refresh
- Prices: WebSocket real-time
- Balance: WebSocket + polling every 30s
- Positions: WebSocket
- Chart: API fetch on load + cache

---

## 3. STRATEGIES PAGE

### Route: `/strategies`

### Purpose
Create, manage, and monitor trading strategies.

### Sub-pages
- `/strategies` - List all strategies
- `/strategies/new` - Create new strategy
- `/strategies/:id` - View/Edit strategy

### Strategy List View

```
┌─────────────────────────────────────────────────────────────────────┐
│  STRATEGIES                                          [+ New]        │
├─────────────────────────────────────────────────────────────────────┤
│  Filter: [All] [Paper] [Live]    Search: [___________]            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │  RSI Momentum                          [Edit] [Clone] [Delete] ││
│  │  Symbol: BTC/USDT | TF: 1h | Mode: Paper | Broker: Binance     ││
│  │  Status: ● Running  Last eval: 10 min ago                     ││
│  │  Today: 3 trades | P&L: +$15.00                                ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │  EMA Crossover                          [Edit] [Clone] [Delete]││
│  │  Symbol: ETH/USDT | TF: 15m | Mode: Live | Broker: Binance    ││
│  │  Status: ○ Stopped                                              ││
│  │  Total: 50 trades | P&L: +$250.00                               ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Strategy Editor (Create/Edit)

```
┌─────────────────────────────────────────────────────────────────────┐
│  CREATE STRATEGY                                    [Save] [Test] │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  BASIC INFO                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ Strategy Name: [________________________]                      ││
│  │ Symbol:        [BTC/USDT ▼]  Timeframe: [1h ▼]                 ││
│  │ Broker:        [Binance ▼]    Mode:     [Paper ▼]              ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                     │
│  INDICATORS                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ + Add Indicator                                                 ││
│  │  [RSI ▼]  Period: [14] [✓ Enabled]    [×]                     ││
│  │  [EMA ▼]  Period: [9]  [✓ Enabled]    [×]                      ││
│  │  [EMA ▼]  Period: [21] [✓ Enabled]    [×]                      ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                     │
│  ENTRY CONDITIONS                                                   │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ + Add Condition (AND)                                          ││
│  │  [RSI] [less than ▼] [30]  [×] [AND ▼]                         ││
│  │  [EMA_9] [crosses above ▼] [EMA_21]  [×] [AND ▼]              ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                     │
│  EXIT CONDITIONS                                                    │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ + Add Condition (OR)                                            ││
│  │  [RSI] [greater than ▼] [70]  [×] [OR ▼]                      ││
│  │  [EMA_9] [crosses below ▼] [EMA_21]  [×] [OR ▼]               ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                     │
│  RISK SETTINGS                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ Stop Loss:    [%] [1.0]                                        ││
│  │ Take Profit:  [%] [2.0]                                        ││
│  │ Trailing SL:  [✓] [%] [0.5]                                   ││
│  │ Position Size: [Calculated ▼] [%] [10]                        ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Strategy Testing

Click "Test" to evaluate strategy against current data:

```
┌─────────────────────────────────────────────────────────────────────┐
│  STRATEGY TEST RESULTS                                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Current Market (BTC/USDT 1h)                                       │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ RSI (14): 28.5  ✓                                               ││
│  │ EMA 9: 44,900   ✓                                               ││
│  │ EMA 21: 44,850   ✓                                              ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                     │
│  Entry Conditions:                                                  │
│  ✓ RSI < 30 (28.5)                                                 │
│  ✓ EMA 9 crosses above EMA 21                                      │
│  ───────────────────────────                                       │
│  RESULT: 🟢 BUY SIGNAL                                             │
│                                                                     │
│  Exit Conditions:                                                   │
│  ✗ RSI > 70 (28.5)                                                 │
│  ✗ EMA 9 crosses below EMA 21                                      │
│                                                                     │
│  Risk: Entry: $45,000 | SL: $44,550 | TP: $45,900                  │
│  Position Size: 0.022 BTC ($1,000 at risk)                         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 4. BOTS PAGE

### Route: `/bots`

### Purpose
Start/stop trading bots and monitor their status.

```
┌─────────────────────────────────────────────────────────────────────┐
│  TRADING BOTS                                                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  GLOBAL MODE: [Paper ● ] [ ○ Live ]    [Start All] [Stop All]     │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ RSI Momentum (BTC/USDT 1h Paper)                               ││
│  │ ● Running | Last signal: BUY (5 min ago)                       ││
│  │ Today: 3 trades | P&L: +$15.00                                  ││
│  │                                                                   ││
│  │ [Stop]  [View Logs]  [View Trades]                             ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ EMA Crossover (ETH/USDT 15m Live)                              ││
│  │ ○ Stopped                                                       ││
│  │ Total: 50 trades | P&L: +$250.00                               ││
│  │                                                                   ││
│  │ [Start]  [Configure]  [View Trades]                            ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Bot Control Flow
1. User clicks "Start" on a strategy
2. System validates broker connection
3. System checks risk limits
4. Bot status changes to "Starting..."
5. Celery task begins evaluating strategy
6. Bot status changes to "Running"
7. Signals/trades begin appearing

---

## 5. TRADES PAGE

### Route: `/trades`

### Purpose
View trade history with filtering and export.

```
┌─────────────────────────────────────────────────────────────────────┐
│  TRADE HISTORY                                      [Export CSV]   │
├─────────────────────────────────────────────────────────────────────┤
│  Filter:                                                            │
│  Mode: [All ▼] Symbol: [All ▼] Status: [All ▼]                    │
│  Date: [📅 Start] to [📅 End]    [Apply Filter]                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Summary: Total: 150 | Wins: 90 | Losses: 60 | Win Rate: 60%      │
│           Total P&L: +$250.00 | Avg: $1.67/trade                    │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ Time    │ Symbol   │Side│Qty  │Entry   │Exit    │P&L   │ Mode ││
│  ├─────────┼──────────┼────┼─────┼────────┼────────┼──────┼──────┤│
│  │10:30:00 │BTC/USDT  │BUY │0.01 │45,000  │45,500  │+5.00 │Paper ││
│  │09:15:00 │ETH/USDT  │SELL│0.1  │2,500   │2,480   │-2.00 │Paper ││
│  │08:00:00 │BTC/USDT  │BUY │0.01 │44,500  │45,000  │+5.00 │Paper ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                     │
│  [< Prev] Page 1 of 15 [Next >]                                    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Trade Detail Modal

Click on a trade to see details:

```
┌─────────────────────────────────────────────────────────────────────┐
│  TRADE DETAIL                                    [×]                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Trade ID: trade_123                                                │
│  Strategy: RSI Momentum                                            │
│  Symbol: BTC/USDT                                                  │
│  Side: BUY  |  Quantity: 0.01  |  Mode: Paper                      │
│                                                                     │
│  Entry:                                                            │
│  Price: $45,000.00                                                 │
│  Time: 2024-01-15 10:30:00                                        │
│  Type: Market                                                      │
│                                                                     │
│  Exit:                                                             │
│  Price: $45,500.00                                                 │
│  Time: 2024-01-15 12:00:00                                        │
│  Reason: Take Profit                                                │
│                                                                     │
│  P&L: +$5.00 (+0.11%)  |  Commission: $0.10                        │
│  Duration: 90 minutes                                              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 6. BACKTEST PAGE

### Route: `/backtest`

### Purpose
Run historical tests on strategies.

```
┌─────────────────────────────────────────────────────────────────────┐
│  BACKTEST                                            [+ New]       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ Run New Backtest                                                ││
│  │                                                                  ││
│  │ Strategy:   [Select Strategy ▼]                                 ││
│  │ Symbol:     [BTC/USDT ▼]                                        ││
│  │ Timeframe:  [1h ▼]                                               ││
│  │ Date Range: [2023-01-01] to [2023-12-31]                        ││
│  │ Capital:     [$10,000]                                           ││
│  │                                                                  ││
│  │ [Run Backtest]                                                   ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                     │
│  PAST BACKTESTS                                                     │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ RSI Momentum | BTC/USDT 1h | 2023 | +25% | ✓ Completed         ││
│  │ EMA Crossover | ETH/USDT 15m | 2023 | +15% | ✓ Completed       ││
│  │ RSI Momentum | BTC/USDT 1h | Jan 2024 | - | ⟳ Running          ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Backtest Running State

```
┌─────────────────────────────────────────────────────────────────────┐
│  BACKTEST RUNNING                                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Progress: ████████████░░░░░░░░ 60%                                 │
│  Processing: 6,000 of 10,000 candles                                │
│  Current: 2023-06-15                                                │
│  Est. time remaining: 2 minutes                                     │
│                                                                     │
│  Live Results So Far:                                               │
│  Trades: 90 | P&L: +$180 | Win Rate: 60%                           │
│                                                                     │
│  [Cancel]                                                           │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Backtest Results

```
┌─────────────────────────────────────────────────────────────────────┐
│  BACKTEST RESULTS                                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Summary                         Metrics                             │
│  ┌─────────────────────────┐    ┌─────────────────────────┐        │
│  │ Initial: $10,000       │    │ Total Return: +25.0%    │        │
│  │ Final: $12,500         │    │ Annual Return: +25.0%   │        │
│  │ Total Trades: 150      │    │ Sharpe Ratio: 1.5       │        │
│  │ Duration: 1 year       │    │ Max Drawdown: 8.5%      │        │
│  └─────────────────────────┘    │ Win Rate: 60%           │        │
│                                  │ Profit Factor: 1.8       │        │
│                                  └─────────────────────────┘        │
│                                                                     │
│  Equity Curve Chart                                                 │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ (Recharts line chart showing equity over time)               │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  Drawdown Chart                                                    │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ (Area chart showing drawdown from peak)                      │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  Trade List                                                         │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ Time    │ Symbol   │Side│Entry   │Exit    │P&L   │ Reason   │ │
│  ├─────────┼──────────┼────┼────────┼────────┼──────┼──────────┤ │
│  │ ...     │ ...      │..  │...     │...     │...   │ ...      │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  [Save Results] [Delete] [Run Again]                               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 7. SETTINGS PAGE

### Route: `/settings`

### Purpose
Configure broker connections, notifications, and risk defaults.

### Sections

```
┌─────────────────────────────────────────────────────────────────────┐
│  SETTINGS                                                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  BROKER CONNECTIONS                                                │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ Binance: ● Connected (Testnet)                    [Disconnect]  ││
│  │ Zerodha: ○ Not connected                         [Connect]     ││
│  │ Upstox:   ○ Not connected                         [Connect]     ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                     │
│  NOTIFICATIONS                                                     │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ Telegram: [✓ Enabled]  Bot Token: [••••••••••••]              ││
│  │ Chat ID: [123456789]                           [Test]          ││
│  │                                                                  ││
│  │ Alert Types:                                                    ││
│  │ [✓] Trade Entry         [✓] Trade Exit                         ││
│  │ [✓] Stop Loss Hit      [✓] Take Profit Hit                    ││
│  │ [✓] Errors             [✓] Daily Summary (6 PM)              ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                     │
│  RISK DEFAULTS                                                     │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ Max Daily Loss:     [%] [5.0]                                  ││
│  │ Risk Per Trade:     [%] [1.0]                                  ││
│  │ Max Open Positions:   [3]                                       ││
│  │ Auto Stop (Consec. Losses): [3]                                 ││
│  │ Max Drawdown:         [%] [10.0]                                ││
│  │ Trade Cooldown:       [5] minutes                               ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                     │
│  SECURITY                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ Two-Factor Auth: [✓] Enabled                    [Disable]     ││
│  │ (Using Google Authenticator)                                    ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                     │
│  [Save Changes]                                                    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Broker Connection Modal

```
┌─────────────────────────────────────────────────────────────────────┐
│  CONNECT BROKER                                     [×]            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Broker: [Binance ▼]                                                │
│                                                                     │
│  API Key:     [________________________]                           │
│  API Secret: [________________________]                           │
│                                                                     │
│  [✓] Use Testnet (Sandbox)                                         │
│                                                                     │
│  Note: Your credentials are encrypted and stored securely.        │
│  We never share your API keys with third parties.                  │
│                                                                     │
│  [Cancel] [Connect]                                                │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 8. LOGS PAGE

### Route: `/logs`

### Purpose
View application logs for debugging and monitoring.

```
┌─────────────────────────────────────────────────────────────────────┐
│  LOGS                                                [Auto-refresh]│
├─────────────────────────────────────────────────────────────────────┤
│  Filter:                                                            │
│  Level: [All ▼]  Category: [All ▼]  Search: [___________]         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ 2024-01-15 10:30:00 | INFO  | TRADE  | BUY signal detected    ││
│  │ 2024-01-15 10:30:00 | INFO  | BROKER | Price update: 45000    ││
│  │ 2024-01-15 10:29:00 | WARN  | SIGNAL | RSI near oversold      ││
│  │ 2024-01-15 10:25:00 | ERROR | BROKER | Connection timeout     ││
│  │ 2024-01-15 10:20:00 | INFO  | SYSTEM | Bot started: RSI      ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                     │
│  [Load More]                                                        │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 9. NAVIGATION FLOW DIAGRAM

```
┌──────────┐
│  Login   │
└────┬─────┘
     │
     ▼
┌──────────┐
│Dashboard │◄────────────────────────────────────────┐
└────┬─────┘                                         │
     │                                               │
     ├────────────┬────────────┬────────┬────────────┤
     ▼            ▼            ▼        ▼            │
┌─────────┐  ┌────────┐  ┌───────┐  ┌────────┐     │
│Strategies│  │  Bots  │  │Trades │  │Backtest│     │
└────┬────┘  └────┬───┘  └───┬───┘  └──┬─────┘     │
     │            │           │         │            │
     │            │           │         │            │
     ▼            ▼           ▼         ▼            │
  Strategy    Bot Control  History    Results       │
  Editor      Status                                   │
                                                         │
                                                         │
     ┌─────────────────────────────────────────────────┤
     ▼                                                 │
┌──────────┐    ┌──────────┐    ┌──────────┐          │
│ Settings │    │   Logs   │    │ Sidebar  │──────────┘
└──────────┘    └──────────┘    └──────────┘
```

---

## KEY USER INTERACTIONS

### 1. Mode Switching
```
Dashboard → Click Paper/Live toggle
  → Update all data to reflect selected mode
  → Update UI indicators
  → Persist preference
```

### 2. Starting a Bot
```
Strategies → Select strategy → Click "Start"
  → Validate broker connection
  → Validate risk limits
  → Update strategy status to "starting"
  → Start Celery task
  → Update to "running" when task starts
  → Begin receiving signals/trades via WebSocket
```

### 3. Creating Strategy
```
Strategies → Click "New"
  → Fill form (name, symbol, indicators, conditions, risk)
  → Click "Test" to validate conditions
  → Click "Save" to persist
  → Redirect to strategy list
```

### 4. Running Backtest
```
Backtest → Fill form (strategy, symbol, dates, capital)
  → Click "Run Backtest"
  → Return immediately with backtest_id
  → Poll for status via WebSocket or API
  → Show progress updates
  → Display results when complete
```

---

*End of UI Flow Documentation*