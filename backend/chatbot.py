from flask import Blueprint, request, jsonify, session, current_app
from datetime import datetime
from models import db, Complaint
from flask_mail import Message
import requests
from langdetect import detect
from sentence_transformers import SentenceTransformer, util
import re
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

chatbot_bp = Blueprint('chatbot', __name__)

# === Groq API Configuration (from .env file)
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
GROQ_API_URL = os.getenv('GROQ_API_URL', 'https://api.groq.com/openai/v1/chat/completions')
GROQ_MODEL = os.getenv('GROQ_MODEL', 'llama-3.1-8b-instant')

# Enhanced FAQ for Votonomy-specific questions
faq_questions = [
    "How do I vote in Votonomy?",
    "How to register for voting?",
    "Why isn't my account approved?",
    "How many times can I vote?",
    "What is a Halka?",
    "How to file a complaint?",
    "I have a complaint",
    "I have a complain",
    "Check complaint status",
    "Check my complaint status",
    "What is Votonomy?",
    "How does blockchain voting work?",
    "What documents do I need to register?",
    "History of Pakistan elections",
    "When was Pakistan founded?",
    "Who was the founder of Pakistan?",
    "What are Pakistan's national symbols?"
]

faq_answers = [
    "To vote in Votonomy: 1) Register with your CNIC and voter ID 2) Complete pre-survey 3) Cast your vote for all positions 4) Complete post-survey 5) Get confirmation",
    "To register: Go to /register, enter your full name, father's name, voter ID, CNIC, age, gender, province, city, and complete address. Your info must match our voter database.",
    "Your account might not be approved due to mismatched data with our voter database. Please verify your CNIC, name, and other details match exactly.",
    "You can vote only once in Votonomy. The system blocks repeat voting to ensure election integrity.",
    "A Halka is your voting constituency (like NA-52, NA-53, NA-54). It's assigned based on your address sector in Islamabad.",
    "Type 'I have a complaint' or 'I have a complain' and I'll guide you through filing a complaint with your email.",
    "Please write your complaint now. Also share your email in the next message.",
    "Please write your complaint now. Also share your email in the next message.",
    "Please enter your complaint ID (like C0001, C0042, etc.) to check the status of your complaint.",
    "Please enter your complaint ID (like C0001, C0042, etc.) to check the status of your complaint.",
    "Votonomy is Pakistan's blockchain-based electronic voting system that ensures secure, transparent, and tamper-proof elections.",
    "Blockchain voting in Votonomy creates an immutable record of votes, ensuring transparency and preventing fraud through cryptographic security.",
    "You need: Valid CNIC, Voter ID, complete Islamabad address with sector (like I-8/2, G-10/3), and personal details matching our database.",
    "Pakistan has held multiple democratic elections since 1947. Key elections include 1970, 1977, 1988, 1990, 1993, 1997, 2002, 2008, 2013, 2018, and 2024.",
    "Pakistan was founded on August 14, 1947, gaining independence from British rule.",
    "Quaid-e-Azam Muhammad Ali Jinnah was the founder of Pakistan and its first Governor-General.",
    "Pakistan's national symbols include the crescent and star flag (green and white), the national anthem 'Qaumi Taranah', and the national flower Jasmine."
]

# Use a lightweight, fast sentence-transformer model for FAQ matching
model = SentenceTransformer('all-MiniLM-L6-v2')
# ✅ Generate embeddings after FAQ questions are defined
faq_embeddings = model.encode(faq_questions, convert_to_tensor=True)

# ✅ ENHANCED RESTRICTIVE PROMPTS
EN_PROMPT = """You are VotoBot, the official assistant for Votonomy - Pakistan's blockchain voting system. 

STRICT RULES - You MUST follow these:
1. ONLY answer questions about: Votonomy voting system, Pakistan voting process, voter registration, Pakistan history, Pakistan geography, and Pakistani government
2. REFUSE to answer: personal advice, general knowledge, entertainment, sports, technology unrelated to voting, international affairs (except Pakistan), medical advice, legal advice, financial advice, or any non-Pakistan/non-voting topics
3. If asked irrelevant questions, politely redirect: "I only assist with Votonomy voting and Pakistan-related questions. How can I help you with voting or Pakistan?"
4. Keep responses factual, professional, and focused on helping Pakistani voters
5. Encourage users to use Votonomy for secure democratic participation

Available topics: Votonomy features, registration process, voting steps, halka system, blockchain security, Pakistan history, Pakistani elections, government structure, geography of Pakistan."""

