"""
TOTP Generator for Angel One SmartAPI Authentication

This module provides secure Time-based One-Time Password (TOTP) generation
for Angel One SmartAPI login flow.

The TOTP is generated from a secret key (QR code secret) provided by Angel One
during account setup.

Usage:
    from smartapi.totp_generator import TOTPGenerator
    
    generator = TOTPGenerator(secret_key)
    otp = generator.generate_totp()
    print(f"Current OTP: {otp}")
"""

import pyotp
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class TOTPGenerator:
    """
    Generates Time-based One-Time Passwords (TOTP) for Angel One authentication.
    
    The TOTP is a 6-digit code that changes every 30 seconds, used as a
    second factor for SmartAPI login.
    
    Attributes:
        secret_key: The base32-encoded secret key from Angel One QR code
        totp: The TOTP generator instance
    """
    
    def __init__(self, secret_key: str):
        """
        Initialize TOTP generator with secret key.
        
        Args:
            secret_key: Base32-encoded secret from Angel One QR code
                       (e.g., "ABCDEFGHIJKLMNOP")
        
        Raises:
            ValueError: If secret_key is empty or invalid
        """
        if not secret_key or not secret_key.strip():
            raise ValueError("TOTP secret key cannot be empty")
        
        self.secret_key = secret_key.strip()
        
        try:
            # Initialize pyotp TOTP with the secret key
            self.totp = pyotp.TOTP(self.secret_key)
            logger.debug("TOTP generator initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize TOTP: {e}")
            raise ValueError(f"Invalid TOTP secret key: {e}")
    
    def generate_totp(self) -> str:
        """
        Generate current TOTP code.
        
        Returns a 6-digit code valid for 30 seconds.
        
        Returns:
            str: 6-digit TOTP code (e.g., "123456")
        
        Example:
            >>> generator = TOTPGenerator("MYSECRETKEY")
            >>> otp = generator.generate_totp()
            >>> print(otp)
            "123456"
        """
        try:
            otp = self.totp.now()
            logger.debug("TOTP generated successfully")
            return otp
        except Exception as e:
            logger.error(f"Failed to generate TOTP: {e}")
            raise RuntimeError(f"TOTP generation failed: {e}")
    
    def verify_totp(self, otp: str, window: int = 1) -> bool:
        """
        Verify if a given OTP is valid.
        
        This is useful for testing or validation purposes.
        
        Args:
            otp: The OTP to verify
            window: Number of time windows to check (default: 1)
                   window=1 means check current + 1 previous + 1 future window
        
        Returns:
            bool: True if OTP is valid, False otherwise
        
        Example:
            >>> generator = TOTPGenerator("MYSECRETKEY")
            >>> otp = generator.generate_totp()
            >>> generator.verify_totp(otp)
            True
        """
        try:
            result = self.totp.verify(otp, valid_window=window)
            if result:
                logger.debug("TOTP verification successful")
            else:
                logger.warning("TOTP verification failed")
            return result
        except Exception as e:
            logger.error(f"TOTP verification error: {e}")
            return False
    
    def get_remaining_seconds(self) -> int:
        """
        Get remaining seconds until current TOTP expires.
        
        Useful for timing login attempts to avoid using an expiring code.
        
        Returns:
            int: Seconds remaining (0-30)
        
        Example:
            >>> generator = TOTPGenerator("MYSECRETKEY")
            >>> remaining = generator.get_remaining_seconds()
            >>> print(f"TOTP expires in {remaining} seconds")
        """
        import time
        current_time = int(time.time())
        time_step = 30  # TOTP time step is 30 seconds
        remaining = time_step - (current_time % time_step)
        return remaining
    
    @staticmethod
    def validate_secret_format(secret_key: str) -> bool:
        """
        Validate if a secret key is in correct base32 format.
        
        Args:
            secret_key: The secret key to validate
        
        Returns:
            bool: True if valid base32 format, False otherwise
        
        Example:
            >>> TOTPGenerator.validate_secret_format("ABCDEFGH")
            True
            >>> TOTPGenerator.validate_secret_format("12345678")
            False
        """
        try:
            # Base32 alphabet is A-Z and 2-7
            import base64
            base64.b32decode(secret_key)
            return True
        except Exception:
            return False


# Convenience function for quick TOTP generation
def generate_totp_from_secret(secret_key: str) -> Optional[str]:
    """
    Quick utility function to generate TOTP from secret key.
    
    Args:
        secret_key: Base32-encoded secret from Angel One
    
    Returns:
        str: 6-digit TOTP code, or None if generation fails
    
    Example:
        >>> from smartapi.totp_generator import generate_totp_from_secret
        >>> otp = generate_totp_from_secret("MYSECRETKEY")
        >>> print(otp)
        "123456"
    """
    try:
        generator = TOTPGenerator(secret_key)
        return generator.generate_totp()
    except Exception as e:
        logger.error(f"Failed to generate TOTP: {e}")
        return None


if __name__ == "__main__":
    # Example usage and testing
    import os
    
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("=" * 60)
    print("TOTP Generator Test")
    print("=" * 60)
    
    # Get secret from environment or use test secret
    secret = os.getenv("ANGEL_TOTP_SECRET", "")
    
    if not secret:
        print("\n⚠️  ANGEL_TOTP_SECRET not set")
        print("Usage: export ANGEL_TOTP_SECRET='your_secret_here'")
        
        # Use a test secret for demonstration
        print("\nUsing test secret for demonstration...")
        secret = "JBSWY3DPEHPK3PXP"  # Example base32 secret
    
    try:
        # Create generator
        generator = TOTPGenerator(secret)
        
        # Generate TOTP
        otp = generator.generate_totp()
        print(f"\n✓ Current TOTP: {otp}")
        
        # Check remaining time
        remaining = generator.get_remaining_seconds()
        print(f"✓ Expires in: {remaining} seconds")
        
        # Verify the OTP
        is_valid = generator.verify_totp(otp)
        print(f"✓ Verification: {'✓ Valid' if is_valid else '✗ Invalid'}")
        
        # Validate secret format
        is_valid_format = TOTPGenerator.validate_secret_format(secret)
        print(f"✓ Secret format: {'✓ Valid base32' if is_valid_format else '✗ Invalid'}")
        
        print("\n" + "=" * 60)
        print("✓ TOTP Generator working correctly")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        print("=" * 60)
