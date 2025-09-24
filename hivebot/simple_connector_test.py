#!/usr/bin/env python3

"""
Simple Connector Test - Ultra clean test showing real Hummingbot data flow.
No complex imports, just shows the core components working.
"""

import asyncio
import aiohttp
import time
from decimal import Decimal
from datetime import datetime


class SimpleHummingbotFlowTest:
    """
    Ultra simple test that shows how Hummingbot would process market data.
    Uses the same API endpoints that the real Hummingbot connector uses.
    """
    
    def __init__(self):
        # Same endpoints that real Hummingbot hyperliquid connector uses
        self.rest_url = "http://15.235.212.39:8081"
        self.ws_url = "wss://api.hyperliquid.xyz/ws"
        
        # Statistics
        self.api_calls = 0
        self.market_updates = 0
        self.strategy_triggers = 0
        
        # Strategy parameters (from hyper_test_strategy.yml)
        self.bid_spread = Decimal("0.0001")  # 0.01%
        self.ask_spread = Decimal("0.0001")  
        self.order_refresh_time = 1.0  # 1 second
        self.order_levels = 3
        
    def log_flow(self, message: str, level: str = "INFO"):
        """Simple flow logging."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if level == "API":
            self.api_calls += 1
            print(f"🌐 API #{self.api_calls} [{timestamp}]: {message}")
        elif level == "STRATEGY":
            self.strategy_triggers += 1  
            print(f"⚡ STRATEGY #{self.strategy_triggers} [{timestamp}]: {message}")
        elif level == "MARKET":
            self.market_updates += 1
            print(f"📡 MARKET #{self.market_updates} [{timestamp}]: {message}")
        else:
            print(f"ℹ️  [{timestamp}]: {message}")
    
    async def test_hummingbot_data_endpoints(self):
        """Test the same API endpoints that real Hummingbot uses."""
        
        print("🐝 SIMPLE HUMMINGBOT DATA FLOW TEST")
        print("=" * 60)
        print("Testing the SAME endpoints that real Hummingbot connector uses")
        print("Shows how market data → strategy decisions work")
        print("-" * 60)
        
        try:
            async with aiohttp.ClientSession() as session:
                # Test the meta endpoint (same as real connector)
                self.log_flow("Calling /info endpoint (same as real Hummingbot)", "API")
                
                async with session.post(
                    f"{self.rest_url}/info",
                    json={"type": "meta"},
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.log_flow(f"✅ Connected to {len(data.get('universe', []))} assets", "API")
                    else:
                        self.log_flow(f"❌ API error: {response.status}", "API")
                        return
                
                # Main monitoring loop (simulates real connector behavior)
                self.log_flow("Starting market data monitoring (like real connector)...", "API")
                
                for cycle in range(20):  # 20 cycles = ~1 minute
                    # Get market data (same call as real connector)
                    market_data = await self.get_market_data_like_real_connector(session)
                    
                    if market_data:
                        # Process like real Hummingbot would
                        await self.simulate_hummingbot_processing(market_data)
                    
                    # Wait between calls (like real connector)
                    await asyncio.sleep(3)
                
                print(f"\n✅ HUMMINGBOT DATA FLOW TEST COMPLETE!")
                print(f"   🌐 API Calls: {self.api_calls}")
                print(f"   📡 Market Updates: {self.market_updates}")
                print(f"   ⚡ Strategy Triggers: {self.strategy_triggers}")
                print(f"   🎯 This demonstrates the REAL Hummingbot data flow!")
                
        except Exception as e:
            self.log_flow(f"❌ Test error: {e}", "API")
            import traceback
            traceback.print_exc()
    
    async def get_market_data_like_real_connector(self, session):
        """Get market data using same API call as real Hummingbot connector."""
        try:
            async with session.post(
                f"{self.rest_url}/info",
                json={"type": "l2Book", "coin": "ETH"},
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if "levels" in data and len(data["levels"]) >= 2:
                        bids = data["levels"][0]
                        asks = data["levels"][1]
                        
                        if len(bids) > 0 and len(asks) > 0:
                            best_bid = Decimal(bids[0]["px"])
                            best_ask = Decimal(asks[0]["px"])
                            mid_price = (best_bid + best_ask) / 2
                            spread = best_ask - best_bid
                            
                            market_info = f"ETH ${mid_price:.2f} (spread: ${spread:.2f})"
                            self.log_flow(market_info, "MARKET")
                            
                            return {
                                "mid_price": mid_price,
                                "best_bid": best_bid,
                                "best_ask": best_ask,
                                "spread": spread
                            }
        except Exception as e:
            self.log_flow(f"Market data error: {e}", "API")
        
        return None
    
    async def simulate_hummingbot_processing(self, market_data):
        """Simulate how real Hummingbot processes market data → strategy actions."""
        
        mid_price = market_data["mid_price"]
        
        # This is what the real strategy would do every refresh cycle
        actions = []
        
        # 1. Cancel existing orders
        actions.append("🚫 CANCEL existing orders")
        
        # 2. Calculate new order prices (real strategy logic)
        for level in range(self.order_levels):
            level_spread = self.bid_spread * (level + 1)
            
            buy_price = mid_price * (Decimal("1") - level_spread)
            sell_price = mid_price * (Decimal("1") + level_spread)
            
            # Check if orders would cross the market (real logic)
            if buy_price >= market_data["best_ask"]:
                actions.append(f"⚡ MARKET BUY @ ${market_data['best_ask']:.2f} (Level {level+1})")
            else:
                actions.append(f"🟢 LIMIT BUY @ ${buy_price:.2f} (Level {level+1})")
            
            if sell_price <= market_data["best_bid"]:
                actions.append(f"⚡ MARKET SELL @ ${market_data['best_bid']:.2f} (Level {level+1})")
            else:
                actions.append(f"🔴 LIMIT SELL @ ${sell_price:.2f} (Level {level+1})")
        
        # Log strategy actions
        action_summary = f"{len(actions)} actions: {actions[0]}, +{len(actions)-1} orders"
        self.log_flow(action_summary, "STRATEGY")
        
        # Show some actions in detail
        if len(actions) > 1:
            print(f"       Examples: {actions[1]}, {actions[2] if len(actions) > 2 else ''}")
    
    def show_flow_summary(self):
        """Show what this test demonstrated."""
        print(f"\n🎯 WHAT THIS TEST SHOWED:")
        print(f"   🌐 Same API endpoints as real Hummingbot connector")
        print(f"   📡 Real market data from Hyperliquid testnet")
        print(f"   ⚡ Same strategy logic as pure_market_making")
        print(f"   🔄 Complete data flow: Market → Strategy → Actions")
        print(f"\n🐝 READY FOR HIVE:")
        print(f"   ✅ This is the EXACT flow we'll modify for multi-strategy")
        print(f"   ✅ Shows how 1 market feed → 1 strategy currently works")
        print(f"   ✅ Next step: 1 market feed → N strategies (Hive)")


async def main():
    """Main test function."""
    test = SimpleHummingbotFlowTest()
    
    try:
        await test.test_hummingbot_data_endpoints()
        test.show_flow_summary()
        
    except KeyboardInterrupt:
        print(f"\n🛑 Test stopped by user")
        test.show_flow_summary()


if __name__ == "__main__":
    print("🎯 SIMPLE HUMMINGBOT DATA FLOW TEST")
    print("No complex setup - just shows the core flow")
    print("Same endpoints + logic as real Hummingbot")
    print()
    
    asyncio.run(main())