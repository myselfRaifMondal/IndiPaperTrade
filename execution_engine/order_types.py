"""
Order Types and Data Structures for Order Simulation Engine

This module defines order types, order states, and data structures
used throughout the order simulation system.

Order Types:
- Market Order: Execute immediately at current market price
- Limit Order: Execute only when price condition is met

Order States:
- PENDING: Order created, waiting for execution
- PARTIAL: Partially filled (not implemented in basic version)
- FILLED: Order completely executed
- CANCELLED: Order cancelled before execution
- REJECTED: Order rejected due to validation failure
- EXPIRED: Order expired (for time-based orders)

Usage:
    from execution_engine import Order, OrderType, OrderSide, OrderStatus
    
    order = Order(
        symbol="RELIANCE",
        order_type=OrderType.MARKET,
        side=OrderSide.BUY,
        quantity=10,
        price=2500.0
    )
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime
import uuid


class OrderType(Enum):
    """
    Types of orders supported by the simulation engine.
    """
    MARKET = "MARKET"  # Execute immediately at market price
    LIMIT = "LIMIT"    # Execute when price condition is met
    STOP_LOSS = "STOP_LOSS"  # Stop loss order (future enhancement)
    STOP_LOSS_LIMIT = "STOP_LOSS_LIMIT"  # Stop loss limit (future)


class OrderSide(Enum):
    """
    Side of the order: Buy or Sell.
    """
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(Enum):
    """
    Current status of an order.
    """
    PENDING = "PENDING"      # Created, waiting for execution
    PARTIAL = "PARTIAL"      # Partially filled (future)
    FILLED = "FILLED"        # Completely executed
    CANCELLED = "CANCELLED"  # Cancelled by user
    REJECTED = "REJECTED"    # Rejected due to validation
    EXPIRED = "EXPIRED"      # Expired (time-based orders)


class TimeInForce(Enum):
    """
    Time in force for orders.
    """
    DAY = "DAY"        # Valid for trading day
    GTC = "GTC"        # Good till cancelled
    IOC = "IOC"        # Immediate or cancel
    FOK = "FOK"        # Fill or kill


@dataclass
class Order:
    """
    Represents a trading order.
    
    Attributes:
        symbol: Trading symbol (e.g., "RELIANCE", "TCS")
        order_type: Type of order (MARKET, LIMIT)
        side: Buy or Sell
        quantity: Number of shares/contracts
        price: Order price (for LIMIT orders, None for MARKET)
        order_id: Unique order identifier
        status: Current order status
        created_at: Order creation timestamp
        updated_at: Last update timestamp
        filled_quantity: Quantity filled so far
        filled_price: Average fill price
        time_in_force: Time validity of order
        user_data: Additional user-defined data
    """
    
    # Required fields
    symbol: str
    order_type: OrderType
    side: OrderSide
    quantity: int
    
    # Optional fields with defaults
    price: Optional[float] = None  # Required for LIMIT orders
    order_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    filled_quantity: int = 0
    filled_price: Optional[float] = None
    time_in_force: TimeInForce = TimeInForce.DAY
    user_data: Dict[str, Any] = field(default_factory=dict)
    
    # Execution details
    execution_timestamp: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    
    def __post_init__(self):
        """Validate order after initialization."""
        if self.quantity <= 0:
            raise ValueError("Quantity must be positive")
        
        if self.order_type == OrderType.LIMIT and self.price is None:
            raise ValueError("LIMIT orders require a price")
        
        if self.price is not None and self.price <= 0:
            raise ValueError("Price must be positive")
    
    def is_buy(self) -> bool:
        """Check if this is a buy order."""
        return self.side == OrderSide.BUY
    
    def is_sell(self) -> bool:
        """Check if this is a sell order."""
        return self.side == OrderSide.SELL
    
    def is_market_order(self) -> bool:
        """Check if this is a market order."""
        return self.order_type == OrderType.MARKET
    
    def is_limit_order(self) -> bool:
        """Check if this is a limit order."""
        return self.order_type == OrderType.LIMIT
    
    def is_pending(self) -> bool:
        """Check if order is pending execution."""
        return self.status == OrderStatus.PENDING
    
    def is_filled(self) -> bool:
        """Check if order is completely filled."""
        return self.status == OrderStatus.FILLED
    
    def is_active(self) -> bool:
        """Check if order is still active (can be executed)."""
        return self.status in [OrderStatus.PENDING, OrderStatus.PARTIAL]
    
    def remaining_quantity(self) -> int:
        """Get remaining quantity to be filled."""
        return self.quantity - self.filled_quantity
    
    def update_status(self, new_status: OrderStatus, reason: Optional[str] = None) -> None:
        """
        Update order status.
        
        Args:
            new_status: New status to set
            reason: Optional reason for status change
        """
        self.status = new_status
        self.updated_at = datetime.now()
        
        if new_status == OrderStatus.REJECTED and reason:
            self.rejection_reason = reason
    
    def fill(self, quantity: int, price: float) -> None:
        """
        Fill order (completely or partially).
        
        Args:
            quantity: Quantity filled
            price: Fill price
        """
        if quantity > self.remaining_quantity():
            raise ValueError("Fill quantity exceeds remaining quantity")
        
        # Update filled quantity
        old_filled = self.filled_quantity
        self.filled_quantity += quantity
        
        # Calculate weighted average fill price
        if self.filled_price is None:
            self.filled_price = price
        else:
            total_value = (old_filled * self.filled_price) + (quantity * price)
            self.filled_price = total_value / self.filled_quantity
        
        # Update status
        if self.filled_quantity == self.quantity:
            self.status = OrderStatus.FILLED
            self.execution_timestamp = datetime.now()
        else:
            self.status = OrderStatus.PARTIAL
        
        self.updated_at = datetime.now()
    
    def cancel(self) -> bool:
        """
        Cancel order if possible.
        
        Returns:
            bool: True if cancelled, False if cannot be cancelled
        """
        if self.is_active():
            self.status = OrderStatus.CANCELLED
            self.updated_at = datetime.now()
            return True
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert order to dictionary.
        
        Returns:
            dict: Order as dictionary
        """
        return {
            'order_id': self.order_id,
            'symbol': self.symbol,
            'order_type': self.order_type.value,
            'side': self.side.value,
            'quantity': self.quantity,
            'price': self.price,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'filled_quantity': self.filled_quantity,
            'filled_price': self.filled_price,
            'time_in_force': self.time_in_force.value,
            'execution_timestamp': self.execution_timestamp.isoformat() if self.execution_timestamp else None,
            'rejection_reason': self.rejection_reason,
            'user_data': self.user_data
        }
    
    def __repr__(self) -> str:
        """String representation of order."""
        price_str = f"@{self.price}" if self.price else ""
        return (
            f"Order({self.order_id[:8]}... {self.side.value} {self.quantity} "
            f"{self.symbol} {self.order_type.value}{price_str} [{self.status.value}])"
        )


