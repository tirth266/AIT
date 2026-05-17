# MongoDB Architecture - Institutional Trading Platform

## 1. Index Strategy

### 1.1 Orders Collection

```javascript
// Primary index - unique order identification
db.orders.createIndex({ "order_id": 1 }, { unique: true })

// User queries - active orders by user
db.orders.createIndex({ "user_id": 1, "status": 1, "created_at": -1 })

// Symbol queries - orders by symbol
db.orders.createIndex({ "symbol": 1, "exchange": 1, "created_at": -1 })

// Strategy-specific orders
db.orders.createIndex({ "strategy_id": 1, "created_at": -1 })

// Status-based queries for order processing
db.orders.createIndex({ "status": 1, "created_at": -1 })

// TTL index for order cleanup (180 days retention)
db.orders.createIndex({ "created_at": 1 }, { expireAfterSeconds: 15552000 })

// Compound index for fills tracking
db.orders.createIndex({ "status": 1, "filled_at": 1 }, { partialFilterExpression: { "filled_at": { $exists: true } } })

// Text search for comments/tags
db.orders.createIndex({ "order_tag": "text", "comments": "text" })
```

### 1.2 Trades Collection

```javascript
// Unique trade identification
db.trades.createIndex({ "trade_id": 1 }, { unique: true })

// Order-to-trade lookup
db.trades.createIndex({ "order_id": 1 })

// Position tracking
db.trades.createIndex({ "position_id": 1 })

// User trade history
db.trades.createIndex({ "user_id": 1, "execution_time": -1 })

// Symbol-based trades
db.trades.createIndex({ "symbol": 1, "exchange": 1, "execution_time": -1 })

// Strategy attribution
db.trades.createIndex({ "strategy_id": 1, "execution_time": -1 })

// TTL index - 365 days retention
db.trades.createIndex({ "execution_time": 1 }, { expireAfterSeconds: 31536000 })

// Compound for P&L calculations
db.trades.createIndex({ "user_id": 1, "symbol": 1, "execution_time": -1 })
```

### 1.3 Positions Collection

```javascript
// Unique position identification
db.positions.createIndex({ "position_id": 1 }, { unique: true })

// User positions
db.positions.createIndex({ "user_id": 1, "status": 1 })

// Active positions by symbol
db.positions.createIndex({ "symbol": 1, "exchange": 1, "status": 1 })

// Strategy positions
db.positions.createIndex({ "strategy_id": 1, "status": 1 })

// Open positions (high frequency query)
db.positions.createIndex({ "status": 1, "mtm_updated_at": -1 })

// TTL for closed positions (90 days)
db.positions.createIndex({ "closed_at": 1 }, { expireAfterSeconds: 7776000, partialFilterExpression: { "status": "CLOSED" } })
```

### 1.4 Candles Collection

```javascript
// Unique OHLCV identification
db.candles.createIndex({ "symbol": 1, "interval": 1, "timestamp": 1 }, { unique: true })

// Time-range queries
db.candles.createIndex({ "symbol": 1, "interval": 1, "timestamp": -1 })

// Recent candles (cache-style)
db.candles.createIndex({ "symbol": 1, "interval": 1, "timestamp": -1 }, { partialFilterExpression: { "timestamp": { $gt: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000) } } })

// TTL - 2 years retention for candles
db.candles.createIndex({ "timestamp": 1 }, { expireAfterSeconds: 63072000 })
```

### 1.5 Users Collection

```javascript
// Unique user identification
db.users.createIndex({ "user_id": 1 }, { unique: true })

// Email lookup
db.users.createIndex({ "email": 1 }, { unique: true })

// Active users
db.users.createIndex({ "status": 1, "created_at": -1 })

// API key lookup
db.users.createIndex({ "api_keys.key": 1 }, { unique: true, sparse: true })
```

### 1.6 Strategies Collection

```javascript
// Unique strategy identification
db.strategies.createIndex({ "strategy_id": 1 }, { unique: true })

// User strategies
db.strategies.createIndex({ "user_id": 1, "status": 1 })

// Active strategies
db.strategies.createIndex({ "status": 1, "updated_at": -1 })
```

