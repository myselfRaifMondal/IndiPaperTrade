"""
Market Data Engine for IndiPaperTrade.

This module provides a real-time market data connection to Angel One SmartAPI,
fetching live prices, maintaining a price cache, and handling WebSocket feeds.

Architecture:
- SmartAPIClient: Manages connection to Angel One REST API
- WebSocketClient: Handles real-time price feed via WebSocket
- MarketDataCache: Thread-safe in-memory price storage
- MarketDataEngine: Orchestrates all market data operations
"""

import json
import logging
import threading
import time
from datetime import datetime
from typing import Dict, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum
import queue

try:
    from smartapi import SmartConnect
    from smartapi import SmartWebSocketV2
except ImportError:
    raise ImportError(
        "smartapi-python library not found. "
        "Install with: pip install smartapi-python"
    )

import websocket
from config.settings import Settings, INSTRUMENT_TOKENS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OrderType(Enum):
    """Order types supported by Angel One."""
    REGULAR = "REGULAR"
    AMO = "AMO"  # After Market Order


class Mode(Enum):
    """Data subscription modes."""
    LTP = 1      # Last Traded Price (0-second snapshot)
    QUOTE = 2    # Quote (best bid/ask)
    FULL = 3     # Full depth


@dataclass
class PriceData:
    """
    Represents real-time price data for a single instrument.
    
    Attributes:
        symbol: Trading symbol (e.g., "RELIANCE", "NIFTY50")
        ltp: Last Traded Price
        open: Opening price of the day
        high: Highest price of the day
        low: Lowest price of the day
        close: Previous closing price
        volume: Total volume traded
        bid: Best bid price
        ask: Best ask price
        timestamp: When the price was last updated
    """
    symbol: str
    ltp: float = 0.0
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: int = 0
    bid: float = 0.0
    ask: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    def get_mid_price(self) -> float:
        """Calculate mid price between bid and ask."""
        if self.bid > 0 and self.ask > 0:
            return (self.bid + self.ask) / 2.0
        return self.ltp
    
    def get_spread(self) -> float:
        """Get bid-ask spread in absolute terms."""
        if self.bid > 0 and self.ask > 0:
            return self.ask - self.bid
        return 0.0
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            'symbol': self.symbol,
            'ltp': self.ltp,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume,
            'bid': self.bid,
            'ask': self.ask,
            'timestamp': self.timestamp.isoformat(),
        }


class MarketDataCache:
    """
    Thread-safe in-memory cache for market data.
    
    Maintains the latest price data for all subscribed instruments.
    All operations are protected by locks for thread safety.
    """
    
    def __init__(self):
        """Initialize the price cache."""
        self._cache: Dict[str, PriceData] = {}
        self._lock = threading.RLock()
    
    def update(self, symbol: str, price_data: PriceData) -> None:
        """
        Update price data for a symbol.
        
        Args:
            symbol: Trading symbol
            price_data: PriceData object with latest values
        """
        with self._lock:
            self._cache[symbol] = price_data
            logger.debug(f"Cache updated: {symbol} = {price_data.ltp}")
    
    def get(self, symbol: str) -> Optional[PriceData]:
        """
        Retrieve latest price data for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            PriceData object or None if symbol not found
        """
        with self._lock:
            return self._cache.get(symbol)
    
    def get_all(self) -> Dict[str, PriceData]:
        """
        Get all cached price data.
        
        Returns:
            Dictionary of symbol -> PriceData
        """
        with self._lock:
            return dict(self._cache)
    
    def get_ltp(self, symbol: str) -> Optional[float]:
        """
        Get last traded price for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            LTP value or None if not found
        """
        with self._lock:
            data = self._cache.get(symbol)
            return data.ltp if data else None
    
    def clear(self) -> None:
        """Clear all cached data."""
        with self._lock:
            self._cache.clear()
    
    def size(self) -> int:
        """Get number of cached instruments."""
        with self._lock:
            return len(self._cache)


