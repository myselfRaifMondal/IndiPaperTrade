#!/usr/bin/env python3
"""
Test TOTP import and generation
"""

import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("Testing TOTP import...")
print(f"Python path: {sys.path[:3]}")

try:
    from smartapi import generate_totp_from_secret
    print("✓ TOTP module imported successfully!")
    
    # Test with a dummy secret
    from dotenv import load_dotenv
    load_dotenv()
    
    totp_secret = os.getenv('ANGEL_TOTP_SECRET', '')
    if totp_secret:
        print(f"✓ TOTP secret found in .env (length: {len(totp_secret)})")
        try:
            totp_code = generate_totp_from_secret(totp_secret)
            print(f"✓ Generated TOTP: {totp_code[:2]}**** (length: {len(totp_code)})")
        except Exception as e:
            print(f"✗ Failed to generate TOTP: {e}")
    else:
        print("✗ No TOTP secret found in .env")
        
except ImportError as e:
    print(f"✗ Failed to import TOTP module: {e}")
    print("\nChecking smartapi module...")
    try:
        import smartapi
        print(f"✓ smartapi module found at: {smartapi.__file__}")
        print(f"  Available exports: {dir(smartapi)}")
    except ImportError:
        print("✗ smartapi module not found")
        print("\nDirectory structure:")
        for item in os.listdir('.'):
            if not item.startswith('.'):
                print(f"  {item}")
except Exception as e:
    print(f"✗ Unexpected error: {e}")
    import traceback
    traceback.print_exc()
