"""
Notification System for IndiPaperTrade

This module provides desktop notifications and visual alerts
for trading events.
"""

import logging
from enum import Enum
from typing import Optional
from PyQt6.QtWidgets import QSystemTrayIcon, QApplication
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class NotificationType(Enum):
    """Notification severity levels."""
    INFO = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    ERROR = "ERROR"
    STOP_LOSS_HIT = "STOP_LOSS_HIT"
    TAKE_PROFIT_HIT = "TAKE_PROFIT_HIT"
    PRICE_ALERT = "PRICE_ALERT"
    ORDER_FILLED = "ORDER_FILLED"
    ORDER_REJECTED = "ORDER_REJECTED"


class NotificationManager(QObject):
    """Manages notifications and alerts."""
    
    # Signals for UI updates
    notification_triggered = pyqtSignal(str, str, str)  # title, message, type
    
    def __init__(self):
        """Initialize notification manager."""
        super().__init__()
        self.tray_icon: Optional[QSystemTrayIcon] = None
        self.enabled = True
        logger.info("Notification manager initialized")
    
    def setup_tray_icon(self, icon: Optional[QIcon] = None):
        """
        Setup system tray icon for notifications.
        
        Args:
            icon: Optional QIcon for tray icon
        """
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon = QSystemTrayIcon()
            if icon:
                self.tray_icon.setIcon(icon)
            self.tray_icon.show()
            logger.info("System tray icon initialized")
        else:
            logger.warning("System tray not available")
    
    def show_notification(self, title: str, message: str, 
                         notification_type: NotificationType = NotificationType.INFO,
                         duration: int = 5000):
        """
        Show a desktop notification.
        
        Args:
            title: Notification title
            message: Notification message
            notification_type: Type of notification
            duration: Duration in milliseconds
        """
        if not self.enabled:
            return
        
        # Emit signal for UI
        self.notification_triggered.emit(title, message, notification_type.value)
        
        # Show system tray notification
        if self.tray_icon and self.tray_icon.isVisible():
            icon_type = self._get_icon_type(notification_type)
            self.tray_icon.showMessage(title, message, icon_type, duration)
            logger.info(f"Notification: {title} - {message}")
        else:
            # Fallback to console
            logger.info(f"[{notification_type.value}] {title}: {message}")
    
    def _get_icon_type(self, notification_type: NotificationType) -> QSystemTrayIcon.MessageIcon:
        """Get system tray icon type for notification."""
        if notification_type in [NotificationType.ERROR, NotificationType.ORDER_REJECTED]:
            return QSystemTrayIcon.MessageIcon.Critical
        elif notification_type in [NotificationType.WARNING, NotificationType.STOP_LOSS_HIT]:
            return QSystemTrayIcon.MessageIcon.Warning
        elif notification_type in [NotificationType.SUCCESS, NotificationType.TAKE_PROFIT_HIT, 
                                  NotificationType.ORDER_FILLED]:
            return QSystemTrayIcon.MessageIcon.Information
        else:
            return QSystemTrayIcon.MessageIcon.Information
    
    def show_stop_loss_alert(self, symbol: str, price: float, quantity: float):
        """Show stop loss triggered alert."""
        title = f"🛑 Stop Loss Hit - {symbol}"
        message = f"Stop loss triggered at ₹{price:.2f}\nQuantity: {quantity}"
        self.show_notification(title, message, NotificationType.STOP_LOSS_HIT)
    
    def show_take_profit_alert(self, symbol: str, price: float, quantity: float):
        """Show take profit triggered alert."""
        title = f"✅ Take Profit Hit - {symbol}"
        message = f"Take profit triggered at ₹{price:.2f}\nQuantity: {quantity}"
        self.show_notification(title, message, NotificationType.TAKE_PROFIT_HIT)
    
    def show_price_alert(self, symbol: str, condition: str, target_price: float, current_price: float):
        """Show price alert triggered."""
        title = f"📊 Price Alert - {symbol}"
        message = f"Price {condition} ₹{target_price:.2f}\nCurrent: ₹{current_price:.2f}"
        self.show_notification(title, message, NotificationType.PRICE_ALERT)
    
    def show_order_filled(self, symbol: str, side: str, quantity: float, price: float):
        """Show order filled notification."""
        title = f"Order Filled - {symbol}"
        message = f"{side} {quantity} @ ₹{price:.2f}"
        self.show_notification(title, message, NotificationType.ORDER_FILLED)
    
    def show_order_rejected(self, symbol: str, reason: str):
        """Show order rejected notification."""
        title = f"Order Rejected - {symbol}"
        message = f"Reason: {reason}"
        self.show_notification(title, message, NotificationType.ORDER_REJECTED)
    
    def enable(self):
        """Enable notifications."""
        self.enabled = True
        logger.info("Notifications enabled")
    
    def disable(self):
        """Disable notifications."""
        self.enabled = False
        logger.info("Notifications disabled")
    
    def is_enabled(self) -> bool:
        """Check if notifications are enabled."""
        return self.enabled
