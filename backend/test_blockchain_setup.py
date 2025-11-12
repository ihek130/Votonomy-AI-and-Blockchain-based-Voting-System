"""
Test Blockchain Setup
Run this to verify Solana connection and encryption
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from blockchain.solana_client import get_solana_client
from blockchain.encryption import get_encryption_service


def test_encryption():
    """Test encryption module"""
    print("\n" + "="*60)
    print("🔐 TESTING ENCRYPTION MODULE")
    print("="*60)
    
    # Initialize encryption service
    encryption = get_encryption_service()
    
    # Test voter ID hashing
    voter_id = "PKV1001"
    voter_hash = encryption.hash_voter_id(voter_id)
    print(f"✅ Voter ID Hash: {voter_id} -> {voter_hash[:16]}...")
    
    # Test vote encryption
    vote_data = {
        "candidate_id": "NA122-PTI-PM",
        "position": "PM",
        "halka": "NA-122",
        "timestamp": "2025-11-12T10:30:00"
    }
    encrypted = encryption.encrypt_vote_data(vote_data)
    print(f"✅ Encrypted Vote: {encrypted[:40]}...")
    
    # Test decryption
    decrypted = encryption.decrypt_vote_data(encrypted)
    print(f"✅ Decrypted Vote: {decrypted['candidate_id']}")
    
    # Test payload creation
    payload = encryption.create_vote_payload(voter_id, "NA122-PTI-PM", "PM", "NA-122")
    print(f"✅ Vote Payload Created:")
    print(f"   - Voter Hash: {payload['voter_hash'][:16]}...")
    print(f"   - Encrypted: {payload['encrypted_vote'][:30]}...")
    print(f"   - Metadata: {payload['metadata']}")
    
    return True


def test_solana_connection():
    """Test Solana client connection"""
    print("\n" + "="*60)
    print("🌐 TESTING SOLANA CONNECTION")
    print("="*60)
    
    # Initialize Solana client
    client = get_solana_client()
    
    # Check connection
    connected = client.check_connection()
    if not connected:
        print("❌ Failed to connect to Solana devnet")
        return False
    
    # Get network stats
    stats = client.get_network_stats()
    print(f"\n📊 Network Stats:")
    print(f"   - Connected: {stats['connected']}")
    print(f"   - Network: {stats['network']}")
    print(f"   - Current Slot: {stats['current_slot']}")
    print(f"   - Admin Balance: {stats['admin_balance']} SOL")
    print(f"   - Admin Pubkey: {stats['admin_pubkey']}")
    
    # Check balance
    balance = client.get_balance()
    print(f"\n💰 Admin Wallet Balance: {balance} SOL")
    
    if balance < 0.1:
        print(f"\n⚠️  Low balance detected. Requesting airdrop...")
        client.request_airdrop(2)
    
    return True


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("🚀 VOTONOMY BLOCKCHAIN SETUP TEST")
    print("="*60)
    
    try:
        # Test encryption
        if not test_encryption():
            print("\n❌ Encryption test failed")
            return False
        
        # Test Solana connection
        if not test_solana_connection():
            print("\n❌ Solana connection test failed")
            return False
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60)
        print("\n🎯 Blockchain integration is ready!")
        print("   Next step: Integrate with vote casting in app.py")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
