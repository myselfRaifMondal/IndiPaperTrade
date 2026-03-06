"""
Visualization tools for trading analytics - equity curves, drawdown analysis, and performance charts.

Provides functionality to:
- Plot equity curves (cumulative P&L)
- Visualize drawdown analysis
- Generate performance heatmaps
- Monthly/daily performance statistics
"""

import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt6.QtWidgets import QWidget, QVBoxLayout

logger = logging.getLogger(__name__)


class EquityCurveVisualizer:
    """Visualize equity curves and drawdown analysis."""
    
    @staticmethod
    def calculate_equity_curve(trades: List[Dict], pnl_key: str = 'pnl') -> Tuple[List[float], List[float]]:
        """
        Calculate equity curve from trades.
        
        Args:
            trades: List of closed trades
            pnl_key: Key containing P&L values
        
        Returns:
            Tuple of (timestamps, cumulative_pnls)
        """
        try:
            if not trades:
                return [], []
            
            pnls = [float(t.get(pnl_key, 0)) for t in trades]
            cumulative = []
            running_total = 0
            
            for pnl in pnls:
                running_total += pnl
                cumulative.append(running_total)
            
            # Create timestamps (assume trades are sequential)
            timestamps = list(range(len(cumulative)))
            
            logger.info(f"Calculated equity curve with {len(cumulative)} points")
            return timestamps, cumulative
        
        except Exception as e:
            logger.error(f"Error calculating equity curve: {e}")
            return [], []
    
    @staticmethod
    def calculate_drawdown_curve(equity_curve: List[float]) -> Tuple[List[float], List[float]]:
        """
        Calculate drawdown from equity curve.
        
        Args:
            equity_curve: Cumulative P&L values
        
        Returns:
            Tuple of (timestamps, drawdown_percentages)
        """
        try:
            if not equity_curve:
                return [], []
            
            drawdowns = []
            peak = equity_curve[0]
            
            for value in equity_curve:
                if value > peak:
                    peak = value
                
                dd = (peak - value) / abs(peak) if peak != 0 else 0
                drawdowns.append(dd * 100)  # Convert to percentage
            
            timestamps = list(range(len(drawdowns)))
            
            logger.info(f"Calculated drawdown curve with {len(drawdowns)} points")
            return timestamps, drawdowns
        
        except Exception as e:
            logger.error(f"Error calculating drawdown: {e}")
            return [], []
    
    @staticmethod
    def plot_equity_curve(trades: List[Dict], figure: Figure = None, 
                         ax = None, pnl_key: str = 'pnl') -> Tuple[Figure, any]:
        """
        Plot equity curve on matplotlib figure.
        
        Args:
            trades: List of trades
            figure: Matplotlib figure (creates new if None)
            ax: Matplotlib axis (creates new if None)
            pnl_key: Key containing P&L
        
        Returns:
            Tuple of (figure, axis)
        """
        try:
            if figure is None:
                figure = plt.Figure(figsize=(10, 4), dpi=100)
                figure.patch.set_facecolor('#1a1a1a')
            
            if ax is None:
                ax = figure.add_subplot(111)
                ax.set_facecolor('#111')
            
            timestamps, equity = EquityCurveVisualizer.calculate_equity_curve(trades, pnl_key)
            
            if not equity:
                ax.text(0.5, 0.5, 'No trade data', ha='center', va='center', 
                       color='#888', transform=ax.transAxes)
                return figure, ax
            
            # Plot equity curve
            ax.plot(timestamps, equity, color='#10b981', linewidth=2, label='Equity Curve')
            ax.fill_between(timestamps, equity, alpha=0.2, color='#10b981')
            
            # Style
            ax.set_xlabel('Trade Number', color='#888', fontsize=10)
            ax.set_ylabel('Cumulative P&L (₹)', color='#888', fontsize=10)
            ax.set_title('Equity Curve', color='#fff', fontsize=12, fontweight='bold')
            ax.tick_params(colors='#888', labelsize=9)
            ax.grid(True, color='#333', alpha=0.3, linestyle='--')
            ax.legend(loc='upper left', fontsize=9, facecolor='#2a2a2a', edgecolor='#333')
            
            # Style spines
            ax.spines['top'].set_color('#333')
            ax.spines['bottom'].set_color('#333')
            ax.spines['left'].set_color('#333')
            ax.spines['right'].set_color('#333')
            
            figure.tight_layout()
            logger.info(f"Plotted equity curve for {len(trades)} trades")
            
            return figure, ax
        
        except Exception as e:
            logger.error(f"Error plotting equity curve: {e}")
            return figure, ax
    
    @staticmethod
    def plot_drawdown_curve(trades: List[Dict], figure: Figure = None, 
                           ax = None, pnl_key: str = 'pnl') -> Tuple[Figure, any]:
        """
        Plot drawdown curve on matplotlib figure.
        
        Args:
            trades: List of trades
            figure: Matplotlib figure (creates new if None)
            ax: Matplotlib axis (creates new if None)
            pnl_key: Key containing P&L
        
        Returns:
            Tuple of (figure, axis)
        """
        try:
            if figure is None:
                figure = plt.Figure(figsize=(10, 4), dpi=100)
                figure.patch.set_facecolor('#1a1a1a')
            
            if ax is None:
                ax = figure.add_subplot(111)
                ax.set_facecolor('#111')
            
            timestamps, equity = EquityCurveVisualizer.calculate_equity_curve(trades, pnl_key)
            timestamps, drawdowns = EquityCurveVisualizer.calculate_drawdown_curve(equity)
            
            if not drawdowns:
                ax.text(0.5, 0.5, 'No drawdown data', ha='center', va='center',
                       color='#888', transform=ax.transAxes)
                return figure, ax
            
            # Plot drawdown
            colors = ['#ef4444' if dd > 0 else '#10b981' for dd in drawdowns]
            ax.fill_between(timestamps, drawdowns, alpha=0.5, color='#ef4444', label='Drawdown')
            ax.plot(timestamps, drawdowns, color='#ef4444', linewidth=2)
            
            # Max drawdown line
            max_dd = max(drawdowns) if drawdowns else 0
            ax.axhline(y=max_dd, color='#f59e0b', linestyle='--', linewidth=1, alpha=0.7, label=f'Max DD: {max_dd:.1f}%')
            
            # Style
            ax.set_xlabel('Trade Number', color='#888', fontsize=10)
            ax.set_ylabel('Drawdown (%)', color='#888', fontsize=10)
            ax.set_title('Drawdown Analysis', color='#fff', fontsize=12, fontweight='bold')
            ax.set_ylim(bottom=0)
            ax.tick_params(colors='#888', labelsize=9)
            ax.grid(True, color='#333', alpha=0.3, linestyle='--')
            ax.legend(loc='upper left', fontsize=9, facecolor='#2a2a2a', edgecolor='#333')
            
            # Style spines
            ax.spines['top'].set_color('#333')
            ax.spines['bottom'].set_color('#333')
            ax.spines['left'].set_color('#333')
            ax.spines['right'].set_color('#333')
            
            figure.tight_layout()
            logger.info(f"Plotted drawdown curve for {len(trades)} trades")
            
            return figure, ax
        
        except Exception as e:
            logger.error(f"Error plotting drawdown curve: {e}")
            return figure, ax


class EquityCurveWidget(QWidget):
    """PyQt6 widget for equity curve visualization."""
    
    def __init__(self, parent=None):
        """Initialize equity curve widget."""
        super().__init__(parent)
        
        self.figure = Figure(figsize=(10, 4), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        
        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)
    
    def plot_equity_curve(self, trades: List[Dict], pnl_key: str = 'pnl'):
        """Plot equity curve."""
        try:
            self.figure.clear()
            self.ax = self.figure.add_subplot(111)
            
            EquityCurveVisualizer.plot_equity_curve(trades, self.figure, self.ax, pnl_key)
            self.canvas.draw()
        
        except Exception as e:
            logger.error(f"Error plotting equity curve in widget: {e}")
    
    def plot_drawdown_curve(self, trades: List[Dict], pnl_key: str = 'pnl'):
        """Plot drawdown curve."""
        try:
            self.figure.clear()
            self.ax = self.figure.add_subplot(111)
            
            EquityCurveVisualizer.plot_drawdown_curve(trades, self.figure, self.ax, pnl_key)
            self.canvas.draw()
        
        except Exception as e:
            logger.error(f"Error plotting drawdown curve in widget: {e}")
