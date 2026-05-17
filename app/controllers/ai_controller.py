"""
AI Chatbot Controller — SABot powered by Google Gemini
Route: POST /ai/chat
"""
import os, time, random, logging, threading
from collections import deque
import requests as http_requests
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

logger = logging.getLogger(__name__)
ai_bp  = Blueprint('ai', __name__)

GEMINI_BASE  = 'https://generativelanguage.googleapis.com/v1beta/models'
MODEL_CHAIN  = [
    'gemini-2.5-flash-lite-preview-06-17',
    'gemini-2.5-flash',
    'gemini-1.5-flash',
    'gemini-1.5-flash-8b-001',
]
_dead_models: set = set()

_rl_lock   = threading.Lock()
_rl_store  = {}
_RL_WINDOW = 60
_RL_MAX    = 15

def _check_rate_limit(user_id) -> bool:
    now = time.time()
    with _rl_lock:
        dq = _rl_store.setdefault(user_id, deque())
        while dq and dq[0] < now - _RL_WINDOW:
            dq.popleft()
        if len(dq) >= _RL_MAX:
            return False
        dq.append(now)
        return True

SYSTEM_PROMPT = """You are SABot, a friendly and intelligent AI assistant for SAPCPOS — \
the Student Academic Performance Categorization and Pathway Optimization System used at NEMSU \
(Northeastern Mindanao State University).

Your role is to help students and faculty with:
- Understanding academic performance categories (Excellent, Good, Average, Needs Improvement)
- Interpreting grades, GPA, and academic standing
- Explaining recommended learning pathways and course suggestions
- Understanding the classification system (Decision Tree algorithm)
- Navigating the SAPCPOS platform features
- Answering general questions about academic performance improvement strategies
- Explaining rankings and how they are computed
- Providing encouragement and academic advice

Rules:
- Be friendly, supportive, and encouraging — especially to struggling students.
- Keep answers concise but helpful.
- If asked about specific student data, remind them to check their personal dashboard.
- Respond in the same language the user uses (Filipino or English).
- Use simple emoji occasionally to stay approachable 😊
- Never share other students' information or grades.
"""

def _try_model(url, payload, retries=2):
    for attempt in range(retries):
        try:
            resp = http_requests.post(url, json=payload, timeout=20)
        except http_requests.exceptions.Timeout:
            if attempt < retries - 1:
                time.sleep(1.2)
            continue
        except Exception as e:
            logger.error('Request error: %s', e)
            return None, 'skip'

        if resp.status_code == 200:
            try:
                data = resp.json()
                candidates = data.get('candidates', [])
                if not candidates:
                    return None, 'skip'
                c = candidates[0]
                if c.get('finishReason') == 'SAFETY':
                    return "I'm sorry, I can't respond to that. Please ask about SAPCPOS or academics.", 'ok'
                parts = c.get('content', {}).get('parts', [])
                text  = ' '.join(p.get('text', '') for p in parts).strip()
                if text:
                    return text, 'ok'
            except Exception as e:
                logger.error('Parse error: %s', e)
            return None, 'skip'

        if resp.status_code == 404:
            return None, 'skip'

        if resp.status_code in (429, 503):
            wait = min(0.8 * (2 ** attempt) + random.uniform(0, 0.3), 6.0)
            if attempt < retries - 1:
                time.sleep(wait)
            continue

        return None, 'skip'
    return None, 'retry'

def _call_gemini(api_key, contents):
    payload = {
        'system_instruction': {'parts': [{'text': SYSTEM_PROMPT}]},
        'contents': contents,
        'generationConfig': {'temperature': 0.7, 'maxOutputTokens': 512},
        'safetySettings': [
            {'category': 'HARM_CATEGORY_HARASSMENT',  'threshold': 'BLOCK_MEDIUM_AND_ABOVE'},
            {'category': 'HARM_CATEGORY_HATE_SPEECH', 'threshold': 'BLOCK_MEDIUM_AND_ABOVE'},
        ],
    }
    active = [m for m in MODEL_CHAIN if m not in _dead_models]
    if not active:
        _dead_models.clear()
        active = list(MODEL_CHAIN)
    for model in active:
        url  = f'{GEMINI_BASE}/{model}:generateContent?key={api_key}'
        text, status = _try_model(url, payload)
        if status == 'ok':
            return text
        if status == 'skip':
            _dead_models.add(model)
    return None

@ai_bp.route('/chat', methods=['POST'])
@login_required
def chat():
    api_key = os.getenv('GEMINI_API_KEY', '').strip()
    if not api_key:
        return jsonify({'error': 'AI not configured. Please set GEMINI_API_KEY.'}), 503

    if not _check_rate_limit(current_user.id):
        return jsonify({'reply': "You're sending messages too quickly! Please wait a moment 😊"})

    data         = request.get_json(silent=True) or {}
    user_message = (data.get('message') or '').strip()[:800]
    history      = data.get('history') or []

    if not user_message:
        return jsonify({'error': 'Empty message.'}), 400

    contents = []
    for turn in history[-6:]:
        role = 'user' if turn.get('role') == 'user' else 'model'
        text = (turn.get('text') or '').strip()
        if text:
            contents.append({'role': role, 'parts': [{'text': text}]})
    contents.append({'role': 'user', 'parts': [{'text': user_message}]})

    reply = _call_gemini(api_key, contents)
    if reply:
        return jsonify({'reply': reply})
    return jsonify({'reply': "I'm having trouble connecting right now. Please try again in a few seconds. 🙏"})
