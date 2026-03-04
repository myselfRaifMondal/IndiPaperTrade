"""Alert Management System."""

import logging
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Callable
import uuid

logger = logging.getLogger(__name__)


class AlertType(Enum):
    """Alert types."""
    PRICE = "PRICE"
    TRADE = "TRADE"
    RISK = "RISK"
    SYSTEM = "SYSTEM"


class AlertPriority(Enum):
    """Alert priority levels."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class Alert:
    """Alert representation."""
    alert_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    alert_type: AlertType = AlertType.SYSTEM
    priority: AlertPriority = AlertPriority.MEDIUM
    title: str = ""
    message: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    acknowledged: bool = False


class AlertManager:
    """Manage trading alerts and notifications."""
    
    def __init__(self):
        self.alerts: List[Alert] = []
        self.callbacks: List[Callable] = []
        self.price_alerts: dict = {}  # symbol -> trigger_price
        logger.info("Alert Manager initialized")
    
    def create_alert(self, alert_type: AlertType, priority: AlertPriority,
                    title: str, message: str) -> Alert:
        """Create and dispatch alert."""
        alert = Alert(
            alert_type=alert_type,
            priority=priority,
            title=title,
            message=message
        )
        
        self.alerts.append(alert)
        logger.info(f"Alert created: [{priority.value}] {title}")
        
        # Notify callbacks
        for callback in self.callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")
        
        return alert
    
    def add_price_alert(self, symbol: str, trigger_price: float, direction: str):
        """Add price alert."""
        self.price_alerts[symbol] = {
            'trigger_price': trigger_price,
            'direction': direction  # 'ABOVE' or 'BELOW'
        }
        logger.info(f"Price alert added: {symbol} {direction} ₹{trigger_price}")
    
    def check_price_alerts(self, symbol: str, current_price: float):
        """Check if price alerts should trigger."""
        if symbol not in self.price_alerts:
            return
        
        alert_config = self.price_alerts[symbol]
        trigger_price = alert_config['trigger_price']
        direction = alert_config['direction']
        
        triggered = False
        if direction == 'ABOVE' and current_price >= trigger_price:
            triggered = True
        elif direction == 'BELOW' and current_price <= trigger_price:
            triggered = True
        
        if triggered:
            self.create_alert(
                AlertType.PRICE,
                AlertPriority.MEDIUM,
                f"Price Alert: {symbol}",
                f"{symbol} reached ₹{current_price:.2f} (trigger: ₹{trigger_price:.2f})"
            )
            del self.price_alerts[symbol]
    
    def alert_order_filled(self, order):
        """Alert when order is filled."""
        self.create_alert(
            AlertType.TRADE,
            AlertPriority.LOW,
            "Order Filled",
            f"{order.side.value} {order.quantity} {order.symbol} @ ₹{order.filled_price:.2f}"
        )
    
    def alert_stop_loss_triggered(self, symbol: str, price: float):
        """Alert when stop loss is triggered."""
        self.create_alert(
            AlertType.TRADE,
            AlertPriority.HIGH,
            "Stop Loss Triggered",
            f"{symbol} stop loss triggered at ₹{price:.2f}"
        )
    
    def alert_daily_loss_exceeded(self, loss: float, limit: float):
        """Alert when daily loss limit is exceeded."""
        self.create_alert(
            AlertType.RISK,
            AlertPriority.CRITICAL,
            "Daily Loss Limit Exceeded",
            f"Daily loss ₹{loss:,.2f} exceeded limit ₹{limit:,.2f}"
        )
    
    def alert_drawdown_exceeded(self, drawdown_pct: float, threshold: float):
        """Alert when drawdown exceeds threshold."""
        self.create_alert(
            AlertType.RISK,
            AlertPriority.HIGH,
            "Drawdown Alert",
            f"Drawdown {drawdown_pct:.2f}% exceeded threshold {threshold:.2f}%"
        )
    
    def alert_connection_lost(self):
        """Alert when connection is lost."""
        self.create_alert(
            AlertType.SYSTEM,
            AlertPriority.CRITICAL,
            "Connection Lost",
            "Market data connection interrupted"
        )
    
    def register_callback(self, callback: Callable):
        """Register alert callback."""
        self.callbacks.append(callback)
    
    def get_unacknowledged_alerts(self) -> List[Alert]:
        """Get all unacknowledged alerts."""
        return [a for a in self.alerts if not a.acknowledged]
    
    def acknowledge_alert(self, alert_id: str):
        """Acknowledge alert."""
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                break
    
    def get_alerts_by_type(self, alert_type: AlertType) -> List[Alert]:
        """Get alerts by type."""
        return [a for a in self.alerts if a.alert_type == alert_type]
    
    def clear_old_alerts(self, hours: int = 24):
        """Clear alerts older than specified hours."""
        cutoff = datetime.now() - timedelta(hours=hours)
        self.alerts = [a for a in self.alerts if a.timestamp > cutoff]
