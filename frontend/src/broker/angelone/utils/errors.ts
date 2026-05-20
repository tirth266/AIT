export class BrokerError extends Error {
  constructor(message: string, public code?: string) {
    super(message);
    this.name = 'BrokerError';
  }
}

export class BrokerDisconnectedError extends BrokerError {
  constructor(message = 'Broker disconnected') {
    super(message, 'DISCONNECTED');
    this.name = 'BrokerDisconnectedError';
  }
}

export class TokenExpiredError extends BrokerError {
  constructor(message = 'Broker token expired') {
    super(message, 'TOKEN_EXPIRED');
    this.name = 'TokenExpiredError';
  }
}

export class RateLimitError extends BrokerError {
  constructor(message = 'API rate limit exceeded') {
    super(message, 'RATE_LIMIT');
    this.name = 'RateLimitError';
  }
}

export class OrderRejectedError extends BrokerError {
  constructor(message = 'Order was rejected by the broker', public reason?: string) {
    super(message, 'ORDER_REJECTED');
    this.name = 'OrderRejectedError';
  }
}

export class WebSocketReconnectError extends BrokerError {
  constructor(message = 'Failed to reconnect to WebSocket') {
    super(message, 'WS_RECONNECT_FAILED');
    this.name = 'WebSocketReconnectError';
  }
}
