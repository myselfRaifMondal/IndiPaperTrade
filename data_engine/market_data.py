"""
Market Data Engine for IndiPaperTrade - REST API Based.

Simple, practical market data provider using Angel One REST API.
By default, this engine is strict and returns only real prices.
"""

import logging
import threading
import time
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import random

from SmartApi import SmartConnect
from config import Settings, INSTRUMENT_TOKENS

logger = logging.getLogger(__name__)


class Mode(Enum):
    """Subscription modes (kept for compatibility)."""
    LTP = 1
    QUOTE = 2
    FULL = 3


@dataclass
class PriceData:
    """Price data structure."""
    symbol: str
    ltp: float
    bid: float = 0.0
    ask: float = 0.0
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: int = 0
    oi: int = 0
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class MarketDataEngine:
    """
    Simple REST-based market data engine.
    
    - Fetches prices via Angel One REST API
    - Strict real-price mode by default
    - Maintains price cache
    - Thread-safe operations
    """
    
    # Base prices for simulation
    BASE_PRICES = {
        'RELIANCE': 2500.0,
        'TCS': 3800.0,
        'INFY': 1900.0,
        'HDFCBANK': 1650.0,
        'SBIN': 550.0,
    }
    
    def __init__(self):
        """Initialize Market Data Engine."""
        logger.info("Initializing Market Data Engine (REST API)...")
        self.api = None
        self.price_cache: Dict[str, PriceData] = {}
        self.price_source: Dict[str, str] = {}
        self._lock = threading.Lock()
        self._running = False
        self._authenticated = False
        self._last_fetch = {}
        self.allow_simulated_prices = Settings.ALLOW_SIMULATED_PRICES
        
    def initialize(self) -> bool:
        """
        Initialize and authenticate with Angel One API.
        
        Returns:
            True if successful
        """
        try:
            logger.info("Authenticating with Angel One...")
            
            # Import TOTP generator
            try:
                from smartapi import generate_totp_from_secret
                totp = generate_totp_from_secret(Settings.TOTP_SECRET)
                logger.info(f"Generated TOTP: {totp[:-4]}**** (length: {len(totp)})")
            except Exception as e:
                logger.warning(f"TOTP generation failed: {e}, using password as fallback")
                totp = Settings.PASSWORD
            
            # Create API instance
            self.api = SmartConnect(api_key=Settings.API_KEY)
            
            # Login
            logger.info(f"Attempting login with clientCode={Settings.CLIENT_ID}")
            session = self.api.generateSession(
                clientCode=Settings.CLIENT_ID,
                password=Settings.PASSWORD,
                totp=totp
            )
            
            if session.get('status'):
                logger.info("SmartAPI authentication successful")
                self._authenticated = True
                return True
            else:
                logger.error(f"Authentication failed: {session}")
                return False
                
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            return False
    
    def start(self) -> None:
        """Start the market data engine (no background threads needed with REST)."""
        self._running = True
        logger.info("Market Data Engine started")
    
    def stop(self) -> None:
        """Stop the market data engine."""
        self._running = False
        logger.info("Market Data Engine stopped")
    
    def subscribe(self, symbols: List[str], mode: Mode = Mode.LTP) -> bool:
        """
        Subscribe to price updates (no-op for REST, just cache symbols).
        
        Args:
            symbols: List of symbols to track
            mode: Subscription mode (ignored for REST)
            
        Returns:
            True
        """
        logger.info(f"Subscribing to {', '.join(symbols)}")
        
        # Initialize cache for these symbols
        for symbol in symbols:
            if symbol not in self.price_cache:
                # Trigger initial price fetch
                self.get_price_data(symbol)
        
        return True
    
    def get_price_data(self, symbol: str) -> Optional[PriceData]:
        """
        Get price data for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            PriceData object or None
        """
        # Return cached price if fresh (< 5 seconds old)
        with self._lock:
            if symbol in self.price_cache:
                cached = self.price_cache[symbol]
                if (datetime.now() - cached.timestamp).total_seconds() < 5:
                    return cached
        
        # Try to fetch from REST API
        price = self._fetch_rest_price(symbol)
        
        # Optional fallback to simulated price
        if price is None and self.allow_simulated_prices:
            price = self._simulate_price(symbol)
            with self._lock:
                self.price_source[symbol] = "SIMULATED"
        elif price is None:
            with self._lock:
                self.price_source[symbol] = "UNAVAILABLE"
            return None
        else:
            with self._lock:
                self.price_source[symbol] = "REAL"
        
        # Cache the price
        with self._lock:
            self.price_cache[symbol] = price
        
        return price
    
    def _fetch_rest_price(self, symbol: str) -> Optional[PriceData]:
        """
        Fetch price from Angel One REST API.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            PriceData or None if fetch fails
        """
        try:
            if not self.api or not self._authenticated:
                logger.warning("Market data API not authenticated")
                return None
            
            # Get token info
            token_info = INSTRUMENT_TOKENS.get(symbol)
            if not token_info:
                logger.warning(f"Token not found for {symbol}")
                return None
            
            token = str(token_info['token'])
            exchange, trading_symbol = self._get_exchange_and_tradingsymbol(symbol, token_info)
            
            # Rate limiting: don't fetch more than once per 2 seconds per symbol
            last_time = self._last_fetch.get(symbol, 0)
            if time.time() - last_time < 2:
                return None
            
            # Strategy 1: ltpData (primary method)
            if hasattr(self.api, 'ltpData'):
                logger.debug(
                    f"Fetching LTP for {symbol} using ltpData: exchange={exchange}, "
                    f"tradingsymbol={trading_symbol}, symboltoken={token}"
                )
                ltp_result = self.api.ltpData(exchange, trading_symbol, token)
                parsed = self._parse_ltp_response(symbol, ltp_result)
                if parsed:
                    self._last_fetch[symbol] = time.time()
                    return parsed

            # Strategy 2: getMarketData fallback
            if hasattr(self.api, 'getMarketData'):
                logger.debug(
                    f"Fetching quote for {symbol} using getMarketData: mode=LTP, "
                    f"exchangeTokens={{'{exchange}': ['{token}']}}"
                )
                quote_result = self.api.getMarketData(
                    mode='LTP',
                    exchangeTokens={exchange: [token]}
                )
                parsed = self._parse_quote_response(symbol, quote_result)
                if parsed:
                    self._last_fetch[symbol] = time.time()
                    return parsed

            logger.warning(
                f"No real quote data for {symbol}. "
                f"ltp_result_status={ltp_result.get('status') if isinstance(ltp_result, dict) else 'N/A'}, "
                f"quote_result_status={quote_result.get('status') if isinstance(quote_result, dict) else 'N/A'}"
            )
            return None
            
        except Exception as e:
            logger.warning(f"REST API error for {symbol}: {e}")
            return None

    @staticmethod
    def _get_exchange_and_tradingsymbol(symbol: str, token_info: Dict) -> Tuple[str, str]:
        """Resolve SmartAPI exchange and trading symbol."""
        exchange_code = token_info.get('exchange', 'nse_cm')
        # For ltpData API: NSE, BSE (uppercase)
        exchange = 'NSE' if exchange_code.lower().startswith('nse') else 'BSE'
        # tradingsymbol format: SYMBOL-EQ for equity
        trading_symbol = f"{symbol}-EQ"
        return exchange, trading_symbol

    @staticmethod
    def _parse_ltp_response(symbol: str, response: Dict) -> Optional[PriceData]:
        """Parse SmartAPI ltpData response into PriceData."""
        if not isinstance(response, dict) or not response.get('status'):
            return None

        data = response.get('data') or {}
        # ltpData returns 'ltp' field
        ltp = float(data.get('ltp', 0) or 0)
        if ltp <= 0:
            return None

        return PriceData(
            symbol=symbol,
            ltp=ltp,
            bid=float(data.get('bid', 0) or ltp),
            ask=float(data.get('ask', 0) or ltp),
            open=float(data.get('open', 0) or 0),
            high=float(data.get('high', 0) or 0),
            low=float(data.get('low', 0) or 0),
            close=float(data.get('close', 0) or 0),
            volume=int(data.get('volume', 0) or 0),
            timestamp=datetime.now()
        )

    @staticmethod
    def _parse_quote_response(symbol: str, response: Dict) -> Optional[PriceData]:
        """Parse SmartAPI getMarketData response into PriceData."""
        if not isinstance(response, dict) or not response.get('status'):
            return None

        # getMarketData returns 'data' with 'fetched' array
        fetched = response.get('data', {}).get('fetched', [])
        data = None
        if isinstance(fetched, list) and fetched:
            data = fetched[0]
        elif isinstance(fetched, dict):
            data = fetched

        if not isinstance(data, dict):
            return None

        ltp = float(data.get('ltp', 0) or 0)
        if ltp <= 0:
            return None

        return PriceData(
            symbol=symbol,
            ltp=ltp,
            bid=float(data.get('bid', 0) or ltp),
            ask=float(data.get('ask', 0) or ltp),
            open=float(data.get('open', 0) or 0),
            high=float(data.get('high', 0) or 0),
            low=float(data.get('low', 0) or 0),
            close=float(data.get('close', 0) or 0),
            volume=int(data.get('volume', 0) or 0),
            timestamp=datetime.now()
        )
    
    def _simulate_price(self, symbol: str) -> PriceData:
        """
        Generate simulated price for testing.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Simulated PriceData
        """
        base_price = self.BASE_PRICES.get(symbol, 1000.0)
        
        # Add random variation (±0.5%)
        variation = base_price * (random.random() - 0.5) * 0.01
        ltp = base_price + variation
        spread = ltp * 0.0001  # 0.01% spread
        
        return PriceData(
            symbol=symbol,
            ltp=round(ltp, 2),
            bid=round(ltp - spread, 2),
            ask=round(ltp + spread, 2),
            open=round(base_price * 0.99, 2),
            high=round(base_price * 1.01, 2),
            low=round(base_price * 0.98, 2),
            close=round(base_price, 2),
            volume=random.randint(1000000, 10000000),
            timestamp=datetime.now()
        )
    
    def get_all_prices(self) -> Dict[str, PriceData]:
        """Get all cached prices."""
        with self._lock:
            return dict(self.price_cache)

    def get_price_source(self, symbol: str) -> str:
        """Get latest source for a symbol price: REAL, SIMULATED, UNAVAILABLE."""
        with self._lock:
            return self.price_source.get(symbol, "UNKNOWN")
    
    def is_running(self) -> bool:
        """Check if engine is running."""
        return self._running
