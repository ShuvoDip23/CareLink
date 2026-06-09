from flask import Blueprint, request, jsonify, session
from models import db, ChatSession, ChatMessage, User
from auth import login_required
from datetime import datetime
import json
import uuid
import os
import urllib.request
import urllib.error
import re

chat_bp = Blueprint('chat', __name__)
print("=== UPDATED LLM-DRIVEN CHAT.PY IS RUNNING ===")


# =========================
# Constants / configuration
# =========================

MAX_DYNAMIC_QUESTIONS = 5

EMERGENCY_PATTERNS = [
    r"\b(can'?t breathe|cannot breathe|severe breathing|breathing difficulty)\b",
    r"\b(chest pain.*left arm|left arm.*chest pain)\b",
    r"\b(chest pain.*jaw|jaw.*chest pain)\b",
    r"\b(fainted|passed out|unconscious)\b",
    r"\b(stroke|slurred speech|one side weak|one-sided weakness)\b",
    r"\b(seizure)\b",
    r"\b(coughing blood|vomiting blood|blood in stool)\b",
    r"\b(sudden vision loss)\b",
    r"\b(severe allergic reaction|swollen tongue|throat closing)\b",
]

GENERIC_FALLBACK_QUESTIONS = [
    "How long have you had these symptoms?",
    "How severe are the symptoms: mild, moderate, or severe?",
    "Do you have any fever, shortness of breath, vomiting, or severe weakness?",
    "Do the symptoms get worse with movement, eating, or physical activity?"
]


# =========================
# Helpers
# =========================

def normalize_text(text):
    return text.strip().lower() if text else ""


def parse_json_data(raw_data):
    if not raw_data:
        return {}
    try:
        return json.loads(raw_data)
    except Exception:
        return {}


def to_json_string(data):
    try:
        return json.dumps(data)
    except Exception:
        return "{}"


def save_bot_message(session_pk, message, message_type="text", buttons=None, extra_payload=None):
    metadata = {}
    if buttons:
        metadata["buttons"] = buttons
    if extra_payload:
        metadata["extra_payload"] = extra_payload

    bot_message = ChatMessage(
        session_id=session_pk,
        sender="bot",
        message=message,
        message_type=message_type,
        message_metadata=json.dumps(metadata) if metadata else None
    )
    db.session.add(bot_message)


def extract_json_from_llm_content(content):
    if not content:
        return None

    content = content.strip()

    try:
        return json.loads(content)
    except Exception:
        pass

    start = content.find("{")
    end = content.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(content[start:end + 1])
        except Exception:
            return None

    return None


def call_openrouter(messages, temperature=0.2, max_tokens=700):
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return None

    payload = {
        "model": "openrouter/auto",
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens
    }

    try:
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:5500",
                "X-Title": "CareLink Medical Assistant"
            },
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=40) as response:
            raw_response = response.read().decode("utf-8")
            result = json.loads(raw_response)

        choices = result.get("choices", [])
        if not choices:
            return None

        return choices[0].get("message", {}).get("content")

    except urllib.error.HTTPError as e:
        try:
            print("OPENROUTER HTTP ERROR:", e.read().decode("utf-8"))
        except Exception:
            print("OPENROUTER HTTP ERROR: could not read body")
        return None
    except Exception as e:
        print("call_openrouter failed:", e)
        return None


def emergency_rule_check(text, collected_data=None):
    text = normalize_text(text)
    collected_data = collected_data or {}

    for pattern in EMERGENCY_PATTERNS:
        if re.search(pattern, text):
            return {
                "is_emergency": True,
                "reason": "Your message includes warning signs that may need urgent medical attention.",
                "matched_by": "rule"
            }

    answers_text = ""
    answers = collected_data.get("answers", {})
    if isinstance(answers, dict):
        answers_text = " ".join(str(v) for v in answers.values())

    all_text = " ".join([
        normalize_text(text),
        normalize_text(collected_data.get("symptoms", "")),
        normalize_text(answers_text)
    ])

    red_flag_terms = [
        "shortness of breath",
        "left arm",
        "jaw",
        "fainting",
        "slurred speech",
        "blood in stool",
        "vomiting blood",
        "sudden vision loss",
        "severe weakness",
        "sweating",
        "crushing chest pain"
    ]
    match_count = sum(1 for term in red_flag_terms if term in all_text)

    if match_count >= 2:
        return {
            "is_emergency": True,
            "reason": "Multiple serious warning signs were detected.",
            "matched_by": "rule"
        }

    return {
        "is_emergency": False,
        "reason": "",
        "matched_by": None
    }


