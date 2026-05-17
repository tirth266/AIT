# TESTING DOCUMENTATION

## Overview
Comprehensive testing strategy for the automated trading platform. Covers unit testing, integration testing, strategy testing, and end-to-end validation.

---

## 1. TESTING STRATEGY

### 1.1 Testing Pyramid

```
┌─────────────────────────────────────────────────────────────────────┐
│                         TESTING PYRAMID                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│                          ┌─────────┐                                │
│                         /  E2E    \     (Playwright)               │
│                        /  Tests   \                                │
│                       └─────┬─────┘                                │
│                     ┌───────┴────────┐                             │
│                    /  Integration    \   (pytest + mocking)         │
│                   /   Tests          \                              │
│                  └───────┬────────────┘                             │
│              ┌───────────┴───────────┐                              │
│             /      Unit Tests        \    (pytest + unittest)       │
│            /    (indicators, utils)   \                             │
│           └───────────────────────────┘                             │
│                                                                     │
│  More tests at bottom, fewer at top                                 │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 Test Categories

| Category | Purpose | Tools |
|----------|---------|-------|
| Unit Tests | Test individual functions | pytest |
| Integration Tests | Test API endpoints | pytest + requests |
| Strategy Tests | Test trading logic | Custom framework |
| E2E Tests | Test full user flows | Playwright |
| Load Tests | Test performance | Locust |

---

## 2. UNIT TESTS

### 2.1 Backend Unit Tests

**Setup**:
```bash
cd backend
pip install pytest pytest-cov pytest-mock

# Run tests
pytest -v
pytest --cov=app --cov-report=html
```

**Test Structure**:
```
backend/
├── tests/
│   ├── __init__.py
│   ├── conftest.py           # Pytest fixtures
│   ├── test_indicators.py     # Indicator calculations
│   ├── test_risk_manager.py  # Risk logic
│   ├── test_signal_generator.py
│   ├── test_encryption.py
│   └── test_utils.py
├── app/
│   └── ...
└── requirements.txt
```

**Example: Indicator Tests**

```python
# tests/test_indicators.py
import pytest
import pandas as pd
import pandas_ta as ta

class TestRSI:
    """Test RSI indicator calculations"""
    
    @pytest.fixture
    def sample_data(self):
        """Generate sample price data"""
        dates = pd.date_range('2024-01-01', periods=50, freq='D')
        prices = pd.Series([100 + i + (i % 5) * 2 for i in range(50)], index=dates)
        return prices
    
    def test_rsi_calculation(self, sample_data):
        """Test RSI returns expected values"""
        result = ta.rsi(sample_data, length=14)
        
        # RSI should be between 0 and 100
        assert result.min() >= 0
        assert result.max() <= 100
        
        # Last value should not be NaN (enough data)
        assert not pd.isna(result.iloc[-1])
    
    def test_rsi_oversold(self, sample_data):
        """Test RSI detects oversold conditions"""
        # Create oversold scenario
        oversold_prices = pd.Series([100, 98, 96, 94, 92, 90, 88, 86, 84, 82, 
                                     80, 79, 78, 77, 76, 75, 74, 73, 72, 71])
        result = ta.rsi(oversold_prices, length=14)
        
        # Should be in oversold territory
        assert result.iloc[-1] < 30

class TestEMA:
    """Test EMA indicator calculations"""
    
    def test_ema_increases_with_uptrend(self):
        """Test EMA follows price in uptrend"""
        prices = pd.Series([100, 102, 104, 106, 108, 110])
        ema_5 = ta.ema(prices, length=5)
        
        # EMA should be close to current price
        assert ema_5.iloc[-1] > ema_5.iloc[0]
    
    def test_ema_smoothing(self):
        """Test EMA smooths price fluctuations"""
        # Volatile prices
        prices = pd.Series([100, 110, 90, 105, 95, 108])
        ema = ta.ema(prices, length=3)
        
        # EMA should be less volatile than prices
        ema_std = ema.std()
        price_std = prices.std()
        assert ema_std < price_std
```

**Example: Risk Manager Tests**

```python
# tests/test_risk_manager.py
import pytest
from unittest.mock import Mock, patch
from app.services.risk_manager import RiskManager

