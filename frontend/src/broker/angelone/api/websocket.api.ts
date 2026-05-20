import { angelWS } from '../utils/websocket';

export const websocketApi = {
  connect: () => angelWS.connect(),
  disconnect: () => angelWS.disconnect(),
  subscribe: (tokens: string[], mode?: number, exchangeType?: number) => angelWS.subscribeToTicks(tokens, mode, exchangeType),
  unsubscribe: (tokens: string[], mode?: number, exchangeType?: number) => angelWS.unsubscribeFromTicks(tokens, mode, exchangeType),
  onTick: (handler: (data: any) => void) => {
    angelWS.onMessage(handler);
    return () => angelWS.offMessage(handler);
  }
};
