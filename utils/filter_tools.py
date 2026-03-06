"""
Filter tools for trading data - filtering trades and metrics by date range and other criteria.

Provides functionality to:
- Filter trades by date range
- Filter by symbol, side, profitability
- Group trades by timeframe
- Generate statistics for filtered data
"""

import logging
from typing import List, Dict, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DateRange:
    """Represents a date range."""
    start_date: datetime
    end_date: datetime
    
    def contains(self, date: datetime) -> bool:
        """Check if date is within range."""
        return self.start_date <= date <= self.end_date
    
    def __str__(self) -> str:
        return f"{self.start_date.date()} to {self.end_date.date()}"


class FilterTools:
    """Tools for filtering and analyzing trading data."""
    
    @staticmethod
    def filter_by_date_range(trades: List[Dict], start_date: datetime, 
                            end_date: datetime, date_key: str = 'timestamp') -> List[Dict]:
        """
        Filter trades by date range.
        
        Args:
            trades: List of trade dictionaries
            start_date: Start of range
            end_date: End of range
            date_key: Key in trade dict containing date
        
        Returns:
            Filtered list of trades
        """
        try:
            filtered = []
            for trade in trades:
                trade_date = trade.get(date_key)
                
                # Handle both string and datetime
                if isinstance(trade_date, str):
                    trade_date = datetime.fromisoformat(trade_date)
                
                if trade_date and start_date <= trade_date <= end_date:
                    filtered.append(trade)
            
            logger.info(f"Filtered {len(filtered)} trades from {len(trades)} by date range")
            return filtered
        
        except Exception as e:
            logger.error(f"Error filtering by date range: {e}")
            return trades
    
    @staticmethod
    def filter_by_symbol(trades: List[Dict], symbols: List[str]) -> List[Dict]:
        """Filter trades by symbols."""
        try:
            filtered = [t for t in trades if t.get('symbol') in symbols]
            logger.info(f"Filtered to {len(filtered)} trades for symbols: {symbols}")
            return filtered
        except Exception as e:
            logger.error(f"Error filtering by symbol: {e}")
            return trades
    
    @staticmethod
    def filter_by_side(trades: List[Dict], side: str) -> List[Dict]:
        """
        Filter trades by side (LONG/SHORT or BUY/SELL).
        
        Args:
            trades: List of trades
            side: 'LONG', 'SHORT', 'BUY', or 'SELL'
        
        Returns:
            Filtered trades
        """
        try:
            filtered = [t for t in trades if t.get('side') == side or t.get('type') == side]
            logger.info(f"Filtered to {len(filtered)} {side} trades")
            return filtered
        except Exception as e:
            logger.error(f"Error filtering by side: {e}")
            return trades
    
    @staticmethod
    def filter_winning_trades(trades: List[Dict], pnl_key: str = 'pnl') -> List[Dict]:
        """Filter to only profitable trades."""
        try:
            filtered = [t for t in trades if float(t.get(pnl_key, 0)) > 0]
            logger.info(f"Found {len(filtered)} winning trades from {len(trades)}")
            return filtered
        except Exception as e:
            logger.error(f"Error filtering winning trades: {e}")
            return trades
    
    @staticmethod
    def filter_losing_trades(trades: List[Dict], pnl_key: str = 'pnl') -> List[Dict]:
        """Filter to only losing trades."""
        try:
            filtered = [t for t in trades if float(t.get(pnl_key, 0)) < 0]
            logger.info(f"Found {len(filtered)} losing trades from {len(trades)}")
            return filtered
        except Exception as e:
            logger.error(f"Error filtering losing trades: {e}")
            return trades
    
    @staticmethod
    def filter_by_pnl_range(trades: List[Dict], min_pnl: float, max_pnl: float, 
                           pnl_key: str = 'pnl') -> List[Dict]:
        """Filter trades within a P&L range."""
        try:
            filtered = [
                t for t in trades 
                if min_pnl <= float(t.get(pnl_key, 0)) <= max_pnl
            ]
            logger.info(f"Filtered to {len(filtered)} trades in P&L range [{min_pnl}, {max_pnl}]")
            return filtered
        except Exception as e:
            logger.error(f"Error filtering by P&L range: {e}")
            return trades
    
    @staticmethod
    def group_trades_by_symbol(trades: List[Dict]) -> Dict[str, List[Dict]]:
        """Group trades by symbol."""
        try:
            grouped = {}
            for trade in trades:
                symbol = trade.get('symbol', 'UNKNOWN')
                if symbol not in grouped:
                    grouped[symbol] = []
                grouped[symbol].append(trade)
            
            logger.info(f"Grouped {len(trades)} trades into {len(grouped)} symbols")
            return grouped
        except Exception as e:
            logger.error(f"Error grouping by symbol: {e}")
            return {}
    
    @staticmethod
    def group_trades_by_hour(trades: List[Dict], date_key: str = 'timestamp') -> Dict[str, List[Dict]]:
        """Group trades by hour."""
        try:
            grouped = {}
            for trade in trades:
                trade_date = trade.get(date_key)
                
                if isinstance(trade_date, str):
                    trade_date = datetime.fromisoformat(trade_date)
                
                if not trade_date:
                    continue
                
                hour_key = trade_date.strftime("%Y-%m-%d %H:00")
                if hour_key not in grouped:
                    grouped[hour_key] = []
                grouped[hour_key].append(trade)
            
            logger.info(f"Grouped {len(trades)} trades into {len(grouped)} hours")
            return grouped
        except Exception as e:
            logger.error(f"Error grouping by hour: {e}")
            return {}
    
    @staticmethod
    def calculate_filtered_stats(trades: List[Dict], pnl_key: str = 'pnl') -> Dict:
        """
        Calculate statistics for filtered trades.
        
        Args:
            trades: List of trades
            pnl_key: Key containing P&L values
        
        Returns:
            Dictionary with statistics
        """
        try:
            if not trades:
                return {
                    'total_trades': 0,
                    'total_pnl': 0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'win_rate': 0,
                    'avg_win': 0,
                    'avg_loss': 0,
                    'largest_win': 0,
                    'largest_loss': 0,
                }
            
            pnls = [float(t.get(pnl_key, 0)) for t in trades]
            winning = [p for p in pnls if p > 0]
            losing = [p for p in pnls if p < 0]
            
            stats = {
                'total_trades': len(trades),
                'total_pnl': sum(pnls),
                'winning_trades': len(winning),
                'losing_trades': len(losing),
                'win_rate': (len(winning) / len(trades) * 100) if trades else 0,
                'avg_win': (sum(winning) / len(winning)) if winning else 0,
                'avg_loss': (sum(losing) / len(losing)) if losing else 0,
                'largest_win': max(winning) if winning else 0,
                'largest_loss': min(losing) if losing else 0,
            }
            
            logger.info(f"Calculated stats: {len(trades)} trades, {stats['total_pnl']:.2f} total P&L")
            return stats
        
        except Exception as e:
            logger.error(f"Error calculating stats: {e}")
            return {}


# Global filter tools instance
_filter_tools: Optional[FilterTools] = None


def get_filter_tools() -> FilterTools:
    """Get filter tools instance."""
    global _filter_tools
    if _filter_tools is None:
        _filter_tools = FilterTools()
    return _filter_tools
