# admin.py - FIXED VERSION

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app, send_file, jsonify
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer
from flask_mail import Message
from models import db, Voter, Candidate, Vote, Admin, PreSurvey, SentimentAnalytics
from data import positions_db, candidate_requests  # candidate_requests remains in-memory
import pandas as pd
import io
from functools import wraps

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
    """Update aggregated sentiment analytics for admin dashboard - STRUCTURED SURVEY"""
    try:
        from models import PreSurvey
        
        # Get all surveys
        all_surveys = PreSurvey.query.all()
        
        if not all_surveys:
            print("No surveys found for analytics update")
            return
        
        total_responses = len(all_surveys)
        print(f"Processing {total_responses} survey responses for analytics...")
        
        # ✅ Calculate overall sentiment distribution
        positive_count = sum(1 for s in all_surveys if s.calculate_overall_sentiment() == 'Positive')
        negative_count = sum(1 for s in all_surveys if s.calculate_overall_sentiment() == 'Negative')
        neutral_count = total_responses - positive_count - negative_count
        
        positive_percentage = (positive_count / total_responses) * 100
        negative_percentage = (negative_count / total_responses) * 100
        neutral_percentage = (neutral_count / total_responses) * 100
        
        print(f"Sentiment distribution: {positive_percentage:.1f}% positive, {negative_percentage:.1f}% negative, {neutral_percentage:.1f}% neutral")
        
        # ✅ Calculate average sentiment score (average of all 12 fields)
        all_field_values = []
        for survey in all_surveys:
            all_field_values.extend([
                survey.economy_satisfaction, survey.economy_inflation_impact,
                survey.government_performance, survey.government_corruption,
                survey.security_safety, survey.security_law_order,
                survey.education_quality, survey.healthcare_access,
                survey.infrastructure_roads, survey.infrastructure_utilities,
                survey.future_optimism, survey.future_confidence
            ])
        avg_sentiment = sum(all_field_values) / len(all_field_values)
        
        # ✅ Aggregate topic sentiments
        topic_sentiments = {}
        topic_mapping = {
            'Economy': ['economy_satisfaction', 'economy_inflation_impact'],
            'Government Performance': ['government_performance', 'government_corruption'],
            'Security & Law': ['security_safety', 'security_law_order'],
            'Education & Healthcare': ['education_quality', 'healthcare_access'],
            'Infrastructure': ['infrastructure_roads', 'infrastructure_utilities'],
            'Future Expectations': ['future_optimism', 'future_confidence']
        }
        
        for topic, fields in topic_mapping.items():
            topic_scores = []
            for survey in all_surveys:
                for field in fields:
                    topic_scores.append(getattr(survey, field))
            
            avg_score = sum(topic_scores) / len(topic_scores)
            positive = sum(1 for score in topic_scores if score == 1)
            negative = sum(1 for score in topic_scores if score == -1)
            neutral = sum(1 for score in topic_scores if score == 0)
            
            topic_sentiments[topic] = {
                'average_score': round(avg_score, 3),
                'positive_count': positive,
                'negative_count': negative,
                'neutral_count': neutral,
                'total_responses': len(topic_scores)
            }
        
        # ✅ Halka-wise sentiment
        halka_sentiments = {}
        for survey in all_surveys:
            voter = Voter.query.filter_by(voter_id=survey.voter_id).first()
            if voter and voter.halka:
                if voter.halka not in halka_sentiments:
                    halka_sentiments[voter.halka] = {'scores': [], 'count': 0}
                
                # Calculate average score for this survey
                survey_avg = sum([
                    survey.economy_satisfaction, survey.economy_inflation_impact,
                    survey.government_performance, survey.government_corruption,
                    survey.security_safety, survey.security_law_order,
                    survey.education_quality, survey.healthcare_access,
                    survey.infrastructure_roads, survey.infrastructure_utilities,
                    survey.future_optimism, survey.future_confidence
                ]) / 12
                
                halka_sentiments[voter.halka]['scores'].append(survey_avg)
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
        analytics.trending_keywords = {}  # Not applicable for structured survey
        analytics.emotion_distribution = {}  # Not applicable for structured survey
        analytics.halka_sentiments = halka_sentiments
        analytics.last_updated = datetime.utcnow()
        
        db.session.commit()
        print(f"✅ Sentiment analytics updated successfully: {total_responses} responses processed")
        
    except Exception as e:
        print(f"Error updating sentiment analytics: {str(e)}")
        import traceback
        traceback.print_exc()
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
    from models import Complaint, PreSurvey  # ✅ Updated to use PreSurvey
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
            'neutral_percentage': analytics.neutral_percentage,
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
# ✅ SENTIMENT ANALYSIS ROUTES - STRUCTURED SURVEY
# ------------------------------
@admin_bp.route('/sentiment/analysis')
@admin_login_required
def sentiment_analysis():
    """Advanced Sentiment Analysis Dashboard - USA-Style Voting System"""
    from models import PreSurvey  # ✅ Updated to use structured survey
    
    # ✅ FORCE ANALYTICS UPDATE every time this page is loaded
    try:
        update_sentiment_analytics()
        print("✅ Sentiment analytics auto-updated on dashboard load")
    except Exception as e:
        print(f"❌ Error auto-updating sentiment analytics: {e}")
    
    # ✅ Get or create analytics record
    analytics = SentimentAnalytics.query.first()
    
    # ✅ Get individual survey responses for detailed view
    total_surveys = PreSurvey.query.count()
    recent_surveys = PreSurvey.query.order_by(PreSurvey.created_at.desc()).limit(10).all()
    
    # ✅ Calculate participation rate
    total_voters = Voter.query.filter_by(approved=True).count()
    participation_rate = (total_surveys / total_voters * 100) if total_voters > 0 else 0
    
    return render_template("sentiment_dashboard.html", 
                          analytics=analytics,
                          total_surveys=total_surveys,
                          participation_rate=round(participation_rate, 1),
                          recent_surveys=recent_surveys)

