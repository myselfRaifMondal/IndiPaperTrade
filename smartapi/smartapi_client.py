"""
SmartAPI Client for Angel One Broker Integration

This module provides a production-ready client for Angel One SmartAPI integration.

Features:
- Automatic TOTP generation for login
- Session token management (auth token, refresh token, feed token)
- Rate-limited API calls
- WebSocket market data streaming
- Clean interface for paper trading integration

Authentication Flow:
1. Generate TOTP from secret
2. Call generateSession() to login
3. Extract refreshToken and authToken
4. Call getfeedToken() for WebSocket
5. Initialize WebSocket connection
6. Subscribe to instruments

Usage:
    from smartapi.smartapi_client import SmartAPIClient
    
    client = SmartAPIClient()
    client.login()
    client.start_websocket()
    client.subscribe_symbols(['RELIANCE', 'TCS'])
    
    ltp = client.get_ltp('RELIANCE')
    print(f"RELIANCE LTP: {ltp}")
"""

import os
import logging
import time
from typing import Optional, Dict, List, Callable, Any
from datetime import datetime
import json

from SmartApi import SmartConnect
from SmartApi.smartWebSocketV2 import SmartWebSocketV2

from smartapi.totp_generator import TOTPGenerator
from smartapi.rate_limiter import MultiRateLimiter

logger = logging.getLogger(__name__)


