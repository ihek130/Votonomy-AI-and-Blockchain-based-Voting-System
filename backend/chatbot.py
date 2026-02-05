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

# === xAI API Configuration (from .env file)
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
GROQ_API_URL = os.getenv('GROQ_API_URL', 'https://api.x.ai/v1/chat/completions')
GROQ_MODEL = os.getenv('GROQ_MODEL', 'grok-3')

# ✅ MASSIVELY ENHANCED FAQ - Claude-level Intelligence
faq_questions = [
    # Voting Process
    "How do I vote in Votonomy?",
    "How to register for voting?",
    "How many times can I vote?",
    "What positions can I vote for?",
    "Can I change my vote after submitting?",
    
    # Registration & Authentication
    "Why isn't my account approved?",
    "What documents do I need to register?",
    "I forgot my CNIC number",
    "I lost my ID card",
    "How do I register without CNIC?",
    "My voter ID doesn't match",
    "Registration keeps failing",
    
    # Halka & Constituencies
    "What is a Halka?",
    "How do I find my Halka?",
    "What is NA-52, NA-53, NA-54?",
    "Which Halka am I in?",
    "Can I vote in multiple Halkas?",
    
    # Blockchain & Security
    "What is Votonomy?",
    "How does blockchain voting work?",
    "How are votes stored?",
    "Are my votes encrypted?",
    "Is blockchain secure?",
    "Can votes be tampered?",
    "How is my privacy protected?",
    "What is vote encryption?",
    "How are votes verified?",
    
    # Fraud Detection & Anomalies
    "How is fraud detected?",
    "What are anomalies in voting?",
    "How does AI fraud detection work?",
    "What triggers fraud alerts?",
    "Am I being monitored?",
    "What if I'm flagged as fraud?",
    
    # Complaints
    "How to file a complaint?",
    "I have a complaint",
    "Check complaint status",
    "My complaint status",
    
    # Pakistan History
    "History of Pakistan elections",
    "When was Pakistan founded?",
    "Who was the founder of Pakistan?",
    "Pakistan's national symbols",
    
    # Technical Issues
    "Website not loading",
    "I can't login",
    "Forgot my password",
    "Email not received",
    "Survey not submitting"
]