def requires_deeper_questioning(symptoms_text):
    text = normalize_text(symptoms_text)

    ambiguous_patterns = [
        "chest pain",
        "abdominal pain",
        "stomach pain",
        "headache",
        "dizziness",
        "shortness of breath",
        "breathing problem",
        "back pain",
        "fainting",
        "weakness"
    ]

    return any(item in text for item in ambiguous_patterns)


def check_previous_sessions(user_id, current_symptoms):
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
            past_symptoms = normalize_text(past_data.get("symptoms", ""))

            common_words = set(current_lower.split()) & set(past_symptoms.split())
            if len(common_words) >= 2:
                return {
                    "has_history": True,
                    "past_symptoms": past_data.get("symptoms"),
                    "past_specialty": sess.recommended_specialty,
                    "session_date": sess.started_at.strftime("%Y-%m-%d")
                }
        except Exception:
            pass

    return None


# =========================
# LLM stage 1: normalization
# =========================

def normalize_input_with_llm(user_text):
    fallback = {
        "raw_input": user_text,
        "normalized_text": user_text.strip(),
        "corrected_symptoms": [],
        "duration": "",
        "severity": "",
        "body_location": ""
    }

    system_prompt = """
You are a medical symptom input normalizer for a healthcare chatbot.

Tasks:
1. Correct likely typos
2. Rewrite the user's message into simple clean medical English
3. Extract short symptom phrases
4. Extract duration if mentioned
5. Extract severity if mentioned
6. Extract body location if mentioned

Rules:
- Do NOT diagnose
- Do NOT invent new symptoms
- Preserve the user's meaning closely
- Return JSON only
- Use exactly this schema:

{
  "raw_input": "...",
  "normalized_text": "...",
  "corrected_symptoms": ["..."],
  "duration": "",
  "severity": "",
  "body_location": ""
}
""".strip()

    content = call_openrouter(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Patient message: {user_text}"}
        ],
        temperature=0.1,
        max_tokens=250
    )

    if not content:
        return fallback

    parsed = extract_json_from_llm_content(content)
    if not parsed:
        return fallback

    return {
        "raw_input": parsed.get("raw_input", user_text),
        "normalized_text": parsed.get("normalized_text", user_text.strip()),
        "corrected_symptoms": parsed.get("corrected_symptoms", []),
        "duration": parsed.get("duration", ""),
        "severity": parsed.get("severity", ""),
        "body_location": parsed.get("body_location", "")
    }


# =========================
# LLM stage 2: reasoning
# =========================

