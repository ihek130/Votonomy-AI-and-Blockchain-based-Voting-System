"""
Vote Integrity Verification Script
Compares local database votes with blockchain records
Detects tampering and manipulation
"""

from app import app, db
from blockchain.vote_verifier import get_vote_verifier
from models import Vote
from colorama import init, Fore, Style

init()  # Initialize colorama for colored output


def print_header():
    """Print verification header"""
    print("\n" + "="*70)
    print(f"{Fore.CYAN}🔐 VOTONOMY VOTE INTEGRITY VERIFICATION{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Blockchain-Based Tampering Detection System{Style.RESET_ALL}")
    print("="*70 + "\n")


def verify_all_votes():
    """Verify all blockchain votes for integrity"""
    
    with app.app_context():
        print_header()
        
        # Get verifier
        print("📡 Connecting to Solana blockchain...")
        verifier = get_vote_verifier()
        
        # Get stats
        total_votes = Vote.query.count()
        blockchain_votes = Vote.query.filter_by(is_verified_on_chain=True).count()
        local_only = Vote.query.filter_by(is_verified_on_chain=False).count()
        
        print(f"📊 Database Statistics:")
        print(f"   Total votes: {total_votes}")
        print(f"   Blockchain-verified: {blockchain_votes}")
        print(f"   Local only: {local_only}")
        print()
        
        if blockchain_votes == 0:
            print(f"{Fore.YELLOW}⚠️  No blockchain-verified votes to check{Style.RESET_ALL}")
            print(f"   All {total_votes} votes are local-only (not on blockchain)")
            return
        
        # Run integrity check
        print(f"🔍 Verifying {blockchain_votes} blockchain votes...")
        print(f"   This may take a moment...\n")
        
        results = verifier.check_vote_integrity()
        
        # Display results
        print("="*70)
        print(f"{Fore.CYAN}INTEGRITY VERIFICATION RESULTS{Style.RESET_ALL}")
        print("="*70)
        
        status = results.get('integrity_status')
        
        if status == 'VERIFIED_SECURE':
            print(f"\n{Fore.GREEN}✅ SYSTEM SECURE - NO TAMPERING DETECTED{Style.RESET_ALL}\n")
        elif status == 'COMPROMISED':
            print(f"\n{Fore.RED}🚨 CRITICAL: VOTE TAMPERING DETECTED!{Style.RESET_ALL}\n")
        elif status == 'PARTIAL_VERIFICATION':
            print(f"\n{Fore.YELLOW}⚠️  PARTIAL VERIFICATION - Some votes could not be checked{Style.RESET_ALL}\n")
        else:
            print(f"\n{Fore.RED}❌ ERROR: {results.get('error')}{Style.RESET_ALL}\n")
            return
        
        # Show statistics
        print(f"Votes Checked:        {results.get('total_checked')}")
        print(f"{Fore.GREEN}Verified Intact:      {results.get('verified_intact')}{Style.RESET_ALL}")
        print(f"{Fore.RED}Tampering Detected:   {results.get('tampering_detected')}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Unable to Verify:     {results.get('unable_to_verify')}{Style.RESET_ALL}")
        
        # Show tampered votes
        if results.get('tampered_votes'):
            print(f"\n{Fore.RED}🚨 TAMPERED VOTES DETECTED:{Style.RESET_ALL}")
            print("="*70)
            
            for tampered in results['tampered_votes']:
                print(f"\n{Fore.RED}Vote ID: {tampered['vote_id']}{Style.RESET_ALL}")
                print(f"   Voter: {tampered['voter_id']}")
                print(f"   Position: {tampered['position']}")
                print(f"   Candidate: {tampered['candidate_id']}")
                print(f"   Issue: {tampered['issue']}")
                print(f"   Severity: {tampered['severity']}")
                print(f"   Blockchain Signature: {tampered['blockchain_signature']}")
                print(f"   Verify: https://explorer.solana.com/tx/{tampered['blockchain_signature']}?cluster=devnet")
            
            print("\n" + "="*70)
            print(f"{Fore.RED}⚠️  ACTION REQUIRED:{Style.RESET_ALL}")
            print(f"   1. Someone has modified votes in the local database")
            print(f"   2. The blockchain contains the original, unmodified votes")
            print(f"   3. Use blockchain data as the source of truth")
            print(f"   4. Investigate security breach immediately")
        
        print("\n" + "="*70)


def verify_specific_vote(vote_id):
    """Verify a specific vote"""
    
    with app.app_context():
        print_header()
        
        vote = Vote.query.get(vote_id)
        
        if not vote:
            print(f"{Fore.RED}❌ Vote ID {vote_id} not found{Style.RESET_ALL}")
            return
        
        if not vote.is_verified_on_chain:
            print(f"{Fore.YELLOW}⚠️  Vote ID {vote_id} is not blockchain-verified{Style.RESET_ALL}")
            print(f"   This is a local-only vote")
            return
        
        print(f"🔍 Verifying Vote ID: {vote_id}")
        print(f"   Position: {vote.position}")
        print(f"   Candidate: {vote.candidate_id}")
        print(f"   Blockchain Signature: {vote.blockchain_tx_signature}")
        print()
        
        verifier = get_vote_verifier()
        results = verifier.check_vote_integrity(vote_id=vote_id)
        
        if results.get('tampering_detected', 0) > 0:
            print(f"{Fore.RED}🚨 TAMPERING DETECTED!{Style.RESET_ALL}")
            print(f"   This vote has been modified in the database")
            print(f"   Original data is on blockchain: {vote.blockchain_tx_signature}")
        elif results.get('verified_intact', 0) > 0:
            print(f"{Fore.GREEN}✅ VERIFIED SECURE{Style.RESET_ALL}")
            print(f"   Vote matches blockchain record")
        else:
            print(f"{Fore.YELLOW}⚠️  Unable to verify{Style.RESET_ALL}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Verify specific vote
        try:
            vote_id = int(sys.argv[1])
            verify_specific_vote(vote_id)
        except ValueError:
            print(f"{Fore.RED}❌ Invalid vote ID. Must be a number.{Style.RESET_ALL}")
    else:
        # Verify all votes
        verify_all_votes()