### 1.7 Risk Events Collection

```javascript
// Unique event identification
db.risk_events.createIndex({ "event_id": 1 }, { unique: true })

// User risk events
db.risk_events.createIndex({ "user_id": 1, "timestamp": -1 })

// Event type queries
db.risk_events.createIndex({ "event_type": 1, "timestamp": -1 })

// Severity-based queries
db.risk_events.createIndex({ "severity": 1, "timestamp": -1 })

// TTL - 2 years for audit
db.risk_events.createIndex({ "timestamp": 1 }, { expireAfterSeconds: 63072000 })
```

### 1.8 Audit Logs Collection

```javascript
// Unique log identification
db.audit_logs.createIndex({ "log_id": 1 }, { unique: true })

// User audit trail
db.audit_logs.createIndex({ "user_id": 1, "timestamp": -1 })

// Action type queries
db.audit_logs.createIndex({ "action": 1, "timestamp": -1 })

// Resource-based queries
db.audit_logs.createIndex({ "resource_type": 1, "resource_id": 1, "timestamp": -1 })

// TTL - 7 years for compliance
db.audit_logs.createIndex({ "timestamp": 1 }, { expireAfterSeconds: 220752000 })
```

---

## 2. Mongo Shell Commands

```javascript
// ============================================
// ORDERS - Full Index Setup
// ============================================

db.orders.createIndex({ "order_id": 1 }, { unique: true, background: true })
db.orders.createIndex({ "user_id": 1, "status": 1, "created_at": -1 }, { background: true })
db.orders.createIndex({ "symbol": 1, "exchange": 1, "created_at": -1 }, { background: true })
db.orders.createIndex({ "strategy_id": 1, "created_at": -1 }, { sparse: true, background: true })
db.orders.createIndex({ "status": 1, "created_at": -1 }, { background: true })
db.orders.createIndex({ "created_at": 1 }, { expireAfterSeconds: 15552000, background: true })
db.orders.createIndex({ "status": 1, "filled_at": 1 }, { partialFilterExpression: { "filled_at": { $exists: true } }, background: true })
db.orders.createIndex({ "order_tag": "text", "comments": "text" }, { default_language: "english", background: true })

// ============================================
// TRADES - Full Index Setup
// ============================================

db.trades.createIndex({ "trade_id": 1 }, { unique: true, background: true })
db.trades.createIndex({ "order_id": 1 }, { background: true })
db.trades.createIndex({ "position_id": 1 }, { sparse: true, background: true })
db.trades.createIndex({ "user_id": 1, "execution_time": -1 }, { background: true })
db.trades.createIndex({ "symbol": 1, "exchange": 1, "execution_time": -1 }, { background: true })
db.trades.createIndex({ "strategy_id": 1, "execution_time": -1 }, { sparse: true, background: true })
db.trades.createIndex({ "execution_time": 1 }, { expireAfterSeconds: 31536000, background: true })
db.trades.createIndex({ "user_id": 1, "symbol": 1, "execution_time": -1 }, { background: true })

// ============================================
// POSITIONS - Full Index Setup
// ============================================

db.positions.createIndex({ "position_id": 1 }, { unique: true, background: true })
db.positions.createIndex({ "user_id": 1, "status": 1 }, { background: true })
db.positions.createIndex({ "symbol": 1, "exchange": 1, "status": 1 }, { background: true })
db.positions.createIndex({ "strategy_id": 1, "status": 1 }, { sparse: true, background: true })
db.positions.createIndex({ "status": 1, "mtm_updated_at": -1 }, { background: true })
db.positions.createIndex({ "closed_at": 1 }, { expireAfterSeconds: 7776000, partialFilterExpression: { "status": "CLOSED" }, background: true })

// ============================================
// CANDLES - Full Index Setup
// ============================================

db.candles.createIndex({ "symbol": 1, "interval": 1, "timestamp": 1 }, { unique: true, background: true })
db.candles.createIndex({ "symbol": 1, "interval": 1, "timestamp": -1 }, { background: true })
db.candles.createIndex({ "timestamp": 1 }, { expireAfterSeconds: 63072000, background: true })

// ============================================
// USERS - Full Index Setup
// ============================================

db.users.createIndex({ "user_id": 1 }, { unique: true, background: true })
db.users.createIndex({ "email": 1 }, { unique: true, background: true })
db.users.createIndex({ "status": 1, "created_at": -1 }, { background: true })
db.users.createIndex({ "api_keys.key": 1 }, { unique: true, sparse: true, background: true })

// ============================================
// STRATEGIES - Full Index Setup
// ============================================

db.strategies.createIndex({ "strategy_id": 1 }, { unique: true, background: true })
db.strategies.createIndex({ "user_id": 1, "status": 1 }, { background: true })
db.strategies.createIndex({ "status": 1, "updated_at": -1 }, { background: true })

// ============================================
// RISK_EVENTS - Full Index Setup
// ============================================

db.risk_events.createIndex({ "event_id": 1 }, { unique: true, background: true })
db.risk_events.createIndex({ "user_id": 1, "timestamp": -1 }, { background: true })
db.risk_events.createIndex({ "event_type": 1, "timestamp": -1 }, { background: true })
db.risk_events.createIndex({ "severity": 1, "timestamp": -1 }, { background: true })
db.risk_events.createIndex({ "timestamp": 1 }, { expireAfterSeconds: 63072000, background: true })

// ============================================
// AUDIT_LOGS - Full Index Setup
// ============================================

db.audit_logs.createIndex({ "log_id": 1 }, { unique: true, background: true })
db.audit_logs.createIndex({ "user_id": 1, "timestamp": -1 }, { background: true })
db.audit_logs.createIndex({ "action": 1, "timestamp": -1 }, { background: true })
db.audit_logs.createIndex({ "resource_type": 1, "resource_id": 1, "timestamp": -1 }, { background: true })
db.audit_logs.createIndex({ "timestamp": 1 }, { expireAfterSeconds: 220752000, background: true })
```

