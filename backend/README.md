# Indian Stock Trading Platform - Backend

Production-grade Flask backend for AI-powered Indian stock market trading platform.

## Features

- **MongoDB Atlas Integration** - Scalable cloud database
- **JWT Authentication** - Secure API access
- **REST APIs** - Complete trading operations
- **WebSocket Support** - Real-time updates
- **Risk Management** - Configurable trading controls

## Quick Start

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and update with your values:

```bash
cp .env.example .env
```

Edit `.env` and set your MongoDB Atlas connection string:

```
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/trading_platform
```

### 3. Initialize Database

Run the database setup script to create indexes:

```bash
python scripts/setup_database.py
```

### 4. Generate Sample Data (Optional)

```bash
python scripts/generate_sample_data.py
```

### 5. Run the Application

```bash
python -m flask run --app app:app
```

Or with gunicorn:

```bash
gunicorn -w 4 -b 0.0.0.0:5000 "app:create_app()"
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `/api/v1/auth` | Authentication (login, logout, refresh) |
| `/api/v1/orders` | Order management |
| `/api/v1/trades` | Trade history and execution |
| `/api/v1/positions` | Open positions |
| `/api/v1/watchlist` | Stock watchlists |
| `/api/v1/signals` | AI trading signals |
| `/api/v1/funds` | Account funds management |
| `/api/v1/notifications` | User notifications |
| `/api/v1/strategies` | Trading strategies |
| `/api/v1/market` | Market data |
| `/api/v1/dashboard` | Dashboard statistics |
| `/api/v1/settings` | User settings |
| `/api/v1/health` | Health checks |

## Database Collections

- **users** - User accounts and authentication
- **watchlists** - Stock watchlists
- **strategies** - Trading strategy configurations
- **orders** - Order management
- **trades** - Trade history
- **positions** - Open positions
- **ai_signals** - AI-generated trading signals
- **funds** - Account balance and funds
- **fund_transactions** - Transaction history
- **notifications** - User notifications
- **activity_logs** - User activity tracking

## Indian Stock Symbols

The platform supports major NSE stocks:

| Symbol | Company |
|--------|---------|
| RELIANCE | Reliance Industries |
| TCS | Tata Consultancy Services |
| INFY | Infosys |
| HDFCBANK | HDFC Bank |
| ICICIBANK | ICICI Bank |
| SBIN | State Bank of India |
| AXISBANK | Axis Bank |
| LT | Larsen & Toubro |

## Development

```bash
# Run in development mode
FLASK_ENV=development python -m flask run --app app:app

# Run with debug
FLASK_DEBUG=1 python -m flask run --app app:app
```

## Production

```bash
# Using gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 --timeout 120 "app:create_app('production')"
```

## Project Structure

```
backend/
├── app/
│   ├── api/           # API endpoints
│   ├── auth/          # Authentication
│   ├── config.py      # Configuration
│   ├── database/      # Database connection
│   ├── errors/        # Error handlers
│   ├── extensions.py  # Flask extensions
│   ├── middleware/    # Request middleware
│   ├── models/         # Data models
│   ├── services/      # Business logic
│   ├── utils/         # Utilities
│   └── websocket/     # WebSocket handlers
├── scripts/           # Database scripts
├── requirements.txt   # Python dependencies
└── .env              # Environment variables
```

## License

Proprietary - All rights reserved