"""
Trading Terminal UI for IndiPaperTrade

Professional trading terminal interface with:
- Market Watch with live price updates
- Order placement panel (Buy/Sell)
- Portfolio and positions viewer
- Order book and trade history
- Modern professional dark mode theme
"""

import sys
import time
import logging
from typing import Optional, Dict, List
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QPushButton, QLabel, QLineEdit,
    QComboBox, QSpinBox, QDoubleSpinBox, QTabWidget, QSplitter, QCheckBox,
    QGroupBox, QMessageBox, QHeaderView, QStatusBar, QScrollArea, QFrame
)
from PyQt6.QtCore import QTimer, Qt, pyqtSignal, QThread, QUrl
from PyQt6.QtGui import QFont, QColor, QIcon, QDesktopServices

# Add parent directory to path for imports
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_engine import MarketDataEngine, PriceData
from data_engine.websocket_data import WebSocketDataEngine
from execution_engine import OrderSimulator, OrderSide, OrderType
from portfolio_engine import PortfolioManager
from database import Database
from utils.market_hours import MarketHoursChecker, get_market_status_message
from utils.rss_feed_manager import RSSFeedManager
from utils.notifications import NotificationManager, NotificationType
from utils.price_alerts import AlertCondition
from ui.styles import (
    MAIN_STYLESHEET, MARKET_CLOCK_STYLESHEET, ORDER_PANEL_STYLESHEET,
    MARKET_WATCH_STYLESHEET, POSITIONS_WIDGET_STYLESHEET,
    MARGIN_INFO_STYLESHEET, ORDER_BOOK_STYLESHEET, COLORS, STATUS_COLORS
)

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
    """Market watch panel with live price updates and professional styling."""
    
    symbol_selected = pyqtSignal(str)  # Emit when symbol is selected
    symbol_added = pyqtSignal(str)  # Emit when new symbol is added
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.setStyleSheet(MARKET_WATCH_STYLESHEET)
        
    def init_ui(self):
        group_box = QGroupBox("Market Watch - Live Quotes")
        layout = QVBoxLayout()
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Symbol", "LTP", "Change", "Change %", "Bid", "Ask"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(False)
        self.table.cellClicked.connect(self.on_row_clicked)
        layout.addWidget(self.table)
        
        # Add symbol controls
        add_layout = QHBoxLayout()
        self.symbol_input = QLineEdit()
        self.symbol_input.setPlaceholderText("Enter symbol (e.g., RELIANCE)")
        self.symbol_input.setMaximumHeight(35)
        
        add_btn = QPushButton("+ Add Symbol")
        add_btn.setMaximumWidth(150)
        add_btn.setMaximumHeight(35)
        add_btn.clicked.connect(self.add_symbol_clicked)
        
        add_layout.addWidget(self.symbol_input)
        add_layout.addWidget(add_btn)
        layout.addLayout(add_layout)
        
        group_box.setLayout(layout)
        main_layout = QVBoxLayout()
        main_layout.addWidget(group_box)
        main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(main_layout)
        
        # Symbol to row mapping
        self.symbol_rows = {}
        
    def add_symbol(self, symbol: str):
        """Add a symbol to the market watch."""
        if symbol in self.symbol_rows:
            return
        
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.symbol_rows[symbol] = row
        
        # Initialize cells with professional styling
        symbol_item = QTableWidgetItem(symbol)
        symbol_item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.table.setItem(row, 0, symbol_item)
        
        for col in range(1, 6):
            item = QTableWidgetItem("-")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            item.setFont(QFont("Arial", 10))
            self.table.setItem(row, col, item)
        
        # Emit signal for new symbol
        self.symbol_added.emit(symbol)
    
    def update_price(self, symbol: str, ltp: float, change: float, change_pct: float):
        """Update price for a symbol with color coding."""
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
        
        # Color coding - green for positive, red for negative
        if change >= 0:
            color = QColor(16, 185, 129)  # Green
        else:
            color = QColor(239, 68, 68)  # Red
        
        for col in [1, 2, 3]:
            self.table.item(row, col).setForeground(color)
            self.table.item(row, col).setFont(QFont("Arial", 10, QFont.Weight.Bold))
    
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


