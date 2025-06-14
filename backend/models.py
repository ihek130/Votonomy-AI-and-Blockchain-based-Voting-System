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
    id = db.Column(db.Integer, primary_key=True)
    voter_id = db.Column(db.String(100), db.ForeignKey('voter.voter_id'), nullable=False)
    responses = db.Column(db.PickleType, nullable=False)  # List of 15 answers (Yes/No/Neutral)


class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), nullable=False)
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