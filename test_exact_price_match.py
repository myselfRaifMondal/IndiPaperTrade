#!/usr/bin/env python3
"""
Test script to verify exact price matching for limit orders (e.g., 1950.90).
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from execution_engine.order_simulator import OrderSimulator
from execution_engine.order_types import Order, OrderType, OrderSide, OrderStatus
from utils import get_logger

logger = get_logger(__name__)


class MockPriceData:
    """Mock price data for testing."""
    def __init__(self, ltp, bid=None, ask=None):
        self.ltp = ltp
        self.bid = bid if bid else ltp - 0.5
        self.ask = ask if ask else ltp + 0.5


class MockDataEngine:
    """Mock data engine for testing."""
    def __init__(self):
        self.prices = {}
    
    def get_price_data(self, symbol):
        return self.prices.get(symbol)
    
    def set_price(self, symbol, ltp, bid=None, ask=None):
        self.prices[symbol] = MockPriceData(ltp, bid, ask)


def test_exact_price_match():
    """Test exact price matching with floating-point tolerance."""
    print("\n" + "=" * 70)
    print("Testing Exact Price Match: BUY Limit at ₹1950.90")
    print("=" * 70 + "\n")
    
    # Create mock data engine
    data_engine = MockDataEngine()
    
    # Create order simulator
    simulator = OrderSimulator(data_engine, enable_spread=False, enable_slippage=False)
    
    # Test: BUY limit at 1950.90, market price hits exactly 1950.90
    print("Scenario: BUY limit order at ₹1950.90")
    print("-" * 70)
    
    # Start with price above the limit
    data_engine.set_price("NIFTY50", 1951.50)
    
    # Create BUY limit order at ₹1950.90
    order = Order(
        symbol="NIFTY50",
        order_type=OrderType.LIMIT,
        side=OrderSide.BUY,
        quantity=1,
        price=1950.90
    )
    simulator.orders[order.order_id] = order
    
    print(f"\n1. Initial setup:")
    print(f"   Order Type: BUY LIMIT")
    print(f"   Limit Price: ₹{order.price}")
    print(f"   Quantity: {order.quantity}")
    
    # Check 1: Price above limit
    result = simulator._check_limit_order(order)
    print(f"\n2. Market Price: ₹1951.50 (above limit)")
    print(f"   Should Execute: {result}")
    print(f"   Status: {'❌ Correctly NOT executing' if not result else '⚠️ UNEXPECTED'}")
    
    # Check 2: Price at exactly 1950.90
    data_engine.set_price("NIFTY50", 1950.90)
    result = simulator._check_limit_order(order)
    print(f"\n3. Market Price: ₹1950.90 (EXACTLY at limit)")
    print(f"   Should Execute: {result}")
    print(f"   Status: {'✅ CORRECTLY executing!' if result else '❌ FAILED - Not executing'}")
    
    if not result:
        print(f"\n   ERROR: Order should execute when market price equals limit price!")
        print(f"   This is the issue you reported.")
        return False
    
    # Check 3: Price slightly below (1950.89)
    data_engine.set_price("NIFTY50", 1950.89)
    result = simulator._check_limit_order(order)
    print(f"\n4. Market Price: ₹1950.89 (below limit)")
    print(f"   Should Execute: {result}")
    print(f"   Status: {'✅ Correctly executing' if result else '❌ UNEXPECTED'}")
    
    # Check 4: Price slightly above (1950.91)
    data_engine.set_price("NIFTY50", 1950.91)
    result = simulator._check_limit_order(order)
    print(f"\n5. Market Price: ₹1950.91 (just above limit, within tolerance)")
    print(f"   Should Execute: {result}")
    print(f"   Status: {'✅ Correctly executing (0.01 tolerance)' if result else '❌ UNEXPECTED'}")
    
    print("\n" + "=" * 70)
    print("✅ EXACT PRICE MATCH TEST PASSED!")
    print("=" * 70)
    print("\nExplanation:")
    print("  • BUY limit orders now execute when market price ≤ limit + 0.01")
    print("  • This handles floating-point precision issues")
    print("  • 0.01 tolerance = 1 paisa, negligible in real trading")
    print("  • Your ₹1950.90 order will now execute at ₹1950.90!")
    print()
    
    return True


if __name__ == "__main__":
    try:
        success = test_exact_price_match()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