def reason_case_with_llm(collected_data):
    symptoms = collected_data.get("symptoms", "")
    answers = collected_data.get("answers", {})
    asked_questions = collected_data.get("asked_questions", [])
    question_count = collected_data.get("question_count", 0)

    fallback = {
        "possible_conditions": [
            {"name": "General medical condition", "likelihood": "medium"}
        ],
        "possible_specialties": ["General Physician"],
        "red_flags": [],
        "follow_up_questions": [],
        "likely_specialty": "General Physician",
        "urgency": "low",
        "assessment_complete": question_count >= 3,
        "summary": "The symptoms need general medical evaluation.",
        "reasoning_note": "LLM unavailable, using fallback reasoning."
    }

    system_prompt = """
You are a cautious healthcare triage reasoning assistant for an academic symptom-checker.

You are NOT giving a final diagnosis.
You must:
1. Consider multiple possible causes, not just one
2. Ask only the most useful discriminating follow-up questions
3. Recommend a likely specialist
4. Detect red flags
5. Decide whether enough information is available

Rules:
- Be conservative and safe
- Do not claim certainty
- Do not invent facts not provided by the patient
- Keep follow-up questions short and high-value
- Ask at most 3 follow-up questions at a time
- If enough information already exists, set assessment_complete = true
- Urgency must be one of: low, medium, high, emergency
- likely_specialty should be a doctor label such as:
  Cardiologist, Gastroenterologist, Neurologist, Dermatologist,
  Pulmonologist, Orthopedic, ENT Specialist, Ophthalmologist,
  General Physician, Emergency Medicine

Important behavior:
- For ambiguous symptoms such as chest pain, abdominal pain, headache, dizziness, fainting, weakness, or breathing difficulty, do not complete the assessment too early.
- Usually ask at least 3 to 4 discriminating follow-up questions unless emergency signs are already present.
- A single descriptive answer like "sharp pain" is usually not enough to complete the assessment for chest pain.
- For chest pain, prioritize questions about radiation, shortness of breath, sweating, nausea, food relation, exertion, and pain character before completing the assessment.
- Prefer questions that help distinguish cardiac, gastric, respiratory, musculoskeletal, and anxiety-related causes when chest pain is present.

Return JSON only with this exact schema:

{
  "possible_conditions": [
    {"name": "...", "likelihood": "low|medium|high"}
  ],
  "possible_specialties": ["..."],
  "red_flags": ["..."],
  "follow_up_questions": ["..."],
  "likely_specialty": "...",
  "urgency": "low|medium|high|emergency",
  "assessment_complete": true,
  "summary": "...",
  "reasoning_note": "..."
}
""".strip()

    user_payload = {
        "symptoms": symptoms,
        "answers": answers,
        "asked_questions": asked_questions,
        "question_count": question_count
    }

    content = call_openrouter(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_payload)}
        ],
        temperature=0.2,
        max_tokens=700
    )

    if not content:
        return fallback

    parsed = extract_json_from_llm_content(content)
    if not parsed:
        return fallback

    possible_conditions = parsed.get("possible_conditions", [])
    possible_specialties = parsed.get("possible_specialties", [])
    red_flags = parsed.get("red_flags", [])
    follow_up_questions = parsed.get("follow_up_questions", [])
    likely_specialty = parsed.get("likely_specialty", "General Physician")
    urgency = parsed.get("urgency", "low")
    assessment_complete = bool(parsed.get("assessment_complete", False))
    summary = parsed.get("summary", "The symptoms need medical review.")
    reasoning_note = parsed.get("reasoning_note", "")

    if not isinstance(possible_conditions, list):
        possible_conditions = fallback["possible_conditions"]
    if not isinstance(possible_specialties, list):
        possible_specialties = fallback["possible_specialties"]
    if not isinstance(red_flags, list):
        red_flags = []
    if not isinstance(follow_up_questions, list):
        follow_up_questions = []
    if urgency not in ["low", "medium", "high", "emergency"]:
        urgency = "low"
    if not isinstance(likely_specialty, str) or not likely_specialty.strip():
        likely_specialty = "General Physician"

    if question_count >= MAX_DYNAMIC_QUESTIONS:
        assessment_complete = True
        follow_up_questions = []

    return {
        "possible_conditions": possible_conditions[:4],
        "possible_specialties": possible_specialties[:4],
        "red_flags": red_flags[:5],
        "follow_up_questions": follow_up_questions[:3],
        "likely_specialty": likely_specialty.strip(),
        "urgency": urgency,
        "assessment_complete": assessment_complete,
        "summary": summary,
        "reasoning_note": reasoning_note
    }


# =========================
# Message builders
# =========================

def get_buttons_for_result(result):
    specialist = result.get("likely_specialty", "General Physician")

    if result.get("urgency") == "emergency":
        return [
            {"text": "Find Emergency Room", "action": "emergency_rooms"},
            {"text": "Start New Assessment", "action": "new_assessment"}
        ]

    return [
        {"text": f"Browse {specialist}s", "action": "browse_doctors", "specialty": specialist},
        {"text": "Book Appointment", "action": "book_appointment", "specialty": specialist},
        {"text": "Start New Assessment", "action": "new_assessment"}
    ]


