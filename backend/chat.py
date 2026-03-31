from flask import Blueprint, request, jsonify, session
from models import db, ChatSession, ChatMessage, User
from auth import login_required
from datetime import datetime
import json
import uuid

chat_bp = Blueprint('chat', __name__)

# =========================
# Category configuration
# =========================

CATEGORY_KEYWORDS = {
    'cardio': [
        'chest pain', 'chest', 'heart', 'palpitation', 'palpitations',
        'pressure', 'shortness of breath', 'breathless', 'tightness',
        'arm pain', 'jaw pain'
    ],
    'skin': [
        'rash', 'itch', 'itching', 'acne', 'pimple', 'eczema', 'psoriasis',
        'skin', 'redness', 'blister', 'hives', 'allergy', 'spots'
    ],
    'gastro': [
        'stomach', 'abdominal', 'abdomen', 'nausea', 'vomit', 'vomiting',
        'diarrhea', 'constipation', 'gas', 'bloating', 'indigestion',
        'acid', 'heartburn', 'food poisoning'
    ],
    'respiratory': [
        'cough', 'cold', 'fever', 'throat', 'wheezing', 'breathing',
        'sore throat', 'runny nose', 'flu', 'phlegm'
    ],
    'neuro': [
        'headache', 'migraine', 'dizzy', 'dizziness', 'numbness', 'weakness',
        'seizure', 'confusion', 'fainting', 'tingling'
    ],
    'ortho': [
        'bone', 'joint', 'muscle', 'back pain', 'back', 'knee', 'neck pain',
        'shoulder pain', 'swelling', 'arthritis', 'sprain', 'injury', 'fall'
    ],
    'eye': [
        'eye', 'vision', 'blurred', 'red eye', 'eye pain', 'watering',
        'itchy eyes'
    ],
    'ent': [
        'ear', 'hearing', 'nose', 'sinus', 'ear pain', 'ear discharge',
        'throat pain', 'tonsil'
    ]
}

CATEGORY_LABELS = {
    'cardio': 'Heart / Cardiovascular',
    'skin': 'Skin',
    'gastro': 'Digestive / Gastro',
    'respiratory': 'Respiratory',
    'neuro': 'Neurological',
    'ortho': 'Bone / Joint / Muscle',
    'eye': 'Eye',
    'ent': 'ENT',
    'general': 'General'
}

SPECIALIST_MAP = {
    'cardio': 'Cardiologist',
    'skin': 'Dermatologist',
    'gastro': 'Gastroenterologist',
    'respiratory': 'General Physician',
    'neuro': 'Neurologist',
    'ortho': 'Orthopedic',
    'eye': 'Ophthalmologist',
    'ent': 'ENT Specialist',
    'general': 'General Physician'
}

