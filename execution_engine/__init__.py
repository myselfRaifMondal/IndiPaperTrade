"""
Execution Engine Module

This module provides order simulation capabilities for paper trading.

Components:
- OrderSimulator: Main order execution simulator
- Order: Order data structure
- OrderType: Order type enumeration (MARKET, LIMIT)
- OrderSide: Order side enumeration (BUY, SELL)
- OrderStatus: Order status enumeration
- ExecutionReport: Execution report data structure

Example Usage:
    from execution_engine import OrderSimulator, OrderSide
    from data_engine import MarketDataEngine
    
    # Initialize
    data_engine = MarketDataEngine()
    simulator = OrderSimulator(data_engine)
    
    # Place market order
    order = simulator.place_market_order("RELIANCE", OrderSide.BUY, 10)
    
    # Place limit order
    order = simulator.place_limit_order("TCS", OrderSide.SELL, 5, 3500.0)
    
    # Start background processing for limit orders
    simulator.start()
"""

from execution_engine.order_types import (
    Order,
    OrderType,
    OrderSide,
    OrderStatus,
    TimeInForce,
    ExecutionReport
)

from execution_engine.order_simulator import OrderSimulator

__all__ = [
    'OrderSimulator',
    'Order',
    'OrderType',
    'OrderSide',
    'OrderStatus',
    'TimeInForce',
    'ExecutionReport',
]
