# INDIAN STOCK TRADING PLATFORM - API CONTRACTS
## Production-Grade API Documentation for React + Flask Backend

---

# TABLE OF CONTENTS

1. [API Response Standards](#1-api-response-standards)
2. [Authentication API](#2-authentication-api)
3. [User Management API](#3-user-management-api)
4. [Watchlist API](#4-watchlist-api)
5. [Orders API](#5-orders-api)
6. [Positions API](#6-positions-api)
7. [Trades API](#7-trades-api)
8. [Funds API](#8-funds-api)
9. [Strategies API](#9-strategies-api)
10. [AI Signals API](#10-ai-signals-api)
11. [Notifications API](#11-notifications-api)
12. [Dashboard API](#12-dashboard-api)
13. [Market Data API](#13-market-data-api)
14. [WebSocket Events](#14-websocket-events)
15. [Settings API](#15-settings-api)
16. [API Security & Best Practices](#16-api-security--best-practices)
17. [API Versioning Strategy](#17-api-versioning-strategy)
18. [Frontend Integration Guidelines](#18-frontend-integration-guidelines)

---

# 1. API RESPONSE STANDARDS

## Base URL

```
Production: https://api.yourdomain.com/api/v1
Development: http://localhost:5000/api/v1
WebSocket: ws://localhost:5000/socket.io
```

## Success Response Format

```json
{
  "success": true,
  "message": "Operation completed successfully",
  "data": {
    // Response data object
  },
  "timestamp": "2026-05-16T10:30:00Z"
}
```

## Error Response Format

```json
{
  "success": false,
  "message": "Error description",
  "errors": [
    {
      "field": "email",
      "message": "Invalid email format"
    }
  ],
  "timestamp": "2026-05-16T10:30:00Z"
}
```

## Pagination Response Format

```json
{
  "success": true,
  "data": [],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 150,
    "pages": 8
  },
  "timestamp": "2026-05-16T10:30:00Z"
}
```

---

# 2. AUTHENTICATION API

## Overview

All authentication endpoints use JWT tokens. Access tokens expire in 1 hour, refresh tokens in 7 days.

## Endpoints

### POST /api/v1/auth/register

Register a new user account.

| Attribute | Value |
|-----------|-------|
| Endpoint | `/api/v1/auth/register` |
| Method | POST |
| Auth Required | No |
| Rate Limit | 5 requests/minute |

**Request Headers**
```
Content-Type: application/json
```

**Request Body**
```json
{
  "email": "trader@example.com",
  "password": "SecurePass123!",
  "full_name": "Rajesh Kumar",
  "phone": "+919876543210",
  "pan_number": "ABCDE1234F",
  "broker": "zerodha"
}
```

**Validation Rules**
| Field | Type | Rules |
|-------|------|-------|
| email | string | Required, valid email, unique |
| password | string | Min 8 chars, 1 uppercase, 1 number, 1 special |
| full_name | string | Required, 2-100 chars |
| phone | string | Required, valid Indian mobile |
| pan_number | string | Required, valid PAN format |
| broker | string | Optional, enum: zerodha, upstox, angel, iifl |

**Success Response (201)**
```json
{
  "success": true,
  "message": "Registration successful. Please verify your email.",
  "data": {
    "user_id": "usr_abc123",
    "email": "trader@example.com",
    "full_name": "Rajesh Kumar",
    "broker": "zerodha",
    "created_at": "2026-05-16T10:30:00Z"
  },
  "timestamp": "2026-05-16T10:30:00Z"
}
```

**Error Response (400)**
```json
{
  "success": false,
  "message": "Validation failed",
  "errors": [
    {"field": "email", "message": "Email already registered"},
    {"field": "password", "message": "Password must contain 1 uppercase letter"}
  ],
  "timestamp": "2026-05-16T10:30:00Z"
}
```

**Status Codes**
- 201: Created
- 400: Validation Error
- 409: Conflict
- 429: Rate Limited
- 500: Server Error

---

### POST /api/v1/auth/login

Authenticate user and receive JWT tokens.

| Attribute | Value |
|-----------|-------|
| Endpoint | `/api/v1/auth/login` |
| Method | POST |
| Auth Required | No |
| Rate Limit | 10 requests/minute |

**Request Headers**
```
Content-Type: application/json
```

**Request Body**
```json
{
  "email": "trader@example.com",
  "password": "SecurePass123!"
}
```

**Validation Rules**
| Field | Type | Rules |
|-------|------|-------|
| email | string | Required, valid email |
| password | string | Required |

**Success Response (200)**
```json
{
  "success": true,
  "message": "Login successful",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires_in": 3600,
    "token_type": "Bearer",
    "user": {
      "user_id": "usr_abc123",
      "email": "trader@example.com",
      "full_name": "Rajesh Kumar",
      "role": "trader",
      "broker": "zerodha",
      "twofa_enabled": false
    }
  },
  "timestamp": "2026-05-16T10:30:00Z"
}
```

**Error Response (401)**
```json
{
  "success": false,
  "message": "Invalid credentials",
  "errors": [],
  "timestamp": "2026-05-16T10:30:00Z"
}
```

**Status Codes**
- 200: Success
- 401: Unauthorized
- 423: Account Locked
- 429: Rate Limited

---

### POST /api/v1/auth/logout

Invalidate current session and tokens.

| Attribute | Value |
|-----------|-------|
| Endpoint | `/api/v1/auth/logout` |
| Method | POST |
| Auth Required | Yes |
| Rate Limit | 30 requests/minute |

**Request Headers**
```
Content-Type: application/json
Authorization: Bearer <access_token>
```

**Request Body**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Success Response (200)**
```json
{
  "success": true,
  "message": "Logged out successfully",
  "data": {},
  "timestamp": "2026-05-16T10:30:00Z"
}
```

**Error Response (401)**
```json
{
  "success": false,
  "message": "Invalid or expired token",
  "errors": [],
  "timestamp": "2026-05-16T10:30:00Z"
}
```

---

### POST /api/v1/auth/refresh

Refresh access token using refresh token.

| Attribute | Value |
|-----------|-------|
| Endpoint | `/api/v1/auth/refresh` |
| Method | POST |
| Auth Required | No |
| Rate Limit | 20 requests/minute |

**Request Headers**
```
Content-Type: application/json
```

**Request Body**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Success Response (200)**
```json
{
  "success": true,
  "message": "Token refreshed successfully",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires_in": 3600,
    "token_type": "Bearer"
  },
  "timestamp": "2026-05-16T10:30:00Z"
}
```

**Error Response (401)**
```json
{
  "success": false,
  "message": "Invalid or expired refresh token",
  "errors": [],
  "timestamp": "2026-05-16T10:30:00Z"
}
```

---

### GET /api/v1/auth/profile

Get current user profile.

| Attribute | Value |
|-----------|-------|
| Endpoint | `/api/v1/auth/profile` |
| Method | GET |
| Auth Required | Yes |

**Request Headers**
```
Authorization: Bearer <access_token>
```

**Success Response (200)**
```json
{
  "success": true,
  "message": "Profile retrieved successfully",
  "data": {
    "user_id": "usr_abc123",
    "email": "trader@example.com",
    "full_name": "Rajesh Kumar",
    "phone": "+919876543210",
    "role": "trader",
    "broker": "zerodha",
    "twofa_enabled": false,
    "email_verified": true,
    "kyc_status": "verified",
    "created_at": "2026-01-01T00:00:00Z",
    "last_login": "2026-05-16T09:00:00Z"
  },
  "timestamp": "2026-05-16T10:30:00Z"
}
```

---

### PUT /api/v1/auth/profile

Update user profile information.

| Attribute | Value |
|-----------|-------|
| Endpoint | `/api/v1/auth/profile` |
| Method | PUT |
| Auth Required | Yes |

**Request Headers**
```
Content-Type: application/json
Authorization: Bearer <access_token>
```

**Request Body**
```json
{
  "full_name": "Rajesh Kumar Sharma",
  "phone": "+919876543210"
}
```

**Validation Rules**
| Field | Type | Rules |
|-------|------|-------|
| full_name | string | Optional, 2-100 chars |
| phone | string | Optional, valid Indian mobile |

**Success Response (200)**
```json
{
  "success": true,
  "message": "Profile updated successfully",
  "data": {
    "user_id": "usr_abc123",
    "full_name": "Rajesh Kumar Sharma",
    "phone": "+919876543210",
    "updated_at": "2026-05-16T10:30:00Z"
  },
  "timestamp": "2026-05-16T10:30:00Z"
}
```

---

### PUT /api/v1/auth/change-password

Change user password.

| Attribute | Value |
|-----------|-------|
| Endpoint | `/api/v1/auth/change-password` |
| Method | PUT |
| Auth Required | Yes |
| Rate Limit | 5 requests/minute |

**Request Headers**
```
Content-Type: application/json
Authorization: Bearer <access_token>
```

**Request Body**
```json
{
  "current_password": "OldPass123!",
  "new_password": "NewPass123!",
  "confirm_password": "NewPass123!"
}
```

**Validation Rules**
| Field | Type | Rules |
|-------|------|-------|
| current_password | string | Required |
| new_password | string | Min 8 chars, 1 uppercase, 1 number, 1 special |
| confirm_password | string | Must match new_password |

**Success Response (200)**
```json
{
  "success": true,
  "message": "Password changed successfully",
  "data": {},
  "timestamp": "2026-05-16T10:30:00Z"
}
```

**Error Response (400)**
```json
{
  "success": false,
  "message": "Incorrect current password",
  "errors": [{"field": "current_password", "message": "Current password is incorrect"}],
  "timestamp": "2026-05-16T10:30:00Z"
}
```

---

# 3. USER MANAGEMENT API

## Endpoints

### GET /api/v1/users/me

Get detailed user information including preferences.

| Attribute | Value |
|-----------|-------|
| Endpoint | `/api/v1/users/me` |
| Method | GET |
| Auth Required | Yes |

**Success Response (200)**
```json
{
  "success": true,
  "message": "User data retrieved",
  "data": {
    "user_id": "usr_abc123",
    "email": "trader@example.com",
    "full_name": "Rajesh Kumar",
    "phone": "+919876543210",
    "role": "trader",
    "broker": {
      "name": "zerodha",
      "connected": true,
      "account_id": "AB1234"
    },
    "preferences": {
      "default_product": "MIS",
      "default_order_type": "LIMIT",
      "default_exchange": "NSE",
      "theme": "dark"
    },
    "limits": {
      "max_daily_loss": 10000,
      "max_positions": 10,
      "max_orders_per_minute": 10
    },
    "created_at": "2026-01-01T00:00:00Z"
  },
  "timestamp": "2026-05-16T10:30:00Z"
}
```

### PUT /api/v1/users/me

Update user preferences.

| Attribute | Value |
|-----------|-------|
| Endpoint | `/api/v1/users/me` |
| Method | PUT |
| Auth Required | Yes |

**Request Body**
```json
{
  "preferences": {
    "default_product": "CNC",
    "default_order_type": "MARKET",
    "theme": "light"
  }
}
```

---

# 4. WATCHLIST API

## Overview

Watchlists allow users to track multiple stocks. Each watchlist can contain up to 100 symbols.

## Endpoints

### GET /api/v1/watchlists

Get all watchlists for the user.

| Attribute | Value |
|-----------|-------|
| Endpoint | `/api/v1/watchlists` |
| Method | GET |
| Auth Required | Yes |

**Query Parameters**
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| page | int | Page number | 1 |
| limit | int | Items per page | 20 |

**Request Headers**
```
Authorization: Bearer <access_token>
```

**Success Response (200)**
```json
{
  "success": true,
  "message": "Watchlists retrieved successfully",
  "data": [
    {
      "watchlist_id": "wl_abc123",
      "name": "Nifty 50",
      "description": "Top 50 NSE stocks",
      "symbols": ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"],
      "created_at": "2026-01-01T00:00:00Z",
      "updated_at": "2026-05-15T00:00:00Z",
      "is_default": true
    },
    {
      "watchlist_id": "wl_def456",
      "name": "F&O Stocks",
      "description": "Derivative stocks",
      "symbols": ["BANKNIFTY", "NIFTY", "RELIANCE"],
      "created_at": "2026-02-01T00:00:00Z",
      "updated_at": "2026-05-10T00:00:00Z",
      "is_default": false
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 2,
    "pages": 1
  },
  "timestamp": "2026-05-16T10:30:00Z"
}
```

---

### POST /api/v1/watchlists

Create a new watchlist.

| Attribute | Value |
|-----------|-------|
| Endpoint | `/api/v1/watchlists` |
| Method | POST |
| Auth Required | Yes |
| Rate Limit | 20 requests/minute |

**Request Headers**
```
Content-Type: application/json
Authorization: Bearer <access_token>
```

**Request Body**
```json
{
  "name": "My Watchlist",
  "description": "Custom stocks to watch",
  "symbols": ["RELIANCE", "TCS", "INFY"]
}
```

**Validation Rules**
| Field | Type | Rules |
|-------|------|-------|
| name | string | Required, 1-50 chars, unique |
| description | string | Optional, max 200 chars |
| symbols | array | Optional, array of strings, max 100 |

**Success Response (201)**
```json
{
  "success": true,
  "message": "Watchlist created successfully",
  "data": {
    "watchlist_id": "wl_new123",
    "name": "My Watchlist",
    "description": "Custom stocks to watch",
    "symbols": ["RELIANCE", "TCS", "INFY"],
    "created_at": "2026-05-16T10:30:00Z"
  },
  "timestamp": "2026-05-16T10:30:00Z"
}
```

**Error Response (400)**
```json
{
  "success": false,
  "message": "Validation failed",
  "errors": [
    {"field": "name", "message": "Watchlist name already exists"}
  ],
  "timestamp": "2026-05-16T10:30:00Z"
}
```

---

### PUT /api/v1/watchlists/:id

Update watchlist details.

| Attribute | Value |
|-----------|-------|
| Endpoint | `/api/v1/watchlists/:id` |
| Method | PUT |
| Auth Required | Yes |

**Path Parameters**
| Parameter | Type | Description |
|-----------|------|-------------|
| id | string | Watchlist ID |

**Request Body**
```json
{
  "name": "Updated Name",
  "description": "Updated description"
}
```

**Success Response (200)**
```json
{
  "success": true,
  "message": "Watchlist updated successfully",
  "data": {
    "watchlist_id": "wl_abc123",
    "name": "Updated Name",
    "updated_at": "2026-05-16T10:30:00Z"
  },
  "timestamp": "2026-05-16T10:30:00Z"
}
```

**Error Response (404)**
```json
{
  "success": false,
  "message": "Watchlist not found",
  "errors": [],
  "timestamp": "2026-05-16T10:30:00Z"
}
```

---

### DELETE /api/v1/watchlists/:id

Delete a watchlist.

| Attribute | Value |
|-----------|-------|
| Endpoint | `/api/v1/watchlists/:id` |
| Method | DELETE |
| Auth Required | Yes |

**Success Response (200)**
```json
{
  "success": true,
  "message": "Watchlist deleted successfully",
  "data": {},
  "timestamp": "2026-05-16T10:30:00Z"
}
```

---

### POST /api/v1/watchlists/:id/stocks

Add stocks to a watchlist.

| Attribute | Value |
|-----------|-------|
| Endpoint | `/api/v1/watchlists/:id/stocks` |
| Method | POST |
| Auth Required | Yes |

**Request Body**
```json
{
  "symbols": ["HDFCBANK", "ICICIBANK", "SBIN"]
}
```

**Validation Rules**
| Field | Type | Rules |
|-------|------|-------|
| symbols | array | Required, array of valid stock symbols, max 100 |

**Success Response (200)**
```json
{
  "success": true,
  "message": "Stocks added to watchlist",
  "data": {
    "watchlist_id": "wl_abc123",
    "symbols": ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN"],
    "updated_at": "2026-05-16T10:30:00Z"
  },
  "timestamp": "2026-05-16T10:30:00Z"
}
```

---

### DELETE /api/v1/watchlists/:id/stocks/:symbol

Remove a stock from watchlist.

| Attribute | Value |
|-----------|-------|
| Endpoint | `/api/v1/watchlists/:id/stocks/:symbol` |
| Method | DELETE |
| Auth Required | Yes |

**Path Parameters**
| Parameter | Type | Description |
|-----------|------|-------------|
| id | string | Watchlist ID |
| symbol | string | Stock symbol to remove |

**Success Response (200)**
```json
{
  "success": true,
  "message": "Stock removed from watchlist",
  "data": {
    "watchlist_id": "wl_abc123",
    "symbols": ["RELIANCE", "TCS", "INFY"],
    "updated_at": "2026-05-16T10:30:00Z"
  },
  "timestamp": "2026-05-16T10:30:00Z"
}
```

---

# 5. ORDERS API

## Overview

Support for MARKET, LIMIT, SL (Stop Loss), and SL-M (Stop Loss Market) orders with MIS and CNC product types.

## Endpoints

### GET /api/v1/orders

Get all orders with filters.

| Attribute | Value |
|-----------|-------|
| Endpoint | `/api/v1/orders` |
| Method | GET |
| Auth Required | Yes |

**Query Parameters**
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| status | string | PENDING, EXECUTED, CANCELLED, REJECTED | all |
| product | string | MIS, CNC | all |
| from_date | string | Start date (YYYY-MM-DD) | null |
| to_date | string | End date (YYYY-MM-DD) | null |
| symbol | string | Filter by symbol | null |
| page | int | Page number | 1 |
| limit | int | Items per page | 50 |

**Request Headers**
```
Authorization: Bearer <access_token>
```

**Success Response (200)**
```json
{
  "success": true,
  "message": "Orders retrieved successfully",
  "data": [
    {
      "order_id": "ord_abc123",
      "order_type": "LIMIT",
      "product": "MIS",
      "symbol": "RELIANCE",
      "exchange": "NSE",
      "side": "BUY",
      "quantity": 100,
      "price": 2850.50,
      "trigger_price": null,
      "status": "EXECUTED",
      "filled_quantity": 100,
      "average_price": 2850.50,
      "order_timestamp": "2026-05-16T09:30:00Z",
      "exchange_order_id": "EX123456789",
      "filled_timestamp": "2026-05-16T09:30:05Z"
    },
    {
      "order_id": "ord_def456",
      "order_type": "SL",
      "product": "MIS",
      "symbol": "TCS",
      "exchange": "NSE",
      "side": "SELL",
      "quantity": 50,
      "price": 4200.00,
      "trigger_price": 4180.00,
      "status": "PENDING",
      "filled_quantity": 0,
      "average_price": null,
      "order_timestamp": "2026-05-16T10:00:00Z",
      "exchange_order_id": null,
      "filled_timestamp": null
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 150,
    "pages": 3
  },
  "timestamp": "2026-05-16T10:30:00Z"
}
```

---

### POST /api/v1/orders

Place a new order.

| Attribute | Value |
|-----------|-------|
| Endpoint | `/api/v1/orders` |
| Method | POST |
| Auth Required | Yes |
| Rate Limit | 30 requests/minute |

**Request Headers**
```
Content-Type: application/json
Authorization: Bearer <access_token>
```

**Request Body**
```json
{
  "order_type": "LIMIT",
  "product": "MIS",
  "symbol": "RELIANCE",
  "exchange": "NSE",
  "side": "BUY",
  "quantity": 100,
  "price": 2850.50,
  "trigger_price": null,
  "disclosed_quantity": 0,
  "validity": "DAY",
  "after_market_order": false
}
```

**Validation Rules**
| Field | Type | Rules | Required |
|-------|------|-------|----------|
| order_type | string | Required, enum: MARKET, LIMIT, SL, SL-M | Yes |
| product | string | Required, enum: MIS, CNC, CO | Yes |
| symbol | string | Required, valid stock symbol | Yes |
| exchange | string | Required, enum: NSE, BSE | Yes |
| side | string | Required, enum: BUY, SELL | Yes |
| quantity | int | Required, positive integer, min lot size | Yes |
| price | decimal | Required for LIMIT/SL, nullable for MARKET | Conditional |
| trigger_price | decimal | Required for SL/SL-M, nullable otherwise | Conditional |
| validity | string | Optional, enum: DAY, IOC, GTD, GTC | No |
| disclosed_quantity | int | Optional, for iceberg orders | No |

**Success Response (201)**
```json
{
  "success": true,
  "message": "Order placed successfully",
  "data": {
    "order_id": "ord_new123",
    "order_type": "LIMIT",
    "product": "MIS",
    "symbol": "RELIANCE",
    "exchange": "NSE",
    "side": "BUY",
    "quantity": 100,
    "price": 2850.50,
    "status": "PENDING",
    "order_timestamp": "2026-05-16T10:30:00Z"
  },
  "timestamp": "2026-05-16T10:30:00Z"
}
```

**Error Response (400)**
```json
{
  "success": false,
  "message": "Order validation failed",
  "errors": [
    {"field": "price", "message": "Price is required for LIMIT order"}
  ],
  "timestamp": "2026-05-16T10:30:00Z"
}
```

**Error Response (422)**
```json
{
  "success": false,
  "message": "Insufficient funds",
  "errors": [],
  "timestamp": "2026-05-16T10:30:00Z"
}
```

---

### GET /api/v1/orders/:id

Get order details by ID.

| Attribute | Value |
|-----------|-------|
| Endpoint | `/api/v1/orders/:id` |
| Method | GET |
| Auth Required | Yes |

**Path Parameters**
| Parameter | Type | Description |
|-----------|------|-------------|
| id | string | Order ID |

**Success Response (200)**
```json
{
  "success": true,
  "message": "Order details retrieved",
  "data": {
    "order_id": "ord_abc123",
    "order_type": "LIMIT",
    "product": "MIS",
    "symbol": "RELIANCE",
    "exchange": "NSE",
    "side": "BUY",
    "quantity": 100,
    "price": 2850.50,
    "trigger_price": null,
    "status": "EXECUTED",
    "filled_quantity": 100,
    "average_price": 2850.50,
    "pending_quantity": 0,
    "order_timestamp": "2026-05-16T09:30:00Z",
    "exchange_order_id": "EX123456789",
    "filled_timestamp": "2026-05-16T09:30:05Z",
    "cancelled_timestamp": null,
    "rejected_reason": null,
    "tags": ["momentum", "ai-signal"]
  },
  "timestamp": "2026-05-16T10:30:00Z"
}
```

---

### PUT /api/v1/orders/:id/cancel

Cancel a pending order.

| Attribute | Value |
|-----------|-------|
| Endpoint | `/api/v1/orders/:id/cancel` |
| Method | PUT |
| Auth Required | Yes |

**Path Parameters**
| Parameter | Type | Description |
|-----------|------|-------------|
| id | string | Order ID |

**Success Response (200)**
```json
{
  "success": true,
  "message": "Order cancelled successfully",
  "data": {
    "order_id": "ord_abc123",
    "status": "CANCELLED",
    "cancelled_timestamp": "2026-05-16T10:35:00Z"
  },
  "timestamp": "2026-05-16T10:35:00Z"
}
```

**Error Response (400)**
```json
{
  "success": false,
  "message": "Order cannot be cancelled",
  "errors": [{"message": "Only PENDING orders can be cancelled"}],
  "timestamp": "2026-05-16T10:35:00Z"
}
```

---

### PUT /api/v1/orders/:id/modify

Modify an existing order.

| Attribute | Value |
|-----------|-------|
| Endpoint | `/api/v1/orders/:id/modify` |
| Method | PUT |
| Auth Required | Yes |

**Request Body**
```json
{
  "price": 2860.00,
  "quantity": 150,
  "trigger_price": null
}
```

**Success Response (200)**
```json
{
  "success": true,
  "message": "Order modified successfully",
  "data": {
    "order_id": "ord_abc123",
    "status": "MODIFIED",
    "modified_fields": {
      "price": 2850.50,
      "modified_price": 2860.00,
      "quantity": 100,
      "modified_quantity": 150
    },
    "modified_timestamp": "2026-05-16T10:35:00Z"
  },
  "timestamp": "2026-05-16T10:35:00Z"
}
```

---

### GET /api/v1/orders/history

Get order history with date range.

| Attribute | Value |
|-----------|-------|
| Endpoint | `/api/v1/orders/history` |
| Method | GET |
| Auth Required | Yes |

**Query Parameters**
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| from_date | string | Start date (YYYY-MM-DD) | 30 days ago |
| to_date | string | End date (YYYY-MM-DD) | today |
| page | int | Page number | 1 |
| limit | int | Items per page | 50 |

**Success Response (200)**
```json
{
  "success": true,
  "message": "Order history retrieved",
  "data": [
    {
      "order_id": "ord_abc123",
      "order_type": "MARKET",
      "product": "CNC",
      "symbol": "TCS",
      "exchange": "NSE",
      "side": "BUY",
      "quantity": 10,
      "status": "EXECUTED",
      "average_price": 4205.00,
      "order_timestamp": "2026-05-15T14:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 500,
    "pages": 10
  },
  "summary": {
    "total_orders": 500,
    "executed": 450,
    "cancelled": 30,
    "rejected": 20,
    "total_volume": 15000000
  },
  "timestamp": "2026-05-16T10:30:00Z"
}
```

---

# 6. POSITIONS API

## Endpoints

### GET /api/v1/positions

Get all positions (open and closed).

| Attribute | Value |
|-----------|-------|
| Endpoint | `/api/v1/positions` |
| Method | GET |
| Auth Required | Yes |

**Query Parameters**
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| status | string | OPEN, CLOSED, ALL | ALL |
| product | string | MIS, CNC, ALL | ALL |
| page | int | Page number | 1 |
| limit | int | Items per page | 50 |

**Success Response (200)**
```json
{
  "success": true,
  "message": "Positions retrieved successfully",
  "data": [
    {
      "position_id": "pos_abc123",
      "symbol": "RELIANCE",
      "exchange": "NSE",
      "product": "MIS",
      "side": "BUY",
      "quantity": 100,
      "avg_price": 2850.50,
      "current_price": 2875.00,
      "last_updated": "2026-05-16T10:25:00Z",
      "pnl": 2450.00,
      "pnl_percent": 0.86,
      "status": "OPEN",
      "opened_at": "2026-05-16T09:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 10,
    "pages": 1
  },
  "timestamp": "2026-05-16T10:30:00Z"
}
```

---

### GET /api/v1/positions/open

Get only open positions.

| Attribute | Value |
|-----------|-------|
| Endpoint | `/api/v1/positions/open` |
| Method | GET |
| Auth Required | Yes |

**Success Response (200)**
```json
{
  "success": true,
  "message": "Open positions retrieved",
  "data": [
    {
      "position_id": "pos_abc123",
      "symbol": "RELIANCE",
      "exchange": "NSE",
      "product": "MIS",
      "side": "BUY",
      "quantity": 100,
      "avg_price": 2850.50,
      "current_price": 2875.00,
      "last_updated": "2026-05-16T10:25:00Z",
      "pnl": 2450.00,
      "pnl_percent": 0.86,
      "day_pnl": 1500.00,
      "unrealized_pnl": 2450.00,
      "m2m": 1500.00,
      "opened_at": "2026-05-16T09:30:00Z"
    }
  ],
  "summary": {
    "total_positions": 3,
    "total_value": 8500000,
    "total_pnl": 5000.00,
    "day_pnl": 3500.00
  },
  "timestamp": "2026-05-16T10:30:00Z"
}
```

---

### GET /api/v1/positions/history

Get position history.

| Attribute | Value |
|-----------|-------|
| Endpoint | `/api/v1/positions/history` |
| Method | GET |
| Auth Required | Yes |

**Query Parameters**
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| from_date | string | Start date | 30 days ago |
| to_date | string | End date | today |
| page | int | Page number | 1 |
| limit | int | Items per page | 50 |

**Success Response (200)**
```json
{
  "success": true,
  "message": "Position history retrieved",
  "data": [
    {
      "position_id": "pos_closed123",
      "symbol": "INFY",
      "exchange": "NSE",
      "product": "MIS",
      "side": "BUY",
      "quantity": 200,
      "entry_price": 1450.00,
      "exit_price": 1475.00,
      "pnl": 5000.00,
      "pnl_percent": 1.72,
      "status": "CLOSED",
      "opened_at": "2026-05-14T10:00:00Z",
      "closed_at": "2026-05-15T15:30:00Z",
      "exit_reason": "TARGET_HIT",
      "holding_period": 1
    }
  ],
  "summary": {
    "total_closed": 45,
    "winning_positions": 30,
    "losing_positions": 15,
    "total_pnl": 125000.00,
    "win_rate": 66.67
  },
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 45,
    "pages": 1
  },
  "timestamp": "2026-05-16T10:30:00Z"
}
```

---

### PUT /api/v1/positions/:id/exit

Exit an open position.

| Attribute | Value |
|-----------|-------|
| Endpoint | `/api/v1/positions/:id/exit` |
| Method | PUT |
| Auth Required | Yes |

**Path Parameters**
| Parameter | Type | Description |
|-----------|------|-------------|
| id | string | Position ID |

**Request Body**
```json
{
  "order_type": "MARKET",
  "limit_price": null
}
```

**Success Response (200)**
```json
{
  "success": true,
  "message": "Position exited successfully",
  "data": {
    "position_id": "pos_abc123",
    "status": "CLOSED",
    "exit_price": 2875.00,
    "quantity": 100,
    "pnl": 2450.00,
    "pnl_percent": 0.86,
    "closed_at": "2026-05-16T10:30:00Z",
    "exit_order_id": "ord_exit123"
  },
  "timestamp": "2026-05-16T10:30:00Z"
}
```

---

# 7. TRADES API

## Endpoints

### GET /api/v1/trades

Get trade history.

| Attribute | Value |
|-----------|-------|
| Endpoint | `/api/v1/trades` |
| Method | GET |
| Auth Required | Yes |

**Query Parameters**
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| from_date | string | Start date | 30 days ago |
| to_date | string | End date | today |
| symbol | string | Filter by symbol | null |
| order_id | string | Filter by order | null |
| page | int | Page number | 1 |
| limit | int | Items per page | 50 |

**Success Response (200)**
```json
{
  "success": true,
  "message": "Trades retrieved successfully",
  "data": [
    {
      "trade_id": "trd_abc123",
      "order_id": "ord_abc123",
      "symbol": "RELIANCE",
      "exchange": "NSE",
      "side": "BUY",
      "quantity": 100,
      "price": 2850.50,
      "order_type": "LIMIT",
      "product": "MIS",
      "trade_timestamp": "2026-05-16T09:30:05Z",
      "exchange_trade_id": "EXTR123456"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 500,
    "pages": 10
  },
  "timestamp": "2026-05-16T10:30:00Z"
}
```

---

### GET /api/v1/trades/:id

Get trade details.

| Attribute | Value |
|-----------|-------|
| Endpoint | `/api/v1/trades/:id` |
| Method | GET |
| Auth Required | Yes |

**Path Parameters**
| Parameter | Type | Description |
|-----------|------|-------------|
| id | string | Trade ID |

**Success Response (200)**
```json
{
  "success": true,
  "message": "Trade details retrieved",
  "data": {
    "trade_id": "trd_abc123",
    "order_id": "ord_abc123",
    "symbol": "RELIANCE",
    "exchange": "NSE",
    "side": "BUY",
    "quantity": 100,
    "price": 2850.50,
    "value": 285050.00,
    "order_type": "LIMIT",
    "product": "MIS",
    "brokerage": 20.00,
    "gst": 3.60,
    "stamp_duty": 0.50,
    "sebi_charges": 1.00,
    "total_charges": 25.10,
    "net_value": 285075.10,
    "trade_timestamp": "2026-05-16T09:30:05Z",
    "exchange_trade_id": "EXTR123456"
  },
  "timestamp": "2026-05-16T10:30:00Z"
}
```

---

### GET /api/v1/trades/daily

Get daily trade summary.

| Attribute | Value |
|-----------|-------|
| Endpoint | `/api/v1/trades/daily` |
| Method | GET |
| Auth Required | Yes |

**Query Parameters**
| Parameter | Type | Description |
|-----------|------|-------------|
| date | string | Date (YYYY-MM-DD), defaults to today |

**Success Response (200)**
```json
{
  "success": true,
  "message": "Daily trade summary",
  "data": {
    "date": "2026-05-16",
    "total_trades": 25,
    "buy_trades": 15,
    "sell_trades": 10,
    "total_volume": 15000000,
    "total_brokerage": 500.00,
    "trades": []
  },
  "timestamp": "2026-05-16T10:30:00Z"
}
```

---

# 8. FUNDS API

## Endpoints

### GET /api/v1/funds

Get account balance and margin details.

| Attribute | Value |
|-----------|-------|
| Endpoint | `/api/v1/funds` |
| Method | GET |
| Auth Required | Yes |

**Success Response (200)**
```json
{
  "success": true,
  "message": "Funds information retrieved",
  "data": {
    "account_id": "acc_abc123",
    "broker": "zerodha",
    "balance": {
      "available_cash": 500000.00,
      "used_margin": 150000.00,
      "total_balance": 650000.00,
      "currency": "INR"
    },
    "margin": {
      "available_margin": 500000.00,
      "used_margin": 150000.00,
      "span_margin": 100000.00,
      "exposure_margin": 50000.00,
      "total_margin_used": 150000.00
    },
    "limits": {
      "daily_buy_power": 500000.00,
      "daily_sell_power": 650000.00
    },
    "last_updated": "2026-05-16T10:30:00Z"
  },
  "timestamp": "2026-05-16T10:30:00Z"
}
```

---

### GET /api/v1/funds/ledger

Get transaction ledger.

| Attribute | Value |
|-----------|-------|
| Endpoint | `/api/v1/funds/ledger` |
| Method | GET |
| Auth Required | Yes |

**Query Parameters**
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| from_date | string | Start date | 30 days ago |
| to_date | string | End date | today |
| transaction_type | string | DEBIT, CREDIT, ALL | ALL |
| page | int | Page number | 1 |
| limit | int | Items per page | 50 |

**Success Response (200)**
```json
{
  "success": true,
  "message": "Ledger retrieved successfully",
  "data": [
    {
      "transaction_id": "txn_abc123",
      "type": "CREDIT",
      "amount": 100000.00,
      "balance_after": 600000.00,
      "description": "Funds added via UPI",
      "reference": "UPI/123456789",
      "timestamp": "2026-05-15T10:00:00Z"
    },
    {
      "transaction_id": "txn_def456",
      "type": "DEBIT",
      "amount": 285000.00,
      "balance_after": 315000.00,
      "description": "Order placed: RELIANCE",
      "reference": "ord_abc123",
      "timestamp": "2026-05-16T09:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 100,
    "pages": 2
  },
  "timestamp": "2026-05-16T10:30:00Z"
}
```

---

### POST /api/v1/funds/add

Add funds to trading account.

| Attribute | Value |
|-----------|-------|
| Endpoint | `/api/v1/funds/add` |
| Method | POST |
| Auth Required | Yes |

**Request Body**
```json
{
  "amount": 50000.00,
  "payment_method": "UPI",
  "reference": "UPI123456"
}
```

**Validation Rules**
| Field | Type | Rules |
|-------|------|-------|
| amount | decimal | Required, min 100, max 10000000 |
| payment_method | string | Required, enum: UPI, BANK_TRANSFER, PAYTM |
| reference | string | Optional |

**Success Response (200)**
```json
{
  "success": true,
  "message": "Funds added successfully",
  "data": {
    "transaction_id": "txn_new123",
    "amount": 50000.00,
    "status": "PENDING",
    "created_at": "2026-05-16T10:30:00Z"
  },
  "timestamp": "2026-05-16T10:30:00Z"
}
```

---

### GET /api/v1/funds/holdings

Get holdings (CNC positions).

| Attribute | Value |
|-----------|-------|
| Endpoint | `/api/v1/funds/holdings` |
| Method | GET |
| Auth Required | Yes |

**Success Response (200)**
```json
{
  "success": true,
  "message": "Holdings retrieved successfully",
  "data": [
    {
      "symbol": "RELIANCE",
      "quantity": 100,
      "avg_buy_price": 2500.00,
      "ltp": 2875.00,
      "current_value": 287500.00,
      "pnl": 37500.00,
      "pnl_percent": 15.00,
      "day_change": 2500.00,
      "day_change_percent": 0.88,
      "exchange": "NSE"
    }
  ],
  "summary": {
    "total_invested": 250000.00,
    "total_current_value": 287500.00,
    "total_pnl": 37500.00,
    "total_pnl_percent": 15.00
  },
  "timestamp": "2026-05-16T10:30:00Z"
}
```

---

# 9. STRATEGIES API

## Endpoints

### GET /api/v1/strategies

Get all trading strategies.

| Attribute | Value |
|-----------|-------|
| Endpoint | `/api/v1/strategies` |
| Method | GET |
| Auth Required | Yes |

**Query Parameters**
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| mode | string | PAPER, LIVE, ALL | ALL |
| status | string | ACTIVE, PAUSED, ALL | ALL |
| symbol | string | Filter by symbol | null |
| page | int | Page number | 1 |
| limit | int | Items per page | 20 |

**Success Response (200)**
```json
{
  "success": true,
  "message": "Strategies retrieved successfully",
  "data": [
    {
      "strategy_id": "strat_abc123",
      "name": "RSI Momentum",
      "description": "Buy when RSI < 30, sell when RSI > 70",
      "symbol": "RELIANCE",
      "exchange": "NSE",
      "timeframe": "5MIN",
      "mode": "PAPER",
      "status": "ACTIVE",
      "parameters": {
        "rsi_period": 14,
        "oversold": 30,
        "overbought": 70
      },
      "risk_settings": {
        "max_position_size": 10000,
        "stop_loss_percent": 1.0,
        "target_percent": 2.0,
        "max_daily_loss": 5000
      },
      "statistics": {
        "total_trades": 50,
        "winning_trades": 35,
        "losing_trades": 15,
        "win_rate": 70.00,
        "avg_pnl": 250.00,
        "total_pnl": 12500.00
      },
      "created_at": "2026-01-01T00:00:00Z",
      "updated_at": "2026-05-15T00:00:00Z",
      "last_run": "2026-05-16T10:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 5,
    "pages": 1
  },
  "timestamp": "2026-05-16T10:30:00Z"
}
```

---

### POST /api/v1/strategies

Create a new strategy.

| Attribute | Value |
|-----------|-------|
| Endpoint | `/api/v1/strategies` |
| Method | POST |
| Auth Required | Yes |
| Rate Limit | 10 requests/minute |

**Request Headers**
```
Content-Type: application/json
Authorization: Bearer <access_token>
```

**Request Body**
```json
{
  "name": "RSI Momentum Strategy",
  "description": "Buy when RSI < 30, sell when RSI > 70",
  "symbol": "RELIANCE",
  "exchange": "NSE",
  "timeframe": "5MIN",
  "mode": "PAPER",
  "parameters": {
    "indicator": "RSI",
    "rsi_period": 14,
    "oversold": 30,
    "overbought": 70,
    "entry_condition": "CROSSES_BELOW",
    "exit_condition": "CROSSES_ABOVE"
  },
  "risk_settings": {
    "max_position_size": 10000,
    "stop_loss_percent": 1.0,
    "target_percent": 2.0,
    "max_daily_loss": 5000,
    "trailing_stop_enabled": true,
    "trailing_stop_percent": 0.5
  }
}
```

**Validation Rules**
| Field | Type | Rules |
|-------|------|-------|
| name | string | Required, 1-100 chars, unique |
| symbol | string | Required, valid stock symbol |
| exchange | string | Required, enum: NSE, BSE |
| timeframe | string | Required, enum: 1MIN, 5MIN, 15MIN, 30MIN, 1HOUR, 1DAY |
| parameters | object | Required, strategy-specific parameters |

**Success Response (201)**
```json
{
  "success": true,
  "message": "Strategy created successfully",
  "data": {
    "strategy_id": "strat_new123",
    "name": "RSI Momentum Strategy",
    "status": "PAUSED",
    "created_at": "2026-05-16T10:30:00Z"
  },
  "timestamp": "2026-05-16T10:30:00Z"
}
```

---

### GET /api/v1/strategies/:id

Get strategy details.

| Attribute | Value |
|-----------|-------|
| Endpoint | `/api/v1/strategies/:id` |
| Method | GET |
| Auth Required | Yes |

**Success Response (200)**
```json
{
  "success": true,
  "message": "Strategy details retrieved",
  "data": {
    "strategy_id": "strat_abc123",
    "name": "RSI Momentum",
    "description": "Buy when RSI < 30, sell when RSI > 70",
    "symbol": "RELIANCE",
    "exchange": "NSE",
    "timeframe": "5MIN",
    "mode": "PAPER",
    "status": "ACTIVE",
    "parameters": {
      "indicator": "RSI",
      "rsi_period": 14,
      "oversold": 30,
      "overbought": 70
    },
    "risk_settings": {
      "max_position_size": 10000,
      "stop_loss_percent": 1.0,
      "target_percent": 2.0
    },
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-05-15T00:00:00Z"
  },
  "timestamp": "2026-05-16T10:30:00Z"
}
```

---

### PUT /api/v1/strategies/:id

Update strategy.

| Attribute | Value |
|-----------|-------|
| Endpoint | `/api/v1/strategies/:id` |
| Method | PUT |
| Auth Required | Yes |

**Request Body**
```json
{
  "name": "Updated Strategy Name",
  "parameters": {
    "rsi_period": 21,
    "oversold": 25,
    "overbought": 75
  },
  "risk_settings": {
    "max_position_size": 15000,
    "stop_loss_percent": 1.5
  }
}
```

**Success Response (200)**
```json
{
  "success": true,
  "message": "Strategy updated successfully",
  "data": {
    "strategy_id": "strat_abc123",
    "updated_at": "2026-05-16T10:30:00Z"
  },
  "timestamp": "2026-05-16T10:30:00Z"
}
```

---

### DELETE /api/v1/strategies/:id

Delete a strategy.

| Attribute | Value |
|-----------|-------|
| Endpoint | `/api/v1/strategies/:id` |
| Method | DELETE |
| Auth Required | Yes |

**Success Response (200)**
```json
{
  "success": true,
  "message": "Strategy deleted successfully",
  "data": {},
  "timestamp": "2026-05-16T10:30:00Z"
}
```

---

### POST /api/v1/strategies/:id/start

Start a strategy (begin auto-trading).

| Attribute | Value |
|-----------|-------|
| Endpoint | `/api/v1/strategies/:id/start` |
| Method | POST |
| Auth Required | Yes |

**Request Body**
```json
{
  "mode": "PAPER"
}
```

**Validation Rules**
| Field | Type | Rules |
|-------|------|-------|
| mode | string | Required, enum: PAPER, LIVE |

**Success Response (200)**
```json
{
  "success": true,
  "message": "Strategy started successfully",
  "data": {
    "strategy_id": "strat_abc123",
    "status": "ACTIVE",
    "mode": "PAPER",
    "started_at": "2026-05-16T10:30:00Z"
  },
  "timestamp": "2026-05-16T10:30:00Z"
}
```

---

### POST /api/v1/strategies/:id/stop

Stop a strategy.

| Attribute | Value |
|-----------|-------|
| Endpoint | `/api/v1/strategies/:id/stop` |
| Method | POST |
| Auth Required | Yes |

**Success Response (200)**
```json
{
  "success": true,
  "message": "Strategy stopped successfully",
  "data": {
    "strategy_id": "strat_abc123",
    "status": "PAUSED",
    "stopped_at": "2026-05-16T10:30:00Z"
  },
  "timestamp": "2026-05-16T10:30:00Z"
}
```

---

### GET /api/v1/strategies/:id/signals

Get historical signals for a strategy.

| Attribute | Value |
|-----------|-------|
| Endpoint | `/api/v1/strategies/:id/signals` |
| Method | GET |
| Auth Required | Yes |

**Query Parameters**
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| from_date | string | Start date | 7 days ago |
| to_date | string | End date | today |
| page | int | Page number | 1 |
| limit | int | Items per page | 50 |

**Success Response (200)**
```json
{
  "success": true,
  "message": "Signals retrieved successfully",
  "data": [
    {
      "signal_id": "sig_abc123",
      "strategy_id": "strat_abc123",
      "symbol": "RELIANCE",
      "action": "BUY",
      "price": 2850.50,
      "quantity": 100,
      "confidence": 85.5,
      "reasoning": "RSI crossed below 30 (oversold)",
      "timestamp": "2026-05-16T09:30:00Z",
      "executed": true,
      "order_id": "ord_abc123"
    }
  ],
  "timestamp": "2026-05-16T10:30:00Z"
}
```

---

# 10. AI SIGNALS API

## Endpoints

### GET /api/v1/signals

Get AI-generated trading signals.

| Attribute | Value |
|-----------|-------|
| Endpoint | `/api/v1/signals` |
| Method | GET |
| Auth Required | Yes |

**Query Parameters**
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| symbol | string | Filter by symbol | null |
| action | string | BUY, SELL, ALL | ALL |
| from_date | string | Start date | 7 days ago |
| to_date | string | End date | today |
| page | int | Page number | 1 |
| limit | int | Items per page | 20 |

**Request Headers**
```
Authorization: Bearer <access_token>
```

**Success Response (200)**
```json
{
  "success": true,
  "message": "Signals retrieved successfully",
  "data": [
    {
      "signal_id": "sig_abc123",
      "symbol": "RELIANCE",
      "exchange": "NSE",
      "action": "BUY",
      "confidence": 85.50,
      "target_price": 2900.00,
      "stop_loss": 2820.00,
      "entry_range": {
        "min": 2850.00,
        "max": 2860.00
      },
      "reasoning": "RSI at 28 (oversold), MACD showing bullish divergence, price approaching support at 2840",
      "indicators": {
        "rsi": 28.5,
        "macd": "bullish",
        "sma_20": 2875.00,
        "sma_50": 2850.00,
        "volume_ratio": 1.5
      },
      "timeframe": "1HOUR",
      "generated_at": "2026-05-16T10:00:00Z",
      "expires_at": "2026-05-16T11:00:00Z",
      "status": "ACTIVE"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 50,
    "pages": 3
  },
  "timestamp": "2026-05-16T10:30:00Z"
}
```

---

### GET /api/v1/signals/live

Get live active signals (currently actionable).

| Attribute | Value |
|-----------|-------|
| Endpoint | `/api/v1/signals/live` |
| Method | GET |
| Auth Required | Yes |

**Success Response (200)**
```json
{
  "success": true,
  "message": "Live signals retrieved",
  "data": [
    {
      "signal_id": "sig_abc123",
      "symbol": "RELIANCE",
      "exchange": "NSE",
      "action": "BUY",
      "confidence": 85.50,
      "target_price": 2900.00,
      "stop_loss": 2820.00,
      "entry_range": {
        "min": 2850.00,
        "max": 2860.00
      },
      "reasoning": "RSI at 28 (oversold), MACD showing bullish divergence",
      "timeframe": "1HOUR",
      "generated_at": "2026-05-16T10:00:00Z",
      "time_remaining_minutes": 45
    }
  ],
  "summary": {
    "total_signals": 5,
    "buy_signals": 3,
    "sell_signals": 2,
    "avg_confidence": 78.5
  },
  "timestamp": "2026-05-16T10:30:00Z"
}
```

---

### POST /api/v1/signals/generate

Generate new AI signals for specified symbols.

| Attribute | Value |
|-----------|-------|
| Endpoint | `/api/v1/signals/generate` |
| Method | POST |
| Auth Required | Yes |
| Rate Limit | 5 requests/minute |

**Request Headers**
```
Content-Type: application/json
Authorization: Bearer <access_token>
```

**Request Body**
```json
{
  "symbols": ["RELIANCE", "TCS", "INFY"],
  "timeframe": "1HOUR",
  "analysis_type": "FULL"
}
```

**Validation Rules**
| Field | Type | Rules |
|-------|------|-------|
| symbols | array | Required, 1-10 symbols |
| timeframe | string | Optional, enum: 15MIN, 30MIN, 1HOUR, 4HOUR, 1DAY |
| analysis_type | string | Optional, enum: QUICK, FULL |

**Success Response (200)**
```json
{
  "success": true,
  "message": "Signals generation started",
  "data": {
    "job_id": "job_abc123",
    "status": "PROCESSING",
    "symbols": ["RELIANCE", "TCS", "INFY"],
    "estimated_completion": "2026-05-16T10:35:00Z"
  },
  "timestamp": "2026-05-16T10:30:00Z"
}
```

**Success Response (200) - Immediate Results**
```json
{
  "success": true,
  "message": "Signals generated successfully",
  "data": {
    "signals": [
      {
        "signal_id": "sig_new123",
        "symbol": "RELIANCE",
        "action": "BUY",
        "confidence": 82.00,
        "target_price": 2900.00,
        "stop_loss": 2820.00,
        "reasoning": "AI analysis complete"
      }
    ],
    "generated_count": 3
  },
  "timestamp": "2026-05-16T10:30:00Z"
}
```

---

### GET /api/v1/signals/:id

Get signal details.

| Attribute | Value |
|-----------|-------|
| Endpoint | `/api/v1/signals/:id` |
| Method | GET |
| Auth Required | Yes |

**Success Response (200)**
```json
{
  "success": true,
  "message": "Signal details retrieved",
  "data": {
    "signal_id": "sig_abc123",
    "symbol": "RELIANCE",
    "exchange": "NSE",
    "action": "BUY",
    "confidence": 85.50,
    "target_price": 2900.00,
    "stop_loss": 2820.00,
    "entry_range": {
      "min": 2850.00,
      "max": 2860.00
    },
    "reasoning": "RSI at 28 (oversold), MACD showing bullish divergence, price approaching support at 2840",
    "indicators": {
      "rsi": 28.5,
      "rsi_14": 28.5,
      "macd": "bullish",
      "macd_line": 15.20,
      "signal_line": 12.50,
      "sma_20": 2875.00,
      "sma_50": 2850.00,
      "sma_200": 2800.00,
      "volume_ratio": 1.5,
      "atr": 45.20,
      "bb_upper": 2920.00,
      "bb_middle": 2850.00,
      "bb_lower": 2780.00
    },
    "historical_performance": {
      "total_signals": 50,
      "winning_signals": 40,
      "win_rate": 80.00,
      "avg_return_percent": 2.5
    },
    "timeframe": "1HOUR",
    "generated_at": "2026-05-16T10:00:00Z",
    "expires_at": "2026-05-16T11:00:00Z",
    "status": "ACTIVE"
  },
  "timestamp": "2026-05-16T10:30:00Z"
}
```

---

# 11. NOTIFICATIONS API

## Endpoints

### GET /api/v1/notifications

Get user notifications.

| Attribute | Value |
|-----------|-------|
| Endpoint | `/api/v1/notifications` |
| Method | GET |
| Auth Required | Yes |

**Query Parameters**
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| unread_only | boolean | Only unread notifications | false |
| type | string | Filter by type | null |
| page | int | Page number | 1 |
| limit | int | Items per page | 20 |

**Success Response (200)**
```json
{
  "success": true,
  "message": "Notifications retrieved successfully",
  "data": [
    {
      "notification_id": "notif_abc123",
      "type": "ORDER_FILLED",
      "title": "Order Filled",
      "message": "Buy order for 100 shares of RELIANCE executed at ₹2850.50",
      "read": false,
      "priority": "HIGH",
      "data": {
        "order_id": "ord_abc123",
        "symbol": "RELIANCE",
        "action": "BUY"
      },
      "created_at": "2026-05-16T10:30:00Z"
    },
    {
      "notification_id": "notif_def456",
      "type": "SIGNAL",
      "title": "New Trading Signal",
      "message": "AI generated BUY signal for RELIANCE with 85% confidence",
      "read": true,
      "priority": "MEDIUM",
      "data": {
        "signal_id": "sig_abc123"
      },
      "created_at": "2026-05-16T09:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 50,
    "pages": 3
  },
  "unread_count": 3,
  "timestamp": "2026-05-16T10:30:00Z"
}
```

**Notification Types**
- ORDER_FILLED, ORDER_CANCELLED, ORDER_REJECTED
- POSITION_OPENED, POSITION_CLOSED
- SIGNAL, ALERT
- SYSTEM, INFO
- WARNING, ERROR

---

### PUT /api/v1/notifications/:id/read

Mark notification as read.

| Attribute | Value |
|-----------|-------|
| Endpoint | `/api/v1/notifications/:id/read` |
| Method | PUT |
| Auth Required | Yes |

**Success Response (200)**
```json
{
  "success": true,
  "message": "Notification marked as read",
  "data": {
    "notification_id": "notif_abc123",
    "read": true,
    "read_at": "2026-05-16T10:30:00Z"
  },
  "timestamp": "2026-05-16T10:30:00Z"
}
```

---

### PUT /api/v1/notifications/read-all

Mark all notifications as read.

| Attribute | Value |
|-----------|-------|
| Endpoint | `/api/v1/notifications/read-all` |
| Method | PUT |
| Auth Required | Yes |

**Success Response (200)**
```json
{
  "success": true,
  "message": "All notifications marked as read",
  "data": {
    "updated_count": 15,
    "read_at": "2026-05-16T10:30:00Z"
  },
  "timestamp": "2026-05-16T10:30:00Z"
}
```

---

### DELETE /api/v1/notifications/:id

Delete a notification.

| Attribute | Value |
|-----------|-------|
| Endpoint | `/api/v1/notifications/:id` |
| Method | DELETE |
| Auth Required | Yes |

**Success Response (200)**
```json
{
  "success": true,
  "message": "Notification deleted successfully",
  "data": {},
  "timestamp": "2026-05-16T10:30:00Z"
}
```

---

# 12. DASHBOARD API

## Endpoints

### GET /api/v1/dashboard/summary

Get dashboard summary.

| Attribute | Value |
|-----------|-------|
| Endpoint | `/api/v1/dashboard/summary` |
| Method | GET |
| Auth Required | Yes |

**Success Response (200)**
```json
{
  "success": true,
  "message": "Dashboard summary retrieved",
  "data": {
    "account": {
      "total_balance": 650000.00,
      "available_cash": 500000.00,
      "used_margin": 150000.00,
      "currency": "INR"
    },
    "today": {
      "pnl": 3500.00,
      "pnl_percent": 0.54,
      "trades": 15,
      "buy_trades": 10,
      "sell_trades": 5,
      "winning_trades": 12,
      "losing_trades": 3,
      "win_rate": 80.00
    },
    "positions": {
      "open": 3,
      "total_value": 1500000.00,
      "unrealized_pnl": 5000.00
    },
    "orders": {
      "pending": 2,
      "executed_today": 15
    },
    "strategies": {
      "active": 2,
      "paused": 3
    },
    "alerts": {
      "critical": 0,
      "warnings": 2
    }
  },
  "timestamp": "2026-05-16T10:30:00Z"
}
```

---

### GET /api/v1/dashboard/performance

Get performance metrics.

| Attribute | Value |
|-----------|-------|
| Endpoint | `/api/v1/dashboard/performance` |
| Method | GET |
| Auth Required | Yes |

**Query Parameters**
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| period | string | TODAY, WEEK, MONTH, YEAR, ALL | WEEK |

**Success Response (200)**
```json
{
  "success": true,
  "message": "Performance metrics retrieved",
  "data": {
    "period": "WEEK",
    "summary": {
      "total_pnl": 25000.00,
      "total_pnl_percent": 4.0,
      "total_trades": 75,
      "winning_trades": 50,
      "losing_trades": 25,
      "win_rate": 66.67,
      "avg_trade_pnl": 333.33,
      "avg_win": 500.00,
      "avg_loss": -200.00,
      "profit_factor": 2.5,
      "sharpe_ratio": 1.8,
      "max_drawdown": -5000.00,
      "max_drawdown_percent": -2.5
    },
    "daily_breakdown": [
      {
        "date": "2026-05-16",
        "pnl": 3500.00,
        "pnl_percent": 0.54,
        "trades": 15,
        "win_rate": 80.00
      },
      {
        "date": "2026-05-15",
        "pnl": -1200.00,
        "pnl_percent": -0.18,
        "trades": 12,
        "win_rate": 58.33
      }
    ],
    "by_symbol": [
      {
        "symbol": "RELIANCE",
        "pnl": 15000.00,
        "trades": 30,
        "win_rate": 70.00
      },
      {
        "symbol": "TCS",
        "pnl": 8000.00,
        "trades": 25,
        "win_rate": 64.00
      }
    ]
  },
  "timestamp": "2026-05-16T10:30:00Z"
}
```

---

### GET /api/v1/dashboard/watchlist

Get watchlist with live prices.

| Attribute | Value |
|-----------|-------|
| Endpoint | `/api/v1/dashboard/watchlist` |
| Method | GET |
| Auth Required | Yes |

**Query Parameters**
| Parameter | Type | Description |
|-----------|------|-------------|
| watchlist_id | string | Specific watchlist ID (optional) |

**Success Response (200)**
```json
{
  "success": true,
  "message": "Watchlist data retrieved",
  "data": [
    {
      "symbol": "RELIANCE",
      "last_price": 2875.00,
      "change": 25.00,
      "change_percent": 0.88,
      "open": 2850.00,
      "high": 2880.00,
      "low": 2845.00,
      "volume": 5200000,
      "vwap": 2862.50,
      "timestamp": "2026-05-16T10:30:00Z"
    },
    {
      "symbol": "TCS",
      "last_price": 4215.00,
      "change": -15.00,
      "change_percent": -0.35,
      "open": 4230.00,
      "high": 4240.00,
      "low": 4200.00,
      "volume": 2800000,
      "vwap": 4220.00,
      "timestamp": "2026-05-16T10:30:00Z"
    }
  ],
  "timestamp": "2026-05-16T10:30:00Z"
}
```

---

### GET /api/v1/dashboard/market-overview

Get market overview.

| Attribute | Value |
|-----------|-------|
| Endpoint | `/api/v1/dashboard/market-overview` |
| Method | GET |
| Auth Required | Yes |

**Success Response (200)**
```json
{
  "success": true,
  "message": "Market overview retrieved",
  "data": {
    "indices": {
      "nifty_50": {
        "value": 22500.50,
        "change": 125.50,
        "change_percent": 0.56,
        "timestamp": "2026-05-16T10:30:00Z"
      },
      "sensex": {
        "value": 75000.25,
        "change": 350.25,
        "change_percent": 0.47,
        "timestamp": "2026-05-16T10:30:00Z"
      },
      "bank_nifty": {
        "value": 48000.00,
        "change": -200.00,
        "change_percent": -0.42,
        "timestamp": "2026-05-16T10:30:00Z"
      }
    },
    "market_status": {
      "trading_session": "REGULAR",
      "next_session": "POST-MARKET",
      "session_start": "09:15:00",
      "session_end": "15:30:00"
    },
    "top_movers": {
      "gainers": [
        {"symbol": "ADANI", "change_percent": 5.2},
        {"symbol": "TITAN", "change_percent": 3.8}
      ],
      "losers": [
        {"symbol": "HDFCBANK", "change_percent": -2.5},
        {"symbol": "BAJAJ", "change_percent": -1.8}
      ]
    }
  },
  "timestamp": "2026-05-16T10:30:00Z"
}
```

---

# 13. MARKET DATA API

## Endpoints

### GET /api/v1/market/quotes

Get quotes for multiple symbols.

| Attribute | Value |
|-----------|-------|
| Endpoint | `/api/v1/market/quotes` |
| Method | GET |
| Auth Required | Yes |

**Query Parameters**
| Parameter | Type | Description |
|-----------|------|-------------|
| symbols | string | Comma-separated symbols (required) |

**Example**: `/api/v1/market/quotes?symbols=RELIANCE,TCS,INFY`

**Success Response (200)**
```json
{
  "success": true,
  "message": "Quotes retrieved successfully",
  "data": [
    {
      "symbol": "RELIANCE",
      "exchange": "NSE",
      "last_price": 2875.00,
      "change": 25.00,
      "change_percent": 0.88,
      "open": 2850.00,
      "high": 2880.00,
      "low": 2845.00,
      "prev_close": 2850.00,
      "volume": 5200000,
      "value": 14946000000,
      "vwap": 2862.50,
      "52w_high": 3200.00,
      "52w_low": 2200.00,
      "avg_volume_20d": 4800000,
      "timestamp": "2026-05-16T10:30:00Z"
    }
  ],
  "timestamp": "2026-05-16T10:30:00Z"
}
```

---

### GET /api/v1/market/depth/:symbol

Get market depth (order book) for a symbol.

| Attribute | Value |
|-----------|-------|
| Endpoint | `/api/v1/market/depth/:symbol` |
| Method | GET |
| Auth Required | Yes |

**Path Parameters**
| Parameter | Type | Description |
|-----------|------|-------------|
| symbol | string | Stock symbol |

**Success Response (200)**
```json
{
  "success": true,
  "message": "Market depth retrieved",
  "data": {
    "symbol": "RELIANCE",
    "exchange": "NSE",
    "timestamp": "2026-05-16T10:30:00Z",
    "buy_orders": [
      {"price": 2874.50, "quantity": 2500, "orders": 15},
      {"price": 2874.00, "quantity": 5000, "orders": 25},
      {"price": 2873.50, "quantity": 7500, "orders": 30},
      {"price": 2873.00, "quantity": 10000, "orders": 45},
      {"price": 2872.50, "quantity": 15000, "orders": 60}
    ],
    "sell_orders": [
      {"price": 2875.00, "quantity": 3000, "orders": 20},
      {"price": 2875.50, "quantity": 4500, "orders": 28},
      {"price": 2876.00, "quantity": 8000, "orders": 35},
      {"price": 2876.50, "quantity": 12000, "orders": 50},
      {"price": 2877.00, "quantity": 18000, "orders": 70}
    ],
    "total_buy_quantity": 35000,
    "total_sell_quantity": 42000
  },
  "timestamp": "2026-05-16T10:30:00Z"
}
```

---

### GET /api/v1/market/candles/:symbol

Get OHLCV candle data.

| Attribute | Value |
|-----------|-------|
| Endpoint | `/api/v1/market/candles/:symbol` |
| Method | GET |
| Auth Required | Yes |

**Query Parameters**
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| timeframe | string | 1MIN, 5MIN, 15MIN, 30MIN, 1HOUR, 1DAY | 5MIN |
| from | string | Start datetime | 24h ago |
| to | string | End datetime | now |
| limit | int | Number of candles | 100 |

**Success Response (200)**
```json
{
  "success": true,
  "message": "Candle data retrieved",
  "data": {
    "symbol": "RELIANCE",
    "exchange": "NSE",
    "timeframe": "5MIN",
    "candles": [
      {
        "timestamp": "2026-05-16T10:25:00Z",
        "open": 2872.00,
        "high": 2875.50,
        "low": 2870.00,
        "close": 2875.00,
        "volume": 125000,
        "value": 359375000,
        "trades": 2500
      },
      {
        "timestamp": "2026-05-16T10:20:00Z",
        "open": 2868.00,
        "high": 2872.00,
        "low": 2865.00,
        "close": 2872.00,
        "volume": 98000,
        "value": 281056000,
        "trades": 1950
      }
    ],
    "count": 100
  },
  "timestamp": "2026-05-16T10:30:00Z"
}
```

---

### GET /api/v1/market/top-gainers

Get top gaining stocks.

| Attribute | Value |
|-----------|-------|
| Endpoint | `/api/v1/market/top-gainers` |
| Method | GET |
| Auth Required | Yes |

**Query Parameters**
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| exchange | string | NSE, BSE | NSE |
| index | string | NIFTY50, NIFTY100, NIFTY200, ALL | ALL |
| limit | int | Number of results | 10 |

**Success Response (200)**
```json
{
  "success": true,
  "message": "Top gainers retrieved",
  "data": [
    {
      "symbol": "ADANI",
      "last_price": 3200.00,
      "change": 160.00,
      "change_percent": 5.26,
      "volume": 2500000,
      "value": 8000000000,
      "timestamp": "2026-05-16T10:30:00Z"
    },
    {
      "symbol": "TITAN",
      "last_price": 3850.00,
      "change": 140.00,
      "change_percent": 3.77,
      "volume": 1800000,
      "value": 6930000000,
      "timestamp": "2026-05-16T10:30:00Z"
    }
  ],
  "timestamp": "2026-05-16T10:30:00Z"
}
```

---

### GET /api/v1/market/top-losers

Get top losing stocks.

| Attribute | Value |
|-----------|-------|
| Endpoint | `/api/v1/market/top-losers` |
| Method | GET |
| Auth Required | Yes |

**Query Parameters**
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| exchange | string | NSE, BSE | NSE |
| index | string | NIFTY50, NIFTY100, NIFTY200, ALL | ALL |
| limit | int | Number of results | 10 |

**Success Response (200)**
```json
{
  "success": true,
  "message": "Top losers retrieved",
  "data": [
    {
      "symbol": "HDFCBANK",
      "last_price": 1680.00,
      "change": -45.00,
      "change_percent": -2.61,
      "volume": 4500000,
      "value": 7560000000,
      "timestamp": "2026-05-16T10:30:00Z"
    },
    {
      "symbol": "BAJAJ",
      "last_price": 8200.00,
      "change": -150.00,
      "change_percent": -1.80,
      "volume": 1200000,
      "value": 9840000000,
      "timestamp": "2026-05-16T10:30:00Z"
    }
  ],
  "timestamp": "2026-05-16T10:30:00Z"
}
```

---

# 14. WEBSOCKET EVENTS

## Connection

```
WebSocket URL: ws://localhost:5000/socket.io
```

## Client Events

### Subscribe to Market Data

**Event**: `subscribe_market`

**Payload**:
```json
{
  "type": "subscribe_market",
  "symbols": ["RELIANCE", "TCS", "INFY"],
  "channel": "quotes"
}
```

**Channels**: `quotes`, `depth`, `candles`

---

### Unsubscribe from Market Data

**Event**: `unsubscribe_market`

**Payload**:
```json
{
  "type": "unsubscribe_market",
  "symbols": ["RELIANCE"]
}
```

---

### Subscribe to Watchlist

**Event**: `subscribe_watchlist`

**Payload**:
```json
{
  "type": "subscribe_watchlist",
  "watchlist_id": "wl_abc123"
}
```

---

### Place Order (Real-time)

**Event**: `place_order`

**Payload**:
```json
{
  "type": "place_order",
  "order": {
    "order_type": "MARKET",
    "product": "MIS",
    "symbol": "RELIANCE",
    "exchange": "NSE",
    "side": "BUY",
    "quantity": 100
  }
}
```

---

### Subscribe to User Updates

**Event**: `subscribe_user`

**Payload**:
```json
{
  "type": "subscribe_user",
  "user_id": "usr_abc123",
  "channels": ["orders", "positions", "pnl"]
}
```

---

## Server Events

### Market Tick

**Event**: `market_tick`

**Payload**:
```json
{
  "event": "market_tick",
  "data": {
    "symbol": "RELIANCE",
    "last_price": 2875.00,
    "change": 25.00,
    "change_percent": 0.88,
    "volume": 5200000,
    "timestamp": "2026-05-16T10:30:00Z"
  }
}
```

---

### Order Update

**Event**: `order_update`

**Payload**:
```json
{
  "event": "order_update",
  "data": {
    "order_id": "ord_abc123",
    "status": "EXECUTED",
    "filled_quantity": 100,
    "average_price": 2850.50,
    "message": "Order filled",
    "timestamp": "2026-05-16T09:30:05Z"
  }
}
```

**Order Status Values**: `PENDING`, `EXECUTED`, `CANCELLED`, `REJECTED`, `MODIFIED`

---

### Position Update

**Event**: `position_update`

**Payload**:
```json
{
  "event": "position_update",
  "data": {
    "position_id": "pos_abc123",
    "symbol": "RELIANCE",
    "quantity": 100,
    "current_price": 2875.00,
    "unrealized_pnl": 2450.00,
    "pnl_percent": 0.86,
    "day_pnl": 1500.00,
    "timestamp": "2026-05-16T10:30:00Z"
  }
}
```

---

### P&L Update

**Event**: `pnl_update`

**Payload**:
```json
{
  "event": "pnl_update",
  "data": {
    "total_pnl": 5000.00,
    "day_pnl": 3500.00,
    "unrealized_pnl": 1500.00,
    "realized_pnl": 2000.00,
    "margin_used": 150000.00,
    "available_cash": 500000.00,
    "timestamp": "2026-05-16T10:30:00Z"
  }
}
```

---

### Notification

**Event**: `notification`

**Payload**:
```json
{
  "event": "notification",
  "data": {
    "notification_id": "notif_abc123",
    "type": "ORDER_FILLED",
    "title": "Order Filled",
    "message": "Buy order for RELIANCE executed",
    "priority": "HIGH",
    "timestamp": "2026-05-16T10:30:00Z"
  }
}
```

---

### Strategy Update

**Event**: `strategy_update`

**Payload**:
```json
{
  "event": "strategy_update",
  "data": {
    "strategy_id": "strat_abc123",
    "status": "ACTIVE",
    "signal": {
      "action": "BUY",
      "symbol": "RELIANCE",
      "price": 2850.50,
      "quantity": 100,
      "confidence": 85.00
    },
    "message": "Strategy generated buy signal",
    "timestamp": "2026-05-16T10:30:00Z"
  }
}
```

---

### AI Signal Update

**Event**: `ai_signal`

**Payload**:
```json
{
  "event": "ai_signal",
  "data": {
    "signal_id": "sig_abc123",
    "symbol": "RELIANCE",
    "action": "BUY",
    "confidence": 85.50,
    "target_price": 2900.00,
    "stop_loss": 2820.00,
    "reasoning": "RSI at 28 (oversold)",
    "timestamp": "2026-05-16T10:30:00Z"
  }
}
```

---

### Market Status Update

**Event**: `market_status`

**Payload**:
```json
{
  "event": "market_status",
  "data": {
    "exchange": "NSE",
    "status": "OPEN",
    "session": "REGULAR",
    "next_session": "POST-MARKET",
    "closes_in_seconds": 18000,
    "timestamp": "2026-05-16T10:30:00Z"
  }
}
```

---

## Subscription Flow

### Frontend Implementation

```javascript
// Connect to WebSocket
const socket = io('http://localhost:5000', {
  transports: ['websocket'],
  auth: {
    token: 'Bearer <access_token>'
  }
});

// Subscribe to market data
socket.emit('subscribe_market', {
  symbols: ['RELIANCE', 'TCS'],
  channel: 'quotes'
});

// Listen for updates
socket.on('market_tick', (data) => {
  console.log('Price update:', data);
});

socket.on('order_update', (data) => {
  console.log('Order update:', data);
});
```

---

# 15. SETTINGS API

## Endpoints

### GET /api/v1/settings

Get user settings.

| Attribute | Value |
|-----------|-------|
| Endpoint | `/api/v1/settings` |
| Method | GET |
| Auth Required | Yes |

**Success Response (200)**
```json
{
  "success": true,
  "message": "Settings retrieved successfully",
  "data": {
    "trading": {
      "default_product": "MIS",
      "default_order_type": "LIMIT",
      "default_exchange": "NSE",
      "default_validity": "DAY",
      "auto_square_off": true,
      "square_off_time": "15:15"
    },
    "notifications": {
      "order_filled": true,
      "order_cancelled": true,
      "order_rejected": true,
      "position_opened": true,
      "position_closed": true,
      "stop_loss_hit": true,
      "target_hit": true,
      "daily_summary": true,
      "ai_signals": true,
      "email_notifications": true,
      "sms_notifications": false,
      "push_notifications": true
    },
    "display": {
      "theme": "DARK",
      "language": "en",
      "price_format": "INR",
      "show_volume": true,
      "chart_type": "CANDLESTICK"
    },
    "api_access": {
      "enabled": true,
      "api_key": "ak_abc123***",
      "webhook_url": "https://example.com/webhook",
      "rate_limit": 100
    },
    "risk_management": {
      "max_daily_loss": 10000,
      "max_single_trade_loss": 2000,
      "max_positions": 10,
      "max_orders_per_minute": 10,
      "position_size_percent": 10
    },
    "updated_at": "2026-05-15T00:00:00Z"
  },
  "timestamp": "2026-05-16T10:30:00Z"
}
```

---

### PUT /api/v1/settings

Update user settings.

| Attribute | Value |
|-----------|-------|
| Endpoint | `/api/v1/settings` |
| Method | PUT |
| Auth Required | Yes |

**Request Headers**
```
Content-Type: application/json
Authorization: Bearer <access_token>
```

**Request Body**
```json
{
  "trading": {
    "default_product": "CNC",
    "default_order_type": "MARKET"
  },
  "notifications": {
    "order_filled": true,
    "daily_summary": true
  },
  "display": {
    "theme": "LIGHT"
  },
  "risk_management": {
    "max_daily_loss": 15000
  }
}
```

**Success Response (200)**
```json
{
  "success": true,
  "message": "Settings updated successfully",
  "data": {
    "updated_fields": ["trading", "notifications", "display", "risk_management"],
    "updated_at": "2026-05-16T10:30:00Z"
  },
  "timestamp": "2026-05-16T10:30:00Z"
}
```

---

# 16. API SECURITY & BEST PRACTICES

## Authentication

### JWT Implementation

```
Access Token: Expires in 1 hour
Refresh Token: Expires in 7 days
```

**Authorization Header Format**:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Token Refresh Flow

1. When access token expires (401 response)
2. Use refresh token to get new access token
3. Retry original request with new token

---

## Rate Limiting

**Endpoint Rate Limits**:

| Endpoint Category | Limit |
|-----------------|-------|
| Authentication | 5 req/min |
| Order Placement | 30 req/min |
| Market Data | 60 req/min |
| General API | 100 req/min |

**Rate Limit Headers**:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1715859000
```

---

## Input Validation

### Common Validation Rules

| Field Type | Rules |
|-----------|-------|
| Email | Valid format, max 255 chars |
| Password | Min 8 chars, 1 uppercase, 1 number, 1 special |
| Phone | Indian mobile format (+91XXXXXXXXXX) |
| PAN | Valid PAN format (AAAAA1234A) |
| Symbol | Valid stock symbol, max 20 chars |
| Quantity | Positive integer, min lot size |
| Price | Positive decimal, max 2 decimal places |

---

## Error Codes

| Error Code | HTTP Status | Description |
|------------|-------------|-------------|
| INVALID_CREDENTIALS | 401 | Login failed |
| TOKEN_EXPIRED | 401 | JWT token expired |
| TOKEN_INVALID | 401 | Invalid JWT token |
| UNAUTHORIZED | 403 | Access denied |
| NOT_FOUND | 404 | Resource not found |
| VALIDATION_ERROR | 400 | Invalid input |
| RATE_LIMITED | 429 | Too many requests |
| SERVER_ERROR | 500 | Internal server error |
| BROKER_ERROR | 502 | Broker API error |
| MARKET_CLOSED | 403 | Market is closed |

---

## Security Headers

```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000
Content-Security-Policy: default-src 'self'
```

---

# 17. API VERSIONING STRATEGY

## Versioning Format

```
/api/v1/<endpoint>
```

## Version Transition

1. New versions released as `/api/v2/`
2. Old versions deprecated with 12-month notice
3. Deprecated endpoints return `Warning` header

**Deprecation Header**:
```
Deprecation: true
Sunset: Sat, 01 Jan 2027 00:00:00 GMT
Link: <https://api.example.com/v2/orders>; rel="successor-version"
```

---

# 18. FRONTEND INTEGRATION GUIDELINES

## Axios Configuration

```javascript
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:5000/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
});

// Request interceptor
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Handle token refresh
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        const response = await axios.post('/auth/refresh', { refreshToken });
        localStorage.setItem('access_token', response.data.data.access_token);
        error.config.headers.Authorization = `Bearer ${response.data.data.access_token}`;
        return axios(error.config);
      }
    }
    return Promise.reject(error);
  }
);

export default api;
```

---

## Zustand Store Integration

```javascript
import { create } from 'zustand';
import api from './api';

const useOrderStore = create((set, get) => ({
  orders: [],
  loading: false,
  error: null,

  fetchOrders: async (params) => {
    set({ loading: true, error: null });
    try {
      const response = await api.get('/orders', { params });
      set({ orders: response.data.data, loading: false });
    } catch (error) {
      set({ error: error.response?.data?.message, loading: false });
    }
  },

  placeOrder: async (orderData) => {
    set({ loading: true, error: null });
    try {
      const response = await api.post('/orders', orderData);
      set((state) => ({
        orders: [response.data.data, ...state.orders],
        loading: false
      }));
      return response.data.data;
    } catch (error) {
      set({ error: error.response?.data?.message, loading: false });
      throw error;
    }
  }
}));

export default useOrderStore;
```

---

## WebSocket Integration

```javascript
import { useEffect, useRef } from 'react';
import io from 'socket.io-client';
import { useOrderStore } from './stores';

const SOCKET_URL = 'http://localhost:5000';

export const useWebSocket = (accessToken) => {
  const socketRef = useRef(null);
  const updateOrder = useOrderStore((state) => state.updateOrder);

  useEffect(() => {
    if (accessToken) {
      socketRef.current = io(SOCKET_URL, {
        transports: ['websocket'],
        auth: { token: accessToken }
      });

      socketRef.current.on('connect', () => {
        console.log('WebSocket connected');
        socketRef.current.emit('subscribe_user', {
          user_id: 'current',
          channels: ['orders', 'positions', 'pnl']
        });
      });

      socketRef.current.on('order_update', (data) => {
        updateOrder(data);
      });

      socketRef.current.on('position_update', (data) => {
        // Update position store
      });

      return () => {
        socketRef.current?.disconnect();
      };
    }
  }, [accessToken, updateOrder]);

  return socketRef.current;
};
```

---

## Pagination Guidelines

### Request Format

```javascript
const params = {
  page: 1,
  limit: 20
};

const response = await api.get('/orders', { params });
```

### Response Handling

```javascript
const { data, pagination } = response.data;

// For infinite scroll
const loadMore = () => {
  if (pagination.page < pagination.pages) {
    const nextPage = pagination.page + 1;
    const response = await api.get('/orders', { params: { page: nextPage } });
    setOrders([...orders, ...response.data.data]);
  }
};
```

---

## Sorting Standards

### Query Parameters

| Parameter | Values | Default |
|-----------|--------|---------|
| sort_by | created_at, symbol, price, pnl | created_at |
| sort_order | asc, desc | desc |

### Example

```
GET /api/v1/orders?sort_by=created_at&sort_order=desc
```

---

## Filtering Standards

### Common Filters

| Parameter | Type | Example |
|-----------|------|---------|
| symbol | string | RELIANCE |
| status | string | PENDING, EXECUTED |
| from_date | date | 2026-05-01 |
| to_date | date | 2026-05-16 |

### Example

```
GET /api/v1/orders?status=EXECUTED&symbol=RELIANCE&from_date=2026-05-01
```

---

# 19. COMMON STATUS CODES SUMMARY

| Status Code | Meaning |
|-------------|----------|
| 200 | OK - Success |
| 201 | Created - Resource created |
| 400 | Bad Request - Validation error |
| 401 | Unauthorized - Auth required |
| 403 | Forbidden - Access denied |
| 404 | Not Found - Resource missing |
| 409 | Conflict - Duplicate data |
| 422 | Unprocessable - Business logic error |
| 429 | Too Many Requests - Rate limit |
| 500 | Internal Server Error |
| 502 | Bad Gateway - External service error |
| 503 | Service Unavailable |

---

# 20. INDIAN STOCK SYMBOLS REFERENCE

### Common NSE Symbols

| Symbol | Company Name |
|--------|--------------|
| RELIANCE | Reliance Industries |
| TCS | Tata Consultancy Services |
| INFY | Infosys |
| HDFCBANK | HDFC Bank |
| ICICIBANK | ICICI Bank |
| SBIN | State Bank of India |
| BHARTIARTL | Bharti Airtel |
| HINDUNILVR | Hindustan Unilever |
| KOTAKBANK | Kotak Mahindra Bank |
| ITC | ITC Limited |

### Indices

| Index | Symbol |
|-------|--------|
| Nifty 50 | NIFTY |
| Sensex | SENSEX |
| Bank Nifty | BANKNIFTY |
| Nifty IT | NIFTYIT |
| Nifty Pharma | NIFTYPHARMA |

---

# APPENDIX A: API CHANGELOG

| Version | Date | Changes |
|---------|------|---------|
| v1.0.0 | 2026-05-16 | Initial release |

---

# APPENDIX B: TESTING ENDPOINTS

## cURL Examples

### Login
```bash
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"trader@example.com","password":"SecurePass123!"}'
```

### Get Orders
```bash
curl -X GET http://localhost:5000/api/v1/orders \
  -H "Authorization: Bearer <token>"
```

### Place Order
```bash
curl -X POST http://localhost:5000/api/v1/orders \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"order_type":"LIMIT","product":"MIS","symbol":"RELIANCE","exchange":"NSE","side":"BUY","quantity":100,"price":2850.50}'
```

---

*Document Version: 1.0*
*Last Updated: 2026-05-16*
*API Base URL: http://localhost:5000/api/v1*