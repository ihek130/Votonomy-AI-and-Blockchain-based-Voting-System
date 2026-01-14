# app.py - UPDATED VERSION with Structured Survey + Blockchain Integration

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from itsdangerous import URLSafeTimedSerializer
from models import db, Voter, Candidate, Vote, Admin, PreSurvey, BehaviorLog, Complaint
from admin import admin_bp  # Admin panel routes
from models import Voter, VoterList
from geo_utils import get_halka_from_address
from chatbot import chatbot_bp
# from nlp_analysis import analyze_voter_sentiment  # ✅ OLD NLP - No longer needed
# from content_validator import validate_survey_content, content_validator  # ✅ OLD - No longer needed
from models import PreSurveyNLP, SentimentAnalytics  # Keep for backwards compatibility with existing data
from datetime import datetime
from blockchain.vote_recorder import get_vote_recorder  # ✅ NEW: Blockchain integration

# ✅ NEW: Fraud Detection Integration
from fraud_detection.behavior_analyzer import get_behavior_analyzer
from fraud_detection.fraud_detector import get_fraud_detector
from fraud_detection.pattern_detector import get_pattern_detector
import time

app = Flask(__name__)

app.register_blueprint(chatbot_bp)


# ---------------------------
# Configurations
# ---------------------------
app.secret_key = "f8b6e12a9f2b3e7d5412a4d9c6e8b731ffcae4e58b2d3c7b43fafe16d5a718e3"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///votonomy.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ---------------------------
# Email Config for Forgot Password (Gmail SMTP)
# ---------------------------
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'ihek0011@gmail.com'       # 🔁 Replace with actual email
app.config['MAIL_PASSWORD'] = 'kpop tsvc bodb zggm'        # 🔁 Replace with actual app password

# ---------------------------
# Extensions Initialization
# ---------------------------
db.init_app(app)
mail = Mail(app)
app.mail = mail  # Make mail accessible from blueprints if needed

# Create DB Tables
with app.app_context():
    db.create_all()

# Register admin routes
app.register_blueprint(admin_bp, url_prefix='/admin')