UR_PROMPT = """آپ ووٹو بوٹ ہیں، ووٹونومی کا سرکاری اسسٹنٹ - پاکستان کا بلاک چین ووٹنگ سسٹم۔

سخت اصول - آپ کو یہ ماننا ہوگا:
1. صرف ان سوالات کا جواب دیں: ووٹونومی ووٹنگ سسٹم، پاکستان کی ووٹنگ کا عمل، ووٹر رجسٹریشن، پاکستان کی تاریخ، پاکستان کا جغرافیہ، اور پاکستانی حکومت
2. انکار کریں: ذاتی مشورے، عام معلومات، تفریح، کھیل، ووٹنگ سے غیر متعلقہ ٹیکنالوجی، بین الاقوامی معاملات، طبی مشورہ، قانونی مشورہ یا کوئی غیر پاکستان/غیر ووٹنگ موضوعات
3. غیر متعلقہ سوالات پر: "میں صرف ووٹونومی ووٹنگ اور پاکستان سے متعلق سوالات میں مدد کرتا ہوں۔ ووٹنگ یا پاکستان کے بارے میں کیسے مدد کر سکتا ہوں؟"
4. جوابات حقیقی، پیشہ ورانہ اور پاکستانی ووٹرز کی مدد پر مرکوز رکھیں"""

# ✅ ENHANCED TYPO-TOLERANT FUNCTIONS
def normalize_text(text):
    """Normalize text to handle common typos and variations"""
    if not text:
        return ""
    
    text = text.lower().strip()
    
    # ✅ Common typo corrections
    typo_corrections = {
        # Complaint variations
        'complain': 'complaint',
        'compliant': 'complaint',
        'complayn': 'complaint',
        'complin': 'complaint',
        'complint': 'complaint',
        
        # Check variations
        'chk': 'check',
        'chek': 'check',
        'checkk': 'check',
        
        # Status variations
        'staus': 'status',
        'sataus': 'status',
        'satus': 'status',
        'stat': 'status',
        
        # Vote variations
        'vot': 'vote',
        'voet': 'vote',
        'voot': 'vote',
        
        # Register variations
        'regist': 'register',
        'registr': 'register',
        'regsiter': 'register',
        
        # Pakistan variations
        'pakisan': 'pakistan',
        'pakistna': 'pakistan',
        'pakstan': 'pakistan',
        
        # Votonomy variations
        'votonmy': 'votonomy',
        'votonomi': 'votonomy',
        'votonamu': 'votonomy',
        
        # Common misspellings
        'halka': 'halka',  # This is correct
        'halaka': 'halka',
        'halca': 'halka',
        
        # Email variations
        'emai': 'email',
        'emial': 'email',
        'e-mail': 'email',
    }
    
    # Apply corrections word by word
    words = text.split()
    corrected_words = []
    
    for word in words:
        # Remove punctuation for checking
        clean_word = re.sub(r'[^\w]', '', word)
        if clean_word in typo_corrections:
            # Replace the word but keep original punctuation
            corrected_word = word.replace(clean_word, typo_corrections[clean_word])
            corrected_words.append(corrected_word)
        else:
            corrected_words.append(word)
    
    return ' '.join(corrected_words)