QUESTION_FLOWS = {
    'cardio': [
        {
            'key': 'duration',
            'question': 'How long have you had the chest pain or heart-related symptom?',
            'options': ['Less than 1 hour', '1-24 hours', '1-3 days', 'More than 3 days']
        },
        {
            'key': 'severity',
            'question': 'How severe is it?',
            'options': ['Mild', 'Moderate', 'Severe']
        },
        {
            'key': 'shortness_breath',
            'question': 'Are you also having shortness of breath? (yes/no)'
        },
        {
            'key': 'radiating_pain',
            'question': 'Does the pain spread to your arm, jaw, shoulder, or back? (yes/no)'
        },
        {
            'key': 'sweating_nausea',
            'question': 'Are you also sweating, feeling nauseated, or dizzy? (yes/no)'
        },
        {
            'key': 'past_history',
            'question': 'Do you have any history of high blood pressure, diabetes, or heart disease? (or type none)'
        },
        {
            'key': 'bp_reading',
            'question': 'Do you know your current blood pressure reading? Type like 120/80 or type no'
        }
    ],
    'skin': [
        {
            'key': 'duration',
            'question': 'How long have you had the skin problem?',
            'options': ['Today', '1-3 days', '3-7 days', 'More than a week']
        },
        {
            'key': 'severity',
            'question': 'How severe is it?',
            'options': ['Mild', 'Moderate', 'Severe']
        },
        {
            'key': 'itching',
            'question': 'Is it itchy? (yes/no)'
        },
        {
            'key': 'painful',
            'question': 'Is it painful or burning? (yes/no)'
        },
        {
            'key': 'spreading',
            'question': 'Is the rash or skin problem spreading? (yes/no)'
        },
        {
            'key': 'fever',
            'question': 'Do you also have fever? (yes/no)'
        },
        {
            'key': 'trigger',
            'question': 'Did it start after using a new soap, cream, food, or medicine? (yes/no)'
        },
        {
            'key': 'past_history',
            'question': 'Do you have any history of allergies or skin disease? (or type none)'
        }
    ],
    'gastro': [
        {
            'key': 'duration',
            'question': 'How long have you had the stomach or digestive problem?',
            'options': ['Less than 24 hours', '1-3 days', '3-7 days', 'More than a week']
        },
        {
            'key': 'severity',
            'question': 'How severe is it?',
            'options': ['Mild', 'Moderate', 'Severe']
        },
        {
            'key': 'vomiting',
            'question': 'Are you vomiting? (yes/no)'
        },
        {
            'key': 'diarrhea',
            'question': 'Do you have diarrhea? (yes/no)'
        },
        {
            'key': 'pain_location',
            'question': 'Where is the pain located? (upper abdomen / lower abdomen / all over / no pain)'
        },
        {
            'key': 'food_related',
            'question': 'Does it get worse after eating? (yes/no)'
        },
        {
            'key': 'blood',
            'question': 'Have you noticed blood in vomit or stool? (yes/no)'
        },
        {
            'key': 'past_history',
            'question': 'Do you have any past history like ulcer, gastritis, or digestive disease? (or type none)'
        }
    ],
    'respiratory': [
        {
            'key': 'duration',
            'question': 'How long have you had the breathing, cough, or throat problem?',
            'options': ['Today', '1-3 days', '3-7 days', 'More than a week']
        },
        {
            'key': 'severity',
            'question': 'How severe is it?',
            'options': ['Mild', 'Moderate', 'Severe']
        },
        {
            'key': 'fever',
            'question': 'Do you have fever? (yes/no)'
        },
        {
            'key': 'phlegm',
            'question': 'Are you coughing up phlegm or mucus? (yes/no)'
        },
        {
            'key': 'breathing_difficulty',
            'question': 'Are you having difficulty breathing even while resting? (yes/no)'
        },
        {
            'key': 'chest_tightness',
            'question': 'Do you feel chest tightness or wheezing? (yes/no)'
        },
        {
            'key': 'past_history',
            'question': 'Do you have asthma, allergy, or any lung disease? (or type none)'
        }
    ],
    'neuro': [
        {
            'key': 'duration',
            'question': 'How long have you had this headache, dizziness, or nerve-related symptom?',
            'options': ['Less than 1 hour', '1-24 hours', '1-3 days', 'More than 3 days']
        },
        {
            'key': 'severity',
            'question': 'How severe is it?',
            'options': ['Mild', 'Moderate', 'Severe']
        },
        {
            'key': 'sudden_onset',
            'question': 'Did it start suddenly? (yes/no)'
        },
        {
            'key': 'numbness',
            'question': 'Do you have numbness, weakness, or trouble speaking? (yes/no)'
        },
        {
            'key': 'vision_change',
            'question': 'Do you have blurred vision or confusion? (yes/no)'
        },
        {
            'key': 'past_history',
            'question': 'Do you have migraine, stroke history, or neurological disease? (or type none)'
        }
    ],
    'ortho': [
        {
            'key': 'duration',
            'question': 'How long have you had the bone, joint, muscle, or back problem?',
            'options': ['Today', '1-3 days', '3-7 days', 'More than a week']
        },
        {
            'key': 'severity',
            'question': 'How severe is it?',
            'options': ['Mild', 'Moderate', 'Severe']
        },
        {
            'key': 'injury',
            'question': 'Did it start after an injury, fall, or lifting something heavy? (yes/no)'
        },
        {
            'key': 'swelling',
            'question': 'Is there swelling? (yes/no)'
        },
        {
            'key': 'movement_problem',
            'question': 'Do you have trouble moving the affected area? (yes/no)'
        },
        {
            'key': 'past_history',
            'question': 'Do you have arthritis or any bone/joint disease? (or type none)'
        }
    ],
    'eye': [
        {
            'key': 'duration',
            'question': 'How long have you had the eye problem?',
            'options': ['Today', '1-3 days', '3-7 days', 'More than a week']
        },
        {
            'key': 'severity',
            'question': 'How severe is it?',
            'options': ['Mild', 'Moderate', 'Severe']
        },
        {
            'key': 'vision_loss',
            'question': 'Do you have blurred vision or sudden vision loss? (yes/no)'
        },
        {
            'key': 'redness',
            'question': 'Is the eye red? (yes/no)'
        },
        {
            'key': 'discharge',
            'question': 'Is there discharge or watering? (yes/no)'
        },
        {
            'key': 'painful',
            'question': 'Is it painful? (yes/no)'
        }
    ],
    'ent': [
        {
            'key': 'duration',
            'question': 'How long have you had the ear, nose, or throat problem?',
            'options': ['Today', '1-3 days', '3-7 days', 'More than a week']
        },
        {
            'key': 'severity',
            'question': 'How severe is it?',
            'options': ['Mild', 'Moderate', 'Severe']
        },
        {
            'key': 'fever',
            'question': 'Do you have fever? (yes/no)'
        },
        {
            'key': 'discharge',
            'question': 'Is there any ear discharge, nasal discharge, or throat pus? (yes/no)'
        },
        {
            'key': 'hearing_problem',
            'question': 'Do you have reduced hearing or ear blockage? (yes/no)'
        },
        {
            'key': 'past_history',
            'question': 'Do you have sinus problems, tonsil issues, or ear infections before? (or type none)'
        }
    ],
    'general': [
        {
            'key': 'duration',
            'question': 'How long have you been experiencing these symptoms?',
            'options': ['Today', '1-3 days', '3-7 days', 'More than a week']
        },
        {
            'key': 'severity',
            'question': 'How severe are the symptoms?',
            'options': ['Mild', 'Moderate', 'Severe']
        },
        {
            'key': 'past_history',
            'question': 'Do you have any past medical history? (or type none)'
        }
    ]
}


