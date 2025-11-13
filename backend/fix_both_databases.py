"""
Fix the complaint table in both database locations
"""
import sqlite3
import os

def fix_database(db_path):
    print(f"\n{'='*60}")
    print(f"🔧 Fixing database: {db_path}")
    print(f"{'='*60}")
    
    if not os.path.exists(db_path):
        print(f"⚠️  Database doesn't exist at {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if complaint table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='complaint'")
        table_exists = cursor.fetchone()
        
        if not table_exists:
            print("⚠️  Complaint table doesn't exist in this database")
            conn.close()
            return
        
        # Check current structure
        cursor.execute("PRAGMA table_info(complaint)")
        columns = cursor.fetchall()
        print("\n📋 Current structure:")
        for col in columns:
            nullable = "NULL" if col[3] == 0 else "NOT NULL"
            print(f"   {col[1]} - {nullable}")
        
        # Backup existing data
        print("\n💾 Backing up complaints...")
        cursor.execute("SELECT id, email, complaint_text, status, response, created_at FROM complaint")
        complaints = cursor.fetchall()
        print(f"   Found {len(complaints)} complaints")
        
        # Recreate table
        print("\n🔨 Recreating table with nullable email...")
        cursor.execute("DROP TABLE IF EXISTS complaint_backup")
        cursor.execute("CREATE TABLE complaint_backup AS SELECT * FROM complaint")
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
        
        # Restore data
        if complaints:
            print(f"📥 Restoring {len(complaints)} complaints...")
            for complaint in complaints:
                cursor.execute("""
                    INSERT INTO complaint (id, email, complaint_text, status, response, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, complaint)
        
        conn.commit()
        
        # Verify
        cursor.execute("PRAGMA table_info(complaint)")
        new_columns = cursor.fetchall()
        print("\n✅ New structure:")
        for col in new_columns:
            nullable = "NULL" if col[3] == 0 else "NOT NULL"
            print(f"   {col[1]} - {nullable}")
        
        conn.close()
        print("\n🎉 Successfully fixed this database!")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    # Fix both possible database locations
    databases = [
        'votonomy.db',
        'instance/votonomy.db'
    ]
    
    print("🚀 Fixing all database files...")
    
    for db_path in databases:
        fix_database(db_path)
    
    print("\n" + "="*60)
    print("✅ ALL DONE! Restart Flask and test the complaint portal.")
    print("="*60)
