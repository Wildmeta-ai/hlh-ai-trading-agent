#!/usr/bin/env python3

"""
Multi-Strategy Test - Demonstrates multiple strategies sharing real market data.
This is the CORE of Hive: 1 market feed → N strategies → N×actions
"""

import asyncio
import aiohttp
import yaml
from decimal import Decimal
from datetime import datetime
from pathlib import Path
from typing import Dict, List


class StrategyEngine:
    """Individual strategy engine with its own parameters."""
    
    def __init__(self, name: str, config_path: str):
        self.name = name
        self.config_path = config_path
        self.config = self.load_config()
        self.active_orders = []
        self.actions_generated = 0
        self.last_refresh = 0
        
    def load_config(self) -> Dict:
        """Load strategy configuration from YAML file."""
        try:
            with open(self.config_path, 'r') as file:
                return yaml.safe_load(file)
        except Exception as e:
            print(f"❌ Error loading {self.name} config: {e}")
            return {}
    
    def should_refresh_orders(self, current_time: float) -> bool:
        """Check if this strategy should refresh its orders."""
        refresh_time = self.config.get('order_refresh_time', 60.0)
        return (current_time - self.last_refresh) >= refresh_time
    
    def generate_actions(self, market_data: Dict) -> List[Dict]:
        """Generate strategy actions based on market data and strategy config."""
        if not self.config:
            return []
            
        mid_price = market_data["mid_price"]
        actions = []
        
        # Get strategy parameters
        bid_spread = Decimal(str(self.config.get('bid_spread', 0.01))) / 100  # Convert % to decimal
        ask_spread = Decimal(str(self.config.get('ask_spread', 0.01))) / 100
        order_amount = Decimal(str(self.config.get('order_amount', 0.001)))
        order_levels = self.config.get('order_levels', 1)
        order_level_spread = Decimal(str(self.config.get('order_level_spread', 0))) / 100
        order_level_amount = Decimal(str(self.config.get('order_level_amount', 0)))
        take_if_crossed = self.config.get('take_if_crossed', False)
        
        # Cancel existing orders
        if self.active_orders:
            actions.append({
                "type": "CANCEL_ALL_ORDERS",
                "strategy": self.name,
                "count": len(self.active_orders),
                "reason": f"Refresh cycle"
            })
        
        # Generate orders for each level
        for level in range(order_levels):
            level_spread_adj = bid_spread + (order_level_spread * level)
            level_amount_adj = order_amount + (order_level_amount * level)
            
            # Calculate prices
            buy_price = mid_price * (Decimal("1") - level_spread_adj)
            sell_price = mid_price * (Decimal("1") + level_spread_adj)
            
            # Check for crossing
            buy_crosses = take_if_crossed and buy_price >= market_data["best_ask"]
            sell_crosses = take_if_crossed and sell_price <= market_data["best_bid"]
            
            # Buy orders
            if buy_crosses:
                actions.append({
                    "type": "MARKET_BUY",
                    "strategy": self.name,
                    "amount": level_amount_adj,
                    "price": market_data["best_ask"],
                    "level": level + 1,
                    "reason": f"Limit crosses ask"
                })
            else:
                actions.append({
                    "type": "LIMIT_BUY", 
                    "strategy": self.name,
                    "amount": level_amount_adj,
                    "price": buy_price,
                    "level": level + 1
                })
            
            # Sell orders
            if sell_crosses:
                actions.append({
                    "type": "MARKET_SELL",
                    "strategy": self.name, 
                    "amount": level_amount_adj,
                    "price": market_data["best_bid"],
                    "level": level + 1,
                    "reason": f"Limit crosses bid"
                })
            else:
                actions.append({
                    "type": "LIMIT_SELL",
                    "strategy": self.name,
                    "amount": level_amount_adj,
                    "price": sell_price,
                    "level": level + 1
                })
        
        self.active_orders = [a for a in actions if a["type"].startswith("LIMIT")]
        self.actions_generated += len(actions)
        
        return actions


