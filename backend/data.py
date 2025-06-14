# data.py

registered_voters = []
candidates_db = []
votes = []
voter_requests = []
rejected_requests = []
candidate_requests = []  # For pending candidate registration requests
pre_surveys = []
post_surveys = [] 
# If you use positions, add them here. For example:
positions_db = [
    {"id": "NA-52", "title": "President", "candidate_name": "Ahmad Raza"},
    {"id": "NA-52", "title": "Prime Minister", "candidate_name": "Ali Nawaz"},
    {"id": "NA-52", "title": "Defense Minister", "candidate_name": "Sara Khan"},
    {"id": "NA-53", "title": "President", "candidate_name": "Zahid Bashir"},
    {"id": "NA-53", "title": "Prime Minister", "candidate_name": "Maryam Baloch"},
    {"id": "NA-53", "title": "Defense Minister", "candidate_name": "Hamza Tariq"},
    {"id": "NA-54", "title": "President", "candidate_name": "Usman Qureshi"},
    {"id": "NA-54", "title": "Prime Minister", "candidate_name": "Nida Ayaz"},
    {"id": "NA-54", "title": "Defense Minister", "candidate_name": "Hassan Jameel"},
]
