#!/usr/bin/env python3

"""
Verify Perpetual Order Placement - Test BTC-USD perpetual orders with 1000 USDC balance.
"""

import asyncio
import logging
from decimal import Decimal
import time
import requests
from hummingbot.client.config.config_helpers import load_client_config_map_from_file
from hummingbot.connector.derivative.hyperliquid_perpetual.hyperliquid_perpetual_derivative import HyperliquidPerpetualDerivative
from hummingbot.connector.derivative.hyperliquid_perpetual import hyperliquid_perpetual_constants as CONSTANTS
from hummingbot.core.data_type.common import OrderType, PositionAction


# Your testnet credentials - using spawned bot credentials
TESTNET_PRIVATE_KEY = "0xa130dd7bd28c71a4c97ef4d1cc79908a8a09e76e0c4673b8019dd7f35a1914ee"  # Agent private key
WALLET_ADDRESS = "0x8cf39b53bd5532566bc79588a2270d53176bd0ce"  # Main wallet address


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


def check_perp_balance():
    """Check perpetual balance via API."""
    try:
        url = 'http://15.235.212.39:8081/info'
        payload = {"type": "clearinghouseState", "user": WALLET_ADDRESS}
        
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            balance_data = response.json()
            return balance_data
        else:
            print(f"Balance API request failed: {response.status_code}")
            return {}
    except Exception as e:
        print(f"Balance API check failed: {e}")
        return {}


