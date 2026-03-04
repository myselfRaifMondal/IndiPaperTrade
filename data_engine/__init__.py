"""
Data Engine Package

Provides market data fetching for IndiPaperTrade.

Main Components:
- MarketDataEngine: REST API based market data provider
- PriceData: Price information dataclass
- Mode: Subscription modes (for compatibility)
"""

from .market_data import (
    MarketDataEngine,
    PriceData,
    Mode,
)

__all__ = [
    'MarketDataEngine',
    'PriceData',
    'Mode',
    'OrderType',
]
