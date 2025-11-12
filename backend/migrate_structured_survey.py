"""
Migration Script: Recreate PreSurvey table for structured survey responses
This will DROP the old PreSurvey table and create the new structure
Run this script to fix the OperationalError
"""

from app import app, db
from models import PreSurvey
from sqlalchemy import inspect

with app.app_context():
    try:
        # Check if PreSurvey table exists
        inspector = inspect(db.engine)
        if 'pre_survey' in inspector.get_table_names():
            print("⚠️  Old PreSurvey table found. Dropping it...")
            # Drop the old table
            db.session.execute(db.text('DROP TABLE IF EXISTS pre_survey'))
            db.session.commit()
            print("✅ Old PreSurvey table dropped.")
        
        # Create the new PreSurvey table with updated structure
        db.create_all()
        print("✅ New PreSurvey table created successfully!")
        print("✅ Database migration complete.")
        print("\n📋 New table structure:")
        print("   - 12 integer fields for structured responses (1=Positive, 0=Neutral, -1=Negative)")
        print("   - Automatic overall_sentiment calculation")
        print("\nℹ️  Note: Old PreSurveyNLP data is preserved for backwards compatibility.")
        print("ℹ️  New surveys will use the structured PreSurvey model.")
        print("\n🚀 You can now run: python app.py")
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        import traceback
        traceback.print_exc()
