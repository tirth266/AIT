# STRATEGY ENGINE DOCUMENTATION

## Overview
The Strategy Engine is the core component that evaluates trading strategies, generates signals, and executes trades. This document describes the architecture, indicators, conditions, and execution flow.

---

## 1. ARCHITECTURE OVERVIEW

```
┌─────────────────────────────────────────────────────────────────────┐
│                        STRATEGY ENGINE                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────┐    ┌─────────────────┐    ┌───────────────┐  │
│  │   Candle        │    │   Indicator     │    │   Condition   │  │
│  │   Fetcher      │───▶│   Calculator    │───▶│   Evaluator   │  │
│  └─────────────────┘    └─────────────────┘    └───────┬───────┘  │
│                                                         │          │
│                                                         ▼          │
│  ┌─────────────────┐    ┌─────────────────┐    ┌───────────────┐  │
│  │   Risk         │    │   Order         │    │   Signal      │  │
│  │   Manager      │◀───│   Executor     │◀───│   Generator   │  │
│  └─────────────────┘    └─────────────────┘    └───────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Components

| Component | Description |
|-----------|-------------|
| Candle Fetcher | Retrieves OHLCV data from broker or cache |
| Indicator Calculator | Computes technical indicators |
| Condition Evaluator | Evaluates entry/exit conditions |
| Signal Generator | Determines BUY/SELL/HOLD signals |
| Risk Manager | Validates risk rules before execution |
| Order Executor | Places orders via broker API |

---

## 2. SUPPORTED INDICATORS

### 2.1 RSI (Relative Strength Index)

**Formula**:
```
RSI = 100 - (100 / (1 + RS))
RS = Average Gain / Average Loss (over period)
```

**Parameters**:
| Parameter | Default | Description |
|-----------|---------|-------------|
| period | 14 | Number of periods |
| overbought | 70 | Overbought threshold |
| oversold | 30 | Oversold threshold |

**Usage**:
```python
# pandas-ta
import pandas_ta as ta

df['RSI'] = ta.rsi(df['close'], length=14)
```

---

### 2.2 EMA (Exponential Moving Average)

**Formula**:
```
EMA_today = (Close_today × k) + (EMA_yesterday × (1 - k))
k = 2 / (period + 1)
```

**Parameters**:
| Parameter | Description |
|-----------|-------------|
| period | Number of periods (e.g., 9, 21, 50, 200) |

**Usage**:
```python
df['EMA_9'] = ta.ema(df['close'], length=9)
df['EMA_21'] = ta.ema(df['close'], length=21)
```

---

### 2.3 SMA (Simple Moving Average)

**Formula**:
```
SMA = (Sum of prices over period) / period
```

**Parameters**:
| Parameter | Description |
|-----------|-------------|
| period | Number of periods |

**Usage**:
```python
df['SMA_50'] = ta.sma(df['close'], length=50)
```

---

### 2.4 MACD (Moving Average Convergence Divergence)

**Formula**:
```
EMA_12 = EMA(close, 12)
EMA_26 = EMA(close, 26)
MACD Line = EMA_12 - EMA_26
Signal Line = EMA(MACD, 9)
Histogram = MACD - Signal
```

**Parameters**:
| Parameter | Default | Description |
|-----------|---------|-------------|
| fast | 12 | Fast EMA period |
| slow | 26 | Slow EMA period |
| signal | 9 | Signal line period |

**Usage**:
```python
macd = ta.macd(df['close'], fast=12, slow=26, signal=9)
df['MACD'] = macd['MACD_12_26_9']
df['MACD_signal'] = macd['MACDs_12_26_9']
df['MACD_hist'] = macd['MACDh_12_26_9']
```

---

### 2.5 Bollinger Bands

**Formula**:
```
Middle Band = SMA(close, period)
Upper Band = Middle + (std_dev × STD(close, period))
Lower Band = Middle - (std_dev × STD(close, period))
```

**Parameters**:
| Parameter | Default | Description |
|-----------|---------|-------------|
| period | 20 | Period for SMA and STD |
| std_dev | 2 | Standard deviations |

**Usage**:
```python
bb = ta.bbands(df['close'], length=20, std=2)
df['BB_upper'] = bb['BBU_20_2.0']
df['BB_middle'] = bb['BBM_20_2.0']
df['BB_lower'] = bb['BBL_20_2.0']
```

---

### 2.6 VWAP (Volume Weighted Average Price)

**Formula**:
```
VWAP = Σ(Price × Volume) / Σ(Volume)
```

**Parameters**: None (uses daily session by default)

**Usage**:
```python
df['VWAP'] = ta.vwap(df['close'], df['high'], df['low'], df['volume'])
```

---

### 2.7 Supertrend

**Formula**:
```
ATR = Average True Range (period)
Upper Band = (High + Low) / 2 + (multiplier × ATR)
Lower Band = (High + Low) / 2 - (multiplier × ATR)