class SmartAPIDataFetcher:
    """
    Handles REST API calls to Angel One SmartAPI.
    
    Responsibilities:
    - Authenticate with SmartAPI
    - Fetch historical OHLC data
    - Fetch current quotes
    - Get instrument master data
    """
    
    def __init__(self):
        """Initialize SmartAPI connection."""
        self.smartapi = None
        self._authenticated = False
        self._auth_token = None
        self._feed_token = None
        
    def authenticate(self) -> bool:
        """
        Authenticate with Angel One SmartAPI.
        
        Returns:
            True if authentication successful, False otherwise
        """
        try:
            # Validate credentials
            if not Settings.validate_credentials():
                logger.error("API credentials not properly configured")
                return False
            
            # Create SmartAPI connection object
            self.smartapi = SmartConnect(api_key=Settings.SMARTAPI_API_KEY)
            
            # Attempt login
            session_data = self.smartapi.generateSession(
                clientcode=Settings.SMARTAPI_USERNAME,
                password=Settings.SMARTAPI_PASSWORD,
                totp=Settings.SMARTAPI_PASSWORD  # Some implementations use TOTP
            )
            
            if session_data['status']:
                self._auth_token = session_data['data']['jwtToken']
                self._feed_token = session_data['data']['feedToken']
                self._authenticated = True
                logger.info("SmartAPI authentication successful")
                return True
            else:
                logger.error(f"Authentication failed: {session_data.get('message', 'Unknown error')}")
                return False
                
        except Exception as e:
            logger.error(f"Error during SmartAPI authentication: {str(e)}")
            return False
    
    def get_quote(self, symbol: str) -> Optional[Dict]:
        """
        Fetch current quote (price data) for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Dictionary with price data or None on failure
        """
        try:
            if not self._authenticated or not self.smartapi:
                logger.warning("Not authenticated with SmartAPI")
                return None
            
            # Get instrument token
            token = INSTRUMENT_TOKENS.get(symbol, {}).get('token')
            if not token:
                logger.warning(f"Token not found for symbol: {symbol}")
                return None
            
            # Fetch quote
            params = {
                'mode': Mode.QUOTE.value,
                'exchangeTokens': {
                    INSTRUMENT_TOKENS[symbol]['exchange']: [str(token)]
                }
            }
            
            quote_data = self.smartapi.getQuotes(**params)
            
            if quote_data['status']:
                return quote_data['data']
            else:
                logger.warning(f"Failed to fetch quote for {symbol}: {quote_data.get('message')}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching quote for {symbol}: {str(e)}")
            return None
    
    def parse_quote_data(self, symbol: str, quote_response: Dict) -> Optional[PriceData]:
        """
        Parse quote response into PriceData object.
        
        Args:
            symbol: Trading symbol
            quote_response: Response from SmartAPI quote endpoint
            
        Returns:
            PriceData object or None on error
        """
        try:
            # Extract data from quote response
            data = quote_response.get('fetched', [{}])[0]
            
            return PriceData(
                symbol=symbol,
                ltp=float(data.get('ltp', 0.0)),
                open=float(data.get('open', 0.0)),
                high=float(data.get('high', 0.0)),
                low=float(data.get('low', 0.0)),
                close=float(data.get('close', 0.0)),
                volume=int(data.get('volume', 0)),
                bid=float(data.get('bid', 0.0)),
                ask=float(data.get('ask', 0.0)),
                timestamp=datetime.now()
            )
        except Exception as e:
            logger.error(f"Error parsing quote data for {symbol}: {str(e)}")
            return None
    
    def get_auth_token(self) -> Optional[str]:
        """Return authentication token."""
        return self._auth_token
    
    def get_feed_token(self) -> Optional[str]:
        """Return feed token for WebSocket."""
        return self._feed_token
    
    def is_authenticated(self) -> bool:
        """Check if authenticated with SmartAPI."""
        return self._authenticated


