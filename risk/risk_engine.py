"""
Risk Management Engine.

Calculates and monitors:
- Maximum Drawdown
- Win Rate
- Profit Factor
- Risk-Reward Ratio
- Daily Loss Limits
- Position Exposure
- Sharpe Ratio
"""

import logging
import numpy as np
from datetime import datetime, date, timedelta
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RiskMetrics:
    """Container for risk metrics."""
    max_drawdown: float
    max_drawdown_pct: float
    win_rate: float
    profit_factor: float
    avg_risk_reward_ratio: float
    sharpe_ratio: float
    daily_loss: float
    position_exposure: float
    margin_utilization: float


class RiskEngine:
    """
    Calculate and monitor risk metrics for trading system.
    """
    
    def __init__(self, initial_capital: float, max_daily_loss_pct: float = 3.0):
        """
        Initialize Risk Engine.
        
        Args:
            initial_capital: Starting capital
            max_daily_loss_pct: Maximum allowed daily loss percentage
        """
        self.initial_capital = initial_capital
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_daily_loss = initial_capital * (max_daily_loss_pct / 100)
        
        # Tracking
        self.equity_curve: List[Tuple[datetime, float]] = []
        self.peak_equity = initial_capital
        self.current_drawdown = 0.0
        self.max_drawdown = 0.0
        self.max_drawdown_pct = 0.0
        
        logger.info(f"Risk Engine initialized | Max Daily Loss: ₹{self.max_daily_loss:,.2f} ({max_daily_loss_pct}%)")
    
    def update_equity(self, equity: float) -> None:
        """
        Update equity curve and drawdown.
        
        Args:
            equity: Current equity value
        """
        timestamp = datetime.now()
        self.equity_curve.append((timestamp, equity))
        
        # Update peak
        if equity > self.peak_equity:
            self.peak_equity = equity
            self.current_drawdown = 0.0
        else:
            # Calculate drawdown
            self.current_drawdown = self.peak_equity - equity
            drawdown_pct = (self.current_drawdown / self.peak_equity) * 100
            
            # Update max drawdown
            if self.current_drawdown > self.max_drawdown:
                self.max_drawdown = self.current_drawdown
                self.max_drawdown_pct = drawdown_pct
                logger.info(f"New max drawdown: ₹{self.max_drawdown:,.2f} ({self.max_drawdown_pct:.2f}%)")
    
    def calculate_max_drawdown(self, equity_curve: List[float] = None) -> Tuple[float, float]:
        """
        Calculate maximum drawdown from equity curve.
        
        Args:
            equity_curve: List of equity values (uses internal if None)
            
        Returns:
            (max_drawdown_amount, max_drawdown_percentage)
        """
        if equity_curve is None:
            if not self.equity_curve:
                return 0.0, 0.0
            equity_curve = [eq for _, eq in self.equity_curve]
        
        if len(equity_curve) < 2:
            return 0.0, 0.0
        
        peak = equity_curve[0]
        max_dd = 0.0
        max_dd_pct = 0.0
        
        for equity in equity_curve:
            if equity > peak:
                peak = equity
            
            drawdown = peak - equity
            drawdown_pct = (drawdown / peak) * 100 if peak > 0 else 0.0
            
            if drawdown > max_dd:
                max_dd = drawdown
                max_dd_pct = drawdown_pct
        
        return max_dd, max_dd_pct
    
    def calculate_win_rate(self, trades: List) -> float:
        """
        Calculate win rate from trade history.
        
        Args:
            trades: List of closed trades
            
        Returns:
            Win rate (0-100%)
        """
        if not trades:
            return 0.0
        
        winning_trades = sum(1 for trade in trades if trade.realized_pnl > 0)
        total_trades = len(trades)
        
        return (winning_trades / total_trades) * 100 if total_trades > 0 else 0.0
    
    def calculate_profit_factor(self, trades: List) -> float:
        """
        Calculate profit factor (total profit / total loss).
        
        Args:
            trades: List of closed trades
            
        Returns:
            Profit factor (>1 is profitable)
        """
        if not trades:
            return 0.0
        
        total_profit = sum(trade.realized_pnl for trade in trades if trade.realized_pnl > 0)
        total_loss = abs(sum(trade.realized_pnl for trade in trades if trade.realized_pnl < 0))
        
        if total_loss == 0:
            return float('inf') if total_profit > 0 else 0.0
        
        return total_profit / total_loss
    
    def calculate_risk_reward_ratio(self, trades: List) -> float:
        """
        Calculate average risk-reward ratio.
        
        Args:
            trades: List of closed trades
            
        Returns:
            Average R:R ratio
        """
        if not trades:
            return 0.0
        
        winning_trades = [trade for trade in trades if trade.realized_pnl > 0]
        losing_trades = [trade for trade in trades if trade.realized_pnl < 0]
        
        if not winning_trades or not losing_trades:
            return 0.0
        
        avg_win = np.mean([trade.realized_pnl for trade in winning_trades])
        avg_loss = abs(np.mean([trade.realized_pnl for trade in losing_trades]))
        
        if avg_loss == 0:
            return float('inf') if avg_win > 0 else 0.0
        
        return avg_win / avg_loss
    
    def calculate_sharpe_ratio(self, returns: List[float], risk_free_rate: float = 0.05) -> float:
        """
        Calculate Sharpe ratio (risk-adjusted return).
        
        Args:
            returns: List of period returns
            risk_free_rate: Annual risk-free rate (default 5%)
            
        Returns:
            Sharpe ratio
        """
        if not returns or len(returns) < 2:
            return 0.0
        
        returns_array = np.array(returns)
        excess_returns = returns_array - (risk_free_rate / 252)  # Daily risk-free rate
        
        if np.std(excess_returns) == 0:
            return 0.0
        
        sharpe = np.mean(excess_returns) / np.std(excess_returns)
        return sharpe * np.sqrt(252)  # Annualized
    
    def calculate_daily_loss(self, today_pnl: float) -> float:
        """
        Get today's loss amount.
        
        Args:
            today_pnl: Today's realized PnL
            
        Returns:
            Daily loss (0 or negative)
        """
        return min(0, today_pnl)
    
    def check_daily_loss_limit(self, daily_pnl: float) -> bool:
        """
        Check if daily loss limit is exceeded.
        
        Args:
            daily_pnl: Today's PnL
            
        Returns:
            True if limit exceeded
        """
        daily_loss = abs(self.calculate_daily_loss(daily_pnl))
        
        if daily_loss >= self.max_daily_loss:
            logger.warning(f"Daily loss limit exceeded: ₹{daily_loss:,.2f} / ₹{self.max_daily_loss:,.2f}")
            return True
        
        return False
    
    def calculate_position_exposure(self, positions: Dict, current_capital: float) -> float:
        """
        Calculate total capital allocated to positions.
        
        Args:
            positions: Open positions dict
            current_capital: Current account capital
            
        Returns:
            Position exposure percentage
        """
        total_exposure = 0.0
        
        for symbol, position in positions.items():
            position_value = position.quantity * position.current_price
            total_exposure += position_value
        
        if current_capital == 0:
            return 0.0
        
        return (total_exposure / current_capital) * 100
    
    def calculate_margin_utilization(self, used_margin: float, available_margin: float) -> float:
        """
        Calculate margin utilization percentage.
        
        Args:
            used_margin: Margin currently in use
            available_margin: Total available margin
            
        Returns:
            Utilization percentage
        """
        total_margin = used_margin + available_margin
        
        if total_margin == 0:
            return 0.0
        
        return (used_margin / total_margin) * 100
    
    def get_risk_metrics(self, trades: List, positions: Dict, 
                        current_equity: float, today_pnl: float,
                        used_margin: float, available_margin: float) -> RiskMetrics:
        """
        Calculate comprehensive risk metrics.
        
        Args:
            trades: List of closed trades
            positions: Open positions
            current_equity: Current equity value
            today_pnl: Today's PnL
            used_margin: Margin in use
            available_margin: Available margin
            
        Returns:
            RiskMetrics object
        """
        # Update equity curve
        self.update_equity(current_equity)
        
        # Calculate metrics
        win_rate = self.calculate_win_rate(trades)
        profit_factor = self.calculate_profit_factor(trades)
        risk_reward = self.calculate_risk_reward_ratio(trades)
        
        # Calculate returns for Sharpe ratio
        returns = []
        if len(self.equity_curve) > 1:
            for i in range(1, len(self.equity_curve)):
                prev_eq = self.equity_curve[i-1][1]
                curr_eq = self.equity_curve[i][1]
                ret = (curr_eq - prev_eq) / prev_eq if prev_eq > 0 else 0
                returns.append(ret)
        
        sharpe = self.calculate_sharpe_ratio(returns)
        daily_loss = abs(self.calculate_daily_loss(today_pnl))
        exposure = self.calculate_position_exposure(positions, current_equity)
        margin_util = self.calculate_margin_utilization(used_margin, available_margin)
        
        return RiskMetrics(
            max_drawdown=self.max_drawdown,
            max_drawdown_pct=self.max_drawdown_pct,
            win_rate=win_rate,
            profit_factor=profit_factor,
            avg_risk_reward_ratio=risk_reward,
            sharpe_ratio=sharpe,
            daily_loss=daily_loss,
            position_exposure=exposure,
            margin_utilization=margin_util
        )
    
    def print_risk_report(self, metrics: RiskMetrics) -> None:
        """Print formatted risk report."""
        print("\n" + "=" * 70)
        print("RISK METRICS REPORT".center(70))
        print("=" * 70)
        
        print("\nDRAWDOWN:")
        print(f"  Current Drawdown:     ₹{self.current_drawdown:>12,.2f}")
        print(f"  Maximum Drawdown:     ₹{metrics.max_drawdown:>12,.2f} ({metrics.max_drawdown_pct:.2f}%)")
        
        print("\nPERFORMANCE:")
        print(f"  Win Rate:             {metrics.win_rate:>12.2f}%")
        print(f"  Profit Factor:        {metrics.profit_factor:>12.2f}")
        print(f"  Avg Risk:Reward:      {metrics.avg_risk_reward_ratio:>12.2f}")
        print(f"  Sharpe Ratio:         {metrics.sharpe_ratio:>12.2f}")
        
        print("\nEXPOSURE:")
        print(f"  Position Exposure:    {metrics.position_exposure:>12.2f}%")
        print(f"  Margin Utilization:   {metrics.margin_utilization:>12.2f}%")
        
        print("\nDAILY LIMITS:")
        print(f"  Daily Loss:           ₹{metrics.daily_loss:>12,.2f}")
        print(f"  Max Daily Loss:       ₹{self.max_daily_loss:>12,.2f}")
        limit_pct = (metrics.daily_loss / self.max_daily_loss * 100) if self.max_daily_loss > 0 else 0
        print(f"  Limit Usage:          {limit_pct:>12.2f}%")
        
        print("=" * 70)