class MultiStrategyHiveEngine:
    """
    HIVE CORE: Manages multiple strategies sharing the same market data feed.
    This is the foundation of the 1:N architecture.
    """
    
    def __init__(self):
        self.rest_url = "http://15.235.212.39:8081"
        self.strategies = {}
        self.shared_market_data = {}
        
        # Hive statistics
        self.market_updates = 0
        self.total_actions = 0
        self.strategies_triggered = 0
        
    def add_strategy(self, name: str, config_file: str):
        """Add a strategy to the Hive."""
        config_path = f"conf/strategies/{config_file}"
        if Path(config_path).exists():
            strategy = StrategyEngine(name, config_path)
            self.strategies[name] = strategy
            print(f"✅ Added strategy: {name} ({config_file})")
            return True
        else:
            print(f"❌ Strategy config not found: {config_path}")
            return False
    
    async def get_shared_market_data(self, coin: str = "ETH") -> Dict:
        """Get market data once for ALL strategies to share (Hive efficiency)."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.rest_url}/info",
                    json={"type": "l2Book", "coin": coin},
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
                                
                                return {
                                    "coin": coin,
                                    "mid_price": mid_price,
                                    "best_bid": best_bid,
                                    "best_ask": best_ask,
                                    "bid_size": Decimal(bids[0]["sz"]),
                                    "ask_size": Decimal(asks[0]["sz"]),
                                    "spread": spread,
                                    "spread_pct": spread / mid_price,
                                    "timestamp": datetime.now()
                                }
        except Exception as e:
            print(f"❌ Shared market data error: {e}")
        
        return None
    
    def process_market_update_across_strategies(self, market_data: Dict):
        """
        HIVE CORE LOGIC: Process ONE market update across ALL strategies.
        This is the key innovation - shared market data.
        """
        self.market_updates += 1
        self.shared_market_data = market_data
        
        timestamp = market_data["timestamp"].strftime("%H:%M:%S")
        
        print(f"\n🐝 HIVE MARKET UPDATE #{self.market_updates} [{timestamp}]")
        print(f"   📡 SHARED DATA: ETH ${market_data['mid_price']:.2f} (spread: ${market_data['spread']:.2f})")
        print(f"   🔄 Processing across {len(self.strategies)} strategies...")
        
        current_time = datetime.now().timestamp()
        strategies_that_acted = 0
        cycle_actions = 0
        
        # Process market data through ALL strategies
        for strategy_name, strategy in self.strategies.items():
            if strategy.should_refresh_orders(current_time):
                actions = strategy.generate_actions(market_data)
                
                if actions:
                    strategies_that_acted += 1
                    cycle_actions += len(actions)
                    self.display_strategy_actions(strategy_name, actions)
                    strategy.last_refresh = current_time
                else:
                    print(f"   💤 {strategy_name}: No actions (waiting)")
            else:
                remaining = strategy.config.get('order_refresh_time', 60) - (current_time - strategy.last_refresh)
                print(f"   ⏱️  {strategy_name}: Next refresh in {remaining:.1f}s")
        
        self.strategies_triggered += strategies_that_acted
        self.total_actions += cycle_actions
        
        print(f"   📊 HIVE CYCLE: {strategies_that_acted}/{len(self.strategies)} strategies acted, {cycle_actions} total actions")
    
    def display_strategy_actions(self, strategy_name: str, actions: List[Dict]):
        """Display actions from a specific strategy."""
        print(f"   ⚡ {strategy_name.upper()}: {len(actions)} actions")
        
        # Show first few actions as examples
        for i, action in enumerate(actions[:4]):
            if action["type"] == "CANCEL_ALL_ORDERS":
                print(f"      {i+1}. 🚫 CANCEL {action['count']} orders")
            elif action["type"] == "LIMIT_BUY":
                print(f"      {i+1}. 🟢 BUY {action['amount']} @ ${action['price']:.2f}")
            elif action["type"] == "LIMIT_SELL":
                print(f"      {i+1}. 🔴 SELL {action['amount']} @ ${action['price']:.2f}")
            elif action["type"] == "MARKET_BUY":
                print(f"      {i+1}. ⚡ MARKET BUY {action['amount']} @ ${action['price']:.2f}")
            elif action["type"] == "MARKET_SELL":
                print(f"      {i+1}. ⚡ MARKET SELL {action['amount']} @ ${action['price']:.2f}")
        
        if len(actions) > 4:
            print(f"      ... +{len(actions)-4} more actions")
    
    def show_hive_summary(self):
        """Show Hive efficiency summary.""" 
        print(f"\n🎯 HIVE EFFICIENCY ANALYSIS:")
        print(f"   📡 Market Updates: {self.market_updates} (shared across all strategies)")
        print(f"   ⚡ Total Actions: {self.total_actions}")
        print(f"   🎮 Strategies: {len(self.strategies)} different configurations")
        print(f"   🔄 Strategy Triggers: {self.strategies_triggered}")
        
        if self.market_updates > 0:
            print(f"   📈 Actions per Update: {self.total_actions / self.market_updates:.1f}")
            print(f"   🎯 Strategies per Update: {self.strategies_triggered / self.market_updates:.1f}")
        
        print(f"\n💡 HIVE BENEFITS DEMONSTRATED:")
        print(f"   ✅ Single market data feed serves {len(self.strategies)} strategies")
        print(f"   ✅ Each strategy uses same data but different logic")
        print(f"   ✅ N×efficiency: {len(self.strategies)}× strategies, 1× network calls")
        
        # Show strategy differences
        print(f"\n📊 STRATEGY DIVERSITY:")
        for name, strategy in self.strategies.items():
            refresh_time = strategy.config.get('order_refresh_time', 'N/A')
            spread = strategy.config.get('bid_spread', 'N/A')
            levels = strategy.config.get('order_levels', 'N/A')
            print(f"   {name}: {spread}% spread, {refresh_time}s refresh, {levels} levels, {strategy.actions_generated} actions")


async def run_multi_strategy_test():
    """
    Run the multi-strategy Hive test with shared market data.
    This demonstrates the core 1:N architecture.
    """
    
    print("🐝 MULTI-STRATEGY HIVE TEST")
    print("=" * 70)
    print("CORE INNOVATION: 1 market feed → N strategies")
    print("Same market data processed by multiple strategy configurations")
    print("-" * 70)
    
    # Initialize Hive engine
    hive = MultiStrategyHiveEngine()
    
    # Add multiple strategies with different configurations
    print("📋 SETTING UP HIVE STRATEGIES:")
    strategies_added = 0
    
    if hive.add_strategy("AGGRESSIVE", "hyper_test_strategy.yml"):
        strategies_added += 1
    if hive.add_strategy("CONSERVATIVE", "conservative_test_strategy.yml"):  
        strategies_added += 1
    if hive.add_strategy("MEDIUM", "medium_test_strategy.yml"):
        strategies_added += 1
    
    if strategies_added == 0:
        print("❌ No strategies could be loaded")
        return
    
    print(f"✅ Hive initialized with {strategies_added} strategies")
    print(f"🎯 Each strategy will process the SAME market data differently")
    print("-" * 70)
    
    try:
        # Run multi-strategy monitoring
        for cycle in range(10):  # 10 cycles = ~30 seconds
            print(f"\n{'='*20} HIVE CYCLE {cycle+1} {'='*20}")
            
            # Get market data ONCE (shared across all strategies)
            market_data = await hive.get_shared_market_data("ETH")
            
            if market_data:
                # Process through ALL strategies simultaneously
                hive.process_market_update_across_strategies(market_data)
            else:
                print("❌ Failed to get shared market data")
            
            # Wait before next cycle
            await asyncio.sleep(3)
        
        # Show final analysis
        hive.show_hive_summary()
        
        print(f"\n🚀 HIVE MULTI-STRATEGY TEST COMPLETE!")
        print(f"   ✅ Demonstrated 1:N architecture")
        print(f"   ✅ Shared market data across strategies") 
        print(f"   ✅ Different strategy behaviors from same data")
        print(f"   ✅ Foundation ready for real Hummingbot integration")
        
    except KeyboardInterrupt:
        print(f"\n🛑 Multi-strategy test stopped by user")
        hive.show_hive_summary()
        
    except Exception as e:
        print(f"❌ Multi-strategy test error: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main entry point."""
    print("🎯 HIVE MULTI-STRATEGY ARCHITECTURE TEST")
    print("Demonstrates the core innovation:")
    print("  📡 ONE market data feed")
    print("  ⚡ MULTIPLE strategies processing simultaneously")  
    print("  🔄 Different behaviors from same market data")
    print("  🎯 Foundation for real Hummingbot Hive integration")
    print()
    
    asyncio.run(run_multi_strategy_test())


if __name__ == "__main__":
    main()