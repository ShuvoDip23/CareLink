from flask import Flask, request, jsonify, session, redirect
from flask_cors import CORS
from datetime import datetime
from decimal import Decimal, InvalidOperation
import json
import math
import os
import re
from sqlalchemy import or_, text
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import uuid

from models import db, Doctor, DoctorAvailability, Appointment, User, ChatSession, ChatMessage, EmergencyProvider, EmergencyAlert
from auth import auth_bp, login_required, admin_required
from chat import chat_bp

print("=== NEW APP.PY IS RUNNING ===")

app = Flask(__name__)

DEFAULT_FRONTEND_URL = 'http://127.0.0.1:5500'
LOCAL_FRONTEND_ORIGINS = [
    'http://127.0.0.1:5500',
    'http://localhost:5500',
]


def _configured_frontend_origins():
    raw_frontend_url = os.environ.get('FRONTEND_URL', DEFAULT_FRONTEND_URL)
    origins = list(LOCAL_FRONTEND_ORIGINS)
    for item in raw_frontend_url.split(','):
        origin = item.strip().rstrip('/')
        if origin and origin not in origins:
            origins.append(origin)
    return origins


FRONTEND_URL = os.environ.get('FRONTEND_URL', DEFAULT_FRONTEND_URL).split(',')[0].strip().rstrip('/')
BACKEND_URL = os.environ.get('BACKEND_URL', 'http://127.0.0.1:5000').rstrip('/')
ALLOWED_FRONTEND_ORIGINS = _configured_frontend_origins()

# Flask session secret key
app.secret_key = os.environ.get('SECRET_KEY', 'dev-carelink-secret-change-me')
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
)

# Important for login/session cookies
CORS(
    app,
    origins=ALLOWED_FRONTEND_ORIGINS,
    supports_credentials=True,
    allow_headers=['Content-Type', 'Authorization'],
    methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
)

# Database configuration
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'carelink.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize shared DB
db.init_app(app)

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(chat_bp)


SSLCOMMERZ_INIT_URL = 'https://sandbox.sslcommerz.com/gwprocess/v4/api.php'
SSLCOMMERZ_VALIDATION_URL = 'https://sandbox.sslcommerz.com/validator/api/validationserverAPI.php'

RAJSHAHI_EMERGENCY_PROVIDERS = [
    {
        'name': 'CareLink Emergency - Medical Area',
        'zone': 'Laxmipur / Medical Area',
        'phone': '+8801700000001',
        'address': 'Demo provider near Rajshahi Medical College Hospital area, Laxmipur, Rajshahi',
        'latitude': 24.3745,
        'longitude': 88.6042,
        'available_24_7': True
    },
    {
        'name': 'CareLink Emergency - Zero Point',
        'zone': 'Shaheb Bazar / Zero Point',
        'phone': '+8801700000002',
        'address': 'Demo provider near Shaheb Bazar Zero Point, Rajshahi',
        'latitude': 24.3658,
        'longitude': 88.6049,
        'available_24_7': True
    },
    {
        'name': 'CareLink Emergency - Binodpur',
        'zone': 'Rajshahi University / Kazla / Binodpur',
        'phone': '+8801700000003',
        'address': 'Demo provider near Rajshahi University, Kazla and Binodpur area, Rajshahi',
        'latitude': 24.3689,
        'longitude': 88.6381,
        'available_24_7': True
    },
    {
        'name': 'CareLink Emergency - Upashahar',
        'zone': 'New Market / Upashahar',
        'phone': '+8801700000004',
        'address': 'Demo provider near New Market and Upashahar, Rajshahi',
        'latitude': 24.3791,
        'longitude': 88.5898,
        'available_24_7': True
    },
    {
        'name': 'CareLink Emergency - Talaimari',
        'zone': 'Talaimari / Vodra',
        'phone': '+8801700000005',
        'address': 'Demo provider near Talaimari and Vodra, Rajshahi',
        'latitude': 24.3633,
        'longitude': 88.6244,
        'available_24_7': True
    },
    {
        'name': 'CareLink Emergency - Greater Road',
        'zone': 'Court / C&B / Greater Road',
        'phone': '+8801700000006',
        'address': 'Demo provider near Court, C&B and Greater Road, Rajshahi',
        'latitude': 24.3733,
        'longitude': 88.5905,
        'available_24_7': True
    }
]

DAYS_OF_WEEK = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
DEFAULT_SLOT_TIMES = ['09:00 AM', '10:00 AM', '11:00 AM', '12:00 PM', '02:00 PM', '03:00 PM', '04:00 PM', '05:00 PM']
SPECIALTY_SLOT_PATTERNS = {
    'cardiologist': ['09:00 AM', '10:00 AM', '11:00 AM'],
    'dermatologist': ['12:00 PM', '02:00 PM', '03:00 PM', '04:00 PM'],
    'ent specialist': ['11:00 AM', '12:00 PM', '04:00 PM', '05:00 PM'],
    'general physician': DEFAULT_SLOT_TIMES,
}
BLOCKING_APPOINTMENT_STATUSES = ['payment_pending', 'pending', 'confirmed', 'paid']
BLOCKING_PAYMENT_STATUSES = ['pending', 'paid']


def _sslcommerz_config():
    sandbox_enabled = os.environ.get('SSLCOMMERZ_SANDBOX', 'true').strip().lower() in ['1', 'true', 'yes']
    if not sandbox_enabled:
        raise ValueError('CareLink payments are configured for SSLCommerz sandbox only.')

    store_id = os.environ.get('SSLCOMMERZ_STORE_ID')
    store_password = os.environ.get('SSLCOMMERZ_STORE_PASSWORD')
    if not store_id or not store_password:
        raise ValueError('SSLCommerz sandbox credentials are not configured.')

    return {
        'store_id': store_id,
        'store_password': store_password,
    }


