"""
Matplotlib-based charting module for candlestick charts and technical indicators.

Provides candlestick visualization with technical indicators:
- Simple Moving Average (SMA)
- Relative Strength Index (RSI)
- MACD (Moving Average Convergence Divergence)
- Bollinger Bands
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.dates import DateFormatter, AutoDateLocator
import matplotlib.patches as mpatches
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import Qt

logger = logging.getLogger(__name__)


class CandlestickChart:
    """Candlestick chart with technical indicators."""
    
    def __init__(self, figure: Figure, ax):
        """
        Initialize candlestick chart.
        
        Args:
            figure: Matplotlib figure
            ax: Matplotlib axis
        """
        self.figure = figure
        self.ax = ax
        self.figure.patch.set_facecolor('#1a1a1a')
        self.ax.set_facecolor('#111')
        
        # Set up axis styling
        self.ax.spines['top'].set_color('#333')
        self.ax.spines['bottom'].set_color('#333')
        self.ax.spines['left'].set_color('#333')
        self.ax.spines['right'].set_color('#333')
        
        self.ax.tick_params(colors='#888', labelsize=8)
        self.ax.grid(True, color='#333', alpha=0.3, linestyle='--')
    
    def plot_candlesticks(self, ohlc_data: List[Dict]):
        """
        Plot candlestick chart.
        
        Args:
            ohlc_data: List of dicts with keys: timestamp, open, high, low, close
        """
        if not ohlc_data:
            logger.warning("No OHLC data to plot")
            return
        
        try:
            # Clear previous plot
            self.ax.clear()
            self.ax.set_facecolor('#111')
            
            # Extract data
            times = []
            opens = []
            highs = []
            lows = []
            closes = []
            
            for candle in ohlc_data:
                times.append(candle.get('timestamp'))
                opens.append(candle.get('open', 0))
                highs.append(candle.get('high', 0))
                lows.append(candle.get('low', 0))
                closes.append(candle.get('close', 0))
            
            # Plot candlesticks
            width = 0.6
            for i, (t, o, h, l, c) in enumerate(zip(times, opens, highs, lows, closes)):
                color = '#10b981' if c >= o else '#ef4444'  # Green if close > open, red otherwise
                
                # High-Low line
                self.ax.plot([i, i], [l, h], color=color, linewidth=1)
                
                # Open-Close rectangle
                height = abs(c - o)
                bottom = min(o, c)
                rect = mpatches.Rectangle(
                    (i - width/2, bottom), width, height,
                    facecolor=color, edgecolor=color, linewidth=0.5
                )
                self.ax.add_patch(rect)
            
            # Set x-axis labels
            self.ax.set_xticks(range(0, len(times), max(1, len(times)//10)))
            self.ax.set_xticklabels(
                [str(times[i]) if i < len(times) else '' for i in self.ax.get_xticks()],
                rotation=45, ha='right'
            )
            
            # Set y-axis
            self.ax.set_ylabel('Price (₹)', color='#888', fontsize=9)
            self.ax.set_xlim(-1, len(times))
            self.ax.set_ylim(min(lows) * 0.99, max(highs) * 1.01)
            
            # Styling
            self.ax.grid(True, color='#333', alpha=0.3, linestyle='--')
            self.ax.tick_params(colors='#888', labelsize=8)
            
            self.figure.tight_layout()
            
            logger.info(f"Plotted {len(ohlc_data)} candlesticks")
            
        except Exception as e:
            logger.error(f"Error plotting candlesticks: {e}")
    
    def add_sma(self, ohlc_data: List[Dict], period: int = 20, color: str = '#3b82f6'):
        """
        Add Simple Moving Average (SMA) to chart.
        
        Args:
            ohlc_data: OHLC data
            period: SMA period (default 20)
            color: Line color
        """
        try:
            closes = [candle.get('close', 0) for candle in ohlc_data]
            
            # Calculate SMA
            sma = []
            for i in range(len(closes)):
                if i < period - 1:
                    sma.append(None)
                else:
                    avg = sum(closes[i-period+1:i+1]) / period
                    sma.append(avg)
            
            # Plot SMA
            x_indices = list(range(len(sma)))
            self.ax.plot(
                x_indices, sma,
                color=color, linewidth=1.5, label=f'SMA{period}', alpha=0.8
            )
            
            self.ax.legend(loc='upper left', fontsize=8, facecolor='#2a2a2a', edgecolor='#333')
            
            logger.info(f"Added SMA{period} to chart")
            
        except Exception as e:
            logger.error(f"Error adding SMA: {e}")
    
    def add_bollinger_bands(self, ohlc_data: List[Dict], period: int = 20, std_dev: float = 2.0):
        """
        Add Bollinger Bands to chart.
        
        Args:
            ohlc_data: OHLC data
            period: Period for calculation
            std_dev: Standard deviation multiplier
        """
        try:
            closes = [candle.get('close', 0) for candle in ohlc_data]
            
            # Calculate Bollinger Bands
            upper_band = []
            middle_band = []
            lower_band = []
            
            for i in range(len(closes)):
                if i < period - 1:
                    upper_band.append(None)
                    middle_band.append(None)
                    lower_band.append(None)
                else:
                    window = closes[i-period+1:i+1]
                    sma = sum(window) / period
                    std = np.std(window)
                    
                    middle_band.append(sma)
                    upper_band.append(sma + std_dev * std)
                    lower_band.append(sma - std_dev * std)
            
            # Plot bands
            x_indices = list(range(len(middle_band)))
            self.ax.plot(x_indices, middle_band, color='#f59e0b', linewidth=1, linestyle='--', alpha=0.7)
            self.ax.plot(x_indices, upper_band, color='#ef4444', linewidth=0.8, linestyle=':', alpha=0.5)
            self.ax.plot(x_indices, lower_band, color='#10b981', linewidth=0.8, linestyle=':', alpha=0.5)
            self.ax.fill_between(x_indices, lower_band, upper_band, color='#666', alpha=0.1)
            
            logger.info(f"Added Bollinger Bands (period={period}, std={std_dev})")
            
        except Exception as e:
            logger.error(f"Error adding Bollinger Bands: {e}")
    
    def add_rsi(self, ohlc_data: List[Dict], period: int = 14):
        """
        Add RSI (Relative Strength Index) as subplot.
        
        Args:
            ohlc_data: OHLC data
            period: RSI period
        """
        try:
            closes = [candle.get('close', 0) for candle in ohlc_data]
            
            # Calculate price changes
            deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
            
            # Separate gains and losses
            gains = [d if d > 0 else 0 for d in deltas]
            losses = [-d if d < 0 else 0 for d in deltas]
            
            # Calculate average gains and losses
            rsi_values = []
            for i in range(len(closes)):
                if i < period:
                    rsi_values.append(None)
                else:
                    avg_gain = sum(gains[i-period+1:i+1]) / period
                    avg_loss = sum(losses[i-period+1:i+1]) / period
                    
                    if avg_loss == 0:
                        rs = 100 if avg_gain > 0 else 0
                    else:
                        rs = 100 - (100 / (1 + avg_gain / avg_loss))
                    
                    rsi_values.append(rs)
            
            logger.info(f"Calculated RSI{period}")
            
            return rsi_values
            
        except Exception as e:
            logger.error(f"Error calculating RSI: {e}")
            return []
    
    def add_macd(self, ohlc_data: List[Dict], fast: int = 12, slow: int = 26, signal: int = 9):
        """
        Add MACD (Moving Average Convergence Divergence) as subplot.
        
        Args:
            ohlc_data: OHLC data
            fast: Fast EMA period
            slow: Slow EMA period
            signal: Signal line period
        """
        try:
            closes = [candle.get('close', 0) for candle in ohlc_data]
            
            # Calculate EMAs
            def calculate_ema(data, period):
                ema = []
                multiplier = 2 / (period + 1)
                for i, val in enumerate(data):
                    if i == 0:
                        ema.append(val)
                    else:
                        ema.append(val * multiplier + ema[i-1] * (1 - multiplier))
                return ema
            
            ema_fast = calculate_ema(closes, fast)
            ema_slow = calculate_ema(closes, slow)
            
            # Calculate MACD line
            macd_line = [ema_fast[i] - ema_slow[i] for i in range(len(closes))]
            
            # Calculate signal line
            signal_line = calculate_ema(macd_line, signal)
            
            # Calculate histogram
            histogram = [macd_line[i] - signal_line[i] for i in range(len(macd_line))]
            
            logger.info(f"Calculated MACD (fast={fast}, slow={slow}, signal={signal})")
            
            return {'macd': macd_line, 'signal': signal_line, 'histogram': histogram}
            
        except Exception as e:
            logger.error(f"Error calculating MACD: {e}")
            return {}


class MatplotlibCanvasWidget(QWidget):
    """PyQt6 widget for matplotlib charts."""
    
    def __init__(self, parent=None):
        """Initialize matplotlib canvas widget."""
        super().__init__(parent)
        
        self.figure = Figure(figsize=(8, 6), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        
        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)
        
        self.chart = CandlestickChart(self.figure, self.ax)
    
    def plot(self, ohlc_data: List[Dict], indicators: Optional[Dict] = None):
        """
        Plot candlestick chart with indicators.
        
        Args:
            ohlc_data: OHLC data
            indicators: Dict with keys like 'sma20', 'bollinger', 'rsi14', 'macd'
        """
        try:
            self.figure.clear()
            
            # Create subplots based on indicators
            subplot_count = 1  # Main candlestick chart
            
            if indicators and ('rsi14' in indicators or 'macd' in indicators):
                subplot_count = 2  # Add RSI/MACD subplot
            
            # Plot main candlesticks
            self.ax = self.figure.add_subplot(f'{subplot_count}11' if subplot_count > 1 else '111')
            self.chart.ax = self.ax
            self.chart.figure = self.figure
            
            # Re-apply styling to main axis
            self.figure.patch.set_facecolor('#1a1a1a')
            self.ax.set_facecolor('#111')
            self.ax.spines['top'].set_color('#333')
            self.ax.spines['bottom'].set_color('#333')
            self.ax.spines['left'].set_color('#333')
            self.ax.spines['right'].set_color('#333')
            
            self.chart.plot_candlesticks(ohlc_data)
            
            if indicators:
                if 'sma20' in indicators:
                    self.chart.add_sma(ohlc_data, period=20)
                if 'sma50' in indicators:
                    self.chart.add_sma(ohlc_data, period=50, color='#f59e0b')
                if 'bollinger' in indicators:
                    self.chart.add_bollinger_bands(ohlc_data)
                
                # Plot RSI if requested
                if 'rsi14' in indicators:
                    self._plot_rsi(ohlc_data, subplot_count)
                
                # Plot MACD if requested
                if 'macd' in indicators:
                    self._plot_macd(ohlc_data, subplot_count)
            
            self.canvas.draw()
            logger.info("Chart plotted successfully with indicators")
            
        except Exception as e:
            logger.error(f"Error plotting chart: {e}")
    
    def _plot_rsi(self, ohlc_data: List[Dict], subplot_count: int):
        """Plot RSI indicator as subplot."""
        try:
            rsi_values = self.chart.add_rsi(ohlc_data, period=14)
            
            # Create RSI subplot
            ax_rsi = self.figure.add_subplot(f'{subplot_count}12' if subplot_count > 1 else None)
            
            if ax_rsi:
                x_indices = list(range(len(rsi_values)))
                ax_rsi.plot(x_indices, rsi_values, color='#f59e0b', linewidth=1.5, label='RSI14')
                ax_rsi.axhline(y=70, color='#ef4444', linestyle='--', linewidth=0.8, alpha=0.5)
                ax_rsi.axhline(y=30, color='#10b981', linestyle='--', linewidth=0.8, alpha=0.5)
                ax_rsi.fill_between(x_indices, 30, 70, color='#666', alpha=0.1)
                
                ax_rsi.set_ylabel('RSI', color='#888', fontsize=8)
                ax_rsi.set_ylim(0, 100)
                ax_rsi.tick_params(colors='#888', labelsize=8)
                ax_rsi.grid(True, color='#333', alpha=0.3, linestyle='--')
                ax_rsi.legend(loc='upper left', fontsize=8, facecolor='#2a2a2a', edgecolor='#333')
                
                logger.info("Added RSI14 subplot")
        
        except Exception as e:
            logger.error(f"Error plotting RSI: {e}")
    
    def _plot_macd(self, ohlc_data: List[Dict], subplot_count: int):
        """Plot MACD indicator as subplot."""
        try:
            macd_data = self.chart.add_macd(ohlc_data, fast=12, slow=26, signal=9)
            
            if not macd_data:
                return
            
            # Create MACD subplot
            ax_macd = self.figure.add_subplot(f'{subplot_count}13' if subplot_count > 1 else None)
            
            if ax_macd:
                x_indices = list(range(len(macd_data['macd'])))
                
                # Plot MACD line and signal line
                ax_macd.plot(x_indices, macd_data['macd'], color='#3b82f6', linewidth=1.5, label='MACD')
                ax_macd.plot(x_indices, macd_data['signal'], color='#ef4444', linewidth=1, label='Signal')
                
                # Plot histogram
                colors = ['#10b981' if h > 0 else '#ef4444' for h in macd_data['histogram']]
                ax_macd.bar(x_indices, macd_data['histogram'], color=colors, alpha=0.5, width=0.8)
                
                ax_macd.axhline(y=0, color='#666', linestyle='-', linewidth=0.5)
                ax_macd.set_ylabel('MACD', color='#888', fontsize=8)
                ax_macd.tick_params(colors='#888', labelsize=8)
                ax_macd.grid(True, color='#333', alpha=0.3, linestyle='--')
                ax_macd.legend(loc='upper left', fontsize=8, facecolor='#2a2a2a', edgecolor='#333')
                
                logger.info("Added MACD subplot")
        
        except Exception as e:
            logger.error(f"Error plotting MACD: {e}")