# =========================
# Helper functions
# =========================

def normalize_text(text):
    return text.strip().lower() if text else ''


def is_yes(text):
    return normalize_text(text) in ['yes', 'y', 'yeah', 'yep']


def parse_json_data(raw_data):
    if not raw_data:
        return {}
    try:
        return json.loads(raw_data)
    except Exception:
        return {}


def save_bot_message(session_pk, message, message_type='text', buttons=None):
    metadata = {}
    if buttons:
        metadata['buttons'] = buttons

    bot_message = ChatMessage(
        session_id=session_pk,
        sender='bot',
        message=message,
        message_type=message_type,
        message_metadata=json.dumps(metadata) if metadata else None
    )
    db.session.add(bot_message)


def detect_category(symptoms):
    symptoms = normalize_text(symptoms)

    best_category = 'general'
    best_score = 0

    for category, keywords in CATEGORY_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            if keyword in symptoms:
                score += 1
        if score > best_score:
            best_score = score
            best_category = category

    return best_category


def get_question_flow(category):
    return QUESTION_FLOWS.get(category, QUESTION_FLOWS['general'])


def parse_bp(bp_text):
    bp_text = normalize_text(bp_text)
    if '/' not in bp_text:
        return None, None

    try:
        systolic_str, diastolic_str = bp_text.split('/')
        systolic = int(systolic_str.strip())
        diastolic = int(diastolic_str.strip())
        return systolic, diastolic
    except Exception:
        return None, None


