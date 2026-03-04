"""
WebSocket Market Data Engine for IndiPaperTrade

Real-time streaming market data using Angel One WebSocket API.
Provides tick-by-tick price updates with minimal latency.
"""

import logging
import threading
import time
from typing import Optional, Dict, List, Callable
from datetime import datetime
from dataclasses import dataclass
import sys
import os

# Add smartapi-python to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'smartapi-python'))

from SmartApi.smartWebSocketV2 import SmartWebSocketV2
from SmartApi import SmartConnect
from config import Settings, INSTRUMENT_TOKENS
from .market_data import PriceData

logger = logging.getLogger(__name__)


class WebSocketDataEngine:
    """
    Real-time WebSocket market data engine.
    
    Streams live tick-by-tick price updates from Angel One.
    Much faster than REST polling with no rate limits on updates.
    """
    
    def __init__(self):
        """Initialize WebSocket Data Engine."""
        logger.info("Initializing WebSocket Data Engine...")
        self.api = None
        self.ws = None
        self.price_cache: Dict[str, PriceData] = {}
        self.token_to_symbol: Dict[str, str] = {}
        self._lock = threading.Lock()
        self._running = False
        self._authenticated = False
        self._callbacks: List[Callable[[str, PriceData], None]] = []
        
        # Authentication tokens
        self.auth_token = None
        self.feed_token = None
        
    def initialize(self) -> bool:
        """
        Initialize and authenticate with Angel One API.
        
        Returns:
            True if successful
        """
        try:
            logger.info("Authenticating with Angel One for WebSocket...")
            
            # Generate TOTP
            try:
                import pyotp
                totp = pyotp.TOTP(Settings.TOTP_SECRET).now()
                logger.info(f"Generated TOTP for WebSocket")
            except Exception as e:
                logger.warning(f"TOTP generation failed: {e}")
                return False
            
            # Create API instance and login
            self.api = SmartConnect(api_key=Settings.API_KEY)
            
            session = self.api.generateSession(
                clientCode=Settings.CLIENT_ID,
                password=Settings.PASSWORD,
                totp=totp
            )
            
            if session.get('status'):
                logger.info("SmartAPI authentication successful for WebSocket")
                self.auth_token = session['data']['jwtToken']
                self.feed_token = self.api.getfeedToken()
                self._authenticated = True
                return True
            else:
                logger.error(f"WebSocket authentication failed: {session}")
                return False
                
        except Exception as e:
            logger.error(f"WebSocket initialization error: {e}")
            return False
    
    def start(self) -> None:
        """Start the WebSocket connection."""
        if not self._authenticated:
            logger.error("Cannot start WebSocket: not authenticated")
            return
        
        try:
            # Create WebSocket instance
            self.ws = SmartWebSocketV2(
                auth_token=self.auth_token,
                api_key=Settings.API_KEY,
                client_code=Settings.CLIENT_ID,
                feed_token=self.feed_token
            )
            
            # Assign callbacks
            self.ws.on_open = self._on_open
            self.ws.on_message = self._on_message
            self.ws.on_error = self._on_error
            self.ws.on_close = self._on_close
            self.ws.on_data = self._on_data_callback  # Use correct callback name
            
            # Connect in background thread
            self._running = True
            self._ws_thread = threading.Thread(target=self._run_websocket, daemon=True)
            self._ws_thread.start()
            
            logger.info("WebSocket connection initiated")
            
        except Exception as e:
            logger.error(f"Failed to start WebSocket: {e}")
            self._running = False
    
    def _run_websocket(self):
        """Run WebSocket in background thread."""
        try:
            self.ws.connect()
        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
            self._running = False
    
    def stop(self) -> None:
        """Stop the WebSocket connection."""
        self._running = False
        if self.ws and hasattr(self.ws, 'wsapp') and self.ws.wsapp:
            self.ws.wsapp.close()
        logger.info("WebSocket Data Engine stopped")
    
    def subscribe(self, symbols: List[str]) -> bool:
        """
        Subscribe to real-time price updates.
        
        Args:
            symbols: List of symbols to subscribe
            
        Returns:
            True if successful
        """
        try:
            if not self.ws:
                logger.error("WebSocket not initialized")
                return False
            
            # Build token list
            token_list = []
            nse_tokens = []
            
            for symbol in symbols:
                token_info = INSTRUMENT_TOKENS.get(symbol)
                if not token_info:
                    logger.warning(f"Token not found for {symbol}")
                    continue
                
                token = str(token_info['token'])
                nse_tokens.append(token)
                
                # Map token to symbol for reverse lookup
                with self._lock:
                    self.token_to_symbol[token] = symbol
            
            if nse_tokens:
                token_list.append({
                    "exchangeType": SmartWebSocketV2.NSE_CM,  # NSE Cash Market
                    "tokens": nse_tokens
                })
                
                # Subscribe with LTP mode for fastest updates
                logger.info(f"Subscribing to WebSocket: {', '.join(symbols)}")
                self.ws.subscribe(
                    correlation_id="indipapertrade",
                    mode=SmartWebSocketV2.LTP_MODE,
                    token_list=token_list
                )
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Subscription error: {e}")
            return False
    
    def get_price_data(self, symbol: str) -> Optional[PriceData]:
        """
        Get latest price data for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            PriceData object or None
        """
        with self._lock:
            return self.price_cache.get(symbol)
    
    def register_callback(self, callback: Callable[[str, PriceData], None]):
        """
        Register a callback for price updates.
        
        Args:
            callback: Function to call when price updates (symbol, PriceData)
        """
        self._callbacks.append(callback)
    
    def _on_open(self, wsapp):
        """Handle WebSocket connection open."""
        logger.info("WebSocket connection opened")
    
    def _on_close(self, wsapp, *args):
        """Handle WebSocket connection close."""
        logger.info("WebSocket connection closed")
    
    def _on_error(self, wsapp, error):
        """Handle WebSocket errors."""
        logger.error(f"WebSocket error: {error}")
    
    def _on_message(self, wsapp, message):
        """Handle WebSocket text messages."""
        logger.debug(f"WebSocket message: {message}")
    
    def _on_data_callback(self, wsapp, parsed_data):
        """
        Handle WebSocket parsed data (tick data).
        
        This is called by SmartWebSocketV2 AFTER it has already parsed the binary data.
        
        Args:
            wsapp: WebSocket app instance
            parsed_data: Already parsed dictionary from SmartWebSocketV2
        """
        try:
            if not parsed_data:
                return
            
            # Extract token and find symbol
            token = str(parsed_data.get('token', ''))
            with self._lock:
                symbol = self.token_to_symbol.get(token)
            
            if not symbol:
                return
            
            # Extract LTP (divide by 100 as per API format)
            ltp = parsed_data.get('last_traded_price', 0) / 100.0
            
            if ltp <= 0:
                return
            
            # Create PriceData object
            price_data = PriceData(
                symbol=symbol,
                ltp=ltp,
                timestamp=datetime.now()
            )
            
            # Add additional data if available (QUOTE/SNAP_QUOTE modes)
            if 'open_price_of_the_day' in parsed_data:
                price_data.open = parsed_data['open_price_of_the_day'] / 100.0
            if 'high_price_of_the_day' in parsed_data:
                price_data.high = parsed_data['high_price_of_the_day'] / 100.0
            if 'low_price_of_the_day' in parsed_data:
                price_data.low = parsed_data['low_price_of_the_day'] / 100.0
            if 'closed_price' in parsed_data:
                price_data.close = parsed_data['closed_price'] / 100.0
            
            # Update cache
            with self._lock:
                self.price_cache[symbol] = price_data
            
            # Notify callbacks
            for callback in self._callbacks:
                try:
                    callback(symbol, price_data)
                except Exception as e:
                    logger.error(f"Callback error: {e}")
            
            logger.debug(f"Updated {symbol}: ₹{ltp:.2f}")
            
        except Exception as e:
            logger.error(f"Error processing tick data: {e}")