class SmartAPIClient:
    """
    Production-ready Angel One SmartAPI client.
    
    Handles authentication, token management, rate limiting,
    and WebSocket market data streaming.
    
    Attributes:
        api_key: Angel One API key
        client_id: Angel One client ID
        password: Angel One password
        totp_secret: TOTP secret from QR code
        smart_api: SmartConnect instance
        ws: WebSocket instance
        rate_limiter: Multi-endpoint rate limiter
        auth_token: Current authentication token
        refresh_token: Current refresh token
        feed_token: Feed token for WebSocket
        is_logged_in: Login status
        ws_connected: WebSocket connection status
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        client_id: Optional[str] = None,
        password: Optional[str] = None,
        totp_secret: Optional[str] = None,
    ):
        """
        Initialize SmartAPI client.
        
        Credentials are loaded from environment variables if not provided.
        
        Args:
            api_key: Angel One API key (or set ANGEL_API_KEY env var)
            client_id: Angel One client ID (or set ANGEL_CLIENT_ID env var)
            password: Angel One password (or set ANGEL_PASSWORD env var)
            totp_secret: TOTP secret (or set ANGEL_TOTP_SECRET env var)
        
        Raises:
            ValueError: If required credentials are missing
        """
        # Load credentials from environment or parameters
        self.api_key = api_key or os.getenv('ANGEL_API_KEY')
        self.client_id = client_id or os.getenv('ANGEL_CLIENT_ID')
        self.password = password or os.getenv('ANGEL_PASSWORD')
        self.totp_secret = totp_secret or os.getenv('ANGEL_TOTP_SECRET')
        
        # Validate credentials
        missing = []
        if not self.api_key:
            missing.append('ANGEL_API_KEY')
        if not self.client_id:
            missing.append('ANGEL_CLIENT_ID')
        if not self.password:
            missing.append('ANGEL_PASSWORD')
        if not self.totp_secret:
            missing.append('ANGEL_TOTP_SECRET')
        
        if missing:
            raise ValueError(
                f"Missing required credentials: {', '.join(missing)}. "
                "Set environment variables or pass as parameters."
            )
        
        # Initialize TOTP generator
        self.totp_generator = TOTPGenerator(self.totp_secret)
        
        # Initialize rate limiter
        self.rate_limiter = MultiRateLimiter()
        
        # SmartAPI instances
        self.smart_api: Optional[SmartConnect] = None
        self.ws: Optional[SmartWebSocketV2] = None
        
        # Session tokens
        self.auth_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.feed_token: Optional[str] = None
        
        # Status flags
        self.is_logged_in = False
        self.ws_connected = False
        
        # Market data cache
        self._price_cache: Dict[str, Dict[str, Any]] = {}
        self._price_callbacks: List[Callable] = []
        
        logger.info("SmartAPI client initialized")
    
    def login(self) -> bool:
        """
        Authenticate with Angel One SmartAPI.
        
        Steps:
        1. Generate TOTP
        2. Create SmartConnect instance
        3. Call generateSession()
        4. Extract tokens
        5. Fetch feed token
        
        Returns:
            bool: True if login successful, False otherwise
        
        Raises:
            Exception: If login fails
        
        Example:
            >>> client = SmartAPIClient()
            >>> if client.login():
            ...     print("Login successful")
        """
        logger.info("Starting login process...")
        
        try:
            # Apply login rate limit (1 request/second)
            with self.rate_limiter.limit('login', timeout=5.0):
                
                # Step 1: Generate TOTP
                totp = self.totp_generator.generate_totp()
                logger.debug("TOTP generated")
                
                # Check if TOTP has enough time remaining
                remaining = self.totp_generator.get_remaining_seconds()
                if remaining < 5:
                    logger.warning(
                        f"TOTP expires in {remaining}s, waiting for new code..."
                    )
                    time.sleep(remaining + 1)
                    totp = self.totp_generator.generate_totp()
                
                # Step 2: Create SmartConnect instance
                self.smart_api = SmartConnect(api_key=self.api_key)
                logger.debug("SmartConnect instance created")
                
                # Step 3: Generate session (login)
                session_data = self.smart_api.generateSession(
                    clientCode=self.client_id,
                    password=self.password,
                    totp=totp
                )
                
                logger.debug(f"Session response: {session_data}")
                
                # Step 4: Extract tokens
                if session_data and session_data.get('status'):
                    data = session_data.get('data', {})
                    
                    self.auth_token = data.get('jwtToken')
                    self.refresh_token = data.get('refreshToken')
                    
                    if not self.auth_token or not self.refresh_token:
                        raise Exception("Failed to extract tokens from session")
                    
                    logger.info("✓ Session tokens obtained")
                    
                    # Step 5: Fetch feed token for WebSocket
                    self._fetch_feed_token()
                    
                    self.is_logged_in = True
                    logger.info("✓ Login successful")
                    return True
                    
                else:
                    error_msg = session_data.get('message', 'Unknown error')
                    raise Exception(f"Login failed: {error_msg}")
        
        except Exception as e:
            logger.error(f"Login failed: {e}")
            self.is_logged_in = False
            raise
    
    def _fetch_feed_token(self) -> None:
        """
        Fetch feed token for WebSocket connection.
        
        Must be called after successful login.
        
        Raises:
            Exception: If feed token fetch fails
        """
        try:
            with self.rate_limiter.limit('default', timeout=5.0):
                feed_token = self.smart_api.getfeedToken()
                
                if feed_token:
                    self.feed_token = feed_token
                    logger.info("✓ Feed token obtained")
                else:
                    raise Exception("Failed to fetch feed token")
        
        except Exception as e:
            logger.error(f"Feed token fetch failed: {e}")
            raise
    
    def get_profile(self) -> Optional[Dict]:
        """
        Get user profile information.
        
        Returns:
            dict: User profile data, or None if failed
        
        Example:
            >>> profile = client.get_profile()
            >>> print(profile['name'])
        """
        if not self.is_logged_in:
            logger.error("Not logged in")
            return None
        
        try:
            with self.rate_limiter.limit('default'):
                profile = self.smart_api.getProfile(self.refresh_token)
                logger.debug("Profile fetched successfully")
                return profile
        except Exception as e:
            logger.error(f"Failed to get profile: {e}")
            return None
    
    def get_ltp_data(self, exchange: str, trading_symbol: str, symbol_token: str) -> Optional[Dict]:
        """
        Get Last Traded Price (LTP) data for a symbol.
        
        Rate limit: 10 requests/second, 500 requests/minute
        
        Args:
            exchange: Exchange (NSE, BSE, NFO, etc.)
            trading_symbol: Trading symbol (e.g., 'RELIANCE-EQ')
            symbol_token: Symbol token from instruments list
        
        Returns:
            dict: LTP data with price information
        
        Example:
            >>> ltp_data = client.get_ltp_data('NSE', 'RELIANCE-EQ', '2885')
            >>> print(ltp_data['ltp'])
        """
        if not self.is_logged_in:
            logger.error("Not logged in")
            return None
        
        try:
            # Apply both per-second and per-minute rate limits
            with self.rate_limiter.limit('ltp'):
                with self.rate_limiter.limit('ltp_minute'):
                    
                    ltp_data = self.smart_api.ltpData(
                        exchange=exchange,
                        tradingsymbol=trading_symbol,
                        symboltoken=symbol_token
                    )
                    
                    logger.debug(f"LTP data fetched for {trading_symbol}")
                    return ltp_data
        
        except Exception as e:
            logger.error(f"Failed to get LTP data: {e}")
            return None
    
    def get_quote(self, exchange: str, trading_symbol: str, symbol_token: str) -> Optional[Dict]:
        """
        Get full market quote for a symbol.
        
        Includes: LTP, bid, ask, open, high, low, close, volume, etc.
        
        Args:
            exchange: Exchange (NSE, BSE, NFO, etc.)
            trading_symbol: Trading symbol
            symbol_token: Symbol token
        
        Returns:
            dict: Full quote data
        """
        if not self.is_logged_in:
            logger.error("Not logged in")
            return None
        
        try:
            with self.rate_limiter.limit('default'):
                quote = self.smart_api.getMarketData(
                    mode="FULL",
                    exchangeTokens={
                        exchange: [symbol_token]
                    }
                )
                
                logger.debug(f"Quote fetched for {trading_symbol}")
                return quote
        
        except Exception as e:
            logger.error(f"Failed to get quote: {e}")
            return None
    
    def start_websocket(self, on_tick_callback: Optional[Callable] = None) -> bool:
        """
        Start WebSocket connection for real-time market data.
        
        Must be called after successful login.
        
        Args:
            on_tick_callback: Optional callback function for tick data
                             Signature: callback(tick_data: dict)
        
        Returns:
            bool: True if connection successful
        
        Example:
            >>> def my_callback(tick):
            ...     print(f"Received tick: {tick}")
            >>> 
            >>> client.start_websocket(on_tick_callback=my_callback)
        """
        if not self.is_logged_in:
            logger.error("Cannot start WebSocket: Not logged in")
            return False
        
        if not self.feed_token:
            logger.error("Cannot start WebSocket: No feed token")
            return False
        
        try:
            logger.info("Starting WebSocket connection...")
            
            # Create WebSocket instance
            self.ws = SmartWebSocketV2(
                auth_token=self.auth_token,
                api_key=self.api_key,
                client_code=self.client_id,
                feed_token=self.feed_token
            )
            
            # Set up event handlers
            def on_open(ws):
                logger.info("✓ WebSocket connected")
                self.ws_connected = True
            
            def on_data(ws, message):
                logger.debug(f"WebSocket data: {message}")
                
                # Update price cache
                self._update_price_cache(message)
                
                # Call user callback if provided
                if on_tick_callback:
                    try:
                        on_tick_callback(message)
                    except Exception as e:
                        logger.error(f"Error in tick callback: {e}")
                
                # Call registered callbacks
                for callback in self._price_callbacks:
                    try:
                        callback(message)
                    except Exception as e:
                        logger.error(f"Error in price callback: {e}")
            
            def on_error(ws, error):
                logger.error(f"WebSocket error: {error}")
                self.ws_connected = False
            
            def on_close(ws):
                logger.info("WebSocket disconnected")
                self.ws_connected = False
            
            # Assign callbacks
            self.ws.on_open = on_open
            self.ws.on_data = on_data
            self.ws.on_error = on_error
            self.ws.on_close = on_close
            
            # Connect WebSocket
            self.ws.connect()
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to start WebSocket: {e}")
            self.ws_connected = False
            return False
    
    def subscribe_symbols(
        self,
        tokens: List[Dict[str, Any]],
        mode: int = 1
    ) -> bool:
        """
        Subscribe to symbols for real-time data.
        
        Args:
            tokens: List of token dictionaries
                   Example: [{"exchangeType": 1, "tokens": ["26009"]}]
            mode: Subscription mode
                 1 = LTP
                 2 = Quote
                 3 = Snap Quote
        
        Returns:
            bool: True if subscription successful
        
        Example:
            >>> tokens = [{"exchangeType": 1, "tokens": ["26009", "2885"]}]
            >>> client.subscribe_symbols(tokens, mode=1)
        """
        if not self.ws_connected:
            logger.error("Cannot subscribe: WebSocket not connected")
            return False
        
        try:
            self.ws.subscribe(correlation_id="subscribe_symbols", mode=mode, token_list=tokens)
            logger.info(f"✓ Subscribed to {len(tokens)} symbols")
            return True
        
        except Exception as e:
            logger.error(f"Subscription failed: {e}")
            return False
    
    def unsubscribe_symbols(
        self,
        tokens: List[Dict[str, Any]],
        mode: int = 1
    ) -> bool:
        """
        Unsubscribe from symbols.
        
        Args:
            tokens: List of token dictionaries
            mode: Subscription mode (same as used in subscribe)
        
        Returns:
            bool: True if unsubscribe successful
        """
        if not self.ws_connected:
            logger.error("Cannot unsubscribe: WebSocket not connected")
            return False
        
        try:
            self.ws.unsubscribe(correlation_id="unsubscribe_symbols", mode=mode, token_list=tokens)
            logger.info(f"✓ Unsubscribed from {len(tokens)} symbols")
            return True
        
        except Exception as e:
            logger.error(f"Unsubscribe failed: {e}")
            return False
    
    def _update_price_cache(self, tick_data: Dict) -> None:
        """
        Update internal price cache with tick data.
        
        Args:
            tick_data: Tick data from WebSocket
        """
        try:
            # Extract symbol token from tick data
            token = tick_data.get('token')
            if token:
                self._price_cache[token] = {
                    'ltp': tick_data.get('last_traded_price'),
                    'volume': tick_data.get('volume_trade_for_the_day'),
                    'timestamp': datetime.now(),
                    'raw_data': tick_data
                }
        except Exception as e:
            logger.error(f"Failed to update price cache: {e}")
    
    def get_cached_price(self, token: str) -> Optional[Dict]:
        """
        Get cached price data for a token.
        
        Args:
            token: Symbol token
        
        Returns:
            dict: Cached price data, or None if not found
        """
        return self._price_cache.get(token)
    
    def register_price_callback(self, callback: Callable) -> None:
        """
        Register a callback for price updates.
        
        Args:
            callback: Function to call on price update
                     Signature: callback(tick_data: dict)
        
        Example:
            >>> def my_handler(tick):
            ...     print(f"Price update: {tick}")
            >>> 
            >>> client.register_price_callback(my_handler)
        """
        if callback not in self._price_callbacks:
            self._price_callbacks.append(callback)
            logger.debug("Price callback registered")
    
    def unregister_price_callback(self, callback: Callable) -> None:
        """
        Unregister a price callback.
        
        Args:
            callback: Callback function to remove
        """
        if callback in self._price_callbacks:
            self._price_callbacks.remove(callback)
            logger.debug("Price callback unregistered")
    
    def stop_websocket(self) -> None:
        """
        Stop WebSocket connection.
        """
        if self.ws and self.ws_connected:
            try:
                self.ws.close_connection()
                self.ws_connected = False
                logger.info("✓ WebSocket stopped")
            except Exception as e:
                logger.error(f"Error stopping WebSocket: {e}")
    
    def logout(self) -> bool:
        """
        Logout and cleanup resources.
        
        Returns:
            bool: True if logout successful
        """
        try:
            # Stop WebSocket if connected
            self.stop_websocket()
            
            # Clear tokens
            self.auth_token = None
            self.refresh_token = None
            self.feed_token = None
            self.is_logged_in = False
            
            # Clear cache
            self._price_cache.clear()
            
            logger.info("✓ Logged out successfully")
            return True
        
        except Exception as e:
            logger.error(f"Logout error: {e}")
            return False
    
    def get_rate_limiter_status(self) -> Dict:
        """
        Get current rate limiter status.
        
        Returns:
            dict: Status of all rate limiters
        """
        return self.rate_limiter.get_status()
    
    def __enter__(self):
        """Context manager support."""
        self.login()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup."""
        self.logout()
        return False


