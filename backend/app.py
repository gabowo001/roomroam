from quart import Quart, jsonify, request, websocket
from quart_auth import QuartAuth, login_user, logout_user, current_user, login_required
from quart_cors import cors
import os
import json
from datetime import datetime
from models import get_db_session, init_db, User, Group, Message
from sqlalchemy import func
import random
from dotenv import load_dotenv

load_dotenv()

# Create Quart app
app = Quart(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app = cors(app, allow_origin="*")

# Configuration for development (allow insecure cookies over plain HTTP)
app.config['QUART_AUTH_COOKIE_SECURE'] = False
app.config['QUART_AUTH_COOKIE_SAMESITE'] = 'Lax'

# Initialize auth manager
auth_manager = QuartAuth(app)

@app.before_request
async def log_request():
    print(f"[{datetime.now()}] Request: {request.method} {request.path}")
    print(f"  Headers: {dict(request.headers)}")
    print(f"  Cookies: {request.cookies}")

# In-memory storage for WebSocket connections grouped by group_id
# Structure: {group_id: {ws_connection1, ws_connection2, ...}}
websockets_by_group = {}


async def get_authenticated_user():
    """Helper function to get the authenticated user from database"""
    try:
        if await current_user.is_authenticated:
            auth_id = current_user.auth_id
            return app.db_session.query(User).filter_by(id=int(auth_id)).first()
    except:
        pass
    return None


async def broadcast_message(group_id, message):
    """Broadcast a message to all connected WebSocket clients in a specific group"""
    if group_id in websockets_by_group and websockets_by_group[group_id]:
        message_data = json.dumps({'type': 'message', 'data': message})
        disconnected = set()
        for ws in websockets_by_group[group_id].copy():
            try:
                await ws.send(message_data)
            except Exception:
                disconnected.add(ws)

        # Remove disconnected websockets
        websockets_by_group[group_id].difference_update(disconnected)


@app.before_serving
async def startup():
    """Initialize database connection before serving requests"""
    app.db_session = get_db_session()
    init_db()


@app.after_serving
async def cleanup():
    """Clean up database connection after serving requests"""
    app.db_session.close()


# ==================== AUTH ENDPOINTS ====================

@app.route('/api/test', methods=['GET'])
async def test():
    """Simple test endpoint"""
    return jsonify({'success': True, 'message': 'Server is working!'})

@app.route('/api/register', methods=['POST'])
async def register():
    """Register a new user"""
    try:
        data = await request.get_json()
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({'success': False, 'error': 'Username and password are required'}), 400

        # Check if user already exists
        existing_user = User.get_user_by_username(username, app.db_session)
        if existing_user:
            return jsonify({'success': False, 'error': 'Username already exists'}), 400

        # Create new user
        user = User(username=username)
        user.set_password(password)

        app.db_session.add(user)
        app.db_session.commit()

        return jsonify({'success': True, 'message': 'User registered successfully'})
    except Exception as e:
        import sys
        import traceback
        sys.stderr.write(f"\n\n=== REGISTRATION ERROR ===\n")
        sys.stderr.write(f"Error: {str(e)}\n")
        traceback.print_exc(file=sys.stderr)
        sys.stderr.write("=== END ERROR ===\n\n")
        sys.stderr.flush()
        app.db_session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/login', methods=['POST'])
async def login():
    """Login a user"""
    data = await request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'success': False, 'error': 'Username and password are required'}), 400

    user = User.get_user_by_username(username, app.db_session)
    if user and user.check_password(password):
        login_user(user, remember=True)
        return jsonify({
            'success': True,
            'message': 'Login successful',
            'user': {'id': user.id, 'username': user.username}
        })

    return jsonify({'success': False, 'error': 'Invalid username or password'}), 401


@app.route('/api/logout', methods=['POST'])
@login_required
async def logout():
    """Logout the current user"""
    logout_user()
    return jsonify({'success': True, 'message': 'Logged out successfully'})


# ==================== GROUP ENDPOINTS ====================

