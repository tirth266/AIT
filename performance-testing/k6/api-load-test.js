// k6 Load Testing Scripts for Trading Platform
// Run with: k6 run api-load-test.js

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Custom metrics
const apiLatency = new Trend('api_latency_ms');
const orderLatency = new Trend('order_latency_ms');
const marketDataLatency = new Trend('market_data_latency_ms');
const errorRate = new Counter('errors');
const orderSuccessRate = new Rate('order_success_rate');

// Configuration
export const options = {
  scenarios: {
    // Smoke test
    smoke: {
      executor: 'constant-vus',
      vus: 10,
      duration: '30s',
      tags: { test_type: 'smoke' }
    },
    // Load test
    load: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '2m', target: 100 },
        { duration: '5m', target: 100 },
        { duration: '2m', target: 200 },
        { duration: '5m', target: 200 },
        { duration: '2m', target: 0 }
      ],
      tags: { test_type: 'load' }
    },
    // Stress test
    stress: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '2m', target: 500 },
        { duration: '5m', target: 500 },
        { duration: '2m', target: 1000 },
        { duration: '5m', target: 1000 },
        { duration: '2m', target: 0 }
      ],
      tags: { test_type: 'stress' }
    },
    // Spike test
    spike: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '10s', target: 100 },
        { duration: '30s', target: 1000 },
        { duration: '1m', target: 1000 },
        { duration: '10s', target: 100 },
        { duration: '10s', target: 0 }
      ],
      tags: { test_type: 'spike' }
    },
    // Soak test
    soak: {
      executor: 'constant-vus',
      vus: 200,
      duration: '60m',
      tags: { test_type: 'soak' }
    }
  },
  thresholds: {
    'http_req_duration': ['p(95)<500', 'p(99)<1000'],
    'api_latency_ms': ['p(95)<100', 'p(99)<200'],
    'order_latency_ms': ['p(95)<100', 'p(99)<200'],
    'market_data_latency_ms': ['p(95)<50', 'p(99)<100'],
    'order_success_rate': ['rate>0.99'],
    'errors': ['count<100']
  }
};

// Test data
const BASE_URL = __ENV.BASE_URL || 'http://localhost:3000/api';
const SYMBOLS = [
  'RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK',
  'SBIN', 'BHARTIARTL', 'ITC', 'L&T', 'MARUTI'
];

const AUTH_TOKEN = __ENV.AUTH_TOKEN || 'test-token-123';

// Headers
const getHeaders = () => ({
  'Content-Type': 'application/json',
  'Authorization': `Bearer ${AUTH_TOKEN}`,
  'X-Client-ID': `k6-${__VU}`
});

// Authentication
export function setup() {
  const loginRes = http.post(
    `${BASE_URL}/auth/login`,
    JSON.stringify({
      username: `user_${__VU}`,
      password: 'test_password_123'
    }),
    { headers: getHeaders() }
  );

  if (loginRes.status === 200) {
    const data = JSON.parse(loginRes.body);
    return { token: data.token, session_id: data.session_id };
  }
  return { token: AUTH_TOKEN, session_id: `session-${__VU}` };
}

