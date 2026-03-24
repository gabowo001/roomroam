import { Message, WebSocketMessage } from '../types/message';

export class WebSocketManager {
  private ws: WebSocket | null = null;
  private reconnectTimeout: number | null = null;
  private messageCallback: ((message: Message) => void) | null = null;
  private statusCallback: ((connected: boolean) => void) | null = null;

  constructor() {
    this.setupWebSocket();
  }

  public onMessage(callback: (message: Message) => void): void {
    this.messageCallback = callback;
  }

  public onStatusChange(callback: (connected: boolean) => void): void {
    this.statusCallback = callback;
  }

  private setupWebSocket(): void {
    // Determine the WebSocket URL based on current location
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.hostname}:5000/ws`;
    
    try {
      this.ws = new WebSocket(wsUrl);
      
      this.ws.onopen = () => {
        console.log('WebSocket connected');
        this.statusCallback?.(true);
        
        // Clear any existing reconnect timeout
        if (this.reconnectTimeout) {
          clearTimeout(this.reconnectTimeout);
          this.reconnectTimeout = null;
        }
      };
      
      this.ws.onmessage = (event) => {
        const message: WebSocketMessage = JSON.parse(event.data);
        if (message.type === 'message' && this.messageCallback) {
          this.messageCallback(message.data);
        }
      };
      
      this.ws.onclose = () => {
        console.log('WebSocket disconnected');
        this.statusCallback?.(false);
        
        // Attempt to reconnect after 3 seconds if still authenticated
        this.reconnectTimeout = window.setTimeout(() => {
          this.setupWebSocket();
        }, 3000);
      };
      
      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        this.statusCallback?.(false);
      };
    } catch (error) {
      console.error('Error creating WebSocket connection:', error);
      this.statusCallback?.(false);
    }
  }

  public disconnect(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  public isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}