def _request_json(url, data=None, timeout=30):
    if data is None:
        request_url = url
        request_data = None
        headers = {}
    else:
        request_url = url
        request_data = urlencode(data).encode('utf-8')
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

    ssl_request = Request(request_url, data=request_data, headers=headers)
    try:
        with urlopen(ssl_request, timeout=timeout) as response:
            body = response.read().decode('utf-8')
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f'Could not reach SSLCommerz sandbox: {exc}') from exc

    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError('SSLCommerz returned an invalid response.') from exc


def _create_transaction_id(appointment_id):
    return f'CL{appointment_id}-{uuid.uuid4().hex[:8]}'


def _appointment_amount(doctor):
    return f'{Decimal(str(doctor.fee or 0)).quantize(Decimal("0.01"))}'


def _start_sslcommerz_session(appointment, doctor):
    config = _sslcommerz_config()
    tran_id = appointment.transaction_id or _create_transaction_id(appointment.id)
    appointment.transaction_id = tran_id

    payload = {
        'store_id': config['store_id'],
        'store_passwd': config['store_password'],
        'total_amount': _appointment_amount(doctor),
        'currency': 'BDT',
        'tran_id': tran_id,
        'success_url': f'{BACKEND_URL}/api/payments/success',
        'fail_url': f'{BACKEND_URL}/api/payments/fail',
        'cancel_url': f'{BACKEND_URL}/api/payments/cancel',
        'cus_name': appointment.user_name,
        'cus_email': session.get('user_email', 'patient@example.com'),
        'cus_add1': 'Dhaka',
        'cus_city': 'Dhaka',
        'cus_state': 'Dhaka',
        'cus_postcode': '1000',
        'cus_country': 'Bangladesh',
        'cus_phone': doctor.phone,
        'shipping_method': 'NO',
        'product_name': f'Consultation with {doctor.name}',
        'product_category': 'healthcare',
        'product_profile': 'non-physical-goods',
        'value_a': str(appointment.id),
        'value_b': str(appointment.doctor_id),
        'value_c': appointment.appointment_date,
        'value_d': appointment.appointment_time,
    }

    response = _request_json(SSLCOMMERZ_INIT_URL, payload)
    gateway_url = response.get('GatewayPageURL')
    if not gateway_url:
        reason = response.get('failedreason') or response.get('error') or 'SSLCommerz did not return a payment URL.'
        raise RuntimeError(reason)

    return {
        'gateway_page_url': gateway_url,
        'session_key': response.get('sessionkey'),
    }


def _payment_payload():
    if request.is_json:
        return request.get_json(silent=True) or {}
    return request.values.to_dict()


def _find_appointment_from_payment(payload):
    tran_id = payload.get('tran_id') or payload.get('transaction_id')
    appointment = None

    if tran_id:
        appointment = Appointment.query.filter_by(transaction_id=tran_id).first()

    if not appointment and payload.get('value_a'):
        try:
            appointment = Appointment.query.get(int(payload['value_a']))
        except (TypeError, ValueError):
            appointment = None

    if not appointment and tran_id:
        match = re.match(r'^CL(\d+)-', tran_id)
        if match:
            appointment = Appointment.query.get(int(match.group(1)))

    return appointment, tran_id


def _paid_status(status):
    return str(status or '').upper() in ['VALID', 'VALIDATED']


def _amount_matches(expected, received):
    try:
        return Decimal(str(expected)).quantize(Decimal('0.01')) == Decimal(str(received)).quantize(Decimal('0.01'))
    except (InvalidOperation, TypeError, ValueError):
        return False


def _validate_sslcommerz_payment(val_id):
    config = _sslcommerz_config()
    query = urlencode({
        'val_id': val_id,
        'store_id': config['store_id'],
        'store_passwd': config['store_password'],
        'v': 1,
        'format': 'json',
    })
    return _request_json(f'{SSLCOMMERZ_VALIDATION_URL}?{query}', timeout=30)


def _verify_success_payment(payload, appointment):
    val_id = payload.get('val_id')
    validation = None
    validation_error = None

    if val_id:
        try:
            validation = _validate_sslcommerz_payment(val_id)
        except RuntimeError as exc:
            validation_error = str(exc)

    source = validation or payload
    tran_id = source.get('tran_id') or payload.get('tran_id')
    amount = source.get('currency_amount') or source.get('amount') or payload.get('amount')
    currency = source.get('currency_type') or source.get('currency') or payload.get('currency')

    if validation and not _paid_status(validation.get('status')):
        return False, validation, 'SSLCommerz could not validate this transaction.'

    if not _paid_status(source.get('status')):
        return False, validation, 'Payment was not completed by SSLCommerz.'

    if appointment.transaction_id and tran_id and tran_id != appointment.transaction_id:
        return False, validation, 'Transaction ID did not match this appointment.'

    if amount and not _amount_matches(appointment.doctor.fee, amount):
        return False, validation, 'Payment amount did not match the appointment fee.'

    if currency and currency.upper() != 'BDT':
        return False, validation, 'Payment currency did not match BDT.'

    return True, validation, validation_error


def _payment_method_from(payload, validation=None):
    source = validation or payload
    return source.get('card_type') or source.get('card_brand') or source.get('card_issuer')


