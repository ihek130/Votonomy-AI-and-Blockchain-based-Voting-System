"""Quick test of integrity check"""
from app import app
from blockchain.vote_verifier import get_vote_verifier

with app.app_context():
    print('Testing integrity check...\n')
    verifier = get_vote_verifier()
    results = verifier.check_vote_integrity()
    
    print(f"Status: {results['integrity_status']}")
    print(f"Total: {results['total_checked']}")
    print(f"Verified: {results['verified_intact']}")
    print(f"Unable: {results['unable_to_verify']}")
    print(f"Tampered: {results['tampering_detected']}")
    
    if results.get('tampered_votes'):
        print("\nTampered votes:", results['tampered_votes'])
