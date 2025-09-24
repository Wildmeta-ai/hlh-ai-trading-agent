#!/usr/bin/env python3
"""
Official Hummingbot API Backtesting Demo

This demonstrates the PROPER way to use Hummingbot's backtesting capabilities:
- Uses the official Hummingbot API Backtesting Router
- Production-ready approach with hummingbot-api-client
- Real V2 controller configurations
- Professional-grade backtesting system

This is the actual system that powers the Hummingbot Dashboard backtesting feature.
"""

import asyncio
import json
from datetime import datetime, timedelta

from hummingbot_api_client import HummingbotAPIClient


async def demonstrate_official_backtesting():
    """
    Demonstrates the official Hummingbot API Backtesting Router

    This is the REAL backtesting system that you should integrate into Hivebot.
    Not a simple script - this is production-grade infrastructure.
    """

    print("🚀 OFFICIAL Hummingbot API Backtesting Demo")
    print("=" * 60)
    print("This uses the same API that powers Hummingbot Dashboard!")
    print("=" * 60)

    # ========== OFFICIAL API CONFIGURATION ==========
    api_url = "http://localhost:8000"  # Hummingbot API server
    username = "admin"                 # Set during setup
    password = "admin"                 # Set during setup

    print(f"📡 BACKTESTING INPUTS (Official API):")
    print(f"  API Endpoint: {api_url}")
    print(f"  Authentication: {username} / [hidden]")
    print()

    try:
        # Connect to official Hummingbot API
        async with HummingbotAPIClient(api_url, username, password) as client:

            # ========== CONTROLLER CONFIGURATION ==========
            # This is a REAL V2 controller configuration, not a simple script
            controller_config = {
                "controller_type": "market_making",
                "controller_name": "pmm_simple",
                "connector_name": "hyperliquid",
                "trading_pair": "BTC-USD",
                "total_amount_quote": 1000.0,   # $1000 capital
                "order_amount": 10.0,           # $10 per order
                "spread": 0.002,                # 0.2% spread (20 bps)
                "leverage": 1,
                "position_mode": "HEDGE",       # For derivatives
                "candles_config": [
                    {
                        "connector": "hyperliquid",
                        "trading_pair": "BTC-USD",
                        "interval": "1m",
                        "max_records": 300
                    }
                ]
            }

            print("📊 STRATEGY CONFIGURATION (V2 Controller):")
            print(f"  Controller: {controller_config['controller_type']}.{controller_config['controller_name']}")
            print(f"  Exchange: {controller_config['connector_name']}")
            print(f"  Pair: {controller_config['trading_pair']}")
            print(f"  Capital: ${controller_config['total_amount_quote']:,}")
            print(f"  Order Size: ${controller_config['order_amount']}")
            print(f"  Spread: {controller_config['spread'] * 100:.2f}%")
            print()

            # ========== BACKTESTING PARAMETERS ==========
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=7)  # 7 days back

            backtesting_config = {
                "start_time": int(start_time.timestamp()),
                "end_time": int(end_time.timestamp()),
                "backtesting_resolution": "1m",
                "trade_cost": 0.00025,  # 0.025% fee (2.5 bps)
                "config": controller_config
            }

            print("⏱️  BACKTESTING PERIOD:")
            print(f"  Start: {start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            print(f"  End: {end_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            print(f"  Duration: {(end_time - start_time).days} days")
            print(f"  Resolution: {backtesting_config['backtesting_resolution']}")
            print(f"  Trade Cost: {backtesting_config['trade_cost'] * 100:.3f}%")
            print()

            print("🔄 Running Official Backtesting Router...")
            print("   (This may take 30-60 seconds for real market data processing)")

            # ========== OFFICIAL API CALL ==========
            # This is the REAL production backtesting system
            result = await client.backtesting.run_backtesting(
                start_time=backtesting_config["start_time"],
                end_time=backtesting_config["end_time"],
                backtesting_resolution=backtesting_config["backtesting_resolution"],
                trade_cost=backtesting_config["trade_cost"],
                config=backtesting_config["config"]
            )

            # ========== OFFICIAL BACKTESTING OUTPUTS ==========
            print("✅ Backtesting Complete!")
            print("=" * 60)
            print("📈 OFFICIAL BACKTESTING RESULTS:")
            print("=" * 60)

            # Performance Summary
            results = result["results"]
            print("💰 PERFORMANCE METRICS:")
            print(f"  Net P&L: {results['net_pnl_quote']:+.2f} USD ({results['net_pnl'] * 100:+.2f}%)")
            print(f"  Total Volume: ${results['total_volume']:,.2f}")
            print(f"  Total Executors: {results['total_executors']}")
            print(f"  Positions Taken: {results['total_executors_with_position']}")
            print(f"  Win Rate: {results['accuracy'] * 100:.1f}%")
            print()

            # Risk Metrics
            print("📊 RISK ANALYSIS:")
            print(f"  Max Drawdown: ${results['max_drawdown_usd']:,.2f} ({results['max_drawdown_pct'] * 100:.2f}%)")
            print(f"  Sharpe Ratio: {results['sharpe_ratio']:.2f}")
            print(f"  Profit Factor: {results['profit_factor']:.2f}")
            print(f"  Win Signals: {results['win_signals']}")
            print(f"  Loss Signals: {results['loss_signals']}")
            print()

            # Trade Breakdown
            print("📋 TRADING ACTIVITY:")
            print(f"  Long Positions: {results['total_long']}")
            print(f"  Short Positions: {results['total_short']}")
            print(f"  Long Accuracy: {results['accuracy_long'] * 100:.1f}%")
            print(f"  Short Accuracy: {results['accuracy_short'] * 100:.1f}%")
            print()

            # Executor Details
            executors = result["executors"]
            if executors:
                print(f"🔍 SAMPLE EXECUTOR (First of {len(executors)}):")
                sample_executor = executors[0]
                print(f"  ID: {sample_executor['config']['id']}")
                print(f"  Side: {sample_executor['side']}")
                print(f"  Amount: {sample_executor['amount']}")
                print(f"  Entry Price: ${sample_executor.get('entry_price', 0):.2f}")
                print(f"  Close Price: ${sample_executor.get('close_price', 0):.2f}")
                print(f"  Net P&L: ${sample_executor['net_pnl_quote']:+.2f}")
                print(f"  Status: {sample_executor['status']}")
                print()

            # Close Type Analysis
            if results.get('close_types'):
                print("📈 POSITION CLOSE ANALYSIS:")
                for close_type, count in results['close_types'].items():
                    print(f"  {close_type}: {count} positions")
                print()

            print("=" * 60)
            print("🎯 WHAT THIS DEMONSTRATES:")
            print("  ✓ Official Hummingbot API Backtesting Router")
            print("  ✓ Production-grade V2 controller system")
            print("  ✓ Real market data from exchange APIs")
            print("  ✓ Advanced risk and performance metrics")
            print("  ✓ Professional backtesting infrastructure")
            print("  ✓ Same system used by Hummingbot Dashboard")
            print()
            print("💡 INTEGRATION READY:")
            print("  This is the EXACT API you should integrate into Hivebot")
            print("  for production-grade strategy backtesting capabilities.")
            print("=" * 60)

            return result

    except Exception as e:
        print(f"❌ Error connecting to Hummingbot API: {e}")
        print()
        print("🛠️  SETUP REQUIRED:")
        print("   1. Start Hummingbot API server: cd hummingbot-api && ./run.sh")
        print("   2. Verify server at http://localhost:8000/docs")
        print("   3. Ensure Docker services (PostgreSQL, EMQX) are running")
        print()
        print("📚 This is the OFFICIAL way to use Hummingbot backtesting.")
        print("   Not a demo script, but the real production system.")
        return None


async def show_api_structure():
    """
    Shows the structure of the official API without requiring a running server
    """
    print("\n🔧 HUMMINGBOT API STRUCTURE ANALYSIS")
    print("=" * 50)

    print("📁 Official API Components:")
    print("  • /routers/backtesting.py - Backtesting Router")
    print("  • /models/backtesting.py - Data Models")
    print("  • BacktestingEngineBase - Core Engine")
    print("  • V2 Controllers - Strategy Logic")
    print()

    print("🌐 API Endpoints:")
    print("  POST /backtesting/run-backtesting")
    print("    - Input: BacktestingConfig (start/end time, resolution, controller)")
    print("    - Output: Executors, processed data, performance results")
    print()

    print("📊 Official Input Format:")
    example_input = {
        "start_time": int(datetime.utcnow().timestamp() - 7 * 24 * 3600),
        "end_time": int(datetime.utcnow().timestamp()),
        "backtesting_resolution": "1m",
        "trade_cost": 0.00025,
        "config": {
            "controller_type": "market_making",
            "controller_name": "pmm_simple",
            "connector_name": "hyperliquid",
            "trading_pair": "BTC-USD",
            "total_amount_quote": 1000.0
        }
    }
    print(json.dumps(example_input, indent=2))
    print()

    print("📈 Official Output Format:")
    print("  • executors: List of trade executions with full details")
    print("  • results: Performance metrics (P&L, Sharpe, drawdown, etc.)")
    print("  • processed_data: Market data with strategy signals")
    print()

    print("🎯 Integration Point for Hivebot:")
    print("  Add backtesting endpoint to hive_api.py:")
    print("  @app.post('/api/strategies/{id}/backtest')")
    print("  async def backtest_strategy(id, config: BacktestConfig)")


if __name__ == "__main__":
    print("🚀 Official Hummingbot API Backtesting Demo")
    print("This demonstrates the REAL production backtesting system")
    print()

    # Try to run official API demo
    result = asyncio.run(demonstrate_official_backtesting())

    # Always show the API structure for reference
    asyncio.run(show_api_structure())

    print("\n✅ Demo Complete!")
    print("This is the official, production-ready way to integrate")
    print("Hummingbot's backtesting capabilities into your Hivebot system.")