@app.route('/api/groups/random', methods=['GET'])
@login_required
async def get_random_group():
    """Get or create a random group for the user to join"""
    user = await get_authenticated_user()
    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 401

    # Get all existing groups
    all_groups = app.db_session.query(Group).all()

    # If no groups exist, create a few random groups
    if not all_groups:
        group_names = [
            "Grupo 1", "Grupo 2", "Grupo de Noobs", "Grupo de Pobres",
            "Grupo Elite", "Grupo Random", "Grupo Chido", "Grupo Vintage"
        ]
        for name in group_names:
            group = Group(name=name)
            app.db_session.add(group)
        app.db_session.commit()
        all_groups = app.db_session.query(Group).all()

    # Select a random group
    selected_group = random.choice(all_groups)

    # Update user's current group
    user.current_group_id = selected_group.id
    app.db_session.commit()

    return jsonify({
        'success': True,
        'group': {
            'id': selected_group.id,
            'name': selected_group.name,
            'created_at': selected_group.created_at.isoformat()
        }
    })


@app.route('/api/groups/join/<int:group_id>', methods=['POST'])
@login_required
async def join_group(group_id):
    """Join a specific group"""
    user = await get_authenticated_user()
    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 401

    # Check if group exists
    group = app.db_session.query(Group).filter_by(id=group_id).first()
    if not group:
        return jsonify({'success': False, 'error': 'Group not found'}), 404

    # Update user's current group
    user.current_group_id = group_id
    app.db_session.commit()

    return jsonify({
        'success': True,
        'group': {
            'id': group.id,
            'name': group.name,
            'created_at': group.created_at.isoformat()
        }
    })


@app.route('/api/groups/leave', methods=['POST'])
@login_required
async def leave_group():
    """Leave the current group and optionally join a random one"""
    user = await get_authenticated_user()
    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 401

    data = await request.get_json()
    join_new = data.get('join_new', True)

    # Clear current group
    user.current_group_id = None
    app.db_session.commit()

    response_data = {'success': True, 'message': 'Left group successfully'}

    # If requested, join a random new group
    if join_new:
        all_groups = app.db_session.query(Group).all()
        if all_groups:
            new_group = random.choice(all_groups)
            user.current_group_id = new_group.id
            app.db_session.commit()
            response_data['new_group'] = {
                'id': new_group.id,
                'name': new_group.name,
                'created_at': new_group.created_at.isoformat()
            }

    return jsonify(response_data)


@app.route('/api/groups/like', methods=['POST'])
@login_required
async def like_group():
    """Save the current group to favorites"""
    user = await get_authenticated_user()
    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 401

    if not user.current_group_id:
        return jsonify({'success': False, 'error': 'Not in any group'}), 400

    current_group = app.db_session.query(Group).filter_by(id=user.current_group_id).first()
    if not current_group:
        return jsonify({'success': False, 'error': 'Current group not found'}), 404

    # Check if already saved
    if current_group not in user.saved_groups_rel:
        user.saved_groups_rel.append(current_group)
        app.db_session.commit()
        return jsonify({
            'success': True,
            'message': 'Group saved to favorites',
            'group': {
                'id': current_group.id,
                'name': current_group.name
            }
        })

    return jsonify({
        'success': True,
        'message': 'Group already in favorites',
        'group': {
            'id': current_group.id,
            'name': current_group.name
        }
    })


@app.route('/api/groups/saved', methods=['GET'])
@login_required
async def get_saved_groups():
    """Get all saved groups for the current user"""
    user = await get_authenticated_user()
    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 401

    saved_groups = [
        {
            'id': group.id,
            'name': group.name,
            'created_at': group.created_at.isoformat()
        }
        for group in user.saved_groups_rel
    ]

    return jsonify({
        'success': True,
        'groups': saved_groups,
        'current_group_id': user.current_group_id
    })


@app.route('/api/groups/unsave/<int:group_id>', methods=['POST'])
@login_required
async def unsave_group(group_id):
    """Remove a group from favorites"""
    user = await get_authenticated_user()
    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 401

    group = app.db_session.query(Group).filter_by(id=group_id).first()
    if not group:
        return jsonify({'success': False, 'error': 'Group not found'}), 404

    if group in user.saved_groups_rel:
        user.saved_groups_rel.remove(group)
        app.db_session.commit()

    return jsonify({'success': True, 'message': 'Group removed from favorites'})


