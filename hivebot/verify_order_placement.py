#!/usr/bin/env python3

"""
Verify Order Placement - Systematic test to confirm orders appear on Hyperliquid testnet.
This script will place orders and verify they show up in the API.
"""

import asyncio
import logging
from decimal import Decimal
import time
import requests
import os
from hummingbot.client.config.config_helpers import load_client_config_map_from_file
from hummingbot.connector.exchange.hyperliquid.hyperliquid_exchange import HyperliquidExchange
from hummingbot.connector.exchange.hyperliquid import hyperliquid_constants as CONSTANTS
from hummingbot.core.data_type.common import OrderType


# Your testnet credentials - load from environment
TESTNET_PRIVATE_KEY = os.getenv('HYPERLIQUID_PRIVATE_KEY')
WALLET_ADDRESS = "0x208CbD782D8cfD050f796492A2C64f3A86d11815"

if not TESTNET_PRIVATE_KEY:
    raise ValueError("HYPERLIQUID_PRIVATE_KEY environment variable must be set")


def check_orders_via_api():
    """Check orders using the Hyperliquid API."""
    try:
        url = 'http://15.235.212.39:8081/info'
        payload = {"type": "historicalOrders", "user": WALLET_ADDRESS}
        
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            orders = response.json()
            return orders
        else:
            print(f"API request failed: {response.status_code}")
            return []
    except Exception as e:
        print(f"API check failed: {e}")
        return []


def check_open_orders_via_api():
    """Check open orders using the Hyperliquid API."""
    try:
        url = 'http://15.235.212.39:8081/info'
        payload = {"type": "openOrders", "user": WALLET_ADDRESS}
        
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            orders = response.json()
            return orders
        else:
            print(f"Open orders API request failed: {response.status_code}")
            return []
    except Exception as e:
        print(f"Open orders API check failed: {e}")
        return []


