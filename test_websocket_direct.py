#!/usr/bin/env python3
"""
Direct WebSocket test to see if we get any messages at all.
"""
import os
import sys
import json
import time
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from config import Settings
from data_engine.market_data import SmartAPIDataFetcher, SmartWebSocketV2
from smartapi import generate_totp_from_secret
import pyotp

print("=" * 60)
print("Direct WebSocket Test")
print("=" * 60)

# Authenticate
print("\n1. Authenticating with SmartAPI...")
fetcher = SmartAPIDataFetcher()
if not fetcher.authenticate():
    print("❌ Authentication failed!")
    sys.exit(1)
print("✓ Authenticated")

# Get tokens
auth_token = fetcher.get_auth_token()
feed_token = fetcher.get_feed_token()
print(f"✓ Auth token: {auth_token[:30]}...")
print(f"✓ Feed token: {feed_token[:30]}...")

# Create WebSocket
print("\n2. Creating WebSocket...")
message_count = 0

def on_open(ws):
    global message_count
    message_count = 0
    print(f"\n✓ WebSocket OPENED at {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")

def on_message(ws, message):
    global message_count
    message_count += 1
    msg_preview = str(message)[:100] if len(str(message)) > 100 else str(message)
    print(f"\n📨 Message #{message_count} at {datetime.now().strftime('%H:%M:%S.%f')[:-3]}: {msg_preview}...")
    print(f"   Full length: {len(message)} bytes")
    try:
        data = json.loads(message)
        print(f"   Keys: {list(data.keys())}")
    except:
        print(f"   (Not JSON)")

def on_close(ws):
    print(f"\n⚠ WebSocket CLOSED at {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")

def on_error(ws, error):
    print(f"\n✗ ERROR: {error}")

ws = SmartWebSocketV2(
    auth_token=auth_token,
    api_key=Settings.API_KEY,
    client_code=Settings.CLIENT_ID,
    feed_token=feed_token
)

ws.on_open = on_open
ws.on_message = on_message
ws.on_close = on_close
ws.on_error = on_error

print("✓ WebSocket created with handlers")

# Connect
print("\n3. Connecting WebSocket...")
ws.connect()
print("✓ Connection initiated")

# Wait for open
print("\n4. Waiting for open callback...")
time.sleep(2)
print(f"⏱ Messages received so far: {message_count}")

# Subscribe
print("\n5. Subscribing to RELIANCE...")
token_list = [{"exchangeType": 1, "tokens": ["2885"]}]
ws.subscribe("sub_reliance", 1, token_list)
print(f"✓ Subscription sent at {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
print(f"⏱ Messages received so far: {message_count}")

# Wait for data
print("\n6. Waiting 10 seconds for price data...")
for i in range(20):
    time.sleep(0.5)
    if i % 4 == 0:
        elapsed = i * 0.5
        print(f"   ⏱ {elapsed:.1f}s elapsed, messages: {message_count}")

print(f"\n{'='*60}")
print(f"SUMMARY: Received {message_count} messages total")
print(f"{'='*60}")

try:
    print("\n7. Disconnecting...")
    ws.close()
except:
    pass

print("✓ Done")