async def verify_perp_order_placement():
    """Systematically verify perpetual order placement with BTC-USD."""
    
    print("🔍 PERPETUAL ORDER PLACEMENT VERIFICATION")
    print("=" * 55)
    print(f"🔑 Wallet: {WALLET_ADDRESS}")
    print(f"🌐 Testnet: https://app.hyperliquid-testnet.xyz/trade/BTC")
    print("-" * 55)
    
    # Step 1: Check baseline orders and balance
    print("📊 Step 1: Checking baseline orders and balance...")
    baseline_orders = check_orders_via_api()
    baseline_open = check_open_orders_via_api()
    perp_balance = check_perp_balance()
    
    print(f"   Historical orders: {len(baseline_orders)}")
    print(f"   Open orders: {len(baseline_open)}")
    
    # Check perpetual balance
    if 'marginSummary' in perp_balance:
        usdc_balance = perp_balance['marginSummary'].get('accountValue', '0')
        print(f"   💰 Perpetual Balance: ${usdc_balance} USDC")
    else:
        print(f"   ⚠️ Could not read perpetual balance")
    
    # Step 2: Create perpetual connector
    print("\\n🔌 Step 2: Creating perpetual connector...")
    
    logging.basicConfig(level=logging.WARNING)  # Reduce noise
    
    client_config_map = load_client_config_map_from_file()
    
    connector = HyperliquidPerpetualDerivative(
        client_config_map=client_config_map,
        hyperliquid_perpetual_api_key=WALLET_ADDRESS,  # Main wallet address as API key
        hyperliquid_perpetual_api_secret=TESTNET_PRIVATE_KEY,  # Agent private key for signing
        trading_pairs=["BTC-USD"],
        trading_required=True,
        domain=CONSTANTS.TESTNET_DOMAIN
    )
    
    print("✅ Perpetual connector created")
    
    try:
        # Step 3: Start connector
        print("\\n🚀 Step 3: Starting perpetual connector (wait 60s max)...")
        await connector.start_network()
        
        # Wait with progress indicator
        for i in range(12):  # 60 seconds max
            await asyncio.sleep(5)
            ready = connector.ready
            print(f"   Wait {(i+1)*5}s: Ready={ready}")
            
            if ready:
                break
        
        # Step 4: Get BTC-USD market data
        print(f"\\n📊 Step 4: Getting BTC-USD market data...")
        await asyncio.sleep(5)  # Let order book populate
        
        trading_pair = "BTC-USD"
        if trading_pair in connector.order_books:
            order_book = connector.order_books[trading_pair]
            best_bid = order_book.get_price(is_buy=True)
            best_ask = order_book.get_price(is_buy=False)
            
            if best_bid and best_ask:
                # Ensure Decimal types
                best_bid = Decimal(str(best_bid))
                best_ask = Decimal(str(best_ask))
                mid_price = (best_bid + best_ask) / Decimal("2")
                
                print(f"✅ BTC-USD market data available:")
                print(f"   Best Bid: ${best_bid:.2f}")
                print(f"   Best Ask: ${best_ask:.2f}")
                print(f"   Mid Price: ${mid_price:.2f}")
                
                # Step 5: Place conservative test orders
                print(f"\\n💰 Step 5: Placing BTC-USD test orders...")
                
                # Very conservative prices to avoid immediate fills
                safe_buy_price = mid_price * Decimal("0.95")  # 5% below
                safe_sell_price = mid_price * Decimal("1.05")  # 5% above
                tiny_amount = Decimal("0.001")  # Very small BTC amount
                
                print(f"   Buy: {tiny_amount} BTC @ ${safe_buy_price:.2f} (5% below)")
                print(f"   Sell: {tiny_amount} BTC @ ${safe_sell_price:.2f} (5% above)")
                
                order_ids = []
                
                # Place buy order (synchronous method) with position action
                try:
                    buy_id = connector.buy(
                        trading_pair=trading_pair,
                        amount=tiny_amount,
                        order_type=OrderType.LIMIT,
                        price=safe_buy_price,
                        position_action=PositionAction.OPEN
                    )
                    if buy_id:
                        print(f"🟢 BUY order placed: {buy_id}")
                        order_ids.append(buy_id)
                    else:
                        print(f"🔴 BUY order failed - no ID")
                except Exception as e:
                    print(f"🔴 BUY order error: {e}")
                
                await asyncio.sleep(2)
                
                # Place sell order (synchronous method) with position action
                try:
                    sell_id = connector.sell(
                        trading_pair=trading_pair,
                        amount=tiny_amount,
                        order_type=OrderType.LIMIT,
                        price=safe_sell_price,
                        position_action=PositionAction.OPEN
                    )
                    if sell_id:
                        print(f"🟢 SELL order placed: {sell_id}")
                        order_ids.append(sell_id)
                    else:
                        print(f"🔴 SELL order failed - no ID")
                except Exception as e:
                    print(f"🔴 SELL order error: {e}")
                
                # Step 6: Wait and verify
                print(f"\\n⏱️  Step 6: Waiting 15 seconds for orders to propagate...")
                await asyncio.sleep(15)
                
                # Check API again
                print(f"\\n🔍 Step 7: Checking if orders appear in API...")
                new_orders = check_orders_via_api()
                new_open = check_open_orders_via_api()
                
                print(f"   Historical orders: {len(baseline_orders)} → {len(new_orders)}")
                print(f"   Open orders: {len(baseline_open)} → {len(new_open)}")
                
                # Look for BTC orders specifically
                btc_orders = [o for o in new_orders if o.get("order", {}).get("coin") == "BTC"]
                print(f"   BTC orders found: {len(btc_orders)}")
                
                if len(btc_orders) > 0:
                    print(f"✅ SUCCESS: BTC perpetual orders found in API!")
                    for order in btc_orders[-2:]:  # Show last 2
                        order_data = order.get("order", {})
                        print(f"      {order_data.get('side')} {order_data.get('sz')} @ ${order_data.get('limitPx')}")
                else:
                    print(f"❌ No BTC perpetual orders found in API")
                
                # Final verdict
                print(f"\\n🎯 VERIFICATION RESULTS:")
                if len(order_ids) > 0:
                    print(f"✅ Order placement: SUCCESS ({len(order_ids)} orders got IDs)")
                else:
                    print(f"❌ Order placement: FAILED (no order IDs)")
                
                if len(btc_orders) > len([o for o in baseline_orders if o.get("order", {}).get("coin") == "BTC"]):
                    print(f"✅ API visibility: SUCCESS (new BTC orders appear in API)")
                else:
                    print(f"❌ API visibility: FAILED (no new BTC orders in API)")
                
            else:
                print("❌ No market data available for BTC-USD")
        else:
            print("❌ BTC-USD order book not available")
    
    finally:
        # Cleanup
        try:
            await connector.stop_network()
            print(f"\\n🧹 Perpetual connector stopped")
        except:
            pass


if __name__ == "__main__":
    asyncio.run(verify_perp_order_placement())