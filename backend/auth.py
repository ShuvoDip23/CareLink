from flask import Blueprint, request, jsonify, session
from models import db, User
from functools import wraps

auth_bp = Blueprint('auth', __name__)

# Decorator to require authentication
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function


@auth_bp.route('/api/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.get_json()
        
        # Validate input
        if not data.get('email') or not data.get('password') or not data.get('name'):
            return jsonify({'error': 'Email, password, and name are required'}), 400
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=data['email']).first()
        if existing_user:
            return jsonify({'error': 'Email already registered'}), 400
        
        # Create new user
        user = User(
            email=data['email'],
            name=data['name']
        )
        user.set_password(data['password'])
        
        db.session.add(user)
        db.session.commit()
        
        # Auto-login after registration
        session['user_id'] = user.id
        session['user_email'] = user.email
        session['user_name'] = user.name
        
        return jsonify({
            'message': 'Registration successful',
            'user': user.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/api/login', methods=['POST'])
def login():
    """Login user"""
    try:
        data = request.get_json()
        
        # Validate input
        if not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Email and password are required'}), 400
        
        # Find user
        user = User.query.filter_by(email=data['email']).first()
        
        if not user or not user.check_password(data['password']):
            return jsonify({'error': 'Invalid email or password'}), 401
        
        # Create session
        session['user_id'] = user.id
        session['user_email'] = user.email
        session['user_name'] = user.name
        
        return jsonify({
            'message': 'Login successful',
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/api/logout', methods=['POST'])
def logout():
    """Logout user"""
    session.clear()
    return jsonify({'message': 'Logout successful'}), 200


@auth_bp.route('/api/me', methods=['GET'])
def get_current_user():
    """Get current logged-in user"""
    if 'user_id' not in session:
        return jsonify({'authenticated': False}), 200
    
    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        return jsonify({'authenticated': False}), 200
    
    return jsonify({
        'authenticated': True,
        'user': user.to_dict()
    }), 200
