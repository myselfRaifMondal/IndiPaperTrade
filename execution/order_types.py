"""
Advanced Order Types for Trading System.

Supports:
- Market Orders
- Limit Orders
- Stop Loss Orders
- Stop Limit Orders
- Bracket Orders
"""

import uuid
import logging
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class OrderType(Enum):
    """Order types supported."""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"
    STOP_LIMIT = "STOP_LIMIT"
    BRACKET = "BRACKET"


class OrderSide(Enum):
    """Order side - BUY or SELL."""
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(Enum):
    """Order status lifecycle."""
    PENDING = "PENDING"           # Order created, not yet triggered
    OPEN = "OPEN"                 # Order active, waiting for fill
    PARTIALLY_FILLED = "PARTIALLY_FILLED"  # Partial execution
    FILLED = "FILLED"             # Fully executed
    CANCELLED = "CANCELLED"       # Cancelled by user
    REJECTED = "REJECTED"         # Rejected by system
    TRIGGERED = "TRIGGERED"       # Stop order triggered


@dataclass
class Order:
    """
    Advanced order representation with support for multiple order types.
    """
    order_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    symbol: str = ""
    side: OrderSide = OrderSide.BUY
    quantity: int = 0
    order_type: OrderType = OrderType.MARKET
    
    # Price fields
    limit_price: Optional[float] = None      # For LIMIT orders
    trigger_price: Optional[float] = None    # For STOP orders
    stop_loss_price: Optional[float] = None  # For BRACKET orders
    take_profit_price: Optional[float] = None # For BRACKET orders
    
    # Execution fields
    filled_quantity: int = 0
    filled_price: Optional[float] = None
    average_fill_price: float = 0.0
    
    # Status tracking
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    filled_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    
    # Additional metadata
    commission: float = 0.0
    notes: str = ""
    
    def __post_init__(self):
        """Validate order parameters."""
        if self.quantity <= 0:
            raise ValueError(f"Invalid quantity: {self.quantity}")
        
        if self.order_type == OrderType.LIMIT and self.limit_price is None:
            raise ValueError("LIMIT order requires limit_price")
        
        if self.order_type in [OrderType.STOP_LOSS, OrderType.STOP_LIMIT]:
            if self.trigger_price is None:
                raise ValueError(f"{self.order_type.value} order requires trigger_price")
        
        if self.order_type == OrderType.STOP_LIMIT and self.limit_price is None:
            raise ValueError("STOP_LIMIT order requires both trigger_price and limit_price")
    
    def is_filled(self) -> bool:
        """Check if order is fully filled."""
        return self.status == OrderStatus.FILLED
    
    def is_active(self) -> bool:
        """Check if order is still active."""
        return self.status in [OrderStatus.PENDING, OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED, OrderStatus.TRIGGERED]
    
    def fill(self, price: float, quantity: int = None) -> None:
        """
        Fill order at given price.
        
        Args:
            price: Execution price
            quantity: Quantity to fill (None = fill remaining)
        """
        if not self.is_active():
            logger.warning(f"Cannot fill order {self.order_id} with status {self.status}")
            return
        
        fill_qty = quantity if quantity else (self.quantity - self.filled_quantity)
        fill_qty = min(fill_qty, self.quantity - self.filled_quantity)
        
        if fill_qty <= 0:
            return
        
        # Update filled quantity and average price
        total_value = self.filled_quantity * self.average_fill_price + fill_qty * price
        self.filled_quantity += fill_qty
        self.average_fill_price = total_value / self.filled_quantity
        
        self.filled_price = price
        
        # Update status
        if self.filled_quantity >= self.quantity:
            self.status = OrderStatus.FILLED
            self.filled_at = datetime.now()
        else:
            self.status = OrderStatus.PARTIALLY_FILLED
        
        logger.info(f"Order {self.order_id} filled: {fill_qty} @ ₹{price:.2f} (Total: {self.filled_quantity}/{self.quantity})")
    
    def cancel(self) -> None:
        """Cancel order."""
        if not self.is_active():
            logger.warning(f"Cannot cancel order {self.order_id} with status {self.status}")
            return
        
        self.status = OrderStatus.CANCELLED
        self.cancelled_at = datetime.now()
        logger.info(f"Order {self.order_id} cancelled")
    
    def reject(self, reason: str = "") -> None:
        """Reject order."""
        self.status = OrderStatus.REJECTED
        self.notes = reason
        logger.warning(f"Order {self.order_id} rejected: {reason}")
    
    def trigger(self) -> None:
        """Trigger stop order (convert to active)."""
        if self.order_type in [OrderType.STOP_LOSS, OrderType.STOP_LIMIT]:
            self.status = OrderStatus.TRIGGERED
            logger.info(f"Stop order {self.order_id} triggered at ₹{self.trigger_price}")
    
    def check_trigger(self, current_price: float) -> bool:
        """
        Check if stop order should be triggered.
        
        Args:
            current_price: Current market price
            
        Returns:
            True if order should be triggered
        """
        if self.status != OrderStatus.PENDING:
            return False
        
        if self.order_type not in [OrderType.STOP_LOSS, OrderType.STOP_LIMIT]:
            return False
        
        if self.trigger_price is None:
            return False
        
        # BUY stop: trigger when price rises above trigger
        if self.side == OrderSide.BUY:
            return current_price >= self.trigger_price
        # SELL stop: trigger when price falls below trigger
        else:
            return current_price <= self.trigger_price
    
    def check_limit_fill(self, current_price: float) -> bool:
        """
        Check if limit order can be filled at current price.
        
        Args:
            current_price: Current market price
            
        Returns:
            True if order can be filled
        """
        if self.status not in [OrderStatus.OPEN, OrderStatus.TRIGGERED]:
            return False
        
        if self.order_type == OrderType.MARKET:
            return True
        
        if self.limit_price is None:
            return False
        
        # BUY limit: fill when price drops to or below limit
        if self.side == OrderSide.BUY:
            return current_price <= self.limit_price
        # SELL limit: fill when price rises to or above limit
        else:
            return current_price >= self.limit_price
    
    def to_dict(self) -> Dict:
        """Convert order to dictionary."""
        return {
            'order_id': self.order_id,
            'symbol': self.symbol,
            'side': self.side.value,
            'quantity': self.quantity,
            'order_type': self.order_type.value,
            'limit_price': self.limit_price,
            'trigger_price': self.trigger_price,
            'filled_quantity': self.filled_quantity,
            'filled_price': self.filled_price,
            'average_fill_price': self.average_fill_price,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'filled_at': self.filled_at.isoformat() if self.filled_at else None,
            'commission': self.commission,
        }
    
    def __repr__(self) -> str:
        price_info = ""
        if self.order_type == OrderType.LIMIT:
            price_info = f" @ ₹{self.limit_price}"
        elif self.order_type in [OrderType.STOP_LOSS, OrderType.STOP_LIMIT]:
            price_info = f" trigger=₹{self.trigger_price}"
        
        return (f"Order({self.order_id[:8]}... {self.side.value} {self.quantity} "
                f"{self.symbol} {self.order_type.value}{price_info} [{self.status.value}])")