Supertrend = 
  - If close > Upper Band: Uptrend (use Lower Band)
  - If close < Lower Band: Downtrend (use Upper Band)
```

**Parameters**:
| Parameter | Default | Description |
|-----------|---------|-------------|
| period | 10 | ATR period |
| multiplier | 3 | ATR multiplier |

**Usage**:
```python
# Custom implementation needed - pandas-ta doesn't have Supertrend
# See indicator service implementation
```

---

### 2.8 ATR (Average True Range)

**Formula**:
```
TR = Max(High - Low, |High - Previous Close|, |Low - Previous Close|)
ATR = SMA(TR, period)
```

**Parameters**:
| Parameter | Default | Description |
|-----------|---------|-------------|
| period | 14 | Number of periods |

**Usage**:
```python
df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=14)
```

---

### 2.9 Stochastic Oscillator

**Formula**:
```
%K = 100 × (Current Close - Lowest Low) / (Highest High - Lowest Low)
%D = SMA(%K, period)
```

**Parameters**:
| Parameter | Default | Description |
|-----------|---------|-------------|
| k_period | 14 | %K period |
| d_period | 3 | %D period |

**Usage**:
```python
stoch = ta.stoch(df['high'], df['low'], df['close'])
df['Stoch_K'] = stoch['STOCHk_14_3_3']
df['Stoch_D'] = stoch['STOCHd_14_3_3']
```

---

## 3. CONDITION OPERATORS

### 3.1 Comparison Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `equals` | Equal to | RSI == 50 |
| `not_equals` | Not equal to | RSI != 50 |
| `greater_than` | Greater than | RSI > 70 |
| `less_than` | Less than | RSI < 30 |
| `greater_or_equal` | Greater or equal | RSI >= 50 |
| `less_or_equal` | Less or equal | RSI <= 50 |

### 3.2 Crossover Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `crosses_above` | Indicator crosses above value | EMA_9 crosses above EMA_21 |
| `crosses_below` | Indicator crosses below value | EMA_9 crosses below EMA_21 |

### 3.3 Range Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `between` | Within range | RSI between 30 and 70 |
| `not_between` | Outside range | RSI not between 40 and 60 |

---

## 4. CONDITION EVALUATION

### 4.1 Condition Structure

```python
# Database stored format
{
  "indicator_name": "RSI",
  "operator": "less_than",
  "value": 30,
  "logic": "AND"  # AND/OR for combining with previous
}
```

### 4.2 Evaluation Logic

```python
# app/services/condition_evaluator.py

class ConditionEvaluator:
    def evaluate_entry(self, conditions: list, indicators: dict) -> bool:
        """
        Evaluate all entry conditions with AND/OR logic
        Returns True if BUY signal generated
        """
        if not conditions:
            return False
        
        # Simple evaluation: all AND'd together
        # For complex AND/OR, build expression tree
        
        results = []
        for i, condition in enumerate(conditions):
            result = self.evaluate_condition(condition, indicators)
            results.append(result)
        
        # For now: AND all conditions
        # TODO: Implement proper AND/OR logic
        return all(results)
    
    def evaluate_condition(self, condition: dict, indicators: dict) -> bool:
        indicator_name = condition['indicator_name']
        operator = condition['operator']
        value = condition['value']
        
        current_value = indicators.get(indicator_name)
        if current_value is None:
            return False
        
        return self._apply_operator(operator, current_value, value)
    
    def _apply_operator(self, operator: str, current: float, target) -> bool:
        if operator == 'equals':
            return current == target
        elif operator == 'not_equals':
            return current != target
        elif operator == 'greater_than':
            return current > target
        elif operator == 'less_than':
            return current < target
        elif operator == 'greater_or_equal':
            return current >= target
        elif operator == 'less_or_equal':
            return current <= target
        elif operator == 'crosses_above':
            # Requires historical data comparison
            return self._check_crossover('above', current, target)
        elif operator == 'crosses_below':
            return self._check_crossover('below', current, target)
        
        return False
