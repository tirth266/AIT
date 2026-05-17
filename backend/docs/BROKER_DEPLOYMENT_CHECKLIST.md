# Production Deployment Checklist - Zerodha Kite Connect Integration

## Pre-Deployment Requirements

### 1. Credentials & Security
- [ ] Generate Zerodha API key from https://developers.kite.trade/
- [ ] Generate API secret (keep secure, never commit to repo)
- [ ] Configure redirect URI (must be HTTPS in production)
- [ ] Store credentials securely in environment variables:
  ```
  KITE_API_KEY=your_api_key
  KITE_API_SECRET=your_api_secret
  KITE_REDIRECT_URI=https://your-domain.com/callback
  KITE_ACCESS_TOKEN=your_access_token (after login)
  KITE_REFRESH_TOKEN=your_refresh_token
  ```
- [ ] Set ENCRYPTION_KEY for credential encryption

### 2. Environment Configuration
- [ ] Set `TRADING_MODE=paper` for initial testing
- [ ] Set `ENABLE_LIVE_TRADING=false` initially
- [ ] Configure `REDIS_URL` for rate limiting and sessions
- [ ] Configure `MONGO_URI` for audit logging persistence

### 3. Circuit Breaker Configuration
- [ ] Set `BROKER_CIRCUIT_BREAKER_FAILURE_THRESHOLD=5`
- [ ] Set `BROKER_CIRCUIT_BREAKER_TIMEOUT=30`
- [ ] Test circuit breaker triggers with simulated failures

### 4. Rate Limiting Configuration
- [ ] Set `BROKER_RATE_LIMIT_ORDERS_PER_SECOND=1` (Zerodha limit)
- [ ] Set `BROKER_RATE_LIMIT_ORDERS_PER_MINUTE=60`
- [ ] Verify rate limit handling with load testing

## Sandbox Testing Phase

### 1. Idempotency Testing
- [ ] Test duplicate order prevention
- [ ] Verify idempotency key generation
- [ ] Test retry safety with same idempotency key

### 2. Order Operations
- [ ] Test market order placement
- [ ] Test limit order placement
- [ ] Test stop-loss order placement (SL, SL-M)
- [ ] Test order modification
- [ ] Test order cancellation
- [ ] Test GTT orders

### 3. Portfolio Operations
- [ ] Test position retrieval
- [ ] Test portfolio retrieval
- [ ] Test margin retrieval

### 4. WebSocket Testing
- [ ] Test tick subscription
- [ ] Test tick unsubscription
- [ ] Verify reconnection after disconnect
- [ ] Test tick latency (<100ms target)

### 5. Failure Scenarios
- [ ] Test retry on network timeout
- [ ] Test circuit breaker activation
- [ ] Test rate limit handling
- [ ] Test exchange rejection handling
- [ ] Test authentication failure recovery

## Pre-Live Validation

### 1. Reconciliation
- [ ] Enable automatic reconciliation (every 60 seconds)
- [ ] Verify order state synchronization
- [ ] Verify position state synchronization
- [ ] Test discrepancy detection and alerts

### 2. Audit Logging
- [ ] Verify all order events logged
- [ ] Verify audit persistence to database
- [ ] Test audit retrieval and filtering

### 3. Monitoring Setup
- [ ] Configure alerting for circuit breaker OPEN state
- [ ] Configure alerting for rate limit exceeded
- [ ] Configure alerting for failed orders
- [ ] Set up WebSocket connection monitoring
- [ ] Configure Telegram/email notifications for errors

## Live Trading Activation

### 1. Final Pre-Flight
- [ ] Switch `TRADING_MODE=live`
- [ ] Set `ENABLE_LIVE_TRADING=true`
- [ ] Verify market session detection works
- [ ] Verify trading hours enforcement
- [ ] Test with minimum viable order (1 share)

### 2. Safety Checks
- [ ] Set position size limits
- [ ] Enable daily loss limits
- [ ] Configure max open positions
- [ ] Set trade cooldown periods

### 3. Parallel Paper Mode (Recommended)
- [ ] Enable `ENABLE_PAPER_TRADING=true`
- [ ] Configure `PaperTradingSync` for parallel execution
- [ ] Compare paper vs live performance daily

## Post-Deployment Monitoring

### 1. First Hour
- [ ] Monitor order placement latency
- [ ] Verify WebSocket connection stability
- [ ] Check audit logs for any errors

### 2. First Day
- [ ] Review all filled orders
- [ ] Verify P&L calculations
- [ ] Check reconciliation status
- [ ] Review circuit breaker stats

### 3. First Week
- [ ] Analyze trade success rate
- [ ] Review rate limit usage
- [ ] Check audit log for patterns
- [ ] Validate backup and recovery procedures

## Rollback Procedures

### If Issues Detected:
1. Set `ENABLE_LIVE_TRADING=false` immediately
2. Switch to `TRADING_MODE=paper`
3. Review audit logs to identify root cause
4. Fix issues in non-production environment
5. Re-test all scenarios in sandbox
6. Re-deploy with fixes

### Emergency Contacts:
- Zerodha API Support: https://kite.trade/connect
- Emergency disable live trading via environment variable

## Performance Targets

| Metric | Target |
|--------|--------|
| Order Placement Latency | <500ms |
| WebSocket Tick Latency | <100ms |
| Order Fill Confirmation | <1s |
| Circuit Breaker Response | <30s |
| Reconnection Time | <60s |

## Security Checklist

- [ ] Never commit API keys/secrets to git
- [ ] Use environment variables for all credentials
- [ ] Enable HTTPS for redirect URI in production
- [ ] Rotate access tokens regularly
- [ ] Enable audit logging for all operations
- [ ] Set up IP whitelisting on Zerodha console
- [ ] Enable 2FA on Zerodha account