import pandas as pd
from models import db, VoterList, Voter, PreSurvey, Vote, SentimentAnalytics
from app import app  # your main flask app

def import_voters(csv_file_path):
    df = pd.read_csv(csv_file_path)
    with app.app_context():
        # Clear existing voter data (but keep candidates)
        print("🗑️  Clearing existing voter data...")
        Vote.query.delete()  # Delete all votes
        PreSurvey.query.delete()  # Delete all survey responses
        SentimentAnalytics.query.delete()  # Delete sentiment analytics
        Voter.query.delete()  # Delete all registered voters
        VoterList.query.delete()  # Delete all voter list entries
        db.session.commit()
        print("✅ Existing voter data, votes, and surveys cleared!")
        
        # Import new voters from CSV
        print(f"📥 Importing {len(df)} voters from CSV...")
        for _, row in df.iterrows():
            voter = VoterList(
                voter_id=row['VoterID'],
                full_name=row['FullName'],
                father_name=row['FatherName'],
                cnic=row['CNIC'],
                city=row['City'],
                province=row['Province'],
                gender=row['Gender'],
                age=row['Age']
            )
            db.session.add(voter)
        db.session.commit()
        print(f"✅ {len(df)} voters imported successfully!")

if __name__ == "__main__":
    import_voters(r"D:\Votonomy\backend\sample_voter_data.csv")  # path to your CSV
