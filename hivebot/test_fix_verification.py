#!/usr/bin/env python3

"""
Simple test to verify the position tracker API fix works
"""

import asyncio
import aiohttp
import json
import os

async def test_clearinghouse_api():
    """Test that clearinghouseState API call works (the fix)"""

    user_address = "0x208cbd782d8cfd050f796492a2c64f3a86d11815"
    api_url = "http://15.235.212.39:8081/info"

    print(f"🧪 Testing clearinghouseState API (the fix)")
    print(f"🎯 Wallet: {user_address}")
    print("-" * 60)

    payload = {
        "type": "clearinghouseState",
        "user": user_address
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, json=payload) as response:
                print(f"📊 HTTP Status: {response.status}")

                if response.status == 200:
                    data = await response.json()
                    print(f"✅ SUCCESS! API call works perfectly")

                    # Extract position data like the position tracker does
                    if 'assetPositions' in data:
                        positions = []
                        for position_data in data['assetPositions']:
                            position = position_data.get('position', {})
                            size = position.get('szi', '0')

                            if size != '0':  # Only non-zero positions
                                entry_price = position.get('entryPx', '0')
                                unrealized_pnl = position.get('unrealizedPnl', '0')
                                asset = position_data.get('asset', 'Unknown')

                                positions.append({
                                    'asset': asset,
                                    'size': float(size),
                                    'entry_price': float(entry_price) if entry_price else 0,
                                    'unrealized_pnl': float(unrealized_pnl) if unrealized_pnl else 0,
                                    'side': 'LONG' if float(size) > 0 else 'SHORT'
                                })

                        print(f"🎯 Found {len(positions)} active positions:")
                        for i, pos in enumerate(positions, 1):
                            print(f"   {i}. {pos['asset']}: {pos['side']} {abs(pos['size'])} @ ${pos['entry_price']}")
                            print(f"      PnL: ${pos['unrealized_pnl']:.2f}")

                        # Show account summary
                        if 'marginSummary' in data:
                            margin = data['marginSummary']
                            account_value = margin.get('accountValue', 'N/A')
                            print(f"💰 Account value: ${account_value}")

                        print(f"\n✅ Position tracker fix is working!")
                        print(f"   The 422 error should be resolved now.")

                    else:
                        print(f"⚠️ No assetPositions found in response")

                else:
                    error_text = await response.text()
                    print(f"❌ API call failed: {response.status}")
                    print(f"   Response: {error_text}")

    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_clearinghouse_api())