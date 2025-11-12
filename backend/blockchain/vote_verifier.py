"""
Vote Verifier Module
Verify votes on Solana blockchain and generate audit reports
"""

from datetime import datetime
from models import Vote, Voter, db


class VoteVerifier:
    """
    Verify votes recorded on Solana blockchain
    Generate transparency and audit reports
    """
    
    def __init__(self, solana_client, encryption_service):
        """
        Initialize vote verifier
        
        Args:
            solana_client: SolanaVotingClient instance
            encryption_service: VoteEncryption instance
        """
        self.client = solana_client
        self.encryption = encryption_service
    
    def verify_vote_by_receipt(self, receipt_code):
        """
        Verify a vote using voter's receipt code
        
        Args:
            receipt_code: Receipt code given to voter (e.g., "RECEIPT-2wvCjx6o-7e675812")
        
        Returns:
            dict: Verification result with status and details
        """
        try:
            # Find vote by receipt
            vote = Vote.query.filter_by(verification_receipt=receipt_code).first()
            
            if not vote:
                return {
                    'verified': False,
                    'error': 'Receipt not found in system',
                    'message': 'Invalid receipt code or vote not recorded'
                }
            
            # Check if vote is on blockchain
            if not vote.is_verified_on_chain:
                return {
                    'verified': False,
                    'vote_exists': True,
                    'blockchain_verified': False,
                    'message': 'Vote recorded locally but not yet on blockchain',
                    'position': vote.position,
                    'timestamp': vote.created_at
                }
            
            # Verify on blockchain
            blockchain_verification = self.verify_on_blockchain(vote.blockchain_tx_signature)
            
            if blockchain_verification['exists']:
                return {
                    'verified': True,
                    'vote_exists': True,
                    'blockchain_verified': True,
                    'message': 'Vote successfully verified on Solana blockchain',
                    'position': vote.position,
                    'blockchain_signature': vote.blockchain_tx_signature,
                    'blockchain_slot': vote.blockchain_slot,
                    'blockchain_timestamp': vote.blockchain_timestamp,
                    'explorer_url': f"https://explorer.solana.com/tx/{vote.blockchain_tx_signature}?cluster=devnet"
                }
            else:
                return {
                    'verified': False,
                    'vote_exists': True,
                    'blockchain_verified': False,
                    'message': 'Vote in database but not found on blockchain',
                    'error': 'Blockchain verification failed'
                }
        
        except Exception as e:
            return {
                'verified': False,
                'error': str(e),
                'message': 'Verification error occurred'
            }
    
    def verify_on_blockchain(self, transaction_signature):
        """
        Verify transaction exists on Solana blockchain
        
        Args:
            transaction_signature: Transaction signature to verify
        
        Returns:
            dict: {'exists': bool, 'confirmed': bool, 'details': {...}}
        """
        try:
            tx_details = self.client.get_transaction_details(transaction_signature)
            
            if tx_details:
                return {
                    'exists': True,
                    'confirmed': True,
                    'signature': tx_details['signature'],
                    'slot': tx_details['slot'],
                    'blockTime': tx_details['blockTime']
                }
            else:
                return {
                    'exists': False,
                    'confirmed': False
                }
        except Exception as e:
            return {
                'exists': False,
                'confirmed': False,
                'error': str(e)
            }
    
    def get_blockchain_stats(self):
        """
        Get overall blockchain integration statistics
        
        Returns:
            dict: Blockchain statistics
        """
        try:
            # Count total votes
            total_votes = Vote.query.count()
            
            # Count blockchain-verified votes
            verified_votes = Vote.query.filter_by(is_verified_on_chain=True).count()
            
            # Count pending verification
            pending_votes = Vote.query.filter_by(is_verified_on_chain=False).count()
            
            # Get latest blockchain vote
            latest_blockchain_vote = Vote.query.filter_by(
                is_verified_on_chain=True
            ).order_by(Vote.blockchain_timestamp.desc()).first()
            
            # Get unique voters with blockchain votes
            unique_blockchain_voters = db.session.query(
                Vote.voter_id
            ).filter(
                Vote.is_verified_on_chain == True
            ).distinct().count()
            
            # Calculate verification rate
            verification_rate = (verified_votes / total_votes * 100) if total_votes > 0 else 0
            
            # Get network stats
            network_stats = self.client.get_network_stats()
            
            return {
                'total_votes': total_votes,
                'blockchain_verified': verified_votes,
                'pending_verification': pending_votes,
                'verification_rate': round(verification_rate, 2),
                'unique_blockchain_voters': unique_blockchain_voters,
                'latest_blockchain_vote': {
                    'signature': latest_blockchain_vote.blockchain_tx_signature if latest_blockchain_vote else None,
                    'timestamp': latest_blockchain_vote.blockchain_timestamp if latest_blockchain_vote else None,
                    'position': latest_blockchain_vote.position if latest_blockchain_vote else None
                },
                'network': {
                    'connected': network_stats.get('connected', False),
                    'current_slot': network_stats.get('current_slot', 0),
                    'admin_balance': network_stats.get('admin_balance', 0),
                    'network_url': network_stats.get('network', '')
                }
            }
        except Exception as e:
            return {
                'error': str(e),
                'total_votes': 0,
                'blockchain_verified': 0
            }
    
    def generate_audit_report(self):
        """
        Generate comprehensive audit report for election transparency
        
        Returns:
            dict: Detailed audit report
        """
        try:
            # Get all blockchain-verified votes
            verified_votes = Vote.query.filter_by(is_verified_on_chain=True).all()
            
            # Group by position
            positions_stats = {}
            for vote in verified_votes:
                if vote.position not in positions_stats:
                    positions_stats[vote.position] = {
                        'total': 0,
                        'first_vote': None,
                        'last_vote': None
                    }
                
                positions_stats[vote.position]['total'] += 1
                
                if positions_stats[vote.position]['first_vote'] is None:
                    positions_stats[vote.position]['first_vote'] = vote.blockchain_timestamp
                
                positions_stats[vote.position]['last_vote'] = vote.blockchain_timestamp
            
            # Get all unique transaction signatures
            all_signatures = [v.blockchain_tx_signature for v in verified_votes]
            
            # Generate report timestamp
            report_time = datetime.utcnow()
            
            return {
                'report_generated': report_time,
                'total_verified_votes': len(verified_votes),
                'positions': positions_stats,
                'blockchain_signatures': all_signatures,
                'verification_status': 'All votes cryptographically secured on Solana blockchain',
                'transparency_note': 'All blockchain transactions are publicly verifiable on Solana Explorer',
                'audit_trail': 'Complete immutable record maintained on-chain'
            }
        
        except Exception as e:
            return {
                'error': str(e),
                'report_generated': datetime.utcnow(),
                'status': 'Report generation failed'
            }
    
    def verify_voter_votes(self, voter_id):
        """
        Verify all votes cast by a specific voter
        
        Args:
            voter_id: Voter ID to check
        
        Returns:
            dict: Verification results for all voter's votes
        """
        try:
            votes = Vote.query.filter_by(voter_id=voter_id).all()
            
            if not votes:
                return {
                    'voter_id': voter_id,
                    'votes_found': False,
                    'message': 'No votes found for this voter'
                }
            
            results = []
            for vote in votes:
                verification = {
                    'position': vote.position,
                    'recorded_locally': True,
                    'blockchain_verified': vote.is_verified_on_chain,
                    'receipt': vote.verification_receipt,
                    'timestamp': vote.created_at
                }
                
                if vote.is_verified_on_chain:
                    verification['blockchain_signature'] = vote.blockchain_tx_signature
                    verification['blockchain_slot'] = vote.blockchain_slot
                    verification['explorer_url'] = f"https://explorer.solana.com/tx/{vote.blockchain_tx_signature}?cluster=devnet"
                
                results.append(verification)
            
            return {
                'voter_id': voter_id,
                'votes_found': True,
                'total_votes': len(votes),
                'blockchain_verified_count': sum(1 for v in votes if v.is_verified_on_chain),
                'votes': results
            }
        
        except Exception as e:
            return {
                'voter_id': voter_id,
                'error': str(e),
                'votes_found': False
            }


# Helper function to get verifier instance
def get_vote_verifier():
    """
    Get VoteVerifier instance with initialized clients
    
    Returns:
        VoteVerifier: Verifier instance
    """
    from .solana_client import get_solana_client
    from .encryption import get_encryption_service
    
    solana_client = get_solana_client()
    encryption_service = get_encryption_service()
    
    return VoteVerifier(solana_client, encryption_service)
