# SYSTEM ARCHITECTURE DOCUMENT

## Architecture Overview

This document describes the architecture for a **single-user automated trading platform** using:
- **Frontend**: React 18 + Vite + Zustand
- **Backend**: Flask (Python) + Flask-SocketIO
- **Database**: MongoDB (MongoDB Atlas)
- **Cache/Queue**: Redis (Upstash)
- **Task Queue**: Celery + Redis broker
- **Deployment**: Docker, Render (backend), Vercel (frontend)

This is a **monolithic architecture** optimized for a single user, not a microservices system.

---

## 1. HIGH-LEVEL ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────────┐
│                          FRONTEND (Vercel)                          │
│  React + Vite + Zustand + Socket.IO Client + Tailwind CSS         │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │ HTTPS
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       BACKEND (Render)                              │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  Flask Application (Gunicorn + Eventlet)                       │ │
│  │  ├── REST API Routes (/api/v1/*)                              │ │
│  │  ├── Flask-SocketIO (Real-time WebSocket)                     │ │
│  │  └── Flask-CORS, Flask-Limiter                                │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                   │                                 │
│         ┌─────────────────────────┼─────────────────────────┐     │
│         ▼                         ▼                         ▼     │
│  ┌─────────────┐          ┌─────────────┐          ┌───────────┐ │
│  │   Redis     │          │  Celery     │          │  MongoDB  │ │
│  │  (Upstash)  │          │  Worker     │          │   Atlas   │ │
│  │  Cache +    │          │  (Background│          │           │ │
│  │  Celery     │          │   Tasks)    │          │           │ │
│  │  Broker     │          └─────────────┘          └───────────┘ │
│  └─────────────┘                                                    │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
                    ┌─────────────────────────┐
                    │    External Services    │
                    ├─────────────────────────┤
                    │  Binance API (CCXT)     │
                    │  Zerodha Kite Connect   │
                    │  Upstox API             │
                    │  Telegram Bot API       │
                    └─────────────────────────┘
```

---

## 2. FRONTEND ARCHITECTURE

### Technology Stack
- **React 18** with Vite for fast builds
- **Zustand** for lightweight state management (simpler than Redux)
- **Tailwind CSS** for styling
- **Recharts** for charts (or TradingView Lightweight Charts)
- **Axios** for REST API calls
- **Socket.IO Client** for WebSocket connections

### Component Architecture

```
frontend/src/
├── components/
│   ├── layout/
│   │   ├── Layout.tsx        # Main layout wrapper
│   │   ├── Sidebar.tsx       # Navigation sidebar
│   │   └── Header.tsx        # Top bar with mode toggle
│   │
│   ├── common/
│   │   ├── Button.tsx
│   │   ├── Input.tsx
│   │   ├── Modal.tsx
│   │   ├── Loader.tsx
│   │   └── Card.tsx
│   │
│   ├── trading/
│   │   ├── Chart.tsx         # Price chart (TradingView)
│   │   ├── OrderForm.tsx     # Manual trade form
│   │   ├── PositionCard.tsx  # Open position display
│   │   └── TradeHistory.tsx  # Trade list table
│   │
│   ├── strategy/
│   │   ├── StrategyList.tsx  # Strategy cards
│   │   ├── StrategyForm.tsx  # Create/edit strategy
│   │   ├── IndicatorSelector.tsx
│   │   └── ConditionBuilder.tsx
│   │
│   ├── backtest/
│   │   ├── BacktestForm.tsx
│   │   └── BacktestResults.tsx
│   │
│   └── dashboard/
│       ├── Dashboard.tsx
│       ├── PnLChart.tsx
│       ├── BotStatus.tsx
│       └── QuickStats.tsx
│
├── pages/
│   ├── Login.tsx
│   ├── Dashboard.tsx
│   ├── Strategies.tsx
│   ├── Bots.tsx
│   ├── Trades.tsx
│   ├── Backtest.tsx
│   ├── Settings.tsx
│   └── Logs.tsx
│
├── stores/                    # Zustand stores
│   ├── authStore.ts
│   ├── tradingStore.ts
│   ├── strategyStore.ts
│   └── uiStore.ts
│
├── hooks/
│   ├── useSocket.ts          # WebSocket connection
│   ├── useApi.ts            # API wrapper
│   └── useAuth.ts           # Auth helper
│
├── services/
│   ├── api.ts               # Axios instance
│   └── socket.ts            # Socket.IO instance
│
└── utils/
    ├── formatters.ts        # Number, date formatters
    └── validators.ts        # Form validation
```

### State Management (Zustand)

```typescript
// stores/tradingStore.ts
import { create } from 'zustand'

interface TradingState {
  mode: 'paper' | 'live'
  balance: number
  positions: Position[]
  trades: Trade[]
  setMode: (mode: 'paper' | 'live') => void
  updateBalance: (balance: number) => void
}

export const useTradingStore = create<TradingState>((set) => ({
  mode: 'paper',
  balance: 10000,
  positions: [],
  trades: [],
  setMode: (mode) => set({ mode }),
  updateBalance: (balance) => set({ balance }),
}))
```

### API Client Layer

```typescript
// services/api.ts
import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL + '/api/v1',
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default api
```

### WebSocket Integration

```typescript
// services/socket.ts
import { io } from 'socket.io-client'
import { useTradingStore } from '../stores/tradingStore'

const socket = io(import.meta.env.VITE_SOCKET_URL, {
  auth: { token: localStorage.getItem('token') },
  transports: ['websocket'],
  reconnection: true,
  reconnectionAttempts: Infinity,
  reconnectionDelay: 1000,
})

socket.on('connect', () => {
  console.log('WebSocket connected')
  socket.emit('subscribe', { channels: ['prices', 'trades', 'positions', 'signals'] })
})

socket.on('price', (data) => {
  useTradingStore.getState().updatePrice(data)
})

socket.on('trade', (data) => {
  useTradingStore.getState().addTrade(data)
})

socket.on('signal', (data) => {
  // Show notification
})

export default socket
```

---

## 3. BACKEND ARCHITECTURE

### Technology Stack
- **Flask 2.x**: Web framework
- **Flask-SocketIO**: WebSocket support
- **Flask-CORS**: Cross-origin requests
- **Flask-Limiter**: Rate limiting
- **Gunicorn**: WSGI server with eventlet for async
- **Celery**: Task queue
- **PyJWT**: JWT authentication
- **PyMongo**: MongoDB driver
- **TA-Lib / pandas-ta**: Technical indicators
- **Cryptography**: Fernet for encryption

### Flask Blueprint Structure

```
backend/app/
├── __init__.py              # Flask app factory
├── config.py                # Configuration class
├── extensions.py            # Flask extensions init
│
├── routes/                  # Blueprint routes
│   ├── __init__.py
│   ├── auth.py              # /api/v1/auth/*
│   ├── strategies.py        # /api/v1/strategies/*
│   ├── trades.py            # /api/v1/trades/*
│   ├── bot.py               # /api/v1/bot/*
│   ├── broker.py            # /api/v1/broker/*
│   ├── backtest.py          # /api/v1/backtest/*
│   ├── market.py            # /api/v1/market/*
│   └── settings.py          # /api/v1/settings/*
│
├── services/                # Business logic
│   ├── __init__.py
│   ├── auth_service.py      # Authentication
│   ├── strategy_service.py  # Strategy CRUD
│   ├── trading_engine.py    # Trade execution
│   ├── broker_factory.py    # Broker abstraction
│   ├── notification_service.py
│   ├── backtest_engine.py
│   └── risk_manager.py
│
├── models/                  # Data models
│   ├── __init__.py
│   ├── strategy.py
│   ├── trade.py
│   ├── position.py
│   ├── candle.py
│   └── user.py
│
├── tasks/                   # Celery tasks
│   ├── __init__.py
│   ├── trading_tasks.py     # Real-time evaluation
│   ├── backtest_tasks.py    # Historical backtest
│   └── maintenance_tasks.py # Cleanup, alerts
│
└── utils/                   # Helpers
    ├── __init__.py
    ├── indicators.py        # Indicator calculations
    ├── encryption.py        # Fernet encryption
    ├── validators.py       # Input validation
    └── helpers.py
```

### Flask Application Factory

```python
# app/__init__.py
from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO
from flask_limiter import Limiter
from pymongo import MongoClient

from app.config import Config
from app.extensions import init_extensions

socketio = SocketIO(cors_allowed_origins="*", async_mode='eventlet')

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    init_extensions(app)
    
    # Register blueprints
    from app.routes import auth, strategies, trades, bot, broker, backtest, market, settings
    app.register_blueprint(auth.bp, url_prefix='/api/v1/auth')
    app.register_blueprint(strategies.bp, url_prefix='/api/v1/strategies')
    # ... etc
    
    # Initialize SocketIO
    socketio.init_app(app)
    
    return app
```

### Service Layer Architecture

```python
# app/services/trading_engine.py
class TradingEngine:
    def __init__(self, broker_service, risk_manager, notification_service):
        self.broker = broker_service
        self.risk_manager = risk_manager
        self.notifications = notification_service
    
    def evaluate_strategy(self, strategy, current_candle):
        # 1. Calculate indicators
        indicators = self.calculate_indicators(strategy, current_candle)
        
        # 2. Check entry conditions
        signal = self.check_conditions(strategy.entry_conditions, indicators)
        
        # 3. If signal, check risk rules
        if signal and self.risk_manager.can_trade():
            # 4. Execute trade
            return self.execute_trade(strategy, current_candle, signal)
        
        return None
    
    def calculate_indicators(self, strategy, candle):
        # Use pandas-ta or TA-Lib
        # Return dict of indicator values
        pass
    
    def execute_trade(self, strategy, candle, signal):
        # 1. Calculate position size
        # 2. Place order via broker
        # 3. Create trade record
        # 4. Send notification
        pass
```

---

## 4. DATABASE ARCHITECTURE (MongoDB)

### Collections

```
trading_db/
├── user                    # Single document (owner settings)
├── strategies              # Trading strategies
├── trades                 # Trade history (paper + live)
├── positions              # Open positions
├── candles                # OHLCV data (TTL: 30 days)
├── brokers                # Broker credentials (encrypted)
├── backtests              # Backtest results
├── notifications          # User notifications
└── logs                   # System logs
```

### Index Definitions

```javascript
// trades collection
db.trades.createIndex({ "strategy_id": 1, "created_at": -1 })
db.trades.createIndex({ "symbol": 1, "mode": 1 })
db.trades.createIndex({ "status": 1 })

// candles collection (TTL - 30 days)
db.candles.createIndex({ "symbol": 1, "timeframe": 1, "timestamp": -1 }, { expireAfterSeconds: 2592000 })

// strategies collection
db.strategies.createIndex({ "is_active": 1 })

// logs collection
db.logs.createIndex({ "level": 1, "created_at": -1 })
```

### MongoDB Connection

```python
# app/config.py
class Config:
    MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/trading_db')
    
# app/extensions.py
from pymongo import MongoClient

mongo = MongoClient(Config.MONGO_URI)
db = mongo.get_default_database()
```

---

## 5. CELERY TASK ARCHITECTURE

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Celery Architecture                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐        ┌──────────────┐                     │
│  │   Flask      │        │  Celery      │                     │
│  │   Web Server │───────▶│  Broker      │                     │
│  │  (Render)    │        │  (Redis)     │                     │
│  └──────────────┘        └──────┬───────┘                     │
│                                │                               │
│         ┌──────────────────────┼──────────────────────┐      │
│         ▼                      ▼                      ▼      │
│  ┌─────────────┐        ┌─────────────┐        ┌───────────┐ │
│  │  Trading   │        │  Backtest   │        │Maintenance│ │
│  │  Worker    │        │  Worker     │        │  Worker   │ │
│  │  (realtime)│        │  (async)    │        │  (daily)  │ │
│  └─────────────┘        └─────────────┘        └───────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Celery Configuration

```python
# app/celery.py
from celery import Celery

celery = Celery(
    'trading_app',
    broker=os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/1'),
    backend=os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/2'),
)

celery.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_routes={
        'app.tasks.trading.*': {'queue': 'trading'},
        'app.tasks.backtest.*': {'queue': 'backtest'},
        'app.tasks.maintenance.*': {'queue': 'maintenance'},
    },
    beat_schedule={
        'evaluate-strategies': {
            'task': 'app.tasks.trading.evaluate_all_strategies',
            'schedule': 300.0,  # 5 minutes
        },
        'check-positions': {
            'task': 'app.tasks.trading.check_all_positions',
            'schedule': 60.0,  # 1 minute
        },
    }
)
```

### Trading Tasks

```python
# app/tasks/trading_tasks.py
from app.celery import celery
from app.services.trading_engine import TradingEngine
from app.services.broker_factory import BrokerFactory

@celery.task(bind=True, max_retries=3)
def evaluate_strategy(self, strategy_id: str):
    """Evaluate a single strategy on latest data"""
    strategy = db.strategies.find_one({'_id': ObjectId(strategy_id)})
    broker = BrokerFactory.get_broker(strategy['broker'])
    
    # Fetch latest candle
    candle = broker.get_ohlcv(strategy['symbol'], strategy['timeframe'], 1)
    
    # Evaluate
    engine = TradingEngine(broker, risk_manager, notifications)
    signal = engine.evaluate_strategy(strategy, candle)
    
    return signal

@celery.task
def evaluate_all_strategies():
    """Evaluate all active strategies"""
    active_strategies = db.strategies.find({'is_active': True})
    for strategy in active_strategies:
        evaluate_strategy.delay(str(strategy['_id']))

@celery.task
def check_all_positions():
    """Check all open positions for SL/TP triggers"""
    positions = db.positions.find({'status': 'open'})
    for position in positions:
        check_position_sl_tp.delay(str(position['_id']))
```

### Backtest Tasks

```python
# app/tasks/backtest_tasks.py
@celery.task(bind=True, soft_time_limit=3600)
def run_backtest(self, backtest_id: str):
    """Run historical backtest"""
    backtest = db.backtests.find_one({'_id': ObjectId(backtest_id)})
    strategy = db.strategies.find_one({'_id': ObjectId(backtest['strategy_id'])})
    
    # Fetch historical data
    broker = BrokerFactory.get_broker(strategy['broker'])
    candles = broker.get_ohlcv(backtest['symbol'], backtest['timeframe'], limit=10000)
    
    # Run backtest
    engine = BacktestEngine(strategy, backtest['initial_capital'])
    results = engine.run(candles)
    
    # Save results
    db.backtests.update_one(
        {'_id': ObjectId(backtest_id)},
        {'$set': {**results, 'status': 'completed'}}
    )
    
    return results
```

---

## 6. WEBSOCKET ARCHITECTURE

### Socket.IO Integration

```python
# app/__init__.py (continued)
from flask_socketio import SocketIO

socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Import and register events
from app.routes import websocket
websocket.register_events(socketio)
```

### WebSocket Events

```python
# app/routes/websocket.py
from flask_socketio import emit, join_room
from flask import request
from app.services import auth_service

def register_events(socketio):
    
    @socketio.on('connect')
    def handle_connect(auth):
        token = auth.get('token')
        if auth_service.verify_token(token):
            join_room('user_room')
            emit('connected', {'status': 'ok'})
        else:
            return False  # Reject connection
    
    @socketio.on('subscribe')
    def handle_subscribe(data):
        channels = data.get('channels', [])
        for channel in channels:
            join_room(channel)
    
    @socketio.on('unsubscribe')
    def handle_unsubscribe(data):
        channels = data.get('channels', [])
        for channel in channels:
            leave_room(channel)
    
    @socketio.on('ping')
    def handle_ping():
        emit('pong')
```

### Broadcasting from Tasks

```python
# app/tasks/trading_tasks.py (add to execute_trade)
def execute_trade(strategy, candle, signal):
    # ... execute trade ...
    
    # Broadcast to WebSocket
    from app import socketio
    socketio.emit('trade', {
        'trade_id': str(trade['_id']),
        'symbol': trade['symbol'],
        'side': trade['side'],
        'mode': trade['mode'],
        'pnl': trade.get('pnl'),
    }, room='user_room')
    
    return trade
```

### Frontend WebSocket Usage

```typescript
// services/socket.ts
import { io } from 'socket.io-client'

export const socket = io(import.meta.env.VITE_SOCKET_URL, {
  auth: { token: localStorage.getItem('token') },
  transports: ['websocket'],
  reconnection: true,
  reconnectionDelayMax: 30000,
})

socket.on('connect', () => {
  console.log('Connected to WebSocket')
  socket.emit('subscribe', { channels: ['prices', 'trades', 'positions', 'signals'] })
})

socket.on('price', (data) => {
  useMarketStore.getState().updatePrice(data)
})

socket.on('trade', (data) => {
  useTradingStore.getState().addTrade(data)
})

socket.on('signal', (data) => {
  useNotificationStore.getState().addSignal(data)
})
```

---

## 7. BROKER INTEGRATION ARCHITECTURE

### Abstract Broker Interface

```python
# app/services/broker_factory.py
from abc import ABC, abstractmethod

class BrokerInterface(ABC):
    @abstractmethod
    def get_balance(self) -> dict:
        pass
    
    @abstractmethod
    def create_order(self, symbol: str, side: str, qty: float, 
                     order_type: str = 'market', price: float = None) -> dict:
        pass
    
    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
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
    def get_orders(self, status: str = 'open') -> list:
        pass
```

### Binance Implementation

```python
# app/services/brokers/binance.py
import ccxt
from app.services.broker_factory import BrokerInterface

class BinanceBroker(BrokerInterface):
    def __init__(self, api_key: str, api_secret: str, testnet: bool = True):
        self.client = ccxt.binance({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'}
        })
        if testnet:
            self.client.set_sandbox_mode(True)
    
    def get_balance(self) -> dict:
        balance = self.client.fetch_balance()
        return {
            'total': balance['total']['USDT'],
            'available': balance['free']['USDT']
        }
    
    def create_order(self, symbol, side, qty, order_type='market', price=None):
        if order_type == 'market':
            order = self.client.create_market_order(symbol, side, qty)
        else:
            order = self.client.create_limit_order(symbol, side, qty, price)
        return order
    
    def get_ohlcv(self, symbol, timeframe, limit):
        return self.client.fetch_ohlcv(symbol, timeframe, limit=limit)
    
    # ... implement other methods
```

### Broker Factory

```python
# app/services/broker_factory.py
class BrokerFactory:
    _brokers = {
        'binance': BinanceBroker,
        'zerodha': ZerodhaBroker,
        'upstox': UpstoxBroker,
    }
    
    @classmethod
    def get_broker(cls, broker_name: str, credentials: dict = None):
        if broker_name not in cls._brokers:
            raise ValueError(f"Unknown broker: {broker_name}")
        
        if credentials:
            return cls._brokers[broker_name](**credentials)
        
        # Get from database
        broker_doc = db.brokers.find_one({'broker_name': broker_name})
        if not broker_doc:
            raise ValueError(f"Broker {broker_name} not connected")
        
        # Decrypt credentials
        from app.utils.encryption import decrypt
        api_key = decrypt(broker_doc['api_key_encrypted'])
        api_secret = decrypt(broker_doc['api_secret_encrypted'])
        
        return cls._brokers[broker_name](api_key, api_secret, broker_doc.get('testnet_enabled', True))
```

---

## 8. RISK MANAGEMENT ARCHITECTURE

### Risk Manager Service

```python
# app/services/risk_manager.py
class RiskManager:
    def __init__(self, settings: dict = None):
        self.settings = settings or self.get_default_settings()
    
    @staticmethod
    def get_default_settings():
        return {
            'max_daily_loss_percent': 5.0,
            'risk_per_trade_percent': 1.0,
            'max_open_positions': 3,
            'max_consecutive_losses': 3,
            'max_drawdown_percent': 10.0,
            'trade_cooldown_minutes': 5,
            'mandatory_sl': True,
        }
    
    def can_trade(self, mode: str = 'paper') -> tuple[bool, str]:
        """Returns (can_trade, reason)"""
        
        # Check daily loss
        daily_pnl = self.get_daily_pnl(mode)
        if daily_pnl < -self.settings['max_daily_loss_percent']:
            return False, "Daily loss limit exceeded"
        
        # Check max positions
        open_positions = self.get_open_positions_count(mode)
        if open_positions >= self.settings['max_open_positions']:
            return False, "Max open positions reached"
        
        # Check consecutive losses
        if self.get_consecutive_losses() >= self.settings['max_consecutive_losses']:
            return False, "Circuit breaker: consecutive losses"
        
        # Check cooldown
        if not self.is_cooldown_elapsed():
            return False, "Trade cooldown not elapsed"
        
        # Check drawdown
        if self.get_total_drawdown() >= self.settings['max_drawdown_percent']:
            return False, "Max drawdown exceeded"
        
        return True, "OK"
    
    def calculate_position_size(self, capital: float, entry: float, 
                               stop_loss: float) -> float:
        risk_amount = capital * (self.settings['risk_per_trade_percent'] / 100)
        risk_per_share = abs(entry - stop_loss)
        return risk_amount / risk_per_share
```

---

## 9. DEPLOYMENT ARCHITECTURE

### Development (Docker Compose)

```yaml
# docker-compose.yml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "5000:5000"
    environment:
      - MONGO_URI=mongodb://mongo:27017/trading_db
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/1
    depends_on:
      - mongo
      - redis
    volumes:
      - ./backend:/app
    command: gunicorn --bind 0.0.0.0:5000 --worker-class eventlet -w 1 app:app

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "5173:5173"
    environment:
      - VITE_API_URL=http://localhost:5000
      - VITE_SOCKET_URL=http://localhost:5000
    depends_on:
      - backend

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
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: celery -A app.celery worker -l INFO -Q trading,backtest,maintenance
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

### Production Deployment

**Render (Backend)**:
- Web Service: Gunicorn with eventlet
- Background Worker: Celery worker
- Environment: MONGO_URI, REDIS_URL, JWT_SECRET, etc.

**Vercel (Frontend)**:
- Framework: Vite
- Build: `npm run build`
- Output: `dist`

**MongoDB Atlas**:
- Free tier M0 cluster
- Network access: 0.0.0.0/0 (with strong password)

**Upstash (Redis)**:
- Free tier
- Used for Celery broker + caching

---

## 10. DATA FLOW ARCHITECTURE

### Trading Flow (Real-time)

```
1. Celery Beat schedules 'evaluate_all_strategies'
         │
         ▼
2. Task fetches latest candle from broker
         │
         ▼
3. Calculate indicators (RSI, EMA, etc.)
         │
         ▼
4. Check entry conditions against indicators
         │
         ▼
5. If BUY/SELL signal:
   ├── Risk Manager checks (daily loss, positions, cooldown)
   ├── If passed:
   │   ├── Create trade record (mode: paper/live)
   │   ├── If live: execute via broker API
   │   ├── If paper: simulate at current price
   │   ├── Update position
   │   ├── Send Telegram notification
   │   └── Emit WebSocket event
   └── If failed: log skip reason
```

### Backtest Flow

```
1. User submits backtest request (POST /api/v1/backtest/run)
         │
         ▼
2. Flask creates backtest record, returns 202
         │
         ▼
3. Celery task 'run_backtest' queued
         │
         ▼
4. Task fetches historical candles
         │
         ▼
5. Iterate through each candle:
   ├── Calculate indicators
   ├── Check conditions
   ├── Execute virtual trades
   ├── Update equity curve
         │
         ▼
6. Calculate final metrics (Sharpe, drawdown, etc.)
         │
         ▼
7. Save results to MongoDB
         │
         ▼
8. WebSocket emits backtest_complete
```

---

## 11. ERROR HANDLING ARCHITECTURE

### Error Categories & Handlers

```python
# app/utils/error_handlers.py
class TradingError(Exception):
    """Base trading error"""
    pass

class BrokerConnectionError(TradingError):
    """Broker API connection failed"""
    pass

class InsufficientBalanceError(TradingError):
    """Insufficient funds"""
    pass

class RiskLimitExceededError(TradingError):
    """Risk limit reached"""
    pass

class InvalidSignalError(TradingError):
    """Invalid trading signal"""
    pass
```

### Global Error Handler

```python
# app/__init__.py (error handlers)
@app.errorhandler(Exception)
def handle_error(e):
    logger.error(f"Unhandled error: {str(e)}", exc_info=True)
    
    if isinstance(e, TradingError):
        return jsonify({'error': str(e)}), 400
    
    return jsonify({'error': 'Internal server error'}), 500
```

### Circuit Breaker

```python
# app/services/risk_manager.py
class CircuitBreaker:
    def __init__(self):
        self.error_count = 0
        self.circuit_open = False
        self.last_error_time = None
    
    def record_error(self):
        self.error_count += 1
        self.last_error_time = datetime.utcnow()
        
        if self.error_count >= 5:
            self.circuit_open = True
    
    def can_execute(self) -> bool:
        if not self.circuit_open:
            return True
        
        # Auto-reset after 5 minutes
        if (datetime.utcnow() - self.last_error_time).seconds > 300:
            self.circuit_open = False
            self.error_count = 0
            return True
        
        return False
```

---

## 12. MONITORING & LOGGING

### Structured Logging

```python
# app/utils/logging.py
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        if hasattr(record, 'trade_id'):
            log_data['trade_id'] = record.trade_id
        if hasattr(record, 'strategy_id'):
            log_data['strategy_id'] = record.strategy_id
        return json.dumps(log_data)

# Usage
logger = logging.getLogger('trading')
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger.addHandler(handler)
```

### Log Collection Strategy

| Log Type | Storage | Retention |
|----------|---------|----------|
| Trade logs | MongoDB `logs` | 90 days |
| Error logs | MongoDB `logs` | 90 days |
| Access logs | Console/stdout | N/A |
| System metrics | Optional (Prometheus) | 30 days |

### Health Check Endpoint

```python
# app/routes/health.py
@app.route('/api/v1/health')
def health_check():
    checks = {
        'mongo': check_mongo(),
        'redis': check_redis(),
        'celery': check_celery(),
    }
    
    all_healthy = all(checks.values())
    status = 200 if all_healthy else 503
    
    return jsonify({
        'status': 'healthy' if all_healthy else 'unhealthy',
        'checks': checks,
        'timestamp': datetime.utcnow().isoformat()
    }), status

def check_mongo():
    try:
        mongo.db.command('ping')
        return True
    except:
        return False

def check_redis():
    try:
        redis.ping()
        return True
    except:
        return False
```

---

## 13. ARCHITECTURE DECISION SUMMARY

### Key Architecture Choices

| Decision | Rationale |
|----------|-----------|
| Flask + Gunicorn + Eventlet | Sync Flask needs eventlet for WebSocket async |
| MongoDB | Flexible schema for trading data, simpler than SQL |
| Redis (Upstash) | Free tier, both caching + Celery broker |
| Celery | Python native, works well with Flask |
| Zustand | Simpler than Redux, sufficient for single-user |
| Docker Compose | Local development + production parity |
| Render + Vercel | Free tier suitable for personal use |

### What This Architecture Is NOT

- ❌ Not microservices (single Flask app)
- ❌ Not multi-tenant (single user)
- ❌ Not PostgreSQL (MongoDB)
- ❌ Not Kafka/RabbitMQ (Celery + Redis)
- ❌ Not complex load balancing (single user)

### Scalability Notes

For single-user personal trading:
- Current architecture handles 10+ concurrent strategies
- MongoDB M0 free tier sufficient for < 1GB data
- Upstash free tier sufficient for caching + broker
- Render free tier sufficient for backend + worker

If scaling to multi-user in future:
- Add user_id to all collections
- Implement JWT-based multi-user auth
- Consider PostgreSQL for relational data
- Add Celery task isolation per user

---

*End of Architecture Document*