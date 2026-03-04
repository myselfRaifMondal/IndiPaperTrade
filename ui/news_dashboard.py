"""
News Dashboard UI for IndiPaperTrade

Professional news ingestion dashboard with:
- Live RSS feed aggregation
- Source filtering
- Auto-refresh capability
- Modern professional dark mode theme
- Color-coded news sources
"""

import sys
import logging
from typing import Optional, Dict, List
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QPushButton, QLabel, QLineEdit,
    QComboBox, QSpinBox, QGroupBox, QMessageBox, QScrollArea,
    QFrame, QCheckBox, QSlider
)
from PyQt6.QtCore import QTimer, Qt, pyqtSignal, QThread, QUrl
from PyQt6.QtGui import QFont, QColor, QDesktopServices

import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.rss_feed_manager import RSSFeedManager
from utils.market_hours import MarketHoursChecker, get_market_status_message
from ui.styles import COLORS, MAIN_STYLESHEET

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NewsCard(QFrame):
    """Individual news card widget."""
    
    def __init__(self, news_item: Dict, parent=None):
        super().__init__(parent)
        self.news_item = news_item
        self.init_ui()
    
    def init_ui(self):
        """Initialize the news card UI."""
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setStyleSheet(f"""
            NewsCard {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {COLORS['bg_darker']}, stop:1 {COLORS['bg_dark']});
                border-left: 4px solid {COLORS['primary']};
                border-radius: 8px;
                padding: 15px;
                margin: 8px;
            }}
            NewsCard:hover {{
                border-left-color: {COLORS['accent_green']};
                background: {COLORS['bg_dark']};
            }}
            QLabel {{
                background: transparent;
                color: {COLORS['text_primary']};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Header with title and source
        header_layout = QHBoxLayout()
        
        # Title
        title = QLabel(self.news_item.title if hasattr(self.news_item, 'title') else self.news_item.get('title', 'No Title'))
        title.setWordWrap(True)
        title.setFont(QFont('Arial', 11, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLORS['text_primary']};")
        header_layout.addWidget(title, stretch=3)
        
        # Source badge
        source = self.news_item.source if hasattr(self.news_item, 'source') else self.news_item.get('source', 'Unknown')
        source_label = QLabel(source)
        source_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        source_label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        source_label.setFixedHeight(25)
        source_label.setStyleSheet(self._get_source_style(source))
        header_layout.addWidget(source_label, stretch=1)
        
        layout.addLayout(header_layout)
        
        # Metadata (time)
        published = self.news_item.published if hasattr(self.news_item, 'published') else self.news_item.get('published', '')
        time_label = QLabel(f"🕒 {self._format_time(published)}")
        time_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 10px;")
        layout.addWidget(time_label)
        
        # Summary
        summary = self.news_item.summary if hasattr(self.news_item, 'summary') else self.news_item.get('summary', '')
        if summary:
            summary_label = QLabel(summary[:300] + ('...' if len(summary) > 300 else ''))
            summary_label.setWordWrap(True)
            summary_label.setStyleSheet(f"""
                color: {COLORS['text_secondary']};
                padding-top: 10px;
                border-top: 1px solid {COLORS['border']};
            """)
            layout.addWidget(summary_label)
        
        # Read more button
        btn_layout = QHBoxLayout()
        read_more_btn = QPushButton("Read More →")
        read_more_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['primary']};
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {COLORS['accent_green']};
            }}
        """)
        read_more_btn.clicked.connect(self._open_article)
        btn_layout.addStretch()
        btn_layout.addWidget(read_more_btn)
        layout.addLayout(btn_layout)
    
    def _get_source_style(self, source: str) -> str:
        """Get CSS style for source badge based on source name."""
        source_upper = source.upper()
        
        if 'NSE' in source_upper:
            bg_color = '#3B82F6'
        elif 'BSE' in source_upper:
            bg_color = '#10B981'
        elif 'RBI' in source_upper:
            bg_color = '#F59E0B'
        elif 'SEBI' in source_upper:
            bg_color = '#8B5CF6'
        elif 'MONEYCONTROL' in source_upper:
            bg_color = '#EC4899'
        elif 'ECONOMIC TIMES' in source_upper:
            bg_color = '#EF4444'
        elif 'MINT' in source_upper:
            bg_color = '#06B6D4'
        else:
            bg_color = COLORS['primary']
        
        return f"""
            background: {bg_color};
            color: white;
            padding: 4px 12px;
            border-radius: 4px;
            font-weight: bold;
        """
    
    def _format_time(self, time_str: str) -> str:
        """Format time string to relative time."""
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
                return dt.strftime("%d %b %Y")
        except:
            return time_str
    
    def _open_article(self):
        """Open the news article in default browser."""
        url = self.news_item.link if hasattr(self.news_item, 'link') else self.news_item.get('url', '')
        if url:
            QDesktopServices.openUrl(QUrl(url))


