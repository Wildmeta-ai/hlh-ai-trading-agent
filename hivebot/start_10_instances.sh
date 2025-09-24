#!/bin/bash

# Start 10 separate Python processes that can be tracked
echo "Starting 10 Hummingbot simulator instances..."

# Create a simple simulator script
cat > /tmp/hbot_sim.py << 'EOF'
import sys
import time
import random

# Get instance number from command line
instance_num = sys.argv[1] if len(sys.argv) > 1 else "1"

# Allocate memory (simulate Hummingbot memory usage)
memory_buffer = []
for _ in range(150):  # ~150MB per instance
    memory_buffer.append(bytearray(1024 * 1024))

print(f"Hummingbot instance {instance_num} started")

# Keep running
while True:
    # Simulate some work
    for _ in range(100):
        x = random.random() * 1000
        y = x * 2.5 + random.gauss(0, 10)
    time.sleep(1)
EOF

# Start 10 instances
for i in {1..10}; do
    python /tmp/hbot_sim.py $i > /tmp/hbot_$i.log 2>&1 &
    echo "Started instance $i with PID $!"
    sleep 0.5
done

echo "All 10 instances started"
echo "They can be found with: ps aux | grep hbot_sim"
