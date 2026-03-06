"""
Export tools for trading data - CSV export, reporting, and data persistence.

Provides functionality to:
- Export trades to CSV
- Export performance metrics to CSV
- Generate trading reports
- Archive historical data
"""

import logging
import csv
import json
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path
import os

logger = logging.getLogger(__name__)


class ExportTools:
    """Tools for exporting and archiving trading data."""
    
    def __init__(self, export_dir: str = "exports"):
        """
        Initialize export tools.
        
        Args:
            export_dir: Directory for exports
        """
        self.export_dir = export_dir
        Path(self.export_dir).mkdir(parents=True, exist_ok=True)
        logger.info(f"Export tools initialized with directory: {export_dir}")
    
    def export_trades_to_csv(self, trades: List[Dict], filename: Optional[str] = None) -> str:
        """
        Export trades to CSV file.
        
        Args:
            trades: List of trade dictionaries
            filename: Output filename (default: trades_TIMESTAMP.csv)
        
        Returns:
            Path to exported file
        """
        try:
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"trades_{timestamp}.csv"
            
            file_path = os.path.join(self.export_dir, filename)
            
            if not trades:
                logger.warning("No trades to export")
                return file_path
            
            # Get all unique keys from trades
            fieldnames = set()
            for trade in trades:
                fieldnames.update(trade.keys())
            fieldnames = sorted(list(fieldnames))
            
            # Write CSV
            with open(file_path, 'w', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(trades)
            
            logger.info(f"Exported {len(trades)} trades to {file_path}")
            return file_path
        
        except Exception as e:
            logger.error(f"Error exporting trades to CSV: {e}")
            return ""
    
    def export_metrics_to_csv(self, metrics: Dict, filename: Optional[str] = None) -> str:
        """
        Export performance metrics to CSV.
        
        Args:
            metrics: Dictionary of metrics
            filename: Output filename (default: metrics_TIMESTAMP.csv)
        
        Returns:
            Path to exported file
        """
        try:
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"metrics_{timestamp}.csv"
            
            file_path = os.path.join(self.export_dir, filename)
            
            # Write CSV with metric names and values
            with open(file_path, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['Metric', 'Value'])
                for key, value in metrics.items():
                    writer.writerow([key, value])
            
            logger.info(f"Exported metrics to {file_path}")
            return file_path
        
        except Exception as e:
            logger.error(f"Error exporting metrics to CSV: {e}")
            return ""
    
    def export_to_json(self, data: Dict, filename: Optional[str] = None, pretty: bool = True) -> str:
        """
        Export data to JSON file.
        
        Args:
            data: Data dictionary
            filename: Output filename (default: export_TIMESTAMP.json)
            pretty: Whether to pretty-print JSON
        
        Returns:
            Path to exported file
        """
        try:
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"export_{timestamp}.json"
            
            file_path = os.path.join(self.export_dir, filename)
            
            with open(file_path, 'w') as jsonfile:
                json.dump(data, jsonfile, indent=2 if pretty else None, default=str)
            
            logger.info(f"Exported data to {file_path}")
            return file_path
        
        except Exception as e:
            logger.error(f"Error exporting to JSON: {e}")
            return ""
    
    def generate_trading_report(self, trades: List[Dict], metrics: Dict, 
                               filename: Optional[str] = None) -> str:
        """
        Generate comprehensive trading report.
        
        Args:
            trades: List of closed trades
            metrics: Performance metrics dict
            filename: Output filename (default: report_TIMESTAMP.json)
        
        Returns:
            Path to report file
        """
        try:
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"report_{timestamp}.json"
            
            report = {
                "generated_at": datetime.now().isoformat(),
                "summary": {
                    "total_trades": len(trades),
                    "metrics": metrics
                },
                "trades": trades
            }
            
            return self.export_to_json(report, filename)
        
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return ""
    
    def get_export_history(self) -> List[str]:
        """
        Get list of exported files.
        
        Returns:
            List of filenames in export directory
        """
        try:
            files = os.listdir(self.export_dir)
            return sorted(files, reverse=True)
        except Exception as e:
            logger.error(f"Error getting export history: {e}")
            return []
    
    def get_export_file_path(self, filename: str) -> str:
        """
        Get full path to export file.
        
        Args:
            filename: Filename in export directory
        
        Returns:
            Full file path
        """
        return os.path.join(self.export_dir, filename)


# Global export tools instance
_export_tools: Optional[ExportTools] = None


def get_export_tools(export_dir: str = "exports") -> ExportTools:
    """Get or create global export tools instance."""
    global _export_tools
    if _export_tools is None:
        _export_tools = ExportTools(export_dir)
    return _export_tools


def init_export_tools(export_dir: str = "exports") -> ExportTools:
    """Initialize export tools with custom directory."""
    global _export_tools
    _export_tools = ExportTools(export_dir)
    return _export_tools
