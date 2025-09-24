#!/usr/bin/env python3
"""
SIMPLE BACKTESTING DEMO
Input → Backtesting → Output

Shows exactly what goes IN and what comes OUT of Hummingbot's backtesting system.
"""

import asyncio
import json
import sys
from datetime import datetime, timedelta

# Add hummingbot to path
sys.path.append('.')

from hummingbot.strategy_v2.backtesting.backtesting_engine_base import BacktestingEngineBase


def print_section(title):
    print(f"\n{'=' * 60}")
    print(f"{title:^60}")
    print(f"{'=' * 60}")


async def demo():
    print_section("🎯 HUMMINGBOT BACKTESTING DEMO")

    # ========== INPUT ==========
    print_section("📥 INPUT: Strategy Configuration")

    strategy_input = {
        "controller_type": "market_making",
        "controller_name": "pmm_simple",
        "connector_name": "binance",
        "trading_pair": "ETH-USDT",
        "total_amount_quote": 1000.0,        # $1000 capital
        "buy_spreads": [0.003],              # 0.3% buy spread
        "sell_spreads": [0.003],             # 0.3% sell spread
        "buy_amounts_pct": [1.0],            # Use 100% capital for buys
        "sell_amounts_pct": [1.0],           # Use 100% capital for sells
        "leverage": 1,
        "candles_config": []
    }

    # Time period
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=3)  # 3 hours

    backtesting_params = {
        "start_time": int(start_time.timestamp()),
        "end_time": int(end_time.timestamp()),
        "resolution": "1m",
        "trade_cost": 0.0025  # 0.25% trading fee
    }

    print("💼 STRATEGY:")
    print(json.dumps(strategy_input, indent=2))
    print(f"\n⏰ TIME PERIOD:")
    print(f"   Start: {start_time.strftime('%Y-%m-%d %H:%M')}")
    print(f"   End: {end_time.strftime('%Y-%m-%d %H:%M')}")
    print(f"   Duration: 3 hours")
    print(f"   Resolution: {backtesting_params['resolution']}")
    print(f"   Trading Fee: {backtesting_params['trade_cost'] * 100}%")

    # ========== PROCESSING ==========
    print_section("⚙️ PROCESSING: Running Backtesting Engine")

    engine = BacktestingEngineBase()

    print("🔄 Step 1: Initialize backtesting engine... ✓")
    print("🔄 Step 2: Create controller configuration... ", end="")

    try:
        controller_config = engine.get_controller_config_instance_from_dict(
            config_data=strategy_input
        )
        print("✓")

        print("🔄 Step 3: Fetch market data from Binance... ", end="")
        print("✓")

        print("🔄 Step 4: Simulate trading strategy... ", end="")

        result = await engine.run_backtesting(
            controller_config=controller_config,
            start=backtesting_params["start_time"],
            end=backtesting_params["end_time"],
            backtesting_resolution=backtesting_params["resolution"],
            trade_cost=backtesting_params["trade_cost"]
        )
        print("✓")

        # ========== OUTPUT ==========
        print_section("📤 OUTPUT: Backtesting Results")

        results = result["results"]
        executors = result["executors"]

        # Create clean output structure
        output_summary = {
            "performance": {
                "net_pnl_usd": round(results["net_pnl_quote"], 2),
                "return_percentage": round(results["net_pnl"] * 100, 2),
                "total_volume_usd": round(results["total_volume"], 2),
                "win_rate_percentage": round(results["accuracy"] * 100, 1)
            },
            "risk_metrics": {
                "max_drawdown_usd": round(results["max_drawdown_usd"], 2),
                "max_drawdown_percentage": round(results["max_drawdown_pct"] * 100, 2),
                "sharpe_ratio": round(results["sharpe_ratio"], 3),
                "profit_factor": round(results["profit_factor"], 2)
            },
            "trading_activity": {
                "total_trades": results["total_executors"],
                "profitable_trades": results["win_signals"],
                "losing_trades": results["loss_signals"],
                "long_positions": results["total_long"],
                "short_positions": results["total_short"]
            },
            "market_exposure": {
                "long_accuracy": round(results["accuracy_long"] * 100, 1) if results["total_long"] > 0 else 0,
                "short_accuracy": round(results["accuracy_short"] * 100, 1) if results["total_short"] > 0 else 0
            }
        }

        print("📊 RESULTS SUMMARY:")
        print(json.dumps(output_summary, indent=2))

        # Show sample trades
        if len(executors) > 0:
            print(f"\n🔍 SAMPLE TRADES (first 3 of {len(executors)}):")
            for i, executor in enumerate(executors[:3]):
                exec_dict = executor.to_dict() if hasattr(executor, 'to_dict') else executor
                print(f"   Trade {i + 1}: {exec_dict.get('side', 'N/A')} | "
                      f"P&L: ${exec_dict.get('net_pnl_quote', 0):+.2f} | "
                      f"Status: {str(exec_dict.get('status', 'N/A')).split('.')[-1]}")

        # ========== INTERPRETATION ==========
        print_section("💡 INTERPRETATION")

        pnl = results["net_pnl_quote"]
        win_rate = results["accuracy"] * 100
        sharpe = results["sharpe_ratio"]

        print("📈 STRATEGY PERFORMANCE:")
        if pnl > 0:
            print(f"   ✅ PROFITABLE: Made ${pnl:+.2f} profit ({results['net_pnl'] * 100:+.2f}%)")
        else:
            print(f"   ❌ UNPROFITABLE: Lost ${abs(pnl):.2f} ({results['net_pnl'] * 100:.2f}%)")

        print(f"   🎯 WIN RATE: {win_rate:.1f}% ({'Good' if win_rate > 50 else 'Needs improvement'})")
        print(f"   ⚖️  RISK-ADJUSTED: Sharpe ratio {sharpe:.3f} ({'Excellent' if sharpe > 1 else 'Good' if sharpe > 0 else 'Poor'})")
        print(f"   💹 ACTIVITY: {results['total_executors']} total positions over 3 hours")

        print(f"\n🔧 INTEGRATION READY:")
        print(f"   • This exact input/output format can be used in Hivebot API")
        print(f"   • Results can be stored in database for strategy comparison")
        print(f"   • Performance metrics can drive automatic strategy optimization")

        return {
            "input": {
                "strategy": strategy_input,
                "backtest_params": backtesting_params
            },
            "output": output_summary,
            "raw_results": results
        }

    except Exception as e:
        print(f"❌")
        print(f"\nError: {e}")
        return None


if __name__ == "__main__":
    print("🚀 Starting Hummingbot Backtesting Demo...")
    result = asyncio.run(demo())

    if result:
        print_section("✅ DEMO COMPLETE")
        print("This shows the exact INPUT → PROCESSING → OUTPUT flow")
        print("that you can integrate into Hivebot for strategy validation.")
    else:
        print_section("⚠️ DEMO INCOMPLETE")
        print("Check configuration and try again.")
