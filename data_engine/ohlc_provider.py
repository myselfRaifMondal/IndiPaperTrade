"""
OHLC Data Provider - Fetches and manages candlestick data from market data engine.

Provides OHLC data aggregation for different timeframes:
- 1 minute candles
- 5 minute candles
- 15 minute candles
- 1 hour candles
- Daily candles
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import threading
import json
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class OHLCProvider:
    """
    Provides OHLC (Open, High, Low, Close) candlestick data.
    
    Features:
    - Real-time price aggregation into candles
    - Multiple timeframe support
    - Candle caching for performance
    - Data persistence to disk
    """
    
    def __init__(self, data_dir: Optional[str] = None):
        """Initialize OHLC provider."""
        self.lock = threading.RLock()
        
        # Data directory for persistence
        self.data_dir = data_dir or "data/ohlc_cache"
        Path(self.data_dir).mkdir(parents=True, exist_ok=True)
        
        # Store candles by symbol and timeframe
        # Structure: {symbol: {timeframe: [candle1, candle2, ...]}}
        self.candles: Dict[str, Dict[str, List[Dict]]] = defaultdict(lambda: defaultdict(list))
        
        # Current price tracking for real-time candle building
        # Structure: {symbol: {timeframe: current_candle_dict}}
        self.current_candles: Dict[str, Dict[str, Dict]] = defaultdict(lambda: defaultdict(dict))
        
        # Timestamp of last price update per symbol
        self.last_update: Dict[str, datetime] = {}
        
        # Cache metadata (load times)
        self.cache_metadata: Dict[str, Dict[str, datetime]] = defaultdict(dict)
        
        logger.info(f"OHLC Provider initialized with data_dir={self.data_dir}")
    
    def add_price_update(self, symbol: str, price: float, timestamp: Optional[datetime] = None):
        """
        Add a price update to build candles.
        
        Args:
            symbol: Trading symbol
            price: Current LTP
            timestamp: Update timestamp (default: now)
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        try:
            with self.lock:
                self.last_update[symbol] = timestamp
                
                # Update candles for all timeframes
                for timeframe in ['1m', '5m', '15m', '1h', '1d']:
                    self._update_candle(symbol, timeframe, price, timestamp)
        
        except Exception as e:
            logger.error(f"Error adding price update for {symbol}: {e}")
    
    def _update_candle(self, symbol: str, timeframe: str, price: float, timestamp: datetime):
        """
        Update candle for a specific timeframe.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe ('1m', '5m', '15m', '1h', '1d')
            price: Current price
            timestamp: Update timestamp
        """
        try:
            # Get or create current candle
            current = self.current_candles[symbol][timeframe]
            
            # Calculate candle period
            period = self._get_period_seconds(timeframe)
            
            # Check if we need to close current candle and start new one
            if current:
                candle_start = current.get('timestamp')
                if candle_start and (timestamp - candle_start).total_seconds() >= period:
                    # Close current candle
                    self.candles[symbol][timeframe].append(current)
                    
                    # Remove old candles (keep last 500)
                    if len(self.candles[symbol][timeframe]) > 500:
                        self.candles[symbol][timeframe] = self.candles[symbol][timeframe][-500:]
                    
                    # Start new candle
                    current = {}

            
            # Update current candle
            if not current:
                # New candle
                current['timestamp'] = timestamp
                current['open'] = price
                current['high'] = price
                current['low'] = price
                current['close'] = price
                current['volume'] = 1
            else:
                # Update existing candle
                current['close'] = price
                current['high'] = max(current['high'], price)
                current['low'] = min(current['low'], price)
                current['volume'] = current.get('volume', 1) + 1
            
            self.current_candles[symbol][timeframe] = current
        
        except Exception as e:
            logger.error(f"Error updating candle {symbol} {timeframe}: {e}")
    
    def get_candles(self, symbol: str, timeframe: str = '5m', limit: int = 100) -> List[Dict]:
        """
        Get candlestick data for a symbol.
        
        Args:
            symbol: Trading symbol
            timeframe: Candle timeframe ('1m', '5m', '15m', '1h', '1d')
            limit: Number of candles to return (default 100)
        
        Returns:
            List of candle dicts with keys: timestamp, open, high, low, close, volume
        """
        try:
            with self.lock:
                candles = self.candles[symbol][timeframe]
                
                # Return last N candles
                result = candles[-limit:] if len(candles) > limit else candles
                
                # Include current candle if it exists
                current = self.current_candles[symbol][timeframe]
                if current:
                    result = result + [current]
                
                logger.debug(f"Returning {len(result)} candles for {symbol} {timeframe}")
                return result
        
        except Exception as e:
            logger.error(f"Error getting candles for {symbol}: {e}")
            return []
    
    def get_latest_candle(self, symbol: str, timeframe: str = '5m') -> Optional[Dict]:
        """
        Get the latest candlestick.
        
        Args:
            symbol: Trading symbol
            timeframe: Candle timeframe
        
        Returns:
            Latest candle dict or None
        """
        try:
            with self.lock:
                current = self.current_candles[symbol][timeframe]
                if current:
                    return current
                
                candles = self.candles[symbol][timeframe]
                return candles[-1] if candles else None
        
        except Exception as e:
            logger.error(f"Error getting latest candle for {symbol}: {e}")
            return None
    
    def get_candle_count(self, symbol: str, timeframe: str = '5m') -> int:
        """
        Get total number of candles for a symbol.
        
        Args:
            symbol: Trading symbol
            timeframe: Candle timeframe
        
        Returns:
            Number of candles
        """
        try:
            with self.lock:
                count = len(self.candles[symbol][timeframe])
                if self.current_candles[symbol][timeframe]:
                    count += 1
                return count
        except:
            return 0
    
    def clear_symbol(self, symbol: str):
        """
        Clear all candle data for a symbol.
        
        Args:
            symbol: Trading symbol
        """
        try:
            with self.lock:
                if symbol in self.candles:
                    del self.candles[symbol]
                if symbol in self.current_candles:
                    del self.current_candles[symbol]
                logger.info(f"Cleared candles for {symbol}")
        except Exception as e:
            logger.error(f"Error clearing candles for {symbol}: {e}")
    
    @staticmethod
    def _get_period_seconds(timeframe: str) -> int:
        """
        Get period in seconds for a timeframe.
        
        Args:
            timeframe: Timeframe string ('1m', '5m', '15m', '1h', '1d')
        
        Returns:
            Period in seconds
        """
        periods = {
            '1m': 60,
            '5m': 300,
            '15m': 900,
            '1h': 3600,
            '1d': 86400
        }
        return periods.get(timeframe, 300)
    
    def save_to_disk(self, symbol: str, timeframe: str = None):
        """
        Save candle data to disk for persistence.
        
        Args:
            symbol: Trading symbol
            timeframe: Specific timeframe to save (if None, saves all)
        """
        try:
            with self.lock:
                timeframes = [timeframe] if timeframe else ['1m', '5m', '15m', '1h', '1d']
                
                for tf in timeframes:
                    candles = self.candles[symbol][tf]
                    if not candles:
                        continue
                    
                    # Convert datetime objects to ISO format
                    candles_data = []
                    for c in candles:
                        c_copy = c.copy()
                        if isinstance(c_copy.get('timestamp'), datetime):
                            c_copy['timestamp'] = c_copy['timestamp'].isoformat()
                        candles_data.append(c_copy)
                    
                    # Save to file
                    file_path = os.path.join(self.data_dir, f"{symbol}_{tf}.json")
                    with open(file_path, 'w') as f:
                        json.dump(candles_data, f)
                    
                    self.cache_metadata[symbol][tf] = datetime.now()
                    logger.info(f"Saved {len(candles)} candles for {symbol} {tf}")
        
        except Exception as e:
            logger.error(f"Error saving candles to disk: {e}")
    
    def load_from_disk(self, symbol: str, timeframe: str = None):
        """
        Load candle data from disk.
        
        Args:
            symbol: Trading symbol
            timeframe: Specific timeframe to load (if None, loads all)
        
        Returns:
            Number of candles loaded
        """
        try:
            with self.lock:
                timeframes = [timeframe] if timeframe else ['1m', '5m', '15m', '1h', '1d']
                total_loaded = 0
                
                for tf in timeframes:
                    file_path = os.path.join(self.data_dir, f"{symbol}_{tf}.json")
                    
                    if not os.path.exists(file_path):
                        continue
                    
                    with open(file_path, 'r') as f:
                        candles_data = json.load(f)
                    
                    # Convert ISO strings back to datetime
                    for c in candles_data:
                        if isinstance(c.get('timestamp'), str):
                            c['timestamp'] = datetime.fromisoformat(c['timestamp'])
                    
                    self.candles[symbol][tf] = candles_data
                    total_loaded += len(candles_data)
                    self.cache_metadata[symbol][tf] = datetime.now()
                    logger.info(f"Loaded {len(candles_data)} candles for {symbol} {tf}")
                
                return total_loaded
        
        except Exception as e:
            logger.error(f"Error loading candles from disk: {e}")
            return 0
    
    def get_cache_age(self, symbol: str, timeframe: str) -> Optional[timedelta]:
        """
        Get age of cached data.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
        
        Returns:
            Age of cache or None
        """
        try:
            load_time = self.cache_metadata.get(symbol, {}).get(timeframe)
            if load_time:
                return datetime.now() - load_time
            return None
        except:
            return None
    
    def is_cache_fresh(self, symbol: str, timeframe: str, max_age_seconds: int = 3600) -> bool:
        """
        Check if cached data is still fresh.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            max_age_seconds: Maximum age in seconds (default 1 hour)
        
        Returns:
            True if cache is fresh, False otherwise
        """
        try:
            age = self.get_cache_age(symbol, timeframe)
            if age is None:
                return False
            return age.total_seconds() < max_age_seconds
        except:
            return False


# Global OHLC provider instance
_ohlc_provider: Optional[OHLCProvider] = None


def get_ohlc_provider() -> OHLCProvider:
    """Get or create global OHLC provider instance."""
    global _ohlc_provider
    if _ohlc_provider is None:
        _ohlc_provider = OHLCProvider()
    return _ohlc_provider


def init_ohlc_provider() -> OHLCProvider:
    """Initialize and return OHLC provider."""
    global _ohlc_provider
    _ohlc_provider = OHLCProvider()
    return _ohlc_provider
