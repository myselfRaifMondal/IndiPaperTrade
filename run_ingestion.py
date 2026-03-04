#!/usr/bin/env python3
"""
IndiPaperTrade - News Ingestion Dashboard
PyQt6-based desktop application for real-time Indian financial markets news
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from ui.news_dashboard import main

if __name__ == "__main__":
    main()
