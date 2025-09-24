#!/usr/bin/env python3

"""
Test script to debug position fetching with HIVE_USER_ADDRESS
"""

import asyncio
import aiohttp
import json
import os

async def test_position_fetch():
    """Test position fetching using HIVE_USER_ADDRESS"""

    # Get wallet address from environment (same as position tracker)
    user_address = os.getenv("HIVE_USER_ADDRESS", "")

    if not user_address:
        print("❌ HIVE_USER_ADDRESS environment variable not set!")
        print("   Please set it with: export HIVE_USER_ADDRESS=your_wallet_address")
        return

    print(f"🧪 Testing position fetch for wallet: {user_address}")
    print(f"📏 Address length: {len(user_address)} characters")
    print(f"🔤 Address format: {'✓ starts with 0x' if user_address.startswith('0x') else '❌ missing 0x prefix'}")
    print("-" * 60)

    # Hyperliquid testnet API endpoint
    api_url = "http://15.235.212.39:8081/info"

    # Test different API endpoints that might return position data
    test_requests = [
        {
            "name": "userState (same as position tracker)",
            "payload": {
                "type": "userState",
                "user": user_address
            }
        },
        {
            "name": "clearinghouseState",
            "payload": {
                "type": "clearinghouseState",
                "user": user_address
            }
        },
        {
            "name": "userState with lowercase address",
            "payload": {
                "type": "userState",
                "user": user_address.lower()
            }
        }
    ]

    for i, test in enumerate(test_requests, 1):
        print(f"\n📤 Test {i}: {test['name']}")
        print(f"📄 Payload: {json.dumps(test['payload'], indent=2)}")
        print("-" * 40)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, json=test['payload'], timeout=aiohttp.ClientTimeout(total=10)) as response:
                    print(f"📊 HTTP Status: {response.status}")

                    if response.status == 200:
                        data = await response.json()
                        print(f"✅ Success! Response size: {len(str(data))} chars")

                        # Check for position data
                        if isinstance(data, dict):
                            # Look for position-related fields
                            position_fields = ['assetPositions', 'positions', 'marginSummary', 'crossMarginSummary']
                            found_fields = [field for field in position_fields if field in data]

                            if found_fields:
                                print(f"📊 Found position fields: {found_fields}")

                                # Show asset positions if they exist
                                if 'assetPositions' in data:
                                    positions = data['assetPositions']
                                    print(f"🎯 Asset positions: {len(positions)} items")
                                    for pos in positions:
                                        if pos.get('position', {}).get('szi', '0') != '0':
                                            asset = pos.get('asset', 'Unknown')
                                            size = pos.get('position', {}).get('szi', '0')
                                            entry_px = pos.get('position', {}).get('entryPx', '0')
                                            pnl = pos.get('position', {}).get('unrealizedPnl', '0')
                                            print(f"   💰 {asset}: size={size}, entry=${entry_px}, pnl=${pnl}")

                                # Show margin summary if available
                                if 'marginSummary' in data:
                                    margin = data['marginSummary']
                                    account_value = margin.get('accountValue', 'N/A')
                                    withdrawable = margin.get('withdrawable', 'N/A')
                                    print(f"💰 Account value: ${account_value}")
                                    print(f"💸 Withdrawable: ${withdrawable}")
                            else:
                                print(f"⚠️ No position fields found in response")
                                print(f"   Available keys: {list(data.keys())[:10]}")

                    elif response.status == 422:
                        error_text = await response.text()
                        print(f"❌ UNPROCESSABLE ENTITY (HTTP 422)")
                        print(f"   This is the same error as the position tracker!")
                        print(f"   Response: {error_text}")

                        # Try to parse error details
                        try:
                            error_data = json.loads(error_text)
                            if isinstance(error_data, dict):
                                print(f"   Error details: {error_data}")
                        except:
                            pass

                    elif response.status == 429:
                        error_text = await response.text()
                        print(f"❌ RATE LIMITED (HTTP 429)")
                        print(f"   Response: {error_text}")

                    else:
                        error_text = await response.text()
                        print(f"❌ Request failed (HTTP {response.status})")
                        print(f"   Response: {error_text}")

        except Exception as e:
            print(f"❌ Exception for test {i}: {e}")

        # Wait between requests to avoid rate limiting
        await asyncio.sleep(2)

    print(f"\n✅ Position fetch testing completed!")
    print(f"🔍 Summary:")
    print(f"   Wallet address: {user_address}")
    print(f"   If all tests return 422, the wallet might not exist on testnet")
    print(f"   If some work and others don't, it's an endpoint/format issue")

if __name__ == "__main__":
    asyncio.run(test_position_fetch())