class NewsItemWidget(QWidget):
    """Individual news item widget with click-to-open functionality."""
    
    def __init__(self, news_item, parent=None):
        super().__init__(parent)
        self.news_item = news_item
        self.init_ui()
    
    def init_ui(self):
        """Initialize the news item UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(5)
        
        # Container for hover effect
        container = QWidget()
        container.setStyleSheet(f"""
            QWidget {{
                background: {COLORS['bg_darker']};
                border-left: 3px solid {COLORS['primary']};
                border-radius: 4px;
                padding: 8px;
            }}
            QWidget:hover {{
                background: {COLORS['bg_surface']};
                border-left-color: {COLORS['accent_green']};
            }}
        """)
        container.setCursor(Qt.CursorShape.PointingHandCursor)
        
        item_layout = QVBoxLayout(container)
        item_layout.setContentsMargins(8, 8, 8, 8)
        item_layout.setSpacing(5)
        
        # Header with source and time
        header_layout = QHBoxLayout()
        
        # Source badge
        source_label = QLabel(self.news_item.source)
        source_label.setFont(QFont("Arial", 8, QFont.Weight.Bold))
        source_color = self._get_source_color(self.news_item.source)
        source_label.setStyleSheet(f"""
            background: {source_color};
            color: white;
            padding: 2px 8px;
            border-radius: 3px;
        """)
        header_layout.addWidget(source_label)
        
        # Time
        time_label = QLabel(self._format_time(self.news_item.published))
        time_label.setFont(QFont("Arial", 8))
        time_label.setStyleSheet(f"color: {COLORS['text_tertiary']};")
        header_layout.addWidget(time_label)
        header_layout.addStretch()
        
        item_layout.addLayout(header_layout)
        
        # Title
        title = QLabel(self.news_item.title)
        title.setWordWrap(True)
        title.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLORS['text_primary']};")
        item_layout.addWidget(title)
        
        layout.addWidget(container)
        
        # Make clickable
        container.mousePressEvent = lambda event: self._open_article()
    
    def _get_source_color(self, source: str) -> str:
        """Get color for source badge."""
        if 'NSE' in source:
            return '#3B82F6'
        elif 'BSE' in source:
            return '#10B981'
        elif 'RBI' in source:
            return '#F59E0B'
        elif 'SEBI' in source:
            return '#8B5CF6'
        elif 'MoneyControl' in source:
            return '#EC4899'
        elif 'Economic Times' in source:
            return '#EF4444'
        elif 'Mint' in source:
            return '#06B6D4'
        return COLORS['primary']
    
    def _format_time(self, time_str: str) -> str:
        """Format time to relative format."""
        try:
            from email.utils import parsedate_to_datetime
            from pytz import UTC
            dt = parsedate_to_datetime(time_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            now = datetime.now(UTC)
            diff = (now - dt).total_seconds()
            
            if diff < 60:
                return "Just now"
            elif diff < 3600:
                return f"{int(diff / 60)}m ago"
            elif diff < 86400:
                return f"{int(diff / 3600)}h ago"
            else:
                return dt.strftime("%d %b")
        except:
            return time_str[:10] if len(time_str) > 10 else time_str
    
    def _open_article(self):
        """Open the article in browser."""
        from PyQt6.QtGui import QDesktopServices
        from PyQt6.QtCore import QUrl
        QDesktopServices.openUrl(QUrl(self.news_item.link))


class NewsFeedWidget(QWidget):
    """RSS News Feed Widget - displays live market news with scrollable list."""
    
    def __init__(self, rss_manager: RSSFeedManager):
        super().__init__()
        self.rss_manager = rss_manager
        self.news_widgets = []
        self.current_filter = "All Sources"
        self.init_ui()
        
        # Update timer for refreshing news list
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_news_display)
        self.timer.start(30000)  # Update every 30 seconds
        
        # Initial display after short delay
        QTimer.singleShot(2000, self.update_news_display)
    
    def init_ui(self):
        """Initialize the news feed UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(5)
        
        # Group box container
        group_box = QGroupBox("📰 Market News - Live Feed")
        group_box.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout = QVBoxLayout()
        layout.setSpacing(5)
        
        # Control bar with filter and refresh
        control_layout = QHBoxLayout()
        
        # Source filter
        filter_label = QLabel("Source:")
        filter_label.setFont(QFont("Arial", 9))
        filter_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        control_layout.addWidget(filter_label)
        
        self.source_combo = QComboBox()
        self.source_combo.setFont(QFont("Arial", 9))
        self.source_combo.addItems([
            "All Sources",
            "SEBI",
            "Economic Times",
            "Live Mint",
            "MoneyControl",
            "NSE Announcements",
            "BSE Announcements",
            "RBI Press Releases"
        ])
        self.source_combo.currentTextChanged.connect(self.on_filter_changed)
        self.source_combo.setMaximumWidth(150)
        self.source_combo.setStyleSheet(f"""
            QComboBox {{
                background: {COLORS['bg_surface']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 3px;
                padding: 3px 8px;
            }}
            QComboBox:hover {{
                border-color: {COLORS['primary']};
            }}
            QComboBox::drop-down {{
                border: none;
            }}
        """)
        control_layout.addWidget(self.source_combo)
        
        control_layout.addStretch()
        
        # Item count label
        self.count_label = QLabel("0 items")
        self.count_label.setFont(QFont("Arial", 9))
        self.count_label.setStyleSheet(f"color: {COLORS['text_tertiary']};")
        control_layout.addWidget(self.count_label)
        
        # Refresh button
        refresh_btn = QPushButton("🔄")
        refresh_btn.setFont(QFont("Arial", 10))
        refresh_btn.setMaximumWidth(30)
        refresh_btn.setToolTip("Refresh News")
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['primary']};
                color: white;
                border: none;
                border-radius: 3px;
                padding: 3px;
            }}
            QPushButton:hover {{
                background: {COLORS['accent_green']};
            }}
        """)
        refresh_btn.clicked.connect(self.refresh_feeds)
        control_layout.addWidget(refresh_btn)
        
        layout.addLayout(control_layout)
        
        # Scrollable news area
        from PyQt6.QtWidgets import QScrollArea
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setMinimumHeight(120)
        scroll.setMaximumHeight(180)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background: {COLORS['bg_dark']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
            }}
            QScrollBar:vertical {{
                background: {COLORS['bg_darker']};
                width: 10px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical {{
                background: {COLORS['primary']};
                border-radius: 5px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {COLORS['accent_green']};
            }}
        """)
        
        # Container for news items
        self.news_container = QWidget()
        self.news_layout = QVBoxLayout(self.news_container)
        self.news_layout.setContentsMargins(0, 0, 0, 0)
        self.news_layout.setSpacing(5)
        self.news_layout.addStretch()
        
        # Loading label
        loading = QLabel("Loading news feeds...")
        loading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loading.setStyleSheet(f"color: {COLORS['text_tertiary']}; padding: 20px;")
        self.news_layout.insertWidget(0, loading)
        
        scroll.setWidget(self.news_container)
        layout.addWidget(scroll)
        
        group_box.setLayout(layout)
        main_layout.addWidget(group_box)
    
    def update_news_display(self):
        """Update the news display with latest items."""
        if not self.rss_manager:
            return
        
        try:
            # Get all items
            all_items = self.rss_manager.get_latest_items(count=50)
            
            # Filter by source if needed
            if self.current_filter != "All Sources":
                items = [item for item in all_items if item.source == self.current_filter]
            else:
                items = all_items
            
            # Clear existing widgets
            self.clear_news_widgets()
            
            # Create new widgets
            if not items:
                no_news = QLabel("No news available")
                no_news.setAlignment(Qt.AlignmentFlag.AlignCenter)
                no_news.setStyleSheet(f"color: {COLORS['text_tertiary']}; padding: 20px;")
                self.news_layout.insertWidget(0, no_news)
            else:
                for item in items[:15]:  # Show max 15 items
                    news_widget = NewsItemWidget(item)
                    self.news_widgets.append(news_widget)
                    self.news_layout.insertWidget(len(self.news_widgets) - 1, news_widget)
            
            # Update count
            self.count_label.setText(f"{len(items)} items")
            
        except Exception as e:
            logger.error(f"Error updating news display: {e}")
    
    def clear_news_widgets(self):
        """Clear all news widgets from the layout."""
        for widget in self.news_widgets:
            self.news_layout.removeWidget(widget)
            widget.deleteLater()
        self.news_widgets.clear()
        
        # Also clear any labels
        for i in reversed(range(self.news_layout.count() - 1)):
            item = self.news_layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()
    
    def on_filter_changed(self, source: str):
        """Handle source filter change."""
        self.current_filter = source
        self.update_news_display()
    
    def refresh_feeds(self):
        """Manually refresh RSS feeds."""
        self.count_label.setText("Refreshing...")
        if self.rss_manager:
            self.rss_manager.update_feeds()
        QTimer.singleShot(2000, self.update_news_display)