def extract_complaint_id(text):
    """Extract complaint ID with better pattern matching"""
    # ✅ More flexible complaint ID patterns
    patterns = [
        r'C(\d{1,4})',  # C1234
        r'c(\d{1,4})',  # c1234 (lowercase)
        r'complaint\s*(?:id|number|#)?\s*:?\s*C?(\d{1,4})',  # complaint id: 1234
        r'id\s*:?\s*C?(\d{1,4})',  # id: 1234
        r'#\s*C?(\d{1,4})',  # #1234
        r'(\d{4})',  # just 4 digits
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return None

# ✅ RELEVANCE CHECKER with better typo tolerance
def is_question_relevant(question):
    """Check if the question is relevant to allowed topics"""
    
    # Normalize the question for better matching
    normalized_question = normalize_text(question)
    question_lower = normalized_question.lower()
    
    # ✅ Enhanced Votonomy and voting keywords (with typos)
    voting_keywords = [
        'vote', 'voting', 'votonomy', 'votonomy', 'election', 'ballot', 'candidate', 'voter', 'registration', 'register',
        'halka', 'constituency', 'blockchain', 'survey', 'complaint', 'complain', 'authentication', 'approve', 'reject',
        'status', 'check', 'c0', 'c1', 'c2', 'c3', 'c4', 'c5', 'c6', 'c7', 'c8', 'c9',
        # Typo variations
        'complain', 'compliant', 'chk', 'chek', 'staus', 'sataus', 'vot', 'voet', 'regist'
    ]
    
    # Pakistan-related keywords
    pakistan_keywords = [
        'pakistan', 'pakistani', 'jinnah', 'quaid', 'azam', 'independence', 'partition', 'lahore', 'karachi',
        'islamabad', 'punjab', 'sindh', 'balochistan', 'kpk', 'khyber', 'peshawar', 'quetta', 'multan',
        'faisalabad', 'rawalpindi', 'nawaz', 'bhutto', 'imran', 'khan', 'pti', 'pmln', 'ppp', 'mna', 'mpa',
        'national assembly', 'senate', 'prime minister', 'president', 'governor', 'chief minister',
        'urdu', 'punjabi', 'pashto', 'balochi', 'sindhi', 'kashmir', 'gilgit', 'baltistan',
        # Typo variations
        'pakisan', 'pakistna', 'pakstan'
    ]
    
    # ✅ ENHANCED: Allow basic conversational responses
    conversational_responses = [
        'thanks', 'thank you', 'thankyou', 'thx', 'ty', 'okay', 'ok', 'alright', 'good', 'great', 
        'nice', 'perfect', 'excellent', 'awesome', 'cool', 'got it', 'understood', 'clear',
        'bye', 'goodbye', 'see you', 'later', 'done', 'finished', 'complete', 'yes', 'no',
        'sure', 'fine', 'right', 'correct', 'wrong', 'help', 'assist', 'support', 'guide'
    ]
    
    # Check for greeting/basic interaction
    greetings = ['hello', 'hi', 'hey', 'salam', 'assalam', 'good morning', 'good evening', 'how are you']
    
    # ✅ Allow short responses (1-3 words) that are conversational
    words = question_lower.strip().split()
    if len(words) <= 3:
        for word in words:
            if word in conversational_responses or word in greetings:
                return True
    
    # Check if question contains relevant keywords
    for keyword in voting_keywords + pakistan_keywords:
        if keyword in question_lower:
            return True
    
    # Check for greeting/basic interaction
    for greeting in greetings:
        if greeting in question_lower:
            return True
    
    # ✅ Allow very short responses (likely conversational)
    if len(normalized_question.strip()) <= 10 and any(word in question_lower for word in conversational_responses):
        return True
    
    return False

# ✅ Groq API Call with enhanced error handling
def call_qwen_model(messages, max_tokens=800):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.3
    }

    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
        data = response.json()
        if "choices" in data:
            return data["choices"][0]["message"]["content"]
        else:
            if "message" in data.get("error", {}) and "tokens" in data["error"]["message"]:
                print("🔁 Retrying with shorter history...")
                trimmed = messages[:2] + messages[-2:]
                payload["messages"] = trimmed
                response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
                data = response.json()
                if "choices" in data:
                    return data["choices"][0]["message"]["content"]
            print("⚠️ Groq API error:", data)
            return "⚠️ Sorry, I couldn't respond at the moment. Please ask about Votonomy voting or Pakistan-related topics."
    except requests.exceptions.Timeout:
        return "⚠️ Response timed out. Please try again with a shorter question about Votonomy or Pakistan."
    except Exception as e:
        print("⚠️ Exception in call_qwen_model():", str(e))
        return "⚠️ There was a problem reaching the AI model. Please ask about Votonomy or Pakistan topics."

# ✅ ENHANCED session management
def get_session_state():
    """Get current session state with proper defaults"""
    return {
        'chat_history': session.get('chat_history', []),
        'complaint_mode': session.get('complaint_mode', False),
        'checking_complaint_status': session.get('checking_complaint_status', False),
        'waiting_for_email': session.get('waiting_for_email', False),
        'conversation_count': session.get('conversation_count', 0)
    }

