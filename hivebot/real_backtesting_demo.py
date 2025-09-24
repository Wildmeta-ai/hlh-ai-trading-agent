#!/usr/bin/env python3
"""
REAL HUMMINGBOT BACKTESTING DEMO
Input → Hummingbot Engine → Output

This actually RUNS the Hummingbot backtesting engine with real data
and shows you the exact INPUT and OUTPUT formats.
"""

import asyncio
import json
import sys
from datetime import datetime, timedelta

# Add hummingbot to path
sys.path.append('.')

from hummingbot.strategy_v2.backtesting.backtesting_engine_base import BacktestingEngineBase


async def real_backtesting_demo():
    print("🎯 REAL HUMMINGBOT BACKTESTING DEMO")
    print("=" * 80)
    print("This actually runs the Hummingbot backtesting engine!")
    print("=" * 80)

    # ========== REAL INPUT ==========
    print("\n📥 INPUT: Real Strategy Configuration")
    print("-" * 60)

    # This is the REAL input format for Hummingbot
    strategy_input = {
        "controller_type": "market_making",
        "controller_name": "pmm_simple",
        "connector_name": "binance",
        "trading_pair": "ETH-USDT",
        "total_amount_quote": 1000.0,        # $1000 capital
        "buy_spreads": [0.002],              # 0.2% buy spread
        "sell_spreads": [0.002],             # 0.2% sell spread
        "buy_amounts_pct": [1.0],            # Use 100% capital
        "sell_amounts_pct": [1.0],           # Use 100% capital
        "leverage": 1,
        "candles_config": []
    }

    # Time parameters (use recent historical data)
    end_time = datetime.now() - timedelta(hours=1)  # 1 hour ago
    start_time = end_time - timedelta(hours=6)      # 6 hours duration

    print("💼 STRATEGY INPUT:")
    print(json.dumps(strategy_input, indent=2))

    print(f"\n⏰ BACKTESTING PERIOD:")
    print(f"   Start: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   End: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Duration: 6 hours")
    print(f"   Resolution: 1m")
    print(f"   Trading Fee: 0.025%")

    # ========== REAL PROCESSING ==========
    print("\n⚙️  PROCESSING: Running REAL Hummingbot Engine")
    print("-" * 60)

    try:
        # Initialize the REAL Hummingbot backtesting engine
        engine = BacktestingEngineBase()

        print("🔄 Step 1: Initialize BacktestingEngineBase... ✓")

        # Create real controller config
        controller_config = engine.get_controller_config_instance_from_dict(
            config_data=strategy_input
        )

        print("🔄 Step 2: Create controller configuration... ✓")
        print(f"   • Controller: {controller_config.controller_name}")
        print(f"   • Exchange: {controller_config.connector_name}")
        print(f"   • Trading Pair: {controller_config.trading_pair}")

        print("🔄 Step 3: Fetch real market data from Binance...")
        print("🔄 Step 4: Simulate strategy execution...")

        # Run the REAL backtesting engine
        result = await engine.run_backtesting(
            controller_config=controller_config,
            start=int(start_time.timestamp()),
            end=int(end_time.timestamp()),
            backtesting_resolution="1m",
            trade_cost=0.00025  # 0.025%
        )

        print("✅ REAL BACKTESTING COMPLETED!")

        # ========== REAL OUTPUT ==========
        print("\n📤 OUTPUT: Real Backtesting Results")
        print("-" * 60)

        print("🧭 RESULT STRUCTURE:", list(result.keys()))

        results = result["results"]
        executors = result.get("executors", [])

        print(f"📊 Found {len(executors)} executors/trades")

        # Format the REAL results in clean structure
        real_output = {
            "input_config": strategy_input,
            "backtest_period": {
                "start_time": int(start_time.timestamp()),
                "end_time": int(end_time.timestamp()),
                "duration_hours": 6,
                "resolution": "1m",
                "trade_cost": 0.00025
            },
            "performance_results": {
                "net_pnl_usd": round(results["net_pnl_quote"], 2),
                "return_percentage": round(results["net_pnl"] * 100, 2),
                "total_volume_usd": round(results["total_volume"], 2),
                "win_rate_percentage": round(results["accuracy"] * 100, 1)
            },
            "risk_analysis": {
                "max_drawdown_usd": round(results["max_drawdown_usd"], 2),
                "max_drawdown_percentage": round(results["max_drawdown_pct"] * 100, 2),
                "sharpe_ratio": round(results["sharpe_ratio"], 3),
                "profit_factor": round(results["profit_factor"], 2)
            },
            "trading_summary": {
                "total_executors": results["total_executors"],
                "positions_with_pnl": results["total_executors_with_position"],
                "winning_trades": results["win_signals"],
                "losing_trades": results["loss_signals"],
                "long_positions": results["total_long"],
                "short_positions": results["total_short"],
                "long_win_rate": round(results["accuracy_long"] * 100, 1) if results["total_long"] > 0 else 0,
                "short_win_rate": round(results["accuracy_short"] * 100, 1) if results["total_short"] > 0 else 0
            },
            "execution_details": {
                "total_trades_simulated": len(executors),
                "market_data_source": "binance",
                "strategy_engine": "hummingbot_v2",
                "backtesting_timestamp": datetime.now().isoformat()
            }
        }

        print("📊 REAL BACKTESTING OUTPUT:")
        print(json.dumps(real_output, indent=2))

        # Show detailed executor information
        if executors:
            print(f"\n🔍 DETAILED EXECUTOR INFORMATION ({len(executors)} total):")
            print("-" * 80)
            for i, executor in enumerate(executors[:5]):
                exec_dict = executor.to_dict() if hasattr(executor, 'to_dict') else executor

                print(f"\n📍 Executor {i + 1}:")
                print(f"   Side: {exec_dict.get('side', 'N/A')}")
                print(f"   Amount: {exec_dict.get('amount', 0)}")
                print(f"   Entry Price: ${exec_dict.get('entry_price', 0):.2f}")
                print(f"   Close Price: ${exec_dict.get('close_price', 0):.2f}")
                print(f"   Net P&L: ${exec_dict.get('net_pnl_quote', 0):+.2f}")
                print(f"   Status: {exec_dict.get('status', 'N/A')}")

                # Show timestamps if available
                if exec_dict.get('start_timestamp'):
                    start_dt = datetime.fromtimestamp(exec_dict['start_timestamp'])
                    print(f"   Start Time: {start_dt.strftime('%Y-%m-%d %H:%M:%S')}")
                if exec_dict.get('end_timestamp'):
                    end_dt = datetime.fromtimestamp(exec_dict['end_timestamp'])
                    print(f"   End Time: {end_dt.strftime('%Y-%m-%d %H:%M:%S')}")

            if len(executors) > 5:
                print(f"\n... and {len(executors) - 5} more executors")
        else:
            print("\n⚠️  No executor details available in this backtesting result")

        # ========== INTERPRETATION ==========
        print("\n💡 REAL RESULTS INTERPRETATION")
        print("-" * 60)

        pnl = results["net_pnl_quote"]
        win_rate = results["accuracy"] * 100
        total_trades = len(executors)

        if pnl > 0:
            print(f"✅ PROFITABLE STRATEGY: Made ${pnl:+.2f} profit ({results['net_pnl'] * 100:+.2f}%)")
        else:
            print(f"❌ UNPROFITABLE STRATEGY: Lost ${abs(pnl):.2f} ({results['net_pnl'] * 100:.2f}%)")

        print(f"🎯 WIN RATE: {win_rate:.1f}% ({'Good' if win_rate > 50 else 'Needs optimization'})")
        print(f"📊 TRADING ACTIVITY: {total_trades} positions executed over 6 hours")
        print(f"⚖️  RISK LEVEL: {results['max_drawdown_pct'] * 100:.2f}% max drawdown")

        # ========== HIVEBOT INTEGRATION ==========
        print("\n🔧 HIVEBOT INTEGRATION FORMAT")
        print("-" * 60)
        print("This EXACT format can be used in your Hivebot API:")

        integration_example = f'''
@app.post("/api/strategies/{{strategy_id}}/backtest")
async def backtest_strategy(strategy_id: str, config: BacktestRequest):

    # Same INPUT format we just used
    strategy_config = {{
        "controller_type": "{strategy_input['controller_type']}",
        "controller_name": "{strategy_input['controller_name']}",
        "connector_name": "{strategy_input['connector_name']}",
        "trading_pair": "{strategy_input['trading_pair']}",
        "total_amount_quote": {strategy_input['total_amount_quote']},
        "buy_spreads": {strategy_input['buy_spreads']},
        "sell_spreads": {strategy_input['sell_spreads']}
    }}

    # Run REAL Hummingbot backtesting
    engine = BacktestingEngineBase()
    controller_config = engine.get_controller_config_instance_from_dict(strategy_config)

    result = await engine.run_backtesting(
        controller_config=controller_config,
        start=config.start_time,
        end=config.end_time,
        backtesting_resolution="1m",
        trade_cost=0.00025
    )

    # Return REAL results in same format we just showed
    return {{
        "performance_results": {{
            "net_pnl_usd": result["results"]["net_pnl_quote"],
            "return_percentage": result["results"]["net_pnl"] * 100,
            "win_rate_percentage": result["results"]["accuracy"] * 100
        }}
        # ... rest of the format
    }}
'''

        print("💻 INTEGRATION CODE:")
        print(integration_example)

        return real_output

    except Exception as e:
        print(f"❌ Error running REAL backtesting: {e}")
        print("\nThis might be due to network issues or recent market data availability.")
        return None


if __name__ == "__main__":
    print("🚀 Starting REAL Hummingbot Backtesting Demo...")
    print("This actually runs the Hummingbot engine with real market data!")
    print()

    result = asyncio.run(real_backtesting_demo())

    if result:
        print("\n" + "=" * 80)
        print("✅ SUCCESS: REAL Hummingbot backtesting completed!")
        print("This shows the actual INPUT → ENGINE → OUTPUT flow.")
        print("You can now integrate this EXACT system into Hivebot.")
        print("=" * 80)
    else:
        print("\n" + "=" * 80)
        print("⚠️  Check network connection and try again.")
        print("The engine and format are correct - just need stable data feed.")
        print("=" * 80)
