"""
Portfolio Metrics Calculator - Calculates trading performance metrics.

Calculates:
- Profit Factor (Win $ / Loss $)
- Win Rate (Winning trades / Total trades)
- Max Drawdown (Peak-to-trough decline)
- Sharpe Ratio (Risk-adjusted returns)
- Average Win/Loss
- Total trades, P&L
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np

logger = logging.getLogger(__name__)


class PortfolioMetrics:
    """
    Calculate portfolio and trading performance metrics.
    """
    
    def __init__(self):
        """Initialize metrics calculator."""
        self.closed_trades = []
        self.daily_pnls = {}  # date -> pnl
        self.lock = __import__('threading').RLock()
    
    def add_closed_trade(self, trade: Dict):
        """
        Add a closed trade for metrics calculation.
        
        Args:
            trade: Trade dict with keys:
                - symbol: Trading symbol
                - entry_price: Entry price
                - exit_price: Exit price
                - quantity: Quantity
                - side: BUY or SELL
                - entry_time: Entry timestamp
                - exit_time: Exit timestamp
                - pnl: Profit/Loss amount
        """
        try:
            with self.lock:
                self.closed_trades.append(trade)
                
                # Add to daily P&L
                if 'exit_time' in trade:
                    date_key = trade['exit_time'].date()
                    current_pnl = self.daily_pnls.get(date_key, 0)
                    self.daily_pnls[date_key] = current_pnl + trade.get('pnl', 0)
        
        except Exception as e:
            logger.error(f"Error adding closed trade: {e}")
    
    def get_total_trades(self) -> int:
        """Get total number of completed trades."""
        with self.lock:
            return len(self.closed_trades)
    
    def get_winning_trades(self) -> Tuple[int, float]:
        """
        Get winning trades and total win amount.
        
        Returns:
            (number of wins, total win amount)
        """
        try:
            with self.lock:
                winning = [t for t in self.closed_trades if t.get('pnl', 0) > 0]
                total_wins = sum(t.get('pnl', 0) for t in winning)
                return len(winning), total_wins
        except Exception as e:
            logger.error(f"Error calculating winning trades: {e}")
            return 0, 0
    
    def get_losing_trades(self) -> Tuple[int, float]:
        """
        Get losing trades and total loss amount.
        
        Returns:
            (number of losses, total loss amount)
        """
        try:
            with self.lock:
                losing = [t for t in self.closed_trades if t.get('pnl', 0) < 0]
                total_losses = sum(abs(t.get('pnl', 0)) for t in losing)
                return len(losing), total_losses
        except Exception as e:
            logger.error(f"Error calculating losing trades: {e}")
            return 0, 0
    
    def get_profit_factor(self) -> float:
        """
        Calculate Profit Factor = Total Wins / Total Losses.
        
        Returns:
            Profit factor (higher is better, >1.5 is good)
        """
        try:
            with self.lock:
                win_count, total_wins = self.get_winning_trades()
                loss_count, total_losses = self.get_losing_trades()
                
                if total_losses == 0:
                    return total_wins / 1 if total_wins > 0 else 0
                
                return total_wins / total_losses
        except Exception as e:
            logger.error(f"Error calculating profit factor: {e}")
            return 0
    
    def get_win_rate(self) -> float:
        """
        Calculate Win Rate = Winning trades / Total trades.
        
        Returns:
            Win rate percentage (0-100)
        """
        try:
            with self.lock:
                total = len(self.closed_trades)
                if total == 0:
                    return 0
                
                wins = len([t for t in self.closed_trades if t.get('pnl', 0) > 0])
                return (wins / total) * 100
        except Exception as e:
            logger.error(f"Error calculating win rate: {e}")
            return 0
    
    def get_average_win_loss(self) -> Tuple[float, float]:
        """
        Calculate average win and loss amounts.
        
        Returns:
            (average win amount, average loss amount)
        """
        try:
            with self.lock:
                win_count, total_wins = self.get_winning_trades()
                loss_count, total_losses = self.get_losing_trades()
                
                avg_win = total_wins / win_count if win_count > 0 else 0
                avg_loss = total_losses / loss_count if loss_count > 0 else 0
                
                return avg_win, avg_loss
        except Exception as e:
            logger.error(f"Error calculating average win/loss: {e}")
            return 0, 0
    
    def get_max_drawdown(self) -> float:
        """
        Calculate Maximum Drawdown.
        
        Maximum Drawdown = (Peak - Trough) / Peak
        
        Returns:
            Max drawdown as percentage
        """
        try:
            with self.lock:
                if not self.closed_trades:
                    return 0
                
                # Calculate cumulative P&L
                cumulative_pnl = []
                running_total = 0
                for trade in self.closed_trades:
                    running_total += trade.get('pnl', 0)
                    cumulative_pnl.append(running_total)
                
                if not cumulative_pnl:
                    return 0
                
                # Find max drawdown
                peak = cumulative_pnl[0]
                max_drawdown = 0
                
                for pnl in cumulative_pnl:
                    if pnl > peak:
                        peak = pnl
                    drawdown = (peak - pnl) / abs(peak) if peak != 0 else 0
                    max_drawdown = max(max_drawdown, drawdown)
                
                return max_drawdown * 100
        
        except Exception as e:
            logger.error(f"Error calculating max drawdown: {e}")
            return 0
    
    def get_sharpe_ratio(self, risk_free_rate: float = 0.05) -> float:
        """
        Calculate Sharpe Ratio = (Return - Risk-Free Rate) / Std Dev of Returns.
        
        Args:
            risk_free_rate: Annual risk-free rate (default 5%)
        
        Returns:
            Sharpe ratio (higher is better, >1 is good)
        """
        try:
            with self.lock:
                if len(self.closed_trades) < 2:
                    return 0
                
                # Get daily returns
                pnls = [t.get('pnl', 0) for t in self.closed_trades]
                returns = np.array(pnls)
                
                if len(returns) == 0:
                    return 0
                
                # Calculate daily return metrics
                mean_return = np.mean(returns)
                std_return = np.std(returns)
                
                if std_return == 0:
                    return 0
                
                # Daily risk-free rate
                daily_risk_free = (1 + risk_free_rate) ** (1/252) - 1
                
                # Calculate Sharpe ratio
                sharpe = (mean_return - daily_risk_free) / std_return * np.sqrt(252)
                
                return sharpe
        
        except Exception as e:
            logger.error(f"Error calculating Sharpe ratio: {e}")
            return 0
    
    def get_total_pnl(self) -> float:
        """Get total P&L from all trades."""
        try:
            with self.lock:
                return sum(t.get('pnl', 0) for t in self.closed_trades)
        except:
            return 0
    
    def get_today_pnl(self) -> float:
        """Get today's P&L."""
        try:
            with self.lock:
                today = datetime.now().date()
                return self.daily_pnls.get(today, 0)
        except:
            return 0
    
    def get_daily_pnl(self, date) -> float:
        """Get P&L for a specific date."""
        try:
            with self.lock:
                return self.daily_pnls.get(date, 0)
        except:
            return 0
    
    def get_all_metrics(self) -> Dict:
        """
        Get all metrics at once.
        
        Returns:
            Dict with all calculated metrics
        """
        try:
            with self.lock:
                total_trades = self.get_total_trades()
                win_count, total_wins = self.get_winning_trades()
                loss_count, total_losses = self.get_losing_trades()
                avg_win, avg_loss = self.get_average_win_loss()
                
                return {
                    'total_trades': total_trades,
                    'winning_trades': win_count,
                    'losing_trades': loss_count,
                    'total_wins': total_wins,
                    'total_losses': total_losses,
                    'profit_factor': self.get_profit_factor(),
                    'win_rate': self.get_win_rate(),
                    'average_win': avg_win,
                    'average_loss': avg_loss,
                    'max_drawdown': self.get_max_drawdown(),
                    'sharpe_ratio': self.get_sharpe_ratio(),
                    'total_pnl': self.get_total_pnl(),
                    'today_pnl': self.get_today_pnl()
                }
        except Exception as e:
            logger.error(f"Error getting all metrics: {e}")
            return {}
    
    def clear_trades(self):
        """Clear all trade data."""
        with self.lock:
            self.closed_trades = []
            self.daily_pnls = {}
            logger.info("Cleared all trade metrics")


# Global metrics instance
_portfolio_metrics: Optional[PortfolioMetrics] = None


def get_portfolio_metrics() -> PortfolioMetrics:
    """Get or create global portfolio metrics instance."""
    global _portfolio_metrics
    if _portfolio_metrics is None:
        _portfolio_metrics = PortfolioMetrics()
    return _portfolio_metrics


def init_portfolio_metrics() -> PortfolioMetrics:
    """Initialize and return portfolio metrics."""
    global _portfolio_metrics
    _portfolio_metrics = PortfolioMetrics()
    return _portfolio_metrics
