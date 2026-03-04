"""
IndiPaperTrade - Main Entry Point

A professional-grade local paper trading platform for Indian equity and derivatives markets.

Usage:
    python main.py              # Start the system
    python main.py --test       # Test market data connection
    python main.py --config     # Show configuration
"""

import sys
import logging
import argparse
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config import Settings, INSTRUMENT_TOKENS
from data_engine import MarketDataEngine, PriceData
from utils import setup_logging, get_logger, ensure_data_directories


# Configure logging
logger = get_logger(__name__)


def test_market_data_connection():
    """
    Test the Market Data Engine connection.
    
    This function attempts to:
    1. Authenticate with Angel One SmartAPI
    2. Start the engine
    3. Subscribe to a few instruments
    4. Fetch live prices
    5. Display results
    """
    print("\n" + "=" * 60)
    print("Testing Market Data Engine Connection")
    print("=" * 60 + "\n")
    
    # Create engine
    engine = MarketDataEngine()
    logger.info("Market Data Engine created")
    
    # Initialize
    print("Authenticating with Angel One SmartAPI...")
    if not engine.initialize():
        logger.error("Failed to authenticate with SmartAPI")
        print("❌ Authentication failed")
        print("\nMake sure you have set the following environment variables:")
        print("  - SMARTAPI_CLIENT_ID")
        print("  - SMARTAPI_API_KEY")
        print("  - SMARTAPI_USERNAME")
        print("  - SMARTAPI_PASSWORD")
        print("  - SMARTAPI_FEED_TOKEN")
        return False
    
    print("✓ Authentication successful")
    
    # Start engine
    print("\nStarting Market Data Engine...")
    engine.start()
    logger.info("Engine started")
    print("✓ Engine started")
    
    # Subscribe to instruments
    print("\nSubscribing to instruments:")
    test_symbols = ["RELIANCE", "TCS", "INFY"]
    for symbol in test_symbols:
        print(f"  - {symbol}")
    
    if not engine.subscribe(test_symbols):
        logger.warning("Some subscriptions failed")
        print("⚠ Some subscriptions failed (falling back to REST API)")
    else:
        print("✓ Subscriptions successful")
    
    # Wait for prices to arrive
    print("\nWaiting for price updates (5 seconds)...")
    time.sleep(5)
    
    # Get and display prices
    print("\nLive Market Data:")
    print("-" * 60)
    
    all_prices = engine.get_all_prices()
    
    if not all_prices:
        print("❌ No price data received")
        engine.stop()
        return False
    
    print(f"{'Symbol':<12} {'LTP':<12} {'Bid':<12} {'Ask':<12}")
    print("-" * 60)
    
    for symbol, price in all_prices.items():
        print(f"{symbol:<12} ₹{price.ltp:<11,.2f} ₹{price.bid:<11,.2f} ₹{price.ask:<11,.2f}")
    
    print("-" * 60)
    print(f"\n✓ Successfully fetched prices for {len(all_prices)} instruments\n")
    
    # Stop engine
    engine.stop()
    logger.info("Engine stopped")
    
    return True


def show_configuration():
    """Display current configuration."""
    print("\n" + "=" * 60)
    print("IndiPaperTrade Configuration")
    print("=" * 60 + "\n")
    
    print("SmartAPI Credentials:")
    print("-" * 60)
    creds = Settings.get_credentials_summary()
    for key, value in creds.items():
        print(f"  {key:<25} {value}")
    
    print("\nTrading Settings:")
    print("-" * 60)
    print(f"  {'Initial Capital':<25} ₹{Settings.INITIAL_CAPITAL:,.2f}")
    print(f"  {'Max Leverage':<25} {Settings.MAX_LEVERAGE}x")
    print(f"  {'Slippage Enabled':<25} {Settings.ENABLE_SLIPPAGE}")
    if Settings.ENABLE_SLIPPAGE:
        print(f"  {'Slippage %':<25} {Settings.SLIPPAGE_PERCENT}%")
    print(f"  {'Spread Enabled':<25} {Settings.ENABLE_SPREAD}")
    if Settings.ENABLE_SPREAD:
        print(f"  {'Spread %':<25} {Settings.DEFAULT_SPREAD_PERCENT}%")
    
    print("\nSystem Paths:")
    print("-" * 60)
    print(f"  {'Database Path':<25} {Settings.DATABASE_PATH}")
    print(f"  {'Log File':<25} {Settings.LOG_FILE}")
    print(f"  {'Log Level':<25} {Settings.LOG_LEVEL}")
    
    print("\nDashboard Settings:")
    print("-" * 60)
    print(f"  {'Host':<25} {Settings.DASHBOARD_HOST}")
    print(f"  {'Port':<25} {Settings.DASHBOARD_PORT}")
    print(f"  {'Debug Mode':<25} {Settings.DASHBOARD_DEBUG}")
    
    print("\nSupported Instruments:")
    print("-" * 60)
    print(f"  Total Instruments: {len(INSTRUMENT_TOKENS)}")
    
    # Show sample instruments
    sample_count = 0
    for symbol, info in INSTRUMENT_TOKENS.items():
        if sample_count >= 10:
            remaining = len(INSTRUMENT_TOKENS) - 10
            print(f"  ... and {remaining} more")
            break
        print(f"  {symbol:<20} ({info['exchange']:<4}) Type: {info['type']}")
        sample_count += 1
    
    print("\n" + "=" * 60 + "\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="IndiPaperTrade - Local Paper Trading Platform"
    )
    
    parser.add_argument(
        "--test",
        action="store_true",
        help="Test Market Data Engine connection"
    )
    
    parser.add_argument(
        "--config",
        action="store_true",
        help="Show current configuration"
    )
    
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set logging level"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    ensure_data_directories()
    setup_logging()
    
    logger.info("IndiPaperTrade starting")
    logger.info(f"Log level: {args.log_level}")
    
    # Show configuration
    if args.config:
        show_configuration()
        return 0
    
    # Test connection
    if args.test:
        success = test_market_data_connection()
        return 0 if success else 1
    
    # Default: Show usage
    print("\n" + "=" * 60)
    print("IndiPaperTrade - Paper Trading Platform")
    print("=" * 60)
    print("\nUsage:")
    print("  python main.py --config     Show configuration")
    print("  python main.py --test       Test market data connection")
    print("  python main.py --help       Show help message")
    print("\n" + "=" * 60 + "\n")
    
    print("Next steps:")
    print("  1. Set your Angel One SmartAPI credentials in environment variables")
    print("  2. Run: python main.py --config")
    print("  3. Run: python main.py --test")
    print("\nDocumentation:")
    print("  - See README.md for overview")
    print("  - See MARKET_DATA_ENGINE.md for detailed API documentation")
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