class TestRiskManager:
    """Test risk management logic"""
    
    @pytest.fixture
    def risk_manager(self):
        """Create risk manager with default settings"""
        return RiskManager()
    
    def test_can_trade_within_limits(self, risk_manager):
        """Test can trade when within all limits"""
        with patch.object(risk_manager, 'get_daily_pnl', return_value=0):
            with patch.object(risk_manager, 'get_open_positions_count', return_value=1):
                with patch.object(risk_manager, 'get_consecutive_losses', return_value=0):
                    with patch.object(risk_manager, 'get_total_drawdown', return_value=2):
                        with patch.object(risk_manager, 'is_cooldown_elapsed', return_value=True):
                            with patch.object(risk_manager, 'has_sufficient_balance', return_value=True):
                                can_trade, reason = risk_manager.can_trade()
                                assert can_trade is True
    
    def test_block_when_daily_loss_exceeded(self, risk_manager):
        """Test block trading when daily loss limit exceeded"""
        with patch.object(risk_manager, 'get_daily_pnl', return_value=-10):  # > 5%
            can_trade, reason = risk_manager.can_trade()
            assert can_trade is False
            assert "Daily loss limit" in reason
    
    def test_block_when_max_positions_reached(self, risk_manager):
        """Test block when max open positions reached"""
        with patch.object(risk_manager, 'get_daily_pnl', return_value=0):
            with patch.object(risk_manager, 'get_open_positions_count', return_value=3):
                can_trade, reason = risk_manager.can_trade()
                assert can_trade is False
                assert "Max positions" in reason
    
    def test_circuit_breaker_after_consecutive_losses(self, risk_manager):
        """Test circuit breaker after consecutive losses"""
        with patch.object(risk_manager, 'get_daily_pnl', return_value=0):
            with patch.object(risk_manager, 'get_open_positions_count', return_value=1):
                with patch.object(risk_manager, 'get_consecutive_losses', return_value=3):
                    can_trade, reason = risk_manager.can_trade()
                    assert can_trade is False
                    assert "Circuit breaker" in reason
    
    def test_position_size_calculation(self, risk_manager):
        """Test position size is calculated correctly"""
        capital = 10000
        entry = 45000
        stop_loss = 44500  # 1% stop
        risk_percent = 1
        
        size = risk_manager.calculate_position_size(capital, entry, stop_loss, risk_percent)
        
        # Position size should risk 1% of capital ($100)
        # $100 / ($45,000 - $44,500) = $100 / $500 = 0.2
        expected = 100 / (45000 - 44500)
        assert abs(size - expected) < 0.01
```

**Example: Signal Generator Tests**

```python
# tests/test_signal_generator.py
import pytest
from app.services.signal_generator import SignalGenerator, Signal

class TestSignalGenerator:
    """Test signal generation logic"""
    
    @pytest.fixture
    def strategy(self):
        return {
            'entry_conditions': [
                {'indicator_name': 'RSI', 'operator': 'less_than', 'value': 30}
            ],
            'exit_conditions': [
                {'indicator_name': 'RSI', 'operator': 'greater_than', 'value': 70}
            ]
        }
    
    @pytest.fixture
    def signal_generator(self, strategy):
        return SignalGenerator(strategy)
    
    def test_generate_buy_signal(self, signal_generator):
        """Test BUY signal when entry condition met"""
        indicators = {'RSI': 25}
        
        signal = signal_generator.evaluate(indicators, has_position=False)
        
        assert signal == Signal.BUY
    
    def test_no_signal_when_condition_not_met(self, signal_generator):
        """Test HOLD when entry condition not met"""
        indicators = {'RSI': 50}
        
        signal = signal_generator.evaluate(indicators, has_position=False)
        
        assert signal == Signal.HOLD
    
    def test_generate_sell_signal_when_has_position(self, signal_generator):
        """Test SELL signal when exit condition met and has position"""
        indicators = {'RSI': 75}
        
        signal = signal_generator.evaluate(indicators, has_position=True)
        
        assert signal == Signal.SELL
    
    def test_no_sell_when_no_position(self, signal_generator):
        """Test HOLD when exit condition met but no position"""
        indicators = {'RSI': 75}
        
        signal = signal_generator.evaluate(indicators, has_position=False)
        
        assert signal == Signal.HOLD
