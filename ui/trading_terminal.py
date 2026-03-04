"""
Trading Terminal UI for IndiPaperTrade

Professional trading terminal interface with:
- Market Watch with live price updates
- Order placement panel (Buy/Sell)
- Portfolio and positions viewer
- Order book and trade history
"""

import sys
import time
import logging
from typing import Optional, Dict, List
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QPushButton, QLabel, QLineEdit,
    QComboBox, QSpinBox, QDoubleSpinBox, QTabWidget, QSplitter,
    QGroupBox, QMessageBox, QHeaderView, QStatusBar
)
from PyQt6.QtCore import QTimer, Qt, pyqtSignal, QThread
from PyQt6.QtGui import QFont, QColor

# Add parent directory to path for imports
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_engine import MarketDataEngine, PriceData
from data_engine.websocket_data import WebSocketDataEngine
from execution_engine import OrderSimulator, OrderSide, OrderType
from portfolio_engine import PortfolioManager
from database import Database
from utils.market_hours import MarketHoursChecker, get_market_status_message

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PriceUpdateHandler(QThread):
    """
    Handler for real-time WebSocket price updates.
    Receives callbacks from WebSocket and emits Qt signals to update UI.
    """
    price_updated = pyqtSignal(str, float, float, float)  # symbol, ltp, change, change_pct
    
    def __init__(self):
        super().__init__()
        self.previous_prices = {}
        self.running = True
    
    def on_price_update(self, symbol: str, price_data: PriceData):
        """
        Callback for WebSocket price updates.
        
        Args:
            symbol: Trading symbol
            price_data: Updated price data
        """
        if not self.running:
            return
        
        try:
            ltp = price_data.ltp
            prev_price = self.previous_prices.get(symbol, ltp)
            
            # Calculate change
            change = ltp - prev_price
            change_pct = (change / prev_price * 100) if prev_price != 0 else 0
            
            # Emit signal to update UI
            self.price_updated.emit(symbol, ltp, change, change_pct)
            
            # Update previous price
            self.previous_prices[symbol] = ltp
            
        except Exception as e:
            logger.error(f"Error in price update handler: {e}")
    
    def stop(self):
        """Stop the handler."""
        self.running = False


class MarketWatchWidget(QWidget):
    """Market watch panel with live price updates."""
    
    symbol_selected = pyqtSignal(str)  # Emit when symbol is selected
    symbol_added = pyqtSignal(str)  # Emit when new symbol is added
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("MARKET WATCH")
        title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Symbol", "LTP", "Change", "Change %", "Bid", "Ask"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.cellClicked.connect(self.on_row_clicked)
        
        layout.addWidget(self.table)
        
        # Add symbol controls
        add_layout = QHBoxLayout()
        self.symbol_input = QLineEdit()
        self.symbol_input.setPlaceholderText("Enter symbol (e.g., RELIANCE)")
        add_btn = QPushButton("Add Symbol")
        add_btn.clicked.connect(self.add_symbol_clicked)
        
        add_layout.addWidget(self.symbol_input)
        add_layout.addWidget(add_btn)
        layout.addLayout(add_layout)
        
        self.setLayout(layout)
        
        # Symbol to row mapping
        self.symbol_rows = {}
        
    def add_symbol(self, symbol: str):
        """Add a symbol to the market watch."""
        if symbol in self.symbol_rows:
            return
        
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.symbol_rows[symbol] = row
        
        # Initialize cells
        self.table.setItem(row, 0, QTableWidgetItem(symbol))
        for col in range(1, 6):
            item = QTableWidgetItem("-")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, col, item)
        
        # Emit signal for new symbol
        self.symbol_added.emit(symbol)
    
    def update_price(self, symbol: str, ltp: float, change: float, change_pct: float):
        """Update price for a symbol."""
        if symbol not in self.symbol_rows:
            return
        
        row = self.symbol_rows[symbol]
        
        # Update LTP
        ltp_item = self.table.item(row, 1)
        ltp_item.setText(f"₹{ltp:.2f}")
        
        # Update change
        change_item = self.table.item(row, 2)
        change_item.setText(f"{change:+.2f}")
        
        # Update change %
        change_pct_item = self.table.item(row, 3)
        change_pct_item.setText(f"{change_pct:+.2f}%")
        
        # Color coding
        color = QColor(0, 200, 0) if change >= 0 else QColor(200, 0, 0)
        for col in [1, 2, 3]:
            self.table.item(row, col).setForeground(color)
    
    def add_symbol_clicked(self):
        """Handle add symbol button click."""
        symbol = self.symbol_input.text().strip().upper()
        if symbol:
            self.add_symbol(symbol)
            self.symbol_input.clear()
    
    def on_row_clicked(self, row: int, col: int):
        """Handle row selection."""
        symbol_item = self.table.item(row, 0)
        if symbol_item:
            self.symbol_selected.emit(symbol_item.text())


