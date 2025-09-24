#!/usr/bin/env python3
"""
Clean up old aggressive strategies and enable only idle ones
"""

import sqlite3
import sys

sys.path.append('.')


def clean_strategies():
    """Disable old strategies and enable only idle ones."""

    # Connect directly to database
    db_path = "hive_strategies.db"

    with sqlite3.connect(db_path) as conn:
        # First, check what strategies exist
        cursor = conn.cursor()
        cursor.execute("SELECT name, enabled, order_refresh_time FROM universal_strategy_configs")
        strategies = cursor.fetchall()

        print("🔍 Current strategies in database:")
        for name, enabled, refresh_time in strategies:
            status = "ENABLED" if enabled else "DISABLED"
            print(f"  - {name}: {status} (refresh: {refresh_time}s)")

        # Disable all old aggressive strategies
        aggressive_strategies = ['CONSERVATIVE', 'WIDE', 'PMM_CONSERVATIVE', 'PMM_AGGRESSIVE', 'PMM_MODERATE', 'AVELLANEDA_BTC']

        print(f"\n🛑 Disabling {len(aggressive_strategies)} aggressive strategies...")
        for strategy_name in aggressive_strategies:
            cursor.execute(
                "UPDATE universal_strategy_configs SET enabled = 0 WHERE name = ?",
                (strategy_name,)
            )
            print(f"   ❌ Disabled: {strategy_name}")

        # Enable only idle strategies
        cursor.execute(
            "UPDATE universal_strategy_configs SET enabled = 1 WHERE name = ?",
            ("IDLE_CONSERVATIVE",)
        )
        print(f"   ✅ Enabled: IDLE_CONSERVATIVE")

        conn.commit()

        # Show final state
        cursor.execute("SELECT name, enabled, order_refresh_time FROM universal_strategy_configs WHERE enabled = 1")
        enabled_strategies = cursor.fetchall()

        print(f"\n🎯 Active strategies after cleanup:")
        for name, enabled, refresh_time in enabled_strategies:
            print(f"  ✅ {name}: {refresh_time}s refresh ({refresh_time / 60:.1f} minutes)")

        print(f"\n💤 Ready for rate-limit compliant trading!")


if __name__ == "__main__":
    clean_strategies()