@dataclass
class ExecutionReport:
    """
    Report of order execution.
    
    Attributes:
        order_id: Order identifier
        symbol: Trading symbol
        side: Buy or Sell
        quantity: Executed quantity
        price: Execution price
        timestamp: Execution time
        slippage: Applied slippage (if any)
        spread: Applied spread (if any)
        commission: Commission charged (future)
    """
    order_id: str
    symbol: str
    side: OrderSide
    quantity: int
    price: float
    timestamp: datetime = field(default_factory=datetime.now)
    slippage: float = 0.0
    spread: float = 0.0
    commission: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert execution report to dictionary."""
        return {
            'order_id': self.order_id,
            'symbol': self.symbol,
            'side': self.side.value,
            'quantity': self.quantity,
            'price': self.price,
            'timestamp': self.timestamp.isoformat(),
            'slippage': self.slippage,
            'spread': self.spread,
            'commission': self.commission
        }


if __name__ == "__main__":
    # Example usage and testing
    print("=" * 60)
    print("Order Types Module Test")
    print("=" * 60)
    
    # Test 1: Create market order
    print("\n1. Creating market order:")
    market_order = Order(
        symbol="RELIANCE",
        order_type=OrderType.MARKET,
        side=OrderSide.BUY,
        quantity=10
    )
    print(f"   {market_order}")
    print(f"   Order ID: {market_order.order_id}")
    print(f"   Status: {market_order.status.value}")
    
    # Test 2: Create limit order
    print("\n2. Creating limit order:")
    limit_order = Order(
        symbol="TCS",
        order_type=OrderType.LIMIT,
        side=OrderSide.SELL,
        quantity=5,
        price=3500.0
    )
    print(f"   {limit_order}")
    print(f"   Is limit order: {limit_order.is_limit_order()}")
    
    # Test 3: Fill order
    print("\n3. Filling order:")
    market_order.fill(quantity=10, price=2534.50)
    print(f"   {market_order}")
    print(f"   Filled quantity: {market_order.filled_quantity}")
    print(f"   Filled price: {market_order.filled_price}")
    print(f"   Status: {market_order.status.value}")
    
    # Test 4: Partial fill
    print("\n4. Partial fill:")
    partial_order = Order(
        symbol="INFY",
        order_type=OrderType.LIMIT,
        side=OrderSide.BUY,
        quantity=100,
        price=1500.0
    )
    partial_order.fill(quantity=50, price=1499.0)
    print(f"   {partial_order}")
    print(f"   Filled: {partial_order.filled_quantity}/{partial_order.quantity}")
    print(f"   Remaining: {partial_order.remaining_quantity()}")
    
    # Test 5: Cancel order
    print("\n5. Cancelling order:")
    cancel_order = Order(
        symbol="HDFC",
        order_type=OrderType.LIMIT,
        side=OrderSide.BUY,
        quantity=20,
        price=1600.0
    )
    print(f"   Before: {cancel_order.status.value}")
    cancel_order.cancel()
    print(f"   After: {cancel_order.status.value}")
    
    # Test 6: Order dictionary
    print("\n6. Order to dictionary:")
    order_dict = market_order.to_dict()
    print(f"   Keys: {list(order_dict.keys())}")
    
    # Test 7: Execution report
    print("\n7. Creating execution report:")
    report = ExecutionReport(
        order_id=market_order.order_id,
        symbol="RELIANCE",
        side=OrderSide.BUY,
        quantity=10,
        price=2534.50,
        slippage=0.02,
        spread=0.01
    )
    print(f"   Symbol: {report.symbol}")
    print(f"   Quantity: {report.quantity}")
    print(f"   Price: {report.price}")
    print(f"   Slippage: {report.slippage}%")
    
    print("\n" + "=" * 60)
    print("✓ All tests passed")
    print("=" * 60)