// Main test scenarios
export default function(data) {
  const headers = {
    ...getHeaders(),
    'X-Session-ID': data.session_id
  };

  group('Market Data Operations', () => {
    // Get market quote
    const symbol = SYMBOLS[Math.floor(Math.random() * SYMBOLS.length)];
    const quoteRes = http.get(
      `${BASE_URL}/market/${symbol}`,
      { headers }
    );
    check(quoteRes, {
      'quote status 200': (r) => r.status === 200,
      'quote has price': (r) => JSON.parse(r.body).price !== undefined
    });
    marketDataLatency.add(quoteRes.timings.duration);

    // Get order book
    const orderBookRes = http.get(
      `${BASE_URL}/market/${symbol}/orderbook`,
      { headers }
    );
    check(orderBookRes, {
      'orderbook status 200': (r) => r.status === 200
    });
    apiLatency.add(orderBookRes.timings.duration);

    // Get multiple quotes
    const symbols = SYMBOLS.slice(0, 5).join(',');
    const batchRes = http.get(
      `${BASE_URL}/market/batch?symbols=${symbols}`,
      { headers }
    );
    check(batchRes, {
      'batch status 200': (r) => r.status === 200
    });
    apiLatency.add(batchRes.timings.duration);
  });

  group('Order Operations', () => {
    // Place market order
    const symbol = SYMBOLS[Math.floor(Math.random() * SYMBOLS.length)];
    const side = Math.random() > 0.5 ? 'BUY' : 'SELL';
    const quantity = Math.floor(Math.random() * 100) + 1;

    const orderRes = http.post(
      `${BASE_URL}/orders`,
      JSON.stringify({
        symbol,
        quantity,
        order_type: 'MARKET',
        side
      }),
      { headers }
    );

    const orderSuccess = orderRes.status === 200 || orderRes.status === 201;
    check(orderRes, {
      'order created': () => orderSuccess,
      'order has ID': (r) => orderSuccess && JSON.parse(r.body).order_id !== undefined
    });
    orderSuccessRate.add(orderSuccess ? 1 : 0);
    orderLatency.add(orderRes.timings.duration);

    if (!orderSuccess) {
      errorRate.add(1);
    }

    // Place limit order
    const limitRes = http.post(
      `${BASE_URL}/orders`,
      JSON.stringify({
        symbol,
        quantity: Math.floor(Math.random() * 50) + 1,
        order_type: 'LIMIT',
        side,
        price: Math.random() * 5000 + 100
      }),
      { headers }
    );
    check(limitRes, {
      'limit order created': (r) => r.status === 201
    });

    // Get orders
    const ordersRes = http.get(
      `${BASE_URL}/orders`,
      { headers }
    );
    check(ordersRes, {
      'get orders success': (r) => r.status === 200
    });
    apiLatency.add(ordersRes.timings.duration);

    // Cancel order if exists
    const orderData = JSON.parse(ordersRes.body);
    if (orderData.orders && orderData.orders.length > 0) {
      const orderId = orderData.orders[0].order_id;
      const cancelRes = http.delete(
        `${BASE_URL}/orders/${orderId}`,
        { headers }
      );
      check(cancelRes, {
        'order cancelled': (r) => r.status === 200 || r.status === 204
      });
    }
  });

  group('Portfolio Operations', () => {
    // Get positions
    const positionsRes = http.get(
      `${BASE_URL}/positions`,
      { headers }
    );
    check(positionsRes, {
      'positions status 200': (r) => r.status === 200
    });
    apiLatency.add(positionsRes.timings.duration);

    // Get portfolio
    const portfolioRes = http.get(
      `${BASE_URL}/portfolio`,
      { headers }
    );
    check(portfolioRes, {
      'portfolio status 200': (r) => r.status === 200
    });
    apiLatency.add(portfolioRes.timings.duration);

    // Get holdings
    const holdingsRes = http.get(
      `${BASE_URL}/holdings`,
      { headers }
    );
    check(holdingsRes, {
      'holdings status 200': (r) => r.status === 200
    });
  });

  group('Historical Data', () => {
    const symbol = SYMBOLS[Math.floor(Math.random() * SYMBOLS.length)];

    // 1-minute candles
    const m1Res = http.get(
      `${BASE_URL}/market/${symbol}/history?interval=1m&limit=100`,
      { headers }
    );
    check(m1Res, {
      'm1 history success': (r) => r.status === 200
    });
    apiLatency.add(m1Res.timings.duration);

    // 5-minute candles
    const m5Res = http.get(
      `${BASE_URL}/market/${symbol}/history?interval=5m&limit=100`,
      { headers }
    );
    check(m5Res, {
      'm5 history success': (r) => r.status === 200
    });

    // Daily candles
    const d1Res = http.get(
      `${BASE_URL}/market/${symbol}/history?interval=1d&limit=30`,
      { headers }
    );
    check(d1Res, {
      'd1 history success': (r) => r.status === 200
    });
  });

  group('Watchlist Operations', () => {
    // Get watchlist
    const watchlistRes = http.get(
      `${BASE_URL}/watchlist`,
      { headers }
    );
    check(watchlistRes, {
      'watchlist status 200': (r) => r.status === 200
    });

    // Update watchlist
    const updateRes = http.put(
      `${BASE_URL}/watchlist`,
      JSON.stringify({
        symbols: SYMBOLS.slice(0, 5)
      }),
      { headers }
    );
    check(updateRes, {
      'watchlist updated': (r) => r.status === 200
    });
  });

  sleep(Math.random() * 2 + 0.5);
}

// Handle test teardown
export function handleSummary(data) {
  return {
    stdout: textSummary(data, { indent: ' ', enableColors: true }),
    'summary.json': JSON.stringify(data)
  };
}

function textSummary(data, opts) {
  const indent = opts.indent || '';
  let output = `${indent}Test Summary:\n`;

  if (data.metrics.http_req_duration) {
    const duration = data.metrics.http_req_duration;
    output += `${indent}  HTTP Request Duration:\n`;
    output += `${indent}    Avg: ${duration.values.avg.toFixed(2)}ms\n`;
    output += `${indent}    P95: ${duration.values['p(95)'].toFixed(2)}ms\n`;
    output += `${indent}    P99: ${duration.values['p(99)'].toFixed(2)}ms\n`;
    output += `${indent}    Max: ${duration.values.max.toFixed(2)}ms\n`;
  }

  if (data.metrics.order_latency_ms) {
    const latency = data.metrics.order_latency_ms;
    output += `${indent}  Order Latency:\n`;
    output += `${indent}    Avg: ${latency.values.avg.toFixed(2)}ms\n`;
    output += `${indent}    P95: ${latency.values['p(95)'].toFixed(2)}ms\n`;
    output += `${indent}    P99: ${latency.values['p(99)'].toFixed(2)}ms\n`;
  }

  return output;
}