# ✅ UPDATED: Simple analytics for structured survey responses
def update_sentiment_analytics():
    """Update aggregated sentiment analytics for admin dashboard - Structured Survey Version"""
    try:
        # Get all structured surveys
        all_surveys = PreSurvey.query.all()
        
        if not all_surveys:
            print("No survey responses found")
            return
        
        total_responses = len(all_surveys)
        
        # ✅ Calculate overall sentiment distribution from structured responses
        positive_count = sum(1 for s in all_surveys if s.overall_sentiment == 'Positive')
        negative_count = sum(1 for s in all_surveys if s.overall_sentiment == 'Negative')
        neutral_count = total_responses - positive_count - negative_count
        
        positive_percentage = (positive_count / total_responses) * 100
        negative_percentage = (negative_count / total_responses) * 100
        neutral_percentage = (neutral_count / total_responses) * 100
        
        # ✅ Calculate average sentiment score
        avg_sentiment = sum(s.overall_score for s in all_surveys) / total_responses
        
        # ✅ NEW: Aggregate topic-wise sentiments from structured responses
        topic_sentiments = {}
        
        # Economy
        economy_avg = sum([s.economy_satisfaction + s.economy_inflation_impact for s in all_surveys]) / (total_responses * 2)
        topic_sentiments['Economy'] = {
            'average_score': round(economy_avg, 2),
            'positive_count': sum(1 for s in all_surveys if (s.economy_satisfaction + s.economy_inflation_impact) > 0),
            'negative_count': sum(1 for s in all_surveys if (s.economy_satisfaction + s.economy_inflation_impact) < 0),
            'neutral_count': sum(1 for s in all_surveys if (s.economy_satisfaction + s.economy_inflation_impact) == 0)
        }
        
        # Government
        govt_avg = sum([s.government_performance + s.government_corruption for s in all_surveys]) / (total_responses * 2)
        topic_sentiments['Government Performance'] = {
            'average_score': round(govt_avg, 2),
            'positive_count': sum(1 for s in all_surveys if (s.government_performance + s.government_corruption) > 0),
            'negative_count': sum(1 for s in all_surveys if (s.government_performance + s.government_corruption) < 0),
            'neutral_count': sum(1 for s in all_surveys if (s.government_performance + s.government_corruption) == 0)
        }
        
        # Security
        security_avg = sum([s.security_safety + s.security_law_order for s in all_surveys]) / (total_responses * 2)
        topic_sentiments['Security & Law'] = {
            'average_score': round(security_avg, 2),
            'positive_count': sum(1 for s in all_surveys if (s.security_safety + s.security_law_order) > 0),
            'negative_count': sum(1 for s in all_surveys if (s.security_safety + s.security_law_order) < 0),
            'neutral_count': sum(1 for s in all_surveys if (s.security_safety + s.security_law_order) == 0)
        }
        
        # Education & Healthcare
        edu_health_avg = sum([s.education_quality + s.healthcare_access for s in all_surveys]) / (total_responses * 2)
        topic_sentiments['Education & Healthcare'] = {
            'average_score': round(edu_health_avg, 2),
            'positive_count': sum(1 for s in all_surveys if (s.education_quality + s.healthcare_access) > 0),
            'negative_count': sum(1 for s in all_surveys if (s.education_quality + s.healthcare_access) < 0),
            'neutral_count': sum(1 for s in all_surveys if (s.education_quality + s.healthcare_access) == 0)
        }
        
        # Infrastructure
        infra_avg = sum([s.infrastructure_roads + s.infrastructure_utilities for s in all_surveys]) / (total_responses * 2)
        topic_sentiments['Infrastructure'] = {
            'average_score': round(infra_avg, 2),
            'positive_count': sum(1 for s in all_surveys if (s.infrastructure_roads + s.infrastructure_utilities) > 0),
            'negative_count': sum(1 for s in all_surveys if (s.infrastructure_roads + s.infrastructure_utilities) < 0),
            'neutral_count': sum(1 for s in all_surveys if (s.infrastructure_roads + s.infrastructure_utilities) == 0)
        }
        
        # Future Expectations
        future_avg = sum([s.future_optimism + s.future_confidence for s in all_surveys]) / (total_responses * 2)
        topic_sentiments['Future Expectations'] = {
            'average_score': round(future_avg, 2),
            'positive_count': sum(1 for s in all_surveys if (s.future_optimism + s.future_confidence) > 0),
            'negative_count': sum(1 for s in all_surveys if (s.future_optimism + s.future_confidence) < 0),
            'neutral_count': sum(1 for s in all_surveys if (s.future_optimism + s.future_confidence) == 0)
        }
        
        # ✅ Halka-wise sentiment
        halka_sentiments = {}
        for survey in all_surveys:
            voter = Voter.query.filter_by(voter_id=survey.voter_id).first()
            if voter and voter.halka:
                if voter.halka not in halka_sentiments:
                    halka_sentiments[voter.halka] = {'scores': [], 'count': 0}
                halka_sentiments[voter.halka]['scores'].append(survey.overall_score)
                halka_sentiments[voter.halka]['count'] += 1
        
        for halka in halka_sentiments:
            scores = halka_sentiments[halka]['scores']
            halka_sentiments[halka]['average_score'] = sum(scores) / len(scores)
            halka_sentiments[halka]['sentiment_label'] = 'Positive' if halka_sentiments[halka]['average_score'] > 0.2 else 'Negative' if halka_sentiments[halka]['average_score'] < -0.2 else 'Neutral'
        
        # ✅ Update or create analytics record
        analytics = SentimentAnalytics.query.first()
        if not analytics:
            analytics = SentimentAnalytics()
            db.session.add(analytics)
        
        analytics.total_responses = total_responses
        analytics.positive_percentage = round(positive_percentage, 2)
        analytics.negative_percentage = round(negative_percentage, 2)
        analytics.neutral_percentage = round(neutral_percentage, 2)
        analytics.average_sentiment_score = round(avg_sentiment, 3)
        analytics.topic_sentiments = topic_sentiments
        analytics.trending_keywords = {}  # No keywords in structured survey
        analytics.emotion_distribution = {}  # No emotions in structured survey
        analytics.halka_sentiments = halka_sentiments
        analytics.last_updated = datetime.utcnow()
        
        db.session.commit()
        print(f"✅ Sentiment analytics updated: {total_responses} responses processed")
        
    except Exception as e:
        print(f"Error updating sentiment analytics: {str(e)}")
        db.session.rollback()


