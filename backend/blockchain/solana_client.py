"""
Solana Voting Client
Handles connection to Solana devnet and wallet operations
"""

import json
import time
from pathlib import Path
from solana.rpc.api import Client
from solders.keypair import Keypair  # type: ignore
from solders.transaction import Transaction  # type: ignore
from solders.system_program import TransferParams, transfer  # type: ignore
from solders.pubkey import Pubkey  # type: ignore
from solders.signature import Signature  # type: ignore
from solders.system_program import ID as SYS_PROGRAM_ID  # type: ignore
from solana.rpc.commitment import Confirmed


class SolanaVotingClient:
    """
    Solana blockchain client for Votonomy voting system
    Handles RPC connection, wallet management, and transaction building
    """
    
    def __init__(self, rpc_url, admin_keypair_path=None):
        """
        Initialize Solana client
        
        Args:
            rpc_url: Solana RPC endpoint (e.g., "https://api.devnet.solana.com")
            admin_keypair_path: Path to admin wallet keypair JSON
        """
        self.rpc_url = rpc_url
        self.client = Client(rpc_url, commitment=Confirmed)
        self.admin_keypair = None
        self.admin_keypair_path = admin_keypair_path
        
        # Load or generate admin keypair
        if admin_keypair_path:
            self._load_or_create_keypair(admin_keypair_path)
    
    def _load_or_create_keypair(self, keypair_path):
        """
        Load existing keypair or create new one
        
        Args:
            keypair_path: Path to keypair JSON file
        """
        path = Path(keypair_path)
        
        if path.exists():
            # Load existing keypair
            with open(path, 'r') as f:
                secret_key = json.load(f)
            self.admin_keypair = Keypair.from_bytes(bytes(secret_key))
            print(f"✅ Loaded admin wallet: {self.admin_keypair.pubkey()}")
        else:
            # Generate new keypair
            self.admin_keypair = Keypair()
            
            # Save to file
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w') as f:
                json.dump(list(bytes(self.admin_keypair)), f)
            
            print(f"✅ Created new admin wallet: {self.admin_keypair.pubkey()}")
            print(f"⚠️  Keypair saved to: {keypair_path}")
            print(f"⚠️  Request devnet SOL: solana airdrop 2 {self.admin_keypair.pubkey()} --url devnet")
    
    def check_connection(self):
        """
        Test RPC connection to Solana
        
        Returns:
            bool: True if connected, False otherwise
        """
        try:
            version = self.client.get_version()
            print(f"✅ Connected to Solana {self.rpc_url}")
            print(f"   Solana version: {version.value}")
            return True
        except Exception as e:
            print(f"❌ Failed to connect to Solana: {str(e)}")
            return False
    
    def get_balance(self, pubkey=None):
        """
        Get SOL balance of wallet
        
        Args:
            pubkey: Public key to check (defaults to admin wallet)
        
        Returns:
            float: Balance in SOL
        """
        try:
            if pubkey is None:
                if self.admin_keypair is None:
                    raise ValueError("No admin keypair loaded")
                pubkey = self.admin_keypair.pubkey()
            
            balance_response = self.client.get_balance(pubkey)
            lamports = balance_response.value
            sol = lamports / 1_000_000_000  # Convert lamports to SOL
            
            return sol
        except Exception as e:
            print(f"❌ Failed to get balance: {str(e)}")
            return 0.0
    
    def request_airdrop(self, amount_sol=2):
        """
        Request SOL airdrop from devnet faucet
        Only works on devnet/testnet
        
        Args:
            amount_sol: Amount of SOL to request (default: 2 SOL)
        
        Returns:
            str: Transaction signature if successful, None otherwise
        """
        try:
            if self.admin_keypair is None:
                raise ValueError("No admin keypair loaded")
            
            print(f"🪂 Requesting {amount_sol} SOL airdrop...")
            
            lamports = int(amount_sol * 1_000_000_000)
            response = self.client.request_airdrop(
                self.admin_keypair.pubkey(),
                lamports
            )
            
            signature = response.value
            print(f"✅ Airdrop requested: {signature}")
            
            # Wait for confirmation
            time.sleep(2)
            self.confirm_transaction(signature)
            
            new_balance = self.get_balance()
            print(f"💰 New balance: {new_balance} SOL")
            
            return signature
        except Exception as e:
            print(f"❌ Airdrop failed: {str(e)}")
            print(f"   Try manual airdrop: solana airdrop 2 {self.admin_keypair.pubkey()} --url devnet")
            return None
    
    def confirm_transaction(self, signature, timeout=60):
        """
        Wait for transaction confirmation
        
        Args:
            signature: Transaction signature (string or Signature object)
            timeout: Maximum seconds to wait
        
        Returns:
            bool: True if confirmed, False if timeout
        """
        start_time = time.time()
        
        # Convert string to Signature if needed
        if isinstance(signature, str):
            try:
                sig_obj = Signature.from_string(signature)
            except:
                # If conversion fails, try checking with get_transaction instead
                print(f"⚠️  Signature format issue, using alternative check")
                time.sleep(5)  # Give transaction time to propagate
                return self._confirm_with_get_transaction(signature, timeout)
        else:
            sig_obj = signature
        
        while time.time() - start_time < timeout:
            try:
                response = self.client.get_signature_statuses([sig_obj])
                status = response.value[0]
                
                if status is not None:
                    if status.confirmation_status == Confirmed:
                        print(f"✅ Transaction confirmed: {signature}")
                        return True
                    elif status.err:
                        print(f"❌ Transaction failed: {status.err}")
                        return False
                
                time.sleep(1)
            except Exception as e:
                print(f"⚠️  Confirmation check error: {str(e)}")
                time.sleep(1)
        
        print(f"⏱️  Transaction confirmation timeout: {signature}")
        print(f"   ℹ️  Devnet can be slow. Checking if transaction exists...")
        
        # Try alternative confirmation method
        return self._confirm_with_get_transaction(str(signature), 10)
    
    def _confirm_with_get_transaction(self, signature, timeout=10):
        """
        Alternative confirmation method using get_transaction
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                tx = self.get_transaction_details(signature)
                if tx is not None:
                    print(f"✅ Transaction found on blockchain!")
                    return True
                time.sleep(2)
            except:
                time.sleep(2)
        
        print(f"   ⚠️  Could not confirm. Check explorer:")
        print(f"   https://explorer.solana.com/tx/{signature}?cluster=devnet")
        # Return True anyway - transaction was sent
        return True
    
    def _confirm_with_get_transaction(self, signature, timeout=30):
        """Alternative confirmation method using get_transaction"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                tx = self.get_transaction_details(signature)
                if tx is not None:
                    print(f"✅ Transaction confirmed: {signature}")
                    return True
                time.sleep(2)
            except:
                time.sleep(2)
        return False
    
    def get_latest_blockhash(self):
        """
        Get latest blockhash for transaction
        
        Returns:
            str: Recent blockhash
        """
        try:
            response = self.client.get_latest_blockhash()
            return response.value.blockhash
        except Exception as e:
            print(f"❌ Failed to get blockhash: {str(e)}")
            raise
    
    def get_slot(self):
        """
        Get current slot number
        
        Returns:
            int: Current slot
        """
        try:
            response = self.client.get_slot()
            return response.value
        except Exception as e:
            print(f"❌ Failed to get slot: {str(e)}")
            return 0
    
    def get_transaction_details(self, signature):
        """
        Fetch transaction details from blockchain
        
        Args:
            signature: Transaction signature (string or Signature object)
        
        Returns:
            dict: Transaction details or None
        """
        try:
            # Convert string to Signature if needed
            if isinstance(signature, str):
                sig_obj = Signature.from_string(signature)
            else:
                sig_obj = signature
            
            response = self.client.get_transaction(
                sig_obj,
                encoding="json",
                commitment=Confirmed
            )
            
            if response.value:
                tx = response.value
                return {
                    "signature": signature,
                    "slot": tx.slot,
                    "blockTime": tx.block_time,
                    "meta": tx.transaction.meta,
                    "transaction": tx.transaction.transaction
                }
            return None
        except Exception as e:
            print(f"❌ Failed to get transaction: {str(e)}")
            return None
    
    def ensure_sufficient_balance(self, min_balance_sol=0.1):
        """
        Ensure admin wallet has sufficient SOL for transactions
        
        Args:
            min_balance_sol: Minimum required balance in SOL
        
        Returns:
            bool: True if balance is sufficient
        """
        balance = self.get_balance()
        
        if balance < min_balance_sol:
            print(f"⚠️  Low balance: {balance} SOL (need {min_balance_sol} SOL)")
            print(f"   Attempting airdrop...")
            self.request_airdrop(2)
            balance = self.get_balance()
        
        return balance >= min_balance_sol
    
    def get_network_stats(self):
        """
        Get Solana network statistics
        
        Returns:
            dict: Network stats
        """
        try:
            slot = self.get_slot()
            balance = self.get_balance()
            
            return {
                "connected": True,
                "network": self.rpc_url,
                "current_slot": slot,
                "admin_balance": balance,
                "admin_pubkey": str(self.admin_keypair.pubkey()) if self.admin_keypair else None
            }
        except Exception as e:
            return {
                "connected": False,
                "error": str(e)
            }


# Helper function to get client instance
def get_solana_client():
    """
    Get Solana client instance with configuration from config.py
    
    Returns:
        SolanaVotingClient: Client instance
    """
    from .config import RPC_ENDPOINT, ADMIN_WALLET_PATH
    
    client = SolanaVotingClient(RPC_ENDPOINT, ADMIN_WALLET_PATH)
    
    # Check connection on initialization
    if client.check_connection():
        client.ensure_sufficient_balance()
    
    return client
