"""
Quick Bot Test Script
Creates a bot-like voter using PKV1100 data and triggers fraud alert
"""

from app import app, db
from models import Voter, PreSurvey, Vote, Candidate, BehaviorLog, FraudAlert
from fraud_detection.fraud_detector import get_fraud_detector
from fraud_detection.behavior_analyzer import get_behavior_analyzer
from datetime import datetime
import random

def create_bot_voter():
    """Create test bot voter with PKV1100 data"""
    
    with app.app_context():
        # Check if voter already exists
        existing = Voter.query.filter_by(voter_id='PKV1100').first()
        if existing:
            print("⚠️  Voter PKV1100 already exists. Deleting old data...")
            # Delete related data
            BehaviorLog.query.filter_by(voter_id='PKV1100').delete()
            FraudAlert.query.filter_by(voter_id='PKV1100').delete()
            Vote.query.filter_by(voter_id='PKV1100').delete()
            PreSurvey.query.filter_by(voter_id='PKV1100').delete()
            db.session.delete(existing)
            db.session.commit()
        
        # Create voter
        print("👤 Creating bot voter: Talha Khan (PKV1100)")
        voter = Voter(
            voter_id='PKV1100',
            name='Talha Khan',
            father_name='Noman Khan',
            id_card='82159-4460945-3',
            city='Islamabad',
            province='Punjab',
            gender='Male',
            age=55,
            address='House No. 5, Sector F-10/4, Islamabad',
            approved=True
        )
        db.session.add(voter)
        db.session.commit()
        print(f"✅ Voter created: {voter.name} ({voter.voter_id})")
        
        # Create bot-like pre-survey (all same answers, fast completion)
        print("\n📋 Creating bot-like survey (all same answers)...")
        survey = PreSurvey(
            voter_id='PKV1100',
            economy_satisfaction=1,
            economy_inflation_impact=1,
            government_performance=1,
            government_corruption=1,
            security_safety=1,
            security_law_order=1,
            education_quality=1,
            healthcare_access=1,
            infrastructure_roads=1,
            infrastructure_utilities=1,
            future_optimism=1,
            future_confidence=1
        )
        survey.calculate_overall_sentiment()
        db.session.add(survey)
        db.session.commit()
        print("✅ Survey created: All answers = 1 (Variance = 0.0)")
        
        # Create vote
        print("\n🗳️  Creating vote...")
        candidate = Candidate.query.first()
        if not candidate:
            print("❌ No candidates found! Please add a candidate first.")
            return
        
        vote = Vote(
            voter_id='PKV1100',
            candidate_id=candidate.candidate_id,
            created_at=datetime.utcnow()
        )
        db.session.add(vote)
        db.session.commit()
        print(f"✅ Vote created for: {candidate.candidate_name}")
        
        # Create bot-like behavior log (very fast times)
        print("\n🤖 Creating bot behavior log...")
        session_id = f"bot_session_{random.randint(1000, 9999)}"
        
        behavior = BehaviorLog(
            voter_id='PKV1100',
            session_id=session_id,
            registration_duration=15,  # Very fast (< 25s)
            form_corrections=0,
            survey_duration=12,  # Very fast (< 30s)
            survey_response_variance=0.0,  # All same answers
            survey_entropy=0.0,  # No entropy (robotic)
            voting_duration=3,  # Very fast (< 10s)
            candidate_selection_speed=2,
            total_session_duration=30,
            ip_address='192.168.1.100',
            device_fingerprint='bot_device_test',
            time_of_day=3  # Suspicious time (3 AM)
        )
        db.session.add(behavior)
        db.session.commit()
        print("✅ Behavior log created:")
        print(f"   - Registration: {behavior.registration_duration}s (Fast!)")
        print(f"   - Survey: {behavior.survey_duration}s (Fast!)")
        print(f"   - Variance: {behavior.survey_response_variance} (All same!)")
        print(f"   - Voting: {behavior.voting_duration}s (Fast!)")
        print(f"   - Time: {behavior.time_of_day}:00 (Suspicious!)")
        
        # Run fraud detection
        print("\n🔍 Running fraud detection...")
        fraud_detector = get_fraud_detector()
        
        # Prepare behavior dict
        behavior_dict = {
            'registration_duration': behavior.registration_duration,
            'form_corrections': behavior.form_corrections,
            'survey_duration': behavior.survey_duration,
            'survey_response_variance': behavior.survey_response_variance,
            'survey_entropy': behavior.survey_entropy,
            'voting_duration': behavior.voting_duration,
            'candidate_selection_speed': behavior.candidate_selection_speed,
            'total_session_duration': behavior.total_session_duration,
            'time_of_day': behavior.time_of_day
        }
        
        assessment = fraud_detector.assess_behavior(behavior_dict)
        
        # Update behavior log
        behavior.isolation_forest_score = assessment.get('isolation_forest_score', 0)
        behavior.behavioral_risk_score = assessment['risk_score']
        db.session.commit()
        
        print("\n" + "="*70)
        print("🚨 FRAUD DETECTION RESULTS")
        print("="*70)
        print(f"Risk Score: {assessment['risk_score']:.1f}/100")
        print(f"Severity: {assessment['severity'].upper()}")
        print(f"Action: {assessment['action_recommended']}")
        print(f"\n🚩 Red Flags Detected ({len(assessment['red_flags'])}):")
        for flag in assessment['red_flags']:
            print(f"   ⚠️  {flag}")
        print("="*70)
        
        # Create alert if high risk
        if assessment['risk_score'] >= 70:
            print("\n🚨 CREATING FRAUD ALERT...")
            alert = FraudAlert(
                voter_id='PKV1100',
                risk_score=assessment['risk_score'],
                severity=assessment['severity'],
                alert_type='behavior_anomaly',
                description=f"Bot-like voting pattern detected: {', '.join(assessment['red_flags'])}",
                red_flags=assessment['red_flags'],
                detected_patterns={
                    'fast_registration': behavior.registration_duration < 25,
                    'fast_survey': behavior.survey_duration < 30,
                    'zero_variance': behavior.survey_response_variance == 0,
                    'fast_voting': behavior.voting_duration < 10,
                    'suspicious_hour': behavior.time_of_day in [0, 1, 2, 3, 4, 5]
                },
                status='open'
            )
            db.session.add(alert)
            db.session.commit()
            print(f"✅ ALERT CREATED! Alert ID: {alert.id}")
            print(f"\n🎯 Check admin dashboard at: http://127.0.0.1:5000/admin/fraud/dashboard")
            print(f"   View this alert at: http://127.0.0.1:5000/admin/fraud/alert/{alert.id}")
        else:
            print(f"\n⚠️  Risk score {assessment['risk_score']:.1f}% is below 70% threshold.")
            print("   No alert created. Behavior logged for monitoring.")
        
        print("\n" + "="*70)
        print("✅ BOT TEST COMPLETE!")
        print("="*70)
        print(f"\nVoter ID: PKV1100")
        print(f"Name: Talha Khan")
        print(f"Risk Score: {assessment['risk_score']:.1f}%")
        print(f"Alert Status: {'CREATED' if assessment['risk_score'] >= 70 else 'NOT CREATED'}")
        print("\n💡 Tip: Refresh the admin fraud dashboard to see the alert!")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("🤖 VOTONOMY BOT VOTER TEST SCRIPT")
    print("="*70)
    print("This script creates a bot-like voter to test fraud detection\n")
    
    create_bot_voter()