if __name__ == "__main__":
    # Example usage and testing
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("=" * 70)
    print("SmartAPI Client Test")
    print("=" * 70)
    
    # Check environment variables
    required_vars = [
        'ANGEL_API_KEY',
        'ANGEL_CLIENT_ID',
        'ANGEL_PASSWORD',
        'ANGEL_TOTP_SECRET'
    ]
    
    missing = [var for var in required_vars if not os.getenv(var)]
    
    if missing:
        print(f"\n⚠️  Missing environment variables: {', '.join(missing)}")
        print("\nSet them using:")
        for var in missing:
            print(f"  export {var}='your_value_here'")
        print("\n" + "=" * 70)
        exit(1)
    
    try:
        # Test 1: Initialize client
        print("\n1. Initializing SmartAPI client...")
        client = SmartAPIClient()
        print("   ✓ Client initialized")
        
        # Test 2: Login
        print("\n2. Logging in...")
        if client.login():
            print("   ✓ Login successful")
            print(f"   Auth token: {client.auth_token[:20]}...")
            print(f"   Feed token: {client.feed_token[:20]}...")
        else:
            print("   ✗ Login failed")
            exit(1)
        
        # Test 3: Get profile
        print("\n3. Fetching profile...")
        profile = client.get_profile()
        if profile:
            print(f"   ✓ Profile fetched")
            print(f"   Client: {client.client_id}")
        
        # Test 4: Start WebSocket
        print("\n4. Starting WebSocket...")
        
        def tick_handler(tick):
            print(f"   📊 Tick: {tick}")
        
        if client.start_websocket(on_tick_callback=tick_handler):
            print("   ✓ WebSocket started")
            
            # Wait for connection
            time.sleep(2)
            
            # Test 5: Subscribe to symbols
            print("\n5. Subscribing to symbols...")
            tokens = [
                {
                    "exchangeType": 1,  # NSE
                    "tokens": ["26009"]  # RELIANCE
                }
            ]
            
            if client.subscribe_symbols(tokens, mode=1):
                print("   ✓ Subscribed to RELIANCE")
                
                # Wait for some ticks
                print("\n6. Receiving market data (10 seconds)...")
                time.sleep(10)
        
        # Test 6: Rate limiter status
        print("\n7. Rate limiter status:")
        status = client.get_rate_limiter_status()
        for endpoint, info in status.items():
            if info['available_tokens'] < info['max_requests']:
                print(f"   {endpoint}: {info['available_tokens']:.1f}/{info['max_requests']}")
        
        # Cleanup
        print("\n8. Cleaning up...")
        client.logout()
        print("   ✓ Logged out")
        
        print("\n" + "=" * 70)
        print("✓ All tests passed")
        print("=" * 70)
    
    except Exception as e:
        print(f"\n✗ Error: {e}")
        print("=" * 70)
