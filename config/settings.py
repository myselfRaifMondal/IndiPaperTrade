"""
Configuration and settings management for IndiPaperTrade.
Loads API credentials from environment variables and manages system settings.
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings:
    """
    Central configuration management class.
    All sensitive credentials are loaded from environment variables.
    Supports both legacy SMARTAPI_* and new ANGEL_* credential formats.
    """
    
    # New format: Angel One SmartAPI Credentials (with TOTP)
    ANGEL_API_KEY: str = os.getenv('ANGEL_API_KEY', '')
    ANGEL_CLIENT_ID: str = os.getenv('ANGEL_CLIENT_ID', '')
    ANGEL_PASSWORD: str = os.getenv('ANGEL_PASSWORD', '')
    ANGEL_TOTP_SECRET: str = os.getenv('ANGEL_TOTP_SECRET', '')
    
    # Legacy format: Angel One SmartAPI Credentials (backward compatibility)
    SMARTAPI_CLIENT_ID: str = os.getenv('SMARTAPI_CLIENT_ID', '')
    SMARTAPI_API_KEY: str = os.getenv('SMARTAPI_API_KEY', '')
    SMARTAPI_USERNAME: str = os.getenv('SMARTAPI_USERNAME', '')
    SMARTAPI_PASSWORD: str = os.getenv('SMARTAPI_PASSWORD', '')
    SMARTAPI_FEED_TOKEN: str = os.getenv('SMARTAPI_FEED_TOKEN', '')
    
    # Unified credentials - use classmethods to ensure proper evaluation
    @classmethod
    def get_api_key(cls) -> str:
        """Get API key (prefer new format, fall back to legacy)"""
        return cls.ANGEL_API_KEY or cls.SMARTAPI_API_KEY
    
    @classmethod
    def get_client_id(cls) -> str:
        """Get client ID (prefer new format, fall back to legacy)"""
        return cls.ANGEL_CLIENT_ID or cls.SMARTAPI_CLIENT_ID or cls.SMARTAPI_USERNAME
    
    @classmethod
    def get_password(cls) -> str:
        """Get password (prefer new format, fall back to legacy)"""
        return cls.ANGEL_PASSWORD or cls.SMARTAPI_PASSWORD
    
    @classmethod
    def get_totp_secret(cls) -> str:
        """Get TOTP secret (new format only)"""
        return cls.ANGEL_TOTP_SECRET
    
    @classmethod
    def get_feed_token(cls) -> str:
        """Get feed token (legacy format only)"""
        return cls.SMARTAPI_FEED_TOKEN
    
    # Legacy properties for backward compatibility
    API_KEY: str = os.getenv('ANGEL_API_KEY') or os.getenv('SMARTAPI_API_KEY', '')
    CLIENT_ID: str = os.getenv('ANGEL_CLIENT_ID') or os.getenv('SMARTAPI_CLIENT_ID') or os.getenv('SMARTAPI_USERNAME', '')
    PASSWORD: str = os.getenv('ANGEL_PASSWORD') or os.getenv('SMARTAPI_PASSWORD', '')
    TOTP_SECRET: str = os.getenv('ANGEL_TOTP_SECRET', '')
    FEED_TOKEN: str = os.getenv('SMARTAPI_FEED_TOKEN', '')
    
    # WebSocket Configuration
    WEBSOCKET_URL: str = os.getenv(
        'SMARTAPI_WEBSOCKET_URL',
        'wss://smartapisocket.angelbroking.com/'
    )
    
    # Trading Configuration
    MARKET_DATA_UPDATE_INTERVAL: float = 1.0  # seconds
    WEBSOCKET_RECONNECT_INTERVAL: float = 5.0  # seconds
    WEBSOCKET_MAX_RETRIES: int = 5
    
    # Database Configuration
    DATABASE_URL: str = os.getenv('DATABASE_URL', 'sqlite:///indipapertrade.db')
    DATABASE_PATH: str = os.getenv('DATABASE_PATH', './data/indipapertrade.db')
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE: str = os.getenv('LOG_FILE', './logs/indipapertrade.log')
    
    # Dashboard Configuration
    DASHBOARD_HOST: str = os.getenv('DASHBOARD_HOST', '127.0.0.1')
    DASHBOARD_PORT: int = int(os.getenv('DASHBOARD_PORT', 8501))  # Streamlit default
    DASHBOARD_DEBUG: bool = os.getenv('DASHBOARD_DEBUG', 'False').lower() == 'true'
    
    # Trading Account Settings
    INITIAL_CAPITAL: float = float(os.getenv('INITIAL_CAPITAL', 500000.0))  # 5 lakh rupees
    MAX_LEVERAGE: float = float(os.getenv('MAX_LEVERAGE', 2.0))
    
    # Order Simulation Settings
    ENABLE_SLIPPAGE: bool = os.getenv('ENABLE_SLIPPAGE', 'False').lower() == 'true'
    SLIPPAGE_PERCENT: float = float(os.getenv('SLIPPAGE_PERCENT', 0.01))  # 0.01%
    ENABLE_SPREAD: bool = os.getenv('ENABLE_SPREAD', 'True').lower() == 'true'
    DEFAULT_SPREAD_PERCENT: float = float(os.getenv('DEFAULT_SPREAD_PERCENT', 0.02))  # 0.02%
    
    @classmethod
    def validate_credentials(cls) -> bool:
        """
        Validate that required API credentials are set.
        Supports both new (TOTP-based) and legacy (feed token) authentication.
        Returns True if all required credentials are present.
        """
        # Check new format (with TOTP)
        has_new_format = all([
            cls.ANGEL_API_KEY,
            cls.ANGEL_CLIENT_ID,
            cls.ANGEL_PASSWORD,
            cls.ANGEL_TOTP_SECRET
        ])
        
        # Check legacy format (with feed token)
        has_legacy_format = all([
            cls.SMARTAPI_CLIENT_ID or cls.SMARTAPI_USERNAME,
            cls.SMARTAPI_API_KEY,
            cls.SMARTAPI_PASSWORD,
            cls.SMARTAPI_FEED_TOKEN
        ])
        
        return has_new_format or has_legacy_format
    
    @classmethod
    def get_credentials_summary(cls) -> dict:
        """
        Return a dictionary of credentials for debugging (without sensitive values).
        """
        return {
            'client_id': cls.SMARTAPI_CLIENT_ID[:10] + '***' if cls.SMARTAPI_CLIENT_ID else 'NOT SET',
            'username': cls.SMARTAPI_USERNAME or 'NOT SET',
            'api_key_set': bool(cls.SMARTAPI_API_KEY),
            'password_set': bool(cls.SMARTAPI_PASSWORD),
            'feed_token_set': bool(cls.SMARTAPI_FEED_TOKEN),
        }


# Instrument tokens mapping for common Indian instruments
# Format: "SYMBOL": {"token": <int>, "exchange": "NSE|NFO|MCX"}
INSTRUMENT_TOKENS = {
    # Equity Indices
    "NIFTY50": {"token": 99926000, "exchange": "NSE", "type": "index"},
    "SENSEX": {"token": 99919000, "exchange": "BSE", "type": "index"},
    
    # Sample Equity Stocks (NSE)
    "RELIANCE": {"token": 3045, "exchange": "NSE", "type": "equity"},
    "TCS": {"token": 3456, "exchange": "NSE", "type": "equity"},
    "INFY": {"token": 1270, "exchange": "NSE", "type": "equity"},
    "ICICIBANK": {"token": 1213, "exchange": "NSE", "type": "equity"},
    "HDFC": {"token": 1333, "exchange": "NSE", "type": "equity"},
    
    # Options (NFO)
    "NIFTY22500CE": {"token": None, "exchange": "NFO", "type": "option"},
    "NIFTY22500PE": {"token": None, "exchange": "NFO", "type": "option"},
}


if __name__ == "__main__":
    # For debugging: print configuration status
    print("IndiPaperTrade Configuration Status")
    print("=" * 50)
    print(f"Credentials Valid: {Settings.validate_credentials()}")
    print(f"Credentials: {Settings.get_credentials_summary()}")
    print(f"Initial Capital: ₹{Settings.INITIAL_CAPITAL:,.2f}")
    print(f"Database: {Settings.DATABASE_PATH}")
