"""
Order Simulation Engine for Paper Trading Platform

This module simulates order execution for paper trading without sending
orders to the real broker. It provides realistic execution simulation with:

- Market orders: Execute immediately at current market price
- Limit orders: Execute when price condition is met
- Slippage simulation: Realistic price impact
- Spread simulation: Bid-ask spread consideration
- Order validation: Check quantity, price, capital
- Order book management: Track all orders

The engine integrates with the Market Data Engine to fetch real-time
prices and executes orders based on configured simulation parameters.

Usage:
    from execution_engine import OrderSimulator
    from data_engine import MarketDataEngine
    
    # Initialize
    data_engine = MarketDataEngine()
    simulator = OrderSimulator(data_engine)
    
    # Place market order
    order = simulator.place_market_order("RELIANCE", OrderSide.BUY, 10)
    
    # Place limit order
    order = simulator.place_limit_order("TCS", OrderSide.SELL, 5, 3500.0)
    
    # Check order status
    status = simulator.get_order_status(order.order_id)
"""

import logging
import threading
import time
from typing import Optional, Dict, List, Callable
from datetime import datetime
from threading import RLock

from execution_engine.order_types import (
    Order, OrderType, OrderSide, OrderStatus,
    TimeInForce, ExecutionReport
)
from utils.price_alerts import AlertManager, AlertCondition

logger = logging.getLogger(__name__)