---

## 3. Optimized Queries

### 3.1 Order Queries

```javascript
// Get user's active orders with pagination
db.orders.find({
  user_id: "user_123",
  status: { $in: ["NEW", "OPEN", "PARTIALLY_FILLED"] }
}).sort({ created_at: -1 }).limit(50).skip(0)

// Get orders by symbol with date range
db.orders.find({
  symbol: "RELIANCE",
  exchange: "NSE",
  created_at: {
    $gte: ISODate("2024-01-01T00:00:00Z"),
    $lt: ISODate("2024-01-02T00:00:00Z")
  }
}).sort({ created_at: -1 }).limit(100)

// Get filled orders for P&L calculation
db.orders.find({
  user_id: "user_123",
  status: "FILLED",
  filled_at: {
    $gte: ISODate("2024-01-01T00:00:00Z"),
    $lt: ISODate("2024-01-31T23:59:59Z")
  }
}).sort({ filled_at: -1 })

// Aggregate order statistics
db.orders.aggregate([
  { $match: { user_id: "user_123", created_at: { $gte: ISODate("2024-01-01") } } },
  { $group: {
    _id: "$status",
    count: { $sum: 1 },
    total_quantity: { $sum: "$quantity" },
    filled_quantity: { $sum: "$filled_quantity" }
  }}
])
```

### 3.2 Position Queries

```javascript
// Get all open positions for user
db.positions.find({
  user_id: "user_123",
  status: "OPEN"
}).sort({ mtm_updated_at: -1 })

// Get positions by symbol
db.positions.find({
  symbol: "RELIANCE",
  exchange: "NSE",
  status: "OPEN"
})

// Get positions with unrealized P&L above threshold
db.positions.find({
  user_id: "user_123",
  status: "OPEN",
  unrealized_pnl: { $gt: 10000 }
}).sort({ unrealized_pnl: -1 })

// Aggregate position summary
db.positions.aggregate([
  { $match: { user_id: "user_123", status: "OPEN" } },
  { $group: {
    _id: null,
    total_unrealized_pnl: { $sum: "$unrealized_pnl" },
    total_day_pnl: { $sum: "$day_pnl" },
    position_count: { $sum: 1 },
    total_exposure: { $sum: { $multiply: ["$quantity", "$current_price"] } }
  }}
])
```