class WebSocketFeedHandler:
    """
    Handles real-time price feeds via WebSocket.
    
    Responsibilities:
    - Connect to Angel One WebSocket
    - Subscribe to instruments
    - Parse incoming price updates
    - Maintain connection and handle reconnection
    """
    
    def __init__(self, auth_token: str, feed_token: str):
        """
        Initialize WebSocket handler.
        
        Args:
            auth_token: JWT token from authentication
            feed_token: Feed token for WebSocket connection
        """
        self.auth_token = auth_token
        self.feed_token = feed_token
        self.ws = None
        self._subscribed_tokens: Dict[str, str] = {}  # token -> symbol mapping
        self._running = False
        self._price_queue: queue.Queue = queue.Queue()
        self._reconnect_attempts = 0
        self._last_heartbeat = time.time()
    
    def connect(self) -> bool:
        """
        Establish WebSocket connection to Angel One.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            logger.info("Attempting WebSocket connection to Angel One...")
            
            self.ws = SmartWebSocketV2(
                auth_token=self.auth_token,
                feed_token=self.feed_token,
                client_code=Settings.SMARTAPI_USERNAME
            )
            
            # Set up event handlers
            self.ws.on_open = self._on_open
            self.ws.on_message = self._on_message
            self.ws.on_close = self._on_close
            self.ws.on_error = self._on_error
            
            # Connect
            self.ws.connect()
            self._running = True
            self._reconnect_attempts = 0
            
            logger.info("WebSocket connection established")
            return True
            
        except Exception as e:
            logger.error(f"WebSocket connection failed: {str(e)}")
            return False
    
    def disconnect(self) -> None:
        """Disconnect from WebSocket."""
        try:
            self._running = False
            if self.ws:
                self.ws.close()
            logger.info("WebSocket disconnected")
        except Exception as e:
            logger.error(f"Error disconnecting WebSocket: {str(e)}")
    
    def subscribe(self, symbol: str, mode: Mode = Mode.LTP) -> bool:
        """
        Subscribe to price updates for a symbol.
        
        Args:
            symbol: Trading symbol
            mode: Subscription mode (LTP, QUOTE, FULL)
            
        Returns:
            True if subscription successful
        """
        try:
            token_info = INSTRUMENT_TOKENS.get(symbol)
            if not token_info or not token_info.get('token'):
                logger.warning(f"Token not found for symbol: {symbol}")
                return False
            
            token = str(token_info['token'])
            exchange = token_info['exchange']
            
            # Create subscription request
            subscription_data = {
                'mode': mode.value,
                'tokensByExchange': {
                    exchange: [token]
                }
            }
            
            # Send subscription
            if self.ws:
                self.ws.subscribe(subscription_data)
                self._subscribed_tokens[token] = symbol
                logger.info(f"Subscribed to {symbol} (token: {token})")
                return True
            else:
                logger.warning("WebSocket not connected")
                return False
                
        except Exception as e:
            logger.error(f"Error subscribing to {symbol}: {str(e)}")
            return False
    
    def unsubscribe(self, symbol: str) -> bool:
        """
        Unsubscribe from price updates for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            True if unsubscription successful
        """
        try:
            token_info = INSTRUMENT_TOKENS.get(symbol)
            if not token_info:
                return False
            
            token = str(token_info['token'])
            
            if self.ws and token in self._subscribed_tokens:
                unsubscription_data = {
                    'tokensByExchange': {
                        token_info['exchange']: [token]
                    }
                }
                self.ws.unsubscribe(unsubscription_data)
                del self._subscribed_tokens[token]
                logger.info(f"Unsubscribed from {symbol}")
                return True
                
        except Exception as e:
            logger.error(f"Error unsubscribing from {symbol}: {str(e)}")
        
        return False
    
    def _on_open(self, *args):
        """WebSocket connection opened."""
        logger.info("WebSocket opened")
    
    def _on_message(self, ws, message: str):
        """
        Handle incoming WebSocket message.
        
        Args:
            ws: WebSocket instance
            message: Raw message data
        """
        try:
            data = json.loads(message)
            self._last_heartbeat = time.time()
            
            # Queue the message for processing
            self._price_queue.put(data)
            
        except json.JSONDecodeError:
            logger.debug(f"Non-JSON message received: {message}")
        except Exception as e:
            logger.error(f"Error processing WebSocket message: {str(e)}")
    
    def _on_close(self, *args):
        """WebSocket connection closed."""
        logger.warning("WebSocket closed")
        self._running = False
    
    def _on_error(self, ws, error):
        """
        Handle WebSocket error.
        
        Args:
            ws: WebSocket instance
            error: Error message
        """
        logger.error(f"WebSocket error: {error}")
    
    def get_price_updates(self) -> List[Dict]:
        """
        Get queued price updates from WebSocket.
        
        Returns:
            List of price update dictionaries
        """
        updates = []
        try:
            while True:
                updates.append(self._price_queue.get_nowait())
        except queue.Empty:
            pass
        return updates
    
    def is_connected(self) -> bool:
        """Check if WebSocket is connected and running."""
        return self._running and self.ws is not None


class MarketDataEngine:
    """
    Main orchestrator for market data operations.
    
    This class coordinates:
    - SmartAPI REST authentication
    - WebSocket real-time feeds
    - Price caching
    - Background update threads
    - Event callbacks for price changes
    """
    
    def __init__(self):
        """Initialize the Market Data Engine."""
        self.cache = MarketDataCache()
        self.rest_client = SmartAPIDataFetcher()
        self.ws_handler: Optional[WebSocketFeedHandler] = None
        self._price_callbacks: List[Callable[[str, PriceData], None]] = []
        self._update_thread: Optional[threading.Thread] = None
        self._running = False
        self._authenticated = False
    
    def initialize(self) -> bool:
        """
        Initialize and authenticate with SmartAPI.
        
        Returns:
            True if successful, False otherwise
        """
        logger.info("Initializing Market Data Engine...")
        
        # Authenticate with REST API
        if not self.rest_client.authenticate():
            logger.error("Failed to authenticate with SmartAPI")
            return False
        
        # Initialize WebSocket handler
        auth_token = self.rest_client.get_auth_token()
        feed_token = self.rest_client.get_feed_token()
        
        if not auth_token or not feed_token:
            logger.error("Failed to obtain auth/feed tokens")
            return False
        
        self.ws_handler = WebSocketFeedHandler(auth_token, feed_token)
        
        # Connect WebSocket
        if not self.ws_handler.connect():
            logger.warning("WebSocket connection failed, will retry...")
        
        self._authenticated = True
        logger.info("Market Data Engine initialized successfully")
        return True
    
    def start(self) -> None:
        """
        Start the market data engine background processing.
        
        This spawns a thread that continuously processes price updates
        from the WebSocket and REST API.
        """
        if self._running:
            logger.warning("Market Data Engine already running")
            return
        
        self._running = True
        self._update_thread = threading.Thread(
            target=self._update_loop,
            daemon=True,
            name="MarketDataUpdateThread"
        )
        self._update_thread.start()
        logger.info("Market Data Engine started")
    
    def stop(self) -> None:
        """
        Stop the market data engine and disconnect WebSocket.
        """
        self._running = False
        
        if self.ws_handler:
            self.ws_handler.disconnect()
        
        if self._update_thread:
            self._update_thread.join(timeout=5)
        
        logger.info("Market Data Engine stopped")
    
    def subscribe(self, symbols: List[str], mode: Mode = Mode.LTP) -> bool:
        """
        Subscribe to market data for multiple symbols.
        
        Args:
            symbols: List of trading symbols
            mode: Subscription mode
            
        Returns:
            True if at least one subscription successful
        """
        if not self.ws_handler:
            logger.error("WebSocket handler not initialized")
            return False
        
        success_count = 0
        for symbol in symbols:
            if self.ws_handler.subscribe(symbol, mode):
                success_count += 1
            else:
                # Try REST API as fallback for this symbol
                self._fetch_price_rest(symbol)
        
        return success_count > 0
    
    def unsubscribe(self, symbols: List[str]) -> None:
        """
        Unsubscribe from market data for symbols.
        
        Args:
            symbols: List of trading symbols to unsubscribe
        """
        if not self.ws_handler:
            return
        
        for symbol in symbols:
            self.ws_handler.unsubscribe(symbol)
    
    def get_ltp(self, symbol: str) -> Optional[float]:
        """
        Get last traded price for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            LTP value or None if not available
        """
        return self.cache.get_ltp(symbol)
    
    def get_price_data(self, symbol: str) -> Optional[PriceData]:
        """
        Get complete price data for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            PriceData object or None if not found
        """
        return self.cache.get(symbol)
    
    def get_all_prices(self) -> Dict[str, PriceData]:
        """
        Get all cached price data.
        
        Returns:
            Dictionary of symbol -> PriceData
        """
        return self.cache.get_all()
    
    def register_price_callback(self, callback: Callable[[str, PriceData], None]) -> None:
        """
        Register a callback function for price updates.
        
        The callback will be invoked whenever a price is updated.
        
        Args:
            callback: Function with signature (symbol: str, price_data: PriceData) -> None
        """
        self._price_callbacks.append(callback)
        logger.debug(f"Registered price callback: {callback.__name__}")
    
    def _fetch_price_rest(self, symbol: str) -> None:
        """
        Fetch price data via REST API (fallback for WebSocket).
        
        Args:
            symbol: Trading symbol
        """
        try:
            quote_response = self.rest_client.get_quote(symbol)
            if quote_response:
                price_data = self.rest_client.parse_quote_data(symbol, quote_response)
                if price_data:
                    self.cache.update(symbol, price_data)
                    self._invoke_callbacks(symbol, price_data)
        except Exception as e:
            logger.debug(f"Error fetching REST price for {symbol}: {str(e)}")
    
    def _update_loop(self) -> None:
        """
        Background thread that continuously processes price updates.
        
        This thread:
        1. Processes incoming WebSocket messages
        2. Updates price cache
        3. Invokes registered callbacks
        4. Periodically retries REST API
        """
        rest_fetch_interval = Settings.MARKET_DATA_UPDATE_INTERVAL * 10  # Every 10 cycles
        cycle_count = 0
        
        while self._running:
            try:
                # Process WebSocket updates
                if self.ws_handler:
                    updates = self.ws_handler.get_price_updates()
                    for update in updates:
                        self._process_price_update(update)
                
                # Periodically fetch via REST API
                cycle_count += 1
                if cycle_count % int(rest_fetch_interval / Settings.MARKET_DATA_UPDATE_INTERVAL) == 0:
                    self._periodic_rest_fetch()
                
                # Sleep to avoid busy waiting
                time.sleep(Settings.MARKET_DATA_UPDATE_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error in update loop: {str(e)}")
                time.sleep(1)
    
    def _process_price_update(self, update: Dict) -> None:
        """
        Process a single price update from WebSocket.
        
        Args:
            update: Dictionary with price data
        """
        try:
            # Extract symbol and price data from update
            # This depends on SmartAPI's exact response format
            symbol = update.get('symbol')
            if not symbol:
                return
            
            price_data = PriceData(
                symbol=symbol,
                ltp=float(update.get('ltp', 0.0)),
                open=float(update.get('o', 0.0)),
                high=float(update.get('h', 0.0)),
                low=float(update.get('l', 0.0)),
                close=float(update.get('c', 0.0)),
                volume=int(update.get('v', 0)),
                bid=float(update.get('bid', 0.0)),
                ask=float(update.get('ask', 0.0)),
                timestamp=datetime.now()
            )
            
            self.cache.update(symbol, price_data)
            self._invoke_callbacks(symbol, price_data)
            
        except Exception as e:
            logger.debug(f"Error processing price update: {str(e)}")
    
    def _periodic_rest_fetch(self) -> None:
        """
        Periodically fetch prices via REST API for all subscribed symbols.
        
        This serves as a fallback to WebSocket and ensures we always
        have current prices even if WebSocket has issues.
        """
        try:
            all_prices = self.cache.get_all()
            for symbol in all_prices.keys():
                self._fetch_price_rest(symbol)
        except Exception as e:
            logger.debug(f"Error in periodic REST fetch: {str(e)}")
    
    def _invoke_callbacks(self, symbol: str, price_data: PriceData) -> None:
        """
        Invoke all registered price callbacks.
        
        Args:
            symbol: Trading symbol
            price_data: Updated price data
        """
        for callback in self._price_callbacks:
            try:
                callback(symbol, price_data)
            except Exception as e:
                logger.error(f"Error invoking price callback: {str(e)}")
    
    def is_authenticated(self) -> bool:
        """Check if engine is authenticated."""
        return self._authenticated
    
    def is_running(self) -> bool:
        """Check if engine is running."""
        return self._running


# Example usage and testing
if __name__ == "__main__":
    # Configure logging for demo
    logging.basicConfig(level=logging.DEBUG)
    
    # Create engine
    engine = MarketDataEngine()
    
    # Try to initialize (will fail without proper credentials)
    if engine.initialize():
        logger.info("Engine initialized successfully")
        
        # Register a callback to print price updates
        def on_price_update(symbol: str, price_data: PriceData):
            logger.info(f"{symbol}: {price_data.ltp} (bid:{price_data.bid}, ask:{price_data.ask})")
        
        engine.register_price_callback(on_price_update)
        
        # Start engine
        engine.start()
        
        # Subscribe to some instruments
        symbols = ["RELIANCE", "TCS", "INFY"]
        engine.subscribe(symbols)
        
        # Run for 30 seconds
        try:
            time.sleep(30)
        except KeyboardInterrupt:
            pass
        
        # Stop engine
        engine.stop()
    else:
        logger.error("Failed to initialize engine (API credentials may not be set)")
