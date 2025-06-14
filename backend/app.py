# app.py - FIXED VERSION

from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from itsdangerous import URLSafeTimedSerializer
from models import db, Voter, Candidate, Vote, Admin, PreSurvey
from admin import admin_bp  # Admin panel routes
from models import Voter, VoterList
from geo_utils import get_halka_from_address
from chatbot import chatbot_bp
from nlp_analysis import analyze_voter_sentiment
from content_validator import validate_survey_content, content_validator
from models import PreSurveyNLP, SentimentAnalytics
from datetime import datetime

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

# ✅ FIXED: Helper function to update sentiment analytics
def update_sentiment_analytics():
    """Update aggregated sentiment analytics for admin dashboard"""
    try:
        # Get all surveys
        all_surveys = PreSurveyNLP.query.all()
        
        if not all_surveys:
            return
        
        total_responses = len(all_surveys)
        
        # ✅ Calculate overall sentiment distribution
        positive_count = sum(1 for s in all_surveys if s.overall_sentiment_label == 'Positive')
        negative_count = sum(1 for s in all_surveys if s.overall_sentiment_label == 'Negative')
        neutral_count = total_responses - positive_count - negative_count
        
        positive_percentage = (positive_count / total_responses) * 100
        negative_percentage = (negative_count / total_responses) * 100
        neutral_percentage = (neutral_count / total_responses) * 100
        
        # ✅ Calculate average sentiment score
        avg_sentiment = sum(s.overall_sentiment_score for s in all_surveys) / total_responses
        
        # ✅ Aggregate topic sentiments
        topic_sentiments = {}
        topic_names = ['Economy', 'Government Performance', 'Security & Law', 'Education & Healthcare', 'Infrastructure', 'Future Expectations']
        
        for topic in topic_names:
            scores = []
            for survey in all_surveys:
                if survey.sentiment_breakdown and topic in survey.sentiment_breakdown:
                    topic_sentiment = survey.sentiment_breakdown[topic].get('sentiment', {})
                    if 'compound' in topic_sentiment:
                        scores.append(topic_sentiment['compound'])
            
            if scores:
                topic_sentiments[topic] = {
                    'average_score': sum(scores) / len(scores),
                    'positive_count': sum(1 for score in scores if score > 0.1),
                    'negative_count': sum(1 for score in scores if score < -0.1),
                    'neutral_count': sum(1 for score in scores if -0.1 <= score <= 0.1),
                    'total_responses': len(scores)
                }
        
        # ✅ Aggregate trending keywords
        all_keywords = []
        for survey in all_surveys:
            if survey.keywords_extracted:
                all_keywords.extend([kw['word'] for kw in survey.keywords_extracted[:5]])
        
        keyword_counts = {}
        for keyword in all_keywords:
            keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
        
        trending_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:20]
        
        # ✅ Aggregate emotions
        emotion_totals = {}
        emotion_count = 0
        for survey in all_surveys:
            if survey.emotion_analysis and 'emotions' in survey.emotion_analysis:
                for emotion, percentage in survey.emotion_analysis['emotions'].items():
                    emotion_totals[emotion] = emotion_totals.get(emotion, 0) + percentage
                    emotion_count += 1
        
        emotion_distribution = {}
        if emotion_count > 0:
            for emotion, total in emotion_totals.items():
                emotion_distribution[emotion] = total / len(all_surveys)
        
        # ✅ Halka-wise sentiment (if voters have halka info)
        halka_sentiments = {}
        for survey in all_surveys:
            voter = Voter.query.filter_by(voter_id=survey.voter_id).first()
            if voter and voter.halka:
                if voter.halka not in halka_sentiments:
                    halka_sentiments[voter.halka] = {'scores': [], 'count': 0}
                halka_sentiments[voter.halka]['scores'].append(survey.overall_sentiment_score)
                halka_sentiments[voter.halka]['count'] += 1
        
        for halka in halka_sentiments:
            scores = halka_sentiments[halka]['scores']
            halka_sentiments[halka]['average_score'] = sum(scores) / len(scores)
            halka_sentiments[halka]['sentiment_label'] = 'Positive' if halka_sentiments[halka]['average_score'] > 0.1 else 'Negative' if halka_sentiments[halka]['average_score'] < -0.1 else 'Neutral'
        
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
        analytics.trending_keywords = dict(trending_keywords)
        analytics.emotion_distribution = emotion_distribution
        analytics.halka_sentiments = halka_sentiments
        analytics.last_updated = datetime.utcnow()
        
        db.session.commit()
        print(f"✅ Sentiment analytics updated: {total_responses} responses processed")
        
    except Exception as e:
        print(f"Error updating sentiment analytics: {str(e)}")
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
    
    if request.method == 'POST':
        # ✅ Get voter_id from session (already verified in authentication)
        voter_id = session.get('voter_id')
        
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
# 3. Pre-Election Survey (FIXED - Enhanced Content Validation and Auto-Counter Updates)
# ---------------------------
@app.route('/survey/pre', methods=['GET', 'POST'])
def pre_survey():
    if 'voter_id' not in session:
        return redirect(url_for('authenticate'))

    if request.method == 'POST':
        voter_id = session['voter_id']
        
        # ✅ Check if voter already completed survey
        existing_survey = PreSurveyNLP.query.filter_by(voter_id=voter_id).first()
        if existing_survey:
            flash("⚠️ You have already completed the pre-election survey.", "warning")
            return redirect(url_for('cast_vote'))
        
        # ✅ Get natural language responses
        survey_data = {
            'economic_response': request.form.get('economic_response', '').strip(),
            'government_response': request.form.get('government_response', '').strip(),
            'security_response': request.form.get('security_response', '').strip(),
            'education_healthcare_response': request.form.get('education_healthcare_response', '').strip(),
            'infrastructure_response': request.form.get('infrastructure_response', '').strip(),
            'future_expectations_response': request.form.get('future_expectations_response', '').strip()
        }
        
        # ✅ STEP 1: Validate content relevance and quality (MUCH MORE LENIENT)
        quality_report = validate_survey_content(survey_data)
        
        if not quality_report['overall_valid']:
            # ✅ Show specific errors for invalid responses
            for issue in quality_report['issues']:
                flash(f"❌ {issue}", "danger")
            
            # ✅ Show suggestions for improvement
            for topic, validity in quality_report['topic_validity'].items():
                if not validity['valid']:
                    suggestion = content_validator.suggest_improvements(topic, validity['reason'])
                    flash(f"💡 {topic.replace('_response', '').replace('_', ' ').title()}: {suggestion}", "info")
            
            flash(f"📊 Content Quality Score: {quality_report['quality_score']:.1f}% (minimum 50% required)", "warning")
            return redirect(url_for('pre_survey'))
        
        # ✅ STEP 2: Validate minimum response length (VERY LENIENT - REMOVED)
        # No minimum length requirement - accept even single words
        
        # ✅ STEP 3: Perform NLP sentiment analysis
        try:
            analysis_result = analyze_voter_sentiment(survey_data)
            print(f"✅ Sentiment analysis result: {analysis_result}")  # Debug logging
        except Exception as e:
            print(f"Exception in sentiment analysis: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # ✅ Create a fallback result
            analysis_result = {
                'success': True,
                'analysis': {
                    'overall_sentiment': {'compound': 0.0, 'label': 'Neutral'},
                    'overall_emotions': {'emotions': {}, 'dominant_emotion': 'Neutral'},
                    'overall_keywords': [],
                    'overall_topics': {'topics': {}, 'primary_topic': 'General'},
                    'topic_breakdown': {},
                    'total_word_count': sum(len(text.split()) for text in survey_data.values())
                },
                'overall_score': 0.0,
                'overall_label': 'Neutral'
            }
        
        if analysis_result['success']:
            # ✅ Create survey record with quality metrics
            survey = PreSurveyNLP(
                voter_id=voter_id,
                economic_response=survey_data['economic_response'],
                government_response=survey_data['government_response'],
                security_response=survey_data['security_response'],
                education_healthcare_response=survey_data['education_healthcare_response'],
                infrastructure_response=survey_data['infrastructure_response'],
                future_expectations_response=survey_data['future_expectations_response'],
                overall_sentiment_score=analysis_result.get('overall_score', 0.0),
                overall_sentiment_label=analysis_result.get('overall_label', 'Neutral'),
                sentiment_breakdown=analysis_result['analysis'].get('topic_breakdown', {}),
                emotion_analysis=analysis_result['analysis'].get('overall_emotions', {}),
                keywords_extracted=analysis_result['analysis'].get('overall_keywords', []),
                topics_detected=analysis_result['analysis'].get('overall_topics', {})
            )
            
            try:
                db.session.add(survey)
                db.session.commit()
                
                # ✅ FIXED: Auto-update analytics immediately after survey submission
                try:
                    update_sentiment_analytics()
                    print("✅ Sentiment analytics updated automatically")
                except Exception as analytics_error:
                    print(f"Analytics update error: {analytics_error}")
                    # Don't fail the whole process if analytics update fails
                
                session['step'] = 'pre_done'
                flash("✅ Thank you for sharing your thoughtful responses! Your feedback has been recorded.", "success")
                return redirect(url_for('cast_vote'))
                
            except Exception as db_error:
                print(f"Database error: {db_error}")
                db.session.rollback()
                flash("❌ Error saving your responses. Please try again.", "danger")
                return redirect(url_for('pre_survey'))

    return render_template('pre_survey_nlp.html')

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

    if request.method == 'POST':
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

        for position, candidate_id in votes.items():
            vote = Vote(
                voter_id=voter_id,
                candidate_id=candidate_id,
                position=position
            )
            db.session.add(vote)

        db.session.commit()
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
    if session.get('step') != 'voted':
        return redirect(url_for('cast_vote'))

    if request.method == 'POST':
        session['step'] = 'post_done'
        return redirect(url_for('confirm_vote'))

    return render_template('post_survey.html')

# ---------------------------
# 6. Vote Confirmation
# ---------------------------
@app.route('/confirm', methods=['GET'])
def confirm_vote():
    if session.get('step') != 'post_done':
        return redirect(url_for('post_survey'))

    vote = Vote.query.filter_by(voter_id=session['voter_id']).first()
    session['step'] = 'complete'
    return render_template('confirm.html', user_vote=vote)

# ---------------------------
# Run the App
# ---------------------------
if __name__ == '__main__':
    app.run(debug=True)