def update_post_survey_analytics():
    """Update aggregated analytics for post-election survey"""
    from models import PostSurvey, PostSurveyAnalytics, PreSurvey
    
    try:
        # Get all post-surveys
        all_post_surveys = PostSurvey.query.all()
        
        if not all_post_surveys:
            print("No post-survey responses found")
            return
        
        total_responses = len(all_post_surveys)
        
        # Calculate overall sentiment distribution
        positive_count = sum(1 for s in all_post_surveys if s.overall_sentiment == 'Positive')
        negative_count = sum(1 for s in all_post_surveys if s.overall_sentiment == 'Negative')
        neutral_count = total_responses - positive_count - negative_count
        
        positive_percentage = (positive_count / total_responses) * 100
        negative_percentage = (negative_count / total_responses) * 100
        neutral_percentage = (neutral_count / total_responses) * 100
        
        # Calculate topic-wise sentiments
        topic_sentiments = {}
        
        # Voting Experience
        voting_exp_avg = sum([s.voting_ease + s.technical_issues for s in all_post_surveys]) / (total_responses * 2)
        topic_sentiments['Voting Experience'] = {
            'average_score': round(voting_exp_avg, 2),
            'positive_count': sum(1 for s in all_post_surveys if (s.voting_ease + s.technical_issues) > 0),
            'negative_count': sum(1 for s in all_post_surveys if (s.voting_ease + s.technical_issues) < 0),
            'neutral_count': sum(1 for s in all_post_surveys if (s.voting_ease + s.technical_issues) == 0)
        }
        
        # Election Transparency
        transparency_avg = sum([s.blockchain_trust + s.process_transparency for s in all_post_surveys]) / (total_responses * 2)
        topic_sentiments['Election Transparency'] = {
            'average_score': round(transparency_avg, 2),
            'positive_count': sum(1 for s in all_post_surveys if (s.blockchain_trust + s.process_transparency) > 0),
            'negative_count': sum(1 for s in all_post_surveys if (s.blockchain_trust + s.process_transparency) < 0),
            'neutral_count': sum(1 for s in all_post_surveys if (s.blockchain_trust + s.process_transparency) == 0)
        }
        
        # Candidate Quality
        candidate_avg = sum([s.candidate_satisfaction + s.information_adequacy for s in all_post_surveys]) / (total_responses * 2)
        topic_sentiments['Candidate Quality'] = {
            'average_score': round(candidate_avg, 2),
            'positive_count': sum(1 for s in all_post_surveys if (s.candidate_satisfaction + s.information_adequacy) > 0),
            'negative_count': sum(1 for s in all_post_surveys if (s.candidate_satisfaction + s.information_adequacy) < 0),
            'neutral_count': sum(1 for s in all_post_surveys if (s.candidate_satisfaction + s.information_adequacy) == 0)
        }
        
        # Result Satisfaction
        result_avg = sum([s.result_acceptance + s.winner_satisfaction for s in all_post_surveys]) / (total_responses * 2)
        topic_sentiments['Result Satisfaction'] = {
            'average_score': round(result_avg, 2),
            'positive_count': sum(1 for s in all_post_surveys if (s.result_acceptance + s.winner_satisfaction) > 0),
            'negative_count': sum(1 for s in all_post_surveys if (s.result_acceptance + s.winner_satisfaction) < 0),
            'neutral_count': sum(1 for s in all_post_surveys if (s.result_acceptance + s.winner_satisfaction) == 0)
        }
        
        # System Performance
        system_avg = sum([s.system_performance + s.recommendation for s in all_post_surveys]) / (total_responses * 2)
        topic_sentiments['System Performance'] = {
            'average_score': round(system_avg, 2),
            'positive_count': sum(1 for s in all_post_surveys if (s.system_performance + s.recommendation) > 0),
            'negative_count': sum(1 for s in all_post_surveys if (s.system_performance + s.recommendation) < 0),
            'neutral_count': sum(1 for s in all_post_surveys if (s.system_performance + s.recommendation) == 0)
        }
        
        # Overall Experience
        overall_avg = sum([s.overall_satisfaction + s.system_preference for s in all_post_surveys]) / (total_responses * 2)
        topic_sentiments['Overall Experience'] = {
            'average_score': round(overall_avg, 2),
            'positive_count': sum(1 for s in all_post_surveys if (s.overall_satisfaction + s.system_preference) > 0),
            'negative_count': sum(1 for s in all_post_surveys if (s.overall_satisfaction + s.system_preference) < 0),
            'neutral_count': sum(1 for s in all_post_surveys if (s.overall_satisfaction + s.system_preference) == 0)
        }
        
        # Halka-wise sentiment
        halka_sentiments = {}
        for survey in all_post_surveys:
            voter = Voter.query.filter_by(voter_id=survey.voter_id).first()
            if voter and voter.halka:
                if voter.halka not in halka_sentiments:
                    halka_sentiments[voter.halka] = {'scores': [], 'count': 0}
                halka_sentiments[voter.halka]['scores'].append(survey.overall_score)
                halka_sentiments[voter.halka]['count'] += 1
        
        for halka in halka_sentiments:
            scores = halka_sentiments[halka]['scores']
            halka_sentiments[halka]['average_score'] = sum(scores) / len(scores)
            halka_sentiments[halka]['sentiment_label'] = 'Positive' if halka_sentiments[halka]['average_score'] > 0.2 else 'Negative' if halka_sentiments[halka]['average_score'] < -0.2 else 'Neutral'
        
        # Compare with pre-survey data
        comparison_data = {}
        expectation_reality_gap = {}
        sentiment_shift = {}
        
        all_pre_surveys = PreSurvey.query.all()
        if all_pre_surveys:
            # Overall sentiment shift
            pre_positive = sum(1 for s in all_pre_surveys if s.overall_sentiment == 'Positive')
            pre_total = len(all_pre_surveys)
            pre_positive_pct = (pre_positive / pre_total) * 100
            
            sentiment_shift['overall'] = {
                'pre_positive_pct': round(pre_positive_pct, 2),
                'post_positive_pct': round(positive_percentage, 2),
                'change': round(positive_percentage - pre_positive_pct, 2)
            }
            
            # Topic-wise comparison
            for topic in ['Economy', 'Government Performance', 'Security & Law', 'Education & Healthcare', 'Infrastructure', 'Future Expectations']:
                # Map pre-survey topics to general expectations
                if topic == 'Future Expectations':
                    # Compare with overall satisfaction
                    expectation_reality_gap[topic] = {
                        'pre_avg': sum([s.future_optimism + s.future_confidence for s in all_pre_surveys]) / (len(all_pre_surveys) * 2),
                        'post_avg': overall_avg,
                        'gap': round(overall_avg - (sum([s.future_optimism + s.future_confidence for s in all_pre_surveys]) / (len(all_pre_surveys) * 2)), 2)
                    }
        
        # Update or create analytics record
        analytics = PostSurveyAnalytics.query.first()
        if not analytics:
            analytics = PostSurveyAnalytics()
            db.session.add(analytics)
        
        analytics.total_responses = total_responses
        analytics.positive_percentage = round(positive_percentage, 2)
        analytics.negative_percentage = round(negative_percentage, 2)
        analytics.neutral_percentage = round(neutral_percentage, 2)
        analytics.topic_sentiments = topic_sentiments
        analytics.halka_sentiments = halka_sentiments
        analytics.comparison_data = comparison_data
        analytics.expectation_reality_gap = expectation_reality_gap
        analytics.sentiment_shift = sentiment_shift
        analytics.last_updated = datetime.utcnow()
        
        db.session.commit()
        print(f"✅ Post-survey analytics updated: {total_responses} responses processed")
        
    except Exception as e:
        print(f"Error updating post-survey analytics: {str(e)}")
        db.session.rollback()