class MarketClockWidget(QWidget):
    """Market hours clock and status display with professional styling."""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.setStyleSheet(MARKET_CLOCK_STYLESHEET)
        
        # Update timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)  # Update every second
    
    def init_ui(self):
        group_box = QGroupBox("Market Clock (IST)")
        layout = QVBoxLayout()
        
        # Current time - large prominent display
        self.time_label = QLabel("00:00:00")
        self.time_label.setObjectName("clockLabel")
        self.time_label.setFont(QFont("Courier New", 32, QFont.Weight.Bold))
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.time_label)
        
        # Market status - color coded badge
        status_layout = QHBoxLayout()
        status_layout.addStretch()
        self.status_label = QLabel("MARKET CLOSED")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet(f"""
            background-color: {COLORS['status_closed']};
            color: white;
            border-radius: 6px;
            padding: 10px 20px;
            font-size: 13px;
        """)
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        layout.addLayout(status_layout)
        
        # Status message
        self.message_label = QLabel("")
        self.message_label.setObjectName("timeMessageLabel")
        self.message_label.setFont(QFont("Arial", 10))
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message_label.setWordWrap(True)
        layout.addWidget(self.message_label)
        
        group_box.setLayout(layout)
        main_layout = QVBoxLayout()
        main_layout.addWidget(group_box)
        main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(main_layout)
        
        self.update_time()
    
    def update_time(self):
        """Update clock and market status with professional styling."""
        current_time = MarketHoursChecker.get_current_time()
        time_str = current_time.strftime("%I:%M:%S")
        self.time_label.setText(time_str)
        
        # Update status
        status = MarketHoursChecker.get_market_status()
        message = get_market_status_message()
        
        # Style based on status
        status_styles = {
            "OPEN": f"background-color: {COLORS['status_open']}; color: white; border-radius: 6px; padding: 10px 20px; font-size: 13px; font-weight: bold;",
            "PRE_MARKET": f"background-color: {COLORS['status_premarket']}; color: white; border-radius: 6px; padding: 10px 20px; font-size: 13px; font-weight: bold;",
            "POST_MARKET": f"background-color: {COLORS['status_postmarket']}; color: white; border-radius: 6px; padding: 10px 20px; font-size: 13px; font-weight: bold;",
            "WEEKEND": f"background-color: {COLORS['text_tertiary']}; color: white; border-radius: 6px; padding: 10px 20px; font-size: 13px; font-weight: bold;",
            "CLOSED": f"background-color: {COLORS['status_closed']}; color: white; border-radius: 6px; padding: 10px 20px; font-size: 13px; font-weight: bold;",
        }
        
        status_map = {
            "OPEN": ("MARKET OPEN", "OPEN"),
            "PRE_MARKET": ("PRE-MARKET", "PRE_MARKET"),
            "POST_MARKET": ("POST-MARKET", "POST_MARKET"),
            "WEEKEND": ("WEEKEND", "WEEKEND"),
        }
        
        if status in status_map:
            display_text, style_key = status_map[status]
            self.status_label.setText(display_text)
            self.status_label.setStyleSheet(status_styles[style_key])
        else:
            self.status_label.setText("MARKET CLOSED")
            self.status_label.setStyleSheet(status_styles["CLOSED"])
        
        self.message_label.setText(message)
    
    def is_trading_allowed(self) -> bool:
        """Check if trading is currently allowed."""
        return MarketHoursChecker.is_market_open()


