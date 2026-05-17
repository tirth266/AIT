// k6 WebSocket Load Testing Script
// Run with: k6 run websocket-load-test.js

import ws from 'k6/ws';
import { check, sleep } from 'k6/metrics';
import { Counter, Trend, Gauge } from 'k6/metrics';

// Custom metrics
const wsMessages = new Counter('ws_messages_total');
const wsLatency = new Trend('ws_latency_ms');
const wsErrors = new Counter('ws_errors');
const connectedClients = new Gauge('ws_connected_clients');
const tickThroughput = new Trend('tick_throughput');

// Configuration
export const options = {
  scenarios: {
    // Basic WebSocket test
    basic_ws: {
      executor: 'constant-vus',
      vus: 100,
      duration: '30s',
      tags: { test_type: 'basic' }
    },
    // High concurrency test
    high_concurrency: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '1m', target: 500 },
        { duration: '2m', target: 500 },
        { duration: '1m', target: 1000 },
        { duration: '2m', target: 1000 },
        { duration: '1m', target: 0 }
      ],
      tags: { test_type: 'high_concurrency' }
    },
    // Message throughput test
    throughput: {
      executor: 'constant-vus',
      vus: 200,
      duration: '5m',
      tags: { test_type: 'throughput' }
    }
  },
  thresholds: {
    'ws_latency_ms': ['p(95)<20', 'p(99)<50'],
    'ws_errors': ['count<50'],
    'tick_throughput': ['p(95)>1000']
  }
};

const WS_URL = __ENV.WS_URL || 'ws://localhost:8080/ws';
const SYMBOLS = [
  'RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK',
  'SBIN', 'BHARTIARTL', 'ITC', 'L&T', 'MARUTI'
];

export default function() {
  const clientId = `k6-${__VU}-${__ITER}`;
  let wsocket = null;
  let isConnected = false;
  let messageCount = 0;
  let lastMessageTime = 0;

  const url = `${WS_URL}?client_id=${clientId}&token=${__ENV.AUTH_TOKEN || 'test-token'}`;

  wsocket = new WebSocket(url);

  wsocket.onopen = () => {
    isConnected = true;
    connectedClients.add(1);

    // Subscribe to random symbols
    const symbolsToSubscribe = __VU % 10;
    for (let i = 0; i < symbolsToSubscribe; i++) {
      const symbol = SYMBOLS[Math.floor(Math.random() * SYMBOLS.length)];
      wsocket.send(JSON.stringify({
        type: 'subscribe',
        symbol: symbol
      }));
    }
  };

  wsocket.onmessage = (msg) => {
    const now = Date.now();
    if (lastMessageTime > 0) {
      const latency = now - lastMessageTime;
      wsLatency.add(latency);
    }
    lastMessageTime = now;

    try {
      const data = JSON.parse(msg.data);
      if (data.type === 'tick') {
        tickThroughput.add(1);
      }
      wsMessages.add(1);
      messageCount++;
    } catch (e) {
      // Handle non-JSON messages
      wsMessages.add(1);
      messageCount++;
    }
  };

  wsocket.onerror = (err) => {
    wsErrors.add(1);
  };

  wsocket.onclose = () => {
    isConnected = false;
    connectedClients.add(-1);
  };

  // Send messages for the duration
  const duration = 30;
  const startTime = Date.now();

  while (Date.now() - startTime < duration * 1000 && isConnected) {
    // Request market data
    const symbol = SYMBOLS[Math.floor(Math.random() * SYMBOLS.length)];
    wsocket.send(JSON.stringify({
      type: 'market_data_request',
      symbol: symbol,
      request_id: `req-${Date.now()}`
    }));

    // Place order occasionally
    if (Math.random() < 0.1) {
      wsocket.send(JSON.stringify({
        type: 'order',
        order_id: `ord-${Date.now()}`,
        symbol: symbol,
        quantity: Math.floor(Math.random() * 100) + 1,
        side: Math.random() > 0.5 ? 'BUY' : 'SELL',
        order_type: 'MARKET'
      }));
    }

    sleep(Math.random() * 0.5 + 0.1);
  }

  if (wsocket) {
    wsocket.close();
  }

  check(isConnected, {
    'connected': () => isConnected,
    'messages received': () => messageCount > 0
  });
}