import pandas as pd
from models import db, VoterList
from app import app  # your main flask app

def import_voters(csv_file_path):
    df = pd.read_csv(csv_file_path)
    with app.app_context():
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
        print("Voters imported successfully!")

if __name__ == "__main__":
    import_voters(r"C:\Users\A.C\Desktop\sample_voter_data.csv")  # path to your CSV
