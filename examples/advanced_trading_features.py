"""
Example Usage of Extended Trading System Components.

Demonstrates:
- Advanced order types
- PnL calculations
- Risk metrics
- Performance analysis
- Alert system
"""

import sys
import os
# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from execution.order_types import OrderFactory, OrderSide
from portfolio.pnl_engine import PnLEngine
from risk.risk_engine import RiskEngine
from analytics.performance_analyzer import PerformanceAnalyzer
from alerts.alert_manager import AlertManager, AlertType, AlertPriority
from utils.market_hours import MarketHoursChecker, get_market_status_message


def example_order_types():
    """Example: Creating different order types."""
    print("\n" + "=" * 70)
    print("EXAMPLE: ORDER TYPES".center(70))
    print("=" * 70)
    
    # Market order
    market_order = OrderFactory.create_market_order("RELIANCE", OrderSide.BUY, 10)
    print(f"\n1. {market_order}")
    
    # Limit order
    limit_order = OrderFactory.create_limit_order("TCS", OrderSide.SELL, 5, 3500.0)
    print(f"2. {limit_order}")
    
    # Stop loss order
    stop_order = OrderFactory.create_stop_loss_order("INFY", OrderSide.SELL, 20, 1400.0)
    print(f"3. {stop_order}")
    
    # Stop limit order
    stop_limit = OrderFactory.create_stop_limit_order("HDFCBANK", OrderSide.BUY, 15, 1600.0, 1605.0)
    print(f"4. {stop_limit}")
    
    # Check trigger
    print(f"\nStop order triggered at 1395? {stop_order.check_trigger(1395.0)}")
    print(f"Stop order triggered at 1405? {stop_order.check_trigger(1405.0)}")


def example_pnl_calculations():
    """Example: PnL calculations."""
    print("\n" + "=" * 70)
    print("EXAMPLE: PnL CALCULATIONS".center(70))
    print("=" * 70)
    
    pnl_engine = PnLEngine()
    
    # Unrealized PnL
    unrealized = pnl_engine.calculate_unrealized_pnl(
        entry_price=1340.0,
        current_price=1360.0,
        quantity=10,
        side="LONG"
    )
    print(f"\n1. Unrealized PnL (LONG): ₹{unrealized:,.2f}")
    
    # Realized PnL
    realized = pnl_engine.calculate_realized_pnl(
        entry_price=1340.0,
        exit_price=1360.0,
        quantity=10,
        side="LONG",
        commission=50.0
    )
    print(f"2. Realized PnL (after commission): ₹{realized:,.2f}")
    
    # Record PnL
    pnl_engine.record_realized_pnl(realized)
    print(f"3. Total Realized PnL: ₹{pnl_engine.realized_pnl_total:,.2f}")


def example_risk_metrics():
    """Example: Risk metrics calculation."""
    print("\n" + "=" * 70)
    print("EXAMPLE: RISK METRICS".center(70))
    print("=" * 70)
    
    risk_engine = RiskEngine(initial_capital=100000, max_daily_loss_pct=3.0)
    
    # Simulate equity curve
    equity_values = [100000, 102000, 101500, 103000, 99000, 101000]
    for equity in equity_values:
        risk_engine.update_equity(equity)
    
    print(f"\n1. Max Drawdown: ₹{risk_engine.max_drawdown:,.2f} ({risk_engine.max_drawdown_pct:.2f}%)")
    print(f"2. Current Drawdown: ₹{risk_engine.current_drawdown:,.2f}")
    print(f"3. Peak Equity: ₹{risk_engine.peak_equity:,.2f}")
    
    # Check daily loss limit
    daily_pnl = -2500
    limit_exceeded = risk_engine.check_daily_loss_limit(daily_pnl)
    print(f"4. Daily loss limit exceeded: {limit_exceeded}")


def example_alert_system():
    """Example: Alert management."""
    print("\n" + "=" * 70)
    print("EXAMPLE: ALERT SYSTEM".center(70))
    print("=" * 70)
    
    alert_mgr = AlertManager()
    
    # Price alert
    alert_mgr.add_price_alert("NIFTY", 22500.0, "ABOVE")
    alert_mgr.check_price_alerts("NIFTY", 22550.0)  # Triggers
    
    # Risk alert
    alert_mgr.alert_daily_loss_exceeded(3500, 3000)
    
    # System alert
    alert_mgr.alert_connection_lost()
    
    # Show alerts
    print("\nGenerated Alerts:")
    for i, alert in enumerate(alert_mgr.alerts, 1):
        print(f"{i}. [{alert.priority.value}] {alert.title}: {alert.message}")


def example_market_hours():
    """Example: Market hours checking."""
    print("\n" + "=" * 70)
    print("EXAMPLE: MARKET HOURS".center(70))
    print("=" * 70)
    
    current_time = MarketHoursChecker.get_current_time()
    print(f"\n1. Current Time (IST): {current_time.strftime('%Y-%m-%d %I:%M:%S %p')}")
    
    status = MarketHoursChecker.get_market_status()
    print(f"2. Market Status: {status}")
    
    is_open = MarketHoursChecker.is_market_open()
    print(f"3. Can Trade Now: {is_open}")
    
    message = get_market_status_message()
    print(f"4. Status Message: {message}")
    
    print(f"\n✓ Trading hours: 9:15 AM - 3:30 PM IST (Monday-Friday)")


def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("TRADING SYSTEM COMPONENTS - EXAMPLES".center(80))
    print("=" * 80)
    
    example_market_hours()
    example_order_types()
    example_pnl_calculations()
    example_risk_metrics()
    example_alert_system()
    
    print("\n" + "=" * 80)
    print("ALL EXAMPLES COMPLETED".center(80))
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
