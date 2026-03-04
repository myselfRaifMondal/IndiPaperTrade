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
    data_engine.initialize()
    data_engine.start()
    
    # Subscribe to symbols
    print("2. Subscribing to RELIANCE and TCS...")
    data_engine.subscribe(["RELIANCE", "TCS"])
    
    # Wait for price data
    print("3. Waiting for price data (3 seconds)...")
    time.sleep(3)
    
    # Check if we have price data
    reliance_data = data_engine.get_price_data("RELIANCE")
    tcs_data = data_engine.get_price_data("TCS")
    
    if reliance_data and reliance_data.ltp:
        print(f"   ✓ RELIANCE LTP: ₹{reliance_data.ltp:.2f}")
    else:
        print("   ✗ No price data for RELIANCE")
        
    if tcs_data and tcs_data.ltp:
        print(f"   ✓ TCS LTP: ₹{tcs_data.ltp:.2f}")
    else:
        print("   ✗ No price data for TCS")
    
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
        print(f"   ✓ Order placed successfully")
        print(f"   - Order ID: {order.order_id}")
        print(f"   - Status: {order.status.value}")
        print(f"   - Filled quantity: {order.filled_quantity}")
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
    for i, report in enumerate(executions, 1):
        print(f"   {i}. {report.symbol} {report.side.value} "
              f"{report.quantity} @ ₹{report.price:.2f} "
              f"(slippage: {report.slippage:.4f}%, spread: {report.spread:.4f}%)")
    
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
