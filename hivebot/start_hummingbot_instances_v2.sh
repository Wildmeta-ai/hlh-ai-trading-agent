#!/bin/bash

# Script to start 3 separate Hummingbot instances for performance comparison
# Using standard hummingbot executable with pre-configured strategies

echo "🚀 Starting 3 Hummingbot instances for performance comparison..."

# Activate conda environment
source /Users/yoshiyuki/miniconda3/bin/activate hummingbot

# Create log directory if it doesn't exist
mkdir -p logs/hummingbot_instances

# Start Instance 1 - MEDIUM strategy
echo "Starting Instance 1 (MEDIUM strategy)..."
cat > /tmp/hummingbot_script1.txt << EOF
connect hyperliquid_testnet
config bid_spread 0.05
config ask_spread 0.05
config order_amount 0.001
config order_refresh_time 5.0
config market BTC-USD
import hummingbot_instance1_medium
start
EOF

nohup python bin/hummingbot.py -s /tmp/hummingbot_script1.txt \
    > logs/hummingbot_instances/instance1_medium.log 2>&1 &
INSTANCE1_PID=$!
echo "Instance 1 started with PID: $INSTANCE1_PID"

# Give it time to initialize
sleep 5

# Start Instance 2 - SCALPER strategy
echo "Starting Instance 2 (SCALPER strategy)..."
cat > /tmp/hummingbot_script2.txt << EOF
connect hyperliquid_testnet
config bid_spread 0.02
config ask_spread 0.02
config order_amount 0.001
config order_refresh_time 2.0
config market BTC-USD
import hummingbot_instance2_scalper
start
EOF

nohup python bin/hummingbot.py -s /tmp/hummingbot_script2.txt \
    > logs/hummingbot_instances/instance2_scalper.log 2>&1 &
INSTANCE2_PID=$!
echo "Instance 2 started with PID: $INSTANCE2_PID"

# Give it time to initialize
sleep 5

# Start Instance 3 - CONSERVATIVE strategy
echo "Starting Instance 3 (CONSERVATIVE strategy)..."
cat > /tmp/hummingbot_script3.txt << EOF
connect hyperliquid_testnet
config bid_spread 0.15
config ask_spread 0.15
config order_amount 0.02
config order_refresh_time 15.0
config market BTC-USD
import hummingbot_instance3_conservative
start
EOF

nohup python bin/hummingbot.py -s /tmp/hummingbot_script3.txt \
    > logs/hummingbot_instances/instance3_conservative.log 2>&1 &
INSTANCE3_PID=$!
echo "Instance 3 started with PID: $INSTANCE3_PID"

echo ""
echo "✅ All 3 Hummingbot instances started!"
echo "PIDs: $INSTANCE1_PID, $INSTANCE2_PID, $INSTANCE3_PID"
echo ""
echo "Monitor logs with:"
echo "  tail -f logs/hummingbot_instances/instance1_medium.log"
echo "  tail -f logs/hummingbot_instances/instance2_scalper.log"
echo "  tail -f logs/hummingbot_instances/instance3_conservative.log"
echo ""
echo "Stop all instances with:"
echo "  kill $INSTANCE1_PID $INSTANCE2_PID $INSTANCE3_PID"
