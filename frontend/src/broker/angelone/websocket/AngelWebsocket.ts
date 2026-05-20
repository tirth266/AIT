import { AngelTick, AngelWebsocketRequest } from '../types';
import { tokenUtils } from '../utils/token';

export class AngelWebsocketManager {
  private ws: WebSocket | null = null;
  private url: string;
  private onTick: (tick: AngelTick) => void;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private heartbeatInterval: any;

  constructor(onTick: (tick: AngelTick) => void) {
    this.url = import.meta.env.VITE_ANGEL_WS_URL || 'wss://smartapisocket.angelone.in/smart-api-websocket';
    this.onTick = onTick;
  }

  connect() {
    const jwtToken = tokenUtils.getJwtToken();
    const feedToken = tokenUtils.getFeedToken();
    const clientCode = 'TIRTH'; // This should ideally come from profile store

    if (!jwtToken || !feedToken) {
      console.error('Missing tokens for Angel One WebSocket');
      return;
    }

    const fullUrl = `${this.url}?jwttoken=${jwtToken}&clientcode=${clientCode}&feedtoken=${feedToken}`;
    
    this.ws = new WebSocket(fullUrl);

    this.ws.onopen = () => {
      console.log('Angel One WebSocket connected');
      this.reconnectAttempts = 0;
      this.startHeartbeat();
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.t === 'tf') { // tick data
          this.onTick(data);
        }
      } catch (e) {
        // Handle binary or malformed data
      }
    };

    this.ws.onclose = () => {
      console.log('Angel One WebSocket closed');
      this.stopHeartbeat();
      this.attemptReconnect();
    };

    this.ws.onerror = (error) => {
      console.error('Angel One WebSocket error', error);
    };
  }

  private attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      setTimeout(() => this.connect(), 5000);
    }
  }

  private startHeartbeat() {
    this.heartbeatInterval = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send('ping');
      }
    }, 30000);
  }

  private stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
    }
  }

  subscribe(tokens: Array<{ exchangeType: number; tokens: string[] }>) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      const request: AngelWebsocketRequest = {
        action: 'subscribe',
        params: {
          mode: 1, // LTP
          tokenList: tokens
        }
      };
      this.ws.send(JSON.stringify(request));
    }
  }

  disconnect() {
    this.stopHeartbeat();
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}
