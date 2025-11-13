"""
Database Migration Script
Adds fraud detection tables to existing Votonomy database
"""

from app import app, db
from models import (
    BehaviorLog, FraudAlert, IPCluster, AdminActionLog,
    Voter, Vote, PreSurvey, Admin  # Ensure all models are imported
)

def migrate_database():
    """Create new fraud detection tables"""
    
    with app.app_context():
        print("\n" + "="*70)
        print("🔄 VOTONOMY FRAUD DETECTION - DATABASE MIGRATION")
        print("="*70 + "\n")
        
        print("📋 Creating new tables...")
        print("   - BehaviorLog: User behavior tracking")
        print("   - FraudAlert: Fraud detection alerts")
        print("   - IPCluster: IP/device clustering analysis")
        print("   - AdminActionLog: Admin activity monitoring")
        print()
        
        try:
            # Create all tables (only creates missing ones)
            db.create_all()
            
            print("✅ Database migration completed successfully!")
            print()
            print("📊 New Tables Created:")
            print("   ✅ behavior_log")
            print("   ✅ fraud_alert")
            print("   ✅ ip_cluster")
            print("   ✅ admin_action_log")
            print()
            print("🎯 Fraud detection system is now ready!")
            print("="*70 + "\n")
            
        except Exception as e:
            print(f"❌ Migration failed: {str(e)}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    migrate_database()
