"""
Modern Professional UI Stylesheet for IndiPaperTrade

Includes:
- Dark mode professional theme
- Modern color scheme with gradients
- Consistent typography
- Professional spacing and borders
"""

# Color Scheme
COLORS = {
    # Primary
    "primary": "#1E88E5",           # Professional Blue
    "primary_light": "#42A5F5",
    "primary_dark": "#1565C0",
    
    # Accent
    "accent_green": "#10B981",      # Success Green
    "accent_red": "#EF4444",        # Danger Red
    "accent_orange": "#F97316",     # Warning Orange
    "accent_yellow": "#FBBF24",     # Highlight Yellow
    
    # Background - Darker for professional terminal look
    "bg_dark": "#0A0E1A",           # Very Dark Blue-Black
    "bg_darker": "#060A14",         # Almost Black
    "bg_surface": "#141B2D",        # Panel Surface
    "bg_surface_light": "#1A2333",  # Lighter Panel
    
    # Text
    "text_primary": "#E8EDF4",      # Off White
    "text_secondary": "#9CA3AF",    # Light Gray
    "text_tertiary": "#6B7280",     # Medium Gray
    
    # Borders - More subtle
    "border": "#1F2937",            # Very Dark Border
    "border_light": "#374151",      # Subtle Border
    
    # Status
    "status_open": "#10B981",       # Green for OPEN
    "status_closed": "#EF4444",     # Red for CLOSED
    "status_premarket": "#F97316",  # Orange for PRE_MARKET
    "status_postmarket": "#8B5CF6", # Purple for POST_MARKET
}

# Main Application Stylesheet
MAIN_STYLESHEET = f"""
/* Main Application */
QMainWindow {{
    background-color: {COLORS['bg_darker']};
    color: {COLORS['text_primary']};
}}

/* Central Widget */
QWidget {{
    background-color: {COLORS['bg_darker']};
    color: {COLORS['text_primary']};
}}

/* Menu Bar & Tool Bar */
QMenuBar {{
    background-color: {COLORS['bg_dark']};
    color: {COLORS['text_primary']};
    border-bottom: 1px solid {COLORS['border']};
    padding: 5px 0px;
}}

QMenuBar::item:selected {{
    background-color: {COLORS['primary']};
}}

QToolBar {{
    background-color: {COLORS['bg_dark']};
    border-bottom: 1px solid {COLORS['border']};
    padding: 5px;
}}

/* Status Bar */
QStatusBar {{
    background-color: {COLORS['bg_dark']};
    color: {COLORS['text_secondary']};
    border-top: 1px solid {COLORS['border']};
    padding: 5px;
}}

QStatusBar::item {{
    border: none;
}}

/* Group Box */
QGroupBox {{
    background-color: transparent;
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 10px;
    font-weight: bold;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 3px 0 3px;
    color: {COLORS['primary_light']};
    font-size: 12px;
    font-weight: bold;
}}

/* Tabs */
QTabWidget {{
    background-color: {COLORS['bg_darker']};
    color: {COLORS['text_primary']};
}}

QTabBar::tab {{
    background-color: {COLORS['bg_surface']};
    color: {COLORS['text_secondary']};
    padding: 8px 20px;
    margin: 0px 2px;
    border: 1px solid {COLORS['border']};
    border-radius: 4px 4px 0px 0px;
}}

QTabBar::tab:selected {{
    background-color: {COLORS['primary']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['primary_dark']};
}}

QTabBar::tab:hover {{
    background-color: {COLORS['primary_light']};
}}

/* Tables */
QTableWidget {{
    background-color: rgba(10, 14, 26, 0.5);
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    gridline-color: {COLORS['border']};
    alternate-background-color: rgba(20, 27, 45, 0.3);
}}

QTableWidget::item {{
    padding: 6px;
    border: none;
}}

QTableWidget::item:selected {{
    background-color: {COLORS['primary']};
    color: {COLORS['text_primary']};
}}

QHeaderView::section {{
    background-color: {COLORS['primary']};
    color: {COLORS['text_primary']};
    padding: 10px;
    border: 1px solid {COLORS['border']};
    font-weight: bold;
    font-size: 11px;
}}

/* Buttons */
QPushButton {{
    background-color: {COLORS['primary']};
    color: {COLORS['text_primary']};
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: bold;
    font-size: 11px;
}}

QPushButton:hover {{
    background-color: {COLORS['primary_light']};
}}

QPushButton:pressed {{
    background-color: {COLORS['primary_dark']};
}}

QPushButton:disabled {{
    background-color: {COLORS['border']};
    color: {COLORS['text_tertiary']};
}}

/* Buy Button (Green) */
QPushButton#buyButton {{
    background-color: {COLORS['accent_green']};
}}

QPushButton#buyButton:hover {{
    background-color: #059669;
}}

QPushButton#buyButton:pressed {{
    background-color: #047857;
}}

/* Sell Button (Red) */
QPushButton#sellButton {{
    background-color: {COLORS['accent_red']};
}}

QPushButton#sellButton:hover {{
    background-color: #DC2626;
}}

QPushButton#sellButton:pressed {{
    background-color: #B91C1C;
}}

/* Reset Button */
QPushButton#resetButton {{
    background-color: {COLORS['accent_orange']};
}}

QPushButton#resetButton:hover {{
    background-color: #EA580C;
}}

/* Line Edit & Input Fields */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background-color: rgba(10, 14, 26, 0.8);
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    padding: 8px;
    font-size: 11px;
}}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
    border: 2px solid {COLORS['primary']};
    background-color: rgba(20, 27, 45, 0.9);
}}

QComboBox::drop-down {{
    border: none;
    width: 20px;
}}

QComboBox::down-arrow {{
    image: none;
}}

/* Labels */
QLabel {{
    color: {COLORS['text_primary']};
    background-color: transparent;
    font-size: 11px;
}}

QLabel#title {{
    font-size: 14px;
    font-weight: bold;
    color: {COLORS['primary_light']};
}}

QLabel#subtitle {{
    font-size: 12px;
    color: {COLORS['text_secondary']};
}}

QLabel#status {{
    font-size: 11px;
    font-weight: bold;
}}

/* Scroll Bar */
QScrollBar:vertical {{
    background-color: {COLORS['bg_surface']};
    width: 12px;
    border: none;
}}

QScrollBar::handle:vertical {{
    background-color: {COLORS['border_light']};
    border-radius: 6px;
    min-height: 20px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {COLORS['primary']};
}}

QScrollBar:horizontal {{
    background-color: {COLORS['bg_surface']};
    height: 12px;
    border: none;
}}

QScrollBar::handle:horizontal {{
    background-color: {COLORS['border_light']};
    border-radius: 6px;
    min-width: 20px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {COLORS['primary']};
}}

QScrollBar::add-line, QScrollBar::sub-line {{
    border: none;
    background: none;
}}

/* Splitter */
QSplitter::handle {{
    background-color: {COLORS['border']};
    width: 2px;
    height: 2px;
}}

QSplitter::handle:hover {{
    background-color: {COLORS['primary']};
}}

/* Message Box */
QMessageBox {{
    background-color: {COLORS['bg_surface']};
    color: {COLORS['text_primary']};
}}

QMessageBox QLabel {{
    color: {COLORS['text_primary']};
}}

QMessageBox QPushButton {{
    min-width: 60px;
}}
"""

