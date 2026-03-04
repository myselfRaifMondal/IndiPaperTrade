#!/usr/bin/env python3
"""
Quick test of the Order Simulation Engine
"""

import sys
import os
import time

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Test TOTP availability before importing data_engine
print("Checking TOTP availability...")
try:
    from smartapi import generate_totp_from_secret
    print("✓ TOTP module available")
except ImportError as e:
    print(f"✗ TOTP module not available: {e}")

from execution_engine import OrderSimulator, OrderSide
from data_engine import MarketDataEngine

def main():
    print("=" * 60)
    print("Order Simulation Engine - Quick Test")
    print("=" * 60)
    
    # Initialize Market Data Engine
    print("\n1. Initializing Market Data Engine...")
    data_engine = MarketDataEngine()
    print("   - Created MarketDataEngine instance")
    initialized = data_engine.initialize()
    if not initialized:
        print("   ✗ Initialization failed")
        print("   ✗ Real market data authentication failed. Aborting test.")
        sys.exit(1)
    print("   - Initialized")
    data_engine.start()
    print("   - Engine started")
    
    # Subscribe to symbols
    print("\n2. Subscribing to RELIANCE and TCS...")
    result = data_engine.subscribe(["RELIANCE", "TCS"])
    print(f"   Subscription result: {result}")
    print("   Note: REST real-price mode is enabled (no simulation fallback)")
    
    # Wait for price data (max 10 seconds)
    print("3. Waiting for price data (max 10 seconds)...")
    print("   (Checking every 0.5 seconds...)")
    max_wait = 10
    start_time = time.time()
    data_received = False
    check_count = 0
    
    while (time.time() - start_time) < max_wait:
        check_count += 1
        if check_count % 4 == 0:  # Print every 2 seconds
            print(f"   ... still waiting ({int(time.time() - start_time)}s elapsed)")
        
        reliance_data = data_engine.get_price_data("RELIANCE")
        tcs_data = data_engine.get_price_data("TCS")
        
        if (reliance_data and reliance_data.ltp) or (tcs_data and tcs_data.ltp):
            data_received = True
            break
        time.sleep(0.5)
    
    elapsed = time.time() - start_time
    print(f"   Waited {elapsed:.1f} seconds - {'Data received' if data_received else 'Timeout, continuing anyway'}")
    elapsed = time.time() - start_time
    print(f"   Waited {elapsed:.1f} seconds - {'Data received' if data_received else 'Timeout, continuing anyway'}")
    
    # Check if we have price data
    reliance_data = data_engine.get_price_data("RELIANCE")
    tcs_data = data_engine.get_price_data("TCS")
    
    if reliance_data and reliance_data.ltp:
        print(f"   ✓ RELIANCE LTP: ₹{reliance_data.ltp:.2f} ({data_engine.get_price_source('RELIANCE')})")
    else:
        print("   ✗ No real price data for RELIANCE")
        
    if tcs_data and tcs_data.ltp:
        print(f"   ✓ TCS LTP: ₹{tcs_data.ltp:.2f} ({data_engine.get_price_source('TCS')})")
    else:
        print("   ✗ No real price data for TCS")

    if not ((reliance_data and reliance_data.ltp) and (tcs_data and tcs_data.ltp)):
        print("\n   ✗ Real prices unavailable. Failing test (simulation disabled by design).")
        data_engine.stop()
        sys.exit(1)
    
    # Initialize Order Simulator
    print("\n4. Initializing Order Simulator...")
    simulator = OrderSimulator(
        data_engine=data_engine,
        enable_slippage=True,
        slippage_percent=0.01,
        enable_spread=True,
        spread_percent=0.02
    )
    print("   ✓ Order Simulator initialized")
    
    # Place a market order
    print("\n5. Placing market order: BUY 10 RELIANCE...")
    try:
        order = simulator.place_market_order("RELIANCE", OrderSide.BUY, 10)
        print(f"   ✓ Order placed")
        print(f"   - Order ID: {order.order_id}")
        print(f"   - Status: {order.status.value}")
        print(f"   - Filled quantity: {order.filled_quantity}")
        if order.filled_price:
            print(f"   - Filled price: ₹{order.filled_price:.2f}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Place a limit order
    print("\n6. Placing limit order: SELL 5 TCS @ ₹3500.00...")
    try:
        limit_order = simulator.place_limit_order("TCS", OrderSide.SELL, 5, 3500.0)
        print(f"   ✓ Limit order placed")
        print(f"   - Order ID: {limit_order.order_id}")
        print(f"   - Status: {limit_order.status.value}")
        print(f"   - Limit price: ₹{limit_order.price:.2f}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Start background processing
    print("\n7. Starting background processing for limit orders...")
    simulator.start()
    print("   ✓ Background processing started")
    
    # Let it run for a moment
    time.sleep(1)
    
    # Get statistics
    print("\n8. Order statistics:")
    stats = simulator.get_statistics()
    print(f"   - Total orders: {stats['total_orders']}")
    print(f"   - Filled orders: {stats['filled_orders']}")
    print(f"   - Pending orders: {stats['pending_orders']}")
    print(f"   - Cancelled orders: {stats['cancelled_orders']}")
    print(f"   - Average slippage: {stats['avg_slippage']:.4f}%")
    print(f"   - Average spread: {stats['avg_spread']:.4f}%")
    
    # Show execution reports
    print("\n9. Execution reports:")
    executions = simulator.get_executions()
    if executions:
        for i, report in enumerate(executions, 1):
            print(f"   {i}. {report.symbol} {report.side.value} "
                  f"{report.quantity} @ ₹{report.price:.2f} "
                  f"(slippage: {report.slippage:.4f}%, spread: {report.spread:.4f}%)")
    else:
        print("   (No executions)")
    
    # Cleanup
    print("\n10. Cleaning up...")
    simulator.stop()
    data_engine.stop()
    print("   ✓ All resources cleaned up")
    
    print("\n" + "=" * 60)
    print("✓ Quick test completed successfully!")
    print("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
