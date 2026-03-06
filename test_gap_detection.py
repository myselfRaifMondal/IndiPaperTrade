#!/usr/bin/env python3
"""
Test script to verify the limit order gap detection enhancement.
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


def test_gap_detection():
    """Test the gap detection feature."""
    print("\n" + "=" * 60)
    print("Testing Limit Order Gap Detection")
    print("=" * 60 + "\n")
    
    # Create mock data engine
    data_engine = MockDataEngine()
    
    # Create order simulator
    simulator = OrderSimulator(data_engine, enable_spread=False, enable_slippage=False)
    
    # Test 1: BUY limit order with gap detection (price starts above limit, gaps down through it)
    print("Test 1: BUY limit at ₹100, price gaps from ₹105 to ₹95")
    print("-" * 60)
    
    # Set initial price ABOVE limit
    data_engine.set_price("RELIANCE", 105.0)
    
    # Create BUY limit order at ₹100
    order1 = Order(
        symbol="RELIANCE",
        order_type=OrderType.LIMIT,
        side=OrderSide.BUY,
        quantity=10,
        price=100.0
    )
    simulator.orders[order1.order_id] = order1
    
    # Check with price above limit - should NOT execute
    result = simulator._check_limit_order(order1)
    print(f"  Price: ₹105 (above limit ₹100) -> Execution: {result}")
    assert not result, "Order should not execute when price is above limit"
    
    # Simulate price gap: jump to ₹95 (below limit)
    # This should trigger gap detection: prev_price (105) > limit (100) >= current_price (95)
    data_engine.set_price("RELIANCE", 95.0)
    result = simulator._check_limit_order(order1)
    print(f"  Price: ₹95 (jumped below limit ₹100) -> Execution: {result}")
    print(f"  ✅ Gap detection working: Order will execute on downward gap crossing")
    assert result, "Order should execute when price gaps down through limit"
    
    print()
    
    # Test 2: SELL limit order with gap detection (price starts below limit, gaps up through it)
    print("Test 2: SELL limit at ₹500, price gaps from ₹490 to ₹510")
    print("-" * 60)
    
    # Set initial price BELOW limit
    data_engine.set_price("TCS", 490.0)
    
    # Create SELL limit order at ₹500
    order2 = Order(
        symbol="TCS",
        order_type=OrderType.LIMIT,
        side=OrderSide.SELL,
        quantity=5,
        price=500.0
    )
    simulator.orders[order2.order_id] = order2
    
    # Check with price below limit - should NOT execute
    result = simulator._check_limit_order(order2)
    print(f"  Price: ₹490 (below limit ₹500) -> Execution: {result}")
    assert not result, "Order should not execute when price is below limit"
    
    # Simulate price gap: jump to ₹510 (above limit)
    # This should trigger gap detection: prev_price (490) < limit (500) <= current_price (510)
    data_engine.set_price("TCS", 510.0)
    result = simulator._check_limit_order(order2)
    print(f"  Price: ₹510 (jumped above limit ₹500) -> Execution: {result}")
    print(f"  ✅ Gap detection working: Order will execute on upward gap crossing")
    assert result, "Order should execute when price gaps up through limit"
    
    print()
    
    # Test 3: Normal execution (price gradually approaches limit)
    print("Test 3: BUY limit at ₹100, price gradually approaches from above")
    print("-" * 60)
    
    # Set initial price above limit
    data_engine.set_price("INFY", 102.0)
    
    # Create BUY limit order
    order3 = Order(
        symbol="INFY",
        order_type=OrderType.LIMIT,
        side=OrderSide.BUY,
        quantity=10,
        price=100.0
    )
    simulator.orders[order3.order_id] = order3
    
    # Check with initial price
    result = simulator._check_limit_order(order3)
    print(f"  Price: ₹102 -> Execution: {result}")
    
    # Price drops to exactly limit
    data_engine.set_price("INFY", 100.0)
    result = simulator._check_limit_order(order3)
    print(f"  Price: ₹100 (exactly at limit) -> Execution: {result}")
    assert result, "Order should execute when price equals limit"
    print(f"  ✅ Normal price movement works correctly")
    
    print()
    print("=" * 60)
    print("✅ All gap detection tests passed!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    try:
        test_gap_detection()
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