def _payment_redirect(status, appointment=None, message=None):
    params = {'payment': status}
    if appointment:
        params['appointment_id'] = appointment.id
    if message:
        params['message'] = message
    return redirect(f'{FRONTEND_URL}/appointments.html?{urlencode(params)}')


def _patient_required():
    role = session.get('user_role') or session.get('role') or 'patient'
    return role == 'patient'


def _clean_text(value, fallback=None, max_length=250):
    if value is None:
        return fallback
    text_value = ' '.join(str(value).strip().split())
    if not text_value:
        return fallback
    return text_value[:max_length]


def _coerce_float(value, field_name, minimum=None, maximum=None):
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f'{field_name} must be a valid number')
    if minimum is not None and number < minimum:
        raise ValueError(f'{field_name} cannot be less than {minimum}')
    if maximum is not None and number > maximum:
        raise ValueError(f'{field_name} cannot be greater than {maximum}')
    return number


def _coerce_int(value, field_name, minimum=None, maximum=None):
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ValueError(f'{field_name} must be a valid whole number')
    if minimum is not None and number < minimum:
        raise ValueError(f'{field_name} cannot be less than {minimum}')
    if maximum is not None and number > maximum:
        raise ValueError(f'{field_name} cannot be greater than {maximum}')
    return number


def _doctor_payload(data, existing_doctor=None):
    payload = data or {}
    if not isinstance(payload, dict):
        raise ValueError('Request body must be JSON')

    required_fields = ['name', 'specialty', 'hospital', 'phone', 'fee']
    if existing_doctor is None:
        missing_fields = [
            field for field in required_fields
            if _clean_text(payload.get(field), max_length=250) is None
        ]
        if _clean_text(payload.get('location', payload.get('address')), max_length=250) is None:
            missing_fields.append('location')
        if missing_fields:
            raise ValueError(f'Missing required doctor fields: {", ".join(missing_fields)}')

    approval_status = payload.get('approval_status', existing_doctor.approval_status if existing_doctor else 'approved')
    approval_status = str(approval_status or 'approved').strip().lower()
    if approval_status not in ['approved', 'pending', 'rejected']:
        raise ValueError('approval_status must be approved, pending, or rejected')

    fee_value = payload.get('fee', payload.get('consultation_fee', existing_doctor.fee if existing_doctor else None))

    return {
        'name': _clean_text(payload.get('name'), existing_doctor.name if existing_doctor else None, 100),
        'specialty': _clean_text(payload.get('specialty'), existing_doctor.specialty if existing_doctor else None, 100),
        'hospital': _clean_text(payload.get('hospital'), existing_doctor.hospital if existing_doctor else None, 200),
        'location': _clean_text(payload.get('location', payload.get('address')), existing_doctor.location if existing_doctor else None, 200),
        'phone': _clean_text(payload.get('phone'), existing_doctor.phone if existing_doctor else None, 20),
        'fee': _coerce_float(fee_value, 'consultation fee', 0),
        'rating': _coerce_float(payload.get('rating', existing_doctor.rating if existing_doctor else 4.0), 'rating', 0, 5),
        'qualification': _clean_text(payload.get('qualification'), existing_doctor.qualification if existing_doctor else None, 250),
        'experience_years': _coerce_int(
            payload.get('experience_years', existing_doctor.experience_years if existing_doctor else 0) or 0,
            'experience years',
            0,
            80
        ),
        'approval_status': approval_status,
    }


def _apply_doctor_payload(doctor, payload):
    for field, value in payload.items():
        setattr(doctor, field, value)


def _normalize_slot_time(value):
    text_value = ' '.join(str(value or '').strip().upper().split())
    if not text_value:
        return None
    for pattern in ('%I:%M %p', '%I %p', '%H:%M'):
        try:
            return datetime.strptime(text_value, pattern).strftime('%I:%M %p')
        except ValueError:
            continue
    return text_value


def _slot_period(slot_time):
    try:
        hour = datetime.strptime(slot_time, '%I:%M %p').hour
    except ValueError:
        return 'Available'
    if hour < 12:
        return 'Morning'
    if hour == 12:
        return 'Noon'
    if hour < 16:
        return 'Afternoon'
    return 'Evening'


def _day_from_date(date_value):
    try:
        return datetime.strptime(str(date_value or '').strip(), '%Y-%m-%d').strftime('%A')
    except ValueError:
        return None


def _specialty_slots(specialty):
    normalized = str(specialty or '').strip().lower()
    for key, slots in SPECIALTY_SLOT_PATTERNS.items():
        if key in normalized:
            return slots
    return DEFAULT_SLOT_TIMES


def _availability_rows_for_doctor(doctor):
    existing = DoctorAvailability.query.filter_by(doctor_id=doctor.id).all()
    if existing:
        return existing

    seed_doctor_availability(doctor, commit=False)
    db.session.flush()
    return DoctorAvailability.query.filter_by(doctor_id=doctor.id).all()


def _doctor_available_slot_times(doctor, day_of_week):
    rows = _availability_rows_for_doctor(doctor)
    return {
        _normalize_slot_time(row.slot_time)
        for row in rows
        if row.day_of_week == day_of_week and row.is_available
    }


def _blocking_appointment_query(doctor_id, appointment_date, slot_time):
    normalized_slot = _normalize_slot_time(slot_time)
    return Appointment.query.filter(
        Appointment.doctor_id == doctor_id,
        Appointment.appointment_date == appointment_date,
        Appointment.appointment_time == normalized_slot,
        or_(
            Appointment.status.in_(BLOCKING_APPOINTMENT_STATUSES),
            Appointment.payment_status.in_(BLOCKING_PAYMENT_STATUSES)
        ),
        Appointment.status != 'cancelled',
        Appointment.payment_status.notin_(['cancelled', 'failed'])
    )


