"""
Portfolio Manager for IndiPaperTrade.

Tracks positions, calculates PnL, manages capital, and generates portfolio reports.
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from data_engine import MarketDataEngine, PriceData
from execution_engine import OrderSimulator, Order, OrderType, OrderSide

logger = logging.getLogger(__name__)


class PositionType(Enum):
    """Position types."""
    LONG = "LONG"
    SHORT = "SHORT"


@dataclass
class Position:
    """Represents a trading position."""
    symbol: str
    position_type: PositionType
    quantity: int
    entry_price: float
    entry_time: datetime
    current_price: float = 0.0
    leverage: float = 5.0
    last_updated: datetime = field(default_factory=datetime.now)
    
    @property
    def notional_value(self) -> float:
        """Total position value at current price."""
        return self.quantity * self.current_price
    
    @property
    def entry_value(self) -> float:
        """Total position value at entry price."""
        return self.quantity * self.entry_price
    
    @property
    def unrealized_pnl(self) -> float:
        """Unrealized profit/loss."""
        if self.position_type == PositionType.LONG:
            return self.notional_value - self.entry_value
        else:  # SHORT
            return self.entry_value - self.notional_value
    
    @property
    def pnl_percentage(self) -> float:
        """PnL as percentage of entry value."""
        if self.entry_value == 0:
            return 0.0
        return (self.unrealized_pnl / self.entry_value) * 100
    
    def update_price(self, price: float) -> None:
        """Update current price."""
        self.current_price = price
        self.last_updated = datetime.now()


@dataclass
class ClosedPosition:
    """Represents a closed position."""
    symbol: str
    position_type: PositionType
    quantity: int
    entry_price: float
    exit_price: float
    entry_time: datetime
    exit_time: datetime
    realized_pnl: float
    
    @property
    def pnl_percentage(self) -> float:
        """PnL as percentage."""
        if self.entry_price == 0:
            return 0.0
        if self.position_type == PositionType.LONG:
            return ((self.exit_price - self.entry_price) / self.entry_price) * 100
        else:  # SHORT
            return ((self.entry_price - self.exit_price) / self.entry_price) * 100


class PortfolioManager:
    """
    Portfolio manager for tracking positions, calculating PnL, and managing capital.
    """
    
    def __init__(
        self,
        initial_capital: float,
        market_data_engine: MarketDataEngine,
        order_simulator: OrderSimulator,
        margin_multiplier: float = 1.0
    ):
        """
        Initialize Portfolio Manager.
        
        Args:
            initial_capital: Starting capital in rupees
            market_data_engine: MarketDataEngine instance
            order_simulator: OrderSimulator instance
            margin_multiplier: Leverage multiplier (1.0 = no leverage)
        """
        logger.info(f"Initializing Portfolio Manager with ₹{initial_capital:,.2f}")
        
        self.initial_capital = initial_capital
        self.market_data_engine = market_data_engine
        self.order_simulator = order_simulator
        self.margin_multiplier = margin_multiplier
        
        # Portfolio state
        self.open_positions: Dict[str, Position] = {}
        self.closed_positions: List[ClosedPosition] = []
        self.cash = initial_capital
        self.last_trade_price: Dict[str, float] = {}
        
    def execute_order(self, order: Order) -> bool:
        """
        Execute an order and update positions.
        
        Args:
            order: Order to execute
            
        Returns:
            True if position update successful
        """
        if not order.is_filled():
            return False
        
        symbol = order.symbol
        quantity = order.filled_quantity
        price = order.filled_price
        
        logger.info(
            f"Processing filled order: {order.side.name} {quantity} {symbol} "
            f"@ ₹{price:.2f}"
        )
        
        # Update cash
        if order.side == OrderSide.BUY:
            self.cash -= quantity * price
        else:  # SELL
            self.cash += quantity * price
        
        self.last_trade_price[symbol] = price
        
        # Update or create position
        position_type = PositionType.LONG if order.side == OrderSide.BUY else PositionType.SHORT
        
        if symbol in self.open_positions:
            existing = self.open_positions[symbol]
            
            # Check if closing a position
            if existing.position_type != position_type:
                # Closing opposite position
                close_quantity = min(existing.quantity, quantity)
                
                if close_quantity > 0:
                    closed = ClosedPosition(
                        symbol=symbol,
                        position_type=existing.position_type,
                        quantity=close_quantity,
                        entry_price=existing.entry_price,
                        exit_price=price,
                        entry_time=existing.entry_time,
                        exit_time=datetime.now(),
                        realized_pnl=self._calculate_realized_pnl(
                            existing.position_type, close_quantity,
                            existing.entry_price, price
                        )
                    )
                    self.closed_positions.append(closed)
                    
                    logger.info(
                        f"Closed position: {closed.quantity} {symbol} "
                        f"@ ₹{closed.exit_price:.2f}, PnL: ₹{closed.realized_pnl:.2f}"
                    )
                    
                    # Update existing position
                    if close_quantity < existing.quantity:
                        existing.quantity -= close_quantity
                    else:
                        del self.open_positions[symbol]
                    
                    # Create new position if order size > close size
                    remaining = quantity - close_quantity
                    if remaining > 0:
                        self.open_positions[symbol] = Position(
                            symbol=symbol,
                            position_type=position_type,
                            quantity=remaining,
                            entry_price=price,
                            entry_time=datetime.now(),
                            current_price=price,
                            leverage=self.margin_multiplier
                        )
                
                return True
            
            # Same direction - increase position
            # Calculate new average entry price
            total_qty = existing.quantity + quantity
            avg_price = (
                (existing.quantity * existing.entry_price + quantity * price) /
                total_qty
            )
            
            existing.quantity = total_qty
            existing.entry_price = avg_price
            existing.update_price(price)
            
        else:
            # New position
            self.open_positions[symbol] = Position(
                symbol=symbol,
                position_type=position_type,
                quantity=quantity,
                entry_price=price,
                entry_time=datetime.now(),
                current_price=price,
                leverage=self.margin_multiplier
            )
        
        return True
    
    def update_market_prices(self) -> None:
        """Update all positions with current market prices."""
        for symbol in self.open_positions:
            price_data = self.market_data_engine.get_price_data(symbol)
            
            if price_data:
                self.open_positions[symbol].update_price(price_data.ltp)
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for a symbol."""
        return self.open_positions.get(symbol)
    
    def get_all_positions(self) -> Dict[str, Position]:
        """Get all open positions."""
        return dict(self.open_positions)
    
    def get_closed_positions(self) -> List[ClosedPosition]:
        """Get all closed positions."""
        return list(self.closed_positions)
    
    @property
    def total_notional_value(self) -> float:
        """Total value of all open positions at current prices."""
        return sum(pos.notional_value for pos in self.open_positions.values())
    
    @property
    def total_entry_value(self) -> float:
        """Total value of all open positions at entry prices."""
        return sum(pos.entry_value for pos in self.open_positions.values())
    
    @property
    def unrealized_pnl(self) -> float:
        """Total unrealized PnL from open positions."""
        return sum(pos.unrealized_pnl for pos in self.open_positions.values())
    
    @property
    def realized_pnl(self) -> float:
        """Total realized PnL from closed positions."""
        return sum(pos.realized_pnl for pos in self.closed_positions)
    
    @property
    def total_pnl(self) -> float:
        """Total PnL (realized + unrealized)."""
        return self.realized_pnl + self.unrealized_pnl
    
    @property
    def portfolio_value(self) -> float:
        """Current portfolio value (cash + positions)."""
        return self.cash + self.total_notional_value
    
    @property
    def available_capital(self) -> float:
        """Available capital for new trades."""
        return self.cash * self.margin_multiplier
    
    @property
    def used_capital(self) -> float:
        """Capital tied up in positions."""
        return self.total_entry_value

    @property
    def actual_margin_used(self) -> float:
        """Actual margin blocked with leverage applied."""
        leverage = self.margin_multiplier if self.margin_multiplier > 0 else 1.0
        return self.total_entry_value / leverage
    
    def get_summary(self) -> Dict:
        """Get comprehensive portfolio summary."""
        return {
            'capital': {
                'initial': self.initial_capital,
                'current': self.portfolio_value,
                'cash': self.cash,
                'available': self.available_capital,
                'used': self.used_capital,
                'actual_margin_used': self.actual_margin_used,
            },
            'positions': {
                'open_count': len(self.open_positions),
                'closed_count': len(self.closed_positions),
                'long_positions': len([
                    p for p in self.open_positions.values()
                    if p.position_type == PositionType.LONG
                ]),
                'short_positions': len([
                    p for p in self.open_positions.values()
                    if p.position_type == PositionType.SHORT
                ]),
            },
            'pnl': {
                'realized': self.realized_pnl,
                'unrealized': self.unrealized_pnl,
                'total': self.total_pnl,
                'roi': (self.total_pnl / self.initial_capital * 100) if self.initial_capital > 0 else 0,
            },
            'notional': {
                'at_entry': self.total_entry_value,
                'at_current': self.total_notional_value,
            }
        }
    
    def print_portfolio_summary(self) -> None:
        """Print formatted portfolio summary."""
        summary = self.get_summary()
        cap = summary['capital']
        pos = summary['positions']
        pnl = summary['pnl']
        
        print("\n" + "=" * 70)
        print("PORTFOLIO SUMMARY".center(70))
        print("=" * 70)
        
        print("\nCAPITAL:")
        print(f"  Initial Capital:      ₹{cap['initial']:>12,.2f}")
        print(f"  Current Portfolio:    ₹{cap['current']:>12,.2f}")
        print(f"  Cash Available:       ₹{cap['cash']:>12,.2f}")
        print(f"  Used in Positions:    ₹{cap['used']:>12,.2f}")
        
        print("\nPOSITIONS:")
        print(f"  Open Positions:       {pos['open_count']:>12}")
        print(f"    - Long:             {pos['long_positions']:>12}")
        print(f"    - Short:            {pos['short_positions']:>12}")
        print(f"  Closed Positions:     {pos['closed_count']:>12}")
        
        print("\nP&L:")
        print(f"  Realized:             ₹{pnl['realized']:>12,.2f}")
        print(f"  Unrealized:           ₹{pnl['unrealized']:>12,.2f}")
        print(f"  Total:                ₹{pnl['total']:>12,.2f}")
        print(f"  ROI:                  {pnl['roi']:>12.2f}%")
        
        print("\n" + "=" * 70)
    
    def print_positions(self) -> None:
        """Print all open positions."""
        if not self.open_positions:
            print("No open positions")
            return
        
        print("\n" + "=" * 100)
        print("OPEN POSITIONS".center(100))
        print("=" * 100)
        print(f"{'Symbol':<12} {'Type':<8} {'Qty':<8} {'Entry':<12} {'Current':<12} "
              f"{'Notional':<14} {'Unrealized PnL':<16} {'PnL %':<10}")
        print("-" * 100)
        
        for symbol, pos in sorted(self.open_positions.items()):
            print(
                f"{symbol:<12} {pos.position_type.value:<8} {pos.quantity:<8} "
                f"₹{pos.entry_price:<11.2f} ₹{pos.current_price:<11.2f} "
                f"₹{pos.notional_value:<13,.2f} ₹{pos.unrealized_pnl:<15,.2f} "
                f"{pos.pnl_percentage:>8.2f}%"
            )
        
        print("=" * 100)
    
    def print_closed_positions(self) -> None:
        """Print all closed positions."""
        if not self.closed_positions:
            print("No closed positions")
            return
        
        print("\n" + "=" * 110)
        print("CLOSED POSITIONS".center(110))
        print("=" * 110)
        print(f"{'Symbol':<12} {'Type':<8} {'Qty':<8} {'Entry':<12} {'Exit':<12} "
              f"{'Realized PnL':<14} {'PnL %':<10} {'Exit Time':<20}")
        print("-" * 110)
        
        for pos in self.closed_positions:
            print(
                f"{pos.symbol:<12} {pos.position_type.value:<8} {pos.quantity:<8} "
                f"₹{pos.entry_price:<11.2f} ₹{pos.exit_price:<11.2f} "
                f"₹{pos.realized_pnl:<13,.2f} {pos.pnl_percentage:>8.2f}% "
                f"{pos.exit_time.strftime('%Y-%m-%d %H:%M:%S'):<20}"
            )
        
        print("=" * 110)
    
    @staticmethod
    def _calculate_realized_pnl(
        position_type: PositionType,
        quantity: int,
        entry_price: float,
        exit_price: float
    ) -> float:
        """Calculate realized PnL for a closed position."""
        if position_type == PositionType.LONG:
            return quantity * (exit_price - entry_price)
        else:  # SHORT
            return quantity * (entry_price - exit_price)