class MarketClockWidget(QWidget):
    """Market hours clock and status display."""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
        # Update timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)  # Update every second
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Current time
        self.time_label = QLabel("00:00:00")
        self.time_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.time_label)
        
        # Market status
        self.status_label = QLabel("MARKET CLOSED")
        self.status_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: red;")
        layout.addWidget(self.status_label)
        
        # Status message
        self.message_label = QLabel("")
        self.message_label.setFont(QFont("Arial", 9))
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message_label.setWordWrap(True)
        layout.addWidget(self.message_label)
        
        self.setLayout(layout)
        self.update_time()
    
    def update_time(self):
        """Update clock and market status."""
        current_time = MarketHoursChecker.get_current_time()
        time_str = current_time.strftime("%I:%M:%S %p")
        self.time_label.setText(time_str)
        
        # Update status
        status = MarketHoursChecker.get_market_status()
        message = get_market_status_message()
        
        if status == "OPEN":
            self.status_label.setText("MARKET OPEN")
            self.status_label.setStyleSheet("color: #00AA00; font-weight: bold;")
        elif status == "PRE_MARKET":
            self.status_label.setText("PRE-MARKET")
            self.status_label.setStyleSheet("color: #FF8800; font-weight: bold;")
        elif status == "POST_MARKET":
            self.status_label.setText("POST-MARKET")
            self.status_label.setStyleSheet("color: #FF8800; font-weight: bold;")
        elif status == "WEEKEND":
            self.status_label.setText("WEEKEND")
            self.status_label.setStyleSheet("color: #AA00AA; font-weight: bold;")
        else:
            self.status_label.setText("MARKET CLOSED")
            self.status_label.setStyleSheet("color: #CC0000; font-weight: bold;")
        
        self.message_label.setText(message)
    
    def is_trading_allowed(self) -> bool:
        """Check if trading is currently allowed."""
        return MarketHoursChecker.is_market_open()


