"""
Order Simulator Integration Example

This script demonstrates how to use the Order Simulation Engine
with the Market Data Engine for paper trading.

Features demonstrated:
1. Market order execution
2. Limit order execution
3. Slippage simulation
4. Spread simulation
5. Order callbacks
6. Order status tracking

Usage:
    python examples/order_simulator_example.py
"""

import os
import time
import logging
from datetime import datetime

# Import modules
from execution_engine import OrderSimulator, OrderSide, OrderStatus
from data_engine import MarketDataEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def example_market_orders():
    """
    Example 1: Market Order Execution
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Market Order Execution")
    print("=" * 70)
    
    # Initialize engines
    print("\n1. Initializing engines...")
    data_engine = MarketDataEngine()
    data_engine.initialize()
    data_engine.start()
    
    # Subscribe to symbols
    data_engine.subscribe(["RELIANCE", "TCS", "INFY"])
    time.sleep(3)  # Wait for price data
    
    # Initialize order simulator
    simulator = OrderSimulator(
        data_engine=data_engine,
        enable_slippage=True,
        slippage_percent=0.01,
        enable_spread=True,
        spread_percent=0.02
    )
    
    print("   ✓ Engines initialized")
    
    # Place market orders
    print("\n2. Placing market orders...")
    
    # BUY order
    buy_order = simulator.place_market_order(
        symbol="RELIANCE",
        side=OrderSide.BUY,
        quantity=10
    )
    print(f"   ✓ BUY order placed: {buy_order.order_id[:8]}...")
    print(f"     Status: {buy_order.status.value}")
    print(f"     Filled price: ₹{buy_order.filled_price:.2f}")
    
    # SELL order
    sell_order = simulator.place_market_order(
        symbol="TCS",
        side=OrderSide.SELL,
        quantity=5
    )
    print(f"   ✓ SELL order placed: {sell_order.order_id[:8]}...")
    print(f"     Status: {sell_order.status.value}")
    print(f"     Filled price: ₹{sell_order.filled_price:.2f}")
    
    # Show statistics
    print("\n3. Execution statistics:")
    stats = simulator.get_statistics()
    print(f"   Total orders: {stats['total_orders']}")
    print(f"   Filled orders: {stats['filled_orders']}")
    print(f"   Average slippage: {stats['avg_slippage']:.4f}%")
    print(f"   Average spread: {stats['avg_spread']:.4f}%")
    
    # Cleanup
    data_engine.stop()
    print("\n✓ Example complete")


def example_limit_orders():
    """
    Example 2: Limit Order Execution
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Limit Order Execution")
    print("=" * 70)
    
    # Initialize engines
    print("\n1. Initializing engines...")
    data_engine = MarketDataEngine()
    data_engine.initialize()
    data_engine.start()
    data_engine.subscribe(["RELIANCE"])
    time.sleep(3)
    
    simulator = OrderSimulator(
        data_engine=data_engine,
        enable_slippage=False,
        enable_spread=True
    )
    
    # Start order processing
    simulator.start()
    print("   ✓ Order processor started")
    
    # Get current price
    price_data = data_engine.get_price_data("RELIANCE")
    current_price = price_data.ltp if price_data else 2500.0
    print(f"   Current price: ₹{current_price:.2f}")
    
    # Place limit orders
    print("\n2. Placing limit orders...")
    
    # BUY limit below current price (should execute when price drops)
    buy_limit = simulator.place_limit_order(
        symbol="RELIANCE",
        side=OrderSide.BUY,
        quantity=10,
        price=current_price - 10.0  # 10 rupees below
    )
    print(f"   ✓ BUY limit order: ₹{buy_limit.price:.2f}")
    print(f"     Status: {buy_limit.status.value}")
    
    # SELL limit above current price (should execute when price rises)
    sell_limit = simulator.place_limit_order(
        symbol="RELIANCE",
        side=OrderSide.SELL,
        quantity=5,
        price=current_price + 10.0  # 10 rupees above
    )
    print(f"   ✓ SELL limit order: ₹{sell_limit.price:.2f}")
    print(f"     Status: {sell_limit.status.value}")
    
    # Monitor orders
    print("\n3. Monitoring limit orders (30 seconds)...")
    print("   (Orders will execute if price conditions are met)")
    
    for i in range(30):
        time.sleep(1)
        
        # Check buy limit
        buy_status = simulator.get_order_status(buy_limit.order_id)
        if buy_status == OrderStatus.FILLED:
            order = simulator.get_order(buy_limit.order_id)
            print(f"   ✓ BUY limit FILLED @ ₹{order.filled_price:.2f}")
            break
        
        # Check sell limit
        sell_status = simulator.get_order_status(sell_limit.order_id)
        if sell_status == OrderStatus.FILLED:
            order = simulator.get_order(sell_limit.order_id)
            print(f"   ✓ SELL limit FILLED @ ₹{order.filled_price:.2f}")
            break
        
        if (i + 1) % 5 == 0:
            print(f"   ... waiting ({i + 1}s)")
    
    # Final status
    print("\n4. Final order status:")
    print(f"   BUY limit: {simulator.get_order_status(buy_limit.order_id).value}")
    print(f"   SELL limit: {simulator.get_order_status(sell_limit.order_id).value}")
    
    # Cleanup
    simulator.stop()
    data_engine.stop()
    print("\n✓ Example complete")


