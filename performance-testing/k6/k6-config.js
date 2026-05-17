// k6 Configuration File
// Usage: k6 run -e ENV=production k6-config.js

import http from 'k6/http';
import ws from 'k6/ws';
import { check, sleep } from 'k6';

export const options = {
  scenarios: {
    // Cross-browser smoke test
    smoke: {
      executor: 'constant-vus',
      vus: 5,
      duration: '1m',
      tags: { test_type: 'smoke' },
      logLevel: 'info'
    },

    // Load test - steady increase
    load: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '2m', target: 50 },
        { duration: '5m', target: 50 },
        { duration: '2m', target: 100 },
        { duration: '5m', target: 100 },
        { duration: '2m', target: 200 },
        { duration: '5m', target: 200 },
        { duration: '2m', target: 0 }
      ],
      tags: { test_type: 'load' }
    },

    // Stress test - aggressive
    stress: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '30s', target: 100 },
        { duration: '1m', target: 300 },
        { duration: '2m', target: 500 },
        { duration: '2m', target: 1000 },
        { duration: '5m', target: 1000 },
        { duration: '1m', target: 0 }
      ],
      tags: { test_type: 'stress' }
    },

    // Spike test - sudden burst
    spike: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '10s', target: 50 },
        { duration: '30s', target: 1000 },
        { duration: '1m', target: 1000 },
        { duration: '30s', target: 50 },
        { duration: '10s', target: 0 }
      ],
      tags: { test_type: 'spike' }
    },

    // Soak test - long duration
    soak: {
      executor: 'constant-vus',
      vus: 150,
      duration: '60m',
      tags: { test_type: 'soak' }
    },

    // Breakpoint test - find capacity
    breakpoint: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '5m', target: 100 },
        { duration: '5m', target: 200 },
        { duration: '5m', target: 400 },
        { duration: '5m', target: 800 },
        { duration: '5m', target: 1000 },
        { duration: '5m', target: 1500 },
        { duration: '5m', target: 2000 },
        { duration: '2m', target: 0 }
      ],
      tags: { test_type: 'breakpoint' }
    }
  },

  // Global thresholds
  thresholds: {
    http_req_duration: [
      'p(95)<500',
      'p(99)<1000'
    ],
    http_req_failed: [
      'rate<0.01'
    ],
    ws_messages: [
      'count>100'
    ]
  }
};

export default function() {
  const baseUrl = __ENV.BASE_URL || 'http://localhost:3000/api';
  const wsUrl = __ENV.WS_URL || 'ws://localhost:8080/ws';

  // HTTP Tests
  // ...

  // WebSocket Tests
  // ...
}