### 3.3 Candle Queries

```javascript
// Get candles for chart display
db.candles.find({
  symbol: "RELIANCE",
  interval: "5m",
  timestamp: {
    $gte: ISODate("2024-01-01T00:00:00Z"),
    $lt: ISODate("2024-01-02T00:00:00Z")
  }
}).sort({ timestamp: 1 })

// Get latest candle
db.candles.findOne({
  symbol: "RELIANCE",
  interval: "1h"
}, { sort: { timestamp: -1 } })

// Get candle aggregation for indicators
db.candles.aggregate([
  { $match: {
    symbol: "RELIANCE",
    interval: "1h",
    timestamp: { $gte: ISODate("2024-01-01") }
  }},
  { $group: {
    _id: { $dateToString: { format: "%Y-%m-%d", date: "$timestamp" } },
    open: { $first: "$open" },
    high: { $max: "$high" },
    low: { $min: "$low" },
    close: { $last: "$close" },
    volume: { $sum: "$volume" }
  }},
  { $sort: { _id: 1 } }
])
```

### 3.4 Trade Queries

```javascript
// Get user's trade history with pagination
db.trades.find({
  user_id: "user_123"
}).sort({ execution_time: -1 }).limit(50).skip(0)

// Get trades for P&L calculation
db.trades.aggregate([
  { $match: {
    user_id: "user_123",
    execution_time: {
      $gte: ISODate("2024-01-01T00:00:00Z"),
      $lt: ISODate("2024-01-31T23:59:59Z")
    }
  }},
  { $group: {
    _id: "$symbol",
    total_pnl: { $sum: "$pnl" },
    trade_count: { $sum: 1 },
    total_brokerage: { $sum: "$brokerage" },
    total_taxes: { $sum: { $add: ["$stt", "$gst", "$stamp_duty", "$other_charges"] } }
  }},
  { $sort: { total_pnl: -1 } }
])

// Get daily trade summary
db.trades.aggregate([
  { $match: { user_id: "user_123" } },
  { $group: {
    _id: { $dateToString: { format: "%Y-%m-%d", date: "$execution_time" } },
    total_pnl: { $sum: "$pnl" },
    total_value: { $sum: "$value" },
    trade_count: { $sum: 1 }
  }},
  { $sort: { _id: -1 } },
  { $limit: 30 }
])
```

---

## 4. Aggregation Pipelines

### 4.1 Order Analytics Pipeline

```javascript
db.orders.aggregate([
  // Match recent orders
  {
    $match: {
      created_at: { $gte: ISODate("2024-01-01") },
      user_id: "user_123"
    }
  },
  // Group by status
  {
    $group: {
      _id: "$status",
      count: { $sum: 1 },
      total_value: { $sum: { $multiply: ["$quantity", "$price"] } },
      avg_price: { $avg: "$price" }
    }
  },
  // Sort by count
  { $sort: { count: -1 } }
])
```

### 4.2 Position Risk Pipeline

```javascript
db.positions.aggregate([
  { $match: { user_id: "user_123", status: "OPEN" } },
  {
    $addFields: {
      exposure: { $multiply: ["$quantity", "$current_price"] },
      margin_used: { $multiply: ["$quantity", "$entry_price"] }
    }
  },
  {
    $group: {
      _id: "$symbol",
      total_quantity: { $sum: "$quantity" },
      total_exposure: { $sum: "$exposure" },
      unrealized_pnl: { $sum: "$unrealized_pnl" },
      positions_count: { $sum: 1 }
    }
  },
  { $match: { total_exposure: { $gt: 100000 } } },
  { $sort: { total_exposure: -1 } }
])
```