def get_current_question(data):
    category = data.get('category', 'general')
    question_index = data.get('question_index', 0)
    questions = get_question_flow(category)

    if question_index < len(questions):
        return questions[question_index]
    return None


def get_intro_message(category):
    label = CATEGORY_LABELS.get(category, 'General')
    return f"Thank you. Your symptoms seem related to the {label} category. I'll ask a few specific questions."


def check_previous_sessions(user_id, current_symptoms):
    """
    Keep this helper so later history-aware warnings can be added.
    For now it returns light context only and does not interrupt the flow.
    """
    user = User.query.get(user_id)
    if not user:
        return None

    recent_sessions = ChatSession.query.filter_by(user_id=user_id) \
        .order_by(ChatSession.started_at.desc()) \
        .limit(5) \
        .all()

    if not recent_sessions:
        return None

    current_lower = normalize_text(current_symptoms)

    for sess in recent_sessions:
        if not sess.collected_data:
            continue

        try:
            past_data = json.loads(sess.collected_data)
            past_symptoms = normalize_text(past_data.get('symptoms', ''))

            if 'chest' in current_lower and 'chest' in past_symptoms:
                return {
                    'has_history': True,
                    'past_symptoms': past_data.get('symptoms'),
                    'past_specialty': sess.recommended_specialty,
                    'session_date': sess.started_at.strftime('%Y-%m-%d')
                }

            if 'rash' in current_lower and 'rash' in past_symptoms:
                return {
                    'has_history': True,
                    'past_symptoms': past_data.get('symptoms'),
                    'past_specialty': sess.recommended_specialty,
                    'session_date': sess.started_at.strftime('%Y-%m-%d')
                }
        except Exception:
            pass

    return None


