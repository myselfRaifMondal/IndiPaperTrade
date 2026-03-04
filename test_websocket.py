"""
Quick test for WebSocket real-time streaming.

Tests the WebSocket data engine with live price updates.
"""

import sys
import time
import logging
from data_engine.websocket_data import WebSocketDataEngine

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Test WebSocket streaming."""
    print("\n" + "="*70)
    print("IndiPaperTrade - WebSocket Real-Time Streaming Test")
    print("="*70 + "\n")
    
    # Initialize WebSocket engine
    print("1. Initializing WebSocket engine...")
    ws_engine = WebSocketDataEngine()
    
    if not ws_engine.initialize():
        print("   ✗ WebSocket authentication failed")
        return False
    
    print("   ✓ WebSocket authenticated\n")
    
    # Start WebSocket connection
    print("2. Starting WebSocket connection...")
    ws_engine.start()
    time.sleep(2)  # Wait for connection to establish
    print("   ✓ WebSocket connected\n")
    
    # Subscribe to symbols
    symbols = ["RELIANCE", "TCS", "INFY"]
    print(f"3. Subscribing to: {', '.join(symbols)}")
    
    # Counter for received updates
    update_count = {}
    for symbol in symbols:
        update_count[symbol] = 0
    
    def on_update(symbol, price_data):
        """Callback for price updates."""
        update_count[symbol] += 1
        print(f"   📈 {symbol}: ₹{price_data.ltp:.2f} (Update #{update_count[symbol]})")
    
    # Register callback
    ws_engine.register_callback(on_update)
    
    # Subscribe
    if ws_engine.subscribe(symbols):
        print("   ✓ Subscribed successfully\n")
    else:
        print("   ✗ Subscription failed")
        return False
    
    # Monitor for 15 seconds
    print("4. Monitoring real-time updates for 15 seconds...")
    print("   (Press Ctrl+C to stop early)\n")
    
    try:
        start_time = time.time()
        while time.time() - start_time < 15:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n   Interrupted by user")
    
    # Summary
    print("\n" + "="*70)
    print("Update Summary:")
    print("="*70)
    
    total_updates = sum(update_count.values())
    for symbol, count in update_count.items():
        print(f"   {symbol}: {count} updates")
    
    print(f"\n   Total updates received: {total_updates}")
    
    if total_updates > 0:
        print("\n   ✓ WebSocket streaming working!")
        print("   ✓ Real-time prices are being received")
    else:
        print("\n   ⚠ No updates received")
        print("   Note: Market may be closed or symbols inactive")
    
    # Cleanup
    print("\n5. Stopping WebSocket...")
    ws_engine.stop()
    print("   ✓ WebSocket stopped\n")
    
    return total_updates > 0


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        sys.exit(1)
