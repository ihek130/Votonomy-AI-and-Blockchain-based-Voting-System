# admin.py - FIXED VERSION

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app, send_file, jsonify
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer
from flask_mail import Message
from models import db, Voter, Candidate, Vote, Admin
from data import positions_db, candidate_requests  # candidate_requests remains in-memory
import pandas as pd
import io
from functools import wraps 
from textblob import TextBlob
from models import PreSurveyNLP, SentimentAnalytics
from content_validator import validate_survey_content

admin_bp = Blueprint('admin_bp', __name__, template_folder='templates/admin')

# ------------------------------
# Define admin_login_required decorator BEFORE usage!
# ------------------------------
def admin_login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_bp.admin_login"))
        return func(*args, **kwargs)
    return wrapper

# ------------------------------
# Helper: Token Serializer
# ------------------------------
def get_serializer():
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'])

# ------------------------------
# Vote Count Updater (Dynamic Count)
# ------------------------------
def update_vote_counts():
    vote_data = db.session.query(Vote.candidate_id, db.func.count(Vote.id)).group_by(Vote.candidate_id).all()
    vote_map = {cid: count for cid, count in vote_data}
    for candidate in Candidate.query.all():
        candidate.votes = vote_map.get(candidate.candidate_id, 0)
    db.session.commit()

# ✅ FIXED: Email function moved here to avoid circular imports
def send_resolution_email(email, complaint_id, response):
    """Send resolution email notification"""
    try:
        msg = Message(
            subject=f"Complaint #{complaint_id} Resolved",
            sender=current_app.config['MAIL_USERNAME'],
            recipients=[email]
        )
        msg.body = f"""Dear Voter,

Your complaint (ID: {complaint_id}) has been resolved.

Admin Response:
{response}

Thank you for using Votonomy.

Regards,
Votonomy Team
"""
        current_app.mail.send(msg)
    except Exception as e:
        print(f"Error sending resolution email: {str(e)}")
        raise e

# ✅ FIXED: Enhanced sentiment analytics update function
def update_sentiment_analytics():
    """Update aggregated sentiment analytics for admin dashboard"""
    try:
        # Get all surveys
        all_surveys = PreSurveyNLP.query.all()
        
        if not all_surveys:
            print("No surveys found for analytics update")
            return
        
        total_responses = len(all_surveys)
        print(f"Processing {total_responses} survey responses for analytics...")
        
        # ✅ Calculate overall sentiment distribution
        positive_count = sum(1 for s in all_surveys if s.overall_sentiment_label == 'Positive')
        negative_count = sum(1 for s in all_surveys if s.overall_sentiment_label == 'Negative')
        neutral_count = total_responses - positive_count - negative_count
        
        positive_percentage = (positive_count / total_responses) * 100
        negative_percentage = (negative_count / total_responses) * 100
        neutral_percentage = (neutral_count / total_responses) * 100
        
        print(f"Sentiment distribution: {positive_percentage:.1f}% positive, {negative_percentage:.1f}% negative, {neutral_percentage:.1f}% neutral")
        
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
        print(f"✅ Sentiment analytics updated successfully: {total_responses} responses processed")
        
    except Exception as e:
        print(f"Error updating sentiment analytics: {str(e)}")
        db.session.rollback()
        import traceback
        traceback.print_exc()