def update_session_state(**kwargs):
    """Update session state"""
    for key, value in kwargs.items():
        session[key] = value

def reset_conversation_modes():
    """Reset all conversation modes to prevent loops"""
    update_session_state(
        complaint_mode=False,
        checking_complaint_status=False,
        waiting_for_email=False
    )

# ✅ MAIN CHAT HANDLER WITH ENHANCED FEATURES
@chatbot_bp.route("/chatbot/message", methods=["POST"])
def handle_chat():
    try:
        user_msg = request.json.get("message", "").strip()
        
        # Get session state
        state = get_session_state()
        
        # Increment conversation counter and auto-reset after too many exchanges
        state['conversation_count'] += 1
        if state['conversation_count'] > 50:  # Prevent infinite loops
            reset_conversation_modes()
            state = get_session_state()
            update_session_state(conversation_count=0)
        else:
            update_session_state(conversation_count=state['conversation_count'])
        
        # ✅ Normalize user message to handle typos
        normalized_msg = normalize_text(user_msg)
        msg_lower = normalized_msg.lower()
        
        # ✅ ESCAPE MECHANISM: Allow users to reset conversation
        if any(phrase in msg_lower for phrase in ['reset', 'restart', 'start over', 'new conversation', 'clear']):
            reset_conversation_modes()
            update_session_state(chat_history=[], conversation_count=0)
            return jsonify({"reply": "🔄 Conversation reset! How can I help you with Votonomy voting or Pakistan-related questions?"})
        
        # ✅ FIRST: Check if it's a complaint ID (highest priority)
        complaint_id = extract_complaint_id(user_msg)
        if complaint_id:
            reset_conversation_modes()  # Clear any existing flags
            from models import Complaint
            try:
                complaint_id_formatted = f"C{complaint_id.zfill(4)}"  # Pad with zeros
                cid = int(complaint_id)
                complaint = Complaint.query.get(cid)
                if not complaint:
                    return jsonify({"reply": f"❌ Complaint {complaint_id_formatted} not found. Please check your complaint ID and try again."})
                
                status_emoji = {
                    'Pending': '⏳',
                    'In Progress': '🔄', 
                    'Resolved': '✅'
                }
                
                reply = f"📄 **Complaint {complaint_id_formatted} Status**\n\n"
                reply += f"Status: {status_emoji.get(complaint.status, '📋')} {complaint.status}\n"
                reply += f"Submitted: {complaint.created_at.strftime('%d/%m/%Y at %H:%M')}\n\n"
                
                if complaint.response:
                    reply += f"**Admin Response:**\n{complaint.response}"
                else:
                    if complaint.status == 'Pending':
                        reply += "Your complaint is being reviewed by our team."
                    elif complaint.status == 'In Progress':
                        reply += "Our team is actively working on your complaint."
                    else:
                        reply += "No additional response available."
                        
                return jsonify({"reply": reply})
                
            except Exception as e:
                return jsonify({"reply": "❌ Error checking complaint status. Please try again or contact support."})
        
        # ✅ ENHANCED COMPLAINT STATUS CHECKING with typo tolerance
        status_check_patterns = [
            'complaint status', 'check complaint', 'check my complaint', 'complaint id', 
            'status of complaint', 'my complaint status', 'check status', 'status check',
            'what is my complaint status', 'check my complaint', 'complaint check',
            # Typo variations
            'complain status', 'chk complaint', 'chek my complaint', 'complain id',
            'staus of complaint', 'my complain status', 'chk status', 'sataus check'
        ]
        
        if any(phrase in msg_lower for phrase in status_check_patterns) or (("check" in msg_lower or "status" in msg_lower) and ("complaint" in msg_lower or "complain" in msg_lower)):
            reset_conversation_modes()
            update_session_state(checking_complaint_status=True)
            return jsonify({"reply": "Please enter your complaint ID (format: C0001, C0042, etc.) to check the status."})
        
        # ✅ HANDLE COMPLAINT ID INPUT WHEN IN STATUS CHECK MODE
        if state['checking_complaint_status']:
            reset_conversation_modes()
            # Try to extract any numbers that might be complaint ID
            extracted_id = extract_complaint_id(user_msg)
            if extracted_id:
                from models import Complaint
                try:
                    cid = int(extracted_id)
                    complaint = Complaint.query.get(cid)
                    if not complaint:
                        return jsonify({"reply": f"❌ Complaint C{cid:04d} not found. Please check your complaint ID and try again."})
                    
                    status_emoji = {
                        'Pending': '⏳',
                        'In Progress': '🔄', 
                        'Resolved': '✅'
                    }
                    
                    reply = f"📄 **Complaint C{cid:04d} Status**\n\n"
                    reply += f"Status: {status_emoji.get(complaint.status, '📋')} {complaint.status}\n"
                    reply += f"Submitted: {complaint.created_at.strftime('%d/%m/%Y at %H:%M')}\n\n"
                    
                    if complaint.response:
                        reply += f"**Admin Response:**\n{complaint.response}"
                    else:
                        if complaint.status == 'Pending':
                            reply += "Your complaint is being reviewed by our team."
                        elif complaint.status == 'In Progress':
                            reply += "Our team is actively working on your complaint."
                        else:
                            reply += "No additional response available."
                            
                    return jsonify({"reply": reply})
                    
                except Exception as e:
                    return jsonify({"reply": "❌ Error checking complaint status. Please try again or contact support."})
            else:
                return jsonify({"reply": "❌ Invalid complaint ID format. Please enter it like: C0001, C0042, etc."})

        # ✅ ENHANCED COMPLAINT HANDLING with better typo tolerance
        complaint_patterns = [
            # Original patterns
            "i have a complaint", "i have complain", "i have a complain", "file complaint", 
            "lodge complaint", "make complaint", "i want to complain", "i want to complaint",
            "i need to complain", "i need to file", "register complaint", "submit complaint",
            "complain about", "complaint about", "i complain", "my complaint",
            # Typo variations
            "i have compliant", "i have complayn", "i hav complaint", "file complain",
            "lodge complain", "make complain", "i wan to complain", "i want compliant",
            "i ned to complain", "i need to fil", "register complain", "submit complain",
            "compliant about", "complin about", "i complint", "my complain"
        ]
        
        # Check for complaint filing (but not status checking)
        wants_to_file_complaint = False
        for phrase in complaint_patterns:
            if phrase in msg_lower and "status" not in msg_lower and "check" not in msg_lower and "chk" not in msg_lower:
                wants_to_file_complaint = True
                break
        
        if wants_to_file_complaint:
            reset_conversation_modes()
            update_session_state(complaint_mode=True)
            return jsonify({"reply": "Please write your complaint now. Also share your email in the next message."})

        # ✅ HANDLE COMPLAINT FILING FLOW
        if state['complaint_mode'] and not state['waiting_for_email']:
            update_session_state(waiting_for_email=True)
            # Store complaint text in session temporarily
            session['complaint_text'] = user_msg
            return jsonify({"reply": "Got it! Now please enter your email address so we can contact you about your complaint:"})
        
        elif state['waiting_for_email']:
            complaint_text = session.get('complaint_text', 'No complaint text provided')
            reset_conversation_modes()
            # Remove temporary complaint text
            session.pop('complaint_text', None)
            return submit_complaint_internal(user_msg, complaint_text)

        # ✅ RELEVANCE CHECK with improved typo handling
        if not is_question_relevant(user_msg):
            return jsonify({
                "reply": "I only assist with Votonomy voting system and Pakistan-related questions. I can help you with:\n\n• How to register for voting\n• Voting process in Votonomy\n• Pakistan history and geography\n• Election procedures\n• Filing complaints\n• Checking complaint status\n\nHow can I help you with voting or Pakistan?"
            })

        # Language detection
        try:
            lang = detect(user_msg)
        except:
            lang = "en"
        prompt = UR_PROMPT if lang in ['ur', 'hi', 'fa', 'ps'] else EN_PROMPT

        # FAQ fallback with improved matching
        embedding = model.encode(normalized_msg, convert_to_tensor=True)
        scores = util.pytorch_cos_sim(embedding, faq_embeddings)[0]
        if scores.max().item() > 0.4:  # Lowered threshold for better typo handling
            return jsonify({"reply": faq_answers[int(scores.argmax())]})

        # Construct conversation with enhanced system prompt
        history = state['chat_history'][-4:]  # Keep last 4 exchanges
        messages = [{"role": "system", "content": prompt}] + history + [{"role": "user", "content": user_msg}]
        
        ai_reply = call_qwen_model(messages)
        
        # ✅ POST-PROCESSING: Double-check if AI response went off-topic
        off_topic_words = ['recipe', 'movie', 'song', 'game', 'weather', 'stock', 'crypto', 'bitcoin', 'sports', 'entertainment']
        if any(word in ai_reply.lower() for word in off_topic_words):
            ai_reply = "I focus only on Votonomy voting system and Pakistan-related topics. How can I help you with voter registration, voting process, or Pakistan information?"

        # Update chat history
        current_history = state['chat_history']
        current_history.append({"role": "user", "content": user_msg})
        current_history.append({"role": "assistant", "content": ai_reply})
        
        # Keep history manageable
        if len(current_history) > 20:
            current_history = current_history[-20:]
        
        update_session_state(chat_history=current_history)

        return jsonify({"reply": ai_reply})
        
    except Exception as e:
        print(f"Error in handle_chat: {str(e)}")
        # Reset modes on error to prevent getting stuck
        reset_conversation_modes()
        return jsonify({"reply": "⚠️ Something went wrong. Please try again or ask me about Votonomy voting or Pakistan-related topics."})

