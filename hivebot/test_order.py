#!/usr/bin/env python3
"""
Standalone Order Test - Direct test with database credentials and Hummingbot modules
"""

import asyncio
import os
import sqlite3
import sys
import time
from decimal import Decimal

# Add hummingbot to path
sys.path.insert(0, '/home/ubuntu/hummingbot')

from hummingbot.client.config.config_helpers import ClientConfigAdapter, load_client_config_map_from_file
from hummingbot.connector.derivative.hyperliquid_perpetual.hyperliquid_perpetual_derivative import (
    HyperliquidPerpetualDerivative
)
from hummingbot.core.data_type.common import OrderType, PositionAction, TradeType


async def test_standalone_order():
    """Test order placement using direct database credentials and Hummingbot connector."""

    print("🧪 STANDALONE ORDER TEST")
    print("=" * 60)
    print("Testing direct order placement with database credentials...")

    # Step 1: Use our spawned bot credentials directly
    main_wallet = "0x8cf39b53bd5532566bc79588a2270d53176bd0ce"
    actual_private_key = "0x36b435cda9793d2e598c331058769cb8ac8fe5f6f26056dc759cc1bae36aa5f4"  # New approved agent key
    market = "BTC-USD"

    print(f"👤 Main wallet address: {main_wallet}")
    print(f"🔐 Agent private key: {actual_private_key[:10]}...")
    print(f"📈 Market: {market}")

    # Derive agent address for info
    try:
        from eth_account import Account
        agent_account = Account.from_key(actual_private_key)
        agent_address = agent_account.address
        print(f"🤖 Agent wallet address: {agent_address}")
    except Exception as e:
        print(f"⚠️ Failed to derive agent address: {e}")

    # Step 2: Create client config (simplified)
    try:
        print(f"\n🔧 Creating client config...")
        client_config = load_client_config_map_from_file()
        print(f"✅ Client config created")

    except Exception as e:
        print(f"❌ Client config error: {e}")
        return

    # Step 3: Create Hyperliquid connector directly
    try:
        print(f"\n🔌 Creating Hyperliquid connector...")
        print(f"🔑 Using private key: {actual_private_key[:10]}...")

        # Create connector with main wallet as API key and agent private key for signing
        connector = HyperliquidPerpetualDerivative(
            client_config_map=client_config,
            hyperliquid_perpetual_api_key=main_wallet,  # Main wallet address as API key
            hyperliquid_perpetual_api_secret=actual_private_key,  # Agent private key for signing
            trading_pairs=[market],
            trading_required=True,
            domain="testnet"
        )

        print(f"✅ Connector created: {connector.__class__.__name__}")
        print(f"🔑 Connector API key: {connector.hyperliquid_perpetual_api_key[:10]}...")
        print(f"🔐 Connector secret length: {len(connector.hyperliquid_perpetual_secret_key)}")

    except Exception as e:
        print(f"❌ Connector creation error: {e}")
        import traceback
        traceback.print_exc()
        return

    # Step 4: Test order placement
    try:
        print(f"\n📤 Testing order placement...")

        # Test order size (user requested 0.001 perp BTC)
        tiny_amount = Decimal("0.001")
        test_price = Decimal("50000.0")  # Example price (limit orders may rest)

        print(f"💰 Order amount: {tiny_amount}")
        print(f"💵 Order price: ${test_price}")

        # Create order ID
        order_id = f"standalone_test_{int(time.time())}"
        print(f"🆔 Order ID: {order_id}")

        # **DIRECT BUY CALL** - This should use our overridden method
        print(f"\n🚀 Calling connector.buy()...")
        # Start network and wait a moment for rules
        await connector.start_network()
        await asyncio.sleep(5)
        try:
            await connector._update_trading_rules()
        except Exception:
            pass

        result = connector.buy(
            trading_pair=market,
            amount=tiny_amount,
            order_type=OrderType.LIMIT,
            price=test_price,
            position_action=PositionAction.OPEN
        )

        print(f"📤 Buy result: {result}")

        # Wait a moment for async processing
        await asyncio.sleep(2)

        # Check if order was processed
        if hasattr(connector, '_order_tracker'):
            orders = connector._order_tracker.all_orders
            print(f"📋 Orders in tracker: {len(orders)}")
            for order_id, order in orders.items():
                print(f"  - {order_id}: {order.current_state}")

        print(f"\n🎯 STANDALONE TEST COMPLETE")
        print(f"✅ Order placement attempted successfully")
        print(f"💡 Check Hyperliquid testnet UI to see if order appeared")

    except Exception as e:
        print(f"❌ Order placement error: {e}")
        import traceback
        traceback.print_exc()
        return


if __name__ == "__main__":
    # Run the test
    asyncio.run(test_standalone_order())