```

### 4.3 Crossover Detection

```python
def _check_crossover(self, direction: str, current: float, target) -> bool:
    # Need previous value for crossover detection
    # This requires maintaining recent indicator values
    # Implementation in indicator service with rolling history
    
    # Simplified: check current state
    if direction == 'above':
        return current > target
    elif direction == 'below':
        return current < target
    
    return False
```

---

## 5. SIGNAL GENERATION

### 5.1 Signal Types

| Signal | Value | Description |
|--------|-------|-------------|
| BUY | 1 | Enter long position |
| SELL | -1 | Exit long position / enter short |
| HOLD | 0 | No action |

### 5.2 Signal Generation Logic

```python
# app/services/signal_generator.py

class SignalGenerator:
    def __init__(self, strategy: dict):
        self.strategy = strategy
        self.conditions = strategy.get('entry_conditions', [])
        self.exit_conditions = strategy.get('exit_conditions', [])
    
    def evaluate(self, indicators: dict, has_position: bool) -> int:
        """
        Evaluate strategy conditions and return signal
        """
        # Check exit conditions first (if we have a position)
        if has_position:
            exit_signal = self._evaluate_conditions(
                self.exit_conditions, 
                indicators
            )
            if exit_signal:
                return Signal.SELL
        
        # Check entry conditions
        entry_signal = self._evaluate_conditions(
            self.conditions,
            indicators
        )
        
        if entry_signal:
            return Signal.BUY
        
        return Signal.HOLD
    
    def _evaluate_conditions(self, conditions: list, indicators: dict) -> bool:
        # Evaluate all conditions with AND logic
        # (OR logic requires more complex implementation)
        
        results = []
        for condition in conditions:
            result = self._evaluate_single(condition, indicators)
            results.append(result)
        
        # All conditions must be true (AND logic)
        return all(results)
    
    def _evaluate_single(self, condition: dict, indicators: dict) -> bool:
        # Implementation from ConditionEvaluator
        pass
```

---

## 6. RISK MANAGEMENT

### 6.1 Risk Rules

The Risk Manager enforces these rules before any trade:

1. **Daily Loss Limit**: Stop trading if daily loss > X%
2. **Position Limit**: Max X open positions
3. **Consecutive Loss Circuit**: Pause after X consecutive losses
4. **Drawdown Limit**: Pause if total drawdown > X%
5. **Cooldown**: Wait X minutes between trades
6. **Broker Balance**: Check sufficient funds available
7. **Position Size**: Calculate based on risk %

### 6.2 Position Sizing

```python
# app/services/risk_manager.py

def calculate_position_size(
    capital: float,
    entry_price: float,
    stop_loss_price: float,
    risk_percent: float
) -> float:
    """
    Calculate position size based on risk percentage
    
    Formula:
    Position Size = (Capital × Risk%) / (Entry - Stop Loss)
    """
    risk_amount = capital * (risk_percent / 100)
    price_risk = abs(entry_price - stop_loss_price)
    
    if price_risk == 0:
        return 0
    
    position_size = risk_amount / price_risk
    
    # Round to appropriate precision
    # BTC: 0.00001, Stocks: 1
    return round(position_size, 8)
```

### 6.3 Risk Check Sequence

```python
def can_trade(self, mode: str = 'paper') -> tuple[bool, str]:
    """
    Returns (can_trade: bool, reason: str)
    """
    
    # 1. Check if bot is active and not paused
    if self.is_paused:
        return False, "Bot is paused"
    
    # 2. Check daily loss limit
    daily_pnl = self.get_daily_pnl(mode)
    if daily_pnl < -self.settings['max_daily_loss_percent']:
        return False, "Daily loss limit exceeded"
    
    # 3. Check max open positions
    open_count = self.get_open_positions_count(mode)
    if open_count >= self.settings['max_open_positions']:
        return False, "Max positions reached"
    
    # 4. Check consecutive losses (circuit breaker)
    if self.get_consecutive_losses() >= self.settings['max_consecutive_losses']:
        return False, "Circuit breaker triggered"
    
    # 5. Check cooldown
    if not self.is_cooldown_elapsed():
        return False, f"Cooldown: {self.get_cooldown_remaining()} seconds"
    
    # 6. Check drawdown
    if self.get_total_drawdown() >= self.settings['max_drawdown_percent']:
        return False, "Max drawdown exceeded"
    
    # 7. Check broker balance
    if not self.has_sufficient_balance(mode):
        return False, "Insufficient balance"
    
    return True, "OK"
