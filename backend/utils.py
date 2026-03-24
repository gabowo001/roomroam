from quart import websocket
import json

# In-memory storage for WebSocket connections
websockets = set()


async def broadcast_message(message):
    """Broadcast a message to all connected WebSocket clients"""
    if websockets:
        message_data = json.dumps({'type': 'message', 'data': message})
        disconnected = set()
        for ws in websockets.copy():
            try:
                await ws.send(message_data)
            except Exception:
                disconnected.add(ws)
        
        # Remove disconnected websockets
        websockets.difference_update(disconnected)