# ---------------------------
# Home Page
# ---------------------------
@app.route('/')
def index():
    return render_template('index.html')

# ---------------------------
# 1. User Authentication (Fixed Flow)
# ---------------------------
@app.route('/authenticate', methods=['GET', 'POST'])
def authenticate():
    if request.method == 'POST':
        voter_id = request.form.get('voter_id').strip()

        # ✅ STEP 1: Check if Voter ID exists in CSV database
        voter_list_record = VoterList.query.filter_by(voter_id=voter_id).first()
        if not voter_list_record:
            flash("❌ Your Voter ID does not exist in our database. You are not eligible to vote.", "danger")
            return redirect(url_for('authenticate'))

        # ✅ STEP 2: Check if this voter has already voted
        existing_vote = Vote.query.filter_by(voter_id=voter_id).first()
        if existing_vote:
            flash("❌ You have already completed the voting process. You are not allowed to vote again.", "danger")
            return redirect(url_for('authenticate'))

        # ✅ STEP 3: Voter ID is valid and hasn't voted - check if already registered
        existing_voter = Voter.query.filter_by(voter_id=voter_id).first()
        
        if existing_voter and existing_voter.approved:
            # ✅ Voter is registered and approved - proceed to voting
            session['voter_id'] = voter_id
            session['name'] = existing_voter.name
            session['step'] = 'authenticated'
            return redirect(url_for('pre_survey'))
        
        elif existing_voter and not existing_voter.approved:
            # ✅ Voter registered but pending approval
            flash("⚠️ Your registration is still pending approval.", "warning")
            return redirect(url_for('authenticate'))
        
        else:
            # ✅ Valid Voter ID, hasn't voted, not registered yet - proceed to registration
            session['voter_id'] = voter_id
            flash("✅ Your Voter ID is valid. Please complete your registration.", "info")
            return redirect(url_for('register'))

    return render_template("auth.html")

# ---------------------------
# 2. User Registration (Fixed - No duplicate messages)
# ---------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    # ✅ Ensure user has valid session from authentication
    if 'voter_id' not in session:
        return redirect(url_for('authenticate'))
    
    # ✅ FRAUD DETECTION: Start behavior tracking
    if 'session_id' not in session:
        session['session_id'] = f"{session['voter_id']}_{int(time.time())}"
    
    if 'registration_start' not in session:
        session['registration_start'] = time.time()
        
        # Initialize behavior analyzer
        behavior_analyzer = get_behavior_analyzer()
        behavior_analyzer.start_session(
            voter_id=session['voter_id'],
            session_id=session['session_id'],
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string
        )
        behavior_analyzer.log_registration_start(session['session_id'])
    
    if request.method == 'POST':
        # ✅ Get voter_id from session (already verified in authentication)
        voter_id = session.get('voter_id')
        
        # ✅ FRAUD DETECTION: Track registration duration
        registration_duration = int(time.time() - session.get('registration_start', time.time()))
        
        # Get form data
        name = request.form['name'].strip()
        father_name = request.form['father_name'].strip()
        cnic = request.form['id_card'].strip()
        city = request.form['city'].strip()
        province = request.form['province'].strip()
        gender = request.form['gender'].strip()
        age = request.form['age'].strip()
        address = request.form['address'].strip()
        town = request.form.get('town', '').strip()
        phone = request.form.get('phone', '').strip()
        
        # ✅ FRAUD DETECTION: Log registration completion
        behavior_analyzer = get_behavior_analyzer()
        behavior_analyzer.log_registration_end(session['session_id'], corrections=0)

        # Auto-assign halka based on address
        halka = get_halka_from_address(address)
        if not halka:
            flash("❌ Address sector not recognized. Please use a valid Islamabad address.", "danger")
            return redirect(url_for('register'))

        # ✅ Match voter details against CSV record (excluding voter_id as it's already verified)
        record = VoterList.query.filter_by(
            voter_id=voter_id,  # ✅ Include voter_id to get the correct record
            full_name=name,
            father_name=father_name,
            cnic=cnic,
            city=city,
            province=province,
            gender=gender,
            age=int(age)
        ).first()

        if record:
            # ✅ Check if voter is already registered (double-check)
            existing_voter = Voter.query.filter_by(voter_id=voter_id).first()
            if existing_voter:
                flash("❌ This voter is already registered.", "warning")
                return redirect(url_for('authenticate'))
            
            # ✅ Create new voter record
            voter = Voter(
                voter_id=voter_id,
                name=name,
                father_name=father_name,
                id_card=cnic,
                city=city,
                province=province,
                gender=gender,
                age=int(age),
                town=town,
                phone=phone,
                address=address,
                halka=halka,
                approved=True
            )
            db.session.add(voter)
            db.session.commit()
            
            # ✅ Update session
            session['name'] = voter.name
            session['step'] = 'authenticated'
            
            return redirect(url_for('pre_survey'))

        else:
            flash("❌ Your information does not match our voter records. Please verify all details are correct.", "danger")
            return redirect(url_for('register'))

    return render_template('register.html')