def _is_slot_booked(doctor_id, appointment_date, slot_time):
    return _blocking_appointment_query(doctor_id, appointment_date, slot_time).first() is not None


def _availability_response_for_date(doctor, appointment_date):
    day_of_week = _day_from_date(appointment_date)
    if not day_of_week:
        return None

    rows = _availability_rows_for_doctor(doctor)
    day_rows = {
        _normalize_slot_time(row.slot_time): row
        for row in rows
        if row.day_of_week == day_of_week
    }
    ordered_slots = [
        slot for slot in DEFAULT_SLOT_TIMES
        if slot in day_rows or slot in _specialty_slots(doctor.specialty)
    ]
    for slot in sorted(day_rows):
        if slot not in ordered_slots:
            ordered_slots.append(slot)

    slots = []
    for slot_time in ordered_slots:
        row = day_rows.get(slot_time)
        doctor_available = bool(row and row.is_available)
        is_booked = _is_slot_booked(doctor.id, appointment_date, slot_time) if doctor_available else False
        slots.append({
            'time': slot_time,
            'label': _slot_period(slot_time),
            'is_available': doctor_available and not is_booked,
            'is_doctor_available': doctor_available,
            'is_booked': is_booked,
            'message': 'This slot is already booked.' if is_booked else None
        })

    return {
        'doctor_id': doctor.id,
        'date': appointment_date,
        'day_of_week': day_of_week,
        'slots': slots
    }


def _admin_availability_payload(doctor):
    rows = _availability_rows_for_doctor(doctor)
    availability = {day: [] for day in DAYS_OF_WEEK}
    rows_by_day = {}
    for row in rows:
        slot_time = _normalize_slot_time(row.slot_time)
        rows_by_day.setdefault(row.day_of_week, {})[slot_time] = row

    for day in DAYS_OF_WEEK:
        day_slots = list(DEFAULT_SLOT_TIMES)
        for slot_time in sorted(rows_by_day.get(day, {})):
            if slot_time not in day_slots:
                day_slots.append(slot_time)
        availability[day] = [
            {
                'time': slot_time,
                'label': _slot_period(slot_time),
                'is_available': bool(rows_by_day.get(day, {}).get(slot_time) and rows_by_day[day][slot_time].is_available)
            }
            for slot_time in day_slots
        ]

    return {
        'doctor_id': doctor.id,
        'days': DAYS_OF_WEEK,
        'slot_times': DEFAULT_SLOT_TIMES,
        'availability': availability
    }


def _parse_admin_availability(data):
    entries = []
    raw_entries = data.get('availability') if isinstance(data, dict) else None
    if isinstance(raw_entries, dict):
        for day, slots in raw_entries.items():
            if isinstance(slots, dict):
                iterable = [{'slot_time': slot, 'is_available': available} for slot, available in slots.items()]
            else:
                iterable = slots
            for item in iterable or []:
                if isinstance(item, str):
                    entries.append({'day_of_week': day, 'slot_time': item, 'is_available': True})
                elif isinstance(item, dict):
                    entries.append({
                        'day_of_week': item.get('day_of_week') or day,
                        'slot_time': item.get('slot_time') or item.get('time'),
                        'is_available': item.get('is_available', True)
                    })
    elif isinstance(raw_entries, list):
        entries = raw_entries
    else:
        raise ValueError('availability must be a list or day mapping')

    parsed = []
    seen = set()
    for item in entries:
        day = str(item.get('day_of_week') or '').strip().title()
        slot_time = _normalize_slot_time(item.get('slot_time') or item.get('time'))
        if day not in DAYS_OF_WEEK:
            raise ValueError('day_of_week must be a valid weekday name')
        if not slot_time:
            raise ValueError('slot_time is required')
        key = (day, slot_time)
        if key in seen:
            continue
        seen.add(key)
        parsed.append({
            'day_of_week': day,
            'slot_time': slot_time,
            'is_available': bool(item.get('is_available', True))
        })
    return parsed


def _parse_coordinates(data):
    try:
        latitude = float(data.get('latitude'))
        longitude = float(data.get('longitude'))
    except (TypeError, ValueError):
        return None, None, 'Valid latitude and longitude are required'

    if latitude < -90 or latitude > 90 or longitude < -180 or longitude > 180:
        return None, None, 'Latitude or longitude is outside the valid range'

    return latitude, longitude, None


def haversine_distance_km(lat1, lon1, lat2, lon2):
    radius_km = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius_km * c


def _nearest_provider(latitude, longitude):
    providers = EmergencyProvider.query.all()
    if not providers:
        return None, None

    nearest = min(
        providers,
        key=lambda provider: haversine_distance_km(
            latitude,
            longitude,
            provider.latitude,
            provider.longitude
        )
    )
    distance = haversine_distance_km(latitude, longitude, nearest.latitude, nearest.longitude)
    return nearest, round(distance, 2)


def _clean_summary_line(value, fallback='Not available'):
    text_value = str(value or '').strip()
    if not text_value:
        return fallback
    return ' '.join(text_value.split())[:220]