class OrderPanel(QWidget):
    """Order placement panel with professional styling."""
    
    order_placed = pyqtSignal(dict)  # Emit order details
    
    def __init__(self):
        super().__init__()
        self.current_symbol = ""
        self.current_ltp = 0.0
        self.init_ui()
        self.setStyleSheet(ORDER_PANEL_STYLESHEET)
        
    def init_ui(self):
        group_box = QGroupBox("Place Order")
        layout = QVBoxLayout()
        
        # Symbol display - Large and prominent
        symbol_layout = QHBoxLayout()
        symbol_label_text = QLabel("Symbol:")
        symbol_label_text.setFont(QFont("Arial", 10))
        symbol_label_text.setStyleSheet(f"color: {COLORS['text_secondary']};")
        self.symbol_label = QLabel("-")
        self.symbol_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        self.symbol_label.setStyleSheet(f"color: {COLORS['primary_light']};")
        symbol_layout.addWidget(symbol_label_text)
        symbol_layout.addWidget(self.symbol_label)
        symbol_layout.addStretch()
        layout.addLayout(symbol_layout)
        
        # LTP display
        ltp_layout = QHBoxLayout()
        ltp_label_text = QLabel("LTP:")
        ltp_label_text.setFont(QFont("Arial", 10))
        ltp_label_text.setStyleSheet(f"color: {COLORS['text_secondary']};")
        self.ltp_label = QLabel("₹0.00")
        self.ltp_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.ltp_label.setStyleSheet(f"color: {COLORS['accent_yellow']};")
        ltp_layout.addWidget(ltp_label_text)
        ltp_layout.addWidget(self.ltp_label)
        ltp_layout.addStretch()
        layout.addLayout(ltp_layout)
        
        layout.addSpacing(15)
        
        # Order type
        order_type_label = QLabel("Order Type:")
        order_type_label.setFont(QFont("Arial", 10))
        order_type_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        layout.addWidget(order_type_label)
        
        self.order_type_combo = QComboBox()
        self.order_type_combo.addItems(["MARKET", "LIMIT"])
        self.order_type_combo.currentTextChanged.connect(self.on_order_type_changed)
        self.order_type_combo.setMinimumHeight(35)
        layout.addWidget(self.order_type_combo)
        
        # Quantity
        qty_label = QLabel("Quantity:")
        qty_label.setFont(QFont("Arial", 10))
        qty_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        layout.addWidget(qty_label)
        
        self.quantity_spin = QSpinBox()
        self.quantity_spin.setMinimum(1)
        self.quantity_spin.setMaximum(10000)
        self.quantity_spin.setValue(1)
        self.quantity_spin.setMinimumHeight(35)
        layout.addWidget(self.quantity_spin)
        
        # Price (for limit orders)
        price_label = QLabel("Price:")
        price_label.setFont(QFont("Arial", 10))
        price_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        layout.addWidget(price_label)
        
        self.price_spin = QDoubleSpinBox()
        self.price_spin.setMinimum(0.05)
        self.price_spin.setMaximum(100000.0)
        self.price_spin.setDecimals(2)
        self.price_spin.setSingleStep(0.05)
        self.price_spin.setEnabled(False)
        self.price_spin.setMinimumHeight(35)
        layout.addWidget(self.price_spin)
        
        layout.addSpacing(10)
        
        # Stop Loss / Take Profit Section
        sl_tp_group = QGroupBox("Stop Loss / Take Profit")
        sl_tp_layout = QVBoxLayout()
        
        # Stop Loss
        sl_row = QHBoxLayout()
        self.sl_enabled = QCheckBox("Stop Loss")
        self.sl_enabled.setStyleSheet(f"color: {COLORS['text_primary']};")
        self.sl_enabled.stateChanged.connect(self.on_sl_enabled_changed)
        self.sl_price = QDoubleSpinBox()
        self.sl_price.setMinimum(0.05)
        self.sl_price.setMaximum(100000.0)
        self.sl_price.setDecimals(2)
        self.sl_price.setSingleStep(0.05)
        self.sl_price.setEnabled(False)
        self.sl_price.setMinimumHeight(30)
        self.sl_price.setPrefix("₹")
        sl_row.addWidget(self.sl_enabled)
        sl_row.addWidget(self.sl_price)
        sl_tp_layout.addLayout(sl_row)
        
        # Take Profit
        tp_row = QHBoxLayout()
        self.tp_enabled = QCheckBox("Take Profit")
        self.tp_enabled.setStyleSheet(f"color: {COLORS['text_primary']};")
        self.tp_enabled.stateChanged.connect(self.on_tp_enabled_changed)
        self.tp_price = QDoubleSpinBox()
        self.tp_price.setMinimum(0.05)
        self.tp_price.setMaximum(100000.0)
        self.tp_price.setDecimals(2)
        self.tp_price.setSingleStep(0.05)
        self.tp_price.setEnabled(False)
        self.tp_price.setMinimumHeight(30)
        self.tp_price.setPrefix("₹")
        tp_row.addWidget(self.tp_enabled)
        tp_row.addWidget(self.tp_price)
        sl_tp_layout.addLayout(tp_row)
        
        sl_tp_group.setLayout(sl_tp_layout)
        layout.addWidget(sl_tp_group)
        
        layout.addSpacing(20)
        
        # Buy/Sell buttons - Professional styling
        button_layout = QHBoxLayout()
        
        self.buy_btn = QPushButton("BUY")
        self.buy_btn.setObjectName("buyButton")
        self.buy_btn.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.buy_btn.setMinimumHeight(50)
        self.buy_btn.clicked.connect(lambda: self.place_order("BUY"))
        self.buy_btn.setEnabled(False)
        
        self.sell_btn = QPushButton("SELL")
        self.sell_btn.setObjectName("sellButton")
        self.sell_btn.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.sell_btn.setMinimumHeight(50)
        self.sell_btn.clicked.connect(lambda: self.place_order("SELL"))
        self.sell_btn.setEnabled(False)
        
        button_layout.addWidget(self.buy_btn)
        button_layout.addWidget(self.sell_btn)
        layout.addLayout(button_layout)
        
        layout.addStretch()
        group_box.setLayout(layout)
        main_layout = QVBoxLayout()
        main_layout.addWidget(group_box)
        main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(main_layout)
    
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
    
    def on_sl_enabled_changed(self, state):
        """Handle stop loss checkbox change."""
        self.sl_price.setEnabled(state == 2)  # 2 = checked
        if state == 2 and self.current_ltp > 0:
            # Set default SL to 2% below current price for buy, 2% above for sell
            self.sl_price.setValue(self.current_ltp * 0.98)
    
    def on_tp_enabled_changed(self, state):
        """Handle take profit checkbox change."""
        self.tp_price.setEnabled(state == 2)  # 2 = checked
        if state == 2 and self.current_ltp > 0:
            # Set default TP to 5% above current price for buy, 5% below for sell
            self.tp_price.setValue(self.current_ltp * 1.05)
    
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
            "price": self.price_spin.value() if self.order_type_combo.currentText() == "LIMIT" else None,
            "stop_loss": self.sl_price.value() if self.sl_enabled.isChecked() else None,
            "take_profit": self.tp_price.value() if self.tp_enabled.isChecked() else None
        }
        
        self.order_placed.emit(order_details)


class MarginInfoWidget(QWidget):
    """Margin and leverage information display."""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.setStyleSheet(MARGIN_INFO_STYLESHEET)
        
    def init_ui(self):
        group_box = QGroupBox("Margin & Leverage Info")
        layout = QVBoxLayout()
        
        # Available Margin
        margin_layout = QHBoxLayout()
        margin_label = QLabel("Available Margin:")
        margin_label.setFont(QFont("Arial", 10))
        margin_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        self.margin_value = QLabel("₹100,000.00")
        self.margin_value.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.margin_value.setStyleSheet(f"color: {COLORS['accent_green']};")
        margin_layout.addWidget(margin_label)
        margin_layout.addStretch()
        margin_layout.addWidget(self.margin_value)
        layout.addLayout(margin_layout)
        
        # Used Margin
        used_layout = QHBoxLayout()
        used_label = QLabel("Used Margin:")
        used_label.setFont(QFont("Arial", 10))
        used_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        self.used_value = QLabel("₹0.00")
        self.used_value.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.used_value.setStyleSheet(f"color: {COLORS['accent_orange']};")
        used_layout.addWidget(used_label)
        used_layout.addStretch()
        used_layout.addWidget(self.used_value)
        layout.addLayout(used_layout)
        
        # Margin Utilization
        util_layout = QHBoxLayout()
        util_label = QLabel("Margin Utilization:")
        util_label.setFont(QFont("Arial", 10))
        util_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        self.util_value = QLabel("0%")
        self.util_value.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.util_value.setStyleSheet(f"color: {COLORS['primary_light']};")
        util_layout.addWidget(util_label)
        util_layout.addStretch()
        util_layout.addWidget(self.util_value)
        layout.addLayout(util_layout)
        
        # Default Leverage
        leverage_layout = QHBoxLayout()
        leverage_label = QLabel("Default Leverage:")
        leverage_label.setFont(QFont("Arial", 10))
        leverage_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        self.leverage_value = QLabel("5.0x")
        self.leverage_value.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.leverage_value.setStyleSheet(f"color: {COLORS['accent_yellow']};")
        leverage_layout.addWidget(leverage_label)
        leverage_layout.addStretch()
        leverage_layout.addWidget(self.leverage_value)
        layout.addLayout(leverage_layout)
        
        group_box.setLayout(layout)
        main_layout = QVBoxLayout()
        main_layout.addWidget(group_box)
        main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(main_layout)
    
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
            color = COLORS['accent_green']
        elif utilization < 70:
            color = COLORS['accent_orange']
        else:
            color = COLORS['accent_red']
        self.util_value.setStyleSheet(f"color: {color};")


