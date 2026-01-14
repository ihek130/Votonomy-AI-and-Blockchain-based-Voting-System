"""
Migration script to add position and halka columns to Candidate table
"""
from app import app, db
from sqlalchemy import text

def migrate():
    with app.app_context():
        try:
            # Try to add position column
            with db.engine.connect() as conn:
                conn.execute(text('ALTER TABLE candidate ADD COLUMN position VARCHAR(50)'))
                conn.commit()
            print("✅ Added 'position' column to candidate table")
        except Exception as e:
            if 'duplicate column name' in str(e).lower():
                print("ℹ️  'position' column already exists")
            else:
                print(f"⚠️  Error adding position column: {e}")
        
        try:
            # Try to add halka column
            with db.engine.connect() as conn:
                conn.execute(text('ALTER TABLE candidate ADD COLUMN halka VARCHAR(20)'))
                conn.commit()
            print("✅ Added 'halka' column to candidate table")
        except Exception as e:
            if 'duplicate column name' in str(e).lower():
                print("ℹ️  'halka' column already exists")
            else:
                print(f"⚠️  Error adding halka column: {e}")
        
        # Now populate the columns from candidate_id using raw SQL to avoid model issues
        try:
            with db.engine.connect() as conn:
                # Get all candidates
                result = conn.execute(text('SELECT id, candidate_id FROM candidate'))
                candidates = result.fetchall()
                
                for candidate in candidates:
                    candidate_id = candidate[1]
                    parts = candidate_id.split('-')
                    if len(parts) >= 3:
                        halka = f"{parts[0]}-{parts[1]}"  # e.g., "NA-52"
                        position = parts[2]  # e.g., "President", "PrimeMinister"
                        
                        conn.execute(text(
                            'UPDATE candidate SET position = :position, halka = :halka WHERE id = :id'
                        ), {'position': position, 'halka': halka, 'id': candidate[0]})
                
                conn.commit()
                print(f"✅ Updated position and halka for {len(candidates)} candidates")
        except Exception as e:
            print(f"⚠️  Error updating data: {e}")
        
        print("\n🎉 Migration completed successfully!")

if __name__ == '__main__':
    migrate()