### 4.3 Daily P&L Pipeline

```javascript
db.trades.aggregate([
  {
    $match: {
      user_id: "user_123",
      execution_time: {
        $gte: ISODate("2024-01-01T00:00:00Z"),
        $lt: ISODate("2024-01-02T00:00:00Z")
      }
    }
  },
  {
    $group: {
      _id: null,
      total_pnl: { $sum: "$pnl" },
      total_brokerage: { $sum: "$brokerage" },
      total_taxes: { $sum: { $add: ["$stt", "$gst", "$stamp_duty"] } },
      total_value: { $sum: "$value" },
      winning_trades: { $sum: { $cond: [{ $gt: ["$pnl", 0] }, 1, 0] } },
      losing_trades: { $sum: { $cond: [{ $lt: ["$pnl", 0] }, 1, 0] } }
    }
  },
  {
    $addFields: {
      net_pnl: { $subtract: ["$total_pnl", { $add: ["$total_brokerage", "$total_taxes"] }] }
    }
  }
])
```

### 4.4 Strategy Performance Pipeline

```javascript
db.orders.aggregate([
  { $match: { strategy_id: "strategy_123" } },
  {
    $lookup: {
      from: "trades",
      localField: "order_id",
      foreignField: "order_id",
      as: "trades"
    }
  },
  { $unwind: "$trades" },
  {
    $group: {
      _id: "$strategy_id",
      total_orders: { $sum: 1 },
      filled_orders: { $sum: { $cond: [{ $eq: ["$status", "FILLED"] }, 1, 0] } },
      total_pnl: { $sum: "$trades.pnl" },
      total_brokerage: { $sum: "$trades.brokerage" }
    }
  },
  {
    $addFields: {
      fill_rate: { $divide: ["$filled_orders", "$total_orders"] },
      net_pnl: { $subtract: ["$total_pnl", "$total_brokerage"] }
    }
  }
])
```

### 4.5 Risk Event Aggregation

```javascript
db.risk_events.aggregate([
  {
    $match: {
      timestamp: { $gte: ISODate("2024-01-01") }
    }
  },
  {
    $group: {
      _id: {
        date: { $dateToString: { format: "%Y-%m-%d", date: "$timestamp" } },
        event_type: "$event_type"
      },
      count: { $sum: 1 },
      severity_breakdown: {
        $push: {
          severity: "$severity",
          count: 1
        }
      }
    }
  },
  { $sort: { "_id.date": -1 } }
])
```

---

## 5. Change Streams

### 5.1 Order Change Stream

```javascript
// Monitor order status changes
const orderStream = db.orders.watch([
  { $match: { "operationType": { $in: ["update", "replace"] } } }
])

orderStream.on("change", (change) => {
  console.log("Order changed:", change.fullDocument.order_id)
  // Notify relevant services
  if (change.updateDescription.updatedFields.status) {
    // Handle status change
  }
})
```

### 5.2 Position Change Stream

```javascript
// Real-time position updates
const positionStream = db.positions.watch([
  { $match: { "operationType": { $in: ["update", "insert"] } } }
])

positionStream.on("change", (change) => {
  if (change.operationType === "insert") {
    // New position opened
  } else if (change.updateDescription) {
    // P&L or status update
  }
})
```

### 5.3 Trade Execution Stream

```javascript
// Trade execution notifications
const tradeStream = db.trades.watch([
  { $match: { "fullDocument.mode": "live" } }
])

tradeStream.on("change", (change) => {
  if (change.operationType === "insert") {
    // Process new trade - update positions, P&L, notifications
  }
})
```

### 5.4 Risk Event Stream

```javascript
// Real-time risk alerts
const riskStream = db.risk_events.watch([
  { $match: { "fullDocument.severity": { $in: ["HIGH", "CRITICAL"] } } }
])

riskStream.on("change", (change) => {
  // Trigger alerts
})
```

---

## 6. Pagination Strategy

### 6.1 Cursor-Based Pagination (Recommended for Large Datasets)

