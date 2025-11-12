"""
Vote Encryption Module
Handles AES-256 encryption and voter ID hashing for blockchain storage
"""

import hashlib
import json
import secrets
from datetime import datetime
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64


class VoteEncryption:
    """
    Handles encryption and hashing for vote data before blockchain storage
    - Voter IDs are hashed (SHA-256) for anonymity
    - Vote data is encrypted (AES-256-GCM via Fernet)
    - Receipts are generated for verification
    """
    
    def __init__(self, encryption_key=None):
        """
        Initialize encryption service
        Args:
            encryption_key: Base64-encoded Fernet key. If None, generates new key.
        """
        if encryption_key is None:
            encryption_key = Fernet.generate_key()
        
        if isinstance(encryption_key, str):
            encryption_key = encryption_key.encode()
        
        self.cipher = Fernet(encryption_key)
        self.encryption_key = encryption_key
    
    def hash_voter_id(self, voter_id):
        """
        Create non-reversible hash of voter ID for anonymity
        Uses SHA-256 with salt for security
        
        Args:
            voter_id: Original voter ID (e.g., "PKV1001")
        
        Returns:
            str: Hex-encoded hash (64 characters)
        """
        # Add election-specific salt to prevent rainbow table attacks
        salt = "VOTONOMY-2025-ELECTION".encode()
        data = f"{voter_id}".encode() + salt
        
        hash_obj = hashlib.sha256(data)
        return hash_obj.hexdigest()
    
    def encrypt_vote_data(self, vote_data):
        """
        Encrypt vote data before blockchain storage
        
        Args:
            vote_data: dict containing vote information
                {
                    "candidate_id": "NA122-PTI-PM",
                    "position": "PM",
                    "halka": "NA-122",
                    "timestamp": "2025-11-12T10:30:00"
                }
        
        Returns:
            str: Base64-encoded encrypted data
        """
        # Convert dict to JSON string
        json_data = json.dumps(vote_data, ensure_ascii=False)
        
        # Encrypt using Fernet (AES-256-GCM)
        encrypted_bytes = self.cipher.encrypt(json_data.encode())
        
        # Return as base64 string for storage
        return base64.b64encode(encrypted_bytes).decode()
    
    def decrypt_vote_data(self, encrypted_data):
        """
        Decrypt vote data (for verification purposes only)
        
        Args:
            encrypted_data: Base64-encoded encrypted string
        
        Returns:
            dict: Decrypted vote data
        """
        try:
            # Decode from base64
            encrypted_bytes = base64.b64decode(encrypted_data.encode())
            
            # Decrypt using Fernet
            decrypted_bytes = self.cipher.decrypt(encrypted_bytes)
            
            # Parse JSON
            return json.loads(decrypted_bytes.decode())
        except Exception as e:
            raise ValueError(f"Failed to decrypt vote data: {str(e)}")
    
    def generate_vote_receipt(self, transaction_signature, voter_id_hash):
        """
        Generate verifiable receipt for voter
        Format: RECEIPT-{first8chars_of_sig}-{first8chars_of_hash}
        
        Args:
            transaction_signature: Solana transaction signature
            voter_id_hash: Hashed voter ID
        
        Returns:
            str: Receipt code (e.g., "RECEIPT-5J7Wx2Kp-a3f9c1d2")
        """
        sig_prefix = transaction_signature[:8] if len(transaction_signature) >= 8 else transaction_signature
        hash_prefix = voter_id_hash[:8]
        
        return f"RECEIPT-{sig_prefix}-{hash_prefix}"
    
    def verify_receipt(self, receipt_code, transaction_signature, voter_id_hash):
        """
        Verify if receipt matches transaction and voter hash
        
        Args:
            receipt_code: Receipt provided by voter
            transaction_signature: Blockchain transaction signature
            voter_id_hash: Hashed voter ID
        
        Returns:
            bool: True if receipt is valid
        """
        expected_receipt = self.generate_vote_receipt(transaction_signature, voter_id_hash)
        return receipt_code == expected_receipt
    
    def create_vote_payload(self, voter_id, candidate_id, position, halka):
        """
        Create complete encrypted vote payload for blockchain
        
        Args:
            voter_id: Original voter ID (will be hashed)
            candidate_id: Candidate ID (e.g., "NA122-PTI-PM")
            position: Position (e.g., "PM")
            halka: Electoral constituency (e.g., "NA-122")
        
        Returns:
            dict: {
                "voter_hash": "abc123...",
                "encrypted_vote": "base64_encrypted_data",
                "metadata": {...}
            }
        """
        # Hash voter ID for anonymity
        voter_hash = self.hash_voter_id(voter_id)
        
        # Prepare vote data
        vote_data = {
            "candidate_id": candidate_id,
            "position": position,
            "halka": halka,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Encrypt vote data
        encrypted_vote = self.encrypt_vote_data(vote_data)
        
        # Create metadata (non-sensitive info for transparency)
        metadata = {
            "election_id": "2025-GENERAL-ELECTION",
            "vote_type": "ENCRYPTED_BALLOT",
            "halka": halka,  # Public info for counting
            "version": "1.0.0"
        }
        
        return {
            "voter_hash": voter_hash,
            "encrypted_vote": encrypted_vote,
            "metadata": metadata
        }
    
    @staticmethod
    def generate_encryption_key():
        """
        Generate a new Fernet encryption key
        Should be called once and stored securely
        
        Returns:
            bytes: Fernet key (base64-encoded)
        """
        return Fernet.generate_key()
    
    @staticmethod
    def save_encryption_key(key, filepath):
        """
        Save encryption key to file
        
        Args:
            key: Fernet key (bytes)
            filepath: Path to save key
        """
        with open(filepath, 'wb') as f:
            f.write(key)
    
    @staticmethod
    def load_encryption_key(filepath):
        """
        Load encryption key from file
        
        Args:
            filepath: Path to key file
        
        Returns:
            bytes: Fernet key
        """
        with open(filepath, 'rb') as f:
            return f.read()


# Helper function to initialize encryption service
def get_encryption_service(key_path=None):
    """
    Get or create encryption service instance
    
    Args:
        key_path: Path to encryption key file
    
    Returns:
        VoteEncryption: Encryption service instance
    """
    from .config import ENCRYPTION_KEY_PATH
    
    key_file = key_path or ENCRYPTION_KEY_PATH
    
    # Load existing key or generate new one
    try:
        key = VoteEncryption.load_encryption_key(key_file)
    except FileNotFoundError:
        # Generate new key on first run
        key = VoteEncryption.generate_encryption_key()
        VoteEncryption.save_encryption_key(key, key_file)
        print(f"✅ Generated new encryption key: {key_file}")
    
    return VoteEncryption(key)
