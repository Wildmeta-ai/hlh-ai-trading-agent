#!/usr/bin/env python3

"""
Test script to verify the position tracker fix
"""

import asyncio
import os
import sys
import logging

# Add the hummingbot directory to the path so we can import modules
sys.path.append('/home/ubuntu/hummingbot')

from hive_position_tracker import HivePositionTracker

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def test_position_tracker_fix():
    """Test the fixed position tracker"""

    # Check if HIVE_USER_ADDRESS is set
    user_address = os.getenv("HIVE_USER_ADDRESS", "")
    if not user_address:
        print("❌ HIVE_USER_ADDRESS environment variable not set!")
        return

    print(f"🧪 Testing fixed position tracker for wallet: {user_address}")
    print("-" * 60)

    # Create a mock connector object with the necessary attributes
    class MockConnector:
        def __init__(self, wallet_address):
            self.hyperliquid_perpetual_api_key = wallet_address
            self._trading_required = True
            self.name = "hyperliquid_perpetual_testnet"

    # Create the position tracker
    tracker = HivePositionTracker()

    # Create mock connector
    connector = MockConnector(user_address)

    print("🔍 Testing direct position fetch from Hyperliquid API...")

    try:
        # Test the direct API method
        positions = await tracker.get_hyperliquid_positions_direct(connector)

        if positions:
            print(f"✅ SUCCESS! Found {len(positions)} positions:")
            for i, pos in enumerate(positions, 1):
                print(f"   {i}. {pos['trading_pair']} {pos['side']} {pos['exchange_size']} @ ${pos['entry_price']}")
                print(f"      PnL: ${pos['unrealized_pnl']:.2f} | Strategy: {pos['strategy_name']}")
        else:
            print("⚠️ No positions found (this could be normal if no open positions)")

    except Exception as e:
        print(f"❌ Error testing position tracker: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Set the environment variable for testing
    os.environ['HIVE_USER_ADDRESS'] = '0x208cbd782d8cfd050f796492a2c64f3a86d11815'
    asyncio.run(test_position_tracker_fix())