```javascript
// Get next page using last document's _id
function getNextPage(collection, query, pageSize, lastId) {
  const filter = { ...query }
  if (lastId) {
    filter._id = { $gt: lastId }
  }
  return collection.find(filter).sort({ _id: 1 }).limit(pageSize).toArray()
}

// Usage
const page1 = await getNextPage(db.orders, { user_id: "user_123" }, 50, null)
const page2 = await getNextPage(db.orders, { user_id: "user_123" }, 50, page1[49]._id)
```

### 6.2 Keyset Pagination

```javascript
// Pagination using composite key
function keysetPagination(db, query, lastDoc, pageSize) {
  return db.collection.find({
    ...query,
    created_at: { $lt: lastDoc.created_at },
    order_id: { $lt: lastDoc.order_id }
  }).sort({ created_at: -1, order_id: -1 }).limit(pageSize).toArray()
}
```

### 6.3 Range-Based Pagination

```javascript
// For time-range queries
async function paginateByTimeRange(collection, query, startDate, endDate, pageSize) {
  let cursor = collection.find({
    ...query,
    created_at: { $gte: startDate, $lt: endDate }
  }).sort({ created_at: -1 }).limit(pageSize)

  const results = await cursor.toArray()
  return results
}
```

---

## 7. Archival Strategy

### 7.1 Archival Pipeline

```javascript
// Archive old orders to archival collection
db.orders.aggregate([
  {
    $match: {
      created_at: { $lt: ISODate("2023-01-01") },
      status: { $in: ["FILLED", "CANCELLED", "REJECTED", "EXPIRED"] }
    }
  },
  { $out: "orders_archive" }
])

// Archive old trades
db.trades.aggregate([
  {
    $match: {
      execution_time: { $lt: ISODate("2022-01-01") }
    }
  },
  { $out: "trades_archive" }
])
```

### 7.2 Scheduled Archival Script

```javascript
// Run monthly archival
const archivalJob = async () => {
  const cutoffDate = new Date()
  cutoffDate.setFullYear(cutoffDate.getFullYear() - 1)

  // Archive old trades
  await db.trades.aggregate([
    { $match: { execution_time: { $lt: cutoffDate } } },
    { $merge: { into: "trades_archive" } }
  ])

  // Delete archived from main
  await db.trades.deleteMany({ execution_time: { $lt: cutoffDate } })
}
```

### 7.3 Cold Storage Strategy

```javascript
// Export to S3-compatible storage
db.orders.find({ created_at: { $lt: ISODate("2021-01-01") } })
  .forEach(doc => {
    // Export to cold storage
  })
```

---

## 8. Schema Improvements

### 8.1 Denormalization for Performance

```javascript
// Add frequently accessed fields to orders
{
  order_id: "order_123",
  user_id: "user_123",
  symbol: "RELIANCE",
  exchange: "NSE",
  // Denormalized for quick lookups
  symbol_exchange: "RELIANCE_NSE",
  user_status: "ACTIVE",
  // Embedded for aggregation
  fills: [
    { quantity: 10, price: 2500, time: ISODate("...") }
  ]
}
```

### 8.2 Pre-Aggregation Collections

```javascript
// Daily summary collection
{
  _id: "user_123_2024-01-15",
  user_id: "user_123",
  date: ISODate("2024-01-15"),
  total_orders: 100,
  filled_orders: 80,
  total_pnl: 15000,
  total_brokerage: 500,
  total_taxes: 300,
  trade_count: 50,
  winning_trades: 30,
  losing_trades: 20
}
```

---

## 9. Sharding Recommendations

### 9.1 Shard Key Strategy

```javascript
// Orders - shard by user_id for balanced distribution
sh.shardCollection("trading.orders", { "user_id": 1, "order_id": 1 })

// Trades - shard by user_id + date
sh.shardCollection("trading.trades", { "user_id": 1, "execution_time": 1 })

// Positions - shard by user_id
sh.shardCollection("trading.positions", { "user_id": 1, "position_id": 1 })

// Candles - shard by symbol (hot data on different shards)
sh.shardCollection("trading.candles", { "symbol": 1, "timestamp": 1 })

// Risk events - shard by user_id
sh.shardCollection("trading.risk_events", { "user_id": 1, "timestamp": 1 })

// Audit logs - shard by user_id
sh.shardCollection("trading.audit_logs", { "user_id": 1, "timestamp": 1 })
```

