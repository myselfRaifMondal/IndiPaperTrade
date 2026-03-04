"""
Utility functions and helpers for IndiPaperTrade.
"""

import os
import logging
from datetime import datetime
from typing import Optional

from config.settings import Settings


def setup_logging() -> logging.Logger:
    """
    Configure logging for the application.
    
    Creates logs directory if it doesn't exist and sets up both
    file and console logging.
    
    Returns:
        Configured logger instance
    """
    # Create logs directory
    log_dir = os.path.dirname(Settings.LOG_FILE)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    # Configure root logger
    logger = logging.getLogger('indipapertrade')
    logger.setLevel(getattr(logging, Settings.LOG_LEVEL))
    
    # File handler
    file_handler = logging.FileHandler(Settings.LOG_FILE)
    file_handler.setLevel(logging.DEBUG)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module.
    
    Args:
        name: Module name (typically __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(f'indipapertrade.{name}')


def ensure_data_directories() -> None:
    """Create necessary data directories if they don't exist."""
    directories = [
        os.path.dirname(Settings.DATABASE_PATH),
        os.path.dirname(Settings.LOG_FILE),
        './data',
        './logs',
    ]
    
    for directory in directories:
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)


def format_currency(amount: float, currency: str = '₹') -> str:
    """
    Format an amount as currency string.
    
    Args:
        amount: Numeric amount
        currency: Currency symbol
        
    Returns:
        Formatted string
    """
    return f"{currency}{amount:,.2f}"


def format_percentage(value: float, decimals: int = 2) -> str:
    """
    Format a value as percentage string.
    
    Args:
        value: Numeric value (0-1 or 0-100)
        decimals: Number of decimal places
        
    Returns:
        Formatted percentage string
    """
    if abs(value) < 10:  # Assume it's 0-1 format
        value = value * 100
    return f"{value:.{decimals}f}%"


def is_market_open() -> bool:
    """
    Check if Indian equity market is currently open.
    
    NSE/BSE trading hours: 9:15 AM - 3:30 PM (IST) on weekdays
    
    Returns:
        True if market is open, False otherwise
    """
    from datetime import datetime
    import pytz
    
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    
    # Check if it's a weekday (Monday=0, Sunday=6)
    if now.weekday() >= 5:  # Saturday or Sunday
        return False
    
    # Check if time is between 9:15 AM and 3:30 PM
    market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
    market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
    
    return market_open <= now <= market_close


def parse_timestamp(timestamp_str: str) -> Optional[datetime]:
    """
    Parse timestamp string to datetime object.
    
    Supports common Indian market timestamp formats.
    
    Args:
        timestamp_str: Timestamp string
        
    Returns:
        datetime object or None if parsing fails
    """
    formats = [
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%dT%H:%M:%S',
        '%d-%m-%Y %H:%M:%S',
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(timestamp_str, fmt)
        except ValueError:
            continue
    
    return None


if __name__ == "__main__":
    # Test utilities
    setup_logging()
    ensure_data_directories()
    
    logger = get_logger(__name__)
    logger.info("Logging configured successfully")
    
    # Test formatting
    print(f"Currency: {format_currency(123456.78)}")
    print(f"Percentage: {format_percentage(0.1523)}")
    print(f"Market Open: {is_market_open()}")