```

---

## 7. ORDER EXECUTION

### 7.1 Order Types

| Type | Description | Use Case |
|------|-------------|----------|
| `market` | Execute immediately at current price | Fast entry, liquid markets |
| `limit` | Execute when price reaches target | Better price, waiting |

### 7.2 Order Flow

```python
# app/services/order_executor.py

class OrderExecutor:
    def __init__(self, broker: BrokerInterface):
        self.broker = broker
    
    def execute_trade(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = 'market',
        limit_price: float = None,
        stop_loss: float = None,
        take_profit: float = None,
        mode: str = 'paper'
    ) -> dict:
        
        if mode == 'paper':
            return self._execute_paper_trade(
                symbol, side, quantity, order_type, limit_price
            )
        
        # Live trading
        return self._execute_live_trade(
            symbol, side, quantity, order_type, limit_price
        )
    
    def _execute_paper_trade(
        self, symbol, side, quantity, order_type, limit_price
    ) -> dict:
        # Get current market price
        current_price = self.broker.get_current_price(symbol)
        
        # For market orders, use current price
        # For limit orders, use specified price
        execution_price = limit_price if order_type == 'limit' else current_price
        
        # Create paper trade record
        trade = {
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'entry_price': execution_price,
            'status': 'filled',
            'mode': 'paper'
        }
        
        # Save to database
        # Update balance
        # Send notifications
        
        return trade
    
    def _execute_live_trade(
        self, symbol, side, quantity, order_type, limit_price
    ) -> dict:
        # Place real order via broker API
        result = self.broker.create_order(
            symbol=symbol,
            side=side,
            qty=quantity,
            order_type=order_type,
            price=limit_price
        )
        
        return result
```

### 7.3 Stop Loss & Take Profit

```python
# app/services/sl_tp_manager.py

class SLTPDBManager:
    def __init__(self):
        pass
    
    def check_sl_tp_hit(
        self,
        current_price: float,
        entry_price: float,
        side: str,
        stop_loss: float,
        take_profit: float
    ) -> tuple[bool, str]:
        """
        Check if SL or TP is hit
        Returns (hit: bool, reason: str)
        """
        
        if side == 'BUY':
            # For long position
            if stop_loss and current_price <= stop_loss:
                return True, 'stop_loss'
            if take_profit and current_price >= take_profit:
                return True, 'take_profit'
        
        elif side == 'SELL':
            # For short position
            if stop_loss and current_price >= stop_loss:
                return True, 'stop_loss'
            if take_profit and current_price <= take_profit:
                return True, 'take_profit'
        
        return False, None
    
    def calculate_trailing_stop(
        self,
        current_price: float,
        entry_price: float,
        trailing_percent: float,
        current_stop: float,
        side: str
    ) -> float:
        """
        Update trailing stop based on current price
        """
        if side == 'BUY':
            # For long: stop moves up as price increases
            profit = current_price - entry_price
            new_stop = entry_price + (profit * (1 - trailing_percent))
            return max(new_stop, current_stop)  # Only move up
        
        else:
            # For short: stop moves down as price decreases
            profit = entry_price - current_price
            new_stop = entry_price - (profit * (1 - trailing_percent))
            return min(new_stop, current_stop)  # Only move down
```

---

## 8. BACKTESTING ENGINE

### 8.1 Backtest Flow

```
1. Load strategy and parameters
2. Fetch historical candle data
3. For each candle:
   a. Calculate indicators
   b. Check entry conditions
   c. If signal and no position: Open position
   d. Check exit conditions / SL / TP
   e. If exit signal: Close position
   f. Update equity
4. Calculate final metrics
5. Return results
```

### 8.2 Backtest Implementation

```python
# app/services/backtest_engine.py