# ------------------------------
# Admin Authentication Routes
# ------------------------------
@admin_bp.route('/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        admin = Admin.query.filter_by(email=email).first()
        if not admin:
            flash("Invalid email.", "danger")
            return redirect(url_for("admin_bp.admin_login"))
        if not check_password_hash(admin.password_hash, password):
            flash("Invalid password.", "danger")
            return redirect(url_for("admin_bp.admin_login"))
        session["admin_logged_in"] = True
        flash("Login successful!", "success")
        return redirect(url_for("admin_bp.admin_welcome"))
    return render_template("login.html")

@admin_bp.route('/logout')
def admin_logout():
    session.pop("admin_logged_in", None)
    flash("Logged out successfully", "info")
    return redirect(url_for("admin_bp.admin_login"))

# ------------------------------
# Forgot Password Routes
# ------------------------------
@admin_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        admin = Admin.query.filter_by(email=email).first()
        if not admin:
            flash("Admin not found.", "danger")
            return redirect(url_for('admin_bp.forgot_password'))

        # Generate token
        s = get_serializer()
        token = s.dumps(email, salt="reset-password")

        # Reset link
        reset_url = url_for('admin_bp.reset_password', token=token, _external=True)

        # Email setup
        msg = Message("Votonomy Password Reset",
                      sender=current_app.config['MAIL_USERNAME'],
                      recipients=[email])
        msg.body = f"Click this link to reset your password:\n\n{reset_url}\n\nThis link expires in 10 minutes."
        current_app.mail.send(msg)

        flash("✅ Reset link sent to your email.", "info")
        return redirect(url_for('admin_bp.admin_login'))

    # This just shows the email input form
    return render_template("reset_password.html", token=None)

@admin_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    import re
    s = get_serializer()
    try:
        email = s.loads(token, salt="reset-password", max_age=600)
    except Exception:
        flash("Invalid or expired token.", "danger")
        return redirect(url_for('admin_bp.forgot_password'))

    admin = Admin.query.filter_by(email=email).first()
    if not admin:
        flash("Admin not found.", "danger")
        return redirect(url_for('admin_bp.admin_login'))

    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if new_password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for('admin_bp.reset_password', token=token))

        if len(new_password) < 10 or not re.match(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[\W_]).+$', new_password):
            flash("Password must meet complexity requirements.", "danger")
            return redirect(url_for('admin_bp.reset_password', token=token))

        if check_password_hash(admin.password_hash, new_password):
            flash("You cannot reuse your old password.", "warning")
            return redirect(url_for('admin_bp.reset_password', token=token))

        admin.password_hash = generate_password_hash(new_password)
        db.session.commit()
        flash("✅ Password updated successfully!", "success")
        return redirect(url_for('admin_bp.admin_login'))

    return render_template("reset_password.html", token=token)

# ------------------------------
# Welcome Route (Short Screen)
# ------------------------------
@admin_bp.route('/welcome')
@admin_login_required
def admin_welcome():
    return render_template("welcome.html")

# ------------------------------
# ✅ FIXED: Main Admin Dashboard with Auto-Update
# ------------------------------
@admin_bp.route('/dashboard')
@admin_login_required
def admin_dashboard():
    from models import Complaint, PreSurveyNLP
    update_vote_counts()
    
    # ✅ FORCE ANALYTICS UPDATE on dashboard load
    try:
        update_sentiment_analytics()
        print("✅ Analytics auto-updated on dashboard load")
    except Exception as e:
        print(f"❌ Error auto-updating analytics: {e}")
    
    # ✅ Get sentiment analytics summary
    sentiment_summary = None
    analytics = SentimentAnalytics.query.first()
    if analytics:
        sentiment_summary = {
            'total_responses': analytics.total_responses,
            'positive_percentage': analytics.positive_percentage,
            'negative_percentage': analytics.negative_percentage,
            'average_score': analytics.average_sentiment_score
        }
    
    # Get complaint statistics
    total_complaints = Complaint.query.count()
    pending_complaints = Complaint.query.filter_by(status='Pending').count()
    in_progress_complaints = Complaint.query.filter_by(status='In Progress').count()
    resolved_complaints = Complaint.query.filter_by(status='Resolved').count()
    
    return render_template(
        'dashboard.html',
        num_positions=len(positions_db),
        num_candidates=Candidate.query.count(),
        num_voters=Voter.query.filter_by(approved=True).count(),
        voters_voted=Vote.query.distinct(Vote.voter_id).count(),
        total_complaints=total_complaints,
        pending_complaints=pending_complaints,
        in_progress_complaints=in_progress_complaints,
        resolved_complaints=resolved_complaints,
        sentiment_summary=sentiment_summary
    )

