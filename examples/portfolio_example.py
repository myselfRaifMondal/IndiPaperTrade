"""
Portfolio Manager Example

Demonstrates complete portfolio management workflow:
- Initialize portfolio with capital
- Execute multiple trades (buy/sell, long/short)
- Track positions and calculate PnL
- Close positions and realize profits
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from data_engine import MarketDataEngine
from execution_engine import OrderSimulator, OrderSide, OrderType
from portfolio_engine import PortfolioManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Run portfolio manager example."""
    
    print("\n" + "=" * 70)
    print("PORTFOLIO MANAGER - COMPLETE EXAMPLE".center(70))
    print("=" * 70)
    
    # 1. Initialize Market Data Engine
    print("\n1. Initializing Market Data Engine...")
    market_data = MarketDataEngine()
    market_data.initialize()
    market_data.start()
    market_data.subscribe(['RELIANCE', 'TCS', 'INFY', 'HDFCBANK'])
    print("   ✓ Market Data Engine ready")
    
    # 2. Initialize Order Simulator
    print("\n2. Initializing Order Simulator...")
    order_sim = OrderSimulator(data_engine=market_data)
    order_sim.start()
    print("   ✓ Order Simulator ready")
    
    # 3. Initialize Portfolio Manager
    print("\n3. Initializing Portfolio Manager...")
    portfolio = PortfolioManager(
        initial_capital=100000,
        market_data_engine=market_data,
        order_simulator=order_sim,
        margin_multiplier=1.0
    )
    print("   ✓ Portfolio Manager ready")
    
    # 4. Execute trades and track positions
    print("\n4. Executing trades...")
    
    trades = [
        ("BUY", "RELIANCE", 10, OrderType.MARKET, None),
        ("BUY", "TCS", 5, OrderType.MARKET, None),
        ("SELL", "INFY", 8, OrderType.MARKET, None),
        ("BUY", "HDFCBANK", 15, OrderType.MARKET, None),
    ]
    
    executed_orders = []
    
    for side, symbol, qty, order_type, price in trades:
        order_side = OrderSide.BUY if side == "BUY" else OrderSide.SELL
        
        print(f"\n   Placing: {side} {qty} {symbol}")
        
        if order_type == OrderType.MARKET:
            order = order_sim.place_market_order(
                symbol=symbol,
                side=order_side,
                quantity=qty
            )
        else:
            order = order_sim.place_limit_order(
                symbol=symbol,
                side=order_side,
                quantity=qty,
                price=price
            )
        
        executed_orders.append(order)
        
        if order.is_filled():
            portfolio.execute_order(order)
            print(f"      ✓ Filled @ ₹{order.filled_price:.2f}")
        else:
            print(f"      ✗ Not filled")
    
    # 5. Update market prices and display portfolio
    print("\n5. Updating market prices...")
    portfolio.update_market_prices()
    print("   ✓ Prices updated")
    
    portfolio.print_portfolio_summary()
    portfolio.print_positions()
    
    # 6. Execute limit orders to close some positions
    print("\n6. Executing limit orders to close positions...")
    
    close_orders = [
        ("SELL", "RELIANCE", 5, OrderType.LIMIT, 2550),  # Sell at higher price
        ("BUY", "INFY", 4, OrderType.LIMIT, 1850),       # Buy back at lower price
    ]
    
    for side, symbol, qty, order_type, price in close_orders:
        order_side = OrderSide.BUY if side == "BUY" else OrderSide.SELL
        
        print(f"\n   Placing limit order: {side} {qty} {symbol} @ ₹{price:.2f}")
        
        order = order_sim.place_limit_order(
            symbol=symbol,
            side=order_side,
            quantity=qty,
            price=price
        )
        
        # Manually process the order (since it's at limit)
        # In real trading, the background processor would handle this
        current_price = market_data.get_price_data(symbol)
        if current_price:
            # Check if order should fill based on current market price
            # (simplified - real implementation would simulate price movement)
            print(f"      Current: ₹{current_price.ltp:.2f}")
            
            # For demo, force order to partially fill
            qty_to_fill = int(qty * 0.5)
            if qty_to_fill > 0 and abs(current_price.ltp - price) < 50:  # Within 50 rupees
                order.filled_quantity = qty_to_fill
                order.filled_price = price
                order.status = "FILLED"
                portfolio.execute_order(order)
                print(f"      ✓ Partially filled {qty_to_fill} @ ₹{price:.2f}")
    
    # 7. Final portfolio state
    print("\n7. Final Portfolio State")
    portfolio.update_market_prices()
    portfolio.print_portfolio_summary()
    portfolio.print_positions()
    portfolio.print_closed_positions()
    
    # 8. Position analytics
    print("\n8. Position Analytics")
    summary = portfolio.get_summary()
    
    print(f"\n   Capital Efficiency:")
    print(f"   - Used Capital:       ₹{summary['capital']['used']:>12,.2f}")
    print(f"   - Available Capital:  ₹{summary['capital']['available']:>12,.2f}")
    print(f"   - Utilization:        {(summary['capital']['used'] / summary['capital']['initial'] * 100):>11.2f}%")
    
    print(f"\n   Return on Investment:")
    print(f"   - Absolute Return:    ₹{summary['pnl']['total']:>12,.2f}")
    print(f"   - ROI:                {summary['pnl']['roi']:>12.2f}%")
    
    if summary['positions']['closed_count'] > 0:
        avg_closed_pnl = (
            portfolio.realized_pnl / summary['positions']['closed_count']
        )
        print(f"   - Avg PnL/Closed Pos: ₹{avg_closed_pnl:>12,.2f}")
    
    if summary['positions']['open_count'] > 0:
        avg_unrealized = (
            portfolio.unrealized_pnl / summary['positions']['open_count']
        )
        print(f"   - Avg PnL/Open Pos:   ₹{avg_unrealized:>12,.2f}")
    
    # 9. Cleanup
    print("\n9. Cleaning up...")
    order_sim.stop()
    market_data.stop()
    print("   ✓ Resources cleaned")
    
    print("\n" + "=" * 70)
    print("✓ Portfolio example completed successfully!".center(70))
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