# REMOVED: individual_responses route - violates election integrity
# Individual voter responses should remain confidential

@admin_bp.route('/sentiment/refresh-analytics', methods=['POST'])
@admin_login_required
def refresh_analytics():
    """Manually refresh sentiment analytics"""
    
    try:
        update_sentiment_analytics()
        flash("✅ Sentiment analytics refreshed successfully!", "success")
    except Exception as e:
        flash(f"❌ Error refreshing analytics: {str(e)}", "danger")
    
    return redirect(url_for('admin_bp.sentiment_analysis'))

# ------------------------------
# Blockchain Dashboard & Verification
# ------------------------------
@admin_bp.route('/blockchain/dashboard')
@admin_login_required
def blockchain_dashboard():
    """Blockchain integration statistics and monitoring"""
    from blockchain.vote_verifier import get_vote_verifier
    
    try:
        verifier = get_vote_verifier()
        stats = verifier.get_blockchain_stats()
        
        # Get recent blockchain votes
        recent_votes = Vote.query.filter_by(
            is_verified_on_chain=True
        ).order_by(Vote.blockchain_timestamp.desc()).limit(10).all()
        
        return render_template('admin/blockchain_dashboard.html',
                             stats=stats,
                             recent_votes=recent_votes)
    except Exception as e:
        flash(f"❌ Blockchain dashboard error: {str(e)}", "danger")
        return redirect(url_for('admin_bp.admin_dashboard'))

@admin_bp.route('/blockchain/verify/<receipt_code>')
@admin_login_required
def verify_vote_receipt(receipt_code):
    """Verify a vote using receipt code"""
    from blockchain.vote_verifier import get_vote_verifier
    
    try:
        verifier = get_vote_verifier()
        result = verifier.verify_vote_by_receipt(receipt_code)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'verified': False,
            'error': str(e)
        })

@admin_bp.route('/blockchain/integrity-check')
@admin_login_required
def blockchain_integrity_check():
    """Check vote integrity against blockchain"""
    from blockchain.vote_verifier import get_vote_verifier
    
    try:
        verifier = get_vote_verifier()
        results = verifier.check_vote_integrity()
        
        return jsonify(results)
    except Exception as e:
        return jsonify({
            'error': str(e),
            'integrity_status': 'ERROR'
        })

@admin_bp.route('/blockchain/audit-report')
@admin_login_required
def blockchain_audit_report():
    """Generate blockchain audit report"""
    from blockchain.vote_verifier import get_vote_verifier
    
    try:
        verifier = get_vote_verifier()
        report = verifier.generate_audit_report()
        
        return render_template('admin/blockchain_audit.html', report=report)
    except Exception as e:
        flash(f"❌ Audit report error: {str(e)}", "danger")
        return redirect(url_for('admin_bp.blockchain_dashboard'))

# ------------------------------
# AI Fraud Detection Dashboard
# ------------------------------
@admin_bp.route('/fraud/dashboard')
@admin_login_required
def fraud_dashboard():
    """AI-driven fraud detection monitoring dashboard"""
    from models import BehaviorLog, FraudAlert, IPCluster
    from fraud_detection.fraud_detector import get_fraud_detector
    
    # Get statistics
    total_logs = BehaviorLog.query.count()
    total_alerts = FraudAlert.query.count()
    open_alerts = FraudAlert.query.filter_by(status='open').count()
    critical_alerts = FraudAlert.query.filter_by(severity='critical', status='open').count()
    high_alerts = FraudAlert.query.filter_by(severity='high', status='open').count()
    
    # Get recent alerts
    recent_alerts = FraudAlert.query.order_by(FraudAlert.created_at.desc()).limit(20).all()
    
    # Get high-risk voters
    high_risk_logs = BehaviorLog.query.filter(
        BehaviorLog.behavioral_risk_score >= 70
    ).order_by(BehaviorLog.behavioral_risk_score.desc()).limit(10).all()
    
    # Get suspicious IP clusters
    suspicious_clusters = IPCluster.query.filter(
        IPCluster.risk_assessment.in_(['suspicious', 'fraud'])
    ).order_by(IPCluster.coordination_score.desc()).limit(10).all()
    
    # Get fraud detector stats
    fraud_detector = get_fraud_detector()
    fd_stats = fraud_detector.get_statistics()
    
    stats = {
        'total_behavior_logs': total_logs,
        'total_alerts': total_alerts,
        'open_alerts': open_alerts,
        'critical_alerts': critical_alerts,
        'high_alerts': high_alerts,
        'model_trained': fd_stats['model_trained']
    }
    
    return render_template('admin/fraud_dashboard.html',
                         stats=stats,
                         alerts=recent_alerts,  # Template expects 'alerts', not 'recent_alerts'
                         high_risk_logs=high_risk_logs,
                         suspicious_clusters=suspicious_clusters)