# ------------------------------
# Manage Voters
# ------------------------------
@admin_bp.route('/manage-voters', methods=['GET'])
@admin_login_required
def manage_voters():
    return render_template(
        'manage_voters.html',
        voters=Voter.query.filter_by(approved=True).all(),
        pending_voter_requests=Voter.query.filter_by(approved=False).all()
    )

@admin_bp.route('/add-voter', methods=['GET', 'POST'])
@admin_login_required
def add_voter():
    if request.method == 'POST':
        name = request.form.get("name", "").strip()
        voter_id = request.form.get("voter_id", "").strip()
        if not name or not voter_id:
            flash("Both fields are required!", "danger")
            return redirect(url_for('admin_bp.add_voter'))
        if Voter.query.filter_by(voter_id=voter_id).first():
            flash("Voter ID already exists!", "warning")
            return redirect(url_for('admin_bp.add_voter'))
        db.session.add(Voter(name=name, voter_id=voter_id, approved=True))
        db.session.commit()
        flash("Voter added successfully!", "success")
        return redirect(url_for('admin_bp.manage_voters'))
    return render_template('add_voter.html')

@admin_bp.route('/delete-voter/<voter_id>', methods=['POST'])
@admin_login_required
def delete_voter(voter_id):
    voter = Voter.query.filter_by(voter_id=voter_id).first()
    if voter:
        db.session.delete(voter)
        db.session.commit()
        flash("Voter deleted successfully.", "success")
    else:
        flash("Voter not found.", "warning")
    return redirect(url_for('admin_bp.manage_voters'))

@admin_bp.route('/approve-voter/<voter_id>', methods=['POST'])
@admin_login_required
def approve_voter(voter_id):
    voter = Voter.query.filter_by(voter_id=voter_id, approved=False).first()
    if voter:
        voter.approved = True
        db.session.commit()
        flash(f"Voter {voter.name} has been approved.", "success")
    return redirect(url_for('admin_bp.manage_voters'))

@admin_bp.route('/reject-voter/<voter_id>', methods=['POST'])
@admin_login_required
def reject_voter(voter_id):
    voter = Voter.query.filter_by(voter_id=voter_id, approved=False).first()
    if voter:
        db.session.delete(voter)
        db.session.commit()
        flash(f"Voter {voter.name} has been rejected.", "danger")
    return redirect(url_for('admin_bp.manage_voters'))

# ------------------------------
# Manage Candidates
# ------------------------------
@admin_bp.route('/manage-candidates', methods=['GET'])
@admin_login_required
def manage_candidates():
    update_vote_counts()
    return render_template(
        'manage_candidates.html',
        candidates=Candidate.query.all(),
        pending_candidate_requests=candidate_requests
    )

@admin_bp.route('/add-candidate', methods=['POST'])
@admin_login_required
def add_candidate():
    candidate_name = request.form.get("candidate_name", "").strip()
    candidate_id = request.form.get("candidate_id", "").strip()
    if not candidate_name or not candidate_id:
        flash("Both fields are required!", "danger")
        return redirect(url_for('admin_bp.manage_candidates'))
    if Candidate.query.filter_by(candidate_id=candidate_id).first():
        flash("Candidate ID already exists!", "warning")
        return redirect(url_for('admin_bp.manage_candidates'))
    db.session.add(Candidate(candidate_name=candidate_name, candidate_id=candidate_id))
    db.session.commit()
    flash("Candidate added successfully!", "success")
    return redirect(url_for('admin_bp.manage_candidates'))

@admin_bp.route('/delete-candidate/<candidate_id>', methods=['POST'])
@admin_login_required
def delete_candidate(candidate_id):
    candidate = Candidate.query.filter_by(candidate_id=candidate_id).first()
    if candidate:
        db.session.delete(candidate)
        db.session.commit()
        flash("Candidate deleted successfully.", "success")
    else:
        flash("Candidate not found.", "warning")
    return redirect(url_for('admin_bp.manage_candidates'))

