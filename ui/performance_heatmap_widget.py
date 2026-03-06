"""
Performance heatmap visualization - showing daily/monthly/hourly trading performance.

Provides heatmap visualizations for:
- Daily returns by day of month
- Monthly returns 
- Hourly trading performance
- Win rate by time of day
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.colors import LinearSegmentedColormap
from PyQt6.QtWidgets import QWidget, QVBoxLayout

logger = logging.getLogger(__name__)


class PerformanceHeatmapVisualizer:
    """Visualize trading performance as heatmaps."""
    
    @staticmethod
    def generate_daily_heatmap_data(trades: List[Dict], date_key: str = 'timestamp', 
                                   pnl_key: str = 'pnl') -> Dict:
        """
        Generate heatmap data for daily performance.
        
        Args:
            trades: List of trades
            date_key: Key containing trade date
            pnl_key: Key containing P&L
        
        Returns:
            Dict with day of week and hour statistics
        """
        try:
            data = {}  # {day_of_week: {hour: [pnls]}}
            
            for trade in trades:
                trade_date = trade.get(date_key)
                
                if isinstance(trade_date, str):
                    trade_date = datetime.fromisoformat(trade_date)
                
                if not trade_date:
                    continue
                
                day_of_week = trade_date.strftime("%a")  # Mon, Tue, etc.
                hour = trade_date.hour
                pnl = float(trade.get(pnl_key, 0))
                
                if day_of_week not in data:
                    data[day_of_week] = {}
                if hour not in data[day_of_week]:
                    data[day_of_week][hour] = []
                
                data[day_of_week][hour].append(pnl)
            
            logger.info(f"Generated daily heatmap data for {len(trades)} trades")
            return data
        
        except Exception as e:
            logger.error(f"Error generating daily heatmap data: {e}")
            return {}
    
    @staticmethod
    def generate_monthly_heatmap_data(trades: List[Dict], date_key: str = 'timestamp',
                                     pnl_key: str = 'pnl') -> Dict:
        """
        Generate heatmap data for monthly performance.
        
        Args:
            trades: List of trades
            date_key: Key containing trade date
            pnl_key: Key containing P&L
        
        Returns:
            Dict with year-month and day statistics
        """
        try:
            data = {}  # {year_month: {day: [pnls]}}
            
            for trade in trades:
                trade_date = trade.get(date_key)
                
                if isinstance(trade_date, str):
                    trade_date = datetime.fromisoformat(trade_date)
                
                if not trade_date:
                    continue
                
                year_month = trade_date.strftime("%Y-%m")
                day = trade_date.day
                pnl = float(trade.get(pnl_key, 0))
                
                if year_month not in data:
                    data[year_month] = {}
                if day not in data[year_month]:
                    data[year_month][day] = []
                
                data[year_month][day].append(pnl)
            
            logger.info(f"Generated monthly heatmap data for {len(trades)} trades")
            return data
        
        except Exception as e:
            logger.error(f"Error generating monthly heatmap data: {e}")
            return {}
    
    @staticmethod
    def plot_win_rate_heatmap(trades: List[Dict], figure: Figure = None, 
                             ax = None, date_key: str = 'timestamp',
                             pnl_key: str = 'pnl') -> tuple:
        """
        Plot win rate heatmap by day and hour.
        
        Args:
            trades: List of trades
            figure: Matplotlib figure
            ax: Matplotlib axis
            date_key: Key containing trade date
            pnl_key: Key containing P&L
        
        Returns:
            Tuple of (figure, axis)
        """
        try:
            if figure is None:
                figure = plt.Figure(figsize=(12, 4), dpi=100)
                figure.patch.set_facecolor('#1a1a1a')
            
            if ax is None:
                ax = figure.add_subplot(111)
                ax.set_facecolor('#111')
            
            data = PerformanceHeatmapVisualizer.generate_daily_heatmap_data(
                trades, date_key, pnl_key
            )
            
            if not data:
                ax.text(0.5, 0.5, 'No trade data', ha='center', va='center',
                       color='#888', transform=ax.transAxes)
                return figure, ax
            
            # Create matrix: days x hours
            days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            hours = list(range(24))
            
            matrix = np.zeros((len(days), len(hours)))
            
            for day_idx, day in enumerate(days):
                if day not in data:
                    continue
                for hour_idx, hour in enumerate(hours):
                    if hour in data[day]:
                        pnls = data[day][hour]
                        wins = sum(1 for p in pnls if p > 0)
                        total = len(pnls)
                        win_rate = (wins / total * 100) if total > 0 else 0
                        matrix[day_idx, hour_idx] = win_rate
            
            # Create custom colormap (red to green)
            colors = ['#ef4444', '#f59e0b', '#10b981']
            n_bins = 100
            cmap = LinearSegmentedColormap.from_list('custom', colors, N=n_bins)
            
            # Plot heatmap
            im = ax.imshow(matrix, cmap=cmap, aspect='auto', vmin=0, vmax=100)
            
            # Labels
            ax.set_xticks(range(len(hours)))
            ax.set_xticklabels([f'{h:02d}' for h in hours], fontsize=8)
            ax.set_yticks(range(len(days)))
            ax.set_yticklabels(days, fontsize=9)
            
            ax.set_xlabel('Hour of Day', color='#888', fontsize=10)
            ax.set_ylabel('Day of Week', color='#888', fontsize=10)
            ax.set_title('Win Rate Heatmap (%)', color='#fff', fontsize=12, fontweight='bold')
            
            # Colorbar
            cbar = figure.colorbar(im, ax=ax, label='Win Rate (%)')
            cbar.ax.tick_params(colors='#888', labelsize=8)
            cbar.set_label('Win Rate (%)', color='#888', fontsize=9)
            
            figure.tight_layout()
            logger.info("Plotted win rate heatmap")
            
            return figure, ax
        
        except Exception as e:
            logger.error(f"Error plotting win rate heatmap: {e}")
            return figure, ax


class PerformanceHeatmapWidget(QWidget):
    """PyQt6 widget for performance heatmap visualization."""
    
    def __init__(self, parent=None):
        """Initialize performance heatmap widget."""
        super().__init__(parent)
        
        self.figure = Figure(figsize=(12, 4), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        
        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)
    
    def plot_win_rate_heatmap(self, trades: List[Dict], date_key: str = 'timestamp',
                             pnl_key: str = 'pnl'):
        """Plot win rate heatmap."""
        try:
            self.figure.clear()
            self.ax = self.figure.add_subplot(111)
            
            PerformanceHeatmapVisualizer.plot_win_rate_heatmap(
                trades, self.figure, self.ax, date_key, pnl_key
            )
            self.canvas.draw()
        
        except Exception as e:
            logger.error(f"Error plotting heatmap in widget: {e}")