# ✅ Enhanced Complaint Submission with better validation
def submit_complaint_internal(email, complaint_text):
    """Internal function to handle complaint submission"""
    try:
        email = email.strip()
        complaint_text = complaint_text.strip()

        if not email or not complaint_text:
            return jsonify({"reply": "❌ Both email and complaint text are required."})
        
        # Enhanced email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return jsonify({"reply": "❌ Please enter a valid email address (e.g., user@example.com)."})
        
        # ✅ VERY LENIENT validation - accept almost any complaint
        if len(complaint_text) < 3:
            return jsonify({"reply": "❌ Please enter a complaint with at least 3 characters."})
        
        # Block only very generic/meaningless responses
        very_generic = ["hi", "hello", "test", ".", "ok", "yes", "no"]
        if complaint_text.lower().strip() in very_generic:
            return jsonify({"reply": "❌ Please enter a proper complaint describing your issue."})

        new_complaint = Complaint(email=email, complaint_text=complaint_text, status="Pending")
        db.session.add(new_complaint)
        db.session.commit()

        return jsonify({"reply": f"✅ Complaint registered successfully! Your complaint ID is C{new_complaint.id:04d}. You can check its status anytime using this ID."})
        
    except Exception as e:
        print(f"Error in submit_complaint_internal: {str(e)}")
        return jsonify({"reply": "❌ Error submitting complaint. Please try again later."})

