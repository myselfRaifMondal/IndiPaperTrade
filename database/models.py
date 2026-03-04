"""
SQLAlchemy models for IndiPaperTrade.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Enum
from sqlalchemy.ext.declarative import declarative_base
from enum import Enum as PyEnum

Base = declarative_base()


class OrderStatus(PyEnum):
    """Order status enum."""
    PENDING = "PENDING"
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class OrderType(PyEnum):
    """Order type enum."""
    MARKET = "MARKET"
    LIMIT = "LIMIT"


class OrderSide(PyEnum):
    """Order side enum."""
    BUY = "BUY"
    SELL = "SELL"


class Order(Base):
    """Order model."""
    __tablename__ = 'orders'
    
    id = Column(String, primary_key=True)
    symbol = Column(String, nullable=False, index=True)
    side = Column(String, nullable=False)  # BUY or SELL
    quantity = Column(Integer, nullable=False)
    order_type = Column(String, nullable=False)  # MARKET or LIMIT
    price = Column(Float, nullable=True)  # None for market orders
    filled_price = Column(Float, nullable=True)
    status = Column(String, nullable=False)  # PENDING, FILLED, REJECTED, CANCELLED
    commission = Column(Float, default=0.0)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    filled_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<Order({self.symbol} {self.side} {self.quantity} {self.status})>"


class Position(Base):
    """Position model."""
    __tablename__ = 'positions'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String, nullable=False, unique=True, index=True)
    quantity = Column(Integer, nullable=False)
    entry_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=False)
    leverage = Column(Float, default=5.0)  # 5x leverage
    margin_used = Column(Float, nullable=False)
    unrealized_pnl = Column(Float, default=0.0)
    realized_pnl = Column(Float, default=0.0)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Position({self.symbol} {self.quantity} @ {self.entry_price})>"


class Trade(Base):
    """Trade/execution model."""
    __tablename__ = 'trades'
    
    id = Column(String, primary_key=True)
    order_id = Column(String, nullable=False, index=True)
    symbol = Column(String, nullable=False, index=True)
    side = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    commission = Column(Float, default=0.0)
    executed_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f"<Trade({self.symbol} {self.side} {self.quantity} @ {self.price})>"