def analyze_and_build_result(collected_data):
    category = collected_data.get('category', 'general')
    severity = normalize_text(collected_data.get('severity', ''))
    past_history = normalize_text(collected_data.get('past_history', ''))
    specialist = SPECIALIST_MAP.get(category, 'General Physician')

    risk_level = 'low'
    advice = "Monitor your symptoms and consult a healthcare professional if symptoms persist or worsen."
    is_emergency = False

    if category == 'cardio':
        score = 0

        if is_yes(collected_data.get('shortness_breath', '')):
            score += 2
        if is_yes(collected_data.get('radiating_pain', '')):
            score += 3
        if is_yes(collected_data.get('sweating_nausea', '')):
            score += 2
        if 'severe' in severity:
            score += 2
        if any(word in past_history for word in ['blood pressure', 'hypertension', 'diabetes', 'heart']):
            score += 1

        systolic, diastolic = parse_bp(collected_data.get('bp_reading', ''))
        if systolic and diastolic:
            if systolic >= 180 or diastolic >= 120:
                score += 3

        if score >= 6:
            is_emergency = True
            risk_level = 'emergency'
            specialist = 'Emergency Medicine'
            advice = "Possible serious cardiac warning signs. Seek emergency medical care immediately."
        elif score >= 3:
            risk_level = 'high'
            advice = "Your symptoms may need urgent heart evaluation. Avoid exertion and consult a doctor as soon as possible."
        elif score >= 1:
            risk_level = 'medium'
            advice = "Monitor symptoms carefully and arrange a cardiology consultation soon."
        else:
            risk_level = 'low'
            advice = "Avoid stress, heavy activity, and monitor symptoms. Consult a cardiologist if symptoms continue."

    elif category == 'skin':
        score = 0

        if is_yes(collected_data.get('spreading', '')):
            score += 2
        if is_yes(collected_data.get('fever', '')):
            score += 2
        if is_yes(collected_data.get('painful', '')):
            score += 1
        if 'severe' in severity:
            score += 2
        if is_yes(collected_data.get('trigger', '')):
            score += 1

        if score >= 5:
            risk_level = 'high'
            advice = "This skin condition may need urgent medical review, especially if it is spreading or associated with fever."
        elif score >= 3:
            risk_level = 'medium'
            advice = "Keep the area clean, avoid scratching, and consult a dermatologist."
        else:
            risk_level = 'low'
            advice = "Keep the skin clean, avoid irritants, and monitor for spreading or fever."

    elif category == 'gastro':
        score = 0

        if is_yes(collected_data.get('vomiting', '')):
            score += 1
        if is_yes(collected_data.get('diarrhea', '')):
            score += 1
        if is_yes(collected_data.get('blood', '')):
            score += 4
        if 'severe' in severity:
            score += 2
        if normalize_text(collected_data.get('pain_location', '')) in ['upper abdomen', 'lower abdomen']:
            score += 1

        if is_yes(collected_data.get('blood', '')):
            is_emergency = True
            risk_level = 'emergency'
            specialist = 'Emergency Medicine'
            advice = "Blood in vomit or stool can be serious. Please seek immediate medical attention."
        elif score >= 4:
            risk_level = 'high'
            advice = "Your digestive symptoms may need urgent evaluation. Stay hydrated and seek medical care soon."
        elif score >= 2:
            risk_level = 'medium'
            advice = "Drink fluids, avoid spicy/oily foods, and arrange a consultation if symptoms continue."
        else:
            risk_level = 'low'
            advice = "Stay hydrated and eat light foods. Seek care if symptoms worsen."

    elif category == 'respiratory':
        score = 0

        if is_yes(collected_data.get('fever', '')):
            score += 1
        if is_yes(collected_data.get('phlegm', '')):
            score += 1
        if is_yes(collected_data.get('breathing_difficulty', '')):
            score += 3
        if is_yes(collected_data.get('chest_tightness', '')):
            score += 2
        if 'severe' in severity:
            score += 2

        if is_yes(collected_data.get('breathing_difficulty', '')) and 'severe' in severity:
            is_emergency = True
            risk_level = 'emergency'
            specialist = 'Emergency Medicine'
            advice = "Severe breathing difficulty can be dangerous. Seek emergency medical care immediately."
        elif score >= 4:
            risk_level = 'high'
            advice = "Your symptoms need medical review soon, especially because of breathing involvement."
        elif score >= 2:
            risk_level = 'medium'
            advice = "Rest, drink warm fluids, and consult a doctor if symptoms continue."
        else:
            risk_level = 'low'
            advice = "Rest, stay hydrated, and monitor symptoms."

    elif category == 'neuro':
        score = 0

        if is_yes(collected_data.get('sudden_onset', '')):
            score += 2
        if is_yes(collected_data.get('numbness', '')):
            score += 3
        if is_yes(collected_data.get('vision_change', '')):
            score += 2
        if 'severe' in severity:
            score += 2

        if is_yes(collected_data.get('numbness', '')) and is_yes(collected_data.get('vision_change', '')):
            is_emergency = True
            risk_level = 'emergency'
            specialist = 'Emergency Medicine'
            advice = "These symptoms may indicate a serious neurological condition. Please get immediate medical care."
        elif score >= 4:
            risk_level = 'high'
            advice = "Your neurological symptoms need urgent assessment."
        elif score >= 2:
            risk_level = 'medium'
            advice = "Rest and arrange a neurology consultation soon."
        else:
            risk_level = 'low'
            advice = "Monitor symptoms and seek care if they worsen or happen again."

    elif category == 'ortho':
        score = 0

        if is_yes(collected_data.get('injury', '')):
            score += 2
        if is_yes(collected_data.get('swelling', '')):
            score += 1
        if is_yes(collected_data.get('movement_problem', '')):
            score += 2
        if 'severe' in severity:
            score += 2

        if score >= 5:
            risk_level = 'high'
            advice = "You may need urgent orthopedic evaluation, especially if movement is restricted."
        elif score >= 3:
            risk_level = 'medium'
            advice = "Rest the area, avoid strain, and consult an orthopedic specialist."
        else:
            risk_level = 'low'
            advice = "Rest, avoid heavy activity, and use cold compress if swelling is present."

    elif category == 'eye':
        score = 0

        if is_yes(collected_data.get('vision_loss', '')):
            score += 4
        if is_yes(collected_data.get('painful', '')):
            score += 2
        if is_yes(collected_data.get('redness', '')):
            score += 1
        if is_yes(collected_data.get('discharge', '')):
            score += 1

        if is_yes(collected_data.get('vision_loss', '')):
            is_emergency = True
            risk_level = 'emergency'
            specialist = 'Emergency Medicine'
            advice = "Sudden change in vision can be serious. Seek immediate eye care."
        elif score >= 3:
            risk_level = 'high'
            advice = "Your eye symptoms need prompt ophthalmology evaluation."
        else:
            risk_level = 'medium'
            advice = "Avoid rubbing the eye and arrange an eye consultation."

    elif category == 'ent':
        score = 0

        if is_yes(collected_data.get('fever', '')):
            score += 1
        if is_yes(collected_data.get('discharge', '')):
            score += 2
        if is_yes(collected_data.get('hearing_problem', '')):
            score += 2
        if 'severe' in severity:
            score += 2

        if score >= 4:
            risk_level = 'high'
            advice = "Your symptoms should be checked by an ENT specialist soon."
        elif score >= 2:
            risk_level = 'medium'
            advice = "Arrange an ENT consultation and avoid self-medicating without advice."
        else:
            risk_level = 'low'
            advice = "Monitor symptoms and seek care if they worsen."

    else:
        if 'severe' in severity:
            risk_level = 'high'
            advice = "Your symptoms appear significant. Please see a doctor soon."
        elif 'moderate' in severity:
            risk_level = 'medium'
            advice = "Please schedule a check-up if symptoms persist."
        else:
            risk_level = 'low'
            advice = "Rest, stay hydrated, and monitor symptoms."

    return {
        'category': category,
        'risk_level': risk_level,
        'specialist': specialist,
        'advice': advice,
        'is_emergency': is_emergency
    }


