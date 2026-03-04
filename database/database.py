"""
Database manager for IndiPaperTrade.

Handles database initialization, CRUD operations, and persistence.
"""

import os
import logging
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from .models import Base, Order, Position, Trade

logger = logging.getLogger(__name__)


class Database:
    """Database manager for IndiPaperTrade."""
    
    def __init__(self, db_path: str = None):
        """
        Initialize database.
        
        Args:
            db_path: Path to SQLite database file. Defaults to data/trading.db
        """
        if db_path is None:
            db_path = os.path.join(
                os.path.dirname(__file__),
                '..',
                'data',
                'trading.db'
            )
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self.db_path = db_path
        self.engine = None
        self.Session = None
        
        self._initialize_engine()
        self._create_tables()
    
    def _initialize_engine(self):
        """Initialize SQLAlchemy engine."""
        db_url = f'sqlite:///{self.db_path}'
        
        self.engine = create_engine(
            db_url,
            connect_args={'check_same_thread': False},
            poolclass=StaticPool,
            echo=False
        )
        
        self.Session = sessionmaker(bind=self.engine)
        logger.info(f"Database initialized: {self.db_path}")
    
    def _create_tables(self):
        """Create all tables if they don't exist."""
        Base.metadata.create_all(self.engine)
        logger.info("Database tables created/verified")
    
    def reset(self):
        """Reset database - delete all data."""
        try:
            session = self.Session()
            
            # Delete all records
            session.query(Trade).delete()
            session.query(Order).delete()
            session.query(Position).delete()
            session.commit()
            session.close()
            
            logger.info("Database reset successfully")
            return True
        except Exception as e:
            logger.error(f"Error resetting database: {e}")
            return False
    
    def drop_and_recreate(self):
        """Drop and recreate all tables."""
        try:
            Base.metadata.drop_all(self.engine)
            Base.metadata.create_all(self.engine)
            logger.info("Database dropped and recreated")
            return True
        except Exception as e:
            logger.error(f"Error dropping and recreating database: {e}")
            return False
    
    # Order operations
    
    def add_order(self, order: Order) -> bool:
        """Add order to database."""
        try:
            session = self.Session()
            session.add(order)
            session.commit()
            session.close()
            logger.debug(f"Order added: {order.id}")
            return True
        except Exception as e:
            logger.error(f"Error adding order: {e}")
            return False
    
    def get_order(self, order_id: str) -> Order:
        """Get order by ID."""
        try:
            session = self.Session()
            order = session.query(Order).filter_by(id=order_id).first()
            session.close()
            return order
        except Exception as e:
            logger.error(f"Error getting order: {e}")
            return None
    
    def update_order(self, order_id: str, **kwargs) -> bool:
        """Update order fields."""
        try:
            session = self.Session()
            order = session.query(Order).filter_by(id=order_id).first()
            if order:
                for key, value in kwargs.items():
                    setattr(order, key, value)
                if 'status' in kwargs and kwargs['status'] == 'FILLED':
                    order.filled_at = datetime.utcnow()
                session.commit()
            session.close()
            return order is not None
        except Exception as e:
            logger.error(f"Error updating order: {e}")
            return False
    
    def get_all_orders(self, symbol: str = None, status: str = None) -> list:
        """Get all orders, optionally filtered."""
        try:
            session = self.Session()
            query = session.query(Order)
            
            if symbol:
                query = query.filter_by(symbol=symbol)
            if status:
                query = query.filter_by(status=status)
            
            orders = query.order_by(Order.timestamp.desc()).all()
            session.close()
            return orders
        except Exception as e:
            logger.error(f"Error getting orders: {e}")
            return []
    
    # Position operations
    
    def add_position(self, position: Position) -> bool:
        """Add position to database."""
        try:
            session = self.Session()
            session.add(position)
            session.commit()
            session.close()
            logger.debug(f"Position added: {position.symbol}")
            return True
        except Exception as e:
            logger.error(f"Error adding position: {e}")
            return False
    
    def get_position(self, symbol: str) -> Position:
        """Get position by symbol."""
        try:
            session = self.Session()
            position = session.query(Position).filter_by(symbol=symbol).first()
            session.close()
            return position
        except Exception as e:
            logger.error(f"Error getting position: {e}")
            return None
    
    def update_position(self, symbol: str, **kwargs) -> bool:
        """Update position fields."""
        try:
            session = self.Session()
            position = session.query(Position).filter_by(symbol=symbol).first()
            if position:
                for key, value in kwargs.items():
                    setattr(position, key, value)
                session.commit()
            session.close()
            return position is not None
        except Exception as e:
            logger.error(f"Error updating position: {e}")
            return False
    
    def get_all_positions(self) -> list:
        """Get all positions."""
        try:
            session = self.Session()
            positions = session.query(Position).all()
            session.close()
            return positions
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
    
    def delete_position(self, symbol: str) -> bool:
        """Delete position by symbol (when quantity reaches 0)."""
        try:
            session = self.Session()
            session.query(Position).filter_by(symbol=symbol).delete()
            session.commit()
            session.close()
            logger.debug(f"Position deleted: {symbol}")
            return True
        except Exception as e:
            logger.error(f"Error deleting position: {e}")
            return False
    
    # Trade operations
    
    def add_trade(self, trade: Trade) -> bool:
        """Add trade to database."""
        try:
            session = self.Session()
            session.add(trade)
            session.commit()
            session.close()
            logger.debug(f"Trade added: {trade.id}")
            return True
        except Exception as e:
            logger.error(f"Error adding trade: {e}")
            return False
    
    def get_trades(self, symbol: str = None, limit: int = None) -> list:
        """Get trades, optionally filtered."""
        try:
            session = self.Session()
            query = session.query(Trade)
            
            if symbol:
                query = query.filter_by(symbol=symbol)
            
            trades = query.order_by(Trade.executed_at.desc())
            
            if limit:
                trades = trades.limit(limit)
            
            trades = trades.all()
            session.close()
            return trades
        except Exception as e:
            logger.error(f"Error getting trades: {e}")
            return []
    
    def get_session(self) -> Session:
        """Get a new database session."""
        return self.Session()
