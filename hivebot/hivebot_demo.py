#!/usr/bin/env python3
"""
Hivebot Control Center Demo Application

This demo application showcases the core functionality of the Hivebot Manager:
1. Add Strategy - Create new strategies on running bot instances
2. View Status - Monitor running bot instances and strategy performance 
3. Delete Strategy - Remove strategies from bot instances

Usage:
    python hivebot_demo.py

Requirements:
    - Hivebot Manager running on http://localhost:3000
    - At least one bot instance running and registered
"""

import requests
import json
import time
import sys
from typing import Dict, List, Optional
from datetime import datetime

class HivebotControlCenter:
    """Client for interacting with Hivebot Manager Control Center"""
    
    def __init__(self, base_url: str = "http://localhost:3000"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        
    def get_bots(self) -> List[Dict]:
        """Get list of all registered bot instances"""
        try:
            response = self.session.get(f"{self.base_url}/api/bots")
            response.raise_for_status()
            data = response.json()
            return data.get('bots', [])
        except requests.RequestException as e:
            print(f"❌ Failed to fetch bots: {e}")
            return []
    
    def get_strategies(self) -> List[Dict]:
        """Get list of all strategies across all bots"""
        try:
            response = self.session.get(f"{self.base_url}/api/strategies")
            response.raise_for_status()
            data = response.json()
            return data.get('strategies', [])
        except requests.RequestException as e:
            print(f"❌ Failed to fetch strategies: {e}")
            return []
    
    def add_strategy(self, bot_id: str, strategy_config: Dict) -> bool:
        """Add a new strategy to a bot instance"""
        try:
            payload = {
                "bot_id": bot_id,
                "strategy": strategy_config
            }
            response = self.session.post(
                f"{self.base_url}/api/strategies",
                json=payload,
                headers={'Content-Type': 'application/json'}
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get('success'):
                print(f"✅ Strategy '{strategy_config['name']}' added successfully to bot {bot_id}")
                return True
            else:
                print(f"❌ Failed to add strategy: {result.get('error', 'Unknown error')}")
                return False
                
        except requests.RequestException as e:
            print(f"❌ Failed to add strategy: {e}")
            return False
    
    def delete_all_strategies(self, bot_id: str) -> bool:
        """Delete all strategies from a bot instance"""
        try:
            response = self.session.delete(f"{self.base_url}/api/strategies?bot_id={bot_id}")
            response.raise_for_status()
            result = response.json()
            
            if result.get('success'):
                deleted_strategies = result.get('deleted_strategies', [])
                successful_deletes = [s for s in deleted_strategies if s.get('success')]
                print(f"✅ Deleted {len(successful_deletes)} strategies from bot {bot_id}")
                return True
            else:
                print(f"❌ Failed to delete strategies: {result.get('error', 'Unknown error')}")
                return False
                
        except requests.RequestException as e:
            print(f"❌ Failed to delete strategies: {e}")
            return False
    
    def get_dashboard_metrics(self) -> Dict:
        """Get dashboard overview metrics"""
        try:
            response = self.session.get(f"{self.base_url}/api/bots?format=metrics")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"❌ Failed to fetch dashboard metrics: {e}")
            return {}

def print_header():
    """Print demo application header"""
    print("\n" + "="*60)
    print("🐝 HIVEBOT CONTROL CENTER - DEMO APPLICATION")
    print("="*60)
    print("Demonstrating centralized strategy management capabilities")
    print()

def print_bots_status(control_center: HivebotControlCenter):
    """Display current bot instances status"""
    print("\n📊 BOT INSTANCES STATUS")
    print("-" * 40)
    
    bots = control_center.get_bots()
    if not bots:
        print("❌ No bot instances found!")
        print("   Make sure at least one Hivebot instance is running and registered.")
        return bots
    
    print(f"Found {len(bots)} bot instances:")
    print()
    
    for i, bot in enumerate(bots, 1):
        status_emoji = {
            'running': '🟢',
            'stopped': '🔴', 
            'error': '🔴',
            'offline': '🟡'
        }.get(bot.get('status', 'unknown'), '⚪')
        
        print(f"  {i}. {status_emoji} {bot.get('name', 'Unknown')} [{bot.get('id', 'N/A')}]")
        print(f"     Status: {bot.get('status', 'unknown').upper()}")
        print(f"     Strategies: {bot.get('total_strategies', 0)}")
        print(f"     Actions/min: {bot.get('actions_per_minute', 0):.1f}")
        print(f"     Uptime: {bot.get('uptime', 0)//60}m")
        print(f"     Port: {bot.get('api_port', 'N/A')}")
        print()
    
    return bots

def print_strategies_status(control_center: HivebotControlCenter):
    """Display current strategies across all bots"""
    print("\n🎛️ STRATEGIES STATUS")
    print("-" * 40)
    
    strategies = control_center.get_strategies()
    if not strategies:
        print("📭 No strategies found across all bots")
        return strategies
    
    print(f"Found {len(strategies)} active strategies:")
    print()
    
    # Group strategies by bot
    strategies_by_bot = {}
    for strategy in strategies:
        bot_id = strategy.get('bot_id', 'unknown')
        if bot_id not in strategies_by_bot:
            strategies_by_bot[bot_id] = []
        strategies_by_bot[bot_id].append(strategy)
    
    for bot_id, bot_strategies in strategies_by_bot.items():
        print(f"  🤖 Bot: {bot_id}")
        for strategy in bot_strategies:
            status_emoji = '🟢' if strategy.get('status') == 'active' else '🟡'
            print(f"    {status_emoji} {strategy.get('name', 'Unnamed')}")
            print(f"       Type: {strategy.get('strategy_type', 'N/A')}")
            print(f"       Pairs: {', '.join(strategy.get('trading_pairs', []))}")
            print(f"       Actions: {strategy.get('total_actions', 0)}")
            print(f"       Success Rate: {strategy.get('successful_orders', 0)}/{strategy.get('total_actions', 0) or 1}")
            print()
    
    return strategies

def demo_add_strategy(control_center: HivebotControlCenter, bots: List[Dict]):
    """Demo: Add a new strategy to a bot"""
    print("\n➕ DEMO: ADD STRATEGY")
    print("-" * 40)
    
    if not bots:
        print("❌ No bots available to add strategy to")
        return False
    
    # Find a running bot
    running_bots = [bot for bot in bots if bot.get('status') == 'running']
    if not running_bots:
        print("❌ No running bots found!")
        print("   Please start at least one bot instance first.")
        return False
    
    # Use the first running bot
    target_bot = running_bots[0]
    bot_id = target_bot['name']  # Use name as bot_id (matches the API expectation)
    
    print(f"🎯 Adding demo strategy to bot: {target_bot['name']} [{target_bot['id']}]")
    
    # Create a demo strategy configuration
    demo_strategy = {
        "name": f"demo_strategy_{int(time.time())}",
        "strategy_type": "pure_market_making",
        "connector_type": "hyperliquid_perpetual", 
        "trading_pairs": ["BTC-USD"],
        "bid_spread": 0.01,  # 1%
        "ask_spread": 0.01,  # 1%
        "order_amount": 0.001,  # Small amount for demo
        "order_levels": 1,
        "order_refresh_time": 10.0,  # 10 seconds
        "enabled": True
    }
    
    print(f"📋 Strategy configuration:")
    for key, value in demo_strategy.items():
        print(f"   {key}: {value}")
    print()
    
    # Add the strategy
    success = control_center.add_strategy(bot_id, demo_strategy)
    
    if success:
        print("⏱️  Waiting 3 seconds for strategy to initialize...")
        time.sleep(3)
        return True
    return False

def demo_delete_strategies(control_center: HivebotControlCenter, bots: List[Dict]):
    """Demo: Delete all strategies from a bot"""
    print("\n🗑️  DEMO: DELETE STRATEGIES")
    print("-" * 40)
    
    if not bots:
        print("❌ No bots available")
        return False
    
    # Find bots with strategies
    strategies = control_center.get_strategies()
    bots_with_strategies = list(set(s.get('bot_id') for s in strategies))
    
    if not bots_with_strategies:
        print("📭 No strategies found to delete")
        return False
    
    # Use the first bot with strategies
    target_bot_id = bots_with_strategies[0]
    bot_strategies = [s for s in strategies if s.get('bot_id') == target_bot_id]
    
    print(f"🎯 Deleting {len(bot_strategies)} strategies from bot: {target_bot_id}")
    for strategy in bot_strategies:
        print(f"   - {strategy.get('name', 'Unnamed')}")
    print()
    
    # Delete all strategies
    success = control_center.delete_all_strategies(target_bot_id)
    
    if success:
        print("⏱️  Waiting 2 seconds for deletion to complete...")
        time.sleep(2)
        return True
    return False

def interactive_menu(control_center: HivebotControlCenter):
    """Interactive demo menu"""
    while True:
        print("\n" + "="*40)
        print("INTERACTIVE DEMO MENU")
        print("="*40)
        print("1. 📊 View Bot Status")
        print("2. 🎛️  View Strategies Status") 
        print("3. ➕ Add Demo Strategy")
        print("4. 🗑️  Delete All Strategies")
        print("5. 🔄 Refresh Dashboard Metrics")
        print("6. 🚪 Exit")
        print()
        
        try:
            choice = input("Select option (1-6): ").strip()
            
            if choice == '1':
                bots = print_bots_status(control_center)
                
            elif choice == '2':
                strategies = print_strategies_status(control_center)
                
            elif choice == '3':
                bots = control_center.get_bots()
                demo_add_strategy(control_center, bots)
                
            elif choice == '4':
                bots = control_center.get_bots()
                demo_delete_strategies(control_center, bots)
                
            elif choice == '5':
                print("\n🔄 DASHBOARD METRICS")
                print("-" * 40)
                metrics = control_center.get_dashboard_metrics()
                if metrics:
                    print(f"Total Bots: {metrics.get('total_bots', 0)}")
                    print(f"Active Bots: {metrics.get('active_bots', 0)}")
                    print(f"Total Strategies: {metrics.get('total_strategies', 0)}")
                    print(f"Active Strategies: {metrics.get('active_strategies', 0)}")
                    print(f"Actions (24h): {metrics.get('total_actions_24h', 0)}")
                    print(f"Uptime: {metrics.get('uptime_percentage', 0):.1f}%")
                else:
                    print("❌ Failed to fetch metrics")
                    
            elif choice == '6':
                print("\n👋 Exiting demo application...")
                break
                
            else:
                print("❌ Invalid option. Please select 1-6.")
                
        except KeyboardInterrupt:
            print("\n\n👋 Exiting demo application...")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

def main():
    """Main demo application"""
    print_header()
    
    # Initialize control center client
    control_center = HivebotControlCenter()
    
    print("🔗 Connecting to Hivebot Manager at http://localhost:3000...")
    
    # Test connection
    try:
        bots = control_center.get_bots()
        print(f"✅ Connected successfully! Found {len(bots)} registered bots.")
    except Exception as e:
        print(f"❌ Failed to connect to Hivebot Manager: {e}")
        print("\n💡 Please ensure:")
        print("   1. Hivebot Manager is running (npm run dev or npm start)")
        print("   2. Manager is accessible at http://localhost:3000")
        print("   3. At least one bot instance is registered")
        sys.exit(1)
    
    print("\n🎮 Starting interactive demo...")
    
    # Run initial status overview
    print_bots_status(control_center)
    print_strategies_status(control_center)
    
    # Start interactive menu
    interactive_menu(control_center)

if __name__ == "__main__":
    main()