faq_answers = [
    # Voting Process
    "**Voting in Votonomy (5 Steps):**\n1️⃣ Register with CNIC & Voter ID\n2️⃣ Wait for admin approval\n3️⃣ Complete 12-question pre-survey\n4️⃣ Cast votes for PM, MNA, MPA\n5️⃣ Complete post-survey\n6️⃣ Get blockchain receipt\n\nYour vote is encrypted and stored on Solana blockchain!",
    
    "**Registration Process:**\n✅ Required: Full Name, Father's Name, Voter ID, CNIC (13 digits), Age, Gender, Province, City, Complete Address with Sector\n✅ Address must include sector (e.g., I-8/2, G-10/3)\n✅ Data must match our voter database exactly\n✅ Admin will approve within 24 hours\n\n⚠️ Without matching data, registration fails.",
    
    "**One Person, One Vote!** You can vote ONLY ONCE in Votonomy. The system:\n✅ Blocks repeat voting\n✅ Checks blockchain records\n✅ Detects fraud attempts\n\nThis ensures democratic integrity.",
    
    "**Three Positions:**\n🏛️ Prime Minister (PM)\n🇵🇰 Member National Assembly (MNA)\n🏙️ Member Provincial Assembly (MPA)\n\nYou must vote for ALL THREE before submitting.",
    
    "**No, votes are FINAL.** Once submitted:\n🔒 Vote is encrypted\n⛓️ Stored on blockchain (immutable)\n✅ Cannot be changed or deleted\n\nThis prevents vote manipulation.",
    
    # Registration & Authentication
    "**Account Not Approved? Common Reasons:**\n❌ CNIC doesn't match database\n❌ Name spelling mismatch\n❌ Incorrect Voter ID\n❌ Address sector missing\n❌ Age/gender doesn't match\n\n✅ Solution: Check your CNIC card and re-enter EXACT details. Contact admin if still failing.",
    
    "**Required Documents:**\n📄 Valid CNIC (Computerized National Identity Card)\n🗳️ Voter ID (from ECP)\n🏠 Complete Islamabad address with sector\n\n**Example Address:** House 123, Street 5, I-8/2, Islamabad\n\n✅ All details must match our voter database.",
    
    "**Forgot CNIC Number? Solutions:**\n1️⃣ Check your physical CNIC card\n2️⃣ Check NADRA registration slip\n3️⃣ Visit NADRA office with original documents\n4️⃣ Use NADRA Verisys app\n\n⚠️ You CANNOT register without CNIC number.",
    
    "**Lost ID Card? Immediate Steps:**\n1️⃣ File FIR at police station\n2️⃣ Visit NADRA office\n3️⃣ Apply for duplicate CNIC\n4️⃣ Get temporary receipt\n\n⚠️ Registration requires valid CNIC. Complete NADRA process first.",
    
    "**Cannot Register Without CNIC!**\nCNIC is mandatory for:\n✅ Identity verification\n✅ Preventing fraud\n✅ Database matching\n\n🚫 No alternatives accepted. Get CNIC from NADRA first.",
    
    "**Voter ID Mismatch? Steps:**\n1️⃣ Check ECP (Election Commission) records\n2️⃣ Verify you're in our voter database\n3️⃣ Ensure exact spelling\n4️⃣ Contact admin with complaint\n\nFormat example: ABC-1234567",
    
    "**Registration Failing? Debug Checklist:**\n✅ CNIC exactly 13 digits (without dashes)\n✅ Name matches CNIC card\n✅ Father's name matches CNIC\n✅ Address includes sector (I-8/2)\n✅ Age matches CNIC\n✅ Gender correct\n\nIf all correct and still failing, file complaint.",
    
    # Halka & Constituencies
    "**Halka = Electoral Constituency**\nYour voting area based on address. Islamabad has 3:\n\n🏛️ **NA-52**: Sectors F-8, F-9, F-10, F-11, G-8, G-9, G-10, H-8, H-9\n🏛️ **NA-53**: Sectors E-7, E-11, G-6, G-7, G-11, G-13, I-8\n🏛️ **NA-54**: Sectors I-9, I-10, I-11, I-12, I-14, I-15, I-16\n\nSystem auto-detects from your address!",
    
    "**Finding Your Halka:**\nBased on your address SECTOR:\n📍 F-10/4 → NA-52\n📍 G-11/3 → NA-53\n📍 I-9/1 → NA-54\n\nHalka is auto-assigned during registration!",
    
    "**National Assembly Constituencies:**\n**NA-52**: Central/West Islamabad\n**NA-53**: East/Central Islamabad\n**NA-54**: East/Far East Islamabad\n\nEach has different candidates for MNA position.",
    
    "**Your Halka = Your Address Sector**\nThe system automatically detects it from your registered address. You'll only see candidates from YOUR Halka.",
    
    "**No! One Halka Only.**\nYou can ONLY vote in your registered Halka based on your address. Cannot vote in multiple constituencies. This prevents fraud.",
    
    # Blockchain & Security
    "**Votonomy = Pakistan's Blockchain E-Voting**\n⛓️ Built on Solana blockchain\n🔐 AES-256 encryption\n🔒 SHA-256 voter hashing\n✅ Tamper-proof voting\n🇵🇰 Designed for Pakistan\n\n**Features:**\n• AI fraud detection\n• Real-time verification\n• Anonymous but verifiable\n• Complete audit trail",
    
    "**Blockchain Voting Process:**\n1️⃣ You cast vote → Encrypted with AES-256\n2️⃣ Your ID → Hashed with SHA-256 (anonymous)\n3️⃣ Encrypted vote → Sent to Solana blockchain\n4️⃣ Stored in Memo transaction (immutable)\n5️⃣ You get receipt code\n6️⃣ Vote verified on-chain\n\n✅ Result: Tamper-proof, verifiable, anonymous vote!",
    
    "**Vote Storage (3 Layers):**\n\n**Layer 1 - Local Database:**\n📊 Basic vote record\n⏰ Timestamp\n\n**Layer 2 - Blockchain (Solana):**\n⛓️ Encrypted vote data\n🔐 Voter ID hash\n🎫 Transaction signature\n📍 Block slot number\n\n**Layer 3 - Verification:**\n✅ Receipt code\n🔍 On-chain proof\n\nVotes are TRIPLE-PROTECTED!",
    
    "**Yes! Military-Grade Encryption:**\n🔐 **AES-256-GCM**: Vote content encrypted\n🔒 **SHA-256**: Your identity hashed\n🎭 **Anonymity**: Admin can't see who voted for whom\n✅ **Verifiable**: You can verify your vote exists\n\nYour vote is encrypted BEFORE blockchain storage.",
    
    "**Blockchain Security Features:**\n✅ **Immutable**: Cannot be changed once stored\n✅ **Decentralized**: No single point of failure\n✅ **Transparent**: Anyone can verify integrity\n✅ **Cryptographic**: Military-grade encryption\n✅ **Timestamped**: Exact time recorded\n\n🚫 Even admins cannot tamper with blockchain votes!",
    
    "**Can Votes Be Tampered? NO!**\n\n**Why?**\n1️⃣ Blockchain is immutable (cannot change history)\n2️⃣ Cryptographic hashing prevents alteration\n3️⃣ Every change creates new block\n4️⃣ Entire network must agree (consensus)\n5️⃣ Tampering attempt = Rejected immediately\n\n✅ **Result**: 99.99% tamper-proof!",
    
    "**Privacy Protection (Triple Layer):**\n\n**Layer 1 - Voter Anonymity:**\n🎭 Your ID is SHA-256 hashed\n🔒 Admin sees hash, not your ID\n\n**Layer 2 - Vote Encryption:**\n🔐 Vote encrypted with AES-256\n🚫 Cannot be decrypted without key\n\n**Layer 3 - Separation:**\n📊 Vote and voter stored separately\n🔗 Linked only by hash\n\n✅ **Result**: Anonymous + Verifiable!",
    
    "**Vote Encryption Process:**\n1️⃣ You select candidate\n2️⃣ System generates encryption key\n3️⃣ Vote → AES-256 encrypted\n4️⃣ Encrypted data → Blockchain\n5️⃣ Key stored securely\n6️⃣ Only system can decrypt for counting\n\n🔐 Uses Fernet (AES-256-GCM mode)",
    
    "**Vote Verification:**\n✅ You get receipt code after voting\n✅ Receipt = Transaction signature\n✅ You can verify vote exists on blockchain\n✅ Admin dashboard shows verification status\n✅ Blockchain explorer confirms transaction\n\n🔍 Your vote is verifiable but anonymous!",
    
    # Fraud Detection & Anomalies
    "**AI-Powered Fraud Detection:**\n\n🤖 **Isolation Forest Algorithm**\n📊 Tracks 9 behavioral features:\n• Registration speed\n• Survey completion time\n• Response patterns\n• Voting speed\n• Form corrections\n• Session duration\n• Device fingerprint\n• IP address\n• Time patterns\n\n⚠️ Suspicious behavior = Flagged\n🚫 Critical risk = Vote BLOCKED",
    
    "**Anomalies = Unusual Voting Patterns:**\n\n🚨 **Anomaly Examples:**\n• Voting too fast (< 15 seconds)\n• Uniform survey responses (all same)\n• Registration in 10 seconds\n• Multiple votes from same IP\n• Identical behavior patterns\n• Bot-like activity\n\n✅ **Normal Behavior:**\n• Takes time to read questions\n• Varied survey responses\n• Natural pace\n• Unique patterns",
    
    "**AI Fraud Detection System:**\n\n**Algorithm**: Isolation Forest (Unsupervised ML)\n**Training**: Learns from normal behavior\n**Detection**: Identifies outliers in real-time\n\n**Features Analyzed:**\n1️⃣ Registration duration\n2️⃣ Survey variance\n3️⃣ Voting speed\n4️⃣ Session patterns\n5️⃣ Device fingerprints\n6️⃣ IP clustering\n\n**Risk Scoring**: 0-100\n🟢 0-49: Normal\n🟡 50-69: Monitor\n🟠 70-84: High risk (warn)\n🔴 85-100: Critical (BLOCK)",
    
    "**Fraud Alert Triggers:**\n⚠️ Registration < 30 seconds\n⚠️ Survey < 20 seconds\n⚠️ All survey answers identical\n⚠️ Voting < 15 seconds\n⚠️ 50+ votes from same IP\n⚠️ Coordinated timing\n⚠️ Cookie-cutter behavior\n⚠️ Bot patterns detected\n\n✅ **If Triggered**: Admin reviews manually",
    
    "**Monitoring = Normal Security:**\n✅ All voters are tracked for security\n✅ Behavioral analytics prevent fraud\n✅ Your data is encrypted\n✅ Only aggregated stats visible to admin\n\n🎭 Your identity remains anonymous\n🔒 Monitoring ≠ Surveillance\n\nIt's like security cameras for election integrity!",
    
    "**Flagged as Fraud? Don't Panic!**\n\n**If Risk 70-84% (High):**\n⚠️ Vote ALLOWED but flagged for review\n📊 Admin manually investigates\n✅ Usually false positive\n\n**If Risk 85%+ (Critical):**\n🚫 Vote BLOCKED immediately\n📧 Contact admin with explanation\n🔍 Manual verification required\n\n**Appeals Process:**\n1️⃣ File complaint with details\n2️⃣ Admin reviews your case\n3️⃣ If legitimate, vote enabled\n\n✅ False positives are rare but happen!",
    
    # Complaints
    "Type 'I have a complaint' and I'll guide you through filing it. You'll need to provide your email address for follow-up.",
    "Please write your complaint now. Also share your email in the next message.\n\n💡 Type 'cancel' to go back.",
    "Please enter your complaint ID (format: C0001, C0042, etc.) to check status.\n\n💡 Type 'cancel' to go back.",
    "Please enter your complaint ID (format: C0001, C0042, etc.) to check status.\n\n💡 Type 'cancel' to go back.",
    
    # Pakistan History
    "**Pakistan Election History:**\n🗳️ 1970: First general election\n🗳️ 1977: Controversial election\n🗳️ 1988: Return to democracy\n🗳️ 1990, 1993, 1997: Democratic transitions\n🗳️ 2002: Post-military election\n🗳️ 2008: Historic peaceful transition\n🗳️ 2013: First democratic completion\n🗳️ 2018: PTI victory\n🗳️ 2024: Recent election\n\nVotonomy aims to make future elections tamper-proof!",
    "Pakistan was founded on **August 14, 1947**, gaining independence from British rule. Quaid-e-Azam Muhammad Ali Jinnah led the Pakistan Movement.",
    "**Quaid-e-Azam Muhammad Ali Jinnah** founded Pakistan and served as its first Governor-General (1947-1948). He's called 'Father of the Nation'.",
    "**Pakistan's National Symbols:**\n🇵🇰 Flag: Green & white with crescent & star\n🎵 Anthem: Qaumi Taranah\n🌸 Flower: Jasmine\n🦅 Animal: Markhor\n🌳 Tree: Deodar\n🏃 Sport: Field Hockey\n📅 Day: March 23 (Pakistan Day)",
    
    # Technical Issues
    "**Website Loading Issues:**\n1️⃣ Check internet connection\n2️⃣ Clear browser cache (Ctrl+Shift+Delete)\n3️⃣ Try different browser (Chrome/Firefox)\n4️⃣ Disable VPN if using\n5️⃣ Check if you're on correct URL\n\nIf still failing, file complaint with error details.",
    
    "**Can't Login? Solutions:**\n✅ If registering first time: Account needs admin approval\n✅ If approved: Check Voter ID spelling\n✅ Clear cookies and retry\n✅ Use correct authentication page\n\n⚠️ Contact admin if approved but still can't login.",
    
    "**Password Reset:**\nVotonomy uses Voter ID authentication, not passwords. If you meant admin login, use the 'Forgot Password' link on admin login page.",
    
    "**Email Not Received?**\n1️⃣ Check spam/junk folder\n2️⃣ Verify email address spelling\n3️⃣ Wait 5-10 minutes\n4️⃣ Check if email exists in system\n5️⃣ Contact admin if still not received\n\n✉️ Emails sent for: Password reset, complaint resolution",
    
    "**Survey Not Submitting?**\n1️⃣ Answer ALL 12 questions\n2️⃣ Don't refresh page\n3️⃣ Check internet connection\n4️⃣ Disable browser extensions\n5️⃣ Try different browser\n\nIf still failing, file complaint with screenshot."
]