class PositionsWidget(QWidget):
    """Portfolio positions display."""
    
    def __init__(self):
        super().__init__()
        self.parent_terminal = None  # Will be set by TradingTerminal for close functionality
        self.init_ui()
        self.setStyleSheet(POSITIONS_WIDGET_STYLESHEET)
        
    def init_ui(self):
        group_box = QGroupBox("Open Positions")
        layout = QVBoxLayout()
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(11)
        self.table.setHorizontalHeaderLabels([
            "Symbol", "Type", "Qty", "Avg Price", "LTP", "Leverage", "Margin Used", "P&L", "P&L %", "Status", "Action"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setMaximumHeight(250)
        
        layout.addWidget(self.table)
        group_box.setLayout(layout)
        main_layout = QVBoxLayout()
        main_layout.addWidget(group_box)
        main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(main_layout)
    
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
            
            # Color code P&L
            if position.unrealized_pnl >= 0:
                color = QColor(16, 185, 129)  # Green
            else:
                color = QColor(239, 68, 68)  # Red
            pnl_item.setForeground(color)
            pnl_pct_item.setForeground(color)
            
            self.table.setItem(row, 7, pnl_item)
            self.table.setItem(row, 8, pnl_pct_item)
            
            # Status
            status_item = QTableWidgetItem("OPEN")
            status_item.setForeground(QColor(16, 185, 129))  # Green
            status_item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            self.table.setItem(row, 9, status_item)
            
            # Close button
            close_btn = QPushButton("Close")
            close_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['accent_red']};
                    color: white;
                    border: none;
                    padding: 4px 8px;
                    border-radius: 3px;
                    font-size: 9px;
                }}
                QPushButton:hover {{
                    background-color: #d32f2f;
                }}
            """)
            close_btn.clicked.connect(
                lambda checked, sym=symbol, qty=position.quantity, side=position.position_type.value:
                self.parent_terminal.close_position(sym, qty, side) if self.parent_terminal else None
            )
            self.table.setCellWidget(row, 10, close_btn)



class OrderBookWidget(QWidget):
    """Order book display."""
    
    def __init__(self):
        super().__init__()
        self.parent_terminal = None  # Will be set by TradingTerminal for cancel functionality
        self.init_ui()
        self.setStyleSheet(ORDER_BOOK_STYLESHEET)
        
    def init_ui(self):
        group_box = QGroupBox("Order Book")
        layout = QVBoxLayout()
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Time", "Symbol", "Type", "Side", "Qty", "Price", "Status", "Action"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setMaximumHeight(200)
        
        layout.addWidget(self.table)
        group_box.setLayout(layout)
        main_layout = QVBoxLayout()
        main_layout.addWidget(group_box)
        main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(main_layout)
    
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
        
        # Add cancel button for pending orders
        if order.is_active():
            cancel_btn = QPushButton("Cancel")
            cancel_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['accent_red']};
                    color: white;
                    border: none;
                    padding: 4px 8px;
                    border-radius: 3px;
                    font-size: 9px;
                }}
                QPushButton:hover {{
                    background-color: #d32f2f;
                }}
            """)
            cancel_btn.clicked.connect(lambda: self.cancel_order(order.order_id))
            self.table.setCellWidget(row, 7, cancel_btn)
    
    def cancel_order(self, order_id: str):
        """Cancel a pending order."""
        if self.parent_terminal:
            self.parent_terminal.cancel_order(order_id)
        self.table.setItem(row, 6, status_item)
        
        # Scroll to latest
        self.table.scrollToBottom()


class AlertsWidget(QWidget):
    """Price alerts management widget."""
    
    alert_added = pyqtSignal(dict)  # Emit alert details
    alert_removed = pyqtSignal(str)  # Emit alert ID
    
    def __init__(self):
        super().__init__()
        self.alerts = []
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Alert creation section
        create_group = QGroupBox("Create Price Alert")
        create_layout = QVBoxLayout()
        
        # Symbol input
        symbol_row = QHBoxLayout()
        symbol_label = QLabel("Symbol:")
        symbol_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        self.symbol_input = QLineEdit()
        self.symbol_input.setPlaceholderText("e.g., RELIANCE, TCS")
        self.symbol_input.setMinimumHeight(30)
        symbol_row.addWidget(symbol_label)
        symbol_row.addWidget(self.symbol_input)
        create_layout.addLayout(symbol_row)
        
        # Condition selector
        condition_row = QHBoxLayout()
        condition_label = QLabel("Condition:")
        condition_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        self.condition_combo = QComboBox()
        self.condition_combo.addItems(["Above", "Below", "Crosses"])
        self.condition_combo.setMinimumHeight(30)
        condition_row.addWidget(condition_label)
        condition_row.addWidget(self.condition_combo)
        create_layout.addLayout(condition_row)
        
        # Target price
        price_row = QHBoxLayout()
        price_label = QLabel("Target Price:")
        price_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        self.target_price = QDoubleSpinBox()
        self.target_price.setRange(0.05, 100000.0)
        self.target_price.setDecimals(2)
        self.target_price.setPrefix("₹")
        self.target_price.setMinimumHeight(30)
        price_row.addWidget(price_label)
        price_row.addWidget(self.target_price)
        create_layout.addLayout(price_row)
        
        # Add button
        self.add_btn = QPushButton("Add Alert")
        self.add_btn.setMinimumHeight(35)
        self.add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['primary']};
                color: {COLORS['text_primary']};
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {COLORS['primary_light']};
            }}
        """)
        self.add_btn.clicked.connect(self.add_alert)
        create_layout.addWidget(self.add_btn)
        
        create_group.setLayout(create_layout)
        layout.addWidget(create_group)
        
        # Alerts table
        table_group = QGroupBox("Active Alerts")
        table_layout = QVBoxLayout()
        
        self.alerts_table = QTableWidget()
        self.alerts_table.setColumnCount(5)
        self.alerts_table.setHorizontalHeaderLabels(["Symbol", "Condition", "Target", "Status", "Actions"])
        self.alerts_table.horizontalHeader().setStretchLastSection(False)
        self.alerts_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.alerts_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.alerts_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.alerts_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.alerts_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.alerts_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.alerts_table.setAlternatingRowColors(True)
        self.alerts_table.verticalHeader().setVisible(False)
        self.alerts_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORS['bg_darker']};
                color: {COLORS['text_primary']};
                gridline-color: {COLORS['border']};
                border: 1px solid {COLORS['border']};
            }}
            QTableWidget::item {{
                padding: 8px;
            }}
            QHeaderView::section {{
                background-color: {COLORS['bg_surface']};
                color: {COLORS['text_secondary']};
                padding: 8px;
                border: none;
                font-weight: bold;
            }}
        """)
        
        table_layout.addWidget(self.alerts_table)
        table_group.setLayout(table_layout)
        layout.addWidget(table_group)
        
        self.setLayout(layout)
    
    def add_alert(self):
        """Add a new price alert."""
        symbol = self.symbol_input.text().strip().upper()
        condition = self.condition_combo.currentText()
        target = self.target_price.value()
        
        if not symbol:
            QMessageBox.warning(self, "Invalid Symbol", "Please enter a valid symbol")
            return
        
        alert_data = {
            "symbol": symbol,
            "condition": condition,
            "target_price": target,
            "status": "Active"
        }
        
        # Add to table
        row = self.alerts_table.rowCount()
        self.alerts_table.insertRow(row)
        self.alerts_table.setItem(row, 0, QTableWidgetItem(symbol))
        self.alerts_table.setItem(row, 1, QTableWidgetItem(condition))
        self.alerts_table.setItem(row, 2, QTableWidgetItem(f"₹{target:.2f}"))
        self.alerts_table.setItem(row, 3, QTableWidgetItem("Active"))
        
        # Remove button
        remove_btn = QPushButton("Remove")
        remove_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent_red']};
                color: white;
                border: none;
                padding: 5px 10px;
                border-radius: 3px;
            }}
            QPushButton:hover {{
                background-color: #d32f2f;
            }}
        """)
        remove_btn.clicked.connect(lambda: self.remove_alert(row))
        self.alerts_table.setCellWidget(row, 4, remove_btn)
        
        self.alerts.append(alert_data)
        self.alert_added.emit(alert_data)
        
        # Clear inputs
        self.symbol_input.clear()
        self.target_price.setValue(0.0)
    
    def remove_alert(self, row: int):
        """Remove an alert."""
        if 0 <= row < len(self.alerts):
            alert = self.alerts[row]
            self.alerts_table.removeRow(row)
            self.alerts.pop(row)
            # In real implementation, emit alert ID to remove from manager
            # self.alert_removed.emit(alert_id)
    
    def update_alert_status(self, symbol: str, status: str):
        """Update alert status in table."""
        for row in range(self.alerts_table.rowCount()):
            if self.alerts_table.item(row, 0).text() == symbol:
                self.alerts_table.item(row, 3).setText(status)


class ChartWidget(QWidget):
    """Candlestick chart widget (placeholder for actual charting library)."""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                border: 1px solid #333;
                border-radius: 3px;
            }
        """)
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Chart title
        title = QLabel("Chart - Select symbol to view")
        title.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        title.setStyleSheet("color: #888;")
        layout.addWidget(title)
        
        # Placeholder chart area (in real implementation, use matplotlib/plotly)
        chart_area = QFrame()
        chart_area.setMinimumHeight(300)
        chart_area.setStyleSheet("""
            QFrame {
                background-color: #111;
                border: 1px dashed #333;
            }
        """)
        layout.addWidget(chart_area, 1)
        
        self.setLayout(layout)
    
    def update_chart(self, symbol: str, data: Dict):
        """Update chart with new data."""
        # Placeholder for real chart updates
        pass


