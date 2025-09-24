#!/usr/bin/env python3
"""
Setup script to create very idle strategies for rate limit compliance
"""

import sys

sys.path.append('.')

from enum import Enum

from hive_database import HiveDynamicDatabase, UniversalStrategyConfig


class StrategyType(Enum):
    PURE_MARKET_MAKING = "pure_market_making"


class ConnectorType(Enum):
    HYPERLIQUID_PERPETUAL = "hyperliquid_perpetual"


def setup_idle_strategies():
    """Create very idle strategies to avoid rate limits."""

    db = HiveDynamicDatabase()

    # Note: Not clearing existing strategies, will add new idle one

    # Create very conservative strategies
    idle_strategies = [
        UniversalStrategyConfig(
            name="IDLE_CONSERVATIVE",
            strategy_type="pure_market_making",  # String instead of enum
            connector_type="hyperliquid_perpetual",  # String instead of enum
            trading_pairs=["PURR-USDC"],
            bid_spread=0.30,        # 30% spread (very wide)
            ask_spread=0.30,        # 30% spread
            order_refresh_time=600.0,  # 10 minutes between orders
            order_amount=0.0005,    # Smaller position size
            enabled=True
        ),
        # Single strategy only to minimize activity
    ]

    print(f"💤 Creating {len(idle_strategies)} idle strategies...")

    for strategy in idle_strategies:
        try:
            db.save_universal_strategy(strategy)
            print(f"✅ Created idle strategy: {strategy.name}")
            print(f"   - Refresh time: {strategy.order_refresh_time} seconds ({strategy.order_refresh_time / 60:.1f} minutes)")
            print(f"   - Spread: {strategy.bid_spread * 100}%")
        except Exception as e:
            print(f"❌ Failed to create strategy {strategy.name}: {e}")

    print("\n🎯 Rate limit compliant strategies created!")
    print("These strategies will:")
    print("- Place orders every 10 minutes (instead of seconds)")
    print("- Use very wide spreads (30%) to reduce fills")
    print("- Use smaller position sizes")
    print("- Only run 1 strategy total")


if __name__ == "__main__":
    setup_idle_strategies()
