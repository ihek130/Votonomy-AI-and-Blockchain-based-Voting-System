"""
Vote Recorder Module
Records encrypted votes on Solana blockchain with memo transactions
"""

import json
import time
from datetime import datetime
from solders.transaction import Transaction  # type: ignore
from solders.message import Message  # type: ignore
from solders.instruction import Instruction, AccountMeta  # type: ignore
from solders.pubkey import Pubkey  # type: ignore
from solana.rpc.types import TxOpts
from solana.rpc.commitment import Confirmed

# Memo program ID (Solana's built-in memo program)
MEMO_PROGRAM_ID = Pubkey.from_string("MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr")


class VoteRecorder:
    """
    Records votes on Solana blockchain using memo transactions
    Each vote is encrypted and stored as a memo on-chain
    """
    
    def __init__(self, solana_client, encryption_service):
        """
        Initialize vote recorder
        
        Args:
            solana_client: SolanaVotingClient instance
            encryption_service: VoteEncryption instance
        """
        self.client = solana_client
        self.encryption = encryption_service
    
    def record_vote_on_chain(self, voter_id, candidate_id, position, halka):
        """
        Record encrypted vote on Solana blockchain
        
        Args:
            voter_id: Original voter ID (will be hashed)
            candidate_id: Candidate ID
            position: Position being voted for
            halka: Electoral constituency
        
        Returns:
            dict: {
                'success': bool,
                'signature': str,
                'slot': int,
                'timestamp': datetime,
                'voter_hash': str,
                'encrypted_data': str,
                'receipt': str,
                'error': str (if failed)
            }
        """
        try:
            print(f"\n🔐 Recording vote on blockchain...")
            print(f"   Voter: {voter_id} (will be hashed)")
            print(f"   Candidate: {candidate_id}")
            print(f"   Position: {position}")
            print(f"   Halka: {halka}")
            
            # Step 1: Create encrypted vote payload
            payload = self.encryption.create_vote_payload(
                voter_id=voter_id,
                candidate_id=candidate_id,
                position=position,
                halka=halka
            )
            
            voter_hash = payload['voter_hash']
            encrypted_vote = payload['encrypted_vote']
            metadata = payload['metadata']
            
            print(f"   ✅ Vote encrypted")
            print(f"   ✅ Voter hash: {voter_hash[:16]}...")
            
            # Step 2: Create memo data (what goes on blockchain)
            memo_data = {
                "type": "VOTE",
                "election_id": metadata['election_id'],
                "voter_hash": voter_hash[:32],  # First 32 chars for space
                "encrypted_vote": encrypted_vote[:200],  # Truncate for memo limit
                "halka": halka,
                "position": position,
                "version": metadata['version'],
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Convert to compact JSON
            memo_str = json.dumps(memo_data, separators=(',', ':'))
            
            # Memo program has 566 byte limit, truncate if needed
            if len(memo_str) > 566:
                memo_str = memo_str[:563] + "..."
            
            print(f"   📝 Memo size: {len(memo_str)} bytes")
            
            # Step 3: Send transaction to Solana
            result = self._send_memo_transaction(memo_str)
            
            if result['success']:
                # Step 4: Generate receipt
                receipt = self.encryption.generate_vote_receipt(
                    result['signature'],
                    voter_hash
                )
                
                print(f"   ✅ Transaction confirmed!")
                print(f"   📜 Signature: {result['signature'][:16]}...")
                print(f"   🎫 Receipt: {receipt}")
                
                return {
                    'success': True,
                    'signature': result['signature'],
                    'slot': result['slot'],
                    'timestamp': result['timestamp'],
                    'voter_hash': voter_hash,
                    'encrypted_data': encrypted_vote,
                    'receipt': receipt,
                    'error': None
                }
            else:
                print(f"   ❌ Transaction failed: {result.get('error')}")
                return {
                    'success': False,
                    'error': result.get('error', 'Unknown error')
                }
        
        except Exception as e:
            print(f"   ❌ Vote recording failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }
    
    def _send_memo_transaction(self, memo_text):
        """
        Send memo transaction to Solana
        
        Args:
            memo_text: Text to store in memo
        
        Returns:
            dict: {'success': bool, 'signature': str, 'slot': int, 'timestamp': datetime}
        """
        try:
            # Ensure sufficient balance
            if not self.client.ensure_sufficient_balance(0.01):
                return {
                    'success': False,
                    'error': 'Insufficient SOL balance for transaction'
                }
            
            # Create memo instruction
            memo_instruction = Instruction(
                program_id=MEMO_PROGRAM_ID,
                accounts=[
                    AccountMeta(
                        pubkey=self.client.admin_keypair.pubkey(),
                        is_signer=True,
                        is_writable=False
                    )
                ],
                data=memo_text.encode('utf-8')
            )
            
            # Get recent blockhash
            recent_blockhash = self.client.get_latest_blockhash()
            
            # Create message
            message = Message.new_with_blockhash(
                [memo_instruction],
                self.client.admin_keypair.pubkey(),
                recent_blockhash
            )
            
            # Create signed transaction
            transaction = Transaction([self.client.admin_keypair], message, recent_blockhash)
            
            # Send transaction (send raw transaction)
            response = self.client.client.send_raw_transaction(
                bytes(transaction),
                opts=TxOpts(skip_preflight=False, preflight_commitment=Confirmed)
            )
            
            signature = str(response.value)
            
            # Check if fast mode is enabled
            import os
            fast_mode_file = os.path.join(os.path.dirname(__file__), '..', 'blockchain_fast_mode.txt')
            fast_mode = os.path.exists(fast_mode_file)
            
            if fast_mode:
                # Fast mode: skip full confirmation, just check signature exists
                print(f"   ⚡ Fast mode: minimal confirmation")
                confirmed = True
                time.sleep(2)  # Brief wait for transaction to propagate
            else:
                # Normal mode: full confirmation
                confirmed = self.client.confirm_transaction(signature, timeout=30)
            
            if confirmed:
                # Get slot and timestamp
                slot = self.client.get_slot()
                timestamp = datetime.utcnow()
                
                return {
                    'success': True,
                    'signature': signature,
                    'slot': slot,
                    'timestamp': timestamp
                }
            else:
                return {
                    'success': False,
                    'error': 'Transaction confirmation timeout'
                }
        
        except Exception as e:
            return {
                'success': False,
                'error': f'Transaction failed: {str(e)}'
            }
    
    def verify_vote_on_chain(self, transaction_signature):
        """
        Verify that a vote transaction exists on blockchain
        
        Args:
            transaction_signature: Transaction signature to verify
        
        Returns:
            dict: Transaction details or None
        """
        try:
            tx_details = self.client.get_transaction_details(transaction_signature)
            
            if tx_details:
                return {
                    'exists': True,
                    'signature': tx_details['signature'],
                    'slot': tx_details['slot'],
                    'blockTime': tx_details['blockTime'],
                    'confirmed': True
                }
            else:
                return {
                    'exists': False,
                    'confirmed': False
                }
        except Exception as e:
            print(f"❌ Verification failed: {str(e)}")
            return {
                'exists': False,
                'confirmed': False,
                'error': str(e)
            }


# Helper function to get recorder instance
def get_vote_recorder():
    """
    Get VoteRecorder instance with initialized clients
    
    Returns:
        VoteRecorder: Recorder instance
    """
    from .solana_client import get_solana_client
    from .encryption import get_encryption_service
    
    solana_client = get_solana_client()
    encryption_service = get_encryption_service()
    
    return VoteRecorder(solana_client, encryption_service)
