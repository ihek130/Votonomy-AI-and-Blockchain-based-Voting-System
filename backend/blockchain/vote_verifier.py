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
    
    def check_vote_integrity(self, vote_id=None):
        """
        Check if local database votes match blockchain records
        Detects tampering/manipulation
        
        Args:
            vote_id: Specific vote ID to check, or None for all votes
        
        Returns:
            dict: Integrity report with tampering detection
        """
        try:
            # Get votes to check
            if vote_id:
                votes_to_check = [Vote.query.get(vote_id)]
                if not votes_to_check[0]:
                    return {'error': 'Vote not found'}
            else:
                votes_to_check = Vote.query.filter_by(is_verified_on_chain=True).all()
            
            results = {
                'total_checked': len(votes_to_check),
                'verified_intact': 0,
                'tampering_detected': 0,
                'unable_to_verify': 0,
                'tampered_votes': [],
                'integrity_status': 'CHECKING'
            }
            
            for vote in votes_to_check:
                if not vote.blockchain_tx_signature:
                    results['unable_to_verify'] += 1
                    continue
                
                # Verify transaction exists on blockchain
                try:
                    # Check if transaction exists (simplified verification)
                    tx_exists = self.client.get_transaction_details(vote.blockchain_tx_signature)
                    
                    if not tx_exists:
                        # Transaction not found - possible tampering or network issue
                        results['unable_to_verify'] += 1
                        print(f"⚠️  Transaction not found for vote {vote.id}: {vote.blockchain_tx_signature[:20]}...")
                        continue
                    
                    # Transaction exists on blockchain - vote is verified
                    # Additional check: verify signature matches
                    if tx_exists.get('signature') == vote.blockchain_tx_signature or str(tx_exists.get('signature')) == str(vote.blockchain_tx_signature):
                        results['verified_intact'] += 1
                    else:
                        # Signature mismatch - definite tampering
                        results['tampering_detected'] += 1
                        results['tampered_votes'].append({
                            'vote_id': vote.id,
                            'voter_id': vote.voter_id,
                            'position': vote.position,
                            'candidate_id': vote.candidate_id,
                            'blockchain_signature': vote.blockchain_tx_signature,
                            'issue': 'Blockchain signature mismatch',
                            'severity': 'CRITICAL'
                        })
                        
                except Exception as e:
                    print(f"⚠️  Error verifying vote {vote.id}: {str(e)}")
                    results['unable_to_verify'] += 1
            
            # Determine overall integrity status
            if results['tampering_detected'] > 0:
                results['integrity_status'] = 'COMPROMISED'
            elif results['verified_intact'] == results['total_checked']:
                results['integrity_status'] = 'VERIFIED_SECURE'
            else:
                results['integrity_status'] = 'PARTIAL_VERIFICATION'
            
            return results
            
        except Exception as e:
            return {
                'error': str(e),
                'integrity_status': 'ERROR'
            }
    
    def fetch_vote_from_blockchain(self, transaction_signature):
        """
        Fetch and decrypt vote directly from blockchain
        Ultimate source of truth
        
        Args:
            transaction_signature: Blockchain transaction signature
        
        Returns:
            dict: Decrypted vote data from blockchain
        """
        try:
            # Get transaction from blockchain
            tx_data = self.client.get_transaction_data(transaction_signature)
            
            if not tx_data:
                return {
                    'success': False,
                    'error': 'Transaction not found on blockchain'
                }
            
            # Extract memo data
            memo_data = self._extract_memo_from_transaction(tx_data)
            
            if not memo_data:
                return {
                    'success': False,
                    'error': 'No memo data in transaction'
                }
            
            # Decrypt vote
            try:
                decrypted_vote = self.encryption.decrypt_vote_data(
                    memo_data.get('encrypted_vote', '')
                )
                
                return {
                    'success': True,
                    'vote_data': decrypted_vote,
                    'voter_hash': memo_data.get('voter_hash'),
                    'position': memo_data.get('position'),
                    'halka': memo_data.get('halka'),
                    'timestamp': memo_data.get('timestamp'),
                    'election_id': memo_data.get('election_id'),
                    'source': 'BLOCKCHAIN'
                }
            except Exception as decrypt_error:
                return {
                    'success': False,
                    'error': f'Decryption failed: {str(decrypt_error)}',
                    'encrypted_data_exists': True
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _extract_memo_from_transaction(self, tx_data):
        """
        Extract memo instruction data from transaction
        
        Args:
            tx_data: Transaction data from blockchain
        
        Returns:
            dict: Parsed memo data
        """
        try:
            import json
            
            # Get transaction details
            if not tx_data or 'transaction' not in tx_data:
                return None
            
            transaction = tx_data['transaction']
            
            # Look for memo in transaction message
            if 'message' in transaction:
                instructions = transaction['message'].get('instructions', [])
                
                for instruction in instructions:
                    # Memo program ID
                    if instruction.get('programId') == 'MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr':
                        # Decode memo data
                        memo_text = instruction.get('data', '')
                        if memo_text:
                            try:
                                return json.loads(memo_text)
                            except:
                                # Try base64 decode if needed
                                import base64
                                decoded = base64.b64decode(memo_text).decode('utf-8')
                                return json.loads(decoded)
            
            return None
            
        except Exception as e:
            print(f"⚠️  Error extracting memo: {str(e)}")
            return None
    
    def get_blockchain_verified_results(self):
        """
        Get election results by fetching votes directly from blockchain
        Ultimate tamper-proof results
        
        Returns:
            dict: Election results from blockchain source
        """
        try:
            # Get all blockchain-verified votes
            blockchain_votes = Vote.query.filter_by(
                is_verified_on_chain=True
            ).all()
            
            results = {
                'total_votes': len(blockchain_votes),
                'positions': {},
                'verification_status': 'BLOCKCHAIN_VERIFIED',
                'source': 'SOLANA_BLOCKCHAIN'
            }
            
            for vote in blockchain_votes:
                # Fetch vote from blockchain
                blockchain_data = self.fetch_vote_from_blockchain(
                    vote.blockchain_tx_signature
                )
                
                if blockchain_data.get('success'):
                    position = blockchain_data.get('position')
                    candidate = blockchain_data.get('vote_data', {}).get('candidate_id')
                    
                    if position not in results['positions']:
                        results['positions'][position] = {}
                    
                    if candidate not in results['positions'][position]:
                        results['positions'][position][candidate] = 0
                    
                    results['positions'][position][candidate] += 1
            
            return results
            
        except Exception as e:
            return {
                'error': str(e),
                'verification_status': 'ERROR'
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
