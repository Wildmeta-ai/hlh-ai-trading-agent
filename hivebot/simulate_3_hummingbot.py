#!/usr/bin/env python
"""
Simulate exactly 3 Hummingbot instances for fair comparison.
Each instance represents one strategy running in its own process.
"""

import json
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

    # Allocate some memory to simulate Hummingbot's memory footprint
    # Each instance loads its own copy of libraries, market data, etc.
    memory_buffer = []

    # Simulate loading libraries and initial data (about 100MB base)
    for _ in range(100):
        chunk = bytearray(1024 * 1024)  # 1MB chunks
        memory_buffer.append(chunk)

    # Simulate order book data
    order_book = {
        'bids': [[random.random() * 100000, random.random()] for _ in range(100)],
        'asks': [[random.random() * 100000, random.random()] for _ in range(100)]
    }

    # Simulate strategy state
    strategy_state = {
        'positions': {},
        'orders': {},
        'trades': [],
        'metrics': {}
    }

    print(f"[{instance_name}] Started - Strategy: {strategy_type}")

    while True:
        # Simulate market data processing
        for _ in range(10):
            mid_price = (order_book['bids'][0][0] + order_book['asks'][0][0]) / 2
            spread = order_book['asks'][0][0] - order_book['bids'][0][0]

            # Strategy-specific calculations
            if strategy_type == "SCALPER":
                # Fast calculations, more frequent
                for _ in range(50):
                    calc = random.gauss(mid_price, spread / 100)
                time.sleep(0.1)
            elif strategy_type == "MEDIUM":
                # Medium frequency
                for _ in range(30):
                    calc = random.gauss(mid_price, spread / 50)
                time.sleep(0.5)
            else:  # CONSERVATIVE
                # Slower, less frequent
                for _ in range(10):
                    calc = random.gauss(mid_price, spread / 20)
                time.sleep(1.0)

        # Update order book
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

        # Add some memory pressure
        if len(memory_buffer) < 200:  # Cap at ~200MB
            memory_buffer.append(bytearray(1024 * 512))  # 512KB


if __name__ == "__main__":
    print("Starting 3 Hummingbot instances for fair comparison...")
    print("Each instance simulates a separate Hummingbot process with one strategy")
    print("")

    processes = []

    # Start exactly 3 instances matching the 3 strategies in Hivebot
    strategies = [
        ("Hummingbot_1", "MEDIUM"),
        ("Hummingbot_2", "SCALPER"),
        ("Hummingbot_3", "CONSERVATIVE")
    ]

    for name, strategy_type in strategies:
        p = Process(target=simulate_hummingbot_instance, args=(name, strategy_type))
        p.start()
        processes.append(p)
        print(f"Started {name} (PID: {p.pid}) - {strategy_type} strategy")
        time.sleep(1)  # Stagger startup

    print("\n✅ All 3 Hummingbot instances running")
    print("These simulate the resource usage of 3 separate Hummingbot processes")
    print("\nPress Ctrl+C to stop...")

    try:
        while True:
            time.sleep(10)
            print(f"[Status] 3 instances running - PIDs: {[p.pid for p in processes]}")
    except KeyboardInterrupt:
        print("\nStopping all instances...")
        for p in processes:
            p.terminate()
        for p in processes:
            p.join()
        print("✅ All instances stopped")
