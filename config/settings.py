"""
Configuration and settings management for IndiPaperTrade.
Loads API credentials from environment variables and manages system settings.
"""

import os
from typing import Optional


class Settings:
    """
    Central configuration management class.
    All sensitive credentials are loaded from environment variables.
    """
    
    # Angel One SmartAPI Credentials
    SMARTAPI_CLIENT_ID: str = os.getenv('SMARTAPI_CLIENT_ID', '')
    SMARTAPI_API_KEY: str = os.getenv('SMARTAPI_API_KEY', '')
    SMARTAPI_USERNAME: str = os.getenv('SMARTAPI_USERNAME', '')
    SMARTAPI_PASSWORD: str = os.getenv('SMARTAPI_PASSWORD', '')
    
    # SmartAPI Endpoints
    SMARTAPI_FEED_TOKEN: str = os.getenv('SMARTAPI_FEED_TOKEN', '')
    
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
        Returns True if all required credentials are present.
        """
        required_fields = [
            cls.SMARTAPI_CLIENT_ID,
            cls.SMARTAPI_API_KEY,
            cls.SMARTAPI_USERNAME,
            cls.SMARTAPI_PASSWORD,
            cls.SMARTAPI_FEED_TOKEN,
        ]
        return all(field for field in required_fields)
    
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