# Market Clock Widget Stylesheet
MARKET_CLOCK_STYLESHEET = f"""
QGroupBox {{
    color: {COLORS['text_primary']};
    border: 2px solid {COLORS['primary']};
    border-radius: 8px;
    padding-top: 15px;
    margin-top: 5px;
    background-color: rgba(20, 27, 45, 0.4);
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
    color: {COLORS['primary_light']};
    font-size: 12px;
    font-weight: bold;
}}

QLabel {{
    color: {COLORS['text_primary']};
}}

QLabel#clockLabel {{
    font-size: 28px;
    font-weight: bold;
    color: {COLORS['accent_yellow']};
    font-family: "Courier New", monospace;
    background-color: transparent;
}}

QLabel#statusLabel {{
    font-size: 14px;
    font-weight: bold;
    padding: 8px 12px;
    border-radius: 4px;
}}

QLabel#timeMessageLabel {{
    font-size: 11px;
    color: {COLORS['text_secondary']};
}}

QLabel#statusLabel[status="OPEN"] {{
    background-color: {COLORS['status_open']};
    color: white;
}}

QLabel#statusLabel[status="CLOSED"] {{
    background-color: {COLORS['status_closed']};
    color: white;
}}

QLabel#statusLabel[status="PRE_MARKET"] {{
    background-color: {COLORS['status_premarket']};
    color: white;
}}

QLabel#statusLabel[status="POST_MARKET"] {{
    background-color: {COLORS['status_postmarket']};
    color: white;
}}

QLabel#statusLabel[status="WEEKEND"] {{
    background-color: {COLORS['text_tertiary']};
    color: white;
}}
"""