async def verify_order_placement():
    """Systematically verify order placement."""
    
    print("🔍 SYSTEMATIC ORDER PLACEMENT VERIFICATION")
    print("=" * 55)
    print(f"🔑 Wallet: {WALLET_ADDRESS}")
    print(f"🌐 Testnet: https://app.hyperliquid-testnet.xyz/historicalOrders/{WALLET_ADDRESS}")
    print("-" * 55)
    
    # Step 1: Check baseline orders
    print("📊 Step 1: Checking baseline orders...")
    baseline_orders = check_orders_via_api()
    baseline_open = check_open_orders_via_api()
    
    print(f"   Historical orders: {len(baseline_orders)}")
    print(f"   Open orders: {len(baseline_open)}")
    
    # Step 2: Create connector
    print("\n🔌 Step 2: Creating connector...")
    
    logging.basicConfig(level=logging.WARNING)  # Reduce noise
    
    client_config_map = load_client_config_map_from_file()
    
    connector = HyperliquidExchange(
        client_config_map=client_config_map,
        hyperliquid_api_key="",
        hyperliquid_api_secret=TESTNET_PRIVATE_KEY,
        trading_pairs=["PURR-USDC"],
        trading_required=True,
        domain=CONSTANTS.TESTNET_DOMAIN
    )
    
    print("✅ Connector created")
    
    try:
        # Step 3: Start connector
        print("\n🚀 Step 3: Starting connector (wait 60s max)...")
        await connector.start_network()
        
        # Wait with progress indicator
        for i in range(12):  # 60 seconds max
            await asyncio.sleep(5)
            ready = connector.ready
            print(f"   Wait {(i+1)*5}s: Ready={ready}")
            
            if ready:
                break
        
        # Step 4: Get market data
        print(f"\n📊 Step 4: Getting market data...")
        await asyncio.sleep(5)  # Let order book populate
        
        trading_pair = "PURR-USDC"
        if trading_pair in connector.order_books:
            order_book = connector.order_books[trading_pair]
            best_bid = order_book.get_price(is_buy=True)
            best_ask = order_book.get_price(is_buy=False)
            
            if best_bid and best_ask:
                # Ensure Decimal types
                best_bid = Decimal(str(best_bid))
                best_ask = Decimal(str(best_ask))
                mid_price = (best_bid + best_ask) / Decimal("2")
                
                print(f"✅ Market data available:")
                print(f"   Best Bid: ${best_bid:.6f}")
                print(f"   Best Ask: ${best_ask:.6f}")
                print(f"   Mid Price: ${mid_price:.6f}")
                
                # Step 5: Place test orders
                print(f"\n💰 Step 5: Placing test orders...")
                
                # Very conservative prices to avoid immediate fills
                safe_buy_price = mid_price * Decimal("0.85")  # 15% below
                safe_sell_price = mid_price * Decimal("1.15")  # 15% above
                tiny_amount = Decimal("0.001")  # Very small
                
                print(f"   Buy: {tiny_amount} @ ${safe_buy_price:.6f} (15% below)")
                print(f"   Sell: {tiny_amount} @ ${safe_sell_price:.6f} (15% above)")
                
                order_ids = []
                
                # Place buy order (sync method)
                try:
                    buy_id = connector.buy(
                        trading_pair=trading_pair,
                        amount=tiny_amount,
                        order_type=OrderType.LIMIT,
                        price=safe_buy_price
                    )
                    if buy_id:
                        print(f"🟢 BUY order placed: {buy_id}")
                        order_ids.append(buy_id)
                    else:
                        print(f"🔴 BUY order failed - no ID")
                except Exception as e:
                    print(f"🔴 BUY order error: {e}")
                
                await asyncio.sleep(2)
                
                # Place sell order (sync method)
                try:
                    sell_id = connector.sell(
                        trading_pair=trading_pair,
                        amount=tiny_amount,
                        order_type=OrderType.LIMIT,
                        price=safe_sell_price
                    )
                    if sell_id:
                        print(f"🟢 SELL order placed: {sell_id}")
                        order_ids.append(sell_id)
                    else:
                        print(f"🔴 SELL order failed - no ID")
                except Exception as e:
                    print(f"🔴 SELL order error: {e}")
                
                # Step 6: Wait and verify
                print(f"\n⏱️  Step 6: Waiting 10 seconds for orders to propagate...")
                await asyncio.sleep(10)
                
                # Check API again
                print(f"\n🔍 Step 7: Checking if orders appear in API...")
                new_orders = check_orders_via_api()
                new_open = check_open_orders_via_api()
                
                print(f"   Historical orders: {len(baseline_orders)} → {len(new_orders)}")
                print(f"   Open orders: {len(baseline_open)} → {len(new_open)}")
                
                # Look for PURR orders specifically
                purr_orders = [o for o in new_orders if o.get("order", {}).get("coin") == "PURR"]
                print(f"   PURR orders found: {len(purr_orders)}")
                
                if len(purr_orders) > 0:
                    print(f"✅ SUCCESS: PURR orders found in API!")
                    for order in purr_orders[-2:]:  # Show last 2
                        order_data = order.get("order", {})
                        print(f"      {order_data.get('side')} {order_data.get('sz')} @ ${order_data.get('limitPx')}")
                else:
                    print(f"❌ No PURR orders found in API")
                
                # Final verdict
                print(f"\n🎯 VERIFICATION RESULTS:")
                if len(order_ids) > 0:
                    print(f"✅ Order placement: SUCCESS ({len(order_ids)} orders got IDs)")
                else:
                    print(f"❌ Order placement: FAILED (no order IDs)")
                
                if len(purr_orders) > 0:
                    print(f"✅ API visibility: SUCCESS (orders appear in API)")
                else:
                    print(f"❌ API visibility: FAILED (orders not in API)")
                
            else:
                print("❌ No market data available")
        else:
            print("❌ Order book not available")
    
    finally:
        # Cleanup
        try:
            await connector.stop_network()
            print(f"\n🧹 Connector stopped")
        except:
            pass


if __name__ == "__main__":
    asyncio.run(verify_order_placement())