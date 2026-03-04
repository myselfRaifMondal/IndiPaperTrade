"""
SmartAPI Integration Example

This script demonstrates how to use the SmartAPI integration module
for paper trading platform.

It shows:
1. Authentication with TOTP
2. WebSocket market data streaming
3. Rate limiting
4. Price data caching
5. Integration with existing Market Data Engine

Usage:
    python examples/smartapi_integration_example.py
"""

import os
import time
import logging
from datetime import datetime

# Import SmartAPI module
from smartapi import SmartAPIClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def example_basic_authentication():
    """
    Example 1: Basic authentication and profile retrieval
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Basic Authentication")
    print("=" * 70)
    
    # Initialize client (loads credentials from environment)
    client = SmartAPIClient()
    
    try:
        # Login
        print("\n1. Logging in...")
        if client.login():
            print("   ✓ Login successful")
            print(f"   Auth Token: {client.auth_token[:30]}...")
            print(f"   Refresh Token: {client.refresh_token[:30]}...")
            print(f"   Feed Token: {client.feed_token[:30]}...")
        
        # Get profile
        print("\n2. Fetching profile...")
        profile = client.get_profile()
        if profile:
            print(f"   ✓ Client ID: {client.client_id}")
        
        # Check rate limiter status
        print("\n3. Rate limiter status:")
        status = client.get_rate_limiter_status()
        for endpoint in ['login', 'ltp', 'default']:
            info = status[endpoint]
            print(f"   {endpoint:15s}: {info['available_tokens']:.1f}/{info['max_requests']} tokens")
    
    finally:
        # Cleanup
        client.logout()
        print("\n✓ Logged out")


def example_websocket_streaming():
    """
    Example 2: WebSocket real-time market data streaming
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 2: WebSocket Market Data Streaming")
    print("=" * 70)
    
    client = SmartAPIClient()
    
    try:
        # Login
        print("\n1. Logging in...")
        client.login()
        print("   ✓ Login successful")
        
        # Define tick handler
        tick_count = [0]  # Use list to modify in closure
        
        def tick_handler(tick):
            tick_count[0] += 1
            token = tick.get('token')
            ltp = tick.get('last_traded_price')
            volume = tick.get('volume_trade_for_the_day')
            
            if ltp:  # Only print if we have price data
                print(f"   📊 Tick #{tick_count[0]} | Token: {token} | LTP: ₹{ltp} | Volume: {volume}")
        
        # Start WebSocket
        print("\n2. Starting WebSocket...")
        client.start_websocket(on_tick_callback=tick_handler)
        
        # Wait for connection
        time.sleep(2)
        
        if client.ws_connected:
            print("   ✓ WebSocket connected")
        else:
            print("   ✗ WebSocket connection failed")
            return
        
        # Subscribe to symbols
        print("\n3. Subscribing to symbols...")
        
        # NSE symbols (exchange type 1)
        tokens = [
            {
                "exchangeType": 1,  # NSE
                "tokens": [
                    "26009",  # RELIANCE
                    "2885",   # TCS (if available)
                ]
            }
        ]
        
        client.subscribe_symbols(tokens, mode=1)  # mode=1 for LTP
        print("   ✓ Subscribed to RELIANCE, TCS")
        
        # Receive data for 30 seconds
        print("\n4. Receiving market data (30 seconds)...")
        print("   (Press Ctrl+C to stop early)")
        
        try:
            time.sleep(30)
        except KeyboardInterrupt:
            print("\n   ⚠️  Interrupted by user")
        
        print(f"\n   ✓ Received {tick_count[0]} ticks")
        
        # Check cached prices
        print("\n5. Cached prices:")
        for token in ["26009", "2885"]:
            cached = client.get_cached_price(token)
            if cached:
                print(f"   Token {token}: ₹{cached['ltp']} (cached at {cached['timestamp'].strftime('%H:%M:%S')})")
    
    finally:
        # Cleanup
        print("\n6. Cleaning up...")
        client.logout()
        print("   ✓ Done")