def _build_emergency_summary(user_id):
    user = User.query.get(user_id)
    if not user:
        return 'CareLink emergency summary could not find the logged-in user record.'

    recent_sessions = ChatSession.query.filter_by(user_id=user_id) \
        .order_by(ChatSession.started_at.desc()) \
        .limit(3) \
        .all()

    chat_lines = []
    session_notes = []
    for chat_session in recent_sessions:
        session_notes.append(
            f"{chat_session.started_at.strftime('%Y-%m-%d')}: "
            f"risk {chat_session.risk_level or 'not recorded'}, "
            f"recommended specialty {chat_session.recommended_specialty or 'not recorded'}"
        )
        messages = ChatMessage.query.filter_by(session_id=chat_session.id) \
            .order_by(ChatMessage.timestamp.desc()) \
            .limit(4) \
            .all()
        for message in reversed(messages):
            if message.sender == 'user':
                chat_lines.append(_clean_summary_line(message.message))

    appointments = Appointment.query.filter_by(user_id=str(user_id)) \
        .order_by(Appointment.created_at.desc()) \
        .limit(3) \
        .all()

    appointment_lines = []
    for appointment in appointments:
        doctor_label = appointment.doctor.name if appointment.doctor else 'Doctor not recorded'
        appointment_lines.append(
            f"{appointment.appointment_date} {appointment.appointment_time}: "
            f"{doctor_label} ({appointment.doctor.specialty if appointment.doctor else 'specialty not recorded'}), "
            f"reason: {_clean_summary_line(appointment.reason)}, status: {appointment.status}"
        )

    lines = [
        'CareLink Emergency Medical Summary',
        'Safety note: This summary is generated from CareLink history and is not a medical diagnosis.',
        f"Patient: {_clean_summary_line(user.name)}",
        f"CareLink email: {_clean_summary_line(user.email)}",
        f"Generated at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        '',
        'Recent CareLink chat details:'
    ]

    if session_notes:
        lines.extend(f"- {note}" for note in session_notes)
    else:
        lines.append('- No previous CareLink chat sessions found.')

    lines.append('')
    lines.append('Recent patient-reported chat messages:')
    if chat_lines:
        for line in chat_lines[:6]:
            lines.append(f"- {line}")
    else:
        lines.append('- No patient chat messages found.')

    lines.append('')
    lines.append('Recent appointments:')
    if appointment_lines:
        lines.extend(f"- {line}" for line in appointment_lines)
    else:
        lines.append('- No appointment history found.')

    lines.append('')
    lines.append('For urgent symptoms, contact local emergency services or go to the nearest emergency department.')
    return '\n'.join(lines)


# =========================
# Doctor routes
# =========================

@app.route('/api/doctors', methods=['GET'])
def get_doctors():
    specialty = request.args.get('specialty', '')
    query = request.args.get('q', '')

    doctors_query = Doctor.query.filter_by(approval_status='approved')

    if specialty:
        doctors_query = doctors_query.filter(Doctor.specialty == specialty)

    if query:
        doctors_query = doctors_query.filter(Doctor.name.contains(query))

    doctors = doctors_query.all()
    return jsonify([doctor.to_dict() for doctor in doctors])


@app.route('/api/doctors/<int:doctor_id>', methods=['GET'])
def get_doctor(doctor_id):
    doctor = Doctor.query.filter_by(id=doctor_id, approval_status='approved').first_or_404()
    return jsonify(doctor.to_dict())


@app.route('/api/doctors/<int:doctor_id>/availability', methods=['GET'])
def get_doctor_availability(doctor_id):
    doctor = Doctor.query.filter_by(id=doctor_id, approval_status='approved').first_or_404()
    appointment_date = request.args.get('date', '').strip()
    if not appointment_date:
        return jsonify({'error': 'date is required in YYYY-MM-DD format'}), 400

    payload = _availability_response_for_date(doctor, appointment_date)
    if payload is None:
        return jsonify({'error': 'date must use YYYY-MM-DD format'}), 400
    db.session.commit()
    return jsonify(payload)


@app.route('/api/doctors', methods=['POST'])
@admin_required
def add_doctor():
    try:
        payload = _doctor_payload(request.get_json(silent=True) or {})
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    doctor = Doctor(**payload)

    db.session.add(doctor)
    db.session.flush()
    seed_doctor_availability(doctor, commit=False)
    db.session.commit()

    return jsonify(doctor.to_dict()), 201


