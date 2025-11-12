# app.py - UPDATED VERSION with Structured Survey + Blockchain Integration

from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from itsdangerous import URLSafeTimedSerializer
from models import db, Voter, Candidate, Vote, Admin, PreSurvey
from admin import admin_bp  # Admin panel routes
from models import Voter, VoterList
from geo_utils import get_halka_from_address
from chatbot import chatbot_bp
# from nlp_analysis import analyze_voter_sentiment  # ✅ OLD NLP - No longer needed
# from content_validator import validate_survey_content, content_validator  # ✅ OLD - No longer needed
from models import PreSurveyNLP, SentimentAnalytics  # Keep for backwards compatibility with existing data
from datetime import datetime
from blockchain.vote_recorder import get_vote_recorder  # ✅ NEW: Blockchain integration

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
# 3. Pre-Election Survey (STRUCTURED - Fast & Accessible for All Users)
# ---------------------------
@app.route('/survey/pre', methods=['GET', 'POST'])
def pre_survey():
    if 'voter_id' not in session:
        return redirect(url_for('authenticate'))

    if request.method == 'POST':
        voter_id = session['voter_id']
        
        # ✅ Check if voter already completed survey
        existing_survey = PreSurvey.query.filter_by(voter_id=voter_id).first()
        if existing_survey:
            flash("⚠️ You have already completed the pre-election survey.", "warning")
            return redirect(url_for('cast_vote'))
        
        try:
            # ✅ Get structured responses (1=Positive, 0=Neutral, -1=Negative)
            survey = PreSurvey(
                voter_id=voter_id,
                economy_satisfaction=int(request.form.get('economy_satisfaction')),
                economy_inflation_impact=int(request.form.get('economy_inflation_impact')),
                government_performance=int(request.form.get('government_performance')),
                government_corruption=int(request.form.get('government_corruption')),
                security_safety=int(request.form.get('security_safety')),
                security_law_order=int(request.form.get('security_law_order')),
                education_quality=int(request.form.get('education_quality')),
                healthcare_access=int(request.form.get('healthcare_access')),
                infrastructure_roads=int(request.form.get('infrastructure_roads')),
                infrastructure_utilities=int(request.form.get('infrastructure_utilities')),
                future_optimism=int(request.form.get('future_optimism')),
                future_confidence=int(request.form.get('future_confidence'))
            )
            
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
# Run the App
# ---------------------------
if __name__ == '__main__':
    app.run(debug=True)