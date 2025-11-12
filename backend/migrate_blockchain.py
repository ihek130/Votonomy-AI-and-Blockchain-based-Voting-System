"""
Migration: Add Blockchain Fields to Vote Model
Adds blockchain integration columns to existing votes table
"""

from app import app, db
from models import Vote

def migrate_vote_blockchain_fields():
    """Add blockchain fields to Vote table"""
    print("🔄 Migrating Vote model - Adding blockchain fields...")
    
    with app.app_context():
        # Check if migration needed
        inspector = db.inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('vote')]
        
        if 'blockchain_tx_signature' in columns:
            print("✅ Blockchain fields already exist. No migration needed.")
            return
        
        # Add new columns using raw SQL
        try:
            with db.engine.connect() as conn:
                # Add blockchain fields
                conn.execute(db.text("""
                    ALTER TABLE vote ADD COLUMN blockchain_tx_signature VARCHAR(200);
                """))
                conn.execute(db.text("""
                    ALTER TABLE vote ADD COLUMN blockchain_slot BIGINT;
                """))
                conn.execute(db.text("""
                    ALTER TABLE vote ADD COLUMN blockchain_timestamp DATETIME;
                """))
                conn.execute(db.text("""
                    ALTER TABLE vote ADD COLUMN voter_id_hash VARCHAR(64);
                """))
                conn.execute(db.text("""
                    ALTER TABLE vote ADD COLUMN encrypted_vote_data TEXT;
                """))
                conn.execute(db.text("""
                    ALTER TABLE vote ADD COLUMN verification_receipt VARCHAR(500);
                """))
                conn.execute(db.text("""
                    ALTER TABLE vote ADD COLUMN is_verified_on_chain BOOLEAN DEFAULT 0;
                """))
                conn.execute(db.text("""
                    ALTER TABLE vote ADD COLUMN created_at DATETIME;
                """))
                conn.commit()
            
            print("✅ Successfully added blockchain fields to Vote table")
            print("   - blockchain_tx_signature (VARCHAR 200)")
            print("   - blockchain_slot (BIGINT)")
            print("   - blockchain_timestamp (DATETIME)")
            print("   - voter_id_hash (VARCHAR 64)")
            print("   - encrypted_vote_data (TEXT)")
            print("   - verification_receipt (VARCHAR 500)")
            print("   - is_verified_on_chain (BOOLEAN)")
            print("   - created_at (DATETIME)")
            
        except Exception as e:
            print(f"❌ Migration failed: {str(e)}")
            print("   Note: If columns already exist, this is expected.")

if __name__ == '__main__':
    migrate_vote_blockchain_fields()
    print("\n🎯 Migration complete! Vote model ready for blockchain integration.")
