#!/usr/bin/env python
"""
Start 3 simple Hummingbot instances for performance comparison
Uses minimal configuration to avoid authentication issues
"""

import asyncio
import os
import sys
import time
from multiprocessing import Process

# Add hummingbot to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hummingbot.connector.exchange.hyperliquid.hyperliquid_exchange import HyperliquidExchange
from hummingbot.core.clock import Clock
from hummingbot.strategy.pure_market_making import PureMarketMakingStrategy


def run_instance(instance_name, bid_spread, ask_spread, order_amount, refresh_time):
    """Run a single Hummingbot instance with given parameters"""
    try:
        async def main():
            print(f"Starting {instance_name}...")

            # Create connector
            connector = HyperliquidExchange(
                client_config_map={},
                hyperliquid_api_key="",
                hyperliquid_api_secret="",
                use_vault=False,
                vault_address=None,
                trading_required=False
            )

            # Initialize connector
            await connector._update_trading_rules()

            # Create strategy
            strategy = PureMarketMakingStrategy()
            strategy.init_params(
                market_info={},
                bid_spread=bid_spread,
                ask_spread=ask_spread,
                order_amount=order_amount,
                order_refresh_time=refresh_time,
                max_order_age=30.0,
                order_refresh_tolerance_pct=0.025,
                minimum_spread=0.001,
                order_levels=1,
                order_level_amount=0,
                order_level_spread=0.01,
                inventory_skew_enabled=False,
                inventory_target_base_pct=0.5,
                inventory_range_multiplier=1.0,
                filled_order_delay=60.0,
                hanging_orders_enabled=False,
                order_optimization_enabled=False,
                add_transaction_costs_to_orders=True,
                price_ceiling=-1,
                price_floor=-1,
                ping_pong_enabled=False,
                moving_price_band_enabled=False,
                price_band_refresh_time=None,
                price_band_std_dev_period=None,
                price_band_move_std_dev_multiplier=None,
                take_if_crossed=False,
                price_source="current_market",
                price_type="mid_price",
                price_source_exchange=None,
                price_source_market=None,
                price_source_custom_api=None,
                custom_api_update_interval=5.0,
                order_override=None,
                split_order_levels_enabled=False,
                bid_order_level_spreads=None,
                ask_order_level_spreads=None,
                should_wait_order_cancel_confirmation=True,
                converter=None
            )

            # Create clock
            clock = Clock()
            clock.add_iterator(connector)
            clock.add_iterator(strategy)

            # Run for performance test duration
            print(f"{instance_name} running...")
            start_time = time.time()
            while time.time() - start_time < 300:  # Run for 5 minutes
                clock.tick()
                await asyncio.sleep(1.0)

            print(f"{instance_name} completed")

        asyncio.run(main())

    except Exception as e:
        print(f"Error in {instance_name}: {e}")


if __name__ == "__main__":
    # Start 3 instances as separate processes
    processes = []

    # Instance 1: MEDIUM
    p1 = Process(target=run_instance, args=("MEDIUM", 0.0005, 0.0005, 0.001, 5.0))
    p1.start()
    processes.append(p1)
    print(f"Started MEDIUM instance with PID: {p1.pid}")

    time.sleep(2)

    # Instance 2: SCALPER
    p2 = Process(target=run_instance, args=("SCALPER", 0.0002, 0.0002, 0.001, 2.0))
    p2.start()
    processes.append(p2)
    print(f"Started SCALPER instance with PID: {p2.pid}")

    time.sleep(2)

    # Instance 3: CONSERVATIVE
    p3 = Process(target=run_instance, args=("CONSERVATIVE", 0.0015, 0.0015, 0.02, 15.0))
    p3.start()
    processes.append(p3)
    print(f"Started CONSERVATIVE instance with PID: {p3.pid}")

    print("\n✅ All 3 instances started!")
    print(f"PIDs: {p1.pid}, {p2.pid}, {p3.pid}")
    print("\nInstances will run for 5 minutes for performance testing...")

    # Wait for all to complete
    for p in processes:
        p.join()

    print("\n✅ All instances completed")
