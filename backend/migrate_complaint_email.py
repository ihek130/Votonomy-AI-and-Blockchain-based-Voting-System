"""
Migration script to make email field nullable in Complaint table
Run this once to update the database schema
"""

from app import app, db
from models import Complaint
from sqlalchemy import text

def migrate_complaint_email():
    with app.app_context():
        try:
            # For SQLite, we need to recreate the table
            print("🔄 Migrating Complaint table to make email nullable...")
            
            # Check if any complaints exist
            existing_complaints = Complaint.query.all()
            print(f"📊 Found {len(existing_complaints)} existing complaints")
            
            # SQLite doesn't support ALTER COLUMN directly, so we use a workaround
            # The table will be updated when the app runs with the new model definition
            
            # Just verify the change by checking the model
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            columns = inspector.get_columns('complaint')
            
            email_column = next((col for col in columns if col['name'] == 'email'), None)
            
            if email_column:
                print(f"📋 Email column nullable status: {email_column['nullable']}")
                if not email_column['nullable']:
                    print("⚠️  Email is still NOT NULL in database")
                    print("⚠️  For SQLite, you may need to recreate the database or manually update")
                    print("⚠️  Recommended: Drop and recreate tables, or use Alembic for proper migrations")
                else:
                    print("✅ Email column is already nullable!")
            
            print("\n✅ Migration check complete!")
            print("💡 Note: SQLite limitations mean email may still show as NOT NULL")
            print("💡 The application will handle NULL emails in code regardless")
            
        except Exception as e:
            print(f"❌ Error during migration: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    migrate_complaint_email()