@admin_bp.route('/approve-candidate-request/<candidate_id>', methods=['POST'])
@admin_login_required
def approve_candidate_request(candidate_id):
    req = next((r for r in candidate_requests if r['candidate_id'] == candidate_id), None)
    if req:
        candidate_requests.remove(req)
        db.session.add(Candidate(candidate_name=req['candidate_name'], candidate_id=req['candidate_id']))
        db.session.commit()
        flash(f"Candidate {req['candidate_name']} has been approved.", "success")
    return redirect(url_for('admin_bp.manage_candidates'))

@admin_bp.route('/reject-candidate-request/<candidate_id>', methods=['POST'])
@admin_login_required
def reject_candidate_request(candidate_id):
    req = next((r for r in candidate_requests if r['candidate_id'] == candidate_id), None)
    if req:
        candidate_requests.remove(req)
        flash(f"Candidate {req['candidate_name']} has been rejected.", "danger")
    return redirect(url_for('admin_bp.manage_candidates'))

# ------------------------------
# Complaint Management Routes
# ------------------------------
@admin_bp.route('/manage-complaints', methods=['GET'])
@admin_login_required
def manage_complaints():
    from models import Complaint
    complaints = Complaint.query.order_by(Complaint.created_at.desc()).all()
    return render_template('manage_complaints.html', complaints=complaints)

@admin_bp.route('/update-complaint/<int:complaint_id>', methods=['POST'])
@admin_login_required
def update_complaint(complaint_id):
    from models import Complaint
    
    complaint = Complaint.query.get_or_404(complaint_id)
    new_status = request.form.get('status')
    admin_response = request.form.get('response', '').strip()
    
    if new_status not in ['Pending', 'In Progress', 'Resolved']:
        flash("Invalid status selected.", "danger")
        return redirect(url_for('admin_bp.manage_complaints'))
    
    old_status = complaint.status
    complaint.status = new_status
    
    if admin_response:
        complaint.response = admin_response
    
    db.session.commit()
    
    # Send email notification if complaint is resolved
    if new_status == 'Resolved' and old_status != 'Resolved':
        try:
            send_resolution_email(complaint.email, f"C{complaint.id:04}", admin_response or "Your complaint has been resolved.")
            flash(f"Complaint C{complaint.id:04} marked as resolved and email sent to voter.", "success")
        except Exception as e:
            flash(f"Complaint updated but email failed to send: {str(e)}", "warning")
    else:
        flash(f"Complaint C{complaint.id:04} status updated to {new_status}.", "success")
    
    return redirect(url_for('admin_bp.manage_complaints'))

@admin_bp.route('/delete-complaint/<int:complaint_id>', methods=['POST'])
@admin_login_required
def delete_complaint(complaint_id):
    from models import Complaint
    complaint = Complaint.query.get_or_404(complaint_id)
    
    complaint_ref = f"C{complaint.id:04}"
    db.session.delete(complaint)
    db.session.commit()
    
    flash(f"Complaint {complaint_ref} has been deleted.", "success")
    return redirect(url_for('admin_bp.manage_complaints'))