def example_order_callbacks():
    """
    Example 3: Order Execution Callbacks
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Order Execution Callbacks")
    print("=" * 70)
    
    # Initialize engines
    print("\n1. Initializing engines...")
    data_engine = MarketDataEngine()
    data_engine.initialize()
    data_engine.start()
    data_engine.subscribe(["RELIANCE", "TCS"])
    time.sleep(3)
    
    simulator = OrderSimulator(data_engine=data_engine)
    
    # Define callback
    execution_count = [0]  # Use list for closure
    
    def on_execution(report):
        """Callback for order executions"""
        execution_count[0] += 1
        print(f"\n   📊 Execution #{execution_count[0]}:")
        print(f"      Symbol: {report.symbol}")
        print(f"      Side: {report.side.value}")
        print(f"      Quantity: {report.quantity}")
        print(f"      Price: ₹{report.price:.2f}")
        print(f"      Slippage: {report.slippage:.4f}%")
        print(f"      Time: {report.timestamp.strftime('%H:%M:%S')}")
    
    # Register callback
    simulator.register_execution_callback(on_execution)
    print("   ✓ Callback registered")
    
    # Place multiple orders
    print("\n2. Placing multiple orders...")
    
    symbols = ["RELIANCE", "TCS", "RELIANCE"]
    for i, symbol in enumerate(symbols, 1):
        order = simulator.place_market_order(
            symbol=symbol,
            side=OrderSide.BUY,
            quantity=10
        )
        print(f"   Order {i}: {symbol}")
        time.sleep(1)
    
    print(f"\n3. Total executions: {execution_count[0]}")
    
    # Cleanup
    data_engine.stop()
    print("\n✓ Example complete")


def example_order_cancellation():
    """
    Example 4: Order Cancellation
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Order Cancellation")
    print("=" * 70)
    
    # Initialize engines
    print("\n1. Initializing engines...")
    data_engine = MarketDataEngine()
    data_engine.initialize()
    data_engine.start()
    data_engine.subscribe(["RELIANCE"])
    time.sleep(3)
    
    simulator = OrderSimulator(data_engine=data_engine)
    
    # Get current price
    price_data = data_engine.get_price_data("RELIANCE")
    current_price = price_data.ltp if price_data else 2500.0
    
    # Place limit order far from current price
    print("\n2. Placing limit order (won't execute immediately)...")
    order = simulator.place_limit_order(
        symbol="RELIANCE",
        side=OrderSide.BUY,
        quantity=10,
        price=current_price - 100.0  # Far below current price
    )
    print(f"   Order ID: {order.order_id[:8]}...")
    print(f"   Status: {order.status.value}")
    print(f"   Limit price: ₹{order.price:.2f}")
    print(f"   Current price: ₹{current_price:.2f}")
    
    # Wait a bit
    print("\n3. Waiting 3 seconds...")
    time.sleep(3)
    
    # Cancel order
    print("\n4. Cancelling order...")
    if simulator.cancel_order(order.order_id):
        print(f"   ✓ Order cancelled")
        print(f"   Status: {simulator.get_order_status(order.order_id).value}")
    else:
        print(f"   ✗ Failed to cancel")
    
    # Try to cancel again (should fail)
    print("\n5. Trying to cancel again...")
    if simulator.cancel_order(order.order_id):
        print(f"   ✓ Order cancelled")
    else:
        print(f"   ✗ Cannot cancel (already cancelled)")
    
    # Cleanup
    data_engine.stop()
    print("\n✓ Example complete")


