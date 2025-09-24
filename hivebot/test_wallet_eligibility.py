#!/usr/bin/env python3

"""
Test script to check if agent wallet can trade on behalf of main wallet on Hyperliquid testnet
"""

import asyncio
import aiohttp
import json
import os
from eth_account import Account
from eth_account.messages import encode_defunct

async def check_wallet_eligibility():
    # Get credentials from environment
    main_wallet = os.getenv("HIVE_USER_ADDRESS", "")
    agent_private_key = os.getenv("HIVE_AGENT_PRIVATE_KEY", "")

    if not main_wallet or not agent_private_key:
        print("❌ Missing environment variables:")
        print(f"   HIVE_USER_ADDRESS: {'✓' if main_wallet else '❌'}")
        print(f"   HIVE_AGENT_PRIVATE_KEY: {'✓' if agent_private_key else '❌'}")
        return

    # Derive agent wallet address
    agent_account = Account.from_key(agent_private_key)
    agent_wallet = agent_account.address

    print(f"👤 Main wallet: {main_wallet}")
    print(f"🤖 Agent wallet: {agent_wallet}")
    print()

    base_url = "http://15.235.212.39:8081"

    async with aiohttp.ClientSession() as session:
        # 1. Check main wallet state
        print("1️⃣ Checking main wallet state...")
        payload = {
            "type": "userState",
            "user": main_wallet
        }

        async with session.post(f"{base_url}/info", json=payload) as response:
            if response.status == 200:
                data = await response.json()
                print(f"   ✅ Main wallet exists and accessible")
                print(f"   💰 Account value: ${data.get('marginSummary', {}).get('accountValue', 'N/A')}")
                print(f"   🔒 Withdrawable: ${data.get('marginSummary', {}).get('withdrawable', 'N/A')}")

                # Check if there are any delegated permissions
                if 'crossMarginSummary' in data:
                    print(f"   📊 Cross margin available: {data['crossMarginSummary']}")
            else:
                print(f"   ❌ Failed to fetch main wallet state: {response.status}")
                return

        # 2. Check agent wallet state
        print("\n2️⃣ Checking agent wallet state...")
        payload = {
            "type": "userState",
            "user": agent_wallet
        }

        async with session.post(f"{base_url}/info", json=payload) as response:
            if response.status == 200:
                data = await response.json()
                print(f"   ✅ Agent wallet exists and accessible")
                print(f"   💰 Account value: ${data.get('marginSummary', {}).get('accountValue', 'N/A')}")
            else:
                print(f"   ❌ Failed to fetch agent wallet state: {response.status}")

        # 3. Check if agent has delegated trading rights for main wallet
        print("\n3️⃣ Checking delegated trading permissions...")

        # Try to get delegated accounts for agent
        payload = {
            "type": "userState",
            "user": agent_wallet
        }

        async with session.post(f"{base_url}/info", json=payload) as response:
            if response.status == 200:
                data = await response.json()
                # Look for delegation info in the response
                if 'subAccounts' in data or 'delegatedAccounts' in data:
                    print(f"   🔗 Found delegation data: {data.get('subAccounts', data.get('delegatedAccounts', 'None'))}")
                else:
                    print(f"   ⚠️ No delegation fields found in agent wallet response")

        # 4. Test signature capability
        print("\n4️⃣ Testing signature capability...")

        # Create a test message and sign it with agent key
        test_message = json.dumps({
            "action": {
                "type": "order",
                "orders": [{
                    "a": 0,  # asset index for BTC
                    "b": True,  # is buy
                    "p": "60000",  # price
                    "s": "0.001",  # size
                    "r": False,  # reduce only
                    "t": {"limit": {"tif": "Gtc"}}  # time in force
                }]
            },
            "nonce": 1234567890,
            "signature": ""
        })

        # Sign the message
        message_hash = encode_defunct(text=test_message)
        signature = agent_account.sign_message(message_hash)

        print(f"   ✅ Agent can sign messages")
        print(f"   🔑 Signature: {signature.signature.hex()[:20]}...")

        # 5. Test actual order placement capability (dry run)
        print("\n5️⃣ Testing order placement eligibility...")

        # Construct proper Hyperliquid order request
        order_payload = {
            "action": {
                "type": "order",
                "orders": [{
                    "a": 0,  # BTC asset index
                    "b": True,  # buy order
                    "p": "50000",  # price (low to avoid execution)
                    "s": "0.001",  # small size
                    "r": False,  # not reduce only
                    "t": {"limit": {"tif": "Ioc"}}  # immediate or cancel (won't execute)
                }]
            },
            "nonce": 1234567890
        }

        # Try with main wallet as user
        try:
            # This would need proper signing implementation
            print(f"   📝 Would test order with main wallet: {main_wallet}")
            print(f"   🖊️ Signed by agent wallet: {agent_wallet}")
            print(f"   ⚠️ This requires full Hyperliquid API implementation to test properly")
        except Exception as e:
            print(f"   ❌ Error in test setup: {e}")

if __name__ == "__main__":
    asyncio.run(check_wallet_eligibility())