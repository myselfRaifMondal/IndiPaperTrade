"""
Unit tests for portfolio metrics calculations.

Tests:
- Profit Factor calculation
- Max Drawdown calculation
- Sharpe Ratio calculation
- Win Rate calculation
- Average Win/Loss calculation
"""

import unittest
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from portfolio_engine.metrics_calculator import PortfolioMetrics


class TestMetricsCalculator(unittest.TestCase):
    """Test suite for PortfolioMetrics."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.metrics = PortfolioMetrics()
        self.metrics.closed_trades = []
    
    def test_profit_factor_all_wins(self):
        """Test profit factor with all winning trades."""
        self.metrics.closed_trades = [
            {'pnl': 100, 'symbol': 'NIFTY', 'timestamp': datetime.now()},
            {'pnl': 150, 'symbol': 'NIFTY', 'timestamp': datetime.now()},
            {'pnl': 200, 'symbol': 'NIFTY', 'timestamp': datetime.now()},
        ]
        
        # Total wins: 450, Total losses: 0
        # Profit factor should be infinite or handled as edge case
        pf = self.metrics.get_profit_factor()
        self.assertIsNotNone(pf)
    
    def test_profit_factor_with_losses(self):
        """Test profit factor with mixed trades."""
        self.metrics.closed_trades = [
            {'pnl': 100, 'symbol': 'NIFTY', 'timestamp': datetime.now()},
            {'pnl': -50, 'symbol': 'NIFTY', 'timestamp': datetime.now()},
            {'pnl': 200, 'symbol': 'NIFTY', 'timestamp': datetime.now()},
            {'pnl': -75, 'symbol': 'NIFTY', 'timestamp': datetime.now()},
        ]
        
        # Total wins: 300, Total losses: 125
        # Profit factor: 300 / 125 = 2.4
        pf = self.metrics.get_profit_factor()
        self.assertAlmostEqual(pf, 2.4, places=1)
    
    def test_win_rate_calculation(self):
        """Test win rate calculation."""
        self.metrics.closed_trades = [
            {'pnl': 100, 'symbol': 'NIFTY', 'timestamp': datetime.now()},
            {'pnl': -50, 'symbol': 'NIFTY', 'timestamp': datetime.now()},
            {'pnl': 75, 'symbol': 'NIFTY', 'timestamp': datetime.now()},
            {'pnl': -25, 'symbol': 'NIFTY', 'timestamp': datetime.now()},
        ]
        
        # 2 wins out of 4 = 50%
        wr = self.metrics.get_win_rate()
        self.assertEqual(wr, 50.0)
    
    def test_win_rate_no_trades(self):
        """Test win rate with no trades."""
        self.metrics.closed_trades = []
        wr = self.metrics.get_win_rate()
        self.assertEqual(wr, 0)
    
    def test_max_drawdown_simple(self):
        """Test max drawdown with simple equity curve."""
        # Create trades that form an equity curve
        self.metrics.closed_trades = [
            {'pnl': 100, 'symbol': 'NIFTY', 'timestamp': datetime.now()},
            {'pnl': 50, 'symbol': 'NIFTY', 'timestamp': datetime.now()},
            {'pnl': -30, 'symbol': 'NIFTY', 'timestamp': datetime.now()},
            {'pnl': -20, 'symbol': 'NIFTY', 'timestamp': datetime.now()},
        ]
        
        # Peak is 150, trough is 100
        # Max drawdown: (150-100)/150 = 0.333 = 33.3%
        dd = self.metrics.get_max_drawdown()
        self.assertIsNotNone(dd)
        self.assertGreater(dd, 0)
    
    def test_average_win_loss(self):
        """Test average win and loss calculation."""
        self.metrics.closed_trades = [
            {'pnl': 100, 'symbol': 'NIFTY', 'timestamp': datetime.now()},
            {'pnl': 200, 'symbol': 'NIFTY', 'timestamp': datetime.now()},
            {'pnl': -50, 'symbol': 'NIFTY', 'timestamp': datetime.now()},
            {'pnl': -75, 'symbol': 'NIFTY', 'timestamp': datetime.now()},
        ]
        
        avg_win, avg_loss = self.metrics.get_average_win_loss()
        
        # Average win: (100 + 200) / 2 = 150
        # Average loss: (50 + 75) / 2 = 62.5 (absolute value)
        self.assertAlmostEqual(avg_win, 150, places=0)
        self.assertAlmostEqual(avg_loss, 62.5, places=0)
    
    def test_total_pnl(self):
        """Test total P&L calculation."""
        self.metrics.closed_trades = [
            {'pnl': 100, 'symbol': 'NIFTY', 'timestamp': datetime.now()},
            {'pnl': -50, 'symbol': 'NIFTY', 'timestamp': datetime.now()},
            {'pnl': 75, 'symbol': 'NIFTY', 'timestamp': datetime.now()},
        ]
        
        # Total: 100 - 50 + 75 = 125
        total = self.metrics.get_total_pnl()
        self.assertEqual(total, 125)
    
    def test_today_pnl(self):
        """Test today's P&L calculation."""
        today = datetime.now()
        
        self.metrics.closed_trades = [
            {'pnl': 100, 'symbol': 'NIFTY', 'timestamp': today},
            {'pnl': -50, 'symbol': 'NIFTY', 'timestamp': today},
            {'pnl': 75, 'symbol': 'NIFTY', 'timestamp': today - timedelta(days=1)},
        ]
        
        # Note: The implementation uses current date, not exact timestamp match
        today_pnl = self.metrics.get_today_pnl()
        self.assertIsNotNone(today_pnl)
    
    def test_sharpe_ratio_calculation(self):
        """Test Sharpe ratio calculation."""
        # Create trades with consistent returns
        self.metrics.closed_trades = []
        base_time = datetime.now()
        
        for i in range(30):
            self.metrics.closed_trades.append({
                'pnl': 100 + (i % 2) * 50,  # Alternates between 100 and 150
                'symbol': 'NIFTY',
                'timestamp': base_time - timedelta(days=i)
            })
        
        sr = self.metrics.get_sharpe_ratio()
        self.assertIsNotNone(sr)
        self.assertIsInstance(sr, (int, float))
    
    def test_get_all_metrics(self):
        """Test getting all metrics at once."""
        self.metrics.closed_trades = [
            {'pnl': 100, 'symbol': 'NIFTY', 'timestamp': datetime.now()},
            {'pnl': -50, 'symbol': 'NIFTY', 'timestamp': datetime.now()},
            {'pnl': 75, 'symbol': 'NIFTY', 'timestamp': datetime.now()},
        ]
        
        all_metrics = self.metrics.get_all_metrics()
        
        self.assertIn('profit_factor', all_metrics)
        self.assertIn('max_drawdown', all_metrics)
        self.assertIn('sharpe_ratio', all_metrics)
        self.assertIn('win_rate', all_metrics)
        self.assertIn('average_win', all_metrics)
        self.assertIn('average_loss', all_metrics)
        self.assertIn('total_pnl', all_metrics)