@admin_bp.route('/fraud/alert/<int:alert_id>')
@admin_login_required
def fraud_alert_detail(alert_id):
    """Detailed view of fraud alert"""
    from models import FraudAlert, BehaviorLog, Vote
    
    alert = FraudAlert.query.get_or_404(alert_id)
    
    # Get related behavior logs
    behavior_logs = None
    related_votes = None
    
    if alert.voter_id:
        behavior_logs = BehaviorLog.query.filter_by(voter_id=alert.voter_id).all()
        related_votes = Vote.query.filter_by(voter_id=alert.voter_id).all()
    
    return render_template('admin/fraud_alert_detail.html',
                         alert=alert,
                         behavior_logs=behavior_logs,
                         related_votes=related_votes)

@admin_bp.route('/fraud/alert/<int:alert_id>/resolve', methods=['POST'])
@admin_login_required
def resolve_fraud_alert(alert_id):
    """Resolve fraud alert"""
    from models import FraudAlert
    
    alert = FraudAlert.query.get_or_404(alert_id)
    
    action = request.form.get('action')  # 'confirm', 'false_positive', 'investigate'
    notes = request.form.get('notes', '')
    
    if action == 'confirm':
        alert.status = 'confirmed'
        alert.action_taken = 'blocked'
        flash(f"Alert #{alert_id} confirmed as fraud. Voter flagged.", "danger")
    elif action == 'false_positive':
        alert.status = 'false_positive'
        alert.action_taken = 'verified'
        flash(f"Alert #{alert_id} marked as false positive.", "success")
    elif action == 'investigate':
        alert.status = 'investigating'
        flash(f"Alert #{alert_id} under investigation.", "info")
    
    alert.admin_notes = notes
    alert.resolved_at = datetime.utcnow()
    alert.resolved_by = session.get('admin_id')
    
    db.session.commit()
    
    return redirect(url_for('admin_bp.fraud_dashboard'))

@admin_bp.route('/fraud/retrain-model', methods=['POST'])
@admin_login_required
def retrain_fraud_model():
    """Retrain fraud detection model with latest data"""
    from fraud_detection.fraud_detector import get_fraud_detector
    
    try:
        fraud_detector = get_fraud_detector()
        success = fraud_detector.retrain_model()
        
        if success:
            flash("✅ Fraud detection model retrained successfully!", "success")
        else:
            flash("⚠️ Insufficient data for retraining. Need at least 50 samples.", "warning")
    except Exception as e:
        flash(f"❌ Model retraining failed: {str(e)}", "danger")
    
    return redirect(url_for('admin_bp.fraud_dashboard'))

@admin_bp.route('/fraud/analyze-patterns', methods=['POST'])
@admin_login_required
def analyze_fraud_patterns():
    """Run coordinated attack pattern analysis"""
    from fraud_detection.pattern_detector import get_pattern_detector
    from models import Vote, BehaviorLog
    
    try:
        pattern_detector = get_pattern_detector()
        
        # Check if we have enough data
        total_votes = Vote.query.count()
        total_logs = BehaviorLog.query.count()
        
        if total_votes < 50:
            flash(f"ℹ️ Pattern analysis requires at least 50 votes. Current: {total_votes} votes. Individual behavior alerts are still being monitored.", "info")
            return redirect(url_for('admin_bp.fraud_dashboard'))
        
        # Analyze recent votes
        suspicious_clusters = pattern_detector.analyze_recent_votes(window_minutes=60)
        
        # Update IP clusters
        pattern_detector.update_ip_clusters()
        
        if suspicious_clusters:
            flash(f"⚠️ {len(suspicious_clusters)} suspicious voting patterns detected! Check alerts for details.", "warning")
            for cluster in suspicious_clusters:
                flash(f"  • {cluster['vote_count']} coordinated votes detected with {len(cluster['analysis']['red_flags'])} red flags", "warning")
        else:
            flash(f"✅ No coordinated attack patterns detected in {total_votes} votes. Individual fraud detection is active.", "success")
    except Exception as e:
        flash(f"❌ Pattern analysis failed: {str(e)}", "danger")
    
    return redirect(url_for('admin_bp.fraud_dashboard'))

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