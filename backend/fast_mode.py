"""
Fast Devnet Mode Configuration
Creates a config file to toggle fast vs. secure blockchain voting
"""

import os
from pathlib import Path

# Get backend directory
BACKEND_DIR = Path(__file__).resolve().parent

# Configuration file path
FAST_MODE_CONFIG = BACKEND_DIR / 'blockchain_fast_mode.txt'

def enable_fast_mode():
    """
    Enable fast mode for devnet testing
    - Reduces confirmation timeout
    - Skips some verification steps
    - NOT recommended for production
    """
    with open(FAST_MODE_CONFIG, 'w') as f:
        f.write('ENABLED\n')
        f.write('# Fast mode is enabled for faster devnet testing\n')
        f.write('# Transactions still recorded, but confirmation is faster\n')
        f.write('# To disable, delete this file or run disable_fast_mode()\n')
    print("✅ Fast mode ENABLED")
    print("   ⚡ Blockchain voting will be faster")
    print("   ⚠️  Use only for devnet testing")
    print(f"   📁 Config: {FAST_MODE_CONFIG}")

def disable_fast_mode():
    """Disable fast mode (full security)"""
    if FAST_MODE_CONFIG.exists():
        os.remove(FAST_MODE_CONFIG)
        print("✅ Fast mode DISABLED")
        print("   🔒 Full blockchain confirmation enabled")
    else:
        print("ℹ️  Fast mode was not enabled")

def is_fast_mode_enabled():
    """Check if fast mode is enabled"""
    return FAST_MODE_CONFIG.exists()

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == 'enable':
            enable_fast_mode()
        elif sys.argv[1] == 'disable':
            disable_fast_mode()
        elif sys.argv[1] == 'status':
            if is_fast_mode_enabled():
                print("⚡ Fast mode is ENABLED")
            else:
                print("🔒 Fast mode is DISABLED (full security)")
    else:
        print("Usage:")
        print("  python fast_mode.py enable   - Enable fast devnet mode")
        print("  python fast_mode.py disable  - Disable fast mode")
        print("  python fast_mode.py status   - Check current mode")
