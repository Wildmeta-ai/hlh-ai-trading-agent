#!/usr/bin/env python3
"""
Complete Demo Reset Script - Clears everything for clean testing
"""

import requests
import psycopg2
import json
import sys
from typing import List, Dict

# Database configuration
DB_CONFIG = {
    'host': '15.235.212.36',
    'port': 5432,
    'database': 'hummingbot_api',
    'user': 'hbot',
    'password': 'hummingbot-api'
}

MANAGER_URL = "http://localhost:3000"

def print_header():
    print("\n" + "="*60)
    print("🧹 HIVEBOT DEMO COMPLETE RESET")
    print("="*60)
    print("This will completely clear all demo data:")
    print("• PostgreSQL database (all My_* strategies)")
    print("• Bot instances (stop all running strategies)")
    print("• localStorage will need manual browser clear")
    print()

def get_all_demo_strategies():
    """Get all demo strategies from API"""
    try:
        response = requests.get(f"{MANAGER_URL}/api/strategies")
        if response.ok:
            data = response.json()
            demo_strategies = [s for s in data.get('strategies', []) if s.get('name', '').startswith('My_')]
            print(f"📋 Found {len(demo_strategies)} demo strategies:")
            for strategy in demo_strategies:
                print(f"   - {strategy.get('name')} (status: {strategy.get('status', 'unknown')})")
            return demo_strategies
        else:
            print(f"❌ Failed to get strategies: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Error getting strategies: {e}")
        return []

def delete_strategy_from_api(strategy_name: str):
    """Delete strategy using manager API"""
    try:
        response = requests.delete(f"{MANAGER_URL}/api/strategies?strategy_name={strategy_name}")
        if response.ok:
            print(f"✅ API deletion: {strategy_name}")
            return True
        else:
            print(f"❌ API deletion failed: {strategy_name} ({response.status_code})")
            return False
    except Exception as e:
        print(f"❌ API deletion error: {strategy_name} - {e}")
        return False

def clear_database_directly():
    """Clear demo strategies directly from PostgreSQL"""
    try:
        print("\n🗄️ Clearing PostgreSQL database...")
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # Get count of all strategies (complete reset for demo)
        cur.execute("SELECT COUNT(*) FROM hive_strategy_configs")
        count = cur.fetchone()[0]
        
        print(f"📊 Found {count} strategies in database")
        
        if count > 0:
            # Delete ALL strategies for complete demo reset
            cur.execute("DELETE FROM hive_strategy_configs")
            deleted_strategies = cur.rowcount
            
            # Also clean up stale hive instances
            cur.execute("DELETE FROM hive_instances WHERE last_seen < NOW() - INTERVAL '30 seconds'")
            deleted_instances = cur.rowcount
            
            conn.commit()
            print(f"✅ Deleted {deleted_strategies} strategies from PostgreSQL (complete reset)")
            print(f"✅ Deleted {deleted_instances} stale bot instances from PostgreSQL")
        else:
            print("✅ No strategies to delete")
            
        # Always clean up stale hive instances regardless of strategies
        cur.execute("DELETE FROM hive_instances WHERE last_seen < NOW() - INTERVAL '30 seconds'")
        deleted_instances = cur.rowcount
        if deleted_instances > 0:
            conn.commit()
            print(f"✅ Deleted {deleted_instances} stale bot instances from PostgreSQL")
        else:
            print("✅ No stale bot instances to clean")
            
        cur.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database cleanup error: {e}")
        return False

def get_bot_instances():
    """Get list of bot instances"""
    try:
        response = requests.get(f"{MANAGER_URL}/api/bots")
        if response.ok:
            data = response.json()
            bots = data.get('bots', [])
            print(f"🤖 Found {len(bots)} bot instances:")
            for bot in bots:
                print(f"   - {bot.get('name')} (port: {bot.get('api_port')}, strategies: {bot.get('total_strategies', 0)})")
            return bots
        else:
            print(f"❌ Failed to get bots: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Error getting bots: {e}")
        return []

