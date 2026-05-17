# BROKER INTEGRATION DOCUMENTATION

## Overview
This document covers the integration with supported brokers: Binance, Zerodha, and Upstox. It describes the abstract interface, concrete implementations, credential management, and API usage.

---

## 1. BROKER ARCHITECTURE

### 1.1 Abstract Broker Interface

```python
# app/services/broker/base.py
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

class BrokerInterface(ABC):
    """Abstract base class for all broker integrations"""
    
    @abstractmethod
    def get_balance(self) -> Dict[str, float]:
        """Get account balance"""
        pass
    
    @abstractmethod
    def create_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = 'market',
        price: Optional[float] = None
    ) -> Dict:
        """Place a trading order"""
        pass
    
    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        pass
    
    @abstractmethod
    def get_current_price(self, symbol: str) -> float:
        """Get current market price"""
        pass
    
    @abstractmethod
    def get_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 100
    ) -> List[Dict]:
        """Get OHLCV candlestick data"""
        pass
    
    @abstractmethod
    def get_positions(self) -> List[Dict]:
        """Get open positions"""
        pass
    
    @abstractmethod
    def get_orders(self, status: str = 'open') -> List[Dict]:
        """Get orders (open, closed, etc.)"""
        pass
    
    @abstractmethod
    def get_symbols(self) -> List[str]:
        """Get available trading symbols"""
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """Test broker connection"""
        pass
```

### 1.2 Broker Factory

```python
# app/services/broker_factory.py
class BrokerFactory:
    """Factory for creating broker instances"""
    
    _brokers = {
        'binance': 'BinanceBroker',
        'zerodha': 'ZerodhaBroker',
        'upstox': 'UpstoxBroker',
    }
    
    @classmethod
    def create(cls, broker_name: str, credentials: Dict) -> BrokerInterface:
        """Create a broker instance with given credentials"""
        
        if broker_name not in cls._brokers:
            raise ValueError(f"Unsupported broker: {broker_name}")
        
        # Import the broker class
        if broker_name == 'binance':
            from app.services.brokers.binance import BinanceBroker
            return BinanceBroker(
                api_key=credentials['api_key'],
                api_secret=credentials['api_secret'],
                testnet=credentials.get('testnet', True)
            )
        elif broker_name == 'zerodha':
            from app.services.brokers.zerodha import ZerodhaBroker
            return ZerodhaBroker(
                api_key=credentials['api_key'],
                access_token=credentials['access_token']
            )
        elif broker_name == 'upstox':
            from app.services.brokers.upstox import UpstoxBroker
            return UpstoxBroker(
                api_key=credentials['api_key'],
                api_secret=credentials['api_secret']
            )
    
    @classmethod
    def get_from_db(cls, broker_name: str) -> BrokerInterface:
        """Create broker instance from stored credentials"""
        
        from app.utils.encryption import decrypt
        from app.extensions import db
        
        broker_doc = db.brokers.find_one({'broker_name': broker_name})
        
        if not broker_doc:
            raise ValueError(f"Broker {broker_name} not connected")
        
        credentials = {
            'api_key': decrypt(broker_doc['api_key_encrypted']),
            'api_secret': decrypt(broker_doc['api_secret_encrypted']),
            'testnet': broker_doc.get('testnet_enabled', True)
        }
        
        return cls.create(broker_name, credentials)
```

---

## 2. BINANCE INTEGRATION

### 2.1 Prerequisites

