# IndiPaperTrade - Local Paper Trading Platform for Indian Markets

## Overview

**IndiPaperTrade** is a professional-grade local paper trading system for Indian equity and derivatives markets. It fetches live market data from **Angel One SmartAPI** and simulates order execution internally without placing real trades.

This system is designed for:
- **Paper trading** (simulated trading)
- **Strategy backtesting** and forward testing
- **Market data analysis**
- **Portfolio tracking and PnL calculations**

---

## Market Data Engine - IMPLEMENTED ✓

The **Market Data Engine** is now fully implemented and ready to use.

### Architecture

```
Angel One SmartAPI (REST + WebSocket)
            │
            ▼
┌─────────────────────────────────────┐
│  SmartAPIDataFetcher (REST API)     │
│  WebSocketFeedHandler (Live Feeds)  │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│  MarketDataCache (Thread-safe)      │
│  Real-time Price Storage            │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│  MarketDataEngine (Orchestrator)    │
│  - initialize()                     │
│  - subscribe()                      │
│  - get_ltp()                        │
│  - register_price_callback()        │
└─────────────────────────────────────┘
```

### Key Classes

**PriceData** - Represents real-time price data:
```python
@dataclass
class PriceData:
    symbol: str           # Trading symbol
    ltp: float           # Last Traded Price
    open, high, low, close: float
    volume: int
    bid, ask: float
    timestamp: datetime
```

**MarketDataEngine** - Main interface:
```python
engine = MarketDataEngine()
engine.initialize()        # Authenticate with SmartAPI
engine.start()             # Start background processing
engine.subscribe(symbols)  # Subscribe to price feeds
engine.get_ltp(symbol)     # Get last traded price
engine.register_price_callback(callback_fn)
engine.stop()              # Cleanup and disconnect
```

### Quick Start

```python
from data_engine import MarketDataEngine, PriceData

# Initialize engine
engine = MarketDataEngine()
if not engine.initialize():
    raise RuntimeError("SmartAPI authentication failed")

# Start background processing
engine.start()

# Subscribe to instruments
engine.subscribe(["RELIANCE", "TCS", "INFY"])

# Register callback for price updates
def on_price_update(symbol: str, price_data: PriceData):
    print(f"{symbol}: LTP={price_data.ltp}, Bid={price_data.bid}, Ask={price_data.ask}")

engine.register_price_callback(on_price_update)

# Get prices
import time
time.sleep(2)
print(f"RELIANCE LTP: {engine.get_ltp('RELIANCE')}")

# Get all cached prices
all_prices = engine.get_all_prices()
for symbol, price in all_prices.items():
    print(f"{symbol}: {price.ltp}")

# Stop engine
engine.stop()
```

### Setup & Configuration

**1. Set Environment Variables:**
```bash
export SMARTAPI_CLIENT_ID="your_client_id"
export SMARTAPI_API_KEY="your_api_key"
export SMARTAPI_USERNAME="your_username"
export SMARTAPI_PASSWORD="your_password"
export SMARTAPI_FEED_TOKEN="your_feed_token"
```

**2. Install Dependencies:**
```bash
pip install -r requirements.txt
```

**3. Test the Module:**
```bash
python -m data_engine.market_data
```

### Features Implemented

✓ SmartAPI REST API authentication
✓ WebSocket real-time price feeds
✓ Thread-safe in-memory price caching
✓ Background update processing
✓ Price update callbacks
✓ Multiple subscription modes (LTP, QUOTE, FULL)
✓ Automatic fallback mechanism (REST API)
✓ Robust error handling and logging
✓ Support for equity, index, and options

### File Structure

```
data_engine/
├── __init__.py              # Package exports
└── market_data.py           # Main implementation
                             (1000+ lines)

config/
├── __init__.py
└── settings.py              # Configuration management

utils/
├── __init__.py
└── helpers.py               # Utility functions
```

---

## Next Steps

Coming soon:
- [ ] Order Simulation Engine
- [ ] Portfolio Manager
- [ ] Trade Journal & Database
- [ ] Dashboard / UI
- [ ] Main Application

---

## Support

- Angel One SmartAPI: https://smartapi.angelbroking.com/
- Python Library: https://github.com/angel-broking-suite/smartapi-python