def build_emergency_message(emergency_reason):
    return f"""🚨 **EMERGENCY ALERT** 🚨

Your symptoms may need **immediate medical attention**.

**Why this is urgent:**
- {emergency_reason}

**What to do now:**
- Go to the nearest emergency room immediately
- Do not delay if symptoms are severe or worsening
- If available, seek local emergency help right away

**Important:**
This chatbot does **not** provide a final medical diagnosis.
""".strip()


def build_question_message(reasoning):
    lines = [
        "I’m considering a few possible causes and need a little more information before suggesting the most appropriate specialist.",
        "",
        "**Possible concerns being considered:**"
    ]

    conditions = reasoning.get("possible_conditions", [])
    if conditions:
        for item in conditions:
            name = item.get("name", "Possible condition")
            likelihood = item.get("likelihood", "medium")
            lines.append(f"- {name} ({likelihood} likelihood)")
    else:
        lines.append("- General medical evaluation needed")

    red_flags = reasoning.get("red_flags", [])
    if red_flags:
        lines.append("")
        lines.append("**Important warning signs I am checking for:**")
        for flag in red_flags[:3]:
            lines.append(f"- {flag}")

    follow_up = reasoning.get("follow_up_questions", [])
    if follow_up:
        lines.append("")
        lines.append(f"**Next question:** {follow_up[0]}")

    return "\n".join(lines).strip()


def build_final_message(collected_data, reasoning):
    symptoms = collected_data.get("symptoms", "")
    specialist = reasoning.get("likely_specialty", "General Physician")
    urgency = reasoning.get("urgency", "low")
    summary = reasoning.get("summary", "The symptoms need medical evaluation.")
    red_flags = reasoning.get("red_flags", [])
    possible_conditions = reasoning.get("possible_conditions", [])

    if urgency == "emergency":
        reason = red_flags[0] if red_flags else "Serious warning signs may be present."
        return build_emergency_message(reason)

    urgency_text = {
        "low": "Your symptoms appear lower risk right now, but they still deserve proper attention if they continue.",
        "medium": "Your symptoms should be evaluated by a doctor.",
        "high": "Your symptoms appear concerning and should be checked soon."
    }.get(urgency, "Your symptoms should be evaluated by a doctor.")

    lines = [
        "⚠️ **Disclaimer**: This is not a medical diagnosis. Please consult a qualified healthcare professional for proper diagnosis and treatment.",
        "",
        "**Health Assessment Summary**",
        "",
        urgency_text,
        "",
        "**What you reported:**",
        f"- Symptoms: {symptoms or 'Not provided clearly'}",
        "",
        "**Possible causes being considered:**"
    ]

    if possible_conditions:
        for item in possible_conditions:
            name = item.get("name", "Possible condition")
            likelihood = item.get("likelihood", "medium")
            lines.append(f"- {name} ({likelihood} likelihood)")
    else:
        lines.append("- General medical condition")

    lines.extend([
        "",
        "**Recommended specialist:**",
        f"- {specialist}",
        "",
        "**Urgency level:**",
        f"- {urgency.capitalize()}",
        "",
        "**Reasoning summary:**",
        f"- {summary}"
    ])

    if red_flags:
        lines.append("")
        lines.append("**Warning signs to watch for:**")
        for flag in red_flags[:4]:
            lines.append(f"- {flag}")

    lines.extend([
        "",
        "**Next steps:**",
        f"- Consider consulting a {specialist}",
        "- Book an appointment if symptoms continue or worsen",
        "- Seek urgent care immediately if serious warning signs appear"
    ])

    return "\n".join(lines).strip()


# =========================
# Dynamic question handling
# =========================

