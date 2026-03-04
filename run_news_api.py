#!/usr/bin/env python3
"""
Run the News API Server
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api import start_server

if __name__ == '__main__':
    try:
        port = int(os.getenv('NEWS_API_PORT', 5000))
        debug = os.getenv('FLASK_ENV') == 'development'
        
        print(f"Starting News API Server on port {port}...")
        start_server(port=port, debug=debug)
        
    except KeyboardInterrupt:
        print("\nShutting down server...")
        sys.exit(0)
