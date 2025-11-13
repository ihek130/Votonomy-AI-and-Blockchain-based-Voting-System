"""
Fix script to make email field nullable in Complaint table
For SQLite, we need to recreate the table
"""

from app import app, db
from models import Complaint
import sqlite3

def fix_complaint_table():
    with app.app_context():
        try:
            print("🔧 Fixing Complaint table...")
            
            # Get the database path
            db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
            print(f"📂 Database: {db_path}")
            
            # Connect directly to SQLite
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check if table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='complaint'")
            table_exists = cursor.fetchone()
            
            if table_exists:
                # Check current structure
                cursor.execute("PRAGMA table_info(complaint)")
                columns = cursor.fetchall()
                print("\n📋 Current Complaint table structure:")
                for col in columns:
                    print(f"   {col}")
                
                # Backup existing data
                print("\n💾 Backing up existing complaints...")
                cursor.execute("SELECT id, email, complaint_text, status, response, created_at FROM complaint")
                complaints = cursor.fetchall()
                print(f"   Found {len(complaints)} complaints to backup")
            else:
                print("\n📋 Complaint table doesn't exist yet - will create it fresh!")
                complaints = []
            
            # Drop and recreate table with nullable email
            print("\n🔨 Creating/recreating table with nullable email...")
            if table_exists:
                cursor.execute("DROP TABLE IF EXISTS complaint_backup")
                cursor.execute("""
                    CREATE TABLE complaint_backup AS 
                    SELECT * FROM complaint
                """)
                cursor.execute("DROP TABLE complaint")
            
            cursor.execute("""
                CREATE TABLE complaint (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email VARCHAR(100),
                    complaint_text TEXT NOT NULL,
                    status VARCHAR(20) DEFAULT 'Pending',
                    response TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Restore data if there were any
            if complaints:
                print("📥 Restoring complaints...")
                for complaint in complaints:
                    cursor.execute("""
                        INSERT INTO complaint (id, email, complaint_text, status, response, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, complaint)
            else:
                print("📥 No existing complaints to restore (fresh table)")
            
            conn.commit()
            
            # Verify
            cursor.execute("PRAGMA table_info(complaint)")
            new_columns = cursor.fetchall()
            print("\n✅ New Complaint table structure:")
            for col in new_columns:
                nullable = "NULL" if col[3] == 0 else "NOT NULL"
                print(f"   {col[1]} - {nullable}")
            
            conn.close()
            
            print("\n🎉 Success! Email field is now nullable!")
            print("💡 You can now submit anonymous complaints without email.")
            
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    fix_complaint_table()