class NewsDashboard(QMainWindow):
    """Main news dashboard window."""
    
    def __init__(self):
        super().__init__()
        self.rss_manager = None
        self.market_checker = MarketHoursChecker()
        self.news_cards = []
        self.current_filter = "All Sources"
        self.news_count = 50
        self.auto_refresh_enabled = True
        self.refresh_interval = 60  # seconds
        
        self.init_ui()
        self.init_rss_manager()
        self.setup_timers()
    
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("IndiPaperTrade - News Dashboard")
        self.setGeometry(100, 100, 1400, 900)
        
        # Apply main stylesheet
        self.setStyleSheet(MAIN_STYLESHEET)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Create sidebar
        sidebar = self.create_sidebar()
        main_layout.addWidget(sidebar, stretch=1)
        
        # Create main content area
        content_area = self.create_content_area()
        main_layout.addWidget(content_area, stretch=4)
        
        # Status bar
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Initializing news feed...")
    
    def create_sidebar(self) -> QWidget:
        """Create the sidebar with controls."""
        sidebar = QWidget()
        sidebar.setMaximumWidth(300)
        sidebar.setStyleSheet(f"""
            QWidget {{
                background: {COLORS['bg_dark']};
                border-radius: 8px;
                padding: 10px;
            }}
        """)
        
        layout = QVBoxLayout(sidebar)
        layout.setSpacing(15)
        
        # Header
        header = QLabel("📈 IndiPaperTrade")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setFont(QFont('Arial', 18, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {COLORS['primary']}; padding: 10px;")
        layout.addWidget(header)
        
        subtitle = QLabel("Market News Dashboard")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet(f"color: {COLORS['text_secondary']}; padding-bottom: 10px;")
        layout.addWidget(subtitle)
        
        # Status indicator
        status_group = QGroupBox("Status")
        status_layout = QVBoxLayout()
        
        self.status_indicator = QLabel("● System Active")
        self.status_indicator.setStyleSheet(f"color: {COLORS['accent_green']}; font-weight: bold;")
        status_layout.addWidget(self.status_indicator)
        
        self.items_count_label = QLabel("Items: 0")
        self.items_count_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        status_layout.addWidget(self.items_count_label)
        
        self.last_update_label = QLabel("Last Updated: Never")
        self.last_update_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        status_layout.addWidget(self.last_update_label)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # Filters
        filters_group = QGroupBox("Filters")
        filters_layout = QVBoxLayout()
        
        # Source filter
        source_label = QLabel("News Source:")
        filters_layout.addWidget(source_label)
        
        self.source_combo = QComboBox()
        self.source_combo.addItems([
            "All Sources",
            "NSE Announcements",
            "NSE Circulars",
            "BSE Announcements",
            "RBI Press Releases",
            "SEBI",
            "MoneyControl",
            "Economic Times",
            "Live Mint"
        ])
        self.source_combo.currentTextChanged.connect(self.on_filter_changed)
        filters_layout.addWidget(self.source_combo)
        
        # Count slider
        count_label = QLabel(f"Number of Items: {self.news_count}")
        self.count_label = count_label
        filters_layout.addWidget(count_label)
        
        self.count_slider = QSlider(Qt.Orientation.Horizontal)
        self.count_slider.setMinimum(10)
        self.count_slider.setMaximum(100)
        self.count_slider.setValue(50)
        self.count_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.count_slider.setTickInterval(10)
        self.count_slider.valueChanged.connect(self.on_count_changed)
        filters_layout.addWidget(self.count_slider)
        
        filters_group.setLayout(filters_layout)
        layout.addWidget(filters_group)
        
        # Auto-refresh settings
        refresh_group = QGroupBox("Auto-Refresh")
        refresh_layout = QVBoxLayout()
        
        self.auto_refresh_check = QCheckBox("Enable Auto-Refresh")
        self.auto_refresh_check.setChecked(True)
        self.auto_refresh_check.stateChanged.connect(self.on_auto_refresh_toggled)
        refresh_layout.addWidget(self.auto_refresh_check)
        
        interval_label = QLabel("Refresh Interval:")
        refresh_layout.addWidget(interval_label)
        
        self.interval_combo = QComboBox()
        self.interval_combo.addItems(["30 seconds", "60 seconds", "2 minutes", "5 minutes"])
        self.interval_combo.setCurrentText("60 seconds")
        self.interval_combo.currentTextChanged.connect(self.on_interval_changed)
        refresh_layout.addWidget(self.interval_combo)
        
        refresh_group.setLayout(refresh_layout)
        layout.addWidget(refresh_group)
        
        # Manual refresh button
        refresh_btn = QPushButton("🔄 Refresh Now")
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['primary']};
                color: white;
                border: none;
                padding: 12px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background: {COLORS['accent_green']};
            }}
        """)
        refresh_btn.clicked.connect(self.manual_refresh)
        layout.addWidget(refresh_btn)
        
        # Market status
        market_group = QGroupBox("Market Status")
        market_layout = QVBoxLayout()
        
        self.market_status_label = QLabel()
        self.market_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.market_status_label.setStyleSheet("font-weight: bold; padding: 10px;")
        market_layout.addWidget(self.market_status_label)
        
        self.market_time_label = QLabel()
        self.market_time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.market_time_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        market_layout.addWidget(self.market_time_label)
        
        market_group.setLayout(market_layout)
        layout.addWidget(market_group)
        
        layout.addStretch()
        
        return sidebar
    
    def create_content_area(self) -> QWidget:
        """Create the main content area with news cards."""
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Header
        header = QLabel("📰 Latest News")
        header.setFont(QFont('Arial', 16, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {COLORS['text_primary']}; padding: 15px;")
        layout.addWidget(header)
        
        # Scroll area for news cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                background: {COLORS['bg_darker']};
            }}
            QScrollBar:vertical {{
                background: {COLORS['bg_darker']};
                width: 12px;
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical {{
                background: {COLORS['primary']};
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {COLORS['accent_green']};
            }}
        """)
        
        # Container for news cards
        self.news_container = QWidget()
        self.news_layout = QVBoxLayout(self.news_container)
        self.news_layout.setContentsMargins(10, 10, 10, 10)
        self.news_layout.setSpacing(10)
        self.news_layout.addStretch()
        
        scroll.setWidget(self.news_container)
        layout.addWidget(scroll)
        
        return content_widget
    
    def init_rss_manager(self):
        """Initialize the RSS feed manager."""
        try:
            self.rss_manager = RSSFeedManager(max_items=100)
            self.rss_manager.start_auto_update(interval=300)  # Update every 5 minutes
            self.status_bar.showMessage("RSS feed manager initialized")
            logger.info("RSS feed manager initialized")
            
            # Load initial news
            QTimer.singleShot(2000, self.load_news)
        except Exception as e:
            logger.error(f"Failed to initialize RSS manager: {e}")
            self.status_bar.showMessage(f"Error: {e}")
    
    def setup_timers(self):
        """Setup periodic update timers."""
        # Market status update timer (every 10 seconds)
        self.market_timer = QTimer()
        self.market_timer.timeout.connect(self.update_market_status)
        self.market_timer.start(10000)
        self.update_market_status()
        
        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.load_news)
        if self.auto_refresh_enabled:
            self.refresh_timer.start(self.refresh_interval * 1000)
    
    def update_market_status(self):
        """Update market status display."""
        status_msg = get_market_status_message()
        is_open = self.market_checker.is_market_open()
        
        if is_open:
            color = COLORS['accent_green']
            icon = "🟢"
        else:
            color = COLORS['accent_red']
            icon = "🔴"
        
        self.market_status_label.setText(f"{icon} {status_msg}")
        self.market_status_label.setStyleSheet(f"color: {color}; font-weight: bold; padding: 10px;")
        self.market_time_label.setText(datetime.now().strftime("%d %b %Y, %H:%M"))
    
    def load_news(self):
        """Load and display news items."""
        if not self.rss_manager:
            return
        
        try:
            # Fetch news items
            all_items = self.rss_manager.get_latest_items(self.news_count)
            
            # Filter by source
            if self.current_filter != "All Sources":
                items = [item for item in all_items if (item.source if hasattr(item, 'source') else item.get('source', '')) == self.current_filter]
            else:
                items = all_items
            
            # Clear existing cards
            self.clear_news_cards()
            
            # Create new cards
            if not items:
                no_news = QLabel("No news items available. Please wait for RSS feeds to load.")
                no_news.setAlignment(Qt.AlignmentFlag.AlignCenter)
                no_news.setStyleSheet(f"color: {COLORS['text_secondary']}; padding: 40px; font-size: 14px;")
                self.news_layout.insertWidget(0, no_news)
            else:
                for item in items:
                    card = NewsCard(item)
                    self.news_cards.append(card)
                    self.news_layout.insertWidget(len(self.news_cards) - 1, card)
            
            # Update status
            self.items_count_label.setText(f"Items: {len(items)}")
            self.last_update_label.setText(f"Last Updated: {datetime.now().strftime('%H:%M:%S')}")
            self.status_bar.showMessage(f"Loaded {len(items)} news items")
            
            logger.info(f"Loaded {len(items)} news items")
            
        except Exception as e:
            logger.error(f"Error loading news: {e}")
            self.status_bar.showMessage(f"Error loading news: {e}")
    
    def clear_news_cards(self):
        """Clear all news cards from the layout."""
        for card in self.news_cards:
            self.news_layout.removeWidget(card)
            card.deleteLater()
        self.news_cards.clear()
        
        # Also clear any "no news" labels
        for i in reversed(range(self.news_layout.count() - 1)):  # -1 to keep the stretch
            item = self.news_layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()
    
    def on_filter_changed(self, source: str):
        """Handle source filter change."""
        self.current_filter = source
        self.load_news()
    
    def on_count_changed(self, value: int):
        """Handle news count change."""
        self.news_count = value
        self.count_label.setText(f"Number of Items: {value}")
        self.load_news()
    
    def on_auto_refresh_toggled(self, state):
        """Handle auto-refresh toggle."""
        self.auto_refresh_enabled = (state == Qt.CheckState.Checked.value)
        
        if self.auto_refresh_enabled:
            self.refresh_timer.start(self.refresh_interval * 1000)
            self.status_bar.showMessage("Auto-refresh enabled")
        else:
            self.refresh_timer.stop()
            self.status_bar.showMessage("Auto-refresh disabled")
    
    def on_interval_changed(self, text: str):
        """Handle refresh interval change."""
        intervals = {
            "30 seconds": 30,
            "60 seconds": 60,
            "2 minutes": 120,
            "5 minutes": 300
        }
        self.refresh_interval = intervals.get(text, 60)
        
        if self.auto_refresh_enabled:
            self.refresh_timer.start(self.refresh_interval * 1000)
        
        self.status_bar.showMessage(f"Refresh interval set to {text}")
    
    def manual_refresh(self):
        """Manually refresh news."""
        self.status_bar.showMessage("Refreshing news...")
        if self.rss_manager:
            self.rss_manager.update_feeds()
        QTimer.singleShot(2000, self.load_news)
    
    def closeEvent(self, event):
        """Handle window close event."""
        if self.rss_manager:
            self.rss_manager.stop_auto_update()
        event.accept()


def main():
    """Main entry point for the news dashboard."""
    app = QApplication(sys.argv)
    app.setApplicationName("IndiPaperTrade News Dashboard")
    
    # Create and show the dashboard
    dashboard = NewsDashboard()
    dashboard.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
