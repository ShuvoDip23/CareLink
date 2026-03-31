from flask import Flask, request, jsonify
from flask_cors import CORS
import os

from models import db, Doctor, Appointment
from auth import auth_bp
from chat import chat_bp

print("=== NEW APP.PY IS RUNNING ===")

app = Flask(__name__)

# Important for login/session cookies
CORS(app, supports_credentials=True)

# Flask session secret key
app.secret_key = "carelink_secret_key_123"

# Database configuration
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'carelink.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize shared DB
db.init_app(app)

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(chat_bp)


# =========================
# Doctor routes
# =========================

@app.route('/api/doctors', methods=['GET'])
def get_doctors():
    specialty = request.args.get('specialty', '')
    query = request.args.get('q', '')

    doctors_query = Doctor.query

    if specialty:
        doctors_query = doctors_query.filter(Doctor.specialty == specialty)

    if query:
        doctors_query = doctors_query.filter(Doctor.name.contains(query))

    doctors = doctors_query.all()
    return jsonify([doctor.to_dict() for doctor in doctors])


@app.route('/api/doctors/<int:doctor_id>', methods=['GET'])
def get_doctor(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    return jsonify(doctor.to_dict())


@app.route('/api/doctors', methods=['POST'])
def add_doctor():
    data = request.json

    doctor = Doctor(
        name=data['name'],
        specialty=data['specialty'],
        hospital=data['hospital'],
        location=data['location'],
        phone=data['phone'],
        fee=data['fee'],
        rating=data.get('rating', 4.0)
    )

    db.session.add(doctor)
    db.session.commit()

    return jsonify(doctor.to_dict()), 201


@app.route('/api/doctors/<int:doctor_id>', methods=['PUT'])
def update_doctor(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    data = request.json

    doctor.name = data.get('name', doctor.name)
    doctor.specialty = data.get('specialty', doctor.specialty)
    doctor.hospital = data.get('hospital', doctor.hospital)
    doctor.location = data.get('location', doctor.location)
    doctor.phone = data.get('phone', doctor.phone)
    doctor.fee = data.get('fee', doctor.fee)
    doctor.rating = data.get('rating', doctor.rating)

    db.session.commit()
    return jsonify(doctor.to_dict())


@app.route('/api/doctors/<int:doctor_id>', methods=['DELETE'])
def delete_doctor(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    db.session.delete(doctor)
    db.session.commit()
    return jsonify({"message": "Doctor deleted"})


# =========================
# Appointment routes
# =========================

@app.route('/api/appointments', methods=['POST'])
def create_appointment():
    data = request.json

    appointment = Appointment(
        user_id=data['user_id'],
        user_name=data['user_name'],
        doctor_id=data['doctor_id'],
        appointment_date=data['appointment_date'],
        appointment_time=data['appointment_time'],
        reason=data['reason']
    )

    db.session.add(appointment)
    db.session.commit()

    return jsonify(appointment.to_dict()), 201


@app.route('/api/appointments', methods=['GET'])
def get_appointments():
    user_id = request.args.get('user_id')

    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    appointments = Appointment.query.filter_by(user_id=user_id).order_by(Appointment.created_at.desc()).all()
    return jsonify([appointment.to_dict() for appointment in appointments])


@app.route('/api/specialties', methods=['GET'])
def get_specialties():
    specialties = db.session.query(Doctor.specialty).distinct().all()
    return jsonify([s[0] for s in specialties])


# =========================
# Initialize database
# =========================

def init_db():
    with app.app_context():
        db.create_all()


if __name__ == '__main__':
    init_db()
    print("\n🏥 CareLink Backend Server Starting...")
    print("📍 API running at: http://localhost:5000")
    print("📚 API Endpoints:")
    print("   - GET  /api/doctors")
    print("   - POST /api/doctors")
    print("   - GET  /api/doctors/<id>")
    print("   - PUT  /api/doctors/<id>")
    print("   - DELETE /api/doctors/<id>")
    print("   - POST /api/appointments")
    print("   - GET  /api/appointments?user_id=<id>")
    print("   - GET  /api/specialties")
    print("   - POST /api/register")
    print("   - POST /api/login")
    print("   - POST /api/logout")
    print("   - GET  /api/me")
    print("   - POST /api/session/start")
    print("   - POST /api/chat/message")
    print("   - GET  /api/chat/history")
    print("\n")
    app.run(debug=True, port=5000)