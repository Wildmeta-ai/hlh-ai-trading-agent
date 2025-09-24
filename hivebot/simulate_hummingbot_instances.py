#!/usr/bin/env python
"""
Simulate 3 Hummingbot instances for performance comparison.
Each instance mimics the resource usage pattern of a real Hummingbot instance.
"""

import math
import random
import threading
import time
from multiprocessing import Process


def simulate_market_data_processing():
    """Simulate continuous market data processing"""
    while True:
        # Simulate order book processing
        order_book = [[random.random() * 100, random.random() * 10] for _ in range(50)]
        sorted_book = sorted(order_book, key=lambda x: x[0])

        # Simulate price calculations
        mid_price = sum([x[0] for x in sorted_book[:10]]) / 10
        spread = sorted_book[-1][0] - sorted_book[0][0]

        # Simulate strategy calculations
        for _ in range(100):
            calc = random.gauss(mid_price, spread / 10)

        time.sleep(0.1)  # 10 updates per second


def simulate_order_management():
    """Simulate order placement and management"""
    orders = {}
    order_id = 0

    while True:
        # Create new orders
        if random.random() > 0.7:
            order_id += 1
            orders[order_id] = {
                'price': random.random() * 100000,
                'amount': random.random() * 0.1,
                'side': random.choice(['buy', 'sell']),
                'timestamp': time.time()
            }

        # Update existing orders
        for oid in list(orders.keys()):
            if random.random() > 0.8:
                orders[oid]['price'] *= (1 + random.uniform(-0.001, 0.001))

            # Cancel old orders
            if time.time() - orders[oid]['timestamp'] > 30:
                del orders[oid]

        # Simulate order book matching
        active_orders = list(orders.values())
        if len(active_orders) > 0:
            best_bid = max([o['price'] for o in active_orders if o['side'] == 'buy'], default=0)
            best_ask = min([o['price'] for o in active_orders if o['side'] == 'sell'], default=float('inf'))

        time.sleep(0.5)  # Update every 500ms


def simulate_websocket_connections():
    """Simulate WebSocket connection handling"""
    buffer = []

    while True:
        # Simulate receiving messages
        for _ in range(random.randint(1, 10)):
            msg = {
                'type': random.choice(['trade', 'orderbook', 'ticker']),
                'data': [random.random() for _ in range(10)],
                'timestamp': time.time()
            }
            buffer.append(msg)

        # Process buffer
        if len(buffer) > 100:
            buffer = buffer[-50:]  # Keep last 50 messages

        # Simulate parsing and processing
        for msg in buffer[-10:]:
            processed = str(msg).encode('utf-8')
            decoded = processed.decode('utf-8')

        time.sleep(0.2)  # Process every 200ms


def simulate_database_operations():
    """Simulate database read/write operations"""
    trade_history = []

    while True:
        # Simulate trade recording
        if random.random() > 0.9:
            trade = {
                'id': len(trade_history),
                'price': random.random() * 100000,
                'amount': random.random() * 0.1,
                'timestamp': time.time(),
                'profit': random.uniform(-10, 10)
            }
            trade_history.append(trade)

        # Simulate performance calculations
        if len(trade_history) > 0:
            total_profit = sum([t['profit'] for t in trade_history])
            avg_profit = total_profit / len(trade_history)

        # Clean old trades
        if len(trade_history) > 1000:
            trade_history = trade_history[-500:]

        time.sleep(1.0)  # Update every second


def run_hummingbot_instance(instance_name, strategy_params):
    """Run a simulated Hummingbot instance"""
    print(f"Starting simulated {instance_name} instance...")

    # Start background threads for different components
    threads = [
        threading.Thread(target=simulate_market_data_processing, daemon=True),
        threading.Thread(target=simulate_order_management, daemon=True),
        threading.Thread(target=simulate_websocket_connections, daemon=True),
        threading.Thread(target=simulate_database_operations, daemon=True)
    ]

    for t in threads:
        t.start()

    # Main loop - simulate strategy execution
    print(f"{instance_name} instance running...")
    start_time = time.time()

    while True:
        # Simulate main strategy loop
        current_time = time.time()
        elapsed = current_time - start_time

        # Simulate strategy calculations based on parameters
        bid_spread = strategy_params['bid_spread']
        ask_spread = strategy_params['ask_spread']
        refresh_time = strategy_params['refresh_time']

        # Do some CPU-intensive calculations
        for _ in range(int(1000 / refresh_time)):
            calculation = random.gauss(100000, 1000)
            adjusted = calculation * (1 + bid_spread) * (1 - ask_spread)
            # Add more CPU work
            for i in range(100):
                _ = math.sqrt(adjusted + i)

        # Print status every 30 seconds
        if int(elapsed) % 30 == 0 and int(elapsed) > 0:
            print(f"{instance_name}: Running for {int(elapsed)}s")

        time.sleep(refresh_time)


if __name__ == "__main__":
    # Define strategy parameters for each instance
    strategies = {
        "MEDIUM": {
            'bid_spread': 0.0005,
            'ask_spread': 0.0005,
            'refresh_time': 5.0
        },
        "SCALPER": {
            'bid_spread': 0.0002,
            'ask_spread': 0.0002,
            'refresh_time': 2.0
        },
        "CONSERVATIVE": {
            'bid_spread': 0.0015,
            'ask_spread': 0.0015,
            'refresh_time': 15.0
        }
    }

    # Start 3 instances as separate processes
    processes = []

    for name, params in strategies.items():
        p = Process(target=run_hummingbot_instance, args=(name, params))
        p.start()
        processes.append(p)
        print(f"Started {name} with PID: {p.pid}")
        time.sleep(2)  # Stagger startup

    print("\n✅ All 3 simulated Hummingbot instances started!")
    print("These will run continuously to simulate resource usage.")
    print("\nYou can now run the performance comparison tool.")
    print("\nPress Ctrl+C to stop all instances...")

    try:
        # Keep running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nStopping all instances...")
        for p in processes:
            p.terminate()
        for p in processes:
            p.join()
        print("✅ All instances stopped.")