```

### 2.2 Frontend Unit Tests

**Setup**:
```bash
cd frontend
npm install vitest @testing-library/react @testing-library/jest-dom

# Run tests
npm run test
```

**Example: Component Tests**

```javascript
// src/__tests__/components/StrategyCard.test.jsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import StrategyCard from '../../components/strategy/StrategyCard';

describe('StrategyCard', () => {
  const mockStrategy = {
    id: 'strat_123',
    name: 'RSI Momentum',
    symbol: 'BTC/USDT',
    timeframe: '1h',
    mode: 'paper',
    is_active: true,
    stats: {
      trades_today: 3,
      pnl_today: 15.00
    }
  };

  it('renders strategy name', () => {
    render(<StrategyCard strategy={mockStrategy} />);
    expect(screen.getByText('RSI Momentum')).toBeInTheDocument();
  });

  it('shows running status when active', () => {
    render(<StrategyCard strategy={mockStrategy} />);
    expect(screen.getByText('Running')).toBeInTheDocument();
  });

  it('calls onStart when start button clicked', () => {
    const onStart = vi.fn();
    render(
      <StrategyCard 
        strategy={{...mockStrategy, is_active: false}} 
        onStart={onStart}
      />
    );
    
    fireEvent.click(screen.getByText('Start'));
    expect(onStart).toHaveBeenCalledWith('strat_123');
  });

  it('calls onStop when stop button clicked', () => {
    const onStop = vi.fn();
    render(
      <StrategyCard 
        strategy={mockStrategy} 
        onStop={onStop}
      />
    );
    
    fireEvent.click(screen.getByText('Stop'));
    expect(onStop).toHaveBeenCalledWith('strat_123');
  });
});
```

**Example: Store Tests**

```javascript
// src/__tests__/stores/tradingStore.test.js
import { describe, it, expect } from 'vitest';
import { useTradingStore } from '../../stores/tradingStore';

describe('tradingStore', () => {
  it('should have initial paper mode', () => {
    const { mode } = useTradingStore.getState();
    expect(mode).toBe('paper');
  });

  it('should switch mode correctly', () => {
    const store = useTradingStore.getState();
    store.setMode('live');
    
    expect(useTradingStore.getState().mode).toBe('live');
  });

  it('should update balance', () => {
    const store = useTradingStore.getState();
    store.updateBalance(15000);
    
    expect(useTradingStore.getState().balance).toBe(15000);
  });
});
```

---

## 3. INTEGRATION TESTS

### 3.1 API Integration Tests

```python
# tests/test_api.py
import pytest
from app import create_app
from app.extensions import db
from app.models.user import User
import json

@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['MONGO_URI'] = 'mongodb://localhost:27017/test_trading_db'
    
    with app.app_context():
        yield app
        # Cleanup
        db.client.drop_database('test_trading_db')

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def auth_headers(client):
    # Login and get token
    response = client.post('/api/v1/auth/login', json={
        'password': 'testpassword'
    })
    token = response.get_json()['token']
    return {'Authorization': f'Bearer {token}'}

