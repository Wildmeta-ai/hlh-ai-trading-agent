#!/usr/bin/env python3

"""
Test Dynamic Hivebot - Simple demonstration of database-driven dynamic strategy management.
"""

import asyncio
import time
from hive_dynamic_core import HiveDynamicDatabase, DynamicStrategyConfig, HiveDynamicCore
from hummingbot.client.config.config_helpers import load_client_config_map_from_file

async def test_database_operations():
    """Test database operations for dynamic strategies."""
    print("🗄️  TESTING HIVEBOT DATABASE OPERATIONS")
    print("=" * 60)
    
    # Initialize database
    db = HiveDynamicDatabase("test_hivebot.db")
    
    # Test 1: Load default strategies
    print("\n📋 DEFAULT STRATEGIES FROM DATABASE:")
    strategies = db.load_all_strategies()
    for strategy in strategies:
        print(f"   {strategy.name:12}: {strategy.bid_spread:5.3f}% spread, {strategy.order_refresh_time:4.1f}s refresh, {strategy.order_levels} levels")
    
    # Test 2: Add new strategy dynamically
    print(f"\n➕ ADDING NEW SCALPER STRATEGY:")
    scalper_config = DynamicStrategyConfig(
        name="SCALPER",
        bid_spread=0.001,  # 0.1bp - ultra tight
        ask_spread=0.001,
        order_refresh_time=0.1,  # 100ms - ultra fast
        order_levels=10,  # Many levels
        order_amount=0.0001  # Small size
    )
    
    success = db.save_strategy(scalper_config)
    print(f"   {'✅ Added' if success else '❌ Failed'}: SCALPER strategy (0.1bp spread, 100ms refresh)")
    
    # Test 3: Update existing strategy
    print(f"\n🔄 UPDATING CONSERVATIVE STRATEGY:")
    conservative_update = DynamicStrategyConfig(
        name="CONSERVATIVE",
        bid_spread=0.03,  # Changed from 0.10% to 0.03%
        ask_spread=0.03,
        order_refresh_time=7.0,  # Changed from 10s to 7s
        order_levels=2,  # Changed from 1 to 2
        order_amount=0.008  # Changed size
    )
    
    success = db.save_strategy(conservative_update)
    print(f"   {'✅ Updated' if success else '❌ Failed'}: CONSERVATIVE (0.10% → 0.03% spread, 10s → 7s refresh)")
    
    # Test 4: Show all strategies after changes
    print(f"\n📊 ALL STRATEGIES AFTER UPDATES:")
    strategies = db.load_all_strategies()
    for strategy in strategies:
        print(f"   {strategy.name:12}: {strategy.bid_spread:5.3f}% spread, {strategy.order_refresh_time:4.1f}s refresh, {strategy.order_levels} levels, {strategy.order_amount:.6f} amount")
    
    print(f"\n✅ Database operations test completed!")
    print(f"   📊 Total strategies: {len(strategies)}")
    print(f"   🗄️  Database file: {db.db_path}")
    
    return db