class TestMetricsEdgeCases(unittest.TestCase):
    """Test edge cases in metrics calculations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.metrics = PortfolioMetrics()
    
    def test_empty_trade_list(self):
        """Test metrics with no trades."""
        self.metrics.closed_trades = []
        
        self.assertEqual(self.metrics.get_total_pnl(), 0)
        self.assertEqual(self.metrics.get_win_rate(), 0)
        self.assertEqual(self.metrics.get_max_drawdown(), 0)
    
    def test_single_trade(self):
        """Test metrics with single trade."""
        self.metrics.closed_trades = [
            {'pnl': 100, 'symbol': 'NIFTY', 'timestamp': datetime.now()}
        ]
        
        self.assertEqual(self.metrics.get_total_pnl(), 100)
        self.assertEqual(self.metrics.get_win_rate(), 100)
    
    def test_zero_pnl_trades(self):
        """Test metrics with zero P&L trades."""
        self.metrics.closed_trades = [
            {'pnl': 0, 'symbol': 'NIFTY', 'timestamp': datetime.now()},
            {'pnl': 0, 'symbol': 'NIFTY', 'timestamp': datetime.now()},
        ]
        
        self.assertEqual(self.metrics.get_total_pnl(), 0)
        self.assertEqual(self.metrics.get_win_rate(), 0)  # Zero is not a win


if __name__ == '__main__':
    unittest.main()