### 9.2 Zone-Based Sharding

```javascript
// Create zones for data locality
sh.addShardToZone("shard_rs1", "hot_data")
sh.addShardToZone("shard_rs2", "cold_data")

// Tag chunks
sh.updateZoneKeyRange(
  "trading.candles",
  { symbol: "A" },
  { symbol: "Z" },
  "hot_data"
)
```

---

## 10. Scaling Recommendations

### 10.1 Read Scaling

```javascript
// Read preference for different use cases
// Nearest for real-time
db.orders.find({}).readPreference("nearest")

// Secondary for analytics
db.orders.aggregate([...]).readPreference("secondary")

// Primary preferred for writes
db.orders.insertOne({}).writeConcern({ w: "majority" })
```

### 10.2 Write Scaling

```javascript
// Bulk operations
const bulkOps = [
  { insertOne: { document: { ... } } },
  { insertOne: { document: { ... } } }
]
db.orders.bulkWrite(bulkOps, { ordered: false })

// Batched writes
const batchSize = 1000
for (let i = 0; i < documents.length; i += batchSize) {
  const batch = documents.slice(i, i + batchSize)
  await db.orders.insertMany(batch)
}
```

### 10.3 Connection Pooling

```javascript
// MongoClient options
const client = new MongoClient(uri, {
  maxPoolSize: 100,
  minPoolSize: 10,
  maxIdleTimeMS: 30000,
  connectTimeoutMS: 10000,
  socketTimeoutMS: 45000
})
```

---

## 11. Production Checklist

### 11.1 Security

```javascript
// Enable authentication
db.auth("admin", "password")

// Create user roles
db.createUser({
  user: "trading_app",
  pwd: "secure_password",
  roles: [
    { role: "readWrite", db: "trading" },
    { role: "dbAdmin", db: "trading" }
  ]
})

// Enable TLS
mongod --tlsMode requireTLS --tlsCertificateKeyFile server.pem
```

### 11.2 Monitoring

```javascript
// Set up profiling
db.setProfilingLevel(1, { slowms: 100 })

// Check current operations
db.currentOp()

// Check index usage
db.orders.aggregate([{ $indexStats: {} }])
```

### 11.3 Backup Strategy

```javascript
// Daily backup script
// mongodump --host primary --out /backup/$(date +%Y-%m-%d)

// Point-in-time recovery
// mongodump --host primary --out /backup/pii --query '{ "timestamp": { $gt: ISODate("...") } }'
```

### 11.4 Performance Tuning

```javascript
// Enable compression
mongod --wiredTigerDirectoryForIndexes

// Set cache size
mongod --wiredTigerCacheSizeGB 64

// Optimize query plans
db.orders.find({}).explain("executionStats")
```

### 11.5 Health Checks

```javascript
// Replica set status
rs.status()

// Check chunk distribution
db.chunks.find({ ns: "trading.orders" }).count()

// Index sizes
db.orders.getIndexes().forEach(idx => {
  print(idx.name, db.orders.stats().indexSizes[idx.name])
})
```

---

## 12. Summary

| Collection | Indexes | TTL | Shard Key | Priority |
|------------|---------|-----|-----------|----------|
| orders | 8 | 180 days | user_id | HIGH |
| trades | 8 | 365 days | user_id + date | HIGH |
| positions | 6 | 90 days (closed) | user_id | HIGH |
| candles | 3 | 2 years | symbol | MEDIUM |
| users | 4 | - | - | HIGH |
| strategies | 3 | - | user_id | MEDIUM |
| risk_events | 5 | 2 years | user_id | HIGH |
| audit_logs | 5 | 7 years | user_id | HIGH |

Run the index commands in production with background: true to avoid locking.