# === Enhanced Complaint Submission (External endpoint)
@chatbot_bp.route("/chatbot/submit-complaint", methods=["POST"])
def submit_complaint():
    try:
        data = request.json
        email = data.get("email", "").strip()
        complaint_text = data.get("text", "").strip()
        
        return submit_complaint_internal(email, complaint_text)
        
    except Exception as e:
        print(f"Error in submit_complaint: {str(e)}")
        return jsonify({"reply": "❌ Error processing complaint submission. Please try again."})

# === Complaint Status Check (Enhanced)
@chatbot_bp.route("/chatbot/complaint-status", methods=["POST"])
def complaint_status():
    try:
        data = request.json
        complaint_id = data.get("id", "")
        
        # Enhanced ID extraction
        extracted_id = extract_complaint_id(complaint_id)
        if not extracted_id:
            return jsonify({"reply": "❌ Invalid complaint ID format."})

        cid = int(extracted_id)
        complaint = Complaint.query.get(cid)
        if not complaint:
            return jsonify({"reply": f"❌ Complaint C{cid:04d} not found."})

        return jsonify({
            "reply": f"📄 Status: {complaint.status}\nResponse: {complaint.response or 'No reply yet.'}"
        })
        
    except Exception as e:
        return jsonify({"reply": "❌ Error checking complaint status."})

# === Email Notification (unchanged but with better error handling)
def send_resolution_email(email, complaint_id, response):
    try:
        msg = Message(subject=f"Complaint #{complaint_id} Resolved",
                      sender="noreply@votonomy.com",
                      recipients=[email])
        msg.body = f"""Dear Voter,

Your complaint (ID: {complaint_id}) has been resolved.

Admin Response:
{response}

Regards,
Votonomy Team
"""
        current_app.extensions['mail'].send(msg)
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        # Don't raise the error, just log it