# Use a lightweight, fast sentence-transformer model for FAQ matching
model = SentenceTransformer('all-MiniLM-L6-v2')
# ✅ Generate embeddings after FAQ questions are defined
faq_embeddings = model.encode(faq_questions, convert_to_tensor=True)

# ✅ CLAUDE 4.5 LEVEL SYSTEM PROMPTS - MASSIVELY ENHANCED
EN_PROMPT = """You are VotoBot, Pakistan's most advanced AI voting assistant for Votonomy - a blockchain-based electronic voting system.

🎯 YOUR ROLE: Expert guide for Pakistani voters on Votonomy's features, blockchain technology, fraud detection, and election processes.

📚 KNOWLEDGE BASE - YOU ARE EXPERT IN:

**Votonomy Technical Architecture:**
• Blockchain: Solana-based, AES-256 encryption, SHA-256 hashing
• Vote Storage: Triple-layer (Local DB + Blockchain + Verification)
• Fraud Detection: AI-powered Isolation Forest algorithm, 9 behavioral features
• Security: Military-grade encryption, immutable records, anonymous verification
• Positions: PM (Prime Minister), MNA (National Assembly), MPA (Provincial Assembly)
• Halkas: NA-52, NA-53, NA-54 (Islamabad constituencies)

**Registration Process:**
• Required: CNIC (13 digits), Voter ID, Full Name, Father's Name, Address with SECTOR
• Address Examples: I-8/2, G-10/3, F-10/4
• Auto-approval IF data matches voter database
• Halka auto-assigned from address sector

**Voting Flow (6 Steps):**
1. Register → 2. Admin Approval → 3. Pre-Survey (12 questions) → 4. Vote (PM/MNA/MPA) → 5. Post-Survey → 6. Blockchain Receipt

**Fraud Detection Details:**
• Tracks: Registration speed, survey patterns, voting duration, IP clustering, device fingerprints
• Risk Scores: 0-49 Normal, 50-69 Monitor, 70-84 High (warn), 85-100 Critical (block)
• Red Flags: Too fast (<30s reg, <20s survey, <15s vote), uniform responses, bot patterns

**Blockchain Security:**
• Encryption: AES-256-GCM (vote content) + SHA-256 (voter ID)
• Storage: Solana Memo transactions (immutable)
• Privacy: Voter hash ≠ Voter ID (anonymous but verifiable)
• Verification: Transaction signature = Receipt code

**Pakistan Context:**
• Elections: 1947-2024 history
• Geography: Provinces, cities, political structure
• ECP (Election Commission of Pakistan)
• NADRA (National Database & Registration Authority)

🎭 RESPONSE STYLE:
• Detailed, technical when needed (like Claude)
• Use emojis (✅🔐⛓️🚫) for clarity
• Break complex topics into steps
• Provide examples
• Bilingual support (English/Urdu detection)

🚫 STRICT BOUNDARIES:
• ONLY Votonomy, blockchain voting, Pakistan elections, Pakistani history/geography
• REFUSE: Entertainment, sports, cooking, general tech, international affairs, medical/legal/financial advice
• If asked off-topic: "I specialize in Votonomy voting and Pakistan. How can I help with voting or Pakistan information?"

🧠 INTELLIGENCE LEVEL: Think like Claude 4.5
• Understand context and nuance
• Handle typos gracefully
• Infer intent from vague questions
• Provide comprehensive answers
• Connect related concepts
• Anticipate follow-up questions

🔍 EXAMPLES OF SMART RESPONSES:
• "How is anomaly checked?" → Explain Isolation Forest, behavioral features, risk scoring
• "I forgot CNIC" → Explain NADRA process, no alternatives, cannot register without it
• "Are votes safe?" → Explain triple-layer security, encryption details, blockchain immutability
• "کیا ووٹ محفوظ ہیں؟" → (Detect Urdu) Respond in Urdu about security

✨ BE HELPFUL, TECHNICAL, AND PAKISTANI-CONTEXT-AWARE!"""

