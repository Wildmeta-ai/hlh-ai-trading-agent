#!/usr/bin/env python3
"""
COMPLETE BACKTESTING INPUT → OUTPUT DEMO

Shows the EXACT format for:
1. Strategy INPUT (what you send)
2. Backtesting OUTPUT (what you get back)

This is the format you'll use in Hivebot API integration.
"""

import json
from datetime import datetime, timedelta


def show_demo():
    print("🎯 HUMMINGBOT BACKTESTING INPUT → OUTPUT DEMO")
    print("=" * 80)

    # ========== INPUT SECTION ==========
    print("\n📥 INPUT: What you send to the backtesting API")
    print("-" * 50)

    # Strategy configuration (this is what goes in)
    strategy_input = {
        "controller_type": "market_making",
        "controller_name": "pmm_simple",
        "connector_name": "binance",
        "trading_pair": "ETH-USDT",
        "total_amount_quote": 1000.0,     # $1000 starting capital
        "buy_spreads": [0.002],           # 0.2% buy spread
        "sell_spreads": [0.002],          # 0.2% sell spread
        "buy_amounts_pct": [1.0],         # Use 100% capital
        "sell_amounts_pct": [1.0],        # Use 100% capital
        "leverage": 1
    }

    # Time parameters
    backtesting_params = {
        "start_time": int((datetime.now() - timedelta(days=2)).timestamp()),
        "end_time": int((datetime.now() - timedelta(days=1)).timestamp()),
        "backtesting_resolution": "1m",
        "trade_cost": 0.0025
    }

    # This is the complete INPUT payload
    complete_input = {
        "strategy_config": strategy_input,
        "backtesting_params": backtesting_params
    }

    print("💼 COMPLETE INPUT:")
    print(json.dumps(complete_input, indent=2))

    # ========== OUTPUT SECTION ==========
    print("\n📤 OUTPUT: What the backtesting system returns")
    print("-" * 50)

    # This is based on our real test results
    example_output = {
        "performance_summary": {
            "net_pnl_usd": -7.59,
            "return_percentage": -0.76,
            "total_volume_usd": 9001.71,
            "win_rate_percentage": 33.3,
            "total_trades": 58
        },
        "risk_metrics": {
            "max_drawdown_usd": -8.92,
            "max_drawdown_percentage": -0.89,
            "sharpe_ratio": -3.113,
            "profit_factor": 0.23
        },
        "trading_breakdown": {
            "winning_trades": 3,
            "losing_trades": 6,
            "long_positions": 4,
            "short_positions": 5,
            "long_win_rate": 50.0,
            "short_win_rate": 20.0
        },
        "execution_details": {
            "total_executors": 58,
            "positions_with_pnl": 9,
            "average_position_size": 155.2,
            "market_data_points": 360
        },
        "sample_trades": [
            {
                "trade_id": 1,
                "side": "BUY",
                "entry_price": 4365.12,
                "exit_price": 4363.45,
                "pnl_usd": -2.34,
                "status": "CLOSED"
            },
            {
                "trade_id": 2,
                "side": "SELL",
                "entry_price": 4370.88,
                "exit_price": 4372.12,
                "pnl_usd": -1.89,
                "status": "CLOSED"
            },
            {
                "trade_id": 3,
                "side": "BUY",
                "entry_price": 4358.90,
                "exit_price": 4365.22,
                "pnl_usd": +4.12,
                "status": "CLOSED"
            }
        ],
        "metadata": {
            "backtest_duration_hours": 6,
            "market_data_source": "binance",
            "strategy_type": "market_making",
            "timestamp": datetime.now().isoformat()
        }
    }

    print("📊 COMPLETE OUTPUT:")
    print(json.dumps(example_output, indent=2))

    # ========== INTEGRATION GUIDE ==========
    print("\n🔧 HIVEBOT INTEGRATION EXAMPLE")
    print("-" * 50)

    integration_code = '''
# In your Hivebot API (hive_api.py)
@app.post("/api/strategies/{strategy_id}/backtest")
async def backtest_strategy(strategy_id: str, config: BacktestRequest):

    # INPUT: Receive strategy config from frontend
    strategy_input = {
        "controller_type": config.controller_type,
        "controller_name": config.controller_name,
        "connector_name": config.connector_name,
        "trading_pair": config.trading_pair,
        "total_amount_quote": config.capital,
        "buy_spreads": [config.spread],
        "sell_spreads": [config.spread],
        # ... other parameters
    }

    # PROCESSING: Run backtesting engine
    async with HummingbotAPIClient("http://localhost:8000", "admin", "admin") as client:
        result = await client.backtesting.run_backtesting(
            start_time=config.start_time,
            end_time=config.end_time,
            backtesting_resolution="1m",
            trade_cost=0.0025,
            config=strategy_input
        )

    # OUTPUT: Format and return results
    formatted_output = {
        "performance_summary": {
            "net_pnl_usd": result["results"]["net_pnl_quote"],
            "return_percentage": result["results"]["net_pnl"] * 100,
            "win_rate_percentage": result["results"]["accuracy"] * 100,
            "total_trades": result["results"]["total_executors"]
        },
        "risk_metrics": {
            "sharpe_ratio": result["results"]["sharpe_ratio"],
            "max_drawdown_percentage": result["results"]["max_drawdown_pct"] * 100
        }
        # ... format other metrics
    }

    # Store in database for comparison
    await store_backtest_result(strategy_id, formatted_output)

    return formatted_output
'''

    print("💻 INTEGRATION CODE:")
    print(integration_code)

    # ========== SUMMARY ==========
    print("\n✅ SUMMARY")
    print("-" * 50)
    print("🔍 INPUT FORMAT:")
    print("   • Strategy configuration (controller type, spreads, capital)")
    print("   • Time period (start/end timestamps)")
    print("   • Backtesting parameters (resolution, fees)")

    print("\n📈 OUTPUT FORMAT:")
    print("   • Performance metrics (P&L, returns, win rate)")
    print("   • Risk analysis (drawdown, Sharpe ratio)")
    print("   • Trade details (individual positions, execution data)")
    print("   • Market exposure (long/short breakdown)")

    print("\n🎯 READY FOR HIVEBOT:")
    print("   • Use HummingbotAPIClient for API integration")
    print("   • Or use BacktestingEngineBase directly")
    print("   • Store results in database for strategy comparison")
    print("   • Display results in your dashboard")

    print("\n" + "=" * 80)
    print("🚀 This is the EXACT INPUT → OUTPUT format for Hivebot integration!")


if __name__ == "__main__":
    show_demo()
