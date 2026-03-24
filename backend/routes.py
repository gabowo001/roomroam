from quart import Blueprint, jsonify, request
from quart_auth import current_user, login_required
from quart import current_app
from datetime import datetime
import json
import utils
from models import User

# Create API blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api')


async def get_authenticated_user():
    """Helper function to get the authenticated user from database"""
    try:
        if await current_user.is_authenticated:
            auth_id = current_user.auth_id
            return current_app.db_session.query(User).filter_by(id=int(auth_id)).first()
    except:
        pass
    return None


@api_bp.route('/register', methods=['POST'])
async def register():
    """Register a new user"""
    
    data = await request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'success': False, 'error': 'Username and password are required'}), 400
    
    # Check if user already exists
    existing_user = User.get_user_by_username(username)
    if existing_user:
        return jsonify({'success': False, 'error': 'Username already exists'}), 400
    
    # Create new user
    user = User(username=username)
    user.set_password(password)
    
    current_app.db_session.add(user)
    current_app.db_session.commit()
    
    return jsonify({'success': True, 'message': 'User registered successfully'})


@api_bp.route('/login', methods=['POST'])
async def login():
    """Login a user"""
    
    data = await request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'success': False, 'error': 'Username and password are required'}), 400
    
    user = User.get_user_by_username(username)
    if user and user.check_password(password):
        # Use auth_id for quart_auth
        from quart_auth import login_user
        login_user(user, remember=True)
        return jsonify({
            'success': True, 
            'message': 'Login successful',
            'user': {'id': user.id, 'username': user.username}
        })
    
    return jsonify({'success': False, 'error': 'Invalid username or password'}), 401


@api_bp.route('/logout', methods=['POST'])
@login_required
async def logout():
    """Logout the current user"""
    from quart_auth import logout_user
    logout_user()
    return jsonify({'success': True, 'message': 'Logged out successfully'})


@api_bp.route('/messages', methods=['GET'])
@login_required
async def get_messages():
    """Get all chat messages"""
    
    user = await get_authenticated_user()
    return jsonify({
        'messages': current_app.messages,
        'count': len(current_app.messages),
        'user': {'id': user.id, 'username': user.username} if user else None
    })


@api_bp.route('/messages', methods=['POST'])
@login_required
async def send_message():
    """Send a new chat message"""
    
    try:
        data = await request.get_json()
        
        user = await get_authenticated_user()
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 401
        
        message = {
            'text': data.get('text', ''),
            'username': user.username,
            'timestamp': data.get('timestamp', datetime.now().isoformat()),
            'id': len(current_app.messages) + 1
        }
        
        current_app.messages.append(message)
        
        # Broadcast the new message to all connected WebSocket clients
        await utils.broadcast_message(message)
        
        return jsonify({
            'success': True,
            'message': message,
            'total_messages': len(current_app.messages)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400