def build_final_message(collected_data, result):
    category_label = CATEGORY_LABELS.get(result['category'], 'General')
    symptoms = collected_data.get('symptoms', '')
    duration = collected_data.get('duration', '')
    severity = collected_data.get('severity', '')

    if result['is_emergency']:
        return f"""🚨 **EMERGENCY ALERT** 🚨

Your answers suggest a potentially serious condition.

**Assessment Summary:**
- Symptom Category: {category_label}
- Risk Level: {result['risk_level'].upper()}
- Recommended Action: Immediate emergency care

**Advice:**
{result['advice']}

**Important:**
- Go to the nearest emergency room immediately
- Do not delay if symptoms are severe or worsening
- This chatbot does not provide a final diagnosis
""".strip()

    if result['risk_level'] == 'high':
        urgency_message = "⚠️ Your symptoms appear concerning and should be checked soon."
    elif result['risk_level'] == 'medium':
        urgency_message = "Your symptoms should be evaluated by a doctor."
    else:
        urgency_message = "Your symptoms appear manageable for now, but monitor them carefully."

    return f"""⚠️ **Disclaimer**: This is not a medical diagnosis. Please consult a qualified healthcare professional for proper diagnosis and treatment.

**Health Assessment Complete**

{urgency_message}

**Your Summary:**
- Symptom Category: {category_label}
- Main Symptoms: {symptoms}
- Duration: {duration}
- Severity: {severity}
- Risk Level: {result['risk_level'].capitalize()}

**Recommendation:**
- Specialist: {result['specialist']}
- Advice: {result['advice']}

**Next Steps:**
- Browse the doctor directory to find a {result['specialist']}
- Book an appointment if symptoms continue or worsen
- Seek urgent care immediately if red-flag symptoms appear
""".strip()


