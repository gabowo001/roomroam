from quart import websocket
from quart_auth import current_user, login_required
from quart import current_app
import json
import utils
from models import User


async def get_authenticated_user():
    """Helper function to get the authenticated user from database"""
    try:
        if await current_user.is_authenticated:
            auth_id = current_user.auth_id
            return current_app.db_session.query(User).filter_by(id=int(auth_id)).first()
    except:
        pass
    return None


@login_required
async def ws():
    """WebSocket endpoint for real-time message updates"""
    ws_connection = websocket._get_current_object()
    utils.websockets.add(ws_connection)
    
    try:
        # Send all existing messages to the newly connected client
        for message in current_app.messages:
            await ws_connection.send(json.dumps({'type': 'message', 'data': message}))
        
        # Keep the connection alive
        while True:
            # We don't expect to receive messages from clients through WebSocket
            # Just keep the connection alive to send new messages
            await ws_connection.receive()
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        utils.websockets.discard(ws_connection)
