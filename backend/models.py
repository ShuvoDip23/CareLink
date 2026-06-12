from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import hashlib

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), default='patient', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    chat_sessions = db.relationship('ChatSession', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash password before storing"""
        self.password = hashlib.sha256(password.encode()).hexdigest()
    
    def check_password(self, password):
        """Verify password"""
        return self.password == hashlib.sha256(password.encode()).hexdigest()
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'role': self.role or 'patient',
            'created_at': self.created_at.isoformat()
        }


class ChatSession(db.Model):
    __tablename__ = 'chat_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    session_id = db.Column(db.String(100), nullable=False)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    ended_at = db.Column(db.DateTime, nullable=True)
    
    # Store session state
    current_step = db.Column(db.String(50), default='initial')
    collected_data = db.Column(db.Text, default='{}')  # JSON string
    recommended_specialty = db.Column(db.String(100), nullable=True)
    risk_level = db.Column(db.String(20), default='low')  # low, medium, high, emergency
    
    # Relationships
    messages = db.relationship('ChatMessage', backref='session', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'started_at': self.started_at.isoformat(),
            'ended_at': self.ended_at.isoformat() if self.ended_at else None,
            'current_step': self.current_step,
            'recommended_specialty': self.recommended_specialty,
            'risk_level': self.risk_level
        }


class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('chat_sessions.id'), nullable=False)
    sender = db.Column(db.String(20), nullable=False)  # 'user' or 'bot'
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Optional: store structured data for bot messages
    message_type = db.Column(db.String(50), default='text')  # text, quick_reply, recommendation
    message_metadata = db.Column(db.Text, nullable=True)  # JSON string for buttons, actions, etc.
    
    def to_dict(self):
        return {
            'id': self.id,
            'sender': self.sender,
            'message': self.message,
            'timestamp': self.timestamp.isoformat(),
            'message_type': self.message_type,
            'metadata': self.message_metadata
        }



class Doctor(db.Model):
    __tablename__ = 'doctors'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    name = db.Column(db.String(100), nullable=False)
    specialty = db.Column(db.String(100), nullable=False)
    hospital = db.Column(db.String(200), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    fee = db.Column(db.Float, nullable=False)
    rating = db.Column(db.Float, default=4.0)
    qualification = db.Column(db.String(250), nullable=True)
    experience_years = db.Column(db.Integer, default=0)
    approval_status = db.Column(db.String(20), default='approved', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='doctor_profile')
    availability = db.relationship('DoctorAvailability', backref='doctor', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'specialty': self.specialty,
            'hospital': self.hospital,
            'location': self.location,
            'phone': self.phone,
            'fee': self.fee,
            'consultation_fee': self.fee,
            'rating': self.rating,
            'qualification': self.qualification,
            'experience_years': self.experience_years,
            'approval_status': self.approval_status or 'approved',
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class DoctorAvailability(db.Model):
    __tablename__ = 'doctor_availability'

    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False)
    day_of_week = db.Column(db.String(20), nullable=False)
    slot_time = db.Column(db.String(20), nullable=False)
    is_available = db.Column(db.Boolean, default=True, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'doctor_id': self.doctor_id,
            'day_of_week': self.day_of_week,
            'slot_time': self.slot_time,
            'is_available': bool(self.is_available)
        }





class Appointment(db.Model):
    __tablename__ = 'appointments'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(100), nullable=False)
    user_name = db.Column(db.String(100), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False)
    appointment_date = db.Column(db.String(20), nullable=False)
    appointment_time = db.Column(db.String(20), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='scheduled')
    payment_status = db.Column(db.Text, default='pending')
    transaction_id = db.Column(db.Text, nullable=True)
    payment_method = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    doctor = db.relationship('Doctor', backref='appointments')

    def appointment_datetime(self):
        date_value = str(self.appointment_date or '').strip()
        time_value = str(self.appointment_time or '').strip()
        for pattern in (
            '%Y-%m-%d %H:%M',
            '%Y-%m-%d %I:%M %p',
            '%Y-%m-%d %I %p',
            '%Y-%m-%d',
        ):
            try:
                return datetime.strptime(f'{date_value} {time_value}'.strip(), pattern)
            except ValueError:
                continue
        return None

    def derived_status(self):
        payment_status = str(self.payment_status or 'pending').lower()
        status = str(self.status or 'scheduled').lower()
        appointment_dt = self.appointment_datetime()
        is_cancelled = payment_status == 'cancelled' or status == 'cancelled'
        is_past = bool(appointment_dt and appointment_dt < datetime.utcnow())
        is_paid = payment_status in ['paid', 'confirmed']
        is_upcoming = bool(appointment_dt and appointment_dt >= datetime.utcnow() and is_paid and not is_cancelled)
        is_pending_payment = payment_status in ['pending', 'failed'] and not is_cancelled and not is_past

        if is_cancelled:
            display_status = 'Cancelled'
        elif is_past:
            display_status = 'Past'
        elif is_pending_payment:
            display_status = 'Pending payment'
        elif is_upcoming:
            display_status = 'Upcoming'
        else:
            display_status = status.replace('_', ' ').title()

        return {
            'is_past': is_past,
            'is_upcoming': is_upcoming,
            'is_pending_payment': is_pending_payment,
            'display_status': display_status,
        }

    def to_dict(self):
        payload = {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': self.user_name,
            'doctor_id': self.doctor_id,
            'doctor_name': self.doctor.name if self.doctor else None,
            'doctor_specialty': self.doctor.specialty if self.doctor else None,
            'appointment_date': self.appointment_date,
            'appointment_time': self.appointment_time,
            'reason': self.reason,
            'status': self.status,
            'payment_status': self.payment_status or 'pending',
            'transaction_id': self.transaction_id,
            'payment_method': self.payment_method,
            'created_at': self.created_at.isoformat()
        }
        payload.update(self.derived_status())
        return payload


class EmergencyProvider(db.Model):
    __tablename__ = 'emergency_providers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    zone = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    address = db.Column(db.String(250), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    available_24_7 = db.Column(db.Boolean, default=True, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'zone': self.zone,
            'phone': self.phone,
            'address': self.address,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'available_24_7': bool(self.available_24_7)
        }


class EmergencyAlert(db.Model):
    __tablename__ = 'emergency_alerts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    nearest_provider_id = db.Column(db.Integer, db.ForeignKey('emergency_providers.id'), nullable=True)
    summary = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='emergency_alerts')
    nearest_provider = db.relationship('EmergencyProvider', backref='alerts')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'nearest_provider_id': self.nearest_provider_id,
            'nearest_provider': self.nearest_provider.to_dict() if self.nearest_provider else None,
            'summary': self.summary,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