# ------------------------------
# Content Quality Review Routes
# ------------------------------
@admin_bp.route('/content-quality-review')
@admin_login_required
def content_quality_review():
    """Review survey responses for content quality"""
    
    page = request.args.get('page', 1, type=int)
    per_page = 15
    
    # ✅ Get filter parameters
    quality_filter = request.args.get('quality_filter', '')
    halka_filter = request.args.get('halka_filter', '')
    date_from = request.args.get('date_from', '')
    
    # ✅ Base query
    query = PreSurveyNLP.query
    
    # ✅ Apply filters
    if date_from:
        from datetime import datetime
        try:
            date_obj = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(PreSurveyNLP.created_at >= date_obj)
        except ValueError:
            pass
    
    if halka_filter:
        # Join with Voter table to filter by halka
        query = query.join(Voter, PreSurveyNLP.voter_id == Voter.voter_id).filter(Voter.halka == halka_filter)
    
    # ✅ Get paginated results
    surveys = query.order_by(PreSurveyNLP.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # ✅ Process survey data with quality analysis
    survey_details = []
    total_responses = 0
    high_quality_count = 0
    flagged_count = 0
    poor_quality_count = 0
    
    for survey in surveys.items:
        voter = Voter.query.filter_by(voter_id=survey.voter_id).first()
        
        # ✅ Re-analyze content quality for display
        responses = {
            'economic_response': survey.economic_response,
            'government_response': survey.government_response,
            'security_response': survey.security_response,
            'education_healthcare_response': survey.education_healthcare_response,
            'infrastructure_response': survey.infrastructure_response,
            'future_expectations_response': survey.future_expectations_response
        }
        
        quality_report = validate_survey_content(responses)
        
        # ✅ Apply quality filter
        if quality_filter:
            if quality_filter == 'high' and quality_report['quality_score'] < 80:
                continue
            elif quality_filter == 'medium' and not (50 <= quality_report['quality_score'] < 80):
                continue
            elif quality_filter == 'low' and quality_report['quality_score'] >= 50:
                continue
        
        survey_details.append({
            'survey': survey,
            'voter': voter,
            'quality_report': quality_report
        })
        
        # ✅ Count quality categories
        total_responses += 1
        if quality_report['quality_score'] >= 80:
            high_quality_count += 1
        elif quality_report['quality_score'] >= 50:
            flagged_count += 1
        else:
            poor_quality_count += 1
    
    return render_template("content_quality_review.html", 
                         surveys=survey_details,
                         pagination=surveys,
                         total_responses=total_responses,
                         high_quality_count=high_quality_count,
                         flagged_count=flagged_count,
                         poor_quality_count=poor_quality_count)

@admin_bp.route('/approve-response/<int:survey_id>', methods=['POST'])
@admin_login_required
def approve_response(survey_id):
    """Approve a flagged response as high quality"""
    
    try:
        survey = PreSurveyNLP.query.get_or_404(survey_id)
        
        # ✅ Mark as approved in sentiment_breakdown (using existing JSON field)
        if not survey.sentiment_breakdown:
            survey.sentiment_breakdown = {}
        
        survey.sentiment_breakdown['admin_approved'] = True
        survey.sentiment_breakdown['approval_date'] = datetime.utcnow().isoformat()
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Response approved successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@admin_bp.route('/flag-response/<int:survey_id>', methods=['POST'])
@admin_login_required
def flag_response(survey_id):
    """Flag a response for quality issues"""
    
    try:
        data = request.get_json()
        reason = data.get('reason', 'Quality concerns')
        
        survey = PreSurveyNLP.query.get_or_404(survey_id)
        
        # ✅ Mark as flagged in sentiment_breakdown
        if not survey.sentiment_breakdown:
            survey.sentiment_breakdown = {}
        
        survey.sentiment_breakdown['admin_flagged'] = True
        survey.sentiment_breakdown['flag_reason'] = reason
        survey.sentiment_breakdown['flag_date'] = datetime.utcnow().isoformat()
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Response flagged successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@admin_bp.route('/content-quality-stats')
@admin_login_required
def content_quality_stats():
    """Get content quality statistics"""
    
    try:
        all_surveys = PreSurveyNLP.query.all()
        
        if not all_surveys:
            return jsonify({
                'total_responses': 0,
                'high_quality': 0,
                'medium_quality': 0,
                'low_quality': 0,
                'flagged_by_admin': 0,
                'approved_by_admin': 0
            })
        
        stats = {
            'total_responses': len(all_surveys),
            'high_quality': 0,
            'medium_quality': 0,
            'low_quality': 0,
            'flagged_by_admin': 0,
            'approved_by_admin': 0
        }
        
        for survey in all_surveys:
            # ✅ Check admin flags
            if survey.sentiment_breakdown:
                if survey.sentiment_breakdown.get('admin_flagged'):
                    stats['flagged_by_admin'] += 1
                if survey.sentiment_breakdown.get('admin_approved'):
                    stats['approved_by_admin'] += 1
            
            # ✅ Analyze quality
            responses = {
                'economic_response': survey.economic_response,
                'government_response': survey.government_response,
                'security_response': survey.security_response,
                'education_healthcare_response': survey.education_healthcare_response,
                'infrastructure_response': survey.infrastructure_response,
                'future_expectations_response': survey.future_expectations_response
            }
            
            quality_report = validate_survey_content(responses)
            score = quality_report['quality_score']
            
            if score >= 80:
                stats['high_quality'] += 1
            elif score >= 50:
                stats['medium_quality'] += 1
            else:
                stats['low_quality'] += 1
        
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({'error': str(e)})

# ------------------------------
# ✅ ENHANCED: Advanced NLP Sentiment Analysis Routes with Auto-Update
# ------------------------------
@admin_bp.route('/sentiment/nlp-analysis')
@admin_login_required
def nlp_sentiment_analysis():
    """Advanced NLP sentiment analysis dashboard with auto-update"""
    
    # ✅ FORCE ANALYTICS UPDATE every time this page is loaded
    try:
        update_sentiment_analytics()
        print("✅ Sentiment analytics auto-updated on NLP dashboard load")
    except Exception as e:
        print(f"❌ Error auto-updating sentiment analytics: {e}")
    
    # ✅ Get or create analytics record
    analytics = SentimentAnalytics.query.first()
    
    return render_template("nlp_sentiment_dashboard.html", analytics=analytics)

@admin_bp.route('/sentiment/individual-responses')
@admin_login_required  
def individual_responses():
    """View individual voter responses with detailed analysis"""
    
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # ✅ Get paginated survey responses
    surveys = PreSurveyNLP.query.order_by(PreSurveyNLP.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # ✅ Get voter details for each survey
    survey_details = []
    for survey in surveys.items:
        voter = Voter.query.filter_by(voter_id=survey.voter_id).first()
        survey_details.append({
            'survey': survey,
            'voter': voter
        })
    
    return render_template("individual_responses.html", 
                         survey_details=survey_details, 
                         pagination=surveys)

@admin_bp.route('/sentiment/export-data')
@admin_login_required
def export_sentiment_data():
    """Export sentiment analysis data to Excel"""
    
    try:
        # ✅ Get all survey data
        surveys = PreSurveyNLP.query.all()
        
        if not surveys:
            flash("No sentiment data available to export.", "warning")
            return redirect(url_for('admin_bp.nlp_sentiment_analysis'))
        
        # ✅ Prepare data for export
        export_data = []
        for survey in surveys:
            voter = Voter.query.filter_by(voter_id=survey.voter_id).first()
            
            row = {
                'Voter ID': survey.voter_id,
                'Voter Name': voter.name if voter else 'Unknown',
                'Halka': voter.halka if voter else 'Unknown',
                'Overall Sentiment': survey.overall_sentiment_label,
                'Sentiment Score': survey.overall_sentiment_score,
                'Submission Date': survey.created_at.strftime('%Y-%m-%d %H:%M'),
                'Economic Response': survey.economic_response,
                'Government Response': survey.government_response,
                'Security Response': survey.security_response,
                'Education Healthcare Response': survey.education_healthcare_response,
                'Infrastructure Response': survey.infrastructure_response,
                'Future Expectations Response': survey.future_expectations_response
            }
            
            # ✅ Add dominant emotion if available
            if survey.emotion_analysis and 'dominant_emotion' in survey.emotion_analysis:
                row['Dominant Emotion'] = survey.emotion_analysis['dominant_emotion']
            
            # ✅ Add top keywords if available
            if survey.keywords_extracted:
                top_keywords = [kw['word'] for kw in survey.keywords_extracted[:5]]
                row['Top Keywords'] = ', '.join(top_keywords)
            
            export_data.append(row)
        
        # ✅ Create Excel file
        df = pd.DataFrame(export_data)
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Sentiment Analysis')
            
            # ✅ Add summary sheet
            analytics = SentimentAnalytics.query.first()
            if analytics:
                summary_data = {
                    'Metric': [
                        'Total Responses',
                        'Positive Percentage',
                        'Negative Percentage', 
                        'Neutral Percentage',
                        'Average Sentiment Score'
                    ],
                    'Value': [
                        analytics.total_responses,
                        f"{analytics.positive_percentage:.1f}%",
                        f"{analytics.negative_percentage:.1f}%",
                        f"{analytics.neutral_percentage:.1f}%",
                        f"{analytics.average_sentiment_score:.3f}"
                    ]
                }
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, index=False, sheet_name='Summary')
        
        output.seek(0)
        
        return send_file(
            output,
            download_name=f"sentiment_analysis_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            as_attachment=True,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    except Exception as e:
        flash(f"Error exporting data: {str(e)}", "danger")
        return redirect(url_for('admin_bp.nlp_sentiment_analysis'))

@admin_bp.route('/sentiment/refresh-analytics', methods=['POST'])
@admin_login_required
def refresh_analytics():
    """Manually refresh sentiment analytics"""
    
    try:
        update_sentiment_analytics()
        flash("✅ Sentiment analytics refreshed successfully!", "success")
    except Exception as e:
        flash(f"❌ Error refreshing analytics: {str(e)}", "danger")
    
    return redirect(url_for('admin_bp.nlp_sentiment_analysis'))

@admin_bp.route('/sentiment/topic-analysis/<topic>')
@admin_login_required
def topic_detailed_analysis(topic):
    """Detailed analysis for a specific topic"""
    
    # ✅ Valid topics
    valid_topics = [
        'Economy', 'Government Performance', 'Security & Law', 
        'Education & Healthcare', 'Infrastructure', 'Future Expectations'
    ]
    
    if topic not in valid_topics:
        flash("Invalid topic selected.", "danger")
        return redirect(url_for('admin_bp.nlp_sentiment_analysis'))
    
    # ✅ Get all surveys with data for this topic
    surveys = PreSurveyNLP.query.all()
    topic_responses = []
    
    for survey in surveys:
        if survey.sentiment_breakdown and topic in survey.sentiment_breakdown:
            voter = Voter.query.filter_by(voter_id=survey.voter_id).first()
            topic_data = survey.sentiment_breakdown[topic]
            
            # ✅ Get the original response text
            response_field_map = {
                'Economy': survey.economic_response,
                'Government Performance': survey.government_response,
                'Security & Law': survey.security_response,
                'Education & Healthcare': survey.education_healthcare_response,
                'Infrastructure': survey.infrastructure_response,
                'Future Expectations': survey.future_expectations_response
            }
            
            topic_responses.append({
                'voter': voter,
                'survey': survey,
                'topic_data': topic_data,
                'response_text': response_field_map.get(topic, ''),
                'created_at': survey.created_at
            })
    
    # ✅ Sort by sentiment score (most positive first)
    topic_responses.sort(key=lambda x: x['topic_data']['sentiment']['compound'], reverse=True)
    
    return render_template("topic_analysis.html", 
                         topic=topic, 
                         responses=topic_responses,
                         total_responses=len(topic_responses))

# ------------------------------
# Download Voting Results
# ------------------------------
@admin_bp.route('/download-results', methods=['GET'])
@admin_login_required
def download_results():
    if Vote.query.count() == 0:
        flash("No voting data available to download.", "warning")
        return redirect(url_for('admin_bp.admin_dashboard'))
    votes_query = Vote.query.all()
    data = [{'voter_id': v.voter_id, 'candidate': v.candidate_id} for v in votes_query]
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Votes')
    output.seek(0)
    return send_file(
        output,
        download_name="vote_results.xlsx",
        as_attachment=True,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )