"""
Data Engine Package

Provides real-time market data fetching and caching for IndiPaperTrade.

Main Components:
- MarketDataEngine: Main orchestrator
- SmartAPIDataFetcher: REST API interface
- WebSocketFeedHandler: WebSocket real-time feeds
- MarketDataCache: Thread-safe price cache
- PriceData: Price information dataclass
"""

from .market_data import (
    MarketDataEngine,
    MarketDataCache,
    SmartAPIDataFetcher,
    WebSocketFeedHandler,
    PriceData,
    Mode,
    OrderType,
)

__all__ = [
    'MarketDataEngine',
    'MarketDataCache',
    'SmartAPIDataFetcher',
    'WebSocketFeedHandler',
    'PriceData',
    'Mode',
    'OrderType',
]