# ---------------------------
# 3. Pre-Election Survey (STRUCTURED - Fast & Accessible for All Users)
# ---------------------------
@app.route('/survey/pre', methods=['GET', 'POST'])
def pre_survey():
    if 'voter_id' not in session:
        return redirect(url_for('authenticate'))
    
    # ✅ FRAUD DETECTION: Track survey start
    if request.method == 'GET' and 'survey_start' not in session:
        session['survey_start'] = time.time()
        
        behavior_analyzer = get_behavior_analyzer()
        if 'session_id' in session:
            behavior_analyzer.log_survey_start(session['session_id'])

    if request.method == 'POST':
        voter_id = session['voter_id']
        
        # ✅ FRAUD DETECTION: Calculate survey duration
        survey_duration = int(time.time() - session.get('survey_start', time.time()))
        
        # ✅ Check if voter already completed survey
        existing_survey = PreSurvey.query.filter_by(voter_id=voter_id).first()
        if existing_survey:
            flash("⚠️ You have already completed the pre-election survey.", "warning")
            return redirect(url_for('cast_vote'))
        
        try:
            # ✅ Get structured responses (1=Positive, 0=Neutral, -1=Negative)
            responses = [
                int(request.form.get('economy_satisfaction')),
                int(request.form.get('economy_inflation_impact')),
                int(request.form.get('government_performance')),
                int(request.form.get('government_corruption')),
                int(request.form.get('security_safety')),
                int(request.form.get('security_law_order')),
                int(request.form.get('education_quality')),
                int(request.form.get('healthcare_access')),
                int(request.form.get('infrastructure_roads')),
                int(request.form.get('infrastructure_utilities')),
                int(request.form.get('future_optimism')),
                int(request.form.get('future_confidence'))
            ]
            
            survey = PreSurvey(
                voter_id=voter_id,
                economy_satisfaction=responses[0],
                economy_inflation_impact=responses[1],
                government_performance=responses[2],
                government_corruption=responses[3],
                security_safety=responses[4],
                security_law_order=responses[5],
                education_quality=responses[6],
                healthcare_access=responses[7],
                infrastructure_roads=responses[8],
                infrastructure_utilities=responses[9],
                future_optimism=responses[10],
                future_confidence=responses[11]
            )
            
            # ✅ FRAUD DETECTION: Log survey completion
            behavior_analyzer = get_behavior_analyzer()
            if 'session_id' in session:
                behavior_analyzer.log_survey_end(session['session_id'], responses)
                
                # Check for survey bot patterns
                if survey_duration < 20:
                    flash("⚠️ Survey completed very quickly. Your response has been flagged for review.", "warning")
                elif len(set(responses)) == 1:
                    flash("⚠️ Uniform survey responses detected. Your response has been flagged for review.", "warning")
            
            # ✅ Calculate overall sentiment
            survey.calculate_overall_sentiment()
            
            # ✅ Save to database
            db.session.add(survey)
            db.session.commit()
            
            session['step'] = 'pre_done'
            flash("✅ Thank you for completing the survey! You can now proceed to vote.", "success")
            return redirect(url_for('cast_vote'))
            
        except Exception as e:
            print(f"Error saving survey: {str(e)}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            flash("❌ Error saving your responses. Please try again.", "danger")
            return redirect(url_for('pre_survey'))

    return render_template('pre_survey_structured.html')

# ---------------------------
# 4. Vote Casting
# ---------------------------
@app.route('/vote', methods=['GET', 'POST'])
def cast_vote():
    if session.get('step') != 'pre_done':
        return redirect(url_for('pre_survey'))

    voter_id = session['voter_id']
    voter = Voter.query.filter_by(voter_id=voter_id).first()

    # ✅ Block repeat voting
    if Vote.query.filter_by(voter_id=voter_id).first():
        flash("❌ You have completed the voting process once and are not allowed to vote again.", "danger")
        return redirect(url_for('confirm_vote'))
    
    # ✅ FRAUD DETECTION: Track voting start
    if request.method == 'GET' and 'voting_start' not in session:
        session['voting_start'] = time.time()
        
        behavior_analyzer = get_behavior_analyzer()
        if 'session_id' in session:
            behavior_analyzer.log_voting_start(session['session_id'])

    if request.method == 'POST':
        # ✅ FRAUD DETECTION: Calculate voting duration
        voting_duration = int(time.time() - session.get('voting_start', time.time()))
        votes = {}
        for key in request.form:
            if key.startswith("votes["):
                position = key.split("[")[1].split("]")[0]
                candidate_id = request.form.get(key)
                if candidate_id:
                    votes[position] = candidate_id

        if len(votes) < 3:
            flash("❌ You must vote for all required positions before submitting.", "danger")
            return redirect(url_for('cast_vote'))
        
        # ✅ FRAUD DETECTION: PRE-VOTE FRAUD CHECK
        behavior_analyzer = get_behavior_analyzer()
        assessment = None
        if 'session_id' in session:
            behavior_analyzer.log_voting_end(session['session_id'])
            
            # Get current behavior metrics
            session_data = behavior_analyzer.get_session_metrics(session['session_id'])
            
            if session_data:
                # Calculate behavior metrics for assessment
                reg_duration = int(session_data.get('registration_duration', 0))
                survey_duration = int(session_data.get('survey_duration', 0))
            else:
                # Session data not found, use defaults
                reg_duration = 0
                survey_duration = 0
            
                # Get survey variance from database
                survey = PreSurvey.query.filter_by(voter_id=voter_id).first()
                if survey:
                    responses = [
                        survey.economy_satisfaction, survey.economy_inflation_impact,
                        survey.government_performance, survey.government_corruption,
                        survey.security_safety, survey.security_law_order,
                        survey.education_quality, survey.healthcare_access,
                        survey.infrastructure_roads, survey.infrastructure_utilities,
                        survey.future_optimism, survey.future_confidence
                    ]
                    import statistics
                    survey_variance = statistics.variance(responses) if len(set(responses)) > 1 else 0.0
                else:
                    survey_variance = 0.0
                
                # Prepare behavior data for fraud detection
                behavior_dict = {
                    'registration_duration': reg_duration,
                    'form_corrections': 0,
                    'survey_duration': survey_duration,
                    'survey_response_variance': survey_variance,
                    'survey_entropy': 1.0 if survey_variance > 0.5 else 0.5,
                    'voting_duration': voting_duration,
                    'candidate_selection_speed': voting_duration // 2,
                    'total_session_duration': reg_duration + survey_duration + voting_duration,
                    'time_of_day': datetime.utcnow().hour
                }
                
                # Run fraud detection BEFORE saving vote
                try:
                    fraud_detector = get_fraud_detector()
                    assessment = fraud_detector.assess_behavior(behavior_dict)
                    
                    print(f"🔍 Pre-Vote Fraud Check: {assessment['risk_score']:.1f}/100 ({assessment['severity']})")
                    
                    # BLOCK VOTE if critical risk (85%+)
                    if assessment['risk_score'] >= 85:
                        flash("🚫 VOTE REJECTED: Your voting behavior has been identified as fraudulent.", "danger")
                        flash(f"Reason: {', '.join(assessment['red_flags'][:3])}", "warning")
                        flash("If you believe this is an error, please contact election administrators.", "info")
                        
                        # Log the blocked attempt
                        behavior_log = behavior_analyzer.save_to_database(voter_id, session['session_id'])
                        behavior_log.isolation_forest_score = assessment['isolation_forest_score']
                        behavior_log.behavioral_risk_score = assessment['risk_score']
                        db.session.commit()
                        
                        # Create fraud alert
                        fraud_detector.create_fraud_alert(voter_id, behavior_log, assessment)
                        
                        print(f"🚫 VOTE BLOCKED for {voter_id}: Risk {assessment['risk_score']:.1f}%")
                        return redirect(url_for('index'))
                    
                    # WARN but ALLOW if high risk (70-84%)
                    elif assessment['risk_score'] >= 70:
                        flash("⚠️ Your voting behavior has been flagged for review.", "warning")
                        flash("Your vote will be recorded but may be verified by administrators.", "info")
                    
                except Exception as e:
                    print(f"⚠️  Fraud detection error: {str(e)}")
                    # If fraud detection fails, allow vote to proceed
        

        # ✅ BLOCKCHAIN INTEGRATION: Initialize vote recorder
        try:
            vote_recorder = get_vote_recorder()
            blockchain_enabled = True
            print("🔗 Blockchain vote recorder initialized")
        except Exception as e:
            blockchain_enabled = False
            print(f"⚠️  Blockchain unavailable: {str(e)}")

        for position, candidate_id in votes.items():
            # STEP 1: Create vote record in local database
            vote = Vote(
                voter_id=voter_id,
                candidate_id=candidate_id,
                position=position,
                created_at=datetime.utcnow()
            )
            db.session.add(vote)
            db.session.flush()  # Get vote.id for reference

            # STEP 2: Record vote on Solana blockchain
            if blockchain_enabled:
                try:
                    print(f"\n🔐 Recording {position} vote on blockchain...")
                    blockchain_result = vote_recorder.record_vote_on_chain(
                        voter_id=voter_id,
                        candidate_id=candidate_id,
                        position=position,
                        halka=voter.halka
                    )

                    if blockchain_result['success']:
                        # Update vote with blockchain data
                        vote.blockchain_tx_signature = blockchain_result['signature']
                        vote.blockchain_slot = blockchain_result['slot']
                        vote.blockchain_timestamp = blockchain_result['timestamp']
                        vote.voter_id_hash = blockchain_result['voter_hash']
                        vote.encrypted_vote_data = blockchain_result['encrypted_data']
                        vote.verification_receipt = blockchain_result['receipt']
                        vote.is_verified_on_chain = True
                        print(f"✅ {position} vote recorded on blockchain: {blockchain_result['signature'][:16]}...")
                    else:
                        # Blockchain failed but vote saved locally
                        vote.is_verified_on_chain = False
                        print(f"⚠️  {position} blockchain recording failed: {blockchain_result.get('error')}")
                        flash(f"⚠️ Vote recorded locally. Blockchain verification pending for {position}.", "warning")
                
                except Exception as e:
                    # Blockchain error - vote still valid in local DB
                    vote.is_verified_on_chain = False
                    print(f"❌ Blockchain error for {position}: {str(e)}")
                    flash(f"⚠️ Vote recorded locally. Blockchain temporarily unavailable for {position}.", "warning")
            else:
                # Blockchain disabled - local vote only
                vote.is_verified_on_chain = False

        db.session.commit()
        
        # ✅ FRAUD DETECTION: Update final behavior log (assessment done pre-vote)
        if 'session_id' in session and 'assessment' in locals():
            behavior_log = BehaviorLog.query.filter_by(
                voter_id=voter_id, 
                session_id=session['session_id']
            ).first()
            
            if behavior_log:
                behavior_log.isolation_forest_score = assessment['isolation_forest_score']
                behavior_log.behavioral_risk_score = assessment['risk_score']
                db.session.commit()
                print(f"✅ Vote allowed with Risk: {assessment['risk_score']:.1f}/100")
        
        # Show success message with blockchain status
        blockchain_count = Vote.query.filter_by(voter_id=voter_id, is_verified_on_chain=True).count()
        if blockchain_count == len(votes):
            flash(f"✅ All {len(votes)} votes recorded and verified on blockchain!", "success")
        elif blockchain_count > 0:
            flash(f"✅ {blockchain_count}/{len(votes)} votes verified on blockchain. Others recorded locally.", "info")
        else:
            flash(f"✅ All {len(votes)} votes recorded locally. Blockchain verification pending.", "info")
        
        session['step'] = 'voted'
        return redirect(url_for('post_survey'))

    # ✅ Filter candidates for voter's Halka only
    all_candidates = Candidate.query.all()
    candidate_data = []
    for c in all_candidates:
        parts = c.candidate_id.split('-')
        if len(parts) >= 3:
            halka = parts[0] + '-' + parts[1]
            position = parts[2]
        else:
            continue

        if halka == voter.halka:
            candidate_data.append({
                'id': c.candidate_id,
                'name': c.candidate_name,
                'halka': halka,
                'position': position
            })

    halkas = [voter.halka]  # Show only assigned Halka
    positions = sorted(set([c['position'] for c in candidate_data]))

    return render_template('vote.html', candidates=candidate_data, halkas=halkas, positions=positions)

# ---------------------------
# 5. Post-Election Survey
# ---------------------------
@app.route('/survey/post', methods=['GET', 'POST'])
def post_survey():
    from models import PostSurvey
    
    if session.get('step') != 'voted':
        return redirect(url_for('cast_vote'))

    voter_id = session.get('voter_id')
    
    # Check if already completed
    existing_survey = PostSurvey.query.filter_by(voter_id=voter_id).first()
    if existing_survey and request.method == 'GET':
        flash('You have already completed the post-election survey.', 'info')
        session['step'] = 'post_done'
        return redirect(url_for('confirm_vote'))
    
    if request.method == 'POST':
        try:
            # Collect all 12 question responses
            voting_ease = int(request.form.get('voting_ease'))
            technical_issues = int(request.form.get('technical_issues'))
            blockchain_trust = int(request.form.get('blockchain_trust'))
            process_transparency = int(request.form.get('process_transparency'))
            candidate_satisfaction = int(request.form.get('candidate_satisfaction'))
            information_adequacy = int(request.form.get('information_adequacy'))
            result_acceptance = int(request.form.get('result_acceptance'))
            winner_satisfaction = int(request.form.get('winner_satisfaction'))
            system_performance = int(request.form.get('system_performance'))
            recommendation = int(request.form.get('recommendation'))
            overall_satisfaction = int(request.form.get('overall_satisfaction'))
            system_preference = int(request.form.get('system_preference'))
            
            # Create new survey record
            if existing_survey:
                # Update existing
                existing_survey.voting_ease = voting_ease
                existing_survey.technical_issues = technical_issues
                existing_survey.blockchain_trust = blockchain_trust
                existing_survey.process_transparency = process_transparency
                existing_survey.candidate_satisfaction = candidate_satisfaction
                existing_survey.information_adequacy = information_adequacy
                existing_survey.result_acceptance = result_acceptance
                existing_survey.winner_satisfaction = winner_satisfaction
                existing_survey.system_performance = system_performance
                existing_survey.recommendation = recommendation
                existing_survey.overall_satisfaction = overall_satisfaction
                existing_survey.system_preference = system_preference
                existing_survey.created_at = datetime.utcnow()
                survey = existing_survey
            else:
                # Create new
                survey = PostSurvey(
                    voter_id=voter_id,
                    voting_ease=voting_ease,
                    technical_issues=technical_issues,
                    blockchain_trust=blockchain_trust,
                    process_transparency=process_transparency,
                    candidate_satisfaction=candidate_satisfaction,
                    information_adequacy=information_adequacy,
                    result_acceptance=result_acceptance,
                    winner_satisfaction=winner_satisfaction,
                    system_performance=system_performance,
                    recommendation=recommendation,
                    overall_satisfaction=overall_satisfaction,
                    system_preference=system_preference
                )
                db.session.add(survey)
            
            # Calculate overall sentiment before committing
            survey.calculate_overall_sentiment()
            
            db.session.commit()
            
            # Update analytics
            update_post_survey_analytics()
            
            flash('Thank you for completing the post-election survey!', 'success')
            session['step'] = 'post_done'
            return redirect(url_for('confirm_vote'))
            
        except ValueError:
            flash('Invalid survey data. Please ensure all questions are answered.', 'danger')
            return render_template('post_survey_structured.html')
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'danger')
            return render_template('post_survey_structured.html')
    
    return render_template('post_survey_structured.html')

