#!/bin/bash

# Quick launcher for Trading Terminal with real-time streaming

echo "🚀 Starting IndiPaperTrade Trading Terminal..."
echo "   Real-time WebSocket streaming enabled"
echo ""

cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Launch terminal
python run_terminal.py

echo ""
echo "Terminal closed. Thanks for trading!"
