"""
Main integration script for AI Trading Agent
Demonstrates the complete workflow from data fetching to strategy generation
"""
import asyncio
import json
import logging
from datetime import datetime

import sys
import importlib.util
sys.path.append('.')

# Import from hyphened directories
import backend.data
from backend.data import get_trader_analysis

# Import ai_agent module
ai_agent_spec = importlib.util.spec_from_file_location("ai_agent", "backend/ai-agent/ai_processor.py")
ai_agent_module = importlib.util.module_from_spec(ai_agent_spec)
ai_agent_spec.loader.exec_module(ai_agent_module)
process_trader_data = ai_agent_module.process_trader_data

# Import mcp_server module  
mcp_spec = importlib.util.spec_from_file_location("mcp_server", "backend/mcp-server/mcp_server.py")
mcp_module = importlib.util.module_from_spec(mcp_spec)
mcp_spec.loader.exec_module(mcp_module)
initialize_mcp_server = mcp_module.initialize_mcp_server
mcp_server = mcp_module.mcp_server

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Main function demonstrating the AI trading agent workflow"""
    
    print("🚀 AI Trading Agent - Minimal Viable Product")
    print("=" * 50)
    
    # Test wallet address from requirements
    test_address = "0x37a45AdBb275d5d3F8100f4cF16977cd4B0f9Fb7"
    
    try:
        # Step 1: Initialize MCP Server
        print("\n1. Initializing MCP Server...")
        await initialize_mcp_server()
        print("✅ MCP Server initialized successfully")
        
        # Step 2: Fetch trader analysis data
        print(f"\n2. Fetching trader analysis for {test_address}...")
        trader_analysis = await get_trader_analysis(test_address)
        
        if not trader_analysis.get("ai_profile"):
            print("⚠️  Using mock data for demonstration")
            trader_analysis = {
                "address": test_address,
                "ai_profile": {
                    "trader": "A high-risk, high-reward daredevil who swings for the fences with 10x leverage while somehow maintaining emotional stability like a zen monk in a crypto hurricane.",
                    "nickname": "Leverage Lunatic",
                    "story": [
                        {
                            "symbol": "🚀 HYPE",
                            "summary": "From a shaky start (-$2.3k loss) to mooning with a $254k gain, this trader rode the HYPE train like it was rocket fuel."
                        },
                        {
                            "symbol": "🐻 SOL", 
                            "summary": "Got mauled by SOL bears (-$13k) but tamed them later with a $27k win - classic 'revenge trading' arc."
                        }
                    ],
                    "labels": ["Human Leverage Calculator", "Drawdown Speedrunner", "Stop-Loss Denier"],
                    "insights": ["Try trading with 1x leverage occasionally - your heart (and brokerage account) will thank you"],
                    "suggestion": "WARNING: Continuing at 10x leverage may cause sudden wealth evaporation 💸!"
                },
                "technical_metrics": {
                    "market_adaptability": {
                        "trend_following": 0.7,
                        "high_volatility": 0.8,
                        "bull_market": 0.6,
                        "bear_market": 0.4
                    },
                    "profile": {
                        "risk_level": "high"
                    },
                    "statistics": {
                        "total_trades": 50,
                        "winning_trades": 32,
                        "max_drawdown": 0.25
                    }
                },
                "trade_story": []
            }
        
        print("✅ Trader analysis data fetched")
        
        # Step 3: Process trader data and generate strategies
        print("\n3. Processing trader data and generating strategies...")
        strategy_results = process_trader_data(trader_analysis)
        print("✅ Strategies generated successfully")
        
        # Step 4: Display results
        print("\n4. Results:")
        print("-" * 30)
        
        print(f"\n🧠 Trader Profile: {trader_analysis['ai_profile']['nickname']}")
        print(f"Description: {trader_analysis['ai_profile']['trader'][:100]}...")
        
        print(f"\n📊 Behavior Analysis:")
        behavior = strategy_results.get("behavior_analysis", {})
        risk_profile = behavior.get("risk_profile", {})
        print(f"  • Risk Level: {risk_profile.get('risk_level', 'Unknown')}")
        print(f"  • Leverage Usage: {risk_profile.get('leverage_usage', 'Unknown')}")
        print(f"  • Win Rate: {risk_profile.get('win_rate', 0):.1%}")
        
        print(f"\n🎯 Generated Strategies ({len(strategy_results.get('strategies', []))}):")
        for i, strategy in enumerate(strategy_results.get("strategies", []), 1):
            print(f"  {i}. {strategy['name']}")
            print(f"     • Symbol: {strategy['symbol']}")
            print(f"     • Leverage: {strategy['leverage']}x")
            print(f"     • Position Size: ${strategy['position_size']:,.0f}")
            print(f"     • Risk per Trade: {strategy['risk_per_trade']:.1%}")
        
        # Step 5: Test MCP Server functions
        print(f"\n5. Testing MCP Server Functions...")
        
        # Test profile info
        profile_result = await mcp_server.profile_info(test_address)
        print(f"✅ Profile Info: Account Value ${profile_result.get('account_value', 0):,.2f}")
        
        # Test strategy configuration generation
        if strategy_results.get("strategies"):
            first_strategy = strategy_results["strategies"][0]
            config_result = await mcp_server.generate_config(first_strategy)
            print(f"✅ Config Generated: {config_result.get('config_id', 'Unknown')[:8]}...")
            
            # Test backtest
            backtest_result = await mcp_server.backtest_strategy(
                first_strategy, 
                "2024-01-01", 
                "2024-03-01"
            )
            print(f"✅ Backtest Complete: {backtest_result.get('total_return', 0):.1%} return")
        
        print(f"\n✅ Recommendations:")
        for rec in strategy_results.get("recommendations", []):
            print(f"  • {rec}")
        
        warnings = strategy_results.get("risk_warnings", [])
        if warnings:
            print(f"\n⚠️  Risk Warnings:")
            for warning in warnings:
                print(f"  • {warning}")
        
        print(f"\n🎉 AI Trading Agent MVP completed successfully!")
        print(f"Timestamp: {datetime.now().isoformat()}")
        
        # Step 6: Save results for frontend integration
        results_file = "/Users/hanwencheng/Projects/trader-monitor/ai-trading/demo_results.json"
        demo_results = {
            "trader_analysis": trader_analysis,
            "strategy_results": strategy_results,
            "mcp_results": {
                "profile": profile_result,
                "config": config_result if 'config_result' in locals() else None,
                "backtest": backtest_result if 'backtest_result' in locals() else None
            },
            "timestamp": datetime.now().isoformat()
        }
        
        with open(results_file, 'w') as f:
            json.dump(demo_results, f, indent=2, default=str)
        
        print(f"\n💾 Results saved to: {results_file}")
        
    except Exception as e:
        logger.error(f"Error in main workflow: {e}")
        print(f"❌ Error: {e}")

def test_hyperliquid_connectivity():
    """Test Hyperliquid API connectivity"""
    print("\n🔍 Testing Hyperliquid API connectivity...")
    
    try:
        import requests
        
        # Test basic info endpoint
        response = requests.post(
            "https://api.hyperliquid.xyz/info",
            json={"type": "allMids"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Hyperliquid API accessible - {len(data)} markets available")
            return True
        else:
            print(f"⚠️  Hyperliquid API returned status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Hyperliquid API connection failed: {e}")
        print("📝 Will use mock connector for demonstration")
        return False

if __name__ == "__main__":
    print("Testing Hyperliquid connectivity first...")
    test_hyperliquid_connectivity()
    
    print("\nStarting main workflow...")
    asyncio.run(main())