class OrderPanel(QWidget):
    """Order placement panel."""
    
    order_placed = pyqtSignal(dict)  # Emit order details
    
    def __init__(self):
        super().__init__()
        self.current_symbol = ""
        self.current_ltp = 0.0
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("ORDER ENTRY")
        title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Symbol display
        symbol_layout = QHBoxLayout()
        symbol_layout.addWidget(QLabel("Symbol:"))
        self.symbol_label = QLabel("-")
        self.symbol_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        symbol_layout.addWidget(self.symbol_label)
        symbol_layout.addStretch()
        layout.addLayout(symbol_layout)
        
        # LTP display
        ltp_layout = QHBoxLayout()
        ltp_layout.addWidget(QLabel("LTP:"))
        self.ltp_label = QLabel("₹0.00")
        self.ltp_label.setFont(QFont("Arial", 12))
        ltp_layout.addWidget(self.ltp_label)
        ltp_layout.addStretch()
        layout.addLayout(ltp_layout)
        
        # Order type
        order_type_layout = QHBoxLayout()
        order_type_layout.addWidget(QLabel("Order Type:"))
        self.order_type_combo = QComboBox()
        self.order_type_combo.addItems(["MARKET", "LIMIT"])
        self.order_type_combo.currentTextChanged.connect(self.on_order_type_changed)
        order_type_layout.addWidget(self.order_type_combo)
        layout.addLayout(order_type_layout)
        
        # Quantity
        qty_layout = QHBoxLayout()
        qty_layout.addWidget(QLabel("Quantity:"))
        self.quantity_spin = QSpinBox()
        self.quantity_spin.setMinimum(1)
        self.quantity_spin.setMaximum(10000)
        self.quantity_spin.setValue(1)
        qty_layout.addWidget(self.quantity_spin)
        layout.addLayout(qty_layout)
        
        # Price (for limit orders)
        price_layout = QHBoxLayout()
        price_layout.addWidget(QLabel("Price:"))
        self.price_spin = QDoubleSpinBox()
        self.price_spin.setMinimum(0.05)
        self.price_spin.setMaximum(100000.0)
        self.price_spin.setDecimals(2)
        self.price_spin.setSingleStep(0.05)
        self.price_spin.setEnabled(False)
        price_layout.addWidget(self.price_spin)
        layout.addLayout(price_layout)
        
        # Buy/Sell buttons
        button_layout = QHBoxLayout()
        
        self.buy_btn = QPushButton("BUY")
        self.buy_btn.setStyleSheet("""
            QPushButton {
                background-color: #0066cc;
                color: white;
                font-size: 16px;
                font-weight: bold;
                padding: 15px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #0052a3;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.buy_btn.clicked.connect(lambda: self.place_order("BUY"))
        self.buy_btn.setEnabled(False)
        
        self.sell_btn = QPushButton("SELL")
        self.sell_btn.setStyleSheet("""
            QPushButton {
                background-color: #cc0000;
                color: white;
                font-size: 16px;
                font-weight: bold;
                padding: 15px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #a30000;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.sell_btn.clicked.connect(lambda: self.place_order("SELL"))
        self.sell_btn.setEnabled(False)
        
        button_layout.addWidget(self.buy_btn)
        button_layout.addWidget(self.sell_btn)
        layout.addLayout(button_layout)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def set_symbol(self, symbol: str, ltp: float = 0.0):
        """Set the current trading symbol."""
        self.current_symbol = symbol
        self.current_ltp = ltp
        self.symbol_label.setText(symbol)
        self.ltp_label.setText(f"₹{ltp:.2f}")
        self.price_spin.setValue(ltp)
        self.buy_btn.setEnabled(True)
        self.sell_btn.setEnabled(True)
    
    def update_ltp(self, ltp: float):
        """Update LTP display."""
        self.current_ltp = ltp
        self.ltp_label.setText(f"₹{ltp:.2f}")
        if self.order_type_combo.currentText() == "MARKET":
            self.price_spin.setValue(ltp)
    
    def on_order_type_changed(self, order_type: str):
        """Handle order type change."""
        if order_type == "LIMIT":
            self.price_spin.setEnabled(True)
            self.price_spin.setValue(self.current_ltp)
        else:
            self.price_spin.setEnabled(False)
    
    def place_order(self, side: str):
        """Place an order."""
        # Check market hours
        if not MarketHoursChecker.is_market_open():
            status = MarketHoursChecker.get_market_status()
            QMessageBox.warning(
                self, 
                "Trading Not Allowed", 
                f"Trading is only allowed during market hours (9:15 AM - 3:30 PM IST).\n\n"
                f"Current Status: {status}\n"
                f"{get_market_status_message()}"
            )
            return
        
        if not self.current_symbol:
            QMessageBox.warning(self, "No Symbol", "Please select a symbol from market watch")
            return
        
        order_details = {
            "symbol": self.current_symbol,
            "side": side,
            "quantity": self.quantity_spin.value(),
            "order_type": self.order_type_combo.currentText(),
            "price": self.price_spin.value() if self.order_type_combo.currentText() == "LIMIT" else None
        }
        
        self.order_placed.emit(order_details)


class MarginInfoWidget(QWidget):
    """Margin and leverage information display."""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("MARGIN & LEVERAGE INFO")
        title.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Info box
        info_layout = QVBoxLayout()
        info_layout.setSpacing(8)
        
        # Available Margin
        margin_layout = QHBoxLayout()
        margin_label = QLabel("Available Margin:")
        margin_label.setFont(QFont("Arial", 10))
        self.margin_value = QLabel("₹100,000.00")
        self.margin_value.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.margin_value.setStyleSheet("color: #00AA00;")
        margin_layout.addWidget(margin_label)
        margin_layout.addStretch()
        margin_layout.addWidget(self.margin_value)
        info_layout.addLayout(margin_layout)
        
        # Used Margin
        used_layout = QHBoxLayout()
        used_label = QLabel("Used Margin:")
        used_label.setFont(QFont("Arial", 10))
        self.used_value = QLabel("₹0.00")
        self.used_value.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.used_value.setStyleSheet("color: #FF6600;")
        used_layout.addWidget(used_label)
        used_layout.addStretch()
        used_layout.addWidget(self.used_value)
        info_layout.addLayout(used_layout)
        
        # Margin Utilization
        util_layout = QHBoxLayout()
        util_label = QLabel("Margin Utilization:")
        util_label.setFont(QFont("Arial", 10))
        self.util_value = QLabel("0%")
        self.util_value.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.util_value.setStyleSheet("color: #0066FF;")
        util_layout.addWidget(util_label)
        util_layout.addStretch()
        util_layout.addWidget(self.util_value)
        info_layout.addLayout(util_layout)
        
        # Default Leverage
        leverage_layout = QHBoxLayout()
        leverage_label = QLabel("Default Leverage:")
        leverage_label.setFont(QFont("Arial", 10))
        self.leverage_value = QLabel("5.0x")
        self.leverage_value.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.leverage_value.setStyleSheet("color: #AA00AA;")
        leverage_layout.addWidget(leverage_label)
        leverage_layout.addStretch()
        leverage_layout.addWidget(self.leverage_value)
        info_layout.addLayout(leverage_layout)
        
        layout.addLayout(info_layout)
        layout.addStretch()
        self.setLayout(layout)
    
    def update_margin_info(self, available: float, used: float, leverage: float = 5.0):
        """Update margin information."""
        self.margin_value.setText(f"₹{available:,.2f}")
        self.used_value.setText(f"₹{used:,.2f}")
        
        total = available + used
        utilization = (used / total * 100) if total > 0 else 0
        self.util_value.setText(f"{utilization:.2f}%")
        
        self.leverage_value.setText(f"{leverage:.1f}x")
        
        # Color code utilization
        if utilization < 30:
            color = "#00AA00"  # Green
        elif utilization < 70:
            color = "#FF6600"  # Orange
        else:
            color = "#FF0000"  # Red
        self.util_value.setStyleSheet(f"color: {color};")


class PositionsWidget(QWidget):
    """Portfolio positions display."""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("POSITIONS")
        title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            "Symbol", "Type", "Qty", "Avg Price", "LTP", "Leverage", "Margin Used", "P&L", "P&L %", "Status"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        layout.addWidget(self.table)
        self.setLayout(layout)
    
    def update_positions(self, positions: Dict):
        """Update positions table."""
        self.table.setRowCount(0)
        
        for symbol, position in positions.items():
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            self.table.setItem(row, 0, QTableWidgetItem(symbol))
            self.table.setItem(row, 1, QTableWidgetItem(position.position_type.value))
            self.table.setItem(row, 2, QTableWidgetItem(str(position.quantity)))
            self.table.setItem(row, 3, QTableWidgetItem(f"₹{position.entry_price:.2f}"))
            self.table.setItem(row, 4, QTableWidgetItem(f"₹{position.current_price:.2f}"))
            
            # Leverage
            leverage = getattr(position, 'leverage', 5.0)
            self.table.setItem(row, 5, QTableWidgetItem(f"{leverage:.1f}x"))
            
            # Margin used = position value / leverage
            position_value = position.quantity * position.entry_price
            margin_used = position_value / leverage
            self.table.setItem(row, 6, QTableWidgetItem(f"₹{margin_used:.2f}"))
            
            pnl_item = QTableWidgetItem(f"₹{position.unrealized_pnl:.2f}")
            pnl_pct_item = QTableWidgetItem(f"{position.pnl_percentage:.2f}%")
            
            color = QColor(0, 150, 0) if position.unrealized_pnl >= 0 else QColor(150, 0, 0)
            pnl_item.setForeground(color)
            pnl_pct_item.setForeground(color)
            
            self.table.setItem(row, 7, pnl_item)
            self.table.setItem(row, 8, pnl_pct_item)
            
            # Status
            status_item = QTableWidgetItem("OPEN")
            status_item.setForeground(QColor(0, 120, 200))
            self.table.setItem(row, 9, status_item)



class OrderBookWidget(QWidget):
    """Order book display."""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("ORDER BOOK")
        title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Time", "Symbol", "Type", "Side", "Qty", "Price", "Status"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        layout.addWidget(self.table)
        self.setLayout(layout)
    
    def add_order(self, order):
        """Add order to the book."""
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        time_str = datetime.now().strftime("%H:%M:%S")
        self.table.setItem(row, 0, QTableWidgetItem(time_str))
        self.table.setItem(row, 1, QTableWidgetItem(order.symbol))
        self.table.setItem(row, 2, QTableWidgetItem(order.order_type.value))
        self.table.setItem(row, 3, QTableWidgetItem(order.side.value))
        self.table.setItem(row, 4, QTableWidgetItem(str(order.quantity)))
        
        price_str = f"₹{order.price:.2f}" if order.price else "MARKET"
        self.table.setItem(row, 5, QTableWidgetItem(price_str))
        
        status_item = QTableWidgetItem(order.status.value)
        if order.status.value == "FILLED":
            status_item.setForeground(QColor(0, 150, 0))
        elif order.status.value == "REJECTED":
            status_item.setForeground(QColor(150, 0, 0))
        
        self.table.setItem(row, 6, status_item)
        
        # Scroll to latest
        self.table.scrollToBottom()


class TradingTerminal(QMainWindow):
    """Main trading terminal window."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IndiPaperTrade - Trading Terminal")
        self.setGeometry(100, 100, 1400, 900)
        
        # Initialize engines
        self.market_data_engine = None
        self.ws_data_engine = None
        self.order_simulator = None
        self.portfolio_manager = None
        self.price_handler = None
        self.db = None
        self.subscribed_symbols = set()
        
        self.init_ui()
        self.init_engines()
        
    def init_ui(self):
        """Initialize UI components."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        
        # Top bar - Market Clock
        self.market_clock = MarketClockWidget()
        main_layout.addWidget(self.market_clock)
        
        # Main trading panel
        trading_layout = QHBoxLayout()
        
        # Left panel - Market Watch
        self.market_watch = MarketWatchWidget()
        self.market_watch.symbol_selected.connect(self.on_symbol_selected)
        self.market_watch.symbol_added.connect(self.on_symbol_added)
        
        # Middle panel - Order Entry
        self.order_panel = OrderPanel()
        self.order_panel.order_placed.connect(self.on_order_placed)
        
        # Right panel - Positions and Orders
        right_panel = QTabWidget()
        self.margin_info_widget = MarginInfoWidget()
        self.positions_widget = PositionsWidget()
        self.order_book_widget = OrderBookWidget()
        
        right_panel.addTab(self.margin_info_widget, "Margin")
        right_panel.addTab(self.positions_widget, "Positions")
        right_panel.addTab(self.order_book_widget, "Order Book")
        
        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.market_watch)
        splitter.addWidget(self.order_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 2)
        
        trading_layout.addWidget(splitter)
        main_layout.addLayout(trading_layout)
        central_widget.setLayout(main_layout)
        
        # Status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Initializing...")

        # Quick actions
        self.reset_db_btn = QPushButton("Reset DB")
        self.reset_db_btn.clicked.connect(self.reset_database)
        self.statusBar.addPermanentWidget(self.reset_db_btn)
        
    def init_engines(self):
        """Initialize trading engines."""
        try:
            # Database
            self.db = Database()

            # Market data (REST - for order execution)
            self.statusBar.showMessage("Connecting to market data...")
            self.market_data_engine = MarketDataEngine()
            if self.market_data_engine.initialize():
                self.market_data_engine.start()
                self.statusBar.showMessage("REST API connected", 2000)
            else:
                self.statusBar.showMessage("Market data authentication failed", 5000)
                QMessageBox.warning(self, "Authentication Failed", 
                                  "Failed to authenticate with Angel One API.")
                return
            
            # Wait to avoid rate limiting (Angel One API has rate limits)
            time.sleep(2)
            
            # WebSocket data engine (for real-time streaming)
            self.statusBar.showMessage("Connecting to WebSocket stream...")
            self.ws_data_engine = WebSocketDataEngine()
            if self.ws_data_engine.initialize():
                self.ws_data_engine.start()
                
                # Wait a moment for WebSocket to connect
                time.sleep(1)
                
                self.statusBar.showMessage("WebSocket stream connected", 2000)
            else:
                self.statusBar.showMessage("WebSocket connection failed", 5000)
                QMessageBox.warning(self, "WebSocket Failed", 
                                  "Failed to connect WebSocket. Using REST polling.")
            
            # Order simulator
            self.order_simulator = OrderSimulator(data_engine=self.market_data_engine)
            self.order_simulator.start()
            
            # Portfolio manager
            self.portfolio_manager = PortfolioManager(
                initial_capital=100000,
                market_data_engine=self.market_data_engine,
                order_simulator=self.order_simulator,
                margin_multiplier=5.0
            )
            
            # Add default symbols
            default_symbols = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "SBIN"]
            for symbol in default_symbols:
                self.market_watch.add_symbol(symbol)
            
            # Price update handler for WebSocket
            self.price_handler = PriceUpdateHandler()
            self.price_handler.price_updated.connect(self.on_price_update)
            
            # Register callback with WebSocket engine
            if self.ws_data_engine:
                self.ws_data_engine.register_callback(self.price_handler.on_price_update)
            
            # Update timer for positions
            self.update_timer = QTimer()
            self.update_timer.timeout.connect(self.update_positions)
            self.update_timer.start(2000)  # Update every 2 seconds

            # Initial margin info
            self.update_margin_info()
            
            self.statusBar.showMessage("Ready - Real-time streaming active", 3000)
            
        except Exception as e:
            logger.error(f"Engine initialization error: {e}")
            QMessageBox.critical(self, "Initialization Error", str(e))
    
    def on_symbol_selected(self, symbol: str):
        """Handle symbol selection from market watch."""
        # Try WebSocket first (real-time), fallback to REST
        price_data = None
        if self.ws_data_engine:
            price_data = self.ws_data_engine.get_price_data(symbol)
        
        if not price_data and self.market_data_engine:
            price_data = self.market_data_engine.get_price_data(symbol)
        
        ltp = price_data.ltp if price_data else 0.0
        self.order_panel.set_symbol(symbol, ltp)
        self.statusBar.showMessage(f"Selected: {symbol}", 2000)
    
    def on_price_update(self, symbol: str, ltp: float, change: float, change_pct: float):
        """Handle price updates from market data thread."""
        self.market_watch.update_price(symbol, ltp, change, change_pct)
        
        # Update order panel if same symbol
        if self.order_panel.current_symbol == symbol:
            self.order_panel.update_ltp(ltp)

    def on_symbol_added(self, symbol: str):
        """Subscribe newly added symbols to data sources."""
        if symbol in self.subscribed_symbols:
            return

        try:
            if self.market_data_engine:
                self.market_data_engine.subscribe([symbol])

            ws_ok = False
            if self.ws_data_engine:
                ws_ok = self.ws_data_engine.subscribe([symbol])

            self.subscribed_symbols.add(symbol)
            if ws_ok:
                self.statusBar.showMessage(f"Subscribed {symbol} to real-time stream", 3000)
            else:
                self.statusBar.showMessage(f"Subscribed {symbol} (REST fallback)", 3000)
        except Exception as e:
            logger.error(f"Failed subscribing {symbol}: {e}")
    
    def on_order_placed(self, order_details: dict):
        """Handle order placement."""
        try:
            symbol = order_details["symbol"]
            side = OrderSide.BUY if order_details["side"] == "BUY" else OrderSide.SELL
            quantity = order_details["quantity"]
            order_type = order_details["order_type"]
            price = order_details.get("price")
            
            # Place order
            if order_type == "MARKET":
                order = self.order_simulator.place_market_order(symbol, side, quantity)
            else:
                order = self.order_simulator.place_limit_order(symbol, side, quantity, price)
            
            # Update portfolio
            if order.is_filled():
                self.portfolio_manager.execute_order(order)
            
            # Add to order book
            self.order_book_widget.add_order(order)

            # Persist order to database (best effort)
            self._save_order_to_db(order)
            
            # Update positions
            self.update_positions()
            self.update_margin_info()
            
            # Show confirmation
            display_price = order.filled_price if order.filled_price else price
            status_msg = f"{side.value} {quantity} {symbol} @ ₹{display_price:.2f}"
            self.statusBar.showMessage(status_msg, 5000)
            
            QMessageBox.information(self, "Order Placed", 
                                  f"Order {order.status.value}\n{status_msg}")
            
        except Exception as e:
            logger.error(f"Order placement error: {e}")
            QMessageBox.critical(self, "Order Error", str(e))
    
    def update_positions(self):
        """Update positions display."""
        if self.portfolio_manager:
            self.portfolio_manager.update_market_prices()
            positions = self.portfolio_manager.get_all_positions()
            self.positions_widget.update_positions(positions)
            self.update_margin_info()

    def update_margin_info(self):
        """Update margin widget with 5x leverage and actual margin used."""
        if not self.portfolio_manager:
            return

        summary = self.portfolio_manager.get_summary()
        leverage = 5.0
        actual_margin_used = summary['capital'].get('actual_margin_used', 0.0)
        available_margin = max(self.portfolio_manager.initial_capital - actual_margin_used, 0.0)

        self.margin_info_widget.update_margin_info(
            available=available_margin,
            used=actual_margin_used,
            leverage=leverage
        )

    def reset_database(self):
        """Reset database data on demand."""
        if not self.db:
            QMessageBox.warning(self, "Database", "Database is not initialized.")
            return

        reply = QMessageBox.question(
            self,
            "Reset Database",
            "This will clear all saved orders/positions/trades. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        if self.db.drop_and_recreate():
            self.statusBar.showMessage("Database reset completed", 4000)
            QMessageBox.information(self, "Database", "Database reset successful.")
        else:
            QMessageBox.critical(self, "Database", "Database reset failed.")

    def _save_order_to_db(self, order):
        """Save executed order into database (best effort)."""
        if not self.db:
            return

        try:
            from database.models import Order as DbOrder

            db_order = DbOrder(
                id=order.order_id,
                symbol=order.symbol,
                side=order.side.value,
                quantity=order.quantity,
                order_type=order.order_type.value,
                price=order.price,
                filled_price=order.filled_price,
                status=order.status.value,
                commission=getattr(order, 'commission', 0.0),
                timestamp=order.created_at,
                filled_at=order.filled_at,
            )
            self.db.add_order(db_order)
        except Exception as e:
            logger.error(f"Failed saving order to database: {e}")
    
    def closeEvent(self, event):
        """Handle window close."""
        try:
            if self.price_handler:
                self.price_handler.stop()
        except Exception as e:
            logger.error(f"Error stopping price handler: {e}")
        
        try:
            if self.ws_data_engine:
                self.ws_data_engine.stop()
        except Exception as e:
            logger.error(f"Error stopping WebSocket engine: {e}")
        
        try:
            if self.order_simulator:
                self.order_simulator.stop()
        except Exception as e:
            logger.error(f"Error stopping order simulator: {e}")
        
        try:
            if self.market_data_engine:
                self.market_data_engine.stop()
        except Exception as e:
            logger.error(f"Error stopping market data engine: {e}")
        
        event.accept()


def main():
    """Launch trading terminal."""
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle("Fusion")
    
    # Create and show terminal
    terminal = TradingTerminal()
    terminal.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
