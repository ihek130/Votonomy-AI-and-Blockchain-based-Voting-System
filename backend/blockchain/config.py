"""
Blockchain Configuration
Settings for Solana devnet and encryption
"""

import os
from pathlib import Path

# Solana Network Configuration
SOLANA_NETWORK = "devnet"  # devnet for testing (free), mainnet-beta for production
RPC_ENDPOINT = "https://api.devnet.solana.com"

# Alternative RPC endpoints (in case primary is down)
BACKUP_RPC_ENDPOINTS = [
    "https://api.devnet.solana.com",
    "https://rpc.ankr.com/solana_devnet",
]

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
WALLETS_DIR = BASE_DIR / "wallets"
KEYS_DIR = BASE_DIR / "keys"

# Ensure directories exist
WALLETS_DIR.mkdir(exist_ok=True)
KEYS_DIR.mkdir(exist_ok=True)

# Admin wallet (will be created if doesn't exist)
ADMIN_WALLET_PATH = WALLETS_DIR / "admin_keypair.json"

# Encryption key path
ENCRYPTION_KEY_PATH = KEYS_DIR / "vote_encryption.key"

# Blockchain settings
CONFIRMATION_TIMEOUT = 60  # seconds
MAX_RETRY_ATTEMPTS = 3
TRANSACTION_FEE_PAYER = "admin"  # Who pays transaction fees

# Election configuration
ELECTION_ID = "2025-GENERAL-ELECTION"
VOTE_PROGRAM_VERSION = "1.0.0"

# Security settings
ENABLE_ENCRYPTION = True
HASH_ALGORITHM = "SHA256"
ENCRYPTION_ALGORITHM = "AES256-GCM"


class BlockchainConfig:
    """Blockchain configuration singleton"""
    
    def __init__(self):
        self.network = SOLANA_NETWORK
        self.rpc_endpoint = RPC_ENDPOINT
        self.admin_wallet_path = str(ADMIN_WALLET_PATH)
        self.encryption_key_path = str(ENCRYPTION_KEY_PATH)
        self.election_id = ELECTION_ID
        
    def get_rpc_endpoint(self):
        """Get primary RPC endpoint"""
        return self.rpc_endpoint
    
    def get_backup_endpoints(self):
        """Get backup RPC endpoints"""
        return BACKUP_RPC_ENDPOINTS
    
    def is_devnet(self):
        """Check if using devnet (free testing)"""
        return self.network == "devnet"
    
    def is_mainnet(self):
        """Check if using mainnet (production)"""
        return self.network == "mainnet-beta"


# Singleton instance
config = BlockchainConfig()