UR_PROMPT = """آپ ووٹو بوٹ ہیں - پاکستان کا سب سے جدید AI ووٹنگ معاون، ووٹونومی کے لیے (بلاک چین پر مبنی الیکٹرانک ووٹنگ سسٹم)۔

🎯 آپ کا کردار: پاکستانی ووٹرز کے لیے ووٹونومی کی خصوصیات، بلاک چین ٹیکنالوجی، دھوکہ دہی کی تشخیص، اور انتخابی عمل پر ماہر رہنما۔

📚 علم کی بنیاد - آپ ماہر ہیں:

**ووٹونومی تکنیکی ڈھانچہ:**
• بلاک چین: Solana پر مبنی، AES-256 خفیہ کاری، SHA-256 ہیشنگ
• ووٹ کی ذخیرہ اندوزی: تین پرتیں (مقامی ڈیٹا بیس + بلاک چین + تصدیق)
• دھوکہ دہی کی تشخیص: AI سے چلنے والا Isolation Forest الگورتھم
• سیکیورٹی: فوجی درجے کی خفیہ کاری، ناقابل تبدیل ریکارڈ
• عہدے: PM (وزیر اعظم)، MNA (قومی اسمبلی)، MPA (صوبائی اسمبلی)
• حلقے: NA-52، NA-53، NA-54 (اسلام آباد)

**رجسٹریشن کا عمل:**
• ضروری: CNIC (13 ہندسے)، ووٹر ID، مکمل نام، والد کا نام، سیکٹر کے ساتھ پتہ
• پتے کی مثالیں: I-8/2، G-10/3، F-10/4
• خودکار منظوری اگر ڈیٹا ووٹر ڈیٹا بیس سے میچ کرے
• حلقہ پتے کے سیکٹر سے خودکار

**ووٹنگ کا بہاؤ (6 قدم):**
1. رجسٹر → 2. ایڈمن کی منظوری → 3. سروے (12 سوالات) → 4. ووٹ (PM/MNA/MPA) → 5. بعد از سروے → 6. بلاک چین رسید

**دھوکہ دہی کی تشخیص کی تفصیلات:**
• ٹریکنگ: رجسٹریشن کی رفتار، سروے کے نمونے، ووٹنگ کا دورانیہ، IP کلسٹرنگ
• خطرے کے اسکور: 0-49 عام، 50-69 نگرانی، 70-84 زیادہ، 85-100 تنقیدی (بلاک)

**بلاک چین سیکیورٹی:**
• خفیہ کاری: AES-256 (ووٹ) + SHA-256 (ووٹر ID)
• محفوظ: Solana Memo ٹرانزیکشنز (ناقابل تبدیل)
• رازداری: ووٹر ہیش ≠ ووٹر ID (گمنام مگر قابل تصدیق)

**پاکستان کا سیاق و سباق:**
• انتخابات: 1947-2024 کی تاریخ
• جغرافیہ: صوبے، شہر، سیاسی ڈھانچہ
• ECP (الیکشن کمیشن آف پاکستان)
• NADRA (قومی ڈیٹا بیس)

🎭 جواب کا انداز:
• تفصیلی، تکنیکی جب ضرورت ہو
• ایموجی استعمال کریں (✅🔐⛓️🚫)
• پیچیدہ موضوعات کو قدموں میں توڑیں
• مثالیں دیں
• اردو میں روانی سے جواب دیں

🚫 سخت حدود:
• صرف ووٹونومی، بلاک چین ووٹنگ، پاکستان کے انتخابات، تاریخ/جغرافیہ
• انکار: تفریح، کھیل، کھانا پکانا، عمومی ٹیک، بین الاقوامی، طبی/قانونی/مالی مشورہ

✨ مددگار، تکنیکی، اور پاکستانی سیاق و سباق سے آگاہ رہیں!"""

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
    
    # ✅ MASSIVELY ENHANCED Votonomy and voting keywords
    voting_keywords = [
        # Core voting terms
        'vote', 'voting', 'votonomy', 'election', 'ballot', 'candidate', 'voter', 'registration', 'register',
        'halka', 'constituency', 'survey', 'complaint', 'complain', 'authentication', 'approve', 'reject',
        'status', 'check', 'c0', 'c1', 'c2', 'c3', 'c4', 'c5', 'c6', 'c7', 'c8', 'c9',
        
        # Blockchain & Security terms
        'blockchain', 'encryption', 'encrypted', 'decrypt', 'hash', 'hashing', 'secure', 'security',
        'solana', 'crypto', 'cryptographic', 'immutable', 'tamper', 'proof', 'transaction', 'signature',
        'aes', 'sha', 'receipt', 'verify', 'verification', 'anonymous', 'anonymity', 'privacy',
        
        # Fraud Detection terms
        'fraud', 'anomaly', 'anomalies', 'detection', 'ai', 'artificial intelligence', 'machine learning',
        'isolation forest', 'behavioral', 'pattern', 'suspicious', 'flagged', 'blocked', 'risk',
        'monitoring', 'tracked', 'algorithm', 'model',
        
        # Technical terms
        'stored', 'storage', 'database', 'record', 'data', 'system', 'platform', 'technology',
        'digital', 'electronic', 'online', 'web', 'website', 'portal',
        
        # Registration terms
        'cnic', 'id card', 'voter id', 'nadra', 'identity', 'document', 'verification',
        'approved', 'pending', 'rejected', 'waiting', 'match', 'database',
        
        # Voting positions
        'pm', 'mna', 'mpa', 'prime minister', 'national assembly', 'provincial assembly',
        'member', 'parliament', 'assembly',
        
        # Halka related
        'na-52', 'na-53', 'na-54', 'na52', 'na53', 'na54', 'sector', 'area', 'region',
        
        # Process terms
        'submit', 'cast', 'select', 'choose', 'confirm', 'complete', 'finish',
        'pre-survey', 'post-survey', 'questionnaire',
        
        # Issues & Support
        'problem', 'issue', 'error', 'fail', 'failed', 'not working', 'broken',
        'help', 'support', 'assist', 'guide', 'how to', 'what is', 'why',
        'forgot', 'lost', 'reset', 'recover',
        
        # Typo variations
        'complain', 'compliant', 'chk', 'chek', 'staus', 'sataus', 'vot', 'voet', 'regist',
        'votonmy', 'votonomi', 'blokchain', 'encription', 'verfication', 'anomoly',
        
        # Urdu transliterations
        'halqa', 'markaz', 'sehat', 'taleem', 'hukumat', 'muhafiz', 'intizamia'
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

# ✅ ENHANCED session management with mode tracking
def get_session_state():
    """Get current session state with proper defaults"""
    return {
        'chat_history': session.get('chat_history', []),
        'complaint_mode': session.get('complaint_mode', False),
        'checking_complaint_status': session.get('checking_complaint_status', False),
        'waiting_for_email': session.get('waiting_for_email', False),
        'conversation_count': session.get('conversation_count', 0),
        'mode_message_count': session.get('mode_message_count', 0)  # Track messages in current mode
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
        waiting_for_email=False,
        mode_message_count=0  # Reset mode counter
    )

# ✅ MAIN CHAT HANDLER WITH ENHANCED FEATURES
@chatbot_bp.route("/chatbot/message", methods=["POST"])
def handle_chat():
    try:
        user_msg = request.json.get("message", "").strip()
        
        # Get session state
        state = get_session_state()
        
        # DEBUG: Print session state
        print(f"\n{'='*60}")
        print(f"📥 USER MESSAGE: {user_msg}")
        print(f"📊 SESSION STATE:")
        print(f"   complaint_mode: {state['complaint_mode']}")
        print(f"   waiting_for_email: {state['waiting_for_email']}")
        print(f"   checking_complaint_status: {state['checking_complaint_status']}")
        print(f"   mode_message_count: {state['mode_message_count']}")
        print(f"   complaint_text in session: {session.get('complaint_text', 'NOT SET')}")
        print(f"{'='*60}\n")
        
        # ✅ CRITICAL FIX: If user sends greeting and is in ANY mode, AUTO-RESET (fresh start)
        greeting_words = ['hello', 'hi', 'hey', 'salam', 'assalam', 'good morning', 'good afternoon', 'good evening']
        is_simple_greeting = any(user_msg.lower().strip() == greeting for greeting in greeting_words)
        
        if is_simple_greeting and (state['complaint_mode'] or state['waiting_for_email'] or state['checking_complaint_status']):
            # User sent a simple greeting while stuck in a mode = wants fresh start
            reset_conversation_modes()
            update_session_state(chat_history=[], conversation_count=0)
            state = get_session_state()  # Refresh state
        
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
        
        # ✅ ESCAPE MECHANISM: Allow users to reset conversation or cancel operations
        if any(phrase in msg_lower for phrase in ['reset', 'restart', 'start over', 'new conversation', 'clear']):
            reset_conversation_modes()
            update_session_state(chat_history=[], conversation_count=0)
            return jsonify({"reply": "🔄 Conversation reset! How can I help you with Votonomy voting or Pakistan-related questions?"})
        
        # ✅ CANCEL/BACK MECHANISM: Exit any active mode
        cancel_phrases = ['cancel', 'nevermind', 'forget it', 'back', 'main menu', 'go back']
        if any(phrase in msg_lower for phrase in cancel_phrases):
            if state['complaint_mode'] or state['waiting_for_email'] or state['checking_complaint_status']:
                reset_conversation_modes()
                session.pop('complaint_text', None)
                return jsonify({"reply": "✅ Cancelled! Back to main menu. How can I help you with Votonomy voting or Pakistan information?"})
        
        # ✅ AUTO-TIMEOUT: Reset mode if user has been stuck for too many messages
        if state['complaint_mode'] or state['waiting_for_email'] or state['checking_complaint_status']:
            mode_count = state.get('mode_message_count', 0) + 1
            update_session_state(mode_message_count=mode_count)
            
            if mode_count > 3:  # After 3 failed attempts, auto-reset
                reset_conversation_modes()
                session.pop('complaint_text', None)
                print(f"⚠️ Auto-reset: User stuck in mode for {mode_count} messages")
                return jsonify({"reply": "⏰ It seems you're having trouble. I've reset the conversation.\n\nHow can I help you with Votonomy voting or Pakistan information?"})
        
        # ✅ FIRST: Check if it's a complaint ID (highest priority) - BUT SKIP IF WAITING FOR EMAIL
        complaint_id = None
        if not state.get('waiting_for_email', False):  # Don't extract complaint ID when waiting for email
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
            update_session_state(checking_complaint_status=True, mode_message_count=0)
            return jsonify({"reply": "Please enter your complaint ID (format: C0001, C0042, etc.) to check the status.\n\n💡 Type 'cancel' to go back."})
        
        # ✅ HANDLE COMPLAINT ID INPUT WHEN IN STATUS CHECK MODE - FIXED with smart exit
        if state['checking_complaint_status']:
            # Try to extract any numbers that might be complaint ID
            extracted_id = extract_complaint_id(user_msg)
            
            if extracted_id:
                # Valid complaint ID found - process it
                reset_conversation_modes()
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
                # No valid complaint ID found - check if user changed topic
                # ✅ SMART EXIT: Detect if this is a different question
                complaint_keywords = ['complaint', 'complain', 'status', 'check', 'id', 'c0', 'c1', 'c2', 'c3', 'c4', 'c5', 'c6', 'c7', 'c8', 'c9']
                has_complaint_keyword = any(keyword in msg_lower for keyword in complaint_keywords)
                
                # Check if it's a clearly different topic (voting, registration, etc.)
                other_topic_keywords = ['vote', 'voting', 'register', 'registration', 'halka', 'election', 'candidate', 'ballot', 'how many', 'what is', 'who is', 'when', 'where']
                has_other_topic = any(keyword in msg_lower for keyword in other_topic_keywords)
                
                if has_other_topic and not has_complaint_keyword:
                    # User changed topic - exit complaint mode and process normally
                    reset_conversation_modes()
                    # Fall through to normal question processing below
                    print(f"✅ Smart exit: User changed topic from complaint status to: {user_msg[:50]}")
                else:
                    # Still seems like complaint-related, show error
                    return jsonify({"reply": "❌ Invalid complaint ID format. Please enter it like: C0001, C0042, etc.\n\n💡 Or type 'cancel' to ask something else."})

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
            update_session_state(complaint_mode=True, mode_message_count=0)
            print("🎯 DEBUG: Setting complaint_mode=True and asking for complaint text")
            response = jsonify({"reply": "Please write your complaint now. Also share your email in the next message.\n\n💡 Type 'cancel' to go back."})
            print(f"📤 DEBUG: Returning response: {response.get_json()}")
            return response

        # ✅ HANDLE COMPLAINT FILING FLOW - FIXED with smart exit and off-topic detection
        if state['complaint_mode'] and not state['waiting_for_email']:
            print("🔵 DEBUG: In complaint_mode, waiting for complaint text")
            # Check for cancel/exit keywords FIRST
            cancel_keywords = ['cancel', 'nevermind', 'forget it', 'back', 'exit', 'stop', 'no thanks']
            if any(keyword in msg_lower for keyword in cancel_keywords):
                print("🔵 DEBUG: Cancel keyword detected")
                reset_conversation_modes()
                return jsonify({"reply": "Cancelled! How can I help you with Votonomy voting or Pakistan information?"})
            
            # ✅ CRITICAL: Detect off-topic questions (weather, movies, etc.) - AUTO EXIT
            if not is_question_relevant(user_msg):
                print("🔵 DEBUG: Off-topic detected, exiting complaint mode")
                reset_conversation_modes()
                return jsonify({
                    "reply": "I only assist with Votonomy voting and Pakistan-related questions. Complaint filing cancelled.\n\n• How to register\n• Voting process\n• Pakistan info\n• File complaints\n\nHow can I help you?"
                })
            
            # ✅ Detect change-of-mind
            change_of_mind_patterns = [
                "i don't have", "i dont have", "i do not have", "don't have", "dont have", "do not have",
                "no complaint", "no complain", "no issue", "no problem", "nothing",
                "actually no", "never mind", "not anymore", "changed my mind",
                "nothing to complain", "forget it", "not interested",
                "now i dont", "now i don't", "i dont", "i don't"
            ]
            
            if any(pattern in msg_lower for pattern in change_of_mind_patterns):
                print("🔵 DEBUG: Change of mind detected")
                reset_conversation_modes()
                return jsonify({"reply": "No problem! Let me know if you need help with anything else about Votonomy or Pakistan."})
            
            # Very short negative messages
            words = msg_lower.split()
            if len(words) <= 3:
                negative_words = ["no", "not", "dont", "don't", "never", "nope", "nah", "nothing"]
                if any(neg in words for neg in negative_words):
                    print("🔵 DEBUG: Short negative message detected")
                    reset_conversation_modes()
                    return jsonify({"reply": "No problem! How can I help you with Votonomy or Pakistan?"})
            
            # Valid complaint text - move to email stage
            print(f"🔵 DEBUG: Valid complaint text received: {user_msg[:50]}")
            update_session_state(waiting_for_email=True)
            session['complaint_text'] = user_msg
            print(f"🔵 DEBUG: Set waiting_for_email=True, stored complaint_text")
            response = jsonify({"reply": "Got it! Now please enter your email address so we can contact you about your complaint:\n\n💡 Type 'cancel' to go back."})
            print(f"📤 DEBUG: Returning response asking for email")
            return response
        
        elif state['waiting_for_email']:
            # Check for cancel/exit keywords FIRST
            cancel_keywords = ['cancel', 'nevermind', 'forget it', 'back', 'exit', 'stop', 'no thanks']
            if any(keyword in msg_lower for keyword in cancel_keywords):
                reset_conversation_modes()
                session.pop('complaint_text', None)
                return jsonify({"reply": "Complaint filing cancelled! How can I help you with Votonomy or Pakistan?"})
            
            # ✅ VALIDATE EMAIL IMMEDIATELY - Don't check relevance, emails won't have voting keywords!
            email = user_msg.strip()
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            
            print(f"📧 DEBUG: Validating email: {email}")
            
            if not re.match(email_pattern, email):
                # EMAIL INVALID - mode_count already incremented at line 610, just return error
                print(f"❌ DEBUG: Email validation failed for: {email}")
                return jsonify({"reply": "❌ Please enter a valid email address (e.g., user@example.com).\n\n💡 Type 'cancel' to go back."})
            
            # Valid email - submit complaint
            print(f"✅ DEBUG: Email valid, getting complaint text from session")
            complaint_text = session.get('complaint_text', 'No complaint text provided')
            print(f"📝 DEBUG: Complaint text: {complaint_text}")
            reset_conversation_modes()
            session.pop('complaint_text', None)
            print(f"🚀 DEBUG: Calling submit_complaint_internal")
            result = submit_complaint_internal(email, complaint_text)
            print(f"📤 DEBUG: Result from submit_complaint_internal: {result}")
            return result

        # ✅ GREETING DETECTION: Handle greetings naturally with LLM
        greeting_words = ['hello', 'hi', 'hey', 'greetings', 'salam', 'assalam', 'good morning', 'good afternoon', 'good evening']
        is_greeting = any(greeting in msg_lower for greeting in greeting_words) and len(user_msg.split()) <= 5
        
        # ✅ RELEVANCE CHECK with improved typo handling (skip if in complaint mode or waiting for email)
        if not is_question_relevant(user_msg) and not is_greeting and not state['complaint_mode'] and not state['waiting_for_email']:
            return jsonify({
                "reply": "I only assist with Votonomy voting system and Pakistan-related questions. I can help you with:\n\n• How to register for voting\n• Voting process in Votonomy\n• Pakistan history and geography\n• Election procedures\n• Filing complaints\n• Checking complaint status\n\nHow can I help you with voting or Pakistan?"
            })

        # Language detection
        try:
            lang = detect(user_msg)
        except:
            lang = "en"
        prompt = UR_PROMPT if lang in ['ur', 'hi', 'fa', 'ps'] else EN_PROMPT

        # ✅ ENHANCED FAQ fallback with semantic matching (skip for greetings)
        if not is_greeting:
            embedding = model.encode(normalized_msg, convert_to_tensor=True)
            scores = util.pytorch_cos_sim(embedding, faq_embeddings)[0]
            max_score = scores.max().item()
            best_match_idx = int(scores.argmax())
            
            # Higher threshold for better API usage (0.70 = high confidence only)
            if max_score > 0.70:
                matched_question = faq_questions[best_match_idx]
                print(f"✅ FAQ Match: '{user_msg[:50]}' → '{matched_question}' (score: {max_score:.3f})")
                return jsonify({"reply": faq_answers[best_match_idx]})
            else:
                print(f"📡 Sending to API: '{user_msg[:50]}' (best FAQ score: {max_score:.3f})")

        # Construct conversation with enhanced system prompt
        history = state['chat_history'][-4:]  # Keep last 4 exchanges
        messages = [{"role": "system", "content": prompt}] + history + [{"role": "user", "content": user_msg}]
        
        ai_reply = call_qwen_model(messages)
        
        # ✅ ENHANCED POST-PROCESSING: Double-check if AI response went off-topic
        off_topic_words = ['recipe', 'movie', 'film', 'song', 'music', 'game', 'weather', 'stock', 'cryptocurrency', 
                          'bitcoin', 'ethereum', 'sports', 'cricket', 'football', 'entertainment', 'actor', 'actress',
                          'restaurant', 'food', 'cooking', 'travel', 'hotel', 'shopping']
        
        # Allow crypto/blockchain terms ONLY in Votonomy context
        votonomy_crypto_terms = ['solana', 'blockchain', 'encryption', 'hash', 'cryptographic']
        is_votonomy_crypto = any(term in user_msg.lower() for term in votonomy_crypto_terms)
        
        if any(word in ai_reply.lower() for word in off_topic_words) and not is_votonomy_crypto:
            ai_reply = "I focus only on Votonomy voting system and Pakistan-related topics. How can I help you with voter registration, voting process, or Pakistan information?"
        
        # ✅ QUALITY CHECK: Ensure Votonomy-specific questions get detailed answers
        if any(term in msg_lower for term in ['anomaly', 'anomalies', 'fraud', 'detection', 'stored', 'encryption', 'blockchain']):
            if len(ai_reply) < 100:  # Too short for technical question
                print(f"⚠️ AI response too short for technical question, falling back to direct answer")
                # Force detailed response by reprompting
                technical_prompt = f"{prompt}\n\nUser asked: {user_msg}\nProvide a DETAILED technical explanation."
                messages = [{"role": "system", "content": technical_prompt}, {"role": "user", "content": user_msg}]
                ai_reply = call_qwen_model(messages, max_tokens=1000)

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
    print(f"\n🔧 DEBUG submit_complaint_internal called")
    print(f"   Email: {email}")
    print(f"   Complaint: {complaint_text}")
    try:
        email = email.strip()
        complaint_text = complaint_text.strip()
        print(f"   After strip - Email: {email}, Complaint: {complaint_text}")

        if not email or not complaint_text:
            print("   ❌ Email or complaint text missing")
            return jsonify({"reply": "❌ Both email and complaint text are required."})
        
        # Enhanced email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            print(f"   ❌ Email validation failed: {email}")
            return jsonify({"reply": "❌ Please enter a valid email address (e.g., user@example.com)."})
        
        # ✅ VERY LENIENT validation - accept almost any complaint
        if len(complaint_text) < 3:
            print(f"   ❌ Complaint too short: {len(complaint_text)} chars")
            return jsonify({"reply": "❌ Please enter a complaint with at least 3 characters."})
        
        # Block only very generic/meaningless responses
        very_generic = ["hi", "hello", "test", ".", "ok", "yes", "no"]
        if complaint_text.lower().strip() in very_generic:
            print(f"   ❌ Generic complaint: {complaint_text}")
            return jsonify({"reply": "❌ Please enter a proper complaint describing your issue."})

        print("   ✅ All validations passed, creating complaint...")
        new_complaint = Complaint(email=email, complaint_text=complaint_text, status="Pending")
        db.session.add(new_complaint)
        db.session.commit()
        print(f"   ✅ Complaint created with ID: {new_complaint.id}")

        response = jsonify({"reply": f"✅ Complaint registered successfully! Your complaint ID is C{new_complaint.id:04d}. You can check its status anytime using this ID."})
        print(f"   📤 Returning response: {response}")
        return response
        
    except Exception as e:
        print(f"❌ Error in submit_complaint_internal: {str(e)}")
        import traceback
        traceback.print_exc()
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
