import secrets
from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()

class VoterList(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    voter_id = db.Column(db.String(100), unique=True, nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    father_name = db.Column(db.String(100), nullable=False)
    cnic = db.Column(db.String(20), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    province = db.Column(db.String(100), nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    age = db.Column(db.Integer, nullable=False)



class Voter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    father_name = db.Column(db.String(100), nullable=True)     # ✅ Added
    voter_id = db.Column(db.String(100), unique=True, nullable=False)
    id_card = db.Column(db.String(50), nullable=True)
    age = db.Column(db.Integer, nullable=True)
    gender = db.Column(db.String(10), nullable=True)           # ✅ Added
    province = db.Column(db.String(100), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    town = db.Column(db.String(100), nullable=True)            # ✅ Optional
    phone = db.Column(db.String(20), nullable=True)            # ✅ Optional
    approved = db.Column(db.Boolean, default=False)
    address = db.Column(db.String(200))
    halka = db.Column(db.String(20))
         

class Candidate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    candidate_name = db.Column(db.String(100), nullable=False)
    candidate_id = db.Column(db.String(100), unique=True, nullable=False)
    votes = db.Column(db.Integer, default=0)

class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    voter_id = db.Column(db.String(100), nullable=False)
    candidate_id = db.Column(db.String(100), nullable=False)
    position = db.Column(db.String(100))
    
    # ✅ Blockchain Integration Fields
    blockchain_tx_signature = db.Column(db.String(200), unique=True, nullable=True)  # Solana transaction signature
    blockchain_slot = db.Column(db.BigInteger, nullable=True)                        # Block slot number
    blockchain_timestamp = db.Column(db.DateTime, nullable=True)                     # On-chain timestamp
    voter_id_hash = db.Column(db.String(64), nullable=True)                         # SHA-256 hash for anonymity
    encrypted_vote_data = db.Column(db.Text, nullable=True)                         # AES-256 encrypted payload
    verification_receipt = db.Column(db.String(500), nullable=True)                 # Voter receipt code
    is_verified_on_chain = db.Column(db.Boolean, default=False)                     # Blockchain verification status
    created_at = db.Column(db.DateTime, default=datetime.utcnow)                    # Local timestamp

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    reset_token = db.Column(db.String(100), nullable=True)
    token_expiry = db.Column(db.DateTime, nullable=True)

    def generate_reset_token(self):
        self.reset_token = secrets.token_urlsafe(32)
        self.token_expiry = datetime.utcnow() + timedelta(minutes=30)
        return self.reset_token

    def verify_token(self, token):
        return self.reset_token == token and datetime.utcnow() < self.token_expiry 

class PreSurvey(db.Model):
    """Structured pre-election survey with Yes/No/Neutral responses"""
    id = db.Column(db.Integer, primary_key=True)
    voter_id = db.Column(db.String(100), db.ForeignKey('voter.voter_id'), nullable=False)
    
    # ✅ Economy Questions (1=Positive/Yes, 0=Neutral, -1=Negative/No)
    economy_satisfaction = db.Column(db.Integer, nullable=False)  # Satisfied with economic situation?
    economy_inflation_impact = db.Column(db.Integer, nullable=False)  # Has inflation affected you?
    
    # ✅ Government Performance Questions
    government_performance = db.Column(db.Integer, nullable=False)  # Satisfied with govt performance?
    government_corruption = db.Column(db.Integer, nullable=False)  # Govt reducing corruption?
    
    # ✅ Security & Law Questions
    security_safety = db.Column(db.Integer, nullable=False)  # Feel safe in your area?
    security_law_order = db.Column(db.Integer, nullable=False)  # Law & order improved?
    
    # ✅ Education & Healthcare Questions
    education_quality = db.Column(db.Integer, nullable=False)  # Satisfied with education quality?
    healthcare_access = db.Column(db.Integer, nullable=False)  # Access to healthcare improved?
    
    # ✅ Infrastructure Questions
    infrastructure_roads = db.Column(db.Integer, nullable=False)  # Road conditions satisfactory?
    infrastructure_utilities = db.Column(db.Integer, nullable=False)  # Utilities (electricity/water) reliable?
    
    # ✅ Future Expectations Questions
    future_optimism = db.Column(db.Integer, nullable=False)  # Optimistic about Pakistan's future?
    future_confidence = db.Column(db.Integer, nullable=False)  # Confident in leadership direction?
    
    # ✅ Calculated Overall Sentiment
    overall_sentiment = db.Column(db.String(20))  # Positive/Negative/Neutral (calculated average)
    overall_score = db.Column(db.Float, default=0.0)  # Average of all responses
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def calculate_overall_sentiment(self):
        """Calculate overall sentiment from all responses"""
        responses = [
            self.economy_satisfaction, self.economy_inflation_impact,
            self.government_performance, self.government_corruption,
            self.security_safety, self.security_law_order,
            self.education_quality, self.healthcare_access,
            self.infrastructure_roads, self.infrastructure_utilities,
            self.future_optimism, self.future_confidence
        ]
        
        avg_score = sum(responses) / len(responses)
        self.overall_score = round(avg_score, 2)
        
        if avg_score > 0.2:
            self.overall_sentiment = 'Positive'
        elif avg_score < -0.2:
            self.overall_sentiment = 'Negative'
        else:
            self.overall_sentiment = 'Neutral'
        
        return self.overall_sentiment
    
    def __repr__(self):
        return f'<PreSurvey {self.voter_id}: {self.overall_sentiment}>'


class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), nullable=True)  # Made optional for anonymous complaints
    complaint_text = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='Pending')  # Pending, In Progress, Resolved
    response = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)    

    # Add this to your models.py file

class PreSurveyNLP(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    voter_id = db.Column(db.String(100), db.ForeignKey('voter.voter_id'), nullable=False)
    
    # ✅ Natural Language Responses for each topic
    economic_response = db.Column(db.Text, nullable=True)
    government_response = db.Column(db.Text, nullable=True) 
    security_response = db.Column(db.Text, nullable=True)
    education_healthcare_response = db.Column(db.Text, nullable=True)
    infrastructure_response = db.Column(db.Text, nullable=True)
    future_expectations_response = db.Column(db.Text, nullable=True)
    
    # ✅ Sentiment Analysis Results (Auto-calculated)
    overall_sentiment_score = db.Column(db.Float, default=0.0)  # -1 to 1 scale
    overall_sentiment_label = db.Column(db.String(20), default='Neutral')  # Positive/Negative/Neutral
    
    # ✅ Detailed Analysis Results (JSON stored)
    sentiment_breakdown = db.Column(db.JSON, nullable=True)  # Per-topic sentiment scores
    emotion_analysis = db.Column(db.JSON, nullable=True)     # Emotion detection results
    keywords_extracted = db.Column(db.JSON, nullable=True)   # Important keywords
    topics_detected = db.Column(db.JSON, nullable=True)      # Topic modeling results
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<PreSurveyNLP {self.voter_id}: {self.overall_sentiment_label}>'

class SentimentAnalytics(db.Model):
    """Store aggregated sentiment analytics for admin dashboard"""
    id = db.Column(db.Integer, primary_key=True)
    
    # ✅ Overall Statistics
    total_responses = db.Column(db.Integer, default=0)
    positive_percentage = db.Column(db.Float, default=0.0)
    negative_percentage = db.Column(db.Float, default=0.0)
    neutral_percentage = db.Column(db.Float, default=0.0)
    average_sentiment_score = db.Column(db.Float, default=0.0)
    
    # ✅ Topic-wise Analysis
    topic_sentiments = db.Column(db.JSON, nullable=True)     # Sentiment per topic
    trending_keywords = db.Column(db.JSON, nullable=True)    # Most frequent keywords
    emotion_distribution = db.Column(db.JSON, nullable=True) # Overall emotion breakdown
    
    # ✅ Geographic Analysis
    halka_sentiments = db.Column(db.JSON, nullable=True)     # Sentiment by halka
    
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<SentimentAnalytics: {self.total_responses} responses>'


# ============================================================================
# FRAUD DETECTION MODELS
# ============================================================================

class BehaviorLog(db.Model):
    """Track user behavior for AI fraud detection"""
    __tablename__ = 'behavior_log'
    
    id = db.Column(db.Integer, primary_key=True)
    voter_id = db.Column(db.String(100), db.ForeignKey('voter.voter_id'), nullable=False)
    session_id = db.Column(db.String(100), nullable=False)
    
    # Registration metrics
    registration_duration = db.Column(db.Integer)  # seconds
    form_corrections = db.Column(db.Integer, default=0)
    
    # Survey metrics
    survey_duration = db.Column(db.Integer)  # seconds
    survey_response_variance = db.Column(db.Float)
    survey_entropy = db.Column(db.Float)
    
    # Voting metrics
    voting_duration = db.Column(db.Integer)  # seconds
    candidate_selection_speed = db.Column(db.Integer)  # seconds
    
    # Session metrics
    total_session_duration = db.Column(db.Integer)  # seconds
    ip_address = db.Column(db.String(50))
    device_fingerprint = db.Column(db.String(200))
    user_agent = db.Column(db.String(300))
    
    # AI scores
    isolation_forest_score = db.Column(db.Float)  # Anomaly score
    behavioral_risk_score = db.Column(db.Float)   # Overall risk
    
    # Additional behavioral features
    page_navigation_pattern = db.Column(db.JSON)  # Navigation sequence
    time_of_day = db.Column(db.Integer)  # Hour (0-23)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<BehaviorLog {self.voter_id}: Risk={self.behavioral_risk_score}>'


class FraudAlert(db.Model):
    """Store fraud detection alerts for admin review"""
    __tablename__ = 'fraud_alert'
    
    id = db.Column(db.Integer, primary_key=True)
    voter_id = db.Column(db.String(100), db.ForeignKey('voter.voter_id'), nullable=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('admin.id'), nullable=True)
    
    alert_type = db.Column(db.String(50), nullable=False)  # 'bot', 'coordination', 'timing', etc.
    severity = db.Column(db.String(20), nullable=False)    # 'low', 'medium', 'high', 'critical'
    risk_score = db.Column(db.Float, nullable=False)
    
    description = db.Column(db.Text)
    detected_patterns = db.Column(db.JSON)  # What triggered the alert
    red_flags = db.Column(db.JSON)          # List of suspicious factors
    
    # Investigation
    status = db.Column(db.String(20), default='open')  # 'open', 'investigating', 'false_positive', 'confirmed'
    admin_notes = db.Column(db.Text)
    action_taken = db.Column(db.String(100))  # 'blocked', 'flagged', 'verified', 'ignored'
    resolved_at = db.Column(db.DateTime)
    resolved_by = db.Column(db.Integer, db.ForeignKey('admin.id'))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    voter = db.relationship('Voter', backref='fraud_alerts', foreign_keys=[voter_id])
    
    def __repr__(self):
        return f'<FraudAlert {self.alert_type}: {self.severity} - {self.status}>'


class IPCluster(db.Model):
    """Track voters from same IP/device for pattern analysis"""
    __tablename__ = 'ip_cluster'
    
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(50), nullable=False, unique=True)
    device_fingerprint = db.Column(db.String(200))
    
    # Cluster statistics
    voter_count = db.Column(db.Integer, default=0)
    vote_similarity_score = db.Column(db.Float)     # 0-1: How similar are votes
    timing_variance = db.Column(db.Float)            # Seconds: Time gaps between votes
    survey_similarity = db.Column(db.Float)          # 0-1: Survey response similarity
    geographic_spread = db.Column(db.Float)          # 0-1: CNIC geographic diversity
    
    # Whitelisting for legitimate shared locations
    is_whitelisted = db.Column(db.Boolean, default=False)
    whitelist_reason = db.Column(db.String(200))  # 'internet_cafe', 'community_center', etc.
    
    # Risk assessment
    risk_assessment = db.Column(db.String(20), default='unknown')  # 'normal', 'suspicious', 'fraud'
    coordination_score = db.Column(db.Float)  # Multi-factor coordination risk
    flagged_at = db.Column(db.DateTime)
    
    # Tracking
    first_vote_at = db.Column(db.DateTime)
    last_vote_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<IPCluster {self.ip_address}: {self.voter_count} voters - {self.risk_assessment}>'


class AdminActionLog(db.Model):
    """Monitor admin actions for suspicious behavior"""
    __tablename__ = 'admin_action_log'
    
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('admin.id'), nullable=False)
    
    action_type = db.Column(db.String(50), nullable=False)  # 'approve_voter', 'delete_vote', etc.
    action_target = db.Column(db.String(100))  # ID of affected entity
    action_details = db.Column(db.JSON)        # Additional context
    
    # Risk indicators
    bulk_action = db.Column(db.Boolean, default=False)  # True if part of bulk operation
    unusual_time = db.Column(db.Boolean, default=False)  # True if outside work hours
    risk_score = db.Column(db.Float)
    
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(300))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<AdminAction {self.action_type} by Admin {self.admin_id}>'