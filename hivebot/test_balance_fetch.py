#!/usr/bin/env python3

"""
Small script to test balance fetching from Hyperliquid API
"""

import asyncio
import aiohttp
import json

async def test_info_endpoint():
    """Test various /info endpoint requests that might be causing 429 errors"""

    # API endpoint (testnet)
    api_url = "http://15.235.212.39:8081/info"

    print(f"🧪 Testing /info endpoint requests")
    print(f"🌐 API URL: {api_url}")
    print("-" * 60)

    # Test different request types that might be causing rate limiting
    test_requests = [
        {"type": "metaAndAssetCtxs"},  # Exchange info
        {"type": "clearinghouseState", "user": "0x8cf39b53bd5532566bc79588a2270d53176bd0ce"},
        {"type": "meta"},  # Meta info
        {"type": "l2Book", "coin": "BTC"},  # Order book
    ]

    for i, payload in enumerate(test_requests, 1):
        print(f"\n📤 Test {i}: {json.dumps(payload, indent=2)}")
        print("-" * 40)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    print(f"📊 HTTP Status: {response.status}")

                    if response.status == 200:
                        data = await response.json()
                        print(f"✅ Success! Response size: {len(str(data))} chars")

                        # Show first few keys if it's a dict
                        if isinstance(data, dict):
                            keys = list(data.keys())[:5]
                            print(f"   Top keys: {keys}")
                        elif isinstance(data, list):
                            print(f"   Response is list with {len(data)} items")

                    elif response.status == 429:
                        error_text = await response.text()
                        print(f"❌ RATE LIMITED (HTTP 429)")
                        print(f"   This endpoint is being throttled!")
                        print(f"   Response: {error_text}")

                    else:
                        error_text = await response.text()
                        print(f"❌ Request failed (HTTP {response.status})")
                        print(f"   Response: {error_text}")

        except Exception as e:
            print(f"❌ Exception for test {i}: {e}")

        # Wait between requests to avoid rate limiting
        await asyncio.sleep(1)

    print("✅ All /info endpoint tests completed!")

if __name__ == "__main__":
    asyncio.run(test_info_endpoint())