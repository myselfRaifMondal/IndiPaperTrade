# IndiPaperTrade - Professional Paper Trading Terminal for Indian Markets

A professional-grade **PyQt6-based trading terminal** with real-time market data streaming, paper trading simulation, and portfolio management. Trade without risk using Angel One SmartAPI.

![Python](https://img.shields.io/badge/Python-3.9+-blue)
![PyQt6](https://img.shields.io/badge/PyQt6-6.x-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 🚀 Features

### Trading Terminal UI
- **Professional 3-panel layout** with resizable windows
- **Market Clock Widget** - Real-time IST clock with market status (OPEN/CLOSED/PRE_MARKET/POST_MARKET)
- **Live Market Watch** with real-time price updates (6 updates/sec via WebSocket)
- **Order Entry Panel** for advanced order types (Market, Limit, Stop Loss, Stop Limit, Bracket)
- **Portfolio Dashboard** with position tracking
- **Margin & Leverage Info** (5x leverage support)
- **Order Book** for trade history and execution tracking
- **Dynamic symbol subscription** - add/remove assets on-the-fly
- **Market Hours Enforcement** - Trading restricted to 9:15 AM - 3:30 PM IST

### Real-Time Data Streaming
- **WebSocket** for tick-by-tick updates (~100-200ms latency)
- **Dual-engine architecture** (WebSocket + REST API fallback)
- **6 updates/second per symbol** in LTP mode
- **Automatic reconnection** with exponential backoff
- **Binary tick parsing** for Angel One's SmartWebSocketV2

### Advanced Trading Engine
- **5 Order Types**: Market, Limit, Stop Loss, Stop Limit, Bracket orders
- **Order Lifecycle Management** - PENDING → OPEN → TRIGGERED → FILLED
- **Partial Fill Support** with remaining quantity tracking
- **Order Simulation** with realistic fills, slippage & spread
- **Real-time P&L tracking** with position averaging
- **Position Management** (LONG/SHORT, OPEN/CLOSED)
- **Commission calculations** with configurable rates

### Portfolio Management & Risk
- **5x Leverage Support** - 1:5 margin multiplier
- **Margin tracking** - available, used, utilization %
- **PnL Engine** - Realized/Unrealized PnL, daily PnL tracking
- **Risk Metrics**:
  - Maximum drawdown tracking (₹ & %)
  - Win rate calculation
  - Profit factor monitoring
  - Sharpe ratio (risk-adjusted returns)
  - Daily loss limits (default 3%)
  - Position exposure tracking
- **Performance Analytics**:
  - Trade statistics (wins/losses)
  - Average profit/loss per trade
  - Largest win/loss tracking
  - Average holding time
  - ROI calculation

### Alert & Notification System
- **Price Alerts** - Trigger on price levels (ABOVE/BELOW)
- **Trade Alerts** - Order fills, stop loss hits
- **Risk Alerts** - Daily loss exceeded, drawdown threshold
- **System Alerts** - Connection lost, data interruption
- **Priority Levels** - LOW, MEDIUM, HIGH, CRITICAL
- **Callback Support** - Custom handlers for alert events

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
├── execution/
│   ├── order_types.py             # Advanced order types (Market, Limit, Stop, Bracket)
│   └── __init__.py
├── execution_engine/
│   └── order_simulator.py         # Order fill logic
├── portfolio/
│   ├── pnl_engine.py              # PnL calculations (realized/unrealized)
│   └── __init__.py
├── portfolio_engine/
│   └── portfolio_manager.py       # Position tracking, PnL
├── risk/
│   ├── risk_engine.py             # Risk metrics (drawdown, Sharpe, profit factor)
│   └── __init__.py
├── analytics/
│   ├── performance_analyzer.py    # Trade statistics & performance metrics
│   └── __init__.py
├── alerts/
│   ├── alert_manager.py           # Alert system (price, trade, risk alerts)
│   └── __init__.py
├── utils/
│   └── market_hours.py            # Market hours checking (9:15 AM - 3:30 PM IST)
├── database/
│   ├── database.py                # SQLAlchemy DB manager
│   ├── models.py                  # Order, Position, Trade models
│   └── __init__.py
├── config/
│   └── settings.py                # Configuration
├── examples/
│   └── advanced_trading_features.py  # Examples for all advanced components
├── run_terminal.py                # Entry point
├── requirements.txt               # Dependencies
└── README.md
```

---

## 📊 Key Components

### Market Hours & Clock
Real-time market status with IST timezone:
```python
from utils.market_hours import MarketHoursChecker, get_market_status_message

status = MarketHoursChecker.get_market_status()  # OPEN/CLOSED/PRE_MARKET/WEEKEND
is_open = MarketHoursChecker.is_market_open()    # True only 9:15 AM - 3:30 PM IST
message = get_market_status_message()            # Human-readable status
```

### Advanced Order Types
```python
from execution.order_types import OrderFactory, OrderSide

# Market order
market = OrderFactory.create_market_order("RELIANCE", OrderSide.BUY, 10)

# Limit order
limit = OrderFactory.create_limit_order("TCS", OrderSide.SELL, 5, 3500.0)

# Stop loss order
stop = OrderFactory.create_stop_loss_order("INFY", OrderSide.SELL, 20, 1400.0)

# Stop limit order
stop_limit = OrderFactory.create_stop_limit_order("HDFCBANK", OrderSide.BUY, 15, 1600.0, 1605.0)

# Bracket order (entry + SL + TP)
bracket = OrderFactory.create_bracket_order("SBIN", OrderSide.BUY, 50, 600.0, 595.0, 605.0)
```

### PnL Engine
```python
from portfolio.pnl_engine import PnLEngine

pnl_engine = PnLEngine()

# Unrealized PnL
unrealized = pnl_engine.calculate_unrealized_pnl(
    entry_price=1340.0,
    current_price=1360.0,
    quantity=10,
    side="LONG"
)

# Realized PnL
realized = pnl_engine.calculate_realized_pnl(
    entry_price=1340.0,
    exit_price=1360.0,
    quantity=10,
    side="LONG",
    commission=50.0
)
```

### Risk Engine
```python
from risk.risk_engine import RiskEngine

risk = RiskEngine(initial_capital=100000, max_daily_loss_pct=3.0)

# Update equity
risk.update_equity(current_equity)

# Get risk metrics
drawdown = risk.max_drawdown           # Maximum loss from peak
drawdown_pct = risk.max_drawdown_pct  # As percentage
sharpe = risk.calculate_sharpe_ratio() # Risk-adjusted return
profit_factor = risk.calculate_profit_factor(trades)  # Profit/Loss ratio

# Check daily loss limit
exceeded = risk.check_daily_loss_limit(daily_pnl)
```

### Performance Analyzer
```python
from analytics.performance_analyzer import PerformanceAnalyzer

analyzer = PerformanceAnalyzer()
analyzer.add_trade(entry_price, exit_price, quantity)

metrics = analyzer.get_metrics()
print(f"Win Rate: {metrics.win_rate:.2%}")
print(f"Avg Profit: ₹{metrics.avg_profit:,.2f}")
print(f"ROI: {metrics.roi:.2%}")
```

### Alert System
```python
from alerts.alert_manager import AlertManager, AlertType, AlertPriority

alert_mgr = AlertManager()

# Price alert
alert_mgr.add_price_alert("NIFTY", 22500.0, "ABOVE")

# Trade alert
alert_mgr.alert_order_filled("RELIANCE", "BUY", 10, 2750.0)

# Risk alert
alert_mgr.alert_daily_loss_exceeded(daily_loss=3500, limit=3000)

# Get all alerts
for alert in alert_mgr.alerts:
    print(f"[{alert.priority}] {alert.title}: {alert.message}")
```

### WebSocketDataEngine
Real-time price streaming:
```python
from data_engine.websocket_data import WebSocketDataEngine

ws = WebSocketDataEngine()
ws.initialize()  # Authenticate
ws.start()       # Connect
ws.subscribe(["RELIANCE", "TCS"])
ws.register_callback(on_price_update)
```

### PortfolioManager
Track positions with 5x leverage:
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

✅ **v2.0 Institutional-Grade Features Released**
- Market Hours Widget - Real-time IST clock with status display
- Trading Hours Enforcement - 9:15 AM - 3:30 PM IST only
- Advanced Order Types - Market, Limit, Stop Loss, Stop Limit, Bracket orders
- PnL Engine - Realized/Unrealized PnL tracking with daily snapshots
- Risk Management Engine - Drawdown, Sharpe ratio, profit factor, daily loss limits
- Performance Analyzer - Trade statistics, win rate, ROI calculation
- Alert System - Price, trade, risk, and system alerts with priorities
- Example Scripts - Comprehensive examples for all advanced features

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