# Order Panel Stylesheet
ORDER_PANEL_STYLESHEET = f"""
QGroupBox {{
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding-top: 15px;
    margin-top: 5px;
    background-color: transparent;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
    color: {COLORS['primary_light']};
    font-size: 11px;
    font-weight: bold;
}}

QLabel {{
    color: {COLORS['text_secondary']};
    font-size: 10px;
}}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background-color: rgba(10, 14, 26, 0.8);
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    padding: 6px;
}}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
    border: 2px solid {COLORS['primary']};
}}
"""

# Market Watch Widget Stylesheet
MARKET_WATCH_STYLESHEET = f"""
QGroupBox {{
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding-top: 15px;
    background-color: transparent;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
    color: {COLORS['primary_light']};
    font-size: 11px;
    font-weight: bold;
}}

QTableWidget {{
    background-color: rgba(10, 14, 26, 0.3);
    color: {COLORS['text_primary']};
    border: none;
    gridline-color: {COLORS['border']};
}}

QTableWidget::item {{
    padding: 6px;
    border: none;
}}

QTableWidget::item:selected {{
    background-color: {COLORS['primary']};
}}

QHeaderView::section {{
    background-color: {COLORS['primary']};
    color: white;
    padding: 8px;
    border: none;
    font-weight: bold;
    font-size: 10px;
}}
"""

# Positions Widget Stylesheet
POSITIONS_WIDGET_STYLESHEET = f"""
QGroupBox {{
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding-top: 15px;
    background-color: transparent;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
    color: {COLORS['primary_light']};
    font-size: 11px;
    font-weight: bold;
}}

QTableWidget {{
    background-color: rgba(10, 14, 26, 0.3);
    color: {COLORS['text_primary']};
    border: none;
    gridline-color: {COLORS['border']};
}}

QTableWidget::item {{
    padding: 6px;
    border: none;
}}

QHeaderView::section {{
    background-color: {COLORS['primary']};
    color: white;
    padding: 8px;
    border: none;
    font-weight: bold;
}}
"""

# Margin Info Widget Stylesheet
MARGIN_INFO_STYLESHEET = f"""
QGroupBox {{
    color: {COLORS['text_primary']};
    border: 2px solid {COLORS['primary']};
    border-radius: 6px;
    padding-top: 15px;
    background-color: transparent;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
    color: {COLORS['primary_light']};
    font-size: 11px;
    font-weight: bold;
}}

QLabel {{
    color: {COLORS['text_secondary']};
}}

QLabel#valueLabel {{
    color: {COLORS['primary_light']};
    font-weight: bold;
    font-size: 12px;
}}

QLabel#warningLabel {{
    color: {COLORS['accent_orange']};
    font-weight: bold;
}}

QLabel#dangerLabel {{
    color: {COLORS['accent_red']};
    font-weight: bold;
}}
"""

# Order Book Widget Stylesheet
ORDER_BOOK_STYLESHEET = f"""
QGroupBox {{
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding-top: 15px;
    background-color: transparent;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
    color: {COLORS['primary_light']};
    font-size: 11px;
    font-weight: bold;
}}

QTableWidget {{
    background-color: rgba(10, 14, 26, 0.3);
    color: {COLORS['text_primary']};
    border: none;
    gridline-color: {COLORS['border']};
}}

QTableWidget::item {{
    padding: 6px;
    border: none;
}}

QHeaderView::section {{
    background-color: {COLORS['primary']};
    color: white;
    padding: 8px;
    border: none;
    font-weight: bold;
}}
"""

# Helper function to get profit/loss color
def get_pnl_color(value: float) -> str:
    """Get color for PnL value (positive=green, negative=red)."""
    if value > 0:
        return COLORS['accent_green']
    elif value < 0:
        return COLORS['accent_red']
    return COLORS['text_secondary']


# Helper function to format table item with color
def format_pnl_text(value: float) -> tuple:
    """Return formatted text and color for PnL value."""
    if value > 0:
        return f"+₹{value:.2f}", COLORS['accent_green']
    elif value < 0:
        return f"₹{value:.2f}", COLORS['accent_red']
    return f"₹{value:.2f}", COLORS['text_secondary']


# Icon colors for status indicators
STATUS_COLORS = {
    "OPEN": COLORS['status_open'],
    "CLOSED": COLORS['status_closed'],
    "PRE_MARKET": COLORS['status_premarket'],
    "POST_MARKET": COLORS['status_postmarket'],
    "WEEKEND": COLORS['text_tertiary'],
}
