#!/usr/bin/env python3
"""
IndiPaperTrade - Trading Terminal UI

Launches the PyQt6-based trading terminal for the paper trading platform.

Usage:
    python run_ui.py            # Start the trading terminal
    python run_ui.py --help     # Show help message
"""

import sys
import logging
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config import Settings
from utils import setup_logging, get_logger, ensure_data_directories
from ui.trading_terminal import TradingTerminal
from PyQt6.QtWidgets import QApplication


# Configure logging
logger = get_logger(__name__)


def main():
    """Main entry point for the trading terminal UI."""
    parser = argparse.ArgumentParser(
        description="IndiPaperTrade - Trading Terminal UI"
    )
    
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set logging level"
    )
    
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run in demo mode with simulated data"
    )
    
    args = parser.parse_args()
    
    # Setup logging and directories
    ensure_data_directories()
    setup_logging()
    
    logger.info("IndiPaperTrade Trading Terminal UI starting")
    logger.info(f"Log level: {args.log_level}")
    
    # Create Qt application
    app = QApplication(sys.argv)
    
    # Create and show trading terminal
    try:
        terminal = TradingTerminal(demo_mode=args.demo)
        terminal.show()
        
        logger.info("Trading Terminal UI started successfully")
        sys.exit(app.exec())
        
    except Exception as e:
        logger.error(f"Failed to start Trading Terminal: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
