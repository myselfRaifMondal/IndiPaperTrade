# IndiPaperTrade - Professional Paper Trading Terminal for Indian Markets

A professional-grade **PyQt6-based trading terminal** with real-time market data streaming, paper trading simulation, and portfolio management. Trade without risk using Angel One SmartAPI.

![Python](https://img.shields.io/badge/Python-3.9+-blue)
![PyQt6](https://img.shields.io/badge/PyQt6-6.x-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 🚀 Features

### Trading Terminal UI
- **Professional 3-panel layout** with resizable windows
- **Live Market Watch** with real-time price updates (6 updates/sec via WebSocket)
- **Order Entry Panel** for market and limit orders (BUY/SELL)
- **Portfolio Dashboard** with position tracking
- **Margin & Leverage Info** (5x leverage support)
- **Order Book** for trade history and execution tracking
- **Dynamic symbol subscription** - add/remove assets on-the-fly

### Real-Time Data Streaming
- **WebSocket** for tick-by-tick updates (~100-200ms latency)
- **Dual-engine architecture** (WebSocket + REST API fallback)
- **6 updates/second per symbol** in LTP mode
- **Automatic reconnection** with exponential backoff
- **Binary tick parsing** for Angel One's SmartWebSocketV2

### Trading Engine
- **Market & Limit Orders** with realistic fills
- **Order Simulation** with optional slippage & spread
- **Real-time P&L tracking** with position averaging
- **Position Management** (LONG/SHORT, OPEN/CLOSED)
- **Commission calculations** with configurable rates

### Portfolio Management
- **5x Leverage Support** - 1:5 margin multiplier
- **Margin tracking** - available, used, utilization %
- **PnL calculations** - realized, unrealized, total ROI
- **Portfolio valuation** - current value vs. entry value
- **Position averaging** - smart entry price management

### Database & Persistence
- **SQLAlchemy ORM** for data persistence
- **SQLite database** with CRUD operations
- **One-click database reset** from UI
- **Order, Position, Trade history** tracking
- **Best-effort order persistence**

---

## 📋 System Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    Trading Terminal UI (PyQt6)               │
│  ┌─────────────┬──────────────────┬──────────────────────┐  │
│  │Market Watch │   Order Panel    │  Margin/Positions   │  │
│  │  (Real-time)│ (BUY/SELL)      │   Order Book        │  │
│  └─────────────┴──────────────────┴──────────────────────┘  │
└────────────────────┬─────────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
        ▼            ▼            ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ WebSocket    │ │ REST API     │ │  Database    │
│ (Real-time)  │ │ (Fallback)   │ │ (SQLAlchemy) │
│ 6/sec        │ │ 0.5/sec      │ │ (SQLite)     │
└──────────────┘ └──────────────┘ └──────────────┘
        │            │                    │
        └────────────┼────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
        ▼                         ▼
┌──────────────────┐      ┌──────────────────┐
│ Order Simulator  │      │Portfolio Manager │
│ - Fill logic     │      │- Position track  │
│ - Slippage/Spread│      │- PnL calc        │
│ - Commissions    │      │- Margin calc     │
└──────────────────┘      └──────────────────┘
```

---

## 📦 Installation

### Prerequisites
- Python 3.9+
- macOS/Linux/Windows
- Angel One trading account

### Setup

1. **Clone repository:**
```bash
git clone https://github.com/yourusername/IndiPaperTrade.git
cd IndiPaperTrade
```

2. **Create virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Configure credentials** (create `.env`):
```bash
SMARTAPI_CLIENT_ID=your_client_id
SMARTAPI_API_KEY=your_api_key
SMARTAPI_USERNAME=your_username
SMARTAPI_PASSWORD=your_password
SMARTAPI_TOTP_KEY=your_totp_key
```

5. **Run terminal:**
```bash
python run_terminal.py
```

---

## 🎯 Quick Start

### Launch Trading Terminal
```bash
cd IndiPaperTrade
source venv/bin/activate
python run_terminal.py
```

### UI Features
| Panel | Function |
|-------|----------|
| **Market Watch** (Left) | View live prices, select symbols |
| **Order Panel** (Center) | Place BUY/SELL market/limit orders |
| **Margin Tab** | Track 5x leverage, margin usage |
| **Positions Tab** | View open positions with P&L |
| **Order Book Tab** | Trade execution history |

### Add New Symbol
1. Type symbol in "Add Symbol" field (e.g., `TATAMOTORS`)
2. Click **Add Symbol** button
3. Auto-subscribes to WebSocket real-time stream
4. Starts receiving 6 updates/second

### Place Order
1. Select symbol from Market Watch
2. Enter quantity
3. Choose MARKET or LIMIT
4. Click BUY/SELL
5. Order fills immediately (simulated)
6. Position updates in Positions tab

### Reset Database
- Click **Reset DB** button in status bar
- Clears all orders, positions, trades
- Useful for starting fresh trading session

---

## 🏗️ Project Structure

```
IndiPaperTrade/
├── ui/
│   └── trading_terminal.py        # PyQt6 terminal (800+ lines)
├── data_engine/
│   ├── market_data.py             # REST API engine
│   └── websocket_data.py          # WebSocket streaming
├── execution_engine/
│   └── order_simulator.py         # Order fill logic
├── portfolio_engine/
│   └── portfolio_manager.py       # Position tracking, PnL
├── database/
│   ├── database.py                # SQLAlchemy DB manager
│   ├── models.py                  # Order, Position, Trade models
│   └── __init__.py
├── config/
│   └── settings.py                # Configuration
├── run_terminal.py                # Entry point
├── requirements.txt               # Dependencies
└── README.md
```

---

## 📊 Key Components

### WebSocketDataEngine
Real-time price streaming with binary tick parsing:
```python
from data_engine.websocket_data import WebSocketDataEngine

ws = WebSocketDataEngine()
ws.initialize()  # Authenticate
ws.start()       # Connect
ws.subscribe(["RELIANCE", "TCS"])
ws.register_callback(on_price_update)
```

### PortfolioManager
Track positions and calculate PnL with 5x leverage:
```python
portfolio = PortfolioManager(
    initial_capital=100000,
    market_data_engine=engine,
    order_simulator=simulator,
    margin_multiplier=5.0  # 5x leverage
)
portfolio.execute_order(order)
summary = portfolio.get_summary()  # See margin usage
```

### Database Operations
```python
from database import Database

db = Database()
# Save orders
db.add_order(order)
# Get history
orders = db.get_all_orders(symbol="RELIANCE")
# Reset data
db.drop_and_recreate()
```

---

## ⚙️ Configuration

Edit `config/settings.py`:
```python
API_KEY = "your_api_key"
CLIENT_ID = "your_client_id"
INITIAL_CAPITAL = 100000  # ₹
LEVERAGE = 5.0            # 5x margin
SLIPPAGE_MODE = False     # Disable slippage
SPREAD_MODE = True        # Enable spread
```

---

## 📈 Performance

| Metric | Value |
|--------|-------|
| Price Update Frequency | 6/sec (WebSocket), 0.5/sec (REST) |
| Latency (WebSocket) | ~100-200ms |
| Order Fill Time | <50ms |
| Memory Usage | ~50MB |
| Database Size | <1MB (SQLite) |

---

## 🐛 Troubleshooting

### WebSocket Connection Failed
- Ensure `TOTP_KEY` is correct in `.env`
- Check internet connectivity
- Verify Angel One API is not rate-limited (2-sec delay between auth calls)

### Orders Not Filling
- Check symbol is subscribed in Market Watch
- Verify price data is streaming (green prices in table)
- Check Order Book for execution details

### Database Reset Not Working
- Ensure no other sessions are using the database
- Click "Reset DB" button in terminal status bar
- Database file is at `data/trading.db`

---

## 📚 Documentation

- **Real-time Streaming**: See `REALTIME_STREAMING.md`
- **Trading Guide**: See `TRADING_TERMINAL_GUIDE.md`
- **Implementation Notes**: See `STREAMING_SUMMARY.md`

---

## 🔄 Recent Updates

✅ **v1.0 Released**
- Trading Terminal UI with 3-panel layout
- Real-time WebSocket streaming (6 updates/sec)
- 5x leverage with margin tracking
- SQLAlchemy database with CRUD
- Dynamic symbol subscription
- Database reset functionality
- Dual-engine architecture (WebSocket + REST)

---

## 📝 License

MIT License - feel free to use for paper trading and learning

---

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing`)
5. Open Pull Request

---

## 📞 Support

- **Angel One SmartAPI**: https://smartapi.angelbroking.com/
- **SmartAPI Python**: https://github.com/angel-broking-suite/smartapi-python
- **Issues**: Create GitHub issue for bugs/features

---

## ⚠️ Disclaimer

**This is a PAPER TRADING platform. No real trades are placed.** Use for learning and strategy testing only. Always paper trade before live trading with real capital.