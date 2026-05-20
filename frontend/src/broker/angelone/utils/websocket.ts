import { tokenUtils } from './token';
import { WebsocketTick } from '../types';
import { WebSocketReconnectError, BrokerDisconnectedError } from './errors';

type MessageHandler = (data: WebsocketTick) => void;

export class AngelWebSocket {
  private ws: WebSocket | null = null;
  private url: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectInterval = 3000; // ms
  private handlers: Set<MessageHandler> = new Set();
  private isConnecting = false;

  constructor(url: string = import.meta.env.VITE_ANGEL_WS_URL || 'ws://localhost:8000/api/v1/broker/angelone/ws') {
    this.url = url;
  }

  connect(): Promise<void> {
    if (this.ws?.readyState === WebSocket.OPEN) return Promise.resolve();
    if (this.isConnecting) return Promise.resolve(); // Or wait for connection

    this.isConnecting = true;

    return new Promise((resolve, reject) => {
      try {
        const feedToken = tokenUtils.getTokens()?.feedToken;
        // In a real proxy scenario, authentication might happen via headers or initial payload
        // For standard websockets in browser, we might pass token in URL or send it after connection
        const wsUrl = `${this.url}?token=${feedToken || ''}`;
        
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
          this.isConnecting = false;
          this.reconnectAttempts = 0;
          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            // Some brokers send binary data, assuming JSON proxy for frontend here
            const data: WebsocketTick = JSON.parse(event.data);
            this.notifyHandlers(data);
          } catch (e) {
            console.error('Error parsing WS message', e);
          }
        };

        this.ws.onclose = (event) => {
          this.isConnecting = false;
          this.ws = null;
          if (event.code !== 1000 && event.code !== 1005) {
            this.handleReconnect();
          }
        };

        this.ws.onerror = (error) => {
          this.isConnecting = false;
          console.error('WebSocket Error', error);
          if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            reject(new BrokerDisconnectedError('WebSocket connection failed'));
          }
        };
      } catch (e) {
        this.isConnecting = false;
        reject(new BrokerDisconnectedError('Failed to initialize WebSocket'));
      }
    });
  }

  private handleReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      setTimeout(() => {
        this.connect().catch(() => {
          if (this.reconnectAttempts >= this.maxReconnectAttempts) {
             console.error(new WebSocketReconnectError());
          }
        });
      }, this.reconnectInterval);
    } else {
      console.error(new WebSocketReconnectError('Max reconnect attempts reached.'));
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close(1000, 'Normal Closure');
      this.ws = null;
    }
  }

  send(data: any) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    } else {
      console.warn('WebSocket is not open. Message not sent.');
    }
  }

  subscribeToTicks(tokens: string[], mode: number = 1, exchangeType: number = 1) {
    this.send({
      action: 'subscribe',
      params: {
        mode,
        tokenList: [
          { exchangeType, tokens }
        ]
      }
    });
  }

  unsubscribeFromTicks(tokens: string[], mode: number = 1, exchangeType: number = 1) {
    this.send({
      action: 'unsubscribe',
      params: {
        mode,
        tokenList: [
          { exchangeType, tokens }
        ]
      }
    });
  }

  onMessage(handler: MessageHandler) {
    this.handlers.add(handler);
  }

  offMessage(handler: MessageHandler) {
    this.handlers.delete(handler);
  }

  private notifyHandlers(data: WebsocketTick) {
    this.handlers.forEach(handler => handler(data));
  }
}

export const angelWS = new AngelWebSocket();