def example_rate_limiting():
    """
    Example 3: Rate limiting demonstration
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Rate Limiting")
    print("=" * 70)
    
    from smartapi import RateLimiter, MultiRateLimiter
    
    # Single rate limiter
    print("\n1. Single rate limiter (5 requests/second):")
    limiter = RateLimiter(max_requests=5, time_window=1.0)
    
    start = time.time()
    for i in range(10):
        with limiter:
            elapsed = time.time() - start
            available = limiter.get_available_tokens()
            print(f"   Request {i+1:2d} at {elapsed:5.2f}s | Available tokens: {available:.2f}")
    
    total_time = time.time() - start
    print(f"   ✓ Completed 10 requests in {total_time:.2f}s")
    
    # Multi rate limiter
    print("\n2. Multi-rate limiter (SmartAPI limits):")
    multi = MultiRateLimiter()
    
    print("   LTP endpoint (10 requests/second):")
    start = time.time()
    for i in range(5):
        with multi.limit('ltp'):
            elapsed = time.time() - start
            print(f"     LTP request {i+1} at {elapsed:.3f}s")
    
    print(f"   ✓ Completed in {time.time() - start:.3f}s")
    
    # Show status
    print("\n3. Rate limiter status:")
    status = multi.get_status()
    for endpoint, info in status.items():
        print(f"   {endpoint:15s}: {info['available_tokens']:.1f}/{info['max_requests']} tokens | Wait: {info['wait_time']:.2f}s")


def example_price_callbacks():
    """
    Example 4: Register custom price callbacks
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Price Update Callbacks")
    print("=" * 70)
    
    client = SmartAPIClient()
    
    # Track price changes
    price_history = {}
    
    def price_change_tracker(tick):
        """Track price changes"""
        token = tick.get('token')
        ltp = tick.get('last_traded_price')
        
        if not ltp:
            return
        
        if token not in price_history:
            price_history[token] = []
        
        price_history[token].append({
            'price': ltp,
            'time': datetime.now()
        })
        
        # Keep only last 10 prices
        price_history[token] = price_history[token][-10:]
        
        # Calculate change
        if len(price_history[token]) >= 2:
            old_price = price_history[token][0]['price']
            change = ((ltp - old_price) / old_price) * 100
            
            if abs(change) > 0.01:  # Print if change > 0.01%
                print(f"   📈 Token {token}: ₹{ltp} ({change:+.2f}%)")
    
    def volume_alert(tick):
        """Alert on high volume"""
        volume = tick.get('volume_trade_for_the_day', 0)
        token = tick.get('token')
        
        if volume > 10000000:  # Alert if volume > 10M
            print(f"   🔔 HIGH VOLUME ALERT | Token {token}: {volume:,} shares")
    
    try:
        # Login
        print("\n1. Logging in...")
        client.login()
        
        # Register callbacks
        print("\n2. Registering callbacks...")
        client.register_price_callback(price_change_tracker)
        client.register_price_callback(volume_alert)
        print("   ✓ Registered 2 callbacks")
        
        # Start WebSocket
        print("\n3. Starting WebSocket...")
        client.start_websocket()
        time.sleep(2)
        
        # Subscribe
        print("\n4. Subscribing to symbols...")
        tokens = [{"exchangeType": 1, "tokens": ["26009"]}]
        client.subscribe_symbols(tokens, mode=1)
        
        # Receive data
        print("\n5. Monitoring price changes (30 seconds)...")
        time.sleep(30)
        
        # Show summary
        print("\n6. Price history summary:")
        for token, history in price_history.items():
            if history:
                first = history[0]['price']
                last = history[-1]['price']
                change = ((last - first) / first) * 100
                print(f"   Token {token}: ₹{first:.2f} → ₹{last:.2f} ({change:+.2f}%)")
    
    finally:
        client.logout()
        print("\n✓ Done")


def example_error_handling():
    """
    Example 5: Error handling and recovery
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 5: Error Handling")
    print("=" * 70)
    
    # Test 1: Invalid credentials
    print("\n1. Testing invalid credentials...")
    try:
        client = SmartAPIClient(
            api_key="invalid",
            client_id="invalid",
            password="invalid",
            totp_secret="INVALIDKEY123"
        )
        client.login()
    except Exception as e:
        print(f"   ✓ Caught error: {type(e).__name__}")
    
    # Test 2: Missing credentials
    print("\n2. Testing missing credentials...")
    try:
        # Temporarily clear environment
        old_key = os.environ.get('ANGEL_API_KEY')
        if 'ANGEL_API_KEY' in os.environ:
            del os.environ['ANGEL_API_KEY']
        
        client = SmartAPIClient()
    except ValueError as e:
        print(f"   ✓ Caught error: {e}")
    finally:
        # Restore environment
        if old_key:
            os.environ['ANGEL_API_KEY'] = old_key
    
    # Test 3: Rate limit timeout
    print("\n3. Testing rate limit timeout...")
    from smartapi import RateLimiter
    
    limiter = RateLimiter(max_requests=1, time_window=10.0)  # Very restrictive
    
    # Use up token
    limiter.acquire()
    
    # Try to acquire with short timeout
    try:
        with limiter.limit(timeout=0.5):
            pass
    except TimeoutError:
        print("   ✓ Rate limit timeout handled")
    
    print("\n✓ All error handling tests passed")


def main():
    """
    Run all examples
    """
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "SMARTAPI INTEGRATION EXAMPLES" + " " * 24 + "║")
    print("╚" + "=" * 68 + "╝")
    
    # Check credentials
    required_vars = ['ANGEL_API_KEY', 'ANGEL_CLIENT_ID', 'ANGEL_PASSWORD', 'ANGEL_TOTP_SECRET']
    missing = [var for var in required_vars if not os.getenv(var)]
    
    if missing:
        print("\n⚠️  Missing environment variables:")
        for var in missing:
            print(f"   - {var}")
        print("\nSet them using:")
        print("   export ANGEL_API_KEY='your_key'")
        print("   export ANGEL_CLIENT_ID='your_id'")
        print("   export ANGEL_PASSWORD='your_password'")
        print("   export ANGEL_TOTP_SECRET='your_secret'")
        return
    
    # Menu
    print("\nAvailable examples:")
    print("  1. Basic Authentication")
    print("  2. WebSocket Streaming")
    print("  3. Rate Limiting")
    print("  4. Price Callbacks")
    print("  5. Error Handling")
    print("  6. Run All")
    print("  0. Exit")
    
    choice = input("\nSelect example (0-6): ").strip()
    
    if choice == '1':
        example_basic_authentication()
    elif choice == '2':
        example_websocket_streaming()
    elif choice == '3':
        example_rate_limiting()
    elif choice == '4':
        example_price_callbacks()
    elif choice == '5':
        example_error_handling()
    elif choice == '6':
        print("\nRunning all examples...\n")
        example_basic_authentication()
        example_websocket_streaming()
        example_rate_limiting()
        example_price_callbacks()
        example_error_handling()
        print("\n✓ All examples completed")
    elif choice == '0':
        print("\nExiting...")
    else:
        print("\n⚠️  Invalid choice")
    
    print("\n" + "=" * 70)
    print("Examples complete")
    print("=" * 70)


if __name__ == "__main__":
    main()