class TestStrategyAPI:
    """Test strategy endpoints"""
    
    def test_create_strategy(self, client, auth_headers):
        """Test creating a new strategy"""
        response = client.post(
            '/api/v1/strategies',
            headers=auth_headers,
            json={
                'strategy_name': 'Test Strategy',
                'symbol': 'BTC/USDT',
                'timeframe': '1h',
                'mode': 'paper',
                'broker': 'binance',
                'indicators': [
                    {'name': 'RSI', 'params': {'period': 14}}
                ],
                'entry_conditions': [
                    {'indicator_name': 'RSI', 'operator': 'less_than', 'value': 30}
                ],
                'risk_settings': {
                    'stop_loss_percent': 1.0,
                    'take_profit_percent': 2.0
                }
            }
        )
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['success'] is True
        assert 'strategy_id' in data
    
    def test_get_strategies(self, client, auth_headers):
        """Test getting all strategies"""
        response = client.get('/api/v1/strategies', headers=auth_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'strategies' in data
    
    def test_create_strategy_invalid_data(self, client, auth_headers):
        """Test validation error"""
        response = client.post(
            '/api/v1/strategies',
            headers=auth_headers,
            json={'strategy_name': 'Test'}  # Missing required fields
        )
        
        assert response.status_code == 400
    
    def test_unauthorized_access(self, client):
        """Test access without token"""
        response = client.get('/api/v1/strategies')
        
        assert response.status_code == 401
```

---

## 4. STRATEGY TESTING

### 4.1 Backtest Validation

```python
# tests/test_backtest.py
import pytest
from app.services.backtest_engine import BacktestEngine

class TestBacktestEngine:
    """Test backtesting engine"""
    
    @pytest.fixture
    def strategy(self):
        return {
            'entry_conditions': [
                {'indicator_name': 'RSI', 'operator': 'less_than', 'value': 30}
            ],
            'exit_conditions': [
                {'indicator_name': 'RSI', 'operator': 'greater_than', 'value': 70}
            ],
            'risk_settings': {
                'stop_loss_percent': 1.0,
                'take_profit_percent': 2.0
            }
        }
    
    @pytest.fixture
    def candles(self):
        # Generate sample candle data
        # In real tests, load from fixture files
        return []
    
    def test_backtest_returns_metrics(self, strategy, candles):
        """Test backtest returns all required metrics"""
        engine = BacktestEngine(strategy, initial_capital=10000)
        
        if candles:  # Skip if no data
            results = engine.run(candles)
            
            assert 'total_return' in results
            assert 'total_trades' in results
            assert 'win_rate' in results
            assert 'sharpe_ratio' in results
            assert 'max_drawdown' in results
    
    def test_backtest_no_trades_on_no_signals(self, candles):
        """Test no trades when no signals"""
        # Strategy that never triggers
        strategy = {
            'entry_conditions': [
                {'indicator_name': 'RSI', 'operator': 'less_than', 'value': 10}  # Very strict
            ],
            # ...
        }
        
        engine = BacktestEngine(strategy, 10000)
        results = engine.run(candles)
        
        assert results['total_trades'] == 0
```

### 4.2 Indicator Accuracy Tests

```python
# tests/test_indicator_accuracy.py
import pytest
import pandas as pd
import pandas_ta as ta

class TestIndicatorAccuracy:
    """Verify indicator calculations against known values"""
    
    def test_rsi_accuracy(self):
        """Test RSI against known test data"""
        # Known price series
        prices = pd.Series([44.34, 44.09, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84, 46.08, 45.89, 
                           46.03, 45.61, 46.28, 46.28, 46.00, 46.03, 46.41, 46.22, 45.64, 46.14])
        
        rsi = ta.rsi(prices, length=14)
        
        # Known RSI value at end (from external source)
        expected_rsi = 62.79  # Approximate
        assert abs(rsi.iloc[-1] - expected_rsi) < 1
    
    def test_macd_cross_accuracy(self):
        """Test MACD crossover detection"""
        prices = pd.Series([100, 102, 101, 103, 104, 106, 108, 107, 109, 110])
        
        macd = ta.macd(prices)
        macd_line = macd['MACD_12_26_9']
        signal_line = macd['MACDs_12_26_9']
        
        # Check that we have valid values
        assert not macd_line.isna().all()
        assert not signal_line.isna().all()
```

---

## 5. E2E TESTS (Playwright)

### 5.1 Setup

```bash
# Install Playwright
npm install -D @playwright/test playwright
npx playwright install chromium

# Run E2E tests
npx playwright test
```

### 5.2 E2E Test Examples

```javascript
// tests/e2e/login.spec.js
import { test, expect } from '@playwright/test';

test.describe('Login', () => {
  test('should login successfully with correct password', async ({ page }) => {
    await page.goto('http://localhost:5173/login');
    
    await page.fill('input[type="password"]', 'correctpassword');
    await page.click('button[type="submit"]');
    
    // Should redirect to dashboard
    await expect(page).toHaveURL('/dashboard');
    await expect(page.locator('text=Balance')).toBeVisible();
  });
  
  test('should show error with wrong password', async ({ page }) => {
    await page.goto('http://localhost:5173/login');
    
    await page.fill('input[type="password"]', 'wrongpassword');
    await page.click('button[type="submit"]');
    
    await expect(page.locator('text=Invalid credentials')).toBeVisible();
  });
});
```

```javascript
// tests/e2e/strategy.spec.js
import { test, expect } from '@playwright/test';

test.describe('Strategy Management', () => {
  test('should create a new strategy', async ({ page }) => {
    // Login first
    await page.goto('http://localhost:5173/login');
    await page.fill('input[type="password"]', 'password');
    await page.click('button');
    
    // Navigate to strategies
    await page.click('text=Strategies');
    await page.click('text=New');
    
    // Fill form
    await page.fill('input[name="strategy_name"]', 'My Test Strategy');
    await page.selectOption('select[name="symbol"]', 'BTC/USDT');
    await page.selectOption('select[name="timeframe"]', '1h');
    
    // Add indicator
    await page.click('text=Add Indicator');
    await page.selectOption('select[name="indicator"]', 'RSI');
    await page.fill('input[name="period"]', '14');
    
    // Save
    await page.click('text=Save');
    
    // Should see success message
    await expect(page.locator('text=Strategy created')).toBeVisible();
  });
  
  test('should start a strategy bot', async ({ page }) => {
    // Login and navigate to strategies
    // ... login code ...
    
    await page.click('text=Strategies');
    
    // Click start on a strategy
    await page.click('button:has-text("Start")');
    
    // Should show running status
    await expect(page.locator('text=Running')).toBeVisible();
  });
});
```

---

## 6. TEST DATA MANAGEMENT

### 6.1 Fixtures

```python
# tests/fixtures/candles.py
import pytest
import pandas as pd
from datetime import datetime, timedelta

@pytest.fixture
def sample_candles():
    """Generate sample candle data for testing"""
    base_time = datetime(2024, 1, 1)
    candles = []
    
    for i in range(100):
        candles.append({
            'timestamp': (base_time + timedelta(hours=i)).isoformat(),
            'open': 45000 + i * 10,
            'high': 45100 + i * 10,
            'low': 44900 + i * 10,
            'close': 45050 + i * 10,
            'volume': 1000 + i * 10
        })
    
    return candles

@pytest.fixture
def sample_strategy():
    """Sample strategy for testing"""
    return {
        'strategy_name': 'Test Strategy',
        'symbol': 'BTC/USDT',
        'timeframe': '1h',
        'indicators': [
            {'name': 'RSI', 'params': {'period': 14}},
            {'name': 'EMA', 'params': {'period': 9}}
        ],
        'entry_conditions': [
            {'indicator_name': 'RSI', 'operator': 'less_than', 'value': 30}
        ],
        'exit_conditions': [
            {'indicator_name': 'RSI', 'operator': 'greater_than', 'value': 70}
        ],
        'risk_settings': {
            'stop_loss_percent': 1.0,
            'take_profit_percent': 2.0
        }
    }
```

---

## 7. COVERAGE TARGETS

### Coverage Goals

| Component | Target Coverage |
|-----------|-----------------|
| Indicators | 90%+ |
| Risk Manager | 95%+ |
| Signal Generator | 90%+ |
| API Endpoints | 80%+ |
| Overall | 80%+ |

### Running Coverage

```bash
# Backend
cd backend
pytest --cov=app --cov-report=html --cov-report=term
open htmlcov/index.html

# Frontend
cd frontend
npm run test:coverage
```

---

## 8. CI/CD INTEGRATION

### 8.1 GitHub Actions

```yaml
# .github/workflows/test.yml
name: Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install pytest pytest-cov
      - name: Run tests
        run: |
          cd backend
          pytest --cov=app --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Node
        uses: actions/setup-node@v3
        with:
          node-version: '20'
      - name: Install dependencies
        run: |
          cd frontend
          npm ci
      - name: Run tests
        run: |
          cd frontend
          npm run test
```

---

## 9. TESTING CHECKLIST

### Pre-commit
- [ ] All unit tests passing
- [ ] Code coverage meets targets
- [ ] No linting errors

### Pre-merge
- [ ] Integration tests passing
- [ ] E2E tests for critical flows
- [ ] Backtest validation tests passing

### Pre-release
- [ ] Full test suite passing
- [ ] Load tests completed
- [ ] No critical bugs in test reports

---

*End of Testing Documentation*