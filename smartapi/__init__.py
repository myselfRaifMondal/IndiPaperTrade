"""
SmartAPI Integration Module

This package provides production-ready Angel One SmartAPI integration
for paper trading platforms.

Components:
- TOTPGenerator: Automatic TOTP generation for login
- RateLimiter: Rate limiting for API compliance
- SmartAPIClient: Main client for authentication and data streaming

Example Usage:
    from smartapi import SmartAPIClient
    
    # Initialize and login
    client = SmartAPIClient()
    client.login()
    
    # Start WebSocket for market data
    client.start_websocket()
    
    # Subscribe to symbols
    tokens = [{"exchangeType": 1, "tokens": ["26009"]}]
    client.subscribe_symbols(tokens)
    
    # Cleanup
    client.logout()

Environment Variables Required:
    ANGEL_API_KEY: Angel One API key
    ANGEL_CLIENT_ID: Angel One client ID
    ANGEL_PASSWORD: Angel One password
    ANGEL_TOTP_SECRET: TOTP secret from QR code
"""

from smartapi.totp_generator import TOTPGenerator, generate_totp_from_secret
from smartapi.rate_limiter import RateLimiter, MultiRateLimiter
from smartapi.smartapi_client import SmartAPIClient

__version__ = "1.0.0"
__author__ = "IndiPaperTrade Team"

__all__ = [
    'TOTPGenerator',
    'generate_totp_from_secret',
    'RateLimiter',
    'MultiRateLimiter',
    'SmartAPIClient',
]