class OrderSimulator:
    """
    Simulates order execution for paper trading.
    
    Features:
    - Market and limit order execution
    - Slippage simulation
    - Spread simulation
    - Order validation
    - Order book management
    - Execution callbacks
    
    Attributes:
        data_engine: Market data engine for price fetching
        enable_slippage: Enable slippage simulation
        slippage_percent: Slippage percentage (0.01 = 0.01%)
        enable_spread: Enable bid-ask spread
        spread_percent: Spread percentage
        orders: Dictionary of all orders
        executions: List of execution reports
        callbacks: Order execution callbacks
    """
    
    def __init__(
        self,
        data_engine,
        enable_slippage: bool = False,
        slippage_percent: float = 0.01,
        enable_spread: bool = True,
        spread_percent: float = 0.02,
        max_slippage_percent: float = 0.1
    ):
        """
        Initialize order simulator.
        
        Args:
            data_engine: Market data engine instance
            enable_slippage: Enable slippage simulation
            slippage_percent: Default slippage percentage
            enable_spread: Enable spread simulation
            spread_percent: Default spread percentage
            max_slippage_percent: Maximum allowed slippage
        """
        self.data_engine = data_engine
        self.enable_slippage = enable_slippage
        self.slippage_percent = slippage_percent
        self.enable_spread = enable_spread
        self.spread_percent = spread_percent
        self.max_slippage_percent = max_slippage_percent
        
        # Order book
        self.orders: Dict[str, Order] = {}
        self.executions: List[ExecutionReport] = []
        self.lock = RLock()
        
        # Callbacks
        self.execution_callbacks: List[Callable] = []
        
        # Alert manager for price alerts
        self.alert_manager = AlertManager()
        
        # Track positions for SL/TP monitoring
        self.positions: Dict[str, Dict] = {}  # symbol -> {quantity, avg_price, sl, tp}
        
        # Track previous prices for gap detection in limit orders
        self.previous_prices: Dict[str, float] = {}  # symbol -> previous_ltp
        
        # Background processing
        self.running = False
        self.process_thread: Optional[threading.Thread] = None
        
        logger.info(
            f"Order simulator initialized | Slippage: {enable_slippage} "
            f"({slippage_percent}%) | Spread: {enable_spread} ({spread_percent}%)"
        )
    
    def place_order(self, order: Order) -> Order:
        """
        Place an order.
        
        Args:
            order: Order to place
        
        Returns:
            Order: The placed order
        
        Raises:
            ValueError: If order validation fails
        """
        # Validate order
        self._validate_order(order)
        
        # Add to order book
        with self.lock:
            self.orders[order.order_id] = order
        
        logger.info(f"Order placed: {order}")
        
        # Try immediate execution for market orders
        if order.is_market_order():
            self._execute_market_order(order)
        
        return order
    
    def place_market_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: int,
        user_data: Optional[Dict] = None
    ) -> Order:
        """
        Place a market order.
        
        Market orders execute immediately at the current market price.
        
        Args:
            symbol: Trading symbol
            side: Buy or Sell
            quantity: Quantity to trade
            user_data: Optional user-defined data
        
        Returns:
            Order: Placed order
        
        Example:
            >>> order = simulator.place_market_order("RELIANCE", OrderSide.BUY, 10)
            >>> print(order.status)
            FILLED
        """
        order = Order(
            symbol=symbol,
            order_type=OrderType.MARKET,
            side=side,
            quantity=quantity,
            user_data=user_data or {}
        )
        
        return self.place_order(order)
    
    def place_limit_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: int,
        price: float,
        time_in_force: TimeInForce = TimeInForce.DAY,
        user_data: Optional[Dict] = None
    ) -> Order:
        """
        Place a limit order.
        
        Limit orders execute only when price condition is met:
        - BUY: Execute when LTP <= limit price
        - SELL: Execute when LTP >= limit price
        
        Args:
            symbol: Trading symbol
            side: Buy or Sell
            quantity: Quantity to trade
            price: Limit price
            time_in_force: Time validity
            user_data: Optional user-defined data
        
        Returns:
            Order: Placed order
        
        Example:
            >>> order = simulator.place_limit_order("TCS", OrderSide.SELL, 5, 3500.0)
            >>> print(order.status)
            PENDING
        """
        order = Order(
            symbol=symbol,
            order_type=OrderType.LIMIT,
            side=side,
            quantity=quantity,
            price=price,
            time_in_force=time_in_force,
            user_data=user_data or {}
        )
        
        return self.place_order(order)
    
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an order.
        
        Args:
            order_id: Order ID to cancel
        
        Returns:
            bool: True if cancelled, False otherwise
        """
        with self.lock:
            order = self.orders.get(order_id)
            
            if order is None:
                logger.warning(f"Order not found: {order_id}")
                return False
            
            if order.cancel():
                logger.info(f"Order cancelled: {order_id}")
                return True
            else:
                logger.warning(f"Cannot cancel order: {order_id} (status: {order.status.value})")
                return False
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """
        Get order by ID.
        
        Args:
            order_id: Order identifier
        
        Returns:
            Order: Order if found, None otherwise
        """
        with self.lock:
            return self.orders.get(order_id)
    
    def get_order_status(self, order_id: str) -> Optional[OrderStatus]:
        """
        Get order status.
        
        Args:
            order_id: Order identifier
        
        Returns:
            OrderStatus: Order status if found, None otherwise
        """
        order = self.get_order(order_id)
        return order.status if order else None
    
    def get_all_orders(self) -> List[Order]:
        """
        Get all orders.
        
        Returns:
            list: List of all orders
        """
        with self.lock:
            return list(self.orders.values())
    
    def get_active_orders(self) -> List[Order]:
        """
        Get active (pending/partial) orders.
        
        Returns:
            list: List of active orders
        """
        with self.lock:
            return [order for order in self.orders.values() if order.is_active()]
    
    def get_filled_orders(self) -> List[Order]:
        """
        Get filled orders.
        
        Returns:
            list: List of filled orders
        """
        with self.lock:
            return [order for order in self.orders.values() if order.is_filled()]
    
    def get_executions(self) -> List[ExecutionReport]:
        """
        Get all execution reports.
        
        Returns:
            list: List of execution reports
        """
        with self.lock:
            return self.executions.copy()
    
    def register_execution_callback(self, callback: Callable[[ExecutionReport], None]) -> None:
        """
        Register callback for order executions.
        
        Args:
            callback: Callback function (execution_report) -> None
        
        Example:
            >>> def on_execution(report):
            ...     print(f"Executed: {report.symbol} @ {report.price}")
            >>> simulator.register_execution_callback(on_execution)
        """
        if callback not in self.execution_callbacks:
            self.execution_callbacks.append(callback)
            logger.debug("Execution callback registered")
    
    def start(self) -> None:
        """
        Start background order processing.
        
        This starts a thread that continuously checks limit orders
        and executes them when price conditions are met.
        """
        if self.running:
            logger.warning("Order simulator already running")
            return
        
        self.running = True
        self.process_thread = threading.Thread(
            target=self._process_loop,
            daemon=True,
            name="OrderSimulator"
        )
        self.process_thread.start()
        logger.info("Order simulator started")
    
    def stop(self) -> None:
        """Stop background order processing."""
        if not self.running:
            return
        
        self.running = False
        if self.process_thread:
            self.process_thread.join(timeout=5.0)
        
        logger.info("Order simulator stopped")
    
    def _validate_order(self, order: Order) -> None:
        """
        Validate order before placement.
        
        Args:
            order: Order to validate
        
        Raises:
            ValueError: If validation fails
        """
        # Check symbol exists in market data
        if not self.data_engine:
            raise ValueError("Market data engine not available")
        
        # Basic validations (already done in Order.__post_init__)
        # Additional validations can be added here
        pass
    
    def _execute_market_order(self, order: Order) -> bool:
        """
        Execute market order immediately.
        
        Args:
            order: Market order to execute
        
        Returns:
            bool: True if executed, False otherwise
        """
        try:
            # Get current price
            price_data = self.data_engine.get_price_data(order.symbol)
            
            if not price_data or not price_data.ltp:
                logger.error(f"No price data for {order.symbol}")
                order.update_status(OrderStatus.REJECTED, "No price data available")
                return False
            
            # Calculate execution price with slippage and spread
            execution_price = self._calculate_execution_price(
                ltp=price_data.ltp,
                side=order.side,
                bid=price_data.bid,
                ask=price_data.ask
            )
            
            # Fill the order
            order.fill(quantity=order.quantity, price=execution_price)
            
            # Create execution report
            slippage = self._calculate_slippage(price_data.ltp, execution_price, order.side)
            spread = self._calculate_spread(price_data.bid, price_data.ask) if self.enable_spread else 0.0
            
            report = ExecutionReport(
                order_id=order.order_id,
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                price=execution_price,
                slippage=slippage,
                spread=spread
            )
            
            with self.lock:
                self.executions.append(report)
            
            # Invoke callbacks
            self._invoke_execution_callbacks(report)
            
            logger.info(
                f"Market order executed: {order.symbol} {order.side.value} "
                f"{order.quantity} @ ₹{execution_price:.2f} "
                f"(slippage: {slippage:.4f}%, spread: {spread:.4f}%)"
            )
            
            return True
        
        except Exception as e:
            logger.error(f"Market order execution failed: {e}")
            order.update_status(OrderStatus.REJECTED, str(e))
            return False
    
    def _check_limit_order(self, order: Order) -> bool:
        """
        Check if limit order should be executed.
        
        Handles price gaps and volatility by checking if price has crossed
        the limit level (using bid/ask in addition to LTP). Detects gaps
        by comparing current price with previous price.
        
        Args:
            order: Limit order to check
        
        Returns:
            bool: True if should execute, False otherwise
        """
        try:
            # Get current price data
            price_data = self.data_engine.get_price_data(order.symbol)
            
            if not price_data or not price_data.ltp:
                return False
            
            ltp = price_data.ltp
            bid = price_data.bid if hasattr(price_data, 'bid') and price_data.bid else ltp
            ask = price_data.ask if hasattr(price_data, 'ask') and price_data.ask else ltp
            
            # Get previous price for gap detection
            prev_ltp = self.previous_prices.get(order.symbol, ltp)
            
            # Update previous price for next check
            self.previous_prices[order.symbol] = ltp
            
            # Tolerance for floating-point comparison (0.01 = 1 paisa)
            tolerance = 0.01
            
            # Check execution condition - handles gaps where price jumps past limit
            if order.side == OrderSide.BUY:
                # BUY limit: Execute when:
                # 1. Current LTP <= limit price (with tolerance), OR
                # 2. Ask crossed below limit (bid-ask available), OR
                # 3. Price gapped OVER limit (prev_price > limit >= current_price)
                limit_price = order.price
                current_meets = ltp <= limit_price + tolerance
                ask_meets = ask <= limit_price + tolerance if ask else False
                gap_crossed = prev_ltp > limit_price >= ltp  # Gapped down through limit
                
                return current_meets or ask_meets or gap_crossed
            else:
                # SELL limit: Execute when:
                # 1. Current LTP >= limit price (with tolerance), OR
                # 2. Bid crossed above limit (bid-ask available), OR
                # 3. Price gapped OVER limit (prev_price < limit <= current_price)
                limit_price = order.price
                current_meets = ltp >= limit_price - tolerance
                bid_meets = bid >= limit_price - tolerance if bid else False
                gap_crossed = prev_ltp < limit_price <= ltp  # Gapped up through limit
                
                return current_meets or bid_meets or gap_crossed
        
        except Exception as e:
            logger.error(f"Error checking limit order: {e}")
            return False
    
    def _execute_limit_order(self, order: Order) -> bool:
        """
        Execute limit order.
        
        Args:
            order: Limit order to execute
        
        Returns:
            bool: True if executed, False otherwise
        """
        try:
            # Execution price is the limit price (best case scenario)
            # In real trading, you might get a better price
            execution_price = order.price
            
            # Apply spread if enabled
            if self.enable_spread:
                price_data = self.data_engine.get_price_data(order.symbol)
                if price_data and price_data.bid and price_data.ask:
                    spread_amount = (price_data.ask - price_data.bid) / 2
                    if order.side == OrderSide.BUY:
                        execution_price += spread_amount
                    else:
                        execution_price -= spread_amount
            
            # Fill the order
            order.fill(quantity=order.quantity, price=execution_price)
            
            # Create execution report
            report = ExecutionReport(
                order_id=order.order_id,
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                price=execution_price,
                slippage=0.0,  # No slippage for limit orders
                spread=0.0
            )
            
            with self.lock:
                self.executions.append(report)
            
            # Invoke callbacks
            self._invoke_execution_callbacks(report)
            
            logger.info(
                f"Limit order executed: {order.symbol} {order.side.value} "
                f"{order.quantity} @ ₹{execution_price:.2f}"
            )
            
            return True
        
        except Exception as e:
            logger.error(f"Limit order execution failed: {e}")
            order.update_status(OrderStatus.REJECTED, str(e))
            return False
    
    def _calculate_execution_price(
        self,
        ltp: float,
        side: OrderSide,
        bid: Optional[float] = None,
        ask: Optional[float] = None
    ) -> float:
        """
        Calculate execution price with slippage and spread.
        
        Args:
            ltp: Last traded price
            side: Buy or Sell
            bid: Bid price (optional)
            ask: Ask price (optional)
        
        Returns:
            float: Execution price
        """
        price = ltp
        
        # Apply spread if enabled and bid/ask available
        if self.enable_spread and bid and ask:
            if side == OrderSide.BUY:
                # Buy at ask price
                price = ask
            else:
                # Sell at bid price
                price = bid
        
        # Apply slippage if enabled
        if self.enable_slippage:
            slippage_amount = price * (self.slippage_percent / 100)
            
            # Slippage works against you
            if side == OrderSide.BUY:
                price += slippage_amount
            else:
                price -= slippage_amount
        
        return round(price, 2)
    
    def _calculate_slippage(self, ltp: float, execution_price: float, side: OrderSide) -> float:
        """
        Calculate slippage percentage.
        
        Args:
            ltp: Last traded price
            execution_price: Actual execution price
            side: Order side
        
        Returns:
            float: Slippage percentage
        """
        if ltp == 0:
            return 0.0
        
        slippage = ((execution_price - ltp) / ltp) * 100
        
        # Slippage should be positive (cost)
        if side == OrderSide.SELL:
            slippage = -slippage
        
        return round(slippage, 4)
    
    def _calculate_spread(self, bid: Optional[float], ask: Optional[float]) -> float:
        """
        Calculate bid-ask spread percentage.
        
        Args:
            bid: Bid price
            ask: Ask price
        
        Returns:
            float: Spread percentage
        """
        if not bid or not ask or bid == 0:
            return 0.0
        
        spread = ((ask - bid) / bid) * 100
        return round(spread, 4)
    
    def _invoke_execution_callbacks(self, report: ExecutionReport) -> None:
        """
        Invoke execution callbacks.
        
        Args:
            report: Execution report
        """
        for callback in self.execution_callbacks:
            try:
                callback(report)
            except Exception as e:
                logger.error(f"Error in execution callback: {e}")
    
    def _check_stop_loss_order(self, order: Order) -> bool:
        """
        Check if stop loss order should be triggered.
        
        Includes gap detection: if price jumps over the trigger level,
        the stop loss will still execute.
        
        Args:
            order: Stop loss order to check
        
        Returns:
            bool: True if should trigger, False otherwise
        """
        try:
            if not order.trigger_price:
                return False
            
            # Get current price
            price_data = self.data_engine.get_price_data(order.symbol)
            
            if not price_data or not price_data.ltp:
                return False
            
            ltp = price_data.ltp
            trigger_price = order.trigger_price
            
            # Get previous price for gap detection
            prev_ltp = self.previous_prices.get(order.symbol, ltp)
            
            # Update previous price for next check
            self.previous_prices[order.symbol] = ltp
            
            # Tolerance for floating-point comparison (0.01 = 1 paisa)
            tolerance = 0.01
            
            # Check trigger condition with gap detection
            if order.side == OrderSide.SELL:  # Stop loss for long position
                # Trigger when price drops below or crosses stop price
                current_meets = ltp <= trigger_price + tolerance
                gap_crossed = prev_ltp > trigger_price >= ltp  # Down-gap detection
                return current_meets or gap_crossed
                
            else:  # Stop loss for short position
                # Trigger when price rises above or crosses stop price
                current_meets = ltp >= trigger_price - tolerance
                gap_crossed = prev_ltp < trigger_price <= ltp  # Up-gap detection
                return current_meets or gap_crossed
        
        except Exception as e:
            logger.error(f"Error checking stop loss order: {e}")
            return False
    
    def _execute_stop_loss_order(self, order: Order) -> bool:
        """
        Execute stop loss order.
        
        Args:
            order: Stop loss order to execute
        
        Returns:
            bool: True if executed, False otherwise
        """
        try:
            logger.info(f"Stop loss triggered for {order.symbol} at {order.trigger_price}")
            
            # Get current price
            price_data = self.data_engine.get_price_data(order.symbol)
            
            if not price_data or not price_data.ltp:
                order.update_status(OrderStatus.REJECTED, "No market data available")
                return False
            
            # Execute as market order at current price
            execution_price = self._calculate_execution_price(
                ltp=price_data.ltp,
                side=order.side,
                bid=price_data.bid,
                ask=price_data.ask
            )
            
            # Fill the order
            order.fill(quantity=order.quantity, price=execution_price)
            
            # Create execution report
            slippage = self._calculate_slippage(price_data.ltp, execution_price, order.side)
            spread = self._calculate_spread(price_data.bid, price_data.ask) if self.enable_spread else 0.0
            
            report = ExecutionReport(
                order_id=order.order_id,
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                price=execution_price,
                slippage=slippage,
                spread=spread
            )
            
            with self.lock:
                self.executions.append(report)
            
            # Invoke callbacks
            self._invoke_execution_callbacks(report)
            
            logger.info(
                f"Stop loss order executed: {order.symbol} {order.side.value} "
                f"{order.quantity} @ ₹{execution_price:.2f} "
                f"(trigger: ₹{order.trigger_price:.2f})"
            )
            
            return True
        
        except Exception as e:
            logger.error(f"Stop loss order execution failed: {e}")
            order.update_status(OrderStatus.REJECTED, str(e))
            return False
    
    def place_stop_loss_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: int,
        trigger_price: float,
        user_data: Optional[Dict] = None
    ) -> Order:
        """
        Place a stop loss order.
        
        Stop loss orders trigger when price crosses trigger level:
        - SELL stop loss (long protection): Triggers when price drops to trigger
        - BUY stop loss (short protection): Triggers when price rises to trigger
        
        Args:
            symbol: Trading symbol
            side: Buy or Sell
            quantity: Quantity to trade
            trigger_price: Price to trigger stop loss
            user_data: Optional user-defined data
        
        Returns:
            Order: Placed order
        
        Example:
            >>> # Protect long position - sell if price drops to 2950
            >>> order = simulator.place_stop_loss_order("RELIANCE", OrderSide.SELL, 10, 2950.0)
        """
        order = Order(
            symbol=symbol,
            order_type=OrderType.STOP_LOSS,
            side=side,
            quantity=quantity,
            trigger_price=trigger_price,
            user_data=user_data or {}
        )
        
        return self.place_order(order)
    
    def _process_loop(self) -> None:
        """Background loop for processing limit orders, stop loss, and price alerts."""
        logger.info("Order processing loop started")
        
        while self.running:
            try:
                # Get active limit orders
                active_orders = [
                    order for order in self.get_active_orders()
                    if order.is_limit_order()
                ]
                
                # Check each limit order
                for order in active_orders:
                    if self._check_limit_order(order):
                        self._execute_limit_order(order)
                
                # Check stop loss orders
                stop_loss_orders = [
                    order for order in self.get_active_orders()
                    if order.is_stop_loss_order()
                ]
                
                for order in stop_loss_orders:
                    if self._check_stop_loss_order(order):
                        self._execute_stop_loss_order(order)
                
                # Check price alerts
                with self.lock:
                    symbols = set(order.symbol for order in self.orders.values() if order.is_active())
                    
                    for symbol in symbols:
                        try:
                            price_data = self.data_engine.get_price_data(symbol)
                            if price_data and price_data.ltp:
                                self.alert_manager.check_alerts(symbol, price_data.ltp)
                        except Exception as e:
                            logger.error(f"Error checking alerts for {symbol}: {e}")
                
                # Sleep briefly
                time.sleep(0.5)
            
            except Exception as e:
                logger.error(f"Error in order processing loop: {e}")
                time.sleep(1.0)
        
        logger.info("Order processing loop stopped")
    
    def get_statistics(self) -> Dict:
        """
        Get order execution statistics.
        
        Returns:
            dict: Statistics
        """
        with self.lock:
            orders = list(self.orders.values())
            
            return {
                'total_orders': len(orders),
                'pending_orders': len([o for o in orders if o.status == OrderStatus.PENDING]),
                'filled_orders': len([o for o in orders if o.status == OrderStatus.FILLED]),
                'cancelled_orders': len([o for o in orders if o.status == OrderStatus.CANCELLED]),
                'rejected_orders': len([o for o in orders if o.status == OrderStatus.REJECTED]),
                'total_executions': len(self.executions),
                'avg_slippage': sum(e.slippage for e in self.executions) / len(self.executions) if self.executions else 0.0,
                'avg_spread': sum(e.spread for e in self.executions) / len(self.executions) if self.executions else 0.0,
            }


if __name__ == "__main__":
    # Example usage (requires market data engine)
    print("=" * 70)
    print("Order Simulator Module Test")
    print("=" * 70)
    print("\nNote: Full testing requires Market Data Engine integration")
    print("See examples/order_simulator_example.py for complete examples")
    print("=" * 70)
