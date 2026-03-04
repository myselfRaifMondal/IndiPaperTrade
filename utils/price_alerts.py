"""
Price Alert System for IndiPaperTrade

This module provides price alert functionality with configurable conditions
and notification callbacks.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Callable, Optional
from threading import RLock
import uuid

logger = logging.getLogger(__name__)


class AlertCondition(Enum):
    """Alert trigger conditions."""
    ABOVE = "ABOVE"  # Price goes above target
    BELOW = "BELOW"  # Price goes below target
    CROSSES = "CROSSES"  # Price crosses target (either direction)


class AlertStatus(Enum):
    """Alert status."""
    ACTIVE = "ACTIVE"
    TRIGGERED = "TRIGGERED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


@dataclass
class PriceAlert:
    """Price alert configuration."""
    symbol: str
    target_price: float
    condition: AlertCondition
    alert_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: AlertStatus = AlertStatus.ACTIVE
    created_at: datetime = field(default_factory=datetime.now)
    triggered_at: Optional[datetime] = None
    message: Optional[str] = None
    last_price: Optional[float] = None  # Track last known price for CROSSES condition
    
    def __post_init__(self):
        """Validate alert after initialization."""
        if self.target_price <= 0:
            raise ValueError("Target price must be positive")
    
    def should_trigger(self, current_price: float) -> bool:
        """Check if alert should trigger at current price."""
        if self.status != AlertStatus.ACTIVE:
            return False
        
        if self.condition == AlertCondition.ABOVE:
            return current_price > self.target_price
        elif self.condition == AlertCondition.BELOW:
            return current_price < self.target_price
        elif self.condition == AlertCondition.CROSSES:
            if self.last_price is None:
                return False
            # Check if price crossed target
            crossed_up = self.last_price <= self.target_price < current_price
            crossed_down = self.last_price >= self.target_price > current_price
            return crossed_up or crossed_down
        
        return False
    
    def trigger(self):
        """Mark alert as triggered."""
        self.status = AlertStatus.TRIGGERED
        self.triggered_at = datetime.now()
        logger.info(f"Alert {self.alert_id} triggered for {self.symbol} at {self.target_price}")
    
    def update_price(self, price: float):
        """Update last known price for CROSSES condition."""
        self.last_price = price


class AlertManager:
    """Manages price alerts and notifications."""
    
    def __init__(self):
        """Initialize alert manager."""
        self.alerts: Dict[str, PriceAlert] = {}
        self.alert_callbacks: List[Callable] = []
        self.lock = RLock()
        logger.info("Alert manager initialized")
    
    def add_callback(self, callback: Callable):
        """Add callback for alert triggers."""
        self.alert_callbacks.append(callback)
    
    def add_alert(self, symbol: str, target_price: float, condition: AlertCondition, 
                  message: Optional[str] = None) -> PriceAlert:
        """
        Add a new price alert.
        
        Args:
            symbol: Trading symbol
            target_price: Price to trigger alert
            condition: Alert condition (ABOVE/BELOW/CROSSES)
            message: Optional custom message
            
        Returns:
            Created PriceAlert object
        """
        with self.lock:
            alert = PriceAlert(
                symbol=symbol,
                target_price=target_price,
                condition=condition,
                message=message
            )
            self.alerts[alert.alert_id] = alert
            logger.info(f"Added alert {alert.alert_id}: {symbol} {condition.value} {target_price}")
            return alert
    
    def remove_alert(self, alert_id: str) -> bool:
        """
        Remove an alert.
        
        Args:
            alert_id: Alert ID to remove
            
        Returns:
            True if alert was removed, False if not found
        """
        with self.lock:
            if alert_id in self.alerts:
                alert = self.alerts.pop(alert_id)
                logger.info(f"Removed alert {alert_id} for {alert.symbol}")
                return True
            return False
    
    def get_alert(self, alert_id: str) -> Optional[PriceAlert]:
        """Get alert by ID."""
        return self.alerts.get(alert_id)
    
    def get_active_alerts(self, symbol: Optional[str] = None) -> List[PriceAlert]:
        """Get all active alerts, optionally filtered by symbol."""
        with self.lock:
            alerts = [a for a in self.alerts.values() if a.status == AlertStatus.ACTIVE]
            if symbol:
                alerts = [a for a in alerts if a.symbol == symbol]
            return alerts
    
    def get_all_alerts(self) -> List[PriceAlert]:
        """Get all alerts regardless of status."""
        return list(self.alerts.values())
    
    def check_alerts(self, symbol: str, current_price: float):
        """
        Check alerts for a symbol at current price.
        
        Args:
            symbol: Trading symbol
            current_price: Current market price
        """
        with self.lock:
            triggered_alerts = []
            
            for alert in self.get_active_alerts(symbol):
                # Update last price for CROSSES condition
                if alert.condition == AlertCondition.CROSSES:
                    alert.update_price(current_price)
                
                # Check if should trigger
                if alert.should_trigger(current_price):
                    alert.trigger()
                    triggered_alerts.append(alert)
            
            # Notify callbacks
            for alert in triggered_alerts:
                self._notify_callbacks(alert, current_price)
    
    def _notify_callbacks(self, alert: PriceAlert, current_price: float):
        """Notify all callbacks about triggered alert."""
        for callback in self.alert_callbacks:
            try:
                callback(alert, current_price)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")
    
    def cancel_alert(self, alert_id: str) -> bool:
        """Cancel an active alert."""
        with self.lock:
            alert = self.get_alert(alert_id)
            if alert and alert.status == AlertStatus.ACTIVE:
                alert.status = AlertStatus.CANCELLED
                logger.info(f"Cancelled alert {alert_id}")
                return True
            return False
    
    def clear_triggered_alerts(self):
        """Remove all triggered alerts."""
        with self.lock:
            triggered_ids = [aid for aid, alert in self.alerts.items() 
                           if alert.status == AlertStatus.TRIGGERED]
            for aid in triggered_ids:
                self.alerts.pop(aid)
            logger.info(f"Cleared {len(triggered_ids)} triggered alerts")
