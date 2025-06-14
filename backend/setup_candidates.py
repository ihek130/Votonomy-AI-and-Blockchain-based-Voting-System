from app import app
from models import db, Candidate
import re

def slugify(name):
    return re.sub(r'\W+', '', name.replace(" ", ""))

# Structured candidates
structured_candidates = [
    # NA-52
    {"name": "Ahmad Raza", "halka": "NA-52", "position": "President"},
    {"name": "Bilal Zafar", "halka": "NA-52", "position": "President"},
    {"name": "Irfan Hashmi", "halka": "NA-52", "position": "President"},
    {"name": "Saad Qureshi", "halka": "NA-52", "position": "President"},
    {"name": "Ali Nawaz", "halka": "NA-52", "position": "PrimeMinister"},
    {"name": "Imran Saleem", "halka": "NA-52", "position": "PrimeMinister"},
    {"name": "Yasir Abbasi", "halka": "NA-52", "position": "PrimeMinister"},
    {"name": "Hassan Shahbaz", "halka": "NA-52", "position": "PrimeMinister"},
    {"name": "Sara Khan", "halka": "NA-52", "position": "DefenseMinister"},
    {"name": "Mehreen Tariq", "halka": "NA-52", "position": "DefenseMinister"},
    {"name": "Danish Aftab", "halka": "NA-52", "position": "DefenseMinister"},
    {"name": "Taimur Riaz", "halka": "NA-52", "position": "DefenseMinister"},
    # NA-53
    {"name": "Zahid Bashir", "halka": "NA-53", "position": "President"},
    {"name": "Adnan Khalid", "halka": "NA-53", "position": "President"},
    {"name": "Umar Gul", "halka": "NA-53", "position": "President"},
    {"name": "Junaid Murtaza", "halka": "NA-53", "position": "President"},
    {"name": "Maryam Baloch", "halka": "NA-53", "position": "PrimeMinister"},
    {"name": "Zainab Iqbal", "halka": "NA-53", "position": "PrimeMinister"},
    {"name": "Waleed Asif", "halka": "NA-53", "position": "PrimeMinister"},
    {"name": "Sheraz Butt", "halka": "NA-53", "position": "PrimeMinister"},
    {"name": "Hamza Tariq", "halka": "NA-53", "position": "DefenseMinister"},
    {"name": "Areeba Shah", "halka": "NA-53", "position": "DefenseMinister"},
    {"name": "Salman Sheikh", "halka": "NA-53", "position": "DefenseMinister"},
    {"name": "Raheel Ahmed", "halka": "NA-53", "position": "DefenseMinister"},
    # NA-54
    {"name": "Usman Qureshi", "halka": "NA-54", "position": "President"},
    {"name": "Waqas Latif", "halka": "NA-54", "position": "President"},
    {"name": "Shahbaz Rafiq", "halka": "NA-54", "position": "President"},
    {"name": "Ahmed Siddiqui", "halka": "NA-54", "position": "President"},
    {"name": "Nida Ayaz", "halka": "NA-54", "position": "PrimeMinister"},
    {"name": "Sana Rizvi", "halka": "NA-54", "position": "PrimeMinister"},
    {"name": "Adil Farooq", "halka": "NA-54", "position": "PrimeMinister"},
    {"name": "Faizan Haider", "halka": "NA-54", "position": "PrimeMinister"},
    {"name": "Hassan Jameel", "halka": "NA-54", "position": "DefenseMinister"},
    {"name": "Zoya Khalid", "halka": "NA-54", "position": "DefenseMinister"},
    {"name": "Rizwan Sattar", "halka": "NA-54", "position": "DefenseMinister"},
    {"name": "Shahrukh Khan", "halka": "NA-54", "position": "DefenseMinister"},
]

with app.app_context():
    # 🔁 Step 1: Clean existing matching candidates by Halka-Position
    halkas = {"NA-52", "NA-53", "NA-54"}
    positions = {"President", "PrimeMinister", "DefenseMinister"}

    for halka in halkas:
        for position in positions:
            db.session.query(Candidate).filter(
                Candidate.candidate_id.like(f"{halka}-{position}%")
            ).delete()

    db.session.commit()

    # ✅ Step 2: Insert new structured candidates
    inserted = 0
    for entry in structured_candidates:
        cid = f"{entry['halka']}-{entry['position']}-{slugify(entry['name'])}"
        new_candidate = Candidate(candidate_name=entry["name"], candidate_id=cid)
        db.session.add(new_candidate)
        inserted += 1
    db.session.commit()

    print(f"✅ {inserted} structured candidates inserted after cleaning existing ones.")