# ---------------------------
# 6. Vote Confirmation
# ---------------------------
@app.route('/confirm', methods=['GET'])
def confirm_vote():
    if session.get('step') != 'post_done':
        return redirect(url_for('post_survey'))

    # Get all votes for this voter (PM, MNA, MPA)
    votes = Vote.query.filter_by(voter_id=session['voter_id']).all()
    
    # Calculate blockchain verification stats
    total_votes = len(votes)
    verified_votes = sum(1 for v in votes if v.is_verified_on_chain)
    
    session['step'] = 'complete'
    return render_template('confirm.html', 
                         user_votes=votes,
                         total_votes=total_votes,
                         verified_votes=verified_votes)

# ---------------------------
# Complaint Portal API (Anonymous Complaints)
# ---------------------------
@app.route('/api/complaint/submit', methods=['POST'])
def submit_anonymous_complaint():
    """Submit anonymous complaint without email"""
    try:
        data = request.json
        complaint_text = data.get('complaint_text', '').strip()
        
        if not complaint_text:
            return jsonify({"success": False, "message": "❌ Complaint text is required."}), 400
        
        if len(complaint_text) < 10:
            return jsonify({"success": False, "message": "❌ Complaint must be at least 10 characters long."}), 400
        
        # Create complaint with no email
        new_complaint = Complaint(
            email=None,  # Anonymous complaint
            complaint_text=complaint_text,
            status='Pending'
        )
        db.session.add(new_complaint)
        db.session.commit()
        
        complaint_id = f"C{new_complaint.id:04d}"
        
        return jsonify({
            "success": True,
            "message": f"✅ Complaint submitted successfully!",
            "complaint_id": complaint_id
        }), 200
        
    except Exception as e:
        print(f"❌ Error submitting complaint: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": f"❌ Error: {str(e)}"}), 500

