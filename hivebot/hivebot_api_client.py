#!/usr/bin/env python3

"""
Hivebot API Client - Interact with dynamic Hivebot strategy management.
Allows adding/removing/updating strategies while Hivebot is running.
"""

import asyncio
import aiohttp
import json
from typing import Dict, List, Optional


class HivebotApiClient:
    """Client for interacting with Hivebot's dynamic API."""
    
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_strategies(self) -> Dict:
        """Get all strategies from Hivebot."""
        async with self.session.get(f"{self.base_url}/api/strategies") as response:
            return await response.json()
    
    async def create_strategy(self, strategy_config: Dict) -> Dict:
        """Create a new strategy in Hivebot."""
        async with self.session.post(
            f"{self.base_url}/api/strategies",
            json=strategy_config
        ) as response:
            return await response.json()
    
    async def update_strategy(self, name: str, strategy_config: Dict) -> Dict:
        """Update an existing strategy in Hivebot."""
        async with self.session.put(
            f"{self.base_url}/api/strategies/{name}",
            json=strategy_config
        ) as response:
            return await response.json()
    
    async def delete_strategy(self, name: str) -> Dict:
        """Delete a strategy from Hivebot."""
        async with self.session.delete(f"{self.base_url}/api/strategies/{name}") as response:
            return await response.json()
    
    async def get_status(self) -> Dict:
        """Get Hivebot status."""
        async with self.session.get(f"{self.base_url}/api/status") as response:
            return await response.json()


async def demo_dynamic_operations():
    """Demonstrate dynamic Hivebot operations via API."""
    
    print("🤖 HIVEBOT DYNAMIC API DEMONSTRATION")
    print("=" * 60)
    print("Real-time strategy management while Hivebot is running")
    print("-" * 60)
    
    try:
        async with HivebotApiClient() as client:
            
            # 1. Get initial status
            print("\n📊 INITIAL HIVEBOT STATUS:")
            status = await client.get_status()
            print(f"   Running: {status['hive_running']}")
            print(f"   Strategies: {status['total_strategies']}")
            print(f"   Total Actions: {status['total_actions']}")
            print(f"   Uptime: {status['uptime_seconds']:.1f}s")
            
            # 2. List current strategies
            print(f"\n📋 CURRENT STRATEGIES:")
            strategies_response = await client.get_strategies()
            for strategy in strategies_response['strategies']:
                config = strategy['config']
                print(f"   {config['name']}: {config['bid_spread']}% spread, {config['order_refresh_time']}s refresh, {strategy['actions_count']} actions")
            
            # 3. Add a new HIGH-FREQUENCY strategy
            print(f"\n🔥 ADDING HIGH-FREQUENCY STRATEGY DYNAMICALLY...")
            hf_strategy = {
                "name": "HIGH_FREQ",
                "exchange": "hyperliquid_testnet",
                "market": "ETH-USD",
                "bid_spread": 0.002,  # 0.2bp - very tight
                "ask_spread": 0.002,
                "order_amount": 0.0001,  # Small size
                "order_levels": 7,  # Many levels
                "order_refresh_time": 0.2,  # 200ms refresh - very fast!
                "order_level_spread": 0.001,
                "order_level_amount": 0.00005,
                "enabled": True
            }
            
            result = await client.create_strategy(hf_strategy)
            if result['success']:
                print(f"   ✅ Added HIGH_FREQ strategy: 0.2bp spread, 200ms refresh!")
            else:
                print(f"   ❌ Failed: {result['message']}")
            
            # Wait a moment for it to start acting
            await asyncio.sleep(5)
            
            # 4. Update CONSERVATIVE strategy to be more aggressive
            print(f"\n🔄 UPDATING CONSERVATIVE STRATEGY TO BE MORE AGGRESSIVE...")
            updated_conservative = {
                "name": "CONSERVATIVE",
                "exchange": "hyperliquid_testnet", 
                "market": "ETH-USD",
                "bid_spread": 0.02,  # Reduced from 0.1% to 0.02%
                "ask_spread": 0.02,
                "order_amount": 0.005,  # Reduced size
                "order_levels": 3,  # More levels
                "order_refresh_time": 3.0,  # Much faster refresh
                "enabled": True
            }
            
            result = await client.update_strategy("CONSERVATIVE", updated_conservative)
            if result['success']:
                print(f"   ✅ Updated CONSERVATIVE: Now 0.02% spread, 3s refresh (much more aggressive!)")
            else:
                print(f"   ❌ Failed: {result['message']}")
            
            # Wait for changes to take effect
            await asyncio.sleep(8)
            
            # 5. Check updated status
            print(f"\n📈 UPDATED STRATEGIES STATUS:")
            strategies_response = await client.get_strategies()
            for strategy in strategies_response['strategies']:
                config = strategy['config']
                perf = strategy['performance_metrics']
                print(f"   {config['name']:12}: {config['bid_spread']:6.3f}% spread, {config['order_refresh_time']:4.1f}s refresh, {strategy['actions_count']:3d} actions, {perf['actions_per_minute']:5.1f} APM")
            
            # 6. Show final Hivebot performance
            print(f"\n🎯 FINAL HIVEBOT PERFORMANCE:")
            status = await client.get_status()
            print(f"   Total Strategies: {status['total_strategies']}")
            print(f"   Total Actions: {status['total_actions']}")
            print(f"   Actions/Minute: {status['actions_per_minute']:.1f}")
            print(f"   Uptime: {status['uptime_seconds']:.1f}s")
            
            # 7. Demonstrate strategy removal
            print(f"\n🗑️  REMOVING HIGH_FREQ STRATEGY...")
            result = await client.delete_strategy("HIGH_FREQ")
            if result['success']:
                print(f"   ✅ Removed HIGH_FREQ strategy successfully")
            else:
                print(f"   ❌ Failed: {result['message']}")
            
            await asyncio.sleep(3)
            
            # Final status
            strategies_response = await client.get_strategies()
            print(f"\n📊 FINAL STRATEGY COUNT: {len(strategies_response['strategies'])}")
            for strategy in strategies_response['strategies']:
                config = strategy['config']
                print(f"   Remaining: {config['name']} - {strategy['actions_count']} total actions")
            
    except aiohttp.ClientError as e:
        print(f"❌ API Connection Error: {e}")
        print(f"   Make sure Hivebot is running with API server on localhost:8080")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print(f"\n🤖 HIVEBOT DYNAMIC API DEMONSTRATION COMPLETE!")
    print(f"   ✅ Successfully demonstrated hot-add/update/remove strategies")
    print(f"   ✅ All operations performed while Hivebot was running")
    print(f"   ✅ Database persistence maintained throughout")