def get_buttons_for_result(result):
    if result['is_emergency']:
        return [
            {'text': 'Find Emergency Room', 'action': 'emergency_rooms'},
            {'text': 'Start New Assessment', 'action': 'new_assessment'}
        ]

    return [
        {'text': f'Browse {result["specialist"]}s', 'action': 'browse_doctors', 'specialty': result['specialist']},
        {'text': 'Book Appointment', 'action': 'book_appointment', 'specialty': result['specialist']},
        {'text': 'Start New Assessment', 'action': 'new_assessment'}
    ]


# =========================
# Routes
# =========================

@chat_bp.route('/api/session/start', methods=['POST'])
@login_required
def start_session():
    try:
        user_id = session['user_id']
        session_id = str(uuid.uuid4())

        chat_session = ChatSession(
            user_id=user_id,
            session_id=session_id,
            current_step='initial',
            collected_data=json.dumps({})
        )

        db.session.add(chat_session)
        db.session.commit()

        initial_message = (
            "Hello! I'm your Health Assistant. Please describe your symptoms in detail. "
            "For example: chest pain, skin rash, stomach pain, breathing problem, headache, etc."
        )

        save_bot_message(chat_session.id, initial_message, 'text')

        chat_session.current_step = 'collect_symptoms'
        db.session.commit()

        return jsonify({
            'session_id': session_id,
            'db_session_id': chat_session.id,
            'message': initial_message,
            'step': 'collect_symptoms'
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@chat_bp.route('/api/chat/message', methods=['POST'])
@login_required
def send_message():
    try:
        user_id = session['user_id']
        data = request.get_json()

        message = data.get('message', '').strip()
        db_session_id = data.get('db_session_id')

        if not message or not db_session_id:
            return jsonify({'error': 'Message and session ID required'}), 400

        chat_session = ChatSession.query.get(db_session_id)
        if not chat_session or chat_session.user_id != user_id:
            return jsonify({'error': 'Invalid session'}), 400

        user_message = ChatMessage(
            session_id=chat_session.id,
            sender='user',
            message=message,
            message_type='text'
        )
        db.session.add(user_message)

        collected_data = parse_json_data(chat_session.collected_data)
        current_step = chat_session.current_step or 'collect_symptoms'

        # Step 1: collect first symptom message
        if current_step == 'collect_symptoms':
            collected_data['symptoms'] = message
            collected_data['category'] = detect_category(message)
            collected_data['question_index'] = 0

            history = check_previous_sessions(user_id, message)

            intro_message = get_intro_message(collected_data['category'])
            if history and history.get('has_history'):
                intro_message += f"\n\nNote: I found a related past consultation from {history['session_date']}."

            first_question = get_current_question(collected_data)

            if not first_question:
                result = analyze_and_build_result(collected_data)
                final_message = build_final_message(collected_data, result)
                buttons = get_buttons_for_result(result)
                msg_type = 'emergency' if result['is_emergency'] else 'recommendation'

                save_bot_message(chat_session.id, final_message, msg_type, buttons)

                chat_session.current_step = 'completed'
                chat_session.collected_data = json.dumps(collected_data)
                chat_session.recommended_specialty = result['specialist']
                chat_session.risk_level = result['risk_level']
                chat_session.ended_at = datetime.utcnow()
                db.session.commit()

                return jsonify({
                    'message': final_message,
                    'message_type': msg_type,
                    'buttons': buttons,
                    'specialty': result['specialist'],
                    'risk_level': result['risk_level']
                }), 200

            response_message = intro_message + "\n\n" + first_question['question']

            chat_session.current_step = 'questioning'
            chat_session.collected_data = json.dumps(collected_data)
            db.session.commit()

            return jsonify({
                'message': response_message,
                'message_type': 'text',
                'step': 'questioning'
            }), 200

        # Step 2: handle category-specific answers
        elif current_step == 'questioning':
            category = collected_data.get('category', 'general')
            questions = get_question_flow(category)
            question_index = collected_data.get('question_index', 0)

            if question_index < len(questions):
                current_question = questions[question_index]
                collected_data[current_question['key']] = message
                collected_data['question_index'] = question_index + 1

            next_question = get_current_question(collected_data)

            if next_question:
                chat_session.collected_data = json.dumps(collected_data)
                db.session.commit()

                save_bot_message(chat_session.id, next_question['question'], 'text')
                db.session.commit()

                return jsonify({
                    'message': next_question['question'],
                    'message_type': 'text',
                    'step': 'questioning'
                }), 200

            result = analyze_and_build_result(collected_data)
            final_message = build_final_message(collected_data, result)
            buttons = get_buttons_for_result(result)
            msg_type = 'emergency' if result['is_emergency'] else 'recommendation'

            save_bot_message(chat_session.id, final_message, msg_type, buttons)

            chat_session.current_step = 'completed'
            chat_session.collected_data = json.dumps(collected_data)
            chat_session.recommended_specialty = result['specialist']
            chat_session.risk_level = result['risk_level']
            chat_session.ended_at = datetime.utcnow()
            db.session.commit()

            return jsonify({
                'message': final_message,
                'message_type': msg_type,
                'buttons': buttons,
                'specialty': result['specialist'],
                'risk_level': result['risk_level']
            }), 200

        elif current_step == 'completed':
            completed_message = "This assessment is already complete. Please start a new assessment if you'd like another consultation."
            buttons = [{'text': 'Start New Assessment', 'action': 'new_assessment'}]

            save_bot_message(chat_session.id, completed_message, 'text', buttons)
            db.session.commit()

            return jsonify({
                'message': completed_message,
                'message_type': 'text',
                'buttons': buttons
            }), 200

        else:
            fallback_message = "Sorry, I couldn't continue the assessment properly. Please start a new assessment."
            buttons = [{'text': 'Start New Assessment', 'action': 'new_assessment'}]

            save_bot_message(chat_session.id, fallback_message, 'text', buttons)
            db.session.commit()

            return jsonify({
                'message': fallback_message,
                'message_type': 'text',
                'buttons': buttons
            }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@chat_bp.route('/api/chat/history', methods=['GET'])
@login_required
def get_chat_history():
    try:
        user_id = session['user_id']

        sessions = ChatSession.query.filter_by(user_id=user_id) \
            .order_by(ChatSession.started_at.desc()) \
            .limit(10) \
            .all()

        history = []
        for sess in sessions:
            messages = ChatMessage.query.filter_by(session_id=sess.id) \
                .order_by(ChatMessage.timestamp.asc()) \
                .all()

            history.append({
                'session': sess.to_dict(),
                'messages': [msg.to_dict() for msg in messages]
            })

        return jsonify({'history': history}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@chat_bp.route('/api/chat/session/<int:session_id>', methods=['GET'])
@login_required
def get_session_messages(session_id):
    try:
        user_id = session['user_id']

        chat_session = ChatSession.query.get(session_id)
        if not chat_session or chat_session.user_id != user_id:
            return jsonify({'error': 'Session not found'}), 404

        messages = ChatMessage.query.filter_by(session_id=session_id) \
            .order_by(ChatMessage.timestamp.asc()) \
            .all()

        return jsonify({
            'session': chat_session.to_dict(),
            'messages': [msg.to_dict() for msg in messages]
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500