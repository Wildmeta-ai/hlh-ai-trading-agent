#!/usr/bin/env python3

"""
Test if agent wallet can place orders on Hyperliquid testnet
"""

import asyncio
import logging
import os
from decimal import Decimal
import time
import requests
from hummingbot.client.config.config_helpers import load_client_config_map_from_file
from hummingbot.connector.derivative.hyperliquid_perpetual.hyperliquid_perpetual_derivative import HyperliquidPerpetualDerivative
from hummingbot.connector.derivative.hyperliquid_perpetual import hyperliquid_perpetual_constants as CONSTANTS
from hummingbot.core.data_type.common import OrderType, PositionAction
from eth_account import Account

# Get agent credentials from environment or use provided values
AGENT_PRIVATE_KEY = os.getenv("HIVE_AGENT_PRIVATE_KEY", "0xa130dd7bd28c71a4c97ef4d1cc79908a8a09e76e0c4673b8019dd7f35a1914ee")
MAIN_WALLET = os.getenv("HIVE_USER_ADDRESS", "0x8cf39b53bd5532566bc79588a2270d53176bd0ce")

# Derive agent wallet address
agent_account = Account.from_key(AGENT_PRIVATE_KEY)
AGENT_WALLET = agent_account.address

print(f"👤 Main wallet: {MAIN_WALLET}")
print(f"🤖 Agent wallet: {AGENT_WALLET}")
print()

def check_wallet_balance(wallet_address):
    """Check wallet balance via API."""
    try:
        url = 'http://15.235.212.39:8081/info'
        payload = {"type": "clearinghouseState", "user": wallet_address}

        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            account_value = data.get('marginSummary', {}).get('accountValue', 'N/A')
            withdrawable = data.get('withdrawable', 'N/A')
            return account_value, withdrawable
        else:
            return None, None
    except Exception as e:
        print(f"Balance check failed: {e}")
        return None, None

# Check both wallet balances
print("Checking wallet balances...")
main_balance, main_withdrawable = check_wallet_balance(MAIN_WALLET)
agent_balance, agent_withdrawable = check_wallet_balance(AGENT_WALLET)

print(f"\n📊 Main wallet balance:")
if main_balance:
    print(f"   💰 Account value: ${main_balance}")
    print(f"   🔓 Withdrawable: ${main_withdrawable}")
else:
    print(f"   ❌ Could not fetch balance (might not be activated)")

print(f"\n📊 Agent wallet balance:")
if agent_balance:
    print(f"   💰 Account value: ${agent_balance}")
    print(f"   🔓 Withdrawable: ${agent_withdrawable}")
else:
    print(f"   ❌ Could not fetch balance (might not be activated)")

async def test_order_placement():
    """Test placing an order with agent wallet."""

    # Configure logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    print("\n🧪 Testing order placement with agent wallet...")
    print("=" * 50)

    try:
        # Load client config
        client_config = load_client_config_map_from_file()

        # Test 1: Agent trades on its own behalf
        print("\n1️⃣ Test: Agent wallet trading on its own behalf")
        print(f"   API Key (wallet): {AGENT_WALLET}")
        print(f"   Private Key: {AGENT_PRIVATE_KEY[:10]}...")

        connector_agent = HyperliquidPerpetualDerivative(
            client_config_map=client_config,
            hyperliquid_perpetual_api_key=AGENT_WALLET,  # Agent wallet as API key
            hyperliquid_perpetual_api_secret=AGENT_PRIVATE_KEY,  # Agent private key
            trading_pairs=["BTC-USD"],
            trading_required=True,
            domain=CONSTANTS.TESTNET_DOMAIN
        )

        await connector_agent.start_network()
        await asyncio.sleep(5)

        # Try to place a very small, low-price order that won't fill
        try:
            order_id = await connector_agent.place_order(
                trading_pair="BTC-USD",
                amount=Decimal("0.001"),  # Minimum size
                order_type=OrderType.LIMIT,
                side="buy",
                price=Decimal("50000"),  # Low price to avoid execution
                position_action=PositionAction.OPEN
            )
            print(f"   ✅ Order placed successfully! Order ID: {order_id}")

            # Cancel the order
            await asyncio.sleep(2)
            await connector_agent.cancel_order(order_id)
            print(f"   🗑️ Order cancelled")

        except Exception as e:
            print(f"   ❌ Failed to place order: {e}")

        await connector_agent.stop_network()

        # Test 2: Try with main wallet as API key (delegated trading)
        print("\n2️⃣ Test: Agent trading on behalf of main wallet (delegated)")
        print(f"   API Key (wallet): {MAIN_WALLET}")
        print(f"   Private Key: {AGENT_PRIVATE_KEY[:10]}... (agent's)")

        connector_delegated = HyperliquidPerpetualDerivative(
            client_config_map=client_config,
            hyperliquid_perpetual_api_key=MAIN_WALLET,  # Main wallet as API key
            hyperliquid_perpetual_api_secret=AGENT_PRIVATE_KEY,  # Agent private key for signing
            trading_pairs=["BTC-USD"],
            trading_required=True,
            domain=CONSTANTS.TESTNET_DOMAIN
        )

        await connector_delegated.start_network()
        await asyncio.sleep(5)

        # Try to place order
        try:
            order_id = await connector_delegated.place_order(
                trading_pair="BTC-USD",
                amount=Decimal("0.001"),
                order_type=OrderType.LIMIT,
                side="buy",
                price=Decimal("50000"),
                position_action=PositionAction.OPEN
            )
            print(f"   ✅ Order placed successfully! Order ID: {order_id}")

            # Cancel the order
            await asyncio.sleep(2)
            await connector_delegated.cancel_order(order_id)
            print(f"   🗑️ Order cancelled")

        except Exception as e:
            print(f"   ❌ Failed to place order: {e}")

        await connector_delegated.stop_network()

    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_order_placement())