class OrderFactory:
    """Factory for creating different order types."""
    
    @staticmethod
    def create_market_order(symbol: str, side: OrderSide, quantity: int) -> Order:
        """Create market order."""
        return Order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=OrderType.MARKET,
            status=OrderStatus.OPEN
        )
    
    @staticmethod
    def create_limit_order(symbol: str, side: OrderSide, quantity: int, limit_price: float) -> Order:
        """Create limit order."""
        return Order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=OrderType.LIMIT,
            limit_price=limit_price,
            status=OrderStatus.OPEN
        )
    
    @staticmethod
    def create_stop_loss_order(symbol: str, side: OrderSide, quantity: int, trigger_price: float) -> Order:
        """Create stop loss order."""
        return Order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=OrderType.STOP_LOSS,
            trigger_price=trigger_price,
            status=OrderStatus.PENDING
        )
    
    @staticmethod
    def create_stop_limit_order(symbol: str, side: OrderSide, quantity: int, 
                                trigger_price: float, limit_price: float) -> Order:
        """Create stop limit order."""
        return Order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=OrderType.STOP_LIMIT,
            trigger_price=trigger_price,
            limit_price=limit_price,
            status=OrderStatus.PENDING
        )
    
    @staticmethod
    def create_bracket_order(symbol: str, side: OrderSide, quantity: int,
                           entry_price: float, stop_loss: float, take_profit: float) -> Order:
        """Create bracket order (entry + SL + TP)."""
        return Order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=OrderType.BRACKET,
            limit_price=entry_price,
            stop_loss_price=stop_loss,
            take_profit_price=take_profit,
            status=OrderStatus.OPEN
        )