def initialize_case_state(collected_data, llm_normalized):
    normalized_text = llm_normalized.get("normalized_text", "").strip()
    collected_data["raw_symptoms"] = llm_normalized.get("raw_input", normalized_text)
    collected_data["symptoms"] = normalized_text
    collected_data["llm_corrected_symptoms"] = llm_normalized.get("corrected_symptoms", [])
    collected_data["duration"] = llm_normalized.get("duration", "")
    collected_data["severity"] = llm_normalized.get("severity", "")
    collected_data["body_location"] = llm_normalized.get("body_location", "")
    collected_data["answers"] = {}
    collected_data["asked_questions"] = []
    collected_data["pending_question"] = None
    collected_data["question_count"] = 0
    collected_data["reasoning"] = {}
    return collected_data


def record_answer_to_pending_question(collected_data, answer_text):
    pending_question = collected_data.get("pending_question")
    answers = collected_data.get("answers", {})

    if pending_question:
        answers[pending_question] = answer_text

    collected_data["answers"] = answers
    collected_data["pending_question"] = None
    return collected_data


def decide_next_step(user_id, collected_data):
    history = check_previous_sessions(user_id, collected_data.get("symptoms", ""))
    emergency_check = emergency_rule_check(collected_data.get("symptoms", ""), collected_data)

    if emergency_check["is_emergency"]:
        reasoning = {
            "possible_conditions": [{"name": "Potential medical emergency", "likelihood": "high"}],
            "possible_specialties": ["Emergency Medicine"],
            "red_flags": [emergency_check["reason"]],
            "follow_up_questions": [],
            "likely_specialty": "Emergency Medicine",
            "urgency": "emergency",
            "assessment_complete": True,
            "summary": emergency_check["reason"],
            "reasoning_note": "Triggered by emergency safety rules."
        }
        collected_data["reasoning"] = reasoning
        return "complete", reasoning, history

    reasoning = reason_case_with_llm(collected_data)
    collected_data["reasoning"] = reasoning

    min_questions_required = 2
    if requires_deeper_questioning(collected_data.get("symptoms", "")):
        min_questions_required = 4

    if reasoning.get("urgency") == "emergency":
        return "complete", reasoning, history

    current_q_count = collected_data.get("question_count", 0)

    if reasoning.get("assessment_complete") and current_q_count >= min_questions_required:
        return "complete", reasoning, history

    follow_up = reasoning.get("follow_up_questions", [])
    if follow_up:
        next_question = follow_up[0]
        collected_data["pending_question"] = next_question
        collected_data["asked_questions"] = collected_data.get("asked_questions", []) + [next_question]
        collected_data["question_count"] = current_q_count + 1
        return "ask", reasoning, history

    if current_q_count < min_questions_required:
        fallback_question = GENERIC_FALLBACK_QUESTIONS[min(current_q_count, len(GENERIC_FALLBACK_QUESTIONS) - 1)]
        collected_data["pending_question"] = fallback_question
        collected_data["asked_questions"] = collected_data.get("asked_questions", []) + [fallback_question]
        collected_data["question_count"] = current_q_count + 1
        reasoning["follow_up_questions"] = [fallback_question]
        reasoning["assessment_complete"] = False
        return "ask", reasoning, history

    return "complete", reasoning, history


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
            current_step='collect_symptoms',
            collected_data=json.dumps({})
        )

        db.session.add(chat_session)
        db.session.commit()

        initial_message = (
            "Hello! I'm your Health Assistant. Please describe your symptoms in detail. "
            "You can type naturally, for example: "
            "'I have chest pain after eating', 'I feel short of breath', or 'I have a red itchy rash'."
        )

        save_bot_message(chat_session.id, initial_message, 'text')
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

        if current_step == 'collect_symptoms':
            llm_normalized = normalize_input_with_llm(message)
            collected_data = initialize_case_state(collected_data, llm_normalized)

            next_action, reasoning, history = decide_next_step(user_id, collected_data)

            if next_action == "complete":
                final_message = build_final_message(collected_data, reasoning)
                buttons = get_buttons_for_result(reasoning)
                msg_type = 'emergency' if reasoning.get("urgency") == "emergency" else 'recommendation'

                save_bot_message(chat_session.id, final_message, msg_type, buttons, extra_payload=reasoning)

                chat_session.current_step = 'completed'
                chat_session.collected_data = to_json_string(collected_data)
                chat_session.recommended_specialty = reasoning.get("likely_specialty", "General Physician")
                chat_session.risk_level = reasoning.get("urgency", "low")
                chat_session.ended_at = datetime.utcnow()
                db.session.commit()

                return jsonify({
                    'message': final_message,
                    'message_type': msg_type,
                    'buttons': buttons,
                    'specialty': reasoning.get("likely_specialty", "General Physician"),
                    'risk_level': reasoning.get("urgency", "low"),
                    'reasoning': reasoning
                }), 200

            response_message = build_question_message(reasoning)

            if history and history.get("has_history"):
                response_message += f"\n\nNote: I found a somewhat related past consultation from {history['session_date']}."

            save_bot_message(chat_session.id, response_message, 'text', extra_payload=reasoning)

            chat_session.current_step = 'dynamic_questioning'
            chat_session.collected_data = to_json_string(collected_data)
            db.session.commit()

            return jsonify({
                'message': response_message,
                'message_type': 'text',
                'step': 'dynamic_questioning',
                'reasoning': reasoning
            }), 200

        elif current_step == 'dynamic_questioning':
            collected_data = record_answer_to_pending_question(collected_data, message)

            emergency_check = emergency_rule_check(message, collected_data)
            if emergency_check["is_emergency"]:
                reasoning = {
                    "possible_conditions": [{"name": "Potential medical emergency", "likelihood": "high"}],
                    "possible_specialties": ["Emergency Medicine"],
                    "red_flags": [emergency_check["reason"]],
                    "follow_up_questions": [],
                    "likely_specialty": "Emergency Medicine",
                    "urgency": "emergency",
                    "assessment_complete": True,
                    "summary": emergency_check["reason"],
                    "reasoning_note": "Triggered during dynamic questioning by emergency safety rules."
                }

                collected_data["reasoning"] = reasoning
                final_message = build_final_message(collected_data, reasoning)
                buttons = get_buttons_for_result(reasoning)

                save_bot_message(chat_session.id, final_message, 'emergency', buttons, extra_payload=reasoning)

                chat_session.current_step = 'completed'
                chat_session.collected_data = to_json_string(collected_data)
                chat_session.recommended_specialty = "Emergency Medicine"
                chat_session.risk_level = "emergency"
                chat_session.ended_at = datetime.utcnow()
                db.session.commit()

                return jsonify({
                    'message': final_message,
                    'message_type': 'emergency',
                    'buttons': buttons,
                    'specialty': 'Emergency Medicine',
                    'risk_level': 'emergency',
                    'reasoning': reasoning
                }), 200

            next_action, reasoning, _history = decide_next_step(user_id, collected_data)

            if next_action == "ask":
                response_message = build_question_message(reasoning)

                save_bot_message(chat_session.id, response_message, 'text', extra_payload=reasoning)

                chat_session.current_step = 'dynamic_questioning'
                chat_session.collected_data = to_json_string(collected_data)
                db.session.commit()

                return jsonify({
                    'message': response_message,
                    'message_type': 'text',
                    'step': 'dynamic_questioning',
                    'reasoning': reasoning
                }), 200

            final_message = build_final_message(collected_data, reasoning)
            buttons = get_buttons_for_result(reasoning)
            msg_type = 'emergency' if reasoning.get("urgency") == "emergency" else 'recommendation'

            save_bot_message(chat_session.id, final_message, msg_type, buttons, extra_payload=reasoning)

            chat_session.current_step = 'completed'
            chat_session.collected_data = to_json_string(collected_data)
            chat_session.recommended_specialty = reasoning.get("likely_specialty", "General Physician")
            chat_session.risk_level = reasoning.get("urgency", "low")
            chat_session.ended_at = datetime.utcnow()
            db.session.commit()

            return jsonify({
                'message': final_message,
                'message_type': msg_type,
                'buttons': buttons,
                'specialty': reasoning.get("likely_specialty", "General Physician"),
                'risk_level': reasoning.get("urgency", "low"),
                'reasoning': reasoning
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