class TradeHistoryWidget(QWidget):
    """Detailed trade history table."""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
            }
        """)
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Title
        title = QLabel("Trade History")
        title.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        title.setStyleSheet("color: #10b981;")
        layout.addWidget(title)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Time", "Symbol", "Type", "Entry", "Exit", "P&L"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setMaximumHeight(150)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #1a1a1a;
                gridline-color: #333;
                border: 1px solid #333;
            }
            QHeaderView::section {
                background-color: #2a2a2a;
                color: #888;
                padding: 4px;
                border: none;
                font-size: 9px;
            }
            QTableWidget::item {
                padding: 4px;
            }
        """)
        
        layout.addWidget(self.table)
        self.setLayout(layout)
    
    def add_trade(self, symbol: str, trade_type: str, entry_price: float, exit_price: float, pnl: float):
        """Add a trade to the history."""
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        time_str = datetime.now().strftime("%H:%M:%S")
        self.table.setItem(row, 0, QTableWidgetItem(time_str))
        self.table.setItem(row, 1, QTableWidgetItem(symbol))
        self.table.setItem(row, 2, QTableWidgetItem(trade_type))
        self.table.setItem(row, 3, QTableWidgetItem(f"₹{entry_price:.2f}"))
        self.table.setItem(row, 4, QTableWidgetItem(f"₹{exit_price:.2f}"))
        
        pnl_item = QTableWidgetItem(f"₹{pnl:.2f}")
        color = QColor(16, 185, 129) if pnl >= 0 else QColor(239, 68, 68)
        pnl_item.setForeground(color)
        self.table.setItem(row, 5, pnl_item)


class PerformanceMetricsWidget(QWidget):
    """Performance metrics display."""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
            }
        """)
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # Title
        title = QLabel("PERFORMANCE METRICS")
        title.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        title.setStyleSheet("color: #10b981; border-bottom: 1px solid #333; padding-bottom: 8px;")
        layout.addWidget(title)
        
        # Metrics grid
        metrics_grid = QVBoxLayout()
        metrics_grid.setSpacing(8)
        
        # Metric rows
        self.metrics = {
            "Total Trades": (0, "120"),
            "Profit Factor": (1, "1.85"),
            "Max Drawdown": (2, "4.2%"),
            "Sharpe Ratio": (3, "1.45"),
            "Win Rate": (4, "58%"),
            "Avg Win": (5, "₹1,250"),
            "Avg Loss": (6, "₹-850"),
        }
        
        for metric_name, (idx, value) in self.metrics.items():
            metric_layout = QHBoxLayout()
            
            label = QLabel(metric_name + ":")
            label.setFont(QFont("Arial", 9))
            label.setStyleSheet("color: #888;")
            label.setMinimumWidth(120)
            
            value_label = QLabel(value)
            value_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            if metric_name in ["Profit Factor", "Sharpe Ratio", "Win Rate"]:
                value_label.setStyleSheet("color: #10b981;")
            else:
                value_label.setStyleSheet("color: #fff;")
            
            metric_layout.addWidget(label)
            metric_layout.addStretch()
            metric_layout.addWidget(value_label)
            metrics_grid.addLayout(metric_layout)
        
        layout.addLayout(metrics_grid)
        layout.addStretch()
        self.setLayout(layout)
    
    def update_metrics(self, metrics_data: Dict):
        """Update metrics with new data."""
        for key, value in metrics_data.items():
            if key in self.metrics:
                # Update the value in display (would need to refactor to use labels dict)
                pass


class RiskAlertsWidget(QWidget):
    """Risk alerts and warnings."""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
            }
        """)
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Title
        title = QLabel("RISK ALERTS")
        title.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        title.setStyleSheet("color: #ef4444; border-bottom: 1px solid #333; padding-bottom: 8px;")
        layout.addWidget(title)
        
        # Alert items
        self.alert_items = []
        
        # Example alerts
        alerts = [
            ("Daily Loss Limit Exceeded", "You've lost ₹2,500 today (limit: ₹5,000)"),
            ("Max Drawdown Alert", "Current drawdown: 4.2% (limit: 5%)")
        ]
        
        for alert_title, alert_msg in alerts:
            alert_frame = QFrame()
            alert_frame.setStyleSheet("""
                QFrame {
                    background-color: #2a1a1a;
                    border: 1px solid #663333;
                    border-radius: 3px;
                    padding: 8px;
                }
            """)
            
            alert_layout = QHBoxLayout()
            
            # Alert icon (red dot)
            icon = QLabel("●")
            icon.setStyleSheet("color: #ef4444; font-size: 12px;")
            alert_layout.addWidget(icon)
            
            # Alert text
            text_layout = QVBoxLayout()
            title_label = QLabel(alert_title)
            title_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
            title_label.setStyleSheet("color: #ef4444;")
            
            msg_label = QLabel(alert_msg)
            msg_label.setFont(QFont("Arial", 8))
            msg_label.setStyleSheet("color: #aaa;")
            msg_label.setWordWrap(True)
            
            text_layout.addWidget(title_label)
            text_layout.addWidget(msg_label)
            alert_layout.addLayout(text_layout, 1)
            
            alert_frame.setLayout(alert_layout)
            layout.addWidget(alert_frame)
        
        layout.addStretch()
        self.setLayout(layout)


