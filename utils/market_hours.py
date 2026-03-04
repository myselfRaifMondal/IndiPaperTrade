"""
Market Hours Utility for Indian Stock Market.

Indian stock market trading hours:
- Pre-market: 9:00 AM - 9:15 AM (order placement only)
- Regular trading: 9:15 AM - 3:30 PM
- Post-market: 3:40 PM - 4:00 PM (order placement only)
"""

from datetime import datetime, time
import pytz
import logging

logger = logging.getLogger(__name__)

# Indian timezone
IST = pytz.timezone('Asia/Kolkata')

# Market hours configuration
MARKET_OPEN_TIME = time(9, 15)    # 9:15 AM
MARKET_CLOSE_TIME = time(15, 30)  # 3:30 PM
PRE_MARKET_OPEN = time(9, 0)      # 9:00 AM
POST_MARKET_CLOSE = time(16, 0)   # 4:00 PM


class MarketHoursChecker:
    """Check if current time is within market trading hours."""
    
    @staticmethod
    def get_current_time() -> datetime:
        """Get current time in IST."""
        return datetime.now(IST)
    
    @staticmethod
    def is_market_open() -> bool:
        """
        Check if market is currently open for trading.
        
        Returns:
            True if market is open (9:15 AM - 3:30 PM IST)
        """
        now = MarketHoursChecker.get_current_time()
        current_time = now.time()
        
        # Check if it's a weekday (Monday=0, Sunday=6)
        if now.weekday() >= 5:  # Saturday or Sunday
            return False
        
        # Check if within trading hours
        return MARKET_OPEN_TIME <= current_time <= MARKET_CLOSE_TIME
    
    @staticmethod
    def is_pre_market() -> bool:
        """Check if in pre-market session (9:00 AM - 9:15 AM)."""
        now = MarketHoursChecker.get_current_time()
        current_time = now.time()
        
        if now.weekday() >= 5:
            return False
        
        return PRE_MARKET_OPEN <= current_time < MARKET_OPEN_TIME
    
    @staticmethod
    def is_post_market() -> bool:
        """Check if in post-market session (3:40 PM - 4:00 PM)."""
        now = MarketHoursChecker.get_current_time()
        current_time = now.time()
        
        if now.weekday() >= 5:
            return False
        
        return time(15, 40) <= current_time <= POST_MARKET_CLOSE
    
    @staticmethod
    def get_market_status() -> str:
        """
        Get current market status.
        
        Returns:
            "OPEN" | "PRE_MARKET" | "POST_MARKET" | "CLOSED" | "WEEKEND"
        """
        now = MarketHoursChecker.get_current_time()
        
        if now.weekday() >= 5:
            return "WEEKEND"
        
        if MarketHoursChecker.is_market_open():
            return "OPEN"
        elif MarketHoursChecker.is_pre_market():
            return "PRE_MARKET"
        elif MarketHoursChecker.is_post_market():
            return "POST_MARKET"
        else:
            return "CLOSED"
    
    @staticmethod
    def time_until_market_open() -> str:
        """Get time remaining until market opens."""
        now = MarketHoursChecker.get_current_time()
        
        if now.weekday() >= 5:
            # Calculate days until Monday
            days_until_monday = (7 - now.weekday()) % 7
            if days_until_monday == 0:
                days_until_monday = 1
            return f"{days_until_monday} day(s)"
        
        market_open = now.replace(
            hour=MARKET_OPEN_TIME.hour,
            minute=MARKET_OPEN_TIME.minute,
            second=0,
            microsecond=0
        )
        
        if now.time() > MARKET_CLOSE_TIME:
            # Next trading day
            return "Next trading day"
        elif now.time() < MARKET_OPEN_TIME:
            # Today
            delta = market_open - now
            hours = delta.seconds // 3600
            minutes = (delta.seconds % 3600) // 60
            return f"{hours}h {minutes}m"
        else:
            return "Market is open"
    
    @staticmethod
    def time_until_market_close() -> str:
        """Get time remaining until market closes."""
        now = MarketHoursChecker.get_current_time()
        
        if not MarketHoursChecker.is_market_open():
            return "Market closed"
        
        market_close = now.replace(
            hour=MARKET_CLOSE_TIME.hour,
            minute=MARKET_CLOSE_TIME.minute,
            second=0,
            microsecond=0
        )
        
        delta = market_close - now
        hours = delta.seconds // 3600
        minutes = (delta.seconds % 3600) // 60
        return f"{hours}h {minutes}m"


def get_market_status_message() -> str:
    """Get formatted market status message."""
    status = MarketHoursChecker.get_market_status()
    
    if status == "OPEN":
        time_left = MarketHoursChecker.time_until_market_close()
        return f"Market OPEN - Closes in {time_left}"
    elif status == "PRE_MARKET":
        time_until = MarketHoursChecker.time_until_market_open()
        return f"Pre-Market - Opens in {time_until}"
    elif status == "POST_MARKET":
        return "Post-Market Session"
    elif status == "WEEKEND":
        return "Weekend - Market Closed"
    else:
        time_until = MarketHoursChecker.time_until_market_open()
        return f"Market CLOSED - Opens in {time_until}"
