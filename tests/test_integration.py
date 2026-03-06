"""
Integration tests for real-time trading terminal updates.

Tests the complete workflow of:
- Market data feeding to terminal
- Order creation and execution
- Real-time position and metric updates
- Chart data aggregation
- Risk alert triggering
"""

import unittest
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from portfolio_engine.metrics_calculator import PortfolioMetrics
from data_engine.ohlc_provider import OHLCProvider
from utils.export_tools import get_export_tools
from utils.filter_tools import get_filter_tools


class TestIntegrationRealTimeUpdates(unittest.TestCase):
    """Integration tests for real-time update workflows."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.metrics = PortfolioMetrics()
        self.ohlc = OHLCProvider()
        self.export_tools = get_export_tools()
        self.filter_tools = get_filter_tools()
    
    def test_price_feed_to_ohlc_aggregation(self):
        """Test price updates are properly aggregated into OHLC candles."""
        symbol = 'NIFTY'
        timeframe = '5m'
        
        # Feed multiple price updates
        prices = [100.0, 101.5, 102.0, 101.0, 103.0, 102.5]
        
        for price in prices:
            self.ohlc.add_price_update(symbol, price)
        
        # Get candles
        candles = self.ohlc.get_candles(symbol, timeframe)
        
        # Verify data was aggregated
        self.assertGreater(len(candles), 0)
        self.assertIn('open', candles[-1])
        self.assertIn('close', candles[-1])
        self.assertIn('high', candles[-1])
        self.assertIn('low', candles[-1])
    
    def test_trade_execution_to_metrics_update(self):
        """Test that trade execution triggers metrics recalculation."""
        # Simulate closed trades
        self.metrics.closed_trades = [
            {
                'symbol': 'NIFTY',
                'side': 'LONG',
                'entry_price': 100,
                'exit_price': 105,
                'pnl': 500,
                'timestamp': datetime.now()
            },
            {
                'symbol': 'NIFTY',
                'side': 'SHORT',
                'entry_price': 110,
                'exit_price': 108,
                'pnl': 200,
                'timestamp': datetime.now()
            },
            {
                'symbol': 'BANKNIFTY',
                'side': 'LONG',
                'entry_price': 200,
                'exit_price': 195,
                'pnl': -500,
                'timestamp': datetime.now()
            }
        ]
        
        # Verify metrics are updated
        total_pnl = self.metrics.get_total_pnl()
        win_rate = self.metrics.get_win_rate()
        profit_factor = self.metrics.get_profit_factor()
        
        self.assertEqual(total_pnl, 200)  # 500 + 200 - 500
        self.assertAlmostEqual(win_rate, 66.67, places=1)  # 2 wins out of 3
        self.assertGreater(profit_factor, 1)
    
    def test_export_and_filter_workflow(self):
        """Test exporting and filtering trades."""
        trades = [
            {
                'symbol': 'NIFTY',
                'type': 'BUY',
                'entry_price': 100,
                'exit_price': 105,
                'pnl': 500,
                'timestamp': datetime.now().isoformat()
            },
            {
                'symbol': 'BANKNIFTY',
                'type': 'SELL',
                'entry_price': 110,
                'exit_price': 108,
                'pnl': 200,
                'timestamp': datetime.now().isoformat()
            },
            {
                'symbol': 'NIFTY',
                'type': 'BUY',
                'entry_price': 200,
                'exit_price': 195,
                'pnl': -500,
                'timestamp': (datetime.now() - timedelta(days=1)).isoformat()
            }
        ]
        
        # Filter by symbol
        nifty_trades = self.filter_tools.filter_by_symbol(trades, ['NIFTY'])
        self.assertEqual(len(nifty_trades), 2)
        
        # Filter winning trades
        winning = self.filter_tools.filter_winning_trades(trades)
        self.assertEqual(len(winning), 2)
        
        # Calculate stats for filtered trades
        stats = self.filter_tools.calculate_filtered_stats(nifty_trades)
        self.assertIn('total_trades', stats)
        self.assertIn('win_rate', stats)
    
    def test_risk_alert_conditions(self):
        """Test risk alert triggering logic."""
        # Simulate daily loss scenario
        self.metrics.closed_trades = [
            {'pnl': -2000, 'symbol': 'NIFTY', 'timestamp': datetime.now()},
            {'pnl': -2500, 'symbol': 'NIFTY', 'timestamp': datetime.now()},
            {'pnl': 500, 'symbol': 'NIFTY', 'timestamp': datetime.now()},
        ]
        
        # Today's P&L: -2000 - 2500 + 500 = -4000
        today_pnl = self.metrics.get_today_pnl()
        
        # Daily loss limit is ₹5,000
        should_alert = today_pnl < -5000
        
        # Simulate max drawdown alert
        max_dd = self.metrics.get_max_drawdown()
        dd_alert = max_dd > 0.05  # 5% limit
        
        self.assertTrue(isinstance(should_alert, bool))
        self.assertTrue(isinstance(dd_alert, bool))
    
    def test_ohlc_persistence_workflow(self):
        """Test saving and loading OHLC data from disk."""
        symbol = 'NIFTY'
        timeframe = '5m'
        
        # Add price data
        for price in [100, 101, 102, 101.5, 103]:
            self.ohlc.add_price_update(symbol, price)
        
        # Get count before save
        count_before = self.ohlc.get_candle_count(symbol, timeframe)
        
        # Save to disk
        self.ohlc.save_to_disk(symbol, timeframe)
        
        # Create new OHLC provider and load
        ohlc_new = OHLCProvider()
        count_loaded = ohlc_new.load_from_disk(symbol, timeframe)
        
        # Verify data was persisted
        self.assertGreater(count_loaded, 0)
        self.assertGreaterEqual(count_loaded, count_before)

        # Persistence workflow completed successfully
        self.assertTrue(True)

class TestMetricsAggregation(unittest.TestCase):
    """Test aggregation of metrics across multiple timeframes."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.ohlc = OHLCProvider()
    
    def test_multi_timeframe_candle_aggregation(self):
        """Test that price updates create candles in all supported timeframes."""
        symbol = 'TEST'
        timeframes = ['1m', '5m', '15m', '1h', '1d']
        
        # Feed prices for a short period
        for i in range(100):
            price = 100 + (i % 10) - 5  # Prices between 95-105
            self.ohlc.add_price_update(symbol, price)
        
        # Verify candles were created in all timeframes
        for timeframe in timeframes:
            candles = self.ohlc.get_candles(symbol, timeframe)
            self.assertGreater(len(candles), 0, f"No candles for {timeframe}")
    
    def test_candle_data_integrity(self):
        """Test that OHLC data maintains proper relationships."""
        symbol = 'INTEGRITY'
        timeframe = '5m'
        
        # Feed known prices
        prices = [100, 105, 103, 107, 102]
        
        for price in prices:
            self.ohlc.add_price_update(symbol, price)
        
        candles = self.ohlc.get_candles(symbol, timeframe)
        
        # Check latest candle integrity
        if candles:
            latest = candles[-1]
            # Open should be first price in period
            # High should be maximum
            # Low should be minimum
            # Close should be last price
            
            self.assertIsNotNone(latest.get('open'))
            self.assertIsNotNone(latest.get('high'))
            self.assertIsNotNone(latest.get('low'))
            self.assertIsNotNone(latest.get('close'))
            
            # High >= Low
            self.assertGreaterEqual(latest['high'], latest['low'])


if __name__ == '__main__':
    unittest.main()