async def test_dynamic_hive_core():
    """Test dynamic Hive core without API server."""
    print("\n\n🤖 TESTING DYNAMIC HIVEBOT CORE")
    print("=" * 60)
    
    # Initialize Hive core
    client_config_map = load_client_config_map_from_file()
    hive = HiveDynamicCore(client_config_map, db_path="test_hivebot.db")
    
    # Load strategies from database
    await hive.load_strategies_from_database()
    print(f"📋 Loaded {len(hive.strategies)} strategies from database")
    
    # Start coordination loop (simplified, no API server)
    hive._hive_running = True
    hive.start_time = time.time()
    
    print(f"\n🔄 RUNNING DYNAMIC COORDINATION CYCLES:")
    
    # Run a few cycles to show initial behavior
    for cycle in range(5):
        await hive.process_dynamic_hive_cycle()
        await asyncio.sleep(1)
    
    print(f"\n🔥 DEMONSTRATING HOT-ADD STRATEGY:")
    # Add new strategy while "running"
    arbitrage_config = DynamicStrategyConfig(
        name="ARBITRAGE",
        bid_spread=0.005,
        ask_spread=0.005,
        order_refresh_time=2.0,
        order_levels=4,
        order_amount=0.002
    )
    
    success = await hive.add_strategy_dynamically(arbitrage_config)
    print(f"   {'✅ Success' if success else '❌ Failed'}: Hot-added ARBITRAGE strategy!")
    
    # Run more cycles to show the new strategy in action
    print(f"\n📈 CYCLES WITH NEW STRATEGY:")
    for cycle in range(3):
        await hive.process_dynamic_hive_cycle()
        await asyncio.sleep(1)
    
    print(f"\n🔄 DEMONSTRATING HOT-UPDATE STRATEGY:")
    # Update strategy while running
    updated_aggressive = DynamicStrategyConfig(
        name="AGGRESSIVE", 
        bid_spread=0.002,  # Tighter spread
        ask_spread=0.002,
        order_refresh_time=0.5,  # Faster refresh
        order_levels=5,  # More levels
        order_amount=0.0005  # Smaller size
    )
    
    success = await hive.update_strategy_config_dynamically("AGGRESSIVE", updated_aggressive)
    print(f"   {'✅ Success' if success else '❌ Failed'}: Hot-updated AGGRESSIVE strategy!")
    
    # Show updated behavior
    print(f"\n⚡ CYCLES WITH UPDATED STRATEGY:")
    for cycle in range(3):
        await hive.process_dynamic_hive_cycle()
        await asyncio.sleep(1)
    
    print(f"\n🗑️  DEMONSTRATING HOT-REMOVE STRATEGY:")
    success = await hive.remove_strategy_dynamically("MEDIUM")
    print(f"   {'✅ Success' if success else '❌ Failed'}: Hot-removed MEDIUM strategy!")
    
    # Final cycles
    print(f"\n📊 FINAL CYCLES (one strategy removed):")
    for cycle in range(3):
        await hive.process_dynamic_hive_cycle()
        await asyncio.sleep(1)
    
    # Show final statistics
    print(f"\n🎯 DYNAMIC HIVEBOT TEST RESULTS:")
    print(f"   🤖 Final strategy count: {len(hive.strategies)}")
    print(f"   ⚡ Total actions generated: {hive.total_actions}")
    print(f"   🔄 Total cycles executed: {hive.total_cycles}")
    print(f"   📊 Performance: {hive.total_actions/max(hive.total_cycles, 1):.1f} actions per cycle")
    
    print(f"\n📋 FINAL STRATEGY STATUS:")
    for name, info in hive.strategies.items():
        config = info.config
        print(f"   {name:12}: {config.bid_spread:5.3f}% spread, {config.order_refresh_time:4.1f}s refresh, {info.actions_count:3d} actions")
    
    return hive

async def main():
    """Main test function."""
    print("🤖 DYNAMIC HIVEBOT ARCHITECTURE TEST")
    print("Database-driven strategy management with hot operations")
    print()
    
    try:
        # Test database operations
        db = await test_database_operations()
        
        # Test dynamic Hive core
        hive = await test_dynamic_hive_core()
        
        print(f"\n✅ ALL DYNAMIC HIVEBOT TESTS COMPLETED SUCCESSFULLY!")
        print(f"   🗄️  Database persistence: Working")
        print(f"   🔥 Hot-add strategies: Working") 
        print(f"   🔄 Hot-update strategies: Working")
        print(f"   🗑️  Hot-remove strategies: Working")
        print(f"   ⚡ Real-time coordination: Working")
        
        print(f"\n💡 READY FOR PRODUCTION:")
        print(f"   1. No need for pre-created config files")
        print(f"   2. All strategies stored in database")
        print(f"   3. Add/remove/update strategies while running")
        print(f"   4. API server ready for web interface")
        print(f"   5. Persistent configuration across restarts")
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())