"""
PnL (Profit and Loss) Calculation Engine.

Calculates:
- Unrealized PnL (open positions)
- Realized PnL (closed positions)
- Position-level PnL
- Trade-level PnL
- Daily PnL
"""

import logging
from datetime import datetime, date
from typing import Dict, List, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PnLSnapshot:
    """Snapshot of PnL at a point in time."""
    timestamp: datetime
    realized_pnl: float
    unrealized_pnl: float
    total_pnl: float
    equity: float
    

class PnLEngine:
    """
    Calculate and track profit and loss for positions and trades.
    """
    
    def __init__(self):
        """Initialize PnL engine."""
        self.realized_pnl_total = 0.0
        self.realized_pnl_today = 0.0
        self.pnl_history: List[PnLSnapshot] = []
        self.daily_pnl: Dict[date, float] = {}
        self.current_date = datetime.now().date()
        
        logger.info("PnL Engine initialized")
    
    def calculate_unrealized_pnl(self, entry_price: float, current_price: float, 
                                 quantity: int, side: str) -> float:
        """
        Calculate unrealized PnL for open position.
        
        Args:
            entry_price: Entry price
            current_price: Current market price
            quantity: Position quantity
            side: "LONG" or "SHORT"
            
        Returns:
            Unrealized PnL
        """
        if side.upper() == "LONG":
            pnl = (current_price - entry_price) * quantity
        else:  # SHORT
            pnl = (entry_price - current_price) * quantity
        
        return pnl
    
    def calculate_realized_pnl(self, entry_price: float, exit_price: float,
                               quantity: int, side: str, commission: float = 0.0) -> float:
        """
        Calculate realized PnL for closed position.
        
        Args:
            entry_price: Entry price
            exit_price: Exit price
            quantity: Position quantity
            side: "LONG" or "SHORT"
            commission: Total commission paid
            
        Returns:
            Realized PnL (after commission)
        """
        if side.upper() == "LONG":
            pnl = (exit_price - entry_price) * quantity
        else:  # SHORT
            pnl = (entry_price - exit_price) * quantity
        
        # Deduct commission
        pnl -= commission
        
        return pnl
    
    def record_realized_pnl(self, pnl: float, trade_date: date = None) -> None:
        """
        Record realized PnL from closed trade.
        
        Args:
            pnl: Realized profit/loss
            trade_date: Date of trade (defaults to today)
        """
        if trade_date is None:
            trade_date = datetime.now().date()
        
        # Update total realized PnL
        self.realized_pnl_total += pnl
        
        # Update daily PnL
        if trade_date == self.current_date:
            self.realized_pnl_today += pnl
        
        # Update daily PnL tracking
        if trade_date not in self.daily_pnl:
            self.daily_pnl[trade_date] = 0.0
        self.daily_pnl[trade_date] += pnl
        
        logger.info(f"Recorded realized PnL: ₹{pnl:.2f} on {trade_date}")
    
    def get_total_unrealized_pnl(self, positions: Dict) -> float:
        """
        Calculate total unrealized PnL across all open positions.
        
        Args:
            positions: Dictionary of open positions
            
        Returns:
            Total unrealized PnL
        """
        total_unrealized = 0.0
        
        for symbol, position in positions.items():
            pnl = self.calculate_unrealized_pnl(
                entry_price=position.entry_price,
                current_price=position.current_price,
                quantity=position.quantity,
                side=position.position_type.value
            )
            total_unrealized += pnl
        
        return total_unrealized
    
    def get_total_pnl(self, positions: Dict) -> float:
        """
        Get total PnL (realized + unrealized).
        
        Args:
            positions: Dictionary of open positions
            
        Returns:
            Total PnL
        """
        unrealized = self.get_total_unrealized_pnl(positions)
        return self.realized_pnl_total + unrealized
    
    def get_daily_pnl(self, trade_date: date = None) -> float:
        """
        Get PnL for specific date.
        
        Args:
            trade_date: Date to query (defaults to today)
            
        Returns:
            Daily PnL
        """
        if trade_date is None:
            trade_date = self.current_date
        
        return self.daily_pnl.get(trade_date, 0.0)
    
    def reset_daily_pnl(self) -> None:
        """Reset daily PnL counter (call at start of new trading day)."""
        today = datetime.now().date()
        
        if today != self.current_date:
            logger.info(f"New trading day: {today}. Yesterday's PnL: ₹{self.realized_pnl_today:.2f}")
            self.current_date = today
            self.realized_pnl_today = 0.0
    
    def create_snapshot(self, positions: Dict, equity: float) -> PnLSnapshot:
        """
        Create PnL snapshot at current time.
        
        Args:
            positions: Current open positions
            equity: Current equity value
            
        Returns:
            PnLSnapshot
        """
        unrealized = self.get_total_unrealized_pnl(positions)
        total = self.realized_pnl_total + unrealized
        
        snapshot = PnLSnapshot(
            timestamp=datetime.now(),
            realized_pnl=self.realized_pnl_total,
            unrealized_pnl=unrealized,
            total_pnl=total,
            equity=equity
        )
        
        self.pnl_history.append(snapshot)
        return snapshot
    
    def get_pnl_summary(self, positions: Dict) -> Dict:
        """
        Get comprehensive PnL summary.
        
        Args:
            positions: Current open positions
            
        Returns:
            Dictionary with PnL metrics
        """
        unrealized = self.get_total_unrealized_pnl(positions)
        total = self.realized_pnl_total + unrealized
        
        return {
            'realized_pnl': {
                'total': self.realized_pnl_total,
                'today': self.realized_pnl_today,
            },
            'unrealized_pnl': unrealized,
            'total_pnl': total,
            'daily_pnl': dict(self.daily_pnl),
        }
    
    def calculate_pnl_percentage(self, pnl: float, entry_value: float) -> float:
        """
        Calculate PnL as percentage of entry value.
        
        Args:
            pnl: Profit/loss amount
            entry_value: Initial position value
            
        Returns:
            PnL percentage
        """
        if entry_value == 0:
            return 0.0
        return (pnl / entry_value) * 100
    
    def get_position_pnl_breakdown(self, positions: Dict) -> List[Dict]:
        """
        Get PnL breakdown for each position.
        
        Args:
            positions: Dictionary of open positions
            
        Returns:
            List of position PnL details
        """
        breakdown = []
        
        for symbol, position in positions.items():
            unrealized_pnl = self.calculate_unrealized_pnl(
                entry_price=position.entry_price,
                current_price=position.current_price,
                quantity=position.quantity,
                side=position.position_type.value
            )
            
            entry_value = position.quantity * position.entry_price
            pnl_pct = self.calculate_pnl_percentage(unrealized_pnl, entry_value)
            
            breakdown.append({
                'symbol': symbol,
                'quantity': position.quantity,
                'entry_price': position.entry_price,
                'current_price': position.current_price,
                'unrealized_pnl': unrealized_pnl,
                'pnl_percentage': pnl_pct,
                'side': position.position_type.value,
            })
        
        return breakdown
    
    def print_pnl_report(self, positions: Dict) -> None:
        """Print formatted PnL report."""
        summary = self.get_pnl_summary(positions)
        
        print("\n" + "=" * 70)
        print("PnL REPORT".center(70))
        print("=" * 70)
        
        print("\nREALIZED PnL:")
        print(f"  Total Realized:       ₹{summary['realized_pnl']['total']:>12,.2f}")
        print(f"  Today's Realized:     ₹{summary['realized_pnl']['today']:>12,.2f}")
        
        print("\nUNREALIZED PnL:")
        print(f"  Open Positions:       ₹{summary['unrealized_pnl']:>12,.2f}")
        
        print("\nTOTAL PnL:")
        print(f"  Combined:             ₹{summary['total_pnl']:>12,.2f}")
        
        # Position breakdown
        if positions:
            print("\nPOSITION BREAKDOWN:")
            print("-" * 70)
            breakdown = self.get_position_pnl_breakdown(positions)
            for pos in breakdown:
                print(f"  {pos['symbol']:<12} {pos['side']:<6} {pos['quantity']:<6} "
                      f"₹{pos['entry_price']:<8.2f} → ₹{pos['current_price']:<8.2f} "
                      f"PnL: ₹{pos['unrealized_pnl']:>10,.2f} ({pos['pnl_percentage']:>6.2f}%)")
        
        print("=" * 70)