def example_slippage_comparison():
    """
    Example 5: Slippage and Spread Comparison
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 5: Slippage and Spread Comparison")
    print("=" * 70)
    
    # Initialize engines
    print("\n1. Initializing data engine...")
    data_engine = MarketDataEngine()
    data_engine.initialize()
    data_engine.start()
    data_engine.subscribe(["RELIANCE"])
    time.sleep(3)
    
    # Get current price
    price_data = data_engine.get_price_data("RELIANCE")
    current_price = price_data.ltp if price_data else 2500.0
    print(f"   Current price: ₹{current_price:.2f}")
    
    # Test 1: No slippage, no spread
    print("\n2. No slippage, no spread:")
    sim1 = OrderSimulator(
        data_engine=data_engine,
        enable_slippage=False,
        enable_spread=False
    )
    order1 = sim1.place_market_order("RELIANCE", OrderSide.BUY, 10)
    print(f"   Execution price: ₹{order1.filled_price:.2f}")
    print(f"   Difference: ₹{abs(order1.filled_price - current_price):.2f}")
    
    # Test 2: With slippage only
    print("\n3. With slippage (0.01%):")
    sim2 = OrderSimulator(
        data_engine=data_engine,
        enable_slippage=True,
        slippage_percent=0.01,
        enable_spread=False
    )
    order2 = sim2.place_market_order("RELIANCE", OrderSide.BUY, 10)
    print(f"   Execution price: ₹{order2.filled_price:.2f}")
    print(f"   Difference: ₹{abs(order2.filled_price - current_price):.2f}")
    
    # Test 3: With spread only
    print("\n4. With spread (0.02%):")
    sim3 = OrderSimulator(
        data_engine=data_engine,
        enable_slippage=False,
        enable_spread=True,
        spread_percent=0.02
    )
    order3 = sim3.place_market_order("RELIANCE", OrderSide.BUY, 10)
    print(f"   Execution price: ₹{order3.filled_price:.2f}")
    print(f"   Difference: ₹{abs(order3.filled_price - current_price):.2f}")
    
    # Test 4: With both
    print("\n5. With slippage and spread:")
    sim4 = OrderSimulator(
        data_engine=data_engine,
        enable_slippage=True,
        slippage_percent=0.01,
        enable_spread=True,
        spread_percent=0.02
    )
    order4 = sim4.place_market_order("RELIANCE", OrderSide.BUY, 10)
    print(f"   Execution price: ₹{order4.filled_price:.2f}")
    print(f"   Difference: ₹{abs(order4.filled_price - current_price):.2f}")
    
    # Cleanup
    data_engine.stop()
    print("\n✓ Example complete")


def main():
    """
    Run all examples
    """
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "ORDER SIMULATOR EXAMPLES" + " " * 29 + "║")
    print("╚" + "=" * 68 + "╝")
    
    # Check credentials
    required_vars = ['SMARTAPI_CLIENT_ID', 'SMARTAPI_API_KEY', 'SMARTAPI_PASSWORD']
    missing = [var for var in required_vars if not os.getenv(var)]
    
    if missing:
        print("\n⚠️  Missing environment variables:")
        for var in missing:
            print(f"   - {var}")
        print("\nSet them to run examples with live data")
        return
    
    # Menu
    print("\nAvailable examples:")
    print("  1. Market Order Execution")
    print("  2. Limit Order Execution")
    print("  3. Order Execution Callbacks")
    print("  4. Order Cancellation")
    print("  5. Slippage and Spread Comparison")
    print("  6. Run All")
    print("  0. Exit")
    
    choice = input("\nSelect example (0-6): ").strip()
    
    try:
        if choice == '1':
            example_market_orders()
        elif choice == '2':
            example_limit_orders()
        elif choice == '3':
            example_order_callbacks()
        elif choice == '4':
            example_order_cancellation()
        elif choice == '5':
            example_slippage_comparison()
        elif choice == '6':
            print("\nRunning all examples...\n")
            example_market_orders()
            example_limit_orders()
            example_order_callbacks()
            example_order_cancellation()
            example_slippage_comparison()
            print("\n✓ All examples completed")
        elif choice == '0':
            print("\nExiting...")
        else:
            print("\n⚠️  Invalid choice")
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("Examples complete")
    print("=" * 70)


if __name__ == "__main__":
    main()
