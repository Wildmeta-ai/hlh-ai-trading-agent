#!/usr/bin/env python
"""
Simulate exactly 10 Hummingbot instances for fair comparison.
Each instance represents one strategy running in its own process.
This matches the 10 strategies configured in Hivebot.
"""

import math
import os
import random
import threading
import time
from multiprocessing import Process


def simulate_hummingbot_instance(instance_name, strategy_type):
    """
    Simulate a single Hummingbot instance with realistic resource usage.
    Each instance would typically use 150-250MB RAM.
    """

    # Allocate memory to simulate Hummingbot's memory footprint
    memory_buffer = []

    # Base memory allocation (simulate libraries, framework, etc.)
    # Each instance loads its own copy: ~100-150MB base
    base_memory_mb = 100 + random.randint(0, 50)
    for _ in range(base_memory_mb):
        chunk = bytearray(1024 * 1024)  # 1MB chunks
        memory_buffer.append(chunk)

    # Simulate order book data structure
    order_book = {
        'bids': [[random.random() * 100000, random.random()] for _ in range(100)],
        'asks': [[random.random() * 100000, random.random()] for _ in range(100)]
    }

    # Simulate strategy state
    strategy_state = {
        'positions': {},
        'orders': {},
        'trades': [],
        'performance_metrics': {},
        'config': {'type': strategy_type}
    }

    print(f"[{instance_name}] Started - Strategy: {strategy_type}")

    # Define strategy behavior based on type
    refresh_rates = {
        'MICRO': 0.2,
        'TIGHT': 0.5,
        'AGGRESSIVE': 1.0,
        'SCALPER': 2.0,
        'FAST': 3.0,
        'MEDIUM': 5.0,
        'BALANCED': 8.0,
        'SLOW': 12.0,
        'CONSERVATIVE': 15.0,
        'WIDE': 20.0
    }

    refresh_time = refresh_rates.get(strategy_type, 5.0)

    while True:
        # Simulate market data processing
        for _ in range(10):
            mid_price = (order_book['bids'][0][0] + order_book['asks'][0][0]) / 2
            spread = order_book['asks'][0][0] - order_book['bids'][0][0]

            # Strategy calculations based on type
            calculation_intensity = int(100 / refresh_time)
            for _ in range(calculation_intensity):
                calc = random.gauss(mid_price, spread / 50)
                # Some CPU work
                for i in range(10):
                    _ = math.sqrt(abs(calc) + i)

        # Update order book (simulate market data updates)
        order_book['bids'] = [[p * (1 + random.uniform(-0.0001, 0.0001)), v]
                              for p, v in order_book['bids']]
        order_book['asks'] = [[p * (1 + random.uniform(-0.0001, 0.0001)), v]
                              for p, v in order_book['asks']]

        # Simulate order management
        if random.random() > 0.7:
            order_id = f"{instance_name}_{len(strategy_state['orders'])}"
            strategy_state['orders'][order_id] = {
                'price': mid_price * (1 + random.uniform(-0.001, 0.001)),
                'amount': 0.001,
                'side': random.choice(['buy', 'sell']),
                'timestamp': time.time()
            }

        # Clean old orders
        for oid in list(strategy_state['orders'].keys()):
            if time.time() - strategy_state['orders'][oid]['timestamp'] > 30:
                del strategy_state['orders'][oid]

        # Memory growth simulation (caching, history, etc.)
        if len(memory_buffer) < base_memory_mb + 100:  # Cap growth at +100MB
            if random.random() > 0.95:
                memory_buffer.append(bytearray(1024 * 512))  # 512KB

        time.sleep(refresh_time)


if __name__ == "__main__":
    print("=" * 60)
    print("Starting 10 Hummingbot instances for scaled comparison")
    print("Each instance simulates a separate Hummingbot process")
    print("=" * 60)
    print("")

    processes = []

    # Start exactly 10 instances matching the 10 strategies in Hivebot
    strategies = [
        ("Hummingbot_01", "MICRO"),
        ("Hummingbot_02", "TIGHT"),
        ("Hummingbot_03", "AGGRESSIVE"),
        ("Hummingbot_04", "SCALPER"),
        ("Hummingbot_05", "FAST"),
        ("Hummingbot_06", "MEDIUM"),
        ("Hummingbot_07", "BALANCED"),
        ("Hummingbot_08", "SLOW"),
        ("Hummingbot_09", "CONSERVATIVE"),
        ("Hummingbot_10", "WIDE")
    ]

    print("Starting instances:")
    for name, strategy_type in strategies:
        p = Process(target=simulate_hummingbot_instance, args=(name, strategy_type))
        p.start()
        processes.append(p)
        print(f"  ✓ {name} (PID: {p.pid}) - {strategy_type} strategy")
        time.sleep(0.5)  # Stagger startup

    print("")
    print("=" * 60)
    print("✅ All 10 Hummingbot instances running")
    print("These simulate the resource usage of 10 separate processes")
    print("=" * 60)
    print("\nPress Ctrl+C to stop...")

    try:
        while True:
            time.sleep(30)
            alive_count = sum(1 for p in processes if p.is_alive())
            print(f"[Status] {alive_count}/10 instances running")
    except KeyboardInterrupt:
        print("\nStopping all instances...")
        for p in processes:
            p.terminate()
        for p in processes:
            p.join()
        print("✅ All instances stopped")
