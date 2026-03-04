"""
Simple REST-based Market Data Provider for IndiPaperTrade.

This provider:
- Fetches quotes via REST API when available
- Falls back to simulated prices
- No WebSocket complexity
- Thread-safe caching
"""

import logging
import time
from typing import Optional, Dict
from dataclasses import dataclass
from datetime import datetime
import random

from SmartApi import SmartConnect
from config import Settings, INSTRUMENT_TOKENS

logger = logging.getLogger(__name__)


@dataclass
class Price:
    """Simple price data structure."""
    symbol: str
    ltp: float  # Last Traded Price
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: int = 0
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class SimpleMarketDataProvider:
    """
    Simple REST-based market data provider.
    Uses REST API with fallback to simulated prices.
    """
    
    def __init__(self):
        """Initialize the provider."""
        self.api = None
        self.price_cache: Dict[str, Price] = {}
        self.enable_simulation = False  # Set to True to use only simulated prices
        self._last_fetch_time = {}
        
    def authenticate(self) -> bool:
        """Authenticate with Angel One API."""
        try:
            logger.info("Initializing Simple Market Data Provider")
            from smartapi import generate_totp_from_secret
            
            # Generate TOTP
            totp = generate_totp_from_secret(Settings.TOTP_SECRET)
            logger.info(f"Generated TOTP: {totp[:-4]}**** (length: {len(totp)})")
            
            # Create API instance
            self.api = SmartConnect(
                api_key=Settings.API_KEY,
                access_token=None,
                refresh_token=None
            )
            
            # Login
            logger.info(f"Attempting login with clientCode={Settings.CLIENT_ID}, totp_code=generated")
            session = self.api.generateSession(
                clientcode=Settings.CLIENT_ID,
                password=Settings.PASSWORD,
                totp=totp
            )
            
            if session.get('status'):
                logger.info("Authentication successful")
                return True
            else:
                logger.error(f"Authentication failed: {session}")
                return False
                
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False
    
    def get_price(self, symbol: str, use_rest: bool = True) -> Optional[Price]:
        """
        Get price for a symbol.
        
        Args:
            symbol: Trading symbol (e.g., "RELIANCE")
            use_rest: Try REST API first, fall back to simulation
            
        Returns:
            Price object or None
        """
        # Return cached price if recent
        if symbol in self.price_cache:
            cached = self.price_cache[symbol]
            if (datetime.now() - cached.timestamp).total_seconds() < 5:
                return cached
        
        # Try REST API if enabled
        if use_rest and self.api and not self.enable_simulation:
            try:
                price = self._fetch_rest_price(symbol)
                if price:
                    self.price_cache[symbol] = price
                    return price
            except Exception as e:
                logger.debug(f"REST API fetch failed for {symbol}: {e}")
        
        # Fall back to simulated price
        price = self._simulate_price(symbol)
        self.price_cache[symbol] = price
        return price
    
    def _fetch_rest_price(self, symbol: str) -> Optional[Price]:
        """Fetch price via REST API."""
        try:
            token_info = INSTRUMENT_TOKENS.get(symbol)
            if not token_info:
                return None
            
            # Angel One REST API for quotes
            quote_data = self.api.getQuote(
                mode='LTP',
                exchangeTokens={
                    'NSE': [str(token_info['token'])]
                }
            )
            
            if quote_data and quote_data.get('status'):
                fetches = quote_data.get('fetched', [])
                if fetches:
                    data = fetches[0]
                    return Price(
                        symbol=symbol,
                        ltp=float(data.get('ltp', 0)),
                        open=float(data.get('open', 0)),
                        high=float(data.get('high', 0)),
                        low=float(data.get('low', 0)),
                        close=float(data.get('close', 0)),
                        volume=int(data.get('volume', 0)),
                        timestamp=datetime.now()
                    )
            
            return None
            
        except Exception as e:
            logger.debug(f"REST quote fetch error: {e}")
            return None
    
    def _simulate_price(self, symbol: str) -> Price:
        """Generate a simulated price for testing."""
        # Use a base price for each symbol
        base_prices = {
            'RELIANCE': 2500.0,
            'TCS': 3800.0,
            'INFY': 1900.0,
            'HDFCBANK': 1650.0,
            'SBIN': 550.0,
        }
        
        base_price = base_prices.get(symbol, 1000.0)
        
        # Add small random variation (±0.5%)
        variation = base_price * (random.random() - 0.5) * 0.01
        ltp = base_price + variation
        
        return Price(
            symbol=symbol,
            ltp=round(ltp, 2),
            open=round(base_price * 0.99, 2),
            high=round(base_price * 1.01, 2),
            low=round(base_price * 0.98, 2),
            close=round(base_price, 2),
            volume=random.randint(1000000, 10000000),
            timestamp=datetime.now()
        )
    
    def get_multiple_prices(self, symbols: list) -> Dict[str, Price]:
        """Get prices for multiple symbols."""
        prices = {}
        for symbol in symbols:
            price = self.get_price(symbol)
            if price:
                prices[symbol] = price
        return prices
    
    def stop(self):
        """Stop the provider (cleanup if needed)."""
        pass


# Global instance
_provider = None


def get_market_data_provider() -> SimpleMarketDataProvider:
    """Get or create the global market data provider."""
    global _provider
    if _provider is None:
        _provider = SimpleMarketDataProvider()
    return _provider
