from flask import Blueprint, request, jsonify, session
from models import db, User, Doctor
from functools import wraps

auth_bp = Blueprint('auth', __name__)


def _current_role():
    return session.get('user_role') or session.get('role')


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method == 'OPTIONS':
            return '', 204
        if 'user_id' not in session:
            return jsonify({'error': 'Login required'}), 401
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method == 'OPTIONS':
            return '', 204
        if 'user_id' not in session:
            return jsonify({'error': 'Login required'}), 401
        if _current_role() != 'admin':
            return jsonify({'error': 'Admin role required'}), 403
        return f(*args, **kwargs)
    return decorated_function


@auth_bp.route('/api/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.get_json(silent=True) or {}
        account_type = data.get('account_type', 'patient')

        if account_type not in ['patient', 'doctor']:
            return jsonify({'error': 'Account type must be patient or doctor'}), 400
        
        # Validate input
        if not data.get('email') or not data.get('password') or not data.get('name'):
            return jsonify({'error': 'Email, password, and name are required'}), 400

        if account_type == 'doctor':
            required_doctor_fields = [
                'specialty',
                'hospital',
                'location',
                'phone',
                'fee',
                'qualification',
                'experience_years'
            ]
            missing_fields = [field for field in required_doctor_fields if data.get(field) in [None, '']]
            if missing_fields:
                return jsonify({
                    'error': 'Please complete all doctor profile fields',
                    'missing_fields': missing_fields
                }), 400
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=data['email']).first()
        if existing_user:
            return jsonify({'error': 'Email already registered'}), 400
        
        # Create new user
        user = User(
            email=data['email'],
            name=data['name'],
            role=account_type
        )
        user.set_password(data['password'])
        
        db.session.add(user)
        db.session.flush()

        doctor_profile = None
        if account_type == 'doctor':
            try:
                fee = float(data.get('fee'))
                experience_years = int(data.get('experience_years'))
            except (TypeError, ValueError):
                return jsonify({'error': 'Fee and years of experience must be valid numbers'}), 400

            doctor_profile = Doctor(
                user_id=user.id,
                name=data['name'],
                specialty=data['specialty'],
                hospital=data['hospital'],
                location=data['location'],
                phone=data['phone'],
                fee=fee,
                rating=4.8,
                qualification=data.get('qualification'),
                experience_years=experience_years,
                approval_status='pending'
            )
            db.session.add(doctor_profile)

        db.session.commit()
        
        # Auto-login after registration
        session['user_id'] = user.id
        session['user_email'] = user.email
        session['user_name'] = user.name
        session['user_role'] = user.role
        
        response_payload = {
            'message': 'Registration successful',
            'user': user.to_dict()
        }
        if doctor_profile:
            response_payload['message'] = 'Doctor registration submitted for admin approval'
            response_payload['doctor_profile'] = doctor_profile.to_dict()

        return jsonify(response_payload), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/api/login', methods=['POST'])
def login():
    """Login user"""
    try:
        data = request.get_json(silent=True) or {}
        
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
        session['user_role'] = user.role
        
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