class BacktestEngine:
    def __init__(self, strategy: dict, initial_capital: float):
        self.strategy = strategy
        self.capital = initial_capital
        self.position = None
        self.trades = []
        self.equity_curve = []
    
    def run(self, candles: list) -> dict:
        """
        Run backtest on historical data
        """
        
        # Calculate indicators for all candles first
        indicators_cache = self._precalculate_indicators(candles)
        
        # Iterate through candles
        for i, candle in enumerate(candles):
            indicators = indicators_cache[i]
            
            # Check if we should close position
            if self.position:
                exit_signal = self._check_exit(indicators, candle)
                if exit_signal:
                    self._close_position(candle, exit_signal)
            
            # Check if we should open position
            if not self.position:
                entry_signal = self._check_entry(indicators)
                if entry_signal:
                    self._open_position(candle, indicators)
            
            # Record equity
            self._record_equity(candle)
        
        # Close any open position at the end
        if self.position:
            self._close_position(candles[-1], 'backtest_end')
        
        return self._calculate_metrics()
    
    def _open_position(self, candle: dict, indicators: dict):
        # Calculate position size
        size = self._calculate_position_size(candle)
        
        self.position = {
            'entry_price': candle['close'],
            'quantity': size,
            'entry_time': candle['timestamp'],
            'side': 'BUY'  # Simplified for now
        }
    
    def _close_position(self, candle: dict, reason: str):
        pnl = (candle['close'] - self.position['entry_price']) * self.position['quantity']
        
        self.trades.append({
            'entry_price': self.position['entry_price'],
            'exit_price': candle['close'],
            'quantity': self.position['quantity'],
            'pnl': pnl,
            'exit_reason': reason,
            'entry_time': self.position['entry_time'],
            'exit_time': candle['timestamp']
        })
        
        # Update capital
        self.capital += pnl
        
        self.position = None
    
    def _calculate_metrics(self) -> dict:
        # Calculate all performance metrics
        winning_trades = [t for t in self.trades if t['pnl'] > 0]
        losing_trades = [t for t in self.trades if t['pnl'] <= 0]
        
        total_return = (self.capital - 10000) / 10000 * 100
        win_rate = len(winning_trades) / len(self.trades) * 100 if self.trades else 0
        
        # More metrics: Sharpe, drawdown, etc.
        
        return {
            'total_return': total_return,
            'total_trades': len(self.trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            # ... more metrics
        }
```

---

## 9. STRATEGY EVALUATION SCHEDULE

### 9.1 Evaluation Frequency

| Timeframe | Evaluation Interval |
|-----------|---------------------|
| 1m | Every 30 seconds |
| 5m | Every 1 minute |
| 15m | Every 3 minutes |
| 1h | Every 5 minutes |
| 4h | Every 15 minutes |
| 1d | Every 1 hour |

### 9.2 Celery Task Schedule

```python
# celery_config.py

beat_schedule = {
    'evaluate-strategies-1m': {
        'task': 'app.tasks.trading.evaluate_strategies',
        'schedule': 30.0,  # 30 seconds for 1m TF
    },
    'check-positions': {
        'task': 'app.tasks.trading.check_all_positions',
        'schedule': 60.0,  # Check every minute
    },
    'fetch-latest-candles': {
        'task': 'app.tasks.market.fetch_candles',
        'schedule': 60.0,
    },
}
```

---

## 10. STRATEGY STATE MACHINE

```
┌─────────────────────────────────────────────────────────────────────┐
│                       STRATEGY STATE MACHINE                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│     ┌──────────┐                                                   │
│     │ STOPPED │                                                   │
│     └────┬─────┘                                                   │
│          │ start                                                   │
│          ▼                                                         │
│     ┌──────────┐                                                   │
│────▶│STARTING │◀─────────────┐                                     │
│     └────┬─────┘              │ error                             │
│          │                    │                                   │
│          ▼                    │                                   │
│     ┌──────────┐              ┌───────┐                            │
│     │ RUNNING │───────────────│ ERROR │                            │
│     └────┬─────┘              └───┬───┘                            │
│          │ stop                  │                                 │
│          ▼                       │                                 │
│     ┌──────────┐                  │                                 │
│     │STOPPING │──────────────────┘                                 │
│     └────┬─────┘                                                   │
│          │ stopped                                                  │
│          ▼                                                         │
│     ┌──────────┐                                                   │
│     │ STOPPED │ (with circuit breaker state)                       │
│     └──────────┘                                                   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

*End of Strategy Engine Documentation*