# ==================== MESSAGE ENDPOINTS ====================

@app.route('/api/messages', methods=['GET'])
@login_required
async def get_messages():
    """Get all messages for the user's current group"""
    user = await get_authenticated_user()
    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 401

    group_id = request.args.get('group_id', user.current_group_id, type=int)

    if not group_id:
        return jsonify({
            'success': True,
            'messages': [],
            'count': 0,
            'user': {'id': user.id, 'username': user.username},
            'group_id': None
        })

    # Get messages from database
    messages = app.db_session.query(Message).filter_by(group_id=group_id).order_by(Message.timestamp).all()

    message_list = [
        {
            'id': msg.id,
            'text': msg.content,
            'username': msg.user.username,
            'timestamp': msg.timestamp.isoformat()
        }
        for msg in messages
    ]

    return jsonify({
        'success': True,
        'messages': message_list,
        'count': len(message_list),
        'user': {'id': user.id, 'username': user.username},
        'group_id': group_id
    })


@app.route('/api/messages', methods=['POST'])
@login_required
async def send_message():
    """Send a new chat message to the current group"""
    try:
        data = await request.get_json()

        user = await get_authenticated_user()
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 401

        if not user.current_group_id:
            return jsonify({'success': False, 'error': 'Not in any group'}), 400

        # Create message in database
        message = Message(
            content=data.get('text', ''),
            user_id=user.id,
            group_id=user.current_group_id,
            timestamp=datetime.utcnow()
        )

        app.db_session.add(message)
        app.db_session.commit()

        # Prepare message for broadcast
        message_data = {
            'id': message.id,
            'text': message.content,
            'username': user.username,
            'timestamp': message.timestamp.isoformat()
        }

        # Broadcast to all clients in the same group
        await broadcast_message(user.current_group_id, message_data)

        return jsonify({
            'success': True,
            'message': message_data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


# ==================== WEBSOCKET ====================

@app.websocket('/ws')
async def ws():
    """WebSocket endpoint for real-time message updates within a group"""
    print(f"[{datetime.now()}] WebSocket connection attempt")
    print(f"  Headers: {dict(websocket.headers)}")
    print(f"  Cookies: {websocket.cookies}")

    try:
        user = await get_authenticated_user()
        if not user:
            print("  WebSocket Error: User not authenticated")
            await websocket.send(json.dumps({'type': 'error', 'data': 'Not authenticated'}))
            return

        if not user.current_group_id:
            print(f"  WebSocket Error: User {user.username} not in any group")
            await websocket.send(json.dumps({'type': 'error', 'data': 'Not in a group'}))
            return

        group_id = user.current_group_id
        print(f"  WebSocket Success: User {user.username} connected to group {group_id}")
        
        ws_connection = websocket._get_current_object()
        
        # Add connection to the group's set
        if group_id not in websockets_by_group:
            websockets_by_group[group_id] = set()
        websockets_by_group[group_id].add(ws_connection)
        
        # Send all existing messages
        messages = app.db_session.query(Message).filter_by(group_id=group_id).order_by(Message.timestamp).all()
        for msg in messages:
            await ws_connection.send(json.dumps({
                'type': 'message',
                'data': {
                    'id': msg.id,
                    'text': msg.content,
                    'username': msg.user.username,
                    'timestamp': msg.timestamp.isoformat()
                }
            }))

        while True:
            await ws_connection.receive()
    except Exception as e:
        print(f"  WebSocket Error during connection: {e}")
    finally:
        if 'group_id' in locals() and group_id in websockets_by_group:
            websockets_by_group[group_id].discard(ws_connection)
            if not websockets_by_group[group_id]:
                del websockets_by_group[group_id]
        print("  WebSocket connection closed")


if __name__ == '__main__':
    import hypercorn.asyncio
    import asyncio

    port = int(os.environ.get('PORT', 5000))
    print(f"Starting server on port {port}...")

    # Configure Hypercorn
    config = hypercorn.Config()
    config.bind = [f"0.0.0.0:{port}"]

    # Run the app with Hypercorn ASGI server
    asyncio.run(hypercorn.asyncio.serve(app, config))