def clear_bot_strategies(bot):
    """Clear all strategies from a specific bot"""
    try:
        # Check if bot is actually running
        if bot.get('status') != 'running':
            print(f"   ⏸️ Bot {bot.get('name')} is offline, skipping...")
            return True
            
        # Use the correct API port - some bots use port 8080, 8082 etc.
        bot_name = bot.get('name', '')
        if '8080' in bot_name:
            api_port = 8080
        elif '8082' in bot_name:
            api_port = 8082
        elif '8081' in bot_name:
            api_port = 8081
        else:
            api_port = bot.get('api_port', 8080)
            
        print(f"   📡 Connecting to bot {bot.get('name')} on port {api_port}")
        
        # Get bot's strategies
        bot_url = f"http://localhost:{api_port}/api/strategies"
        response = requests.get(bot_url, timeout=10)
        
        if response.ok:
            data = response.json()
            strategies = data.get('strategies', [])
            print(f"   📋 Found {len(strategies)} strategies on {bot.get('name')}")
            
            # Delete each strategy - try both API patterns
            deleted = 0
            for strategy in strategies:
                strategy_name = strategy.get('name')
                try:
                    # Pattern 1: DELETE /api/strategies/STRATEGY_NAME
                    delete_url = f"{bot_url}/{strategy_name}"
                    delete_response = requests.delete(delete_url, timeout=10)
                    
                    if delete_response.ok:
                        deleted += 1
                        print(f"   ✅ Deleted {strategy_name} (pattern 1)")
                    else:
                        # Pattern 2: Try with query parameter
                        delete_url2 = f"{bot_url}?strategy_name={strategy_name}"
                        delete_response2 = requests.delete(delete_url2, timeout=10)
                        
                        if delete_response2.ok:
                            deleted += 1
                            print(f"   ✅ Deleted {strategy_name} (pattern 2)")
                        else:
                            print(f"   ❌ Failed to delete {strategy_name} (tried both patterns)")
                            print(f"      Pattern 1 status: {delete_response.status_code}")
                            print(f"      Pattern 2 status: {delete_response2.status_code}")
                            
                except Exception as e:
                    print(f"   ❌ Error deleting {strategy_name}: {e}")
            
            print(f"   🧹 Cleared {deleted}/{len(strategies)} strategies from {bot.get('name')}")
            return deleted == len(strategies)
        else:
            print(f"   ⚠️ Could not access bot {bot.get('name')} (port {api_port}): HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error clearing bot {bot.get('name')}: {e}")
        return False

def main():
    print_header()
    
    # Auto-confirm for scripted execution
    if len(sys.argv) > 1 and sys.argv[1] == '--auto':
        print("🤖 Auto-confirmed: Running complete reset...")
    else:
        print("💡 Use --auto flag to run without confirmation: python reset_demo.py --auto")
        return
    
    success_count = 0
    total_operations = 4
    
    print("\n🚀 Starting complete reset...")
    
    # 1. Get and delete strategies via API
    print("\n1️⃣ DELETING STRATEGIES VIA API")
    demo_strategies = get_all_demo_strategies()
    
    if demo_strategies:
        for strategy in demo_strategies:
            if delete_strategy_from_api(strategy.get('name')):
                success_count += 0.2
    else:
        print("✅ No demo strategies to delete via API")
        success_count += 1
    
    # 2. Clear database directly
    print("\n2️⃣ CLEARING DATABASE")
    if clear_database_directly():
        success_count += 1
    
    # 3. Clear bot instances
    print("\n3️⃣ CLEARING BOT INSTANCES")
    bots = get_bot_instances()
    
    if bots:
        bot_success = 0
        for bot in bots:
            if clear_bot_strategies(bot):
                bot_success += 1
        print(f"🤖 Cleared strategies from {bot_success}/{len(bots)} bots")
        if bot_success == len(bots):
            success_count += 1
    else:
        print("✅ No bots to clear")
        success_count += 1
    
    # 4. Final verification
    print("\n4️⃣ VERIFICATION")
    final_strategies = get_all_demo_strategies()
    if len(final_strategies) == 0:
        print("✅ Verification: No demo strategies remaining")
        success_count += 1
    else:
        print(f"⚠️ Verification: {len(final_strategies)} strategies still remain")
    
    # Summary
    print("\n" + "="*60)
    print("🎯 RESET SUMMARY")
    print("="*60)
    success_percentage = (success_count / total_operations) * 100
    print(f"Success Rate: {success_percentage:.1f}% ({success_count:.1f}/{total_operations})")
    
    if success_percentage >= 90:
        print("✅ Reset completed successfully!")
        print("\n📝 MANUAL STEPS NEEDED:")
        print("1. Clear browser localStorage:")
        print("   - Open browser dev tools (F12)")
        print("   - Go to Application/Storage tab") 
        print("   - Clear localStorage for localhost:3000")
        print("2. Refresh the demo page: http://localhost:3000/demo")
        print("3. Verify the dashboard shows no demo strategies")
    else:
        print("⚠️ Reset partially completed - some manual cleanup may be needed")
    
    print("\n🎯 Ready for clean demo testing!")

if __name__ == "__main__":
    main()