@app.route('/api/complaint/status/<complaint_id>', methods=['GET'])
def check_complaint_status(complaint_id):
    """Check status of complaint by ID"""
    try:
        # Extract numeric ID
        if complaint_id.startswith('C'):
            complaint_id = complaint_id[1:]
        
        complaint_id_num = int(complaint_id)
        complaint = Complaint.query.get(complaint_id_num)
        
        if not complaint:
            return jsonify({
                "success": False,
                "message": f"❌ Complaint C{complaint_id_num:04d} not found."
            }), 404
        
        status_emoji = {
            'Pending': '⏳',
            'In Progress': '🔄',
            'Resolved': '✅'
        }
        
        return jsonify({
            "success": True,
            "complaint_id": f"C{complaint.id:04d}",
            "status": complaint.status,
            "status_emoji": status_emoji.get(complaint.status, '📋'),
            "submitted_at": complaint.created_at.strftime('%d/%m/%Y at %H:%M'),
            "response": complaint.response if complaint.response else None
        }), 200
        
    except ValueError:
        return jsonify({
            "success": False,
            "message": "❌ Invalid complaint ID format."
        }), 400
    except Exception as e:
        print(f"Error checking complaint status: {str(e)}")
        return jsonify({
            "success": False,
            "message": "❌ Error checking complaint status."
        }), 500

# ---------------------------
# Run the App
# ---------------------------
if __name__ == '__main__':
    app.run(debug=True)