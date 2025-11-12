"""
Test Vote Recorder
Test recording encrypted votes on Solana blockchain
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from blockchain.vote_recorder import get_vote_recorder


def test_vote_recording():
    """Test recording a vote on Solana blockchain"""
    print("\n" + "="*60)
    print("🗳️  TESTING VOTE RECORDING ON BLOCKCHAIN")
    print("="*60)
    
    # Initialize vote recorder
    recorder = get_vote_recorder()
    
    # Test vote data
    test_vote = {
        'voter_id': 'PKV1001',
        'candidate_id': 'NA122-PTI-PM',
        'position': 'PM',
        'halka': 'NA-122'
    }
    
    print(f"\n📝 Test Vote:")
    print(f"   Voter ID: {test_vote['voter_id']}")
    print(f"   Candidate: {test_vote['candidate_id']}")
    print(f"   Position: {test_vote['position']}")
    print(f"   Halka: {test_vote['halka']}")
    
    # Record vote on blockchain
    result = recorder.record_vote_on_chain(
        voter_id=test_vote['voter_id'],
        candidate_id=test_vote['candidate_id'],
        position=test_vote['position'],
        halka=test_vote['halka']
    )
    
    if result['success']:
        print(f"\n✅ VOTE RECORDED ON BLOCKCHAIN!")
        print(f"   Transaction Signature: {result['signature']}")
        print(f"   Block Slot: {result['slot']}")
        print(f"   Timestamp: {result['timestamp']}")
        print(f"   Voter Hash (Anonymous): {result['voter_hash'][:32]}...")
        print(f"   Verification Receipt: {result['receipt']}")
        print(f"\n🔗 View on Solana Explorer:")
        print(f"   https://explorer.solana.com/tx/{result['signature']}?cluster=devnet")
        
        # Test verification
        print(f"\n🔍 Verifying vote on blockchain...")
        verification = recorder.verify_vote_on_chain(result['signature'])
        
        if verification['exists']:
            print(f"   ✅ Vote verified on blockchain!")
            print(f"   Confirmed: {verification['confirmed']}")
            print(f"   Block Slot: {verification['slot']}")
        else:
            print(f"   ❌ Vote not found on blockchain")
        
        return True
    else:
        print(f"\n❌ VOTE RECORDING FAILED")
        print(f"   Error: {result.get('error')}")
        return False


def main():
    """Run vote recording test"""
    print("\n" + "="*60)
    print("🚀 VOTONOMY BLOCKCHAIN VOTE RECORDER TEST")
    print("="*60)
    
    try:
        success = test_vote_recording()
        
        if success:
            print("\n" + "="*60)
            print("✅ VOTE RECORDER TEST PASSED!")
            print("="*60)
            print("\n🎯 Ready to integrate with app.py!")
            print("="*60)
        else:
            print("\n" + "="*60)
            print("❌ VOTE RECORDER TEST FAILED")
            print("="*60)
        
        return success
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
