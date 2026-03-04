"""Performance Analysis Engine."""

import logging
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics container."""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_profit: float
    avg_loss: float
    largest_win: float
    largest_loss: float
    avg_holding_time: float  # hours
    total_pnl: float
    roi: float


class PerformanceAnalyzer:
    """Analyze trading performance."""
    
    def __init__(self):
        self.trade_history = []
        logger.info("Performance Analyzer initialized")
    
    def analyze_trades(self, trades: List, initial_capital: float) -> PerformanceMetrics:
        """Analyze trade performance."""
        if not trades:
            return PerformanceMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        
        winning = [t for t in trades if t.realized_pnl > 0]
        losing = [t for t in trades if t.realized_pnl < 0]
        
        total_pnl = sum(t.realized_pnl for t in trades)
        roi = (total_pnl / initial_capital * 100) if initial_capital > 0 else 0
        
        # Holding times
        holding_times = []
        for t in trades:
            if hasattr(t, 'entry_time') and hasattr(t, 'exit_time'):
                delta = (t.exit_time - t.entry_time).total_seconds() / 3600
                holding_times.append(delta)
        
        return PerformanceMetrics(
            total_trades=len(trades),
            winning_trades=len(winning),
            losing_trades=len(losing),
            win_rate=(len(winning) / len(trades) * 100) if trades else 0,
            avg_profit=np.mean([t.realized_pnl for t in winning]) if winning else 0,
            avg_loss=np.mean([t.realized_pnl for t in losing]) if losing else 0,
            largest_win=max([t.realized_pnl for t in winning]) if winning else 0,
            largest_loss=min([t.realized_pnl for t in losing]) if losing else 0,
            avg_holding_time=np.mean(holding_times) if holding_times else 0,
            total_pnl=total_pnl,
            roi=roi
        )
    
    def print_report(self, metrics: PerformanceMetrics):
        """Print performance report."""
        print("\n" + "=" * 70)
        print("PERFORMANCE REPORT".center(70))
        print("=" * 70)
        print(f"\nTotal Trades:         {metrics.total_trades}")
        print(f"Winning Trades:       {metrics.winning_trades}")
        print(f"Losing Trades:        {metrics.losing_trades}")
        print(f"Win Rate:             {metrics.win_rate:.2f}%")
        print(f"Avg Profit/Trade:     ₹{metrics.avg_profit:,.2f}")
        print(f"Avg Loss/Trade:       ₹{metrics.avg_loss:,.2f}")
        print(f"Largest Win:          ₹{metrics.largest_win:,.2f}")
        print(f"Largest Loss:         ₹{metrics.largest_loss:,.2f}")
        print(f"Avg Holding Time:     {metrics.avg_holding_time:.2f} hours")
        print(f"Total PnL:            ₹{metrics.total_pnl:,.2f}")
        print(f"ROI:                  {metrics.roi:.2f}%")
        print("=" * 70)
