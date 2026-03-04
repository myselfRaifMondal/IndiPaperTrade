#!/usr/bin/env python3
"""
Launch the IndiPaperTrade Trading Terminal

Usage:
    python run_terminal.py
    
Or make executable:
    chmod +x run_terminal.py
    ./run_terminal.py
"""

import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.trading_terminal import main

if __name__ == "__main__":
    main()