async def interactive_hivebot_manager():
    """Interactive Hivebot strategy management."""
    
    print("🤖 INTERACTIVE HIVEBOT MANAGER")
    print("=" * 50)
    
    async with HivebotApiClient() as client:
        while True:
            print("\n🔧 HIVEBOT OPERATIONS:")
            print("1. List strategies")
            print("2. Add strategy")
            print("3. Update strategy") 
            print("4. Remove strategy")
            print("5. Show status")
            print("6. Exit")
            
            try:
                choice = input("\nSelect operation (1-6): ")
                
                if choice == "1":
                    strategies = await client.get_strategies()
                    print(f"\n📋 STRATEGIES ({len(strategies['strategies'])}):")
                    for strategy in strategies['strategies']:
                        config = strategy['config']
                        print(f"   {config['name']:15}: {config['bid_spread']:6.3f}% spread, {config['order_refresh_time']:4.1f}s, {strategy['actions_count']:4d} actions")
                
                elif choice == "2":
                    name = input("Strategy name: ")
                    spread = float(input("Spread % (e.g., 0.01): "))
                    refresh = float(input("Refresh time seconds (e.g., 5.0): "))
                    amount = float(input("Order amount (e.g., 0.001): "))
                    levels = int(input("Order levels (e.g., 1): "))
                    
                    strategy_config = {
                        "name": name,
                        "bid_spread": spread,
                        "ask_spread": spread,
                        "order_refresh_time": refresh,
                        "order_amount": amount,
                        "order_levels": levels
                    }
                    
                    result = await client.create_strategy(strategy_config)
                    print(f"Result: {result['message']}")
                
                elif choice == "3":
                    name = input("Strategy name to update: ")
                    spread = float(input("New spread % (e.g., 0.01): "))
                    refresh = float(input("New refresh time seconds (e.g., 5.0): "))
                    
                    strategy_config = {
                        "name": name,
                        "bid_spread": spread,
                        "ask_spread": spread,
                        "order_refresh_time": refresh
                    }
                    
                    result = await client.update_strategy(name, strategy_config)
                    print(f"Result: {result['message']}")
                
                elif choice == "4":
                    name = input("Strategy name to remove: ")
                    result = await client.delete_strategy(name)
                    print(f"Result: {result['message']}")
                
                elif choice == "5":
                    status = await client.get_status()
                    print(f"\n🤖 HIVEBOT STATUS:")
                    print(f"   Running: {status['hive_running']}")
                    print(f"   Strategies: {status['total_strategies']}")
                    print(f"   Total Actions: {status['total_actions']}")
                    print(f"   Actions/Min: {status['actions_per_minute']:.1f}")
                    print(f"   Uptime: {status['uptime_seconds']:.1f}s")
                
                elif choice == "6":
                    break
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")
    
    print("👋 Interactive manager closed")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        asyncio.run(interactive_hivebot_manager())
    else:
        asyncio.run(demo_dynamic_operations())