@app.route('/api/doctors/<int:doctor_id>', methods=['PUT'])
@admin_required
def update_doctor(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    try:
        payload = _doctor_payload(request.get_json(silent=True) or {}, doctor)
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    _apply_doctor_payload(doctor, payload)
    db.session.commit()
    return jsonify(doctor.to_dict())


@app.route('/api/doctors/<int:doctor_id>', methods=['DELETE'])
@admin_required
def delete_doctor(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    db.session.delete(doctor)
    db.session.commit()
    return jsonify({"message": "Doctor deleted"})


# =========================
# Appointment routes
# =========================

@app.route('/api/appointments', methods=['POST'])
@login_required
def create_appointment():
    data = request.get_json(silent=True) or {}
    required_fields = ['doctor_id', 'appointment_date', 'appointment_time', 'reason']
    missing_fields = [field for field in required_fields if not data.get(field)]
    if missing_fields:
        return jsonify({'error': 'Please complete all appointment fields', 'missing_fields': missing_fields}), 400

    doctor = Doctor.query.filter_by(id=data['doctor_id'], approval_status='approved').first()
    if not doctor:
        return jsonify({'error': 'Doctor is not available for booking'}), 404

    appointment_date = str(data.get('appointment_date') or '').strip()
    appointment_time = _normalize_slot_time(data.get('appointment_time'))
    day_of_week = _day_from_date(appointment_date)
    if not day_of_week or not appointment_time:
        return jsonify({'error': 'Please choose a valid appointment date and time.'}), 400

    available_times = _doctor_available_slot_times(doctor, day_of_week)
    if appointment_time not in available_times:
        db.session.commit()
        return jsonify({'error': 'This doctor is not available at the selected time.'}), 400

    if _is_slot_booked(doctor.id, appointment_date, appointment_time):
        return jsonify({'error': 'This time slot is already booked. Please choose another time.'}), 409

    appointment = Appointment(
        user_id=str(session['user_id']),
        user_name=data.get('user_name') or session.get('user_name', 'Patient'),
        doctor_id=data['doctor_id'],
        appointment_date=appointment_date,
        appointment_time=appointment_time,
        reason=data['reason'],
        status='payment_pending',
        payment_status='pending'
    )

    db.session.add(appointment)
    db.session.flush()
    appointment.transaction_id = _create_transaction_id(appointment.id)
    db.session.commit()

    try:
        payment_session = _start_sslcommerz_session(appointment, doctor)
    except ValueError as exc:
        return jsonify({
            'error': str(exc),
            'appointment': appointment.to_dict()
        }), 503
    except RuntimeError as exc:
        return jsonify({
            'error': str(exc),
            'appointment': appointment.to_dict()
        }), 502

    response = appointment.to_dict()
    response['payment_url'] = payment_session['gateway_page_url']
    response['gateway_page_url'] = payment_session['gateway_page_url']
    response['sslcommerz_session_key'] = payment_session['session_key']
    return jsonify(response), 201


@app.route('/api/appointments', methods=['GET'])
@login_required
def get_appointments():
    user_id = str(session['user_id'])

    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    appointments_query = Appointment.query
    if (session.get('user_role') or session.get('role')) != 'admin':
        appointments_query = appointments_query.filter_by(user_id=user_id)

    appointments = appointments_query.order_by(Appointment.created_at.desc()).all()
    return jsonify([appointment.to_dict() for appointment in appointments])


@app.route('/api/payments/initiate', methods=['POST'])
@login_required
def initiate_payment():
    data = request.get_json(silent=True) or {}
    appointment_id = data.get('appointment_id')
    if not appointment_id:
        return jsonify({'error': 'appointment_id is required'}), 400

    appointment = Appointment.query.filter_by(
        id=appointment_id,
        user_id=str(session['user_id'])
    ).first()
    if not appointment:
        return jsonify({'error': 'Appointment was not found'}), 404

    if appointment.payment_status == 'paid':
        return jsonify({'error': 'This appointment is already paid'}), 400
    if appointment.payment_status == 'cancelled' or appointment.status == 'cancelled':
        return jsonify({'error': 'Cancelled appointments cannot be paid'}), 400

    appointment.status = 'payment_pending'
    appointment.payment_status = 'pending'
    appointment.transaction_id = appointment.transaction_id or _create_transaction_id(appointment.id)
    db.session.commit()

    try:
        payment_session = _start_sslcommerz_session(appointment, appointment.doctor)
    except ValueError as exc:
        return jsonify({
            'error': str(exc),
            'appointment': appointment.to_dict()
        }), 503
    except RuntimeError as exc:
        return jsonify({
            'error': str(exc),
            'appointment': appointment.to_dict()
        }), 502

    response = appointment.to_dict()
    response['payment_url'] = payment_session['gateway_page_url']
    response['gateway_page_url'] = payment_session['gateway_page_url']
    response['sslcommerz_session_key'] = payment_session['session_key']
    return jsonify(response)


@app.route('/api/appointments/<int:appointment_id>/cancel', methods=['POST'])
@login_required
def cancel_appointment(appointment_id):
    appointment = Appointment.query.filter_by(
        id=appointment_id,
        user_id=str(session['user_id'])
    ).first()
    if not appointment:
        return jsonify({'error': 'Appointment was not found'}), 404

    if appointment.payment_status == 'paid':
        return jsonify({'error': 'Paid appointments cannot be cancelled from this action'}), 400

    if appointment.status == 'cancelled' or appointment.payment_status == 'cancelled':
        return jsonify(appointment.to_dict())

    if not appointment.derived_status().get('is_pending_payment'):
        return jsonify({'error': 'Only unpaid pending appointments can be cancelled here'}), 400

    appointment.status = 'cancelled'
    appointment.payment_status = 'cancelled'
    db.session.commit()
    return jsonify(appointment.to_dict())


@app.route('/api/payments/success', methods=['GET', 'POST'])
def payment_success():
    payload = _payment_payload()
    appointment, tran_id = _find_appointment_from_payment(payload)
    if not appointment:
        return _payment_redirect('error', message='We could not find the appointment for this payment.')

    if appointment.payment_status == 'paid':
        return _payment_redirect('success', appointment)

    is_valid, validation, validation_message = _verify_success_payment(payload, appointment)
    if not is_valid:
        appointment.payment_status = 'failed'
        db.session.commit()
        return _payment_redirect('failed', appointment, validation_message)

    appointment.status = 'confirmed'
    appointment.payment_status = 'paid'
    appointment.transaction_id = tran_id or appointment.transaction_id
    appointment.payment_method = _payment_method_from(payload, validation)
    db.session.commit()

    return _payment_redirect('success', appointment)


@app.route('/api/payments/fail', methods=['GET', 'POST'])
def payment_fail():
    payload = _payment_payload()
    appointment, tran_id = _find_appointment_from_payment(payload)
    if appointment:
        if appointment.payment_status == 'paid':
            return _payment_redirect('success', appointment)
        else:
            appointment.payment_status = 'failed'
            appointment.transaction_id = tran_id or appointment.transaction_id
            appointment.payment_method = _payment_method_from(payload)
            db.session.commit()

    return _payment_redirect('failed', appointment)


@app.route('/api/payments/cancel', methods=['GET', 'POST'])
def payment_cancel():
    payload = _payment_payload()
    appointment, tran_id = _find_appointment_from_payment(payload)
    if appointment:
        if appointment.payment_status == 'paid':
            return _payment_redirect('success', appointment)
        else:
            appointment.payment_status = 'cancelled'
            appointment.transaction_id = tran_id or appointment.transaction_id
            appointment.payment_method = _payment_method_from(payload)
            db.session.commit()

    return _payment_redirect('cancelled', appointment)


@app.route('/api/specialties', methods=['GET'])
def get_specialties():
    specialties = db.session.query(Doctor.specialty).filter_by(approval_status='approved').distinct().all()
    return jsonify([s[0] for s in specialties])


# =========================
# Emergency Assist routes
# =========================

@app.route('/api/emergency/providers', methods=['GET'])
@login_required
def get_emergency_providers():
    providers = EmergencyProvider.query.order_by(EmergencyProvider.zone.asc()).all()
    return jsonify([provider.to_dict() for provider in providers])


@app.route('/api/emergency/nearest', methods=['POST'])
@login_required
def get_nearest_emergency_provider():
    data = request.get_json(silent=True) or {}
    latitude, longitude, error = _parse_coordinates(data)
    if error:
        return jsonify({'error': error}), 400

    nearest, distance_km = _nearest_provider(latitude, longitude)
    if not nearest:
        return jsonify({'error': 'No emergency providers are configured'}), 404

    return jsonify({
        'provider': nearest.to_dict(),
        'distance_km': distance_km
    })


@app.route('/api/emergency/summary', methods=['POST'])
@login_required
def get_emergency_summary():
    if not _patient_required():
        return jsonify({'error': 'Emergency summaries are available for patient accounts only'}), 403

    summary = _build_emergency_summary(session['user_id'])
    return jsonify({
        'summary': summary,
        'disclaimer': 'Generated from CareLink history and not a medical diagnosis.'
    })


@app.route('/api/emergency/alert', methods=['POST'])
@login_required
def create_emergency_alert():
    if not _patient_required():
        return jsonify({'error': 'Emergency alerts are available for patient accounts only'}), 403

    data = request.get_json(silent=True) or {}
    latitude, longitude, error = _parse_coordinates(data)
    if error:
        return jsonify({'error': error}), 400

    provider = None
    provider_id = data.get('nearest_provider_id')
    if provider_id:
        try:
            provider = EmergencyProvider.query.get(int(provider_id))
        except (TypeError, ValueError):
            provider = None

    distance_km = None
    if not provider:
        provider, distance_km = _nearest_provider(latitude, longitude)
    elif provider:
        distance_km = round(haversine_distance_km(latitude, longitude, provider.latitude, provider.longitude), 2)

    summary = str(data.get('summary') or '').strip() or _build_emergency_summary(session['user_id'])

    alert = EmergencyAlert(
        user_id=session['user_id'],
        latitude=latitude,
        longitude=longitude,
        nearest_provider_id=provider.id if provider else None,
        summary=summary
    )
    db.session.add(alert)
    db.session.commit()

    return jsonify({
        'message': 'Emergency alert saved',
        'alert': alert.to_dict(),
        'distance_km': distance_km
    }), 201


# =========================
# Demo admin doctor approval routes
# =========================

@app.route('/api/admin/doctors', methods=['GET'])
@admin_required
def admin_get_doctors():
    """Simple demo admin listing. The public navbar keeps this page hidden unless a user is admin."""
    status = request.args.get('status', '')
    doctors_query = Doctor.query

    if status:
        doctors_query = doctors_query.filter_by(approval_status=status)

    doctors = doctors_query.order_by(Doctor.created_at.desc()).all()
    return jsonify([doctor.to_dict() for doctor in doctors])


@app.route('/api/admin/doctors/<int:doctor_id>/approve', methods=['POST'])
@admin_required
def admin_approve_doctor(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    doctor.approval_status = 'approved'
    db.session.commit()
    return jsonify({
        'message': 'Doctor approved',
        'doctor': doctor.to_dict()
    })


@app.route('/api/admin/doctors/<int:doctor_id>', methods=['PUT'])
@admin_required
def admin_update_doctor(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    try:
        payload = _doctor_payload(request.get_json(silent=True) or {}, doctor)
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    _apply_doctor_payload(doctor, payload)
    db.session.commit()
    return jsonify({
        'message': 'Doctor profile updated',
        'doctor': doctor.to_dict()
    })


@app.route('/api/admin/doctors/<int:doctor_id>/availability', methods=['GET'])
@admin_required
def admin_get_doctor_availability(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    payload = _admin_availability_payload(doctor)
    db.session.commit()
    return jsonify(payload)


@app.route('/api/admin/doctors/<int:doctor_id>/availability', methods=['PUT'])
@admin_required
def admin_update_doctor_availability(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    try:
        entries = _parse_admin_availability(request.get_json(silent=True) or {})
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    DoctorAvailability.query.filter_by(doctor_id=doctor.id).delete()
    for entry in entries:
        db.session.add(DoctorAvailability(doctor_id=doctor.id, **entry))
    db.session.commit()
    return jsonify({
        'message': 'Doctor availability updated',
        'availability': _admin_availability_payload(doctor)
    })


@app.route('/api/admin/doctors/<int:doctor_id>/reject', methods=['POST'])
@admin_required
def admin_reject_doctor(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    doctor.approval_status = 'rejected'
    db.session.commit()
    return jsonify({
        'message': 'Doctor rejected',
        'doctor': doctor.to_dict()
    })


# =========================
# Initialize database
# =========================

def _table_columns(table_name):
    rows = db.session.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
    return {row[1] for row in rows}


def ensure_demo_schema():
    """Add small demo-era columns to an existing SQLite DB without requiring Flask-Migrate."""
    users_columns = _table_columns('users')
    doctors_columns = _table_columns('doctors')
    appointments_columns = _table_columns('appointments')

    if 'role' not in users_columns:
        db.session.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'patient'"))

    doctor_column_sql = {
        'user_id': "ALTER TABLE doctors ADD COLUMN user_id INTEGER",
        'qualification': "ALTER TABLE doctors ADD COLUMN qualification VARCHAR(250)",
        'experience_years': "ALTER TABLE doctors ADD COLUMN experience_years INTEGER DEFAULT 0",
        'approval_status': "ALTER TABLE doctors ADD COLUMN approval_status VARCHAR(20) DEFAULT 'approved'"
    }

    for column_name, ddl in doctor_column_sql.items():
        if column_name not in doctors_columns:
            db.session.execute(text(ddl))

    appointment_column_sql = {
        'payment_status': "ALTER TABLE appointments ADD COLUMN payment_status TEXT DEFAULT 'pending'",
        'transaction_id': "ALTER TABLE appointments ADD COLUMN transaction_id TEXT",
        'payment_method': "ALTER TABLE appointments ADD COLUMN payment_method TEXT"
    }

    for column_name, ddl in appointment_column_sql.items():
        if column_name not in appointments_columns:
            db.session.execute(text(ddl))

    db.session.execute(text("UPDATE users SET role = 'patient' WHERE role IS NULL OR role = ''"))
    db.session.execute(text("UPDATE doctors SET approval_status = 'approved' WHERE approval_status IS NULL OR approval_status = ''"))
    db.session.execute(text("UPDATE doctors SET experience_years = 0 WHERE experience_years IS NULL"))
    db.session.execute(text("UPDATE appointments SET payment_status = 'pending' WHERE payment_status IS NULL OR payment_status = ''"))
    db.session.commit()


def seed_emergency_providers():
    """Seed Rajshahi demo emergency providers once, preserving existing records."""
    if EmergencyProvider.query.first():
        return

    for provider_data in RAJSHAHI_EMERGENCY_PROVIDERS:
        db.session.add(EmergencyProvider(**provider_data))

    db.session.commit()


def seed_doctor_availability(doctor, commit=True):
    """Seed a doctor's availability only when they do not already have rows."""
    if DoctorAvailability.query.filter_by(doctor_id=doctor.id).first():
        return

    specialty_slots = set(_specialty_slots(doctor.specialty))
    for day in DAYS_OF_WEEK:
        for slot_time in DEFAULT_SLOT_TIMES:
            db.session.add(DoctorAvailability(
                doctor_id=doctor.id,
                day_of_week=day,
                slot_time=slot_time,
                is_available=slot_time in specialty_slots
            ))

    if commit:
        db.session.commit()


def seed_default_doctor_availability():
    """Add default availability for existing doctors without overwriting admin edits."""
    doctors = Doctor.query.all()
    changed = False
    for doctor in doctors:
        if not DoctorAvailability.query.filter_by(doctor_id=doctor.id).first():
            seed_doctor_availability(doctor, commit=False)
            changed = True
    if changed:
        db.session.commit()


def init_db():
    with app.app_context():
        db.create_all()
        ensure_demo_schema()
        seed_default_doctor_availability()
        seed_emergency_providers()


if __name__ == '__main__':
    init_db()
    print("\nCareLink Backend Server Starting...")
    print("API running at: http://127.0.0.1:5000")
    print("API Endpoints:")
    print("   - GET  /api/doctors")
    print("   - POST /api/doctors")
    print("   - GET  /api/doctors/<id>")
    print("   - PUT  /api/doctors/<id>")
    print("   - DELETE /api/doctors/<id>")
    print("   - POST /api/appointments")
    print("   - GET  /api/appointments")
    print("   - POST /api/appointments/<id>/cancel")
    print("   - POST /api/payments/initiate")
    print("   - GET/POST /api/payments/success")
    print("   - GET/POST /api/payments/fail")
    print("   - GET/POST /api/payments/cancel")
    print("   - GET  /api/specialties")
    print("   - GET  /api/emergency/providers")
    print("   - POST /api/emergency/nearest")
    print("   - POST /api/emergency/summary")
    print("   - POST /api/emergency/alert")
    print("   - GET  /api/admin/doctors")
    print("   - PUT  /api/admin/doctors/<id>")
    print("   - POST /api/admin/doctors/<id>/approve")
    print("   - POST /api/admin/doctors/<id>/reject")
    print("   - POST /api/register")
    print("   - POST /api/login")
    print("   - POST /api/logout")
    print("   - GET  /api/me")
    print("   - POST /api/session/start")
    print("   - POST /api/chat/message")
    print("   - GET  /api/chat/history")
    print("\n")
    app.run(debug=True, port=5000)