class TradingTerminal(QMainWindow):
    """Main trading terminal window with professional dark mode styling."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IndiPaperTrade - Professional Trading Terminal")
        self.setGeometry(50, 50, 1600, 1000)
        self.setMinimumSize(1200, 800)
        
        # Apply professional stylesheet
        self.setStyleSheet(MAIN_STYLESHEET)
        
        # Initialize RSS feed manager
        self.rss_manager = RSSFeedManager(max_items=50)
        
        # Initialize notification manager
        self.notification_manager = NotificationManager()
        
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
        
        # Start RSS feed auto-update (every 5 minutes)
        self.rss_manager.start_auto_update(interval=300)
        
    def init_ui(self):
        """Initialize UI components with professional layout matching desired design."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # ===== TOP BAR: Market Tickers =====
        self.market_clock = MarketClockWidget()
        main_layout.addWidget(self.market_clock)
        
        # ===== MAIN CONTENT: 3-Column Layout =====
        trading_layout = QHBoxLayout()
        trading_layout.setContentsMargins(5, 5, 5, 5)
        trading_layout.setSpacing(5)
        
        # LEFT PANEL: Watchlist, Alerts, Trade History
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(5)
        
        self.market_watch = MarketWatchWidget()
        self.market_watch.symbol_selected.connect(self.on_symbol_selected)
        self.market_watch.symbol_added.connect(self.on_symbol_added)
        left_layout.addWidget(self.market_watch)
        
        left_panel.setLayout(left_layout)
        
        # CENTER PANEL: Chart + Order Entry + Trade History
        center_panel = QWidget()
        center_layout = QVBoxLayout()
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(5)
        
        # Chart widget
        self.chart_widget = ChartWidget()
        center_layout.addWidget(self.chart_widget, 2)
        
        # Order Entry Panel
        self.order_panel = OrderPanel()
        self.order_panel.order_placed.connect(self.on_order_placed)
        center_layout.addWidget(self.order_panel, 1)
        
        # Trade History
        self.trade_history_widget = TradeHistoryWidget()
        center_layout.addWidget(self.trade_history_widget, 1)
        
        center_panel.setLayout(center_layout)
        
        # RIGHT PANEL: Portfolio Summary, Positions, Performance, Alerts
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(5)
        
        # Right panel top section (Portfolio Summary + Open Positions)
        right_top = QWidget()
        right_top_layout = QVBoxLayout()
        right_top_layout.setContentsMargins(0, 0, 0, 0)
        right_top_layout.setSpacing(5)
        
        self.margin_info_widget = MarginInfoWidget()
        self.positions_widget = PositionsWidget()
        
        right_top_layout.addWidget(self.margin_info_widget, 1)
        right_top_layout.addWidget(self.positions_widget, 2)
        right_top.setLayout(right_top_layout)
        
        # Right panel bottom section (Performance Metrics + Risk Alerts)
        right_bottom = QWidget()
        right_bottom_layout = QVBoxLayout()
        right_bottom_layout.setContentsMargins(0, 0, 0, 0)
        right_bottom_layout.setSpacing(5)
        
        self.performance_metrics_widget = PerformanceMetricsWidget()
        self.risk_alerts_widget = RiskAlertsWidget()
        
        right_bottom_layout.addWidget(self.performance_metrics_widget, 1)
        right_bottom_layout.addWidget(self.risk_alerts_widget, 1)
        right_bottom.setLayout(right_bottom_layout)
        
        # Add right panel sections to main layout
        right_layout.addWidget(right_top, 2)
        right_layout.addWidget(right_bottom, 1)
        right_panel.setLayout(right_layout)
        
        # Create horizontal splitter for all 3 panels
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(center_panel)
        splitter.addWidget(right_panel)
        
        # Set stretch factors for responsive layout
        splitter.setStretchFactor(0, 1)  # Left panel: 20%
        splitter.setStretchFactor(1, 2)  # Center panel: 50%
        splitter.setStretchFactor(2, 1)  # Right panel: 30%
        
        # Set collapsible splitter
        splitter.setCollapsible(0, True)
        splitter.setCollapsible(1, False)
        splitter.setCollapsible(2, True)
        
        trading_layout.addWidget(splitter)
        main_layout.addLayout(trading_layout, 1)
        
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
            
            # Add alert callback to order simulator
            self.order_simulator.alert_manager.add_callback(self.on_alert_triggered)
            self.order_simulator.register_execution_callback(self.on_order_executed)
            
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
            stop_loss = order_details.get("stop_loss")
            take_profit = order_details.get("take_profit")
            
            # Place main order
            if order_type == "MARKET":
                order = self.order_simulator.place_market_order(symbol, side, quantity)
            else:
                order = self.order_simulator.place_limit_order(symbol, side, quantity, price)
            
            # Update portfolio
            if order.is_filled():
                self.portfolio_manager.execute_order(order)
                
                # Place stop loss order if enabled
                if stop_loss:
                    sl_side = OrderSide.SELL if side == OrderSide.BUY else OrderSide.BUY
                    sl_order = self.order_simulator.place_stop_loss_order(
                        symbol, sl_side, quantity, stop_loss
                    )
                    self.order_book_widget.add_order(sl_order)
                    logger.info(f"Stop loss order placed: {symbol} @ ₹{stop_loss:.2f}")
                
                # Place take profit order if enabled (as limit order)
                if take_profit:
                    tp_side = OrderSide.SELL if side == OrderSide.BUY else OrderSide.BUY
                    tp_order = self.order_simulator.place_limit_order(
                        symbol, tp_side, quantity, take_profit
                    )
                    self.order_book_widget.add_order(tp_order)
                    logger.info(f"Take profit order placed: {symbol} @ ₹{take_profit:.2f}")
            
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
            if stop_loss:
                status_msg += f"\nSL @ ₹{stop_loss:.2f}"
            if take_profit:
                status_msg += f"\nTP @ ₹{take_profit:.2f}"
            self.statusBar.showMessage(status_msg, 5000)
            
            QMessageBox.information(self, "Order Placed", 
                                  f"Order {order.status.value}\n{status_msg}")
            
        except Exception as e:
            logger.error(f"Order placement error: {e}")
            QMessageBox.critical(self, "Order Error", str(e))
    
    def update_positions(self):
        """Update positions display."""
        try:
            if self.portfolio_manager:
                self.portfolio_manager.update_market_prices()
                positions = self.portfolio_manager.get_all_positions()
                self.positions_widget.update_positions(positions)
                self.positions_widget.parent_terminal = self  # Add reference for close functionality
                self.update_margin_info()
        except Exception as e:
            # Log error but don't show modal dialog from timer callback
            logger.error(f"Error updating positions: {e}", exc_info=True)
            self.statusBar.showMessage(f"Error updating positions: {str(e)[:50]}", 5000)
    
    def update_margin_info(self):
        """Update margin information display."""
        try:
            if self.portfolio_manager and self.margin_info_widget:
                available = self.portfolio_manager.available_capital
                used = self.portfolio_manager.used_capital
                leverage = self.portfolio_manager.margin_multiplier
                self.margin_info_widget.update_margin_info(available, used, leverage)
        except Exception as e:
            logger.error(f"Error updating margin info: {e}", exc_info=True)
    
    def cancel_order(self, order_id: str):
        """Cancel a pending order."""
        if self.order_simulator:
            success = self.order_simulator.cancel_order(order_id)
            if success:
                self.statusBar.showMessage(f"Order cancelled: {order_id}", 3000)
                self.order_book_widget.refresh_orders()
            else:
                QMessageBox.warning(self, "Cancel Failed", f"Could not cancel order {order_id}")
    
    def close_position(self, symbol: str, quantity: int, side: str):
        """Close an open position with a market order."""
        try:
            if not self.order_simulator:
                QMessageBox.warning(self, "Error", "Order simulator not initialized")
                return
            
            # Opposite side to close (side is LONG or SHORT from PositionType)
            close_side = OrderSide.SELL if side == "LONG" else OrderSide.BUY
            
            # Place market order to close
            order = self.order_simulator.place_market_order(symbol, close_side, quantity)
            
            if order.is_filled():
                self.portfolio_manager.execute_order(order)
                self.order_book_widget.add_order(order)
                self.update_positions()
                self.update_margin_info()
                
                self.statusBar.showMessage(
                    f"Position closed: {symbol} {close_side.value} {quantity} @ ₹{order.filled_price:.2f}",
                    5000
                )
                QMessageBox.information(
                    self,
                    "Position Closed",
                    f"{close_side.value} {quantity} {symbol}\n@ ₹{order.filled_price:.2f}"
                )
            else:
                QMessageBox.warning(self, "Close Failed", f"Could not close position for {symbol}")
        
        except Exception as e:
            logger.error(f"Error closing position: {e}")
            QMessageBox.critical(self, "Error", f"Failed to close position: {str(e)}")
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
            if self.rss_manager:
                self.rss_manager.stop_auto_update()
        except Exception as e:
            logger.error(f"Error stopping RSS feed manager: {e}")
        
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
    
    def on_alert_added(self, alert_data: dict):
        """Handle new alert addition."""
        try:
            symbol = alert_data["symbol"]
            target_price = alert_data["target_price"]
            condition_text = alert_data["condition"]
            
            # Convert condition text to AlertCondition enum
            condition_map = {
                "Above": AlertCondition.ABOVE,
                "Below": AlertCondition.BELOW,
                "Crosses": AlertCondition.CROSSES
            }
            condition = condition_map.get(condition_text, AlertCondition.ABOVE)
            
            # Add alert to order simulator's alert manager
            self.order_simulator.alert_manager.add_alert(
                symbol=symbol,
                target_price=target_price,
                condition=condition,
                message=f"{symbol} {condition_text} ₹{target_price:.2f}"
            )
            
            logger.info(f"Alert added: {symbol} {condition_text} ₹{target_price:.2f}")
            self.statusBar.showMessage(f"Alert added: {symbol} {condition_text} ₹{target_price:.2f}", 3000)
            
        except Exception as e:
            logger.error(f"Error adding alert: {e}")
            QMessageBox.critical(self, "Alert Error", str(e))
    
    def on_alert_triggered(self, alert, current_price: float):
        """Handle alert trigger."""
        try:
            # Update UI
            self.alerts_widget.update_alert_status(alert.symbol, "Triggered")
            
            # Show notification
            condition_text = alert.condition.value.title()
            self.notification_manager.show_price_alert(
                symbol=alert.symbol,
                condition=condition_text,
                target_price=alert.target_price,
                current_price=current_price
            )
            
            logger.info(f"Alert triggered: {alert.symbol} @ ₹{current_price:.2f}")
            
        except Exception as e:
            logger.error(f"Error handling alert trigger: {e}")
    
    def on_order_executed(self, execution_report):
        """Handle order execution callback."""
        try:
            order = self.order_simulator.get_order(execution_report.order_id)
            
            if not order:
                return
            
            # Check if this is a stop loss or take profit order
            is_sl = order.is_stop_loss_order()
            is_tp = order.order_type == OrderType.LIMIT and "tp" in str(order.user_data).lower()
            
            if is_sl:
                self.notification_manager.show_stop_loss_alert(
                    symbol=order.symbol,
                    price=execution_report.price,
                    quantity=order.quantity
                )
            elif is_tp:
                self.notification_manager.show_take_profit_alert(
                    symbol=order.symbol,
                    price=execution_report.price,
                    quantity=order.quantity
                )
            else:
                self.notification_manager.show_order_filled(
                    symbol=order.symbol,
                    side=order.side.value,
                    quantity=order.quantity,
                    price=execution_report.price
                )
            
        except Exception as e:
            logger.error(f"Error handling order execution: {e}")


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
