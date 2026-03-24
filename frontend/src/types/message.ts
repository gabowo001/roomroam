export interface Message {
  text: string;
  username: string;
  timestamp: string;
  id: number;
}

export interface WebSocketMessage {
  type: string;
  data: Message;
}