1. Create Binance account (https://www.binance.com)
2. Generate API Key:
   - Go to API Management
   - Create new API key
   - Enable "Read-Only" for reading data (optional)
   - Enable "Enable Trading" for trading
   - Set IP restrictions (optional but recommended)
3. For testing, use Testnet:
   - Go to https://testnet.binancefuture.com
   - Create testnet API key

### 2.2 Implementation

```python
# app/services/brokers/binance.py
import ccxt
from typing import Dict, List, Optional
from app.services.broker.base import BrokerInterface

class BinanceBroker(BrokerInterface):
    """Binance broker implementation using CCXT"""
    
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        testnet: bool = True
    ):
        self.client = ccxt.binance({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot',  # or 'future' for futures
                'defaultQuote': 'USDT',
            }
        })
        
        if testnet:
            self.client.set_sandbox_mode(True)
            self.base_url = 'https://testnet.binance.vision/api'
        
        self.testnet = testnet
    
    def get_balance(self) -> Dict[str, float]:
        """Get account balance"""
        balance = self.client.fetch_balance()
        
        # Get USDT balance (most common)
        usdt_balance = balance.get('USDT', {})
        
        return {
            'total': usdt_balance.get('total', 0),
            'available': usdt_balance.get('free', 0),
            'used': usdt_balance.get('used', 0),
        }
    
    def create_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = 'market',
        price: Optional[float] = None
    ) -> Dict:
        """Place a trading order"""
        
        # Normalize symbol (BTC/USDT -> BTC/USDT)
        # CCXT handles this
        
        if order_type == 'market':
            order = self.client.create_market_order(symbol, side, quantity)
        elif order_type == 'limit':
            order = self.client.create_limit_order(symbol, side, quantity, price)
        else:
            raise ValueError(f"Unsupported order type: {order_type}")
        
        return self._normalize_order(order)
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        # Extract symbol from order_id or pass separately
        # This is simplified
        try:
            # Need symbol and order ID
            return True
        except Exception as e:
            print(f"Cancel order failed: {e}")
            return False
    
    def get_current_price(self, symbol: str) -> float:
        """Get current market price"""
        ticker = self.client.fetch_ticker(symbol)
        return ticker['last']
    
    def get_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 100
    ) -> List[Dict]:
        """Get OHLCV candlestick data"""
        
        # Map timeframe to Binance format
        timeframe_map = {
            '1m': '1m', '5m': '5m', '15m': '15m',
            '30m': '30m', '1h': '1h', '4h': '4h', '1d': '1d'
        }
        
        binance_tf = timeframe_map.get(timeframe, '1h')
        
        ohlcv = self.client.fetch_ohlcv(
            symbol,
            timeframe=binance_tf,
            limit=limit
        )
        
        return [
            {
                'timestamp': candle[0],
                'open': candle[1],
                'high': candle[2],
                'low': candle[3],
                'close': candle[4],
                'volume': candle[5]
            }
            for candle in ohlcv
        ]
    
    def get_positions(self) -> List[Dict]:
        """Get open positions (for futures)"""
        # Not applicable for spot trading
        # For futures, implement position fetching
        return []
    
    def get_orders(self, status: str = 'open') -> List[Dict]:
        """Get orders"""
        if status == 'open':
            orders = self.client.fetch_open_orders()
        else:
            orders = self.client.fetch_closed_orders()
        
        return [self._normalize_order(o) for o in orders]
    
    def get_symbols(self) -> List[str]:
        """Get available trading symbols"""
        markets = self.client.load_markets()
        return [symbol for symbol in markets.keys()]
    
    def test_connection(self) -> bool:
        """Test broker connection"""
        try:
            self.client.fetch_balance()
            return True
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False
    
    def _normalize_order(self, order: Dict) -> Dict:
        """Normalize order response to common format"""
        return {
            'order_id': order.get('id'),
            'symbol': order.get('symbol'),
            'side': order.get('side'),
            'type': order.get('type'),
            'quantity': order.get('amount'),
            'price': order.get('price'),
            'status': order.get('status'),
            'filled': order.get('filled'),
            'remaining': order.get('remaining'),
            'timestamp': order.get('timestamp'),
        }
```

### 2.3 Supported Symbols

Binance Spot Trading Pairs:
- BTC/USDT, ETH/USDT, BNB/USDT, etc.
- Common quote currencies: USDT, BUSD, BTC, ETH

### 2.4 Rate Limits

| Endpoint | Limit |
|----------|-------|
| General | 1200 requests/minute |
| Order placement | 10 orders/second |
| Weight varies by endpoint | See Binance docs |

### 2.5 Error Handling

```python
try:
    order = broker.create_order('BTC/USDT', 'buy', 0.01)
except ccxt.InsufficientFunds:
    print("Insufficient balance")
except ccxt.InvalidOrder:
    print("Invalid order parameters")
except ccxt.RateLimitExceeded:
    print("Rate limited, retrying...")
    time.sleep(5)
    # Retry with backoff
```

---

## 3. ZERODHA INTEGRATION

### 3.1 Prerequisites

1. Create Zerodha account (https://zerodha.com)
2. Get API Key:
   - Go to https://developers.zerodha.com
   - Create app
   - Get API Key and API Secret
3. Generate Access Token:
   - Use login credentials to generate via kite.connect()

### 3.2 Implementation

```python
# app/services/brokers/zerodha.py
from kiteconnect import KiteConnect
from typing import Dict, List, Optional
from app.services.broker.base import BrokerInterface

class ZerodhaBroker(BrokerInterface):
    """Zerodha broker implementation using Kite Connect API"""
    
    def __init__(self, api_key: str, access_token: str):
        self.kite = KiteConnect(api_key=api_key)
        self.kite.set_access_token(access_token)
        
        # Cache instrument list
        self._instruments = None
    
    def get_balance(self) -> Dict[str, float]:
        """Get account balance (margins)"""
        margins = self.kite.margins()
        
        # Total equity (sum of all segments)
        total = 0
        for segment, data in margins.items():
            total += data.get('availablecash', 0) + data.get('net', 0)
        
        return {
            'total': total,
            'available': margins.get('equity', {}).get('availablecash', 0),
            'used': margins.get('equity', {}).get('used', 0),
        }
    
    def create_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = 'market',
        price: Optional[float] = None
    ) -> Dict:
        """Place a trading order"""
        
        # Map side
        side_map = {'buy': 'BUY', 'sell': 'SELL'}
        
        # Map order type
        # MARKET = kiteconnect.KiteConstants.ORDER_TYPE_MARKET
        # LIMIT = kiteconnect.KiteConstants.ORDER_TYPE_LIMIT
        
        order_params = {
            'exchange': 'NSE',  # or 'BSE', 'MCX', etc.
            'tradingsymbol': symbol,
            'transaction_type': side_map.get(side, 'BUY'),
            'quantity': int(quantity),
            'order_type': 'MARKET' if order_type == 'market' else 'LIMIT',
        }
        
        if price:
            order_params['price'] = price
        
        order = self.kite.place_order(**order_params)
        
        return {
            'order_id': order,
            'symbol': symbol,
            'side': side,
            'status': 'pending'
        }
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        try:
            self.kite.cancel_order(order_id)
            return True
        except Exception as e:
            print(f"Cancel order failed: {e}")
            return False
    
    def get_current_price(self, symbol: str) -> float:
        """Get current market price"""
        ltp = self.kite.ltp(f"NSE:{symbol}")
        return ltp[f"NSE:{symbol}"]['lastprice']
    
    def get_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 100
    ) -> List[Dict]:
        """Get OHLCV candlestick data"""
        
        # Map timeframe to Zerodha interval
        interval_map = {
            '1m': '1minute',
            '5m': '5minute',
            '15m': '15minute',
            '30m': '30minute',
            '1h': '1hour',
            '1d': 'day'
        }
        
        interval = interval_map.get(timeframe, 'day')
        
        # Get historical data
        from datetime import datetime, timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30 * limit / 100)  # Approximate
        
        data = self.kite.historical_data(
            instrument_token=self._get_instrument_token(symbol),
            from_date=start_date.strftime('%Y-%m-%d'),
            to_date=end_date.strftime('%Y-%m-%d'),
            interval=interval,
            continuous=False
        )
        
        return [
            {
                'timestamp': candle['date'].timestamp() * 1000,
                'open': candle['open'],
                'high': candle['high'],
                'low': candle['low'],
                'close': candle['close'],
                'volume': candle['volume']
            }
            for candle in data
        ]
    
    def get_positions(self) -> List[Dict]:
        """Get open positions"""
        positions = self.kite.positions()
        
        open_positions = []
        for pos in positions.get('net', []):
            if pos.get('quantity', 0) != 0:
                open_positions.append({
                    'symbol': pos['tradingsymbol'],
                    'quantity': pos['quantity'],
                    'average_price': pos['average_price'],
                    'pnl': pos['pnl'],
                })
        
        return open_positions
    
    def get_orders(self, status: str = 'open') -> List[Dict]:
        """Get orders"""
        if status == 'open':
            orders = self.kite.orders()
        else:
            orders = self.kite.orders()  # Filter by status
        
        return [
            {
                'order_id': o['order_id'],
                'symbol': o['tradingsymbol'],
                'side': o['transaction_type'],
                'quantity': o['quantity'],
                'price': o.get('price'),
                'status': o['status'],
            }
            for o in orders
            if status == 'open' or o['status'] == status
        ]
    
    def get_symbols(self) -> List[str]:
        """Get available trading symbols"""
        instruments = self._get_instruments()
        return [i['tradingsymbol'] for i in instruments if i['exchange'] == 'NSE']
    
    def test_connection(self) -> bool:
        """Test broker connection"""
        try:
            self.kite.profile()
            return True
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False
    
    def _get_instruments(self) -> List[Dict]:
        """Get and cache instrument list"""
        if self._instruments is None:
            self._instruments = self.kite.instruments('NSE')
        return self._instruments
    
    def _get_instrument_token(self, symbol: str) -> int:
        """Get instrument token for symbol"""
        instruments = self._get_instruments()
        for inst in instruments:
            if inst['tradingsymbol'] == symbol:
                return inst['instrument_token']
        raise ValueError(f"Symbol not found: {symbol}")
```

### 3.3 Supported Instruments

- **Exchange**: NSE (National Stock Exchange), BSE (Bombay Stock Exchange)
- **Segments**: Equity, F&O (Futures & Options)
- **Examples**: RELIANCE, HDFCBANK, TCS, INFY

---

## 4. UPSTOX INTEGRATION

### 4.1 Prerequisites

1. Create Upstox account (https://upstox.com)
2. Get API Key:
   - Go to developer portal
   - Create app
   - Get API Key and API Secret
3. Generate Access Token via login flow

### 4.2 Implementation

```python
# app/services/brokers/upstox.py
from upstox_api.api import Upstox
from typing import Dict, List, Optional
from app.services.broker.base import BrokerInterface

class UpstoxBroker(BrokerInterface):
    """Upstox broker implementation"""
    
    def __init__(self, api_key: str, api_secret: str):
        self.client = Upstox(api_key, api_secret)
        self._login()
    
    def _login(self):
        # Get access token via OAuth or stored token
        # This is simplified - in production use proper OAuth flow
        access_token = self._get_access_token()
        self.client.set_access_token(access_token)
    
    def get_balance(self) -> Dict[str, float]:
        """Get account balance"""
        # Get margin details
        margin = self.client.get_margin()
        
        return {
            'total': margin.get('equity', {}).get('net', 0),
            'available': margin.get('equity', {}).get('availablecash', 0),
            'used': margin.get('equity', {}).get('marginused', 0),
        }
    
    def create_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = 'market',
        price: Optional[float] = None
    ) -> Dict:
        """Place a trading order"""
        
        from upstox_api.api import ORDER_TYPE, TRANSACTION_TYPE
        
        order_params = {
            'exchange': 'NSE',
            'symbol': symbol,
            'quantity': int(quantity),
            'transaction_type': TRANSACTION_TYPE.BUY if side == 'buy' else TRANSACTION_TYPE.SELL,
            'order_type': ORDER_TYPE.MARKET if order_type == 'market' else ORDER_TYPE.LIMIT,
            'product': 'D',  # Delivery (or 'I' for intraday)
        }
        
        if price:
            order_params['price'] = price
        
        order = self.client.place_order(**order_params)
        
        return {
            'order_id': order.get('order_id'),
            'symbol': symbol,
            'side': side,
            'status': 'pending'
        }
    
    # Implement other methods similarly to Zerodha
    # ...

    def test_connection(self) -> bool:
        """Test broker connection"""
        try:
            self.client.get_profile()
            return True
        except Exception:
            return False
```

---

## 5. CREDENTIAL MANAGEMENT

### 5.1 Secure Storage

```python
# app/utils/encryption.py
from cryptography.fernet import Fernet
import os

# Generate key (store in environment variable)
FERNET_KEY = os.environ.get('ENCRYPTION_KEY', '').encode()
if not FERNET_KEY:
    FERNET_KEY = Fernet.generate_key()
    print(f"New encryption key generated: {FERNET_KEY.decode()}")

cipher = Fernet(FERNET_KEY)

def encrypt(data: str) -> str:
    """Encrypt sensitive data"""
    return cipher.encrypt(data.encode()).decode()

def decrypt(data: str) -> str:
    """Decrypt sensitive data"""
    return cipher.decrypt(data.encode()).decode()
```

### 5.2 Storing Broker Credentials

```python
# In broker connection endpoint
from app.utils.encryption import encrypt
from app.extensions import db

def connect_broker(broker_name: str, api_key: str, api_secret: str, testnet: bool):
    # Encrypt credentials
    encrypted_key = encrypt(api_key)
    encrypted_secret = encrypt(api_secret)
    
    # Store in database
    db.brokers.update_one(
        {'broker_name': broker_name},
        {
            '$set': {
                'broker_name': broker_name,
                'api_key_encrypted': encrypted_key,
                'api_secret_encrypted': encrypted_secret,
                'testnet_enabled': testnet,
                'is_connected': True,
                'updated_at': datetime.utcnow()
            }
        },
        upsert=True
    )
```

---

## 6. BROKER-SPECIFIC NOTES

### 6.1 Binance

| Aspect | Details |
|--------|---------|
| API Library | CCXT (unified) |
| Testnet | Available (testnet.binance.vision) |
| Rate Limits | 1200 req/min, 10 orders/sec |
| Order Types | Market, Limit, Stop-Limit |
| Supported | Spot, Futures (with different config) |

### 6.2 Zerodha

| Aspect | Details |
|--------|---------|
| API Library | Kite Connect (official) |
| Sandbox | Not available (use small capital) |
| Rate Limits | 3 requests/second |
| Order Types | Market, Limit, SL, SL-M |
| Segments | NSE, BSE, F&O, MCX |

### 6.3 Upstox

| Aspect | Details |
|--------|---------|
| API Library | upstox-python (official) |
| Testnet | Not available |
| Rate Limits | 5 requests/second |
| Order Types | Market, Limit, SL |

---

## 7. ERROR HANDLING

### 7.1 Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `InsufficientFunds` | Not enough balance | Check account balance |
| `InvalidSymbol` | Symbol not found | Verify symbol format |
| `RateLimitExceeded` | Too many requests | Implement backoff |
| `ConnectionError` | Network issue | Retry with exponential backoff |
| `AuthenticationError` | Invalid credentials | Re-authenticate |

### 7.2 Retry Logic

```python
import time
from functools import wraps2

def retry_on_error(max_retries=3, delay=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise e
                    print(f"Attempt {attempt + 1} failed: {e}")
                    time.sleep(delay * (attempt + 1))  # Exponential backoff
        return wrapper
    return decorator

@retry_on_error(max_retries=3, delay=2)
def create_order_with_retry(broker, *args, **kwargs):
    return broker.create_order(*args, **kwargs)
```

---

## 8. TESTING BROKERS

### 8.1 Connection Test

```python
# Test broker connection
def test_broker(broker_name, credentials):
    broker = BrokerFactory.create(broker_name, credentials)
    
    if broker.test_connection():
        print(f"✓ {broker_name} connection successful")
        balance = broker.get_balance()
        print(f"  Balance: {balance}")
    else:
        print(f"✗ {broker_name} connection failed")
```

### 8.2 Paper Trading Testing

Before using live trading:
1. Connect broker with testnet credentials (Binance)
2. Start bot in paper mode
3. Verify trades execute correctly
4. Check trade records match expected behavior
5. Test SL/TP triggers

---

*End of Broker Integration Documentation*