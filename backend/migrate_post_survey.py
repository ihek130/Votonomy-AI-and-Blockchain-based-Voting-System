"""
Post-Survey Database Migration Script
Creates post_survey and post_survey_analytics tables
Run this after adding PostSurvey and PostSurveyAnalytics models to models.py
"""

from app import app, db
from models import PostSurvey, PostSurveyAnalytics
from sqlalchemy import text

def migrate_post_survey_tables():
    """Create post_survey and post_survey_analytics tables"""
    
    with app.app_context():
        try:
            # Check if tables already exist
            with db.engine.connect() as conn:
                result = conn.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='post_survey'"
                ))
                table_exists = result.fetchone() is not None
            
            if table_exists:
                print("⚠️  post_survey table already exists")
                response = input("Do you want to drop and recreate it? (yes/no): ")
                if response.lower() == 'yes':
                    with db.engine.connect() as conn:
                        conn.execute(text("DROP TABLE IF EXISTS post_survey"))
                        conn.execute(text("DROP TABLE IF EXISTS post_survey_analytics"))
                        conn.commit()
                    print("✅ Dropped existing tables")
                else:
                    print("❌ Migration cancelled")
                    return
            
            # Create tables using SQLAlchemy
            print("Creating post_survey and post_survey_analytics tables...")
            db.create_all()
            
            print("\n✅ Migration completed successfully!")
            print("📊 Created tables:")
            print("   - post_survey (12 question fields + metadata)")
            print("   - post_survey_analytics (aggregated statistics)")
            
            # Verify table creation
            with db.engine.connect() as conn:
                result = conn.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%post_survey%'"
                ))
                tables = result.fetchall()
                print(f"\n🔍 Verification: Found {len(tables)} table(s)")
                for table in tables:
                    print(f"   ✓ {table[0]}")
            
            # Show table schema
            with db.engine.connect() as conn:
                result = conn.execute(text("PRAGMA table_info(post_survey)"))
                columns = result.fetchall()
                print("\n📋 post_survey table schema:")
                for col in columns:
                    print(f"   {col[1]:30s} {col[2]:15s} {'NOT NULL' if col[3] else ''}")
            
        except Exception as e:
            print(f"❌ Migration failed: {str(e)}")
            db.session.rollback()
            raise

if __name__ == '__main__':
    print("="*60)
    print("POST-SURVEY DATABASE MIGRATION")
    print("="*60)
    print("\nThis script will create the following tables:")
    print("  1. post_survey - Stores individual post-election survey responses")
    print("  2. post_survey_analytics - Stores aggregated analytics data")
    print("\n" + "="*60 + "\n")
    
    migrate_post_survey_tables()
    
    print("\n" + "="*60)
    print("Next steps:")
    print("  1. Test the survey at /survey/post (after voting)")
    print("  2. View analytics at admin panel > Post-Survey Analysis")
    print("  3. Analytics auto-update when dashboard loads")
    print("="*60)
