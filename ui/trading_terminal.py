"""
Trading Terminal UI for IndiPaperTrade

Professional trading terminal interface with:
- Market Watch with live price updates
- Order placement panel (Buy/Sell)
- Portfolio and positions viewer
- Order book and trade history
"""

import sys
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
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Symbol", "Type", "Qty", "Avg Price", "LTP", "P&L", "P&L %"
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
            
            pnl_item = QTableWidgetItem(f"₹{position.unrealized_pnl:.2f}")
            pnl_pct_item = QTableWidgetItem(f"{position.pnl_percentage:.2f}%")
            
            color = QColor(0, 150, 0) if position.unrealized_pnl >= 0 else QColor(150, 0, 0)
            pnl_item.setForeground(color)
            pnl_pct_item.setForeground(color)
            
            self.table.setItem(row, 5, pnl_item)
            self.table.setItem(row, 6, pnl_pct_item)


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
        
        self.init_ui()
        self.init_engines()
        
    def init_ui(self):
        """Initialize UI components."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout()
        
        # Left panel - Market Watch
        self.market_watch = MarketWatchWidget()
        self.market_watch.symbol_selected.connect(self.on_symbol_selected)
        
        # Middle panel - Order Entry
        self.order_panel = OrderPanel()
        self.order_panel.order_placed.connect(self.on_order_placed)
        
        # Right panel - Positions and Orders
        right_panel = QTabWidget()
        self.positions_widget = PositionsWidget()
        self.order_book_widget = OrderBookWidget()
        
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
        
        main_layout.addWidget(splitter)
        central_widget.setLayout(main_layout)
        
        # Status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Initializing...")
        
    def init_engines(self):
        """Initialize trading engines."""
        try:
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
                order_simulator=self.order_simulator
            )
            
            # Add default symbols
            default_symbols = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "SBIN"]
            for symbol in default_symbols:
                self.market_watch.add_symbol(symbol)
            
            # Subscribe to REST (for order execution fallback)
            self.market_data_engine.subscribe(default_symbols)
            
            # Price update handler for WebSocket
        # Try WebSocket first (real-time), fallback to REST
        price_data = None
        if self.ws_data_engine:
            price_data = self.ws_data_engine.get_price_data(symbol)
        
        if not price_data and self.market_data_engine:
            price_data = self.market_data_engine.get_price_data(symbol)
        
            self.price_handler.price_updated.connect(self.on_price_update)
            
            # Register callback with WebSocket engine
            if self.ws_data_engine:
                self.ws_data_engine.register_callback(self.price_handler.on_price_update)
                
                # Subscribe to WebSocket for real-time updates
                self.ws_data_engine.subscribe(default_symbols)
            
            # Update timer for positions
            self.update_timer = QTimer()
            self.update_timer.timeout.connect(self.update_positions)
            self.update_timer.start(2000)  # Update every 2 seconds
            
            self.statusBar.showMessage("Ready - Real-time streaming active", 3000)
            
        except Exception as e:
            logger.error(f"Engine initialization error: {e}")
            QMessageBox.critical(self, "Initialization Error", str(e))
    
    def on_symbol_selected(self, symbol: str):
        """Handle symbol selection from market watch."""
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
            
            # Update positions
            self.update_positions()
            
            # Show confirmation
            status_msg = f"{side.value} {quantity} {symbol} @ ₹{order.filled_price:.2f if order.filled_price else price:.2f}"
            self.statusBar.showMessage(status_msg, 5000)
            
            QMessageBox.information(self, "Order Placed", 
                                  f"Order {order.status.value}\n{status_msg}")
            
        except Exception as e:
            logger.error(f"Order placement error: {e}")
            QMessageBox.critical(self, "Order Error", str(e))
    
    def update_positions(self):
        """Update positions display."""
        if self.price_handler:
            self.price_handler.stop()
        
        if self.ws_data_engine:
            self.ws_data_engine.stopanager.get_all_positions()
            self.positions_widget.update_positions(positions)
    
    def closeEvent(self, event):
        """Handle window close."""
        if self.market_data_thread:
            self.market_data_thread.stop()
            self.market_data_thread.wait()
        
        if self.order_simulator:
            self.order_simulator.stop()
        
        if self.market_data_engine:
            self.market_data_engine.stop()
        
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
