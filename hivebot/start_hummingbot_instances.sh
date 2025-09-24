#!/bin/bash

# Script to start 3 separate Hummingbot instances for performance comparison
# Each instance runs in background with its own config

echo "🚀 Starting 3 Hummingbot instances for performance comparison..."

# Activate conda environment
source /Users/yoshiyuki/miniconda3/bin/activate hummingbot

# Create log directory if it doesn't exist
mkdir -p logs/hummingbot_instances

# Start Instance 1 - MEDIUM strategy
echo "Starting Instance 1 (MEDIUM strategy)..."
nohup python bin/hummingbot_quickstart.py \
    --config-file-name hummingbot_instance1_medium.yml \
    --headless \
    --config-password test_password \
    > logs/hummingbot_instances/instance1_medium.log 2>&1 &
INSTANCE1_PID=$!
echo "Instance 1 started with PID: $INSTANCE1_PID"

# Give it time to initialize
sleep 3

# Start Instance 2 - SCALPER strategy
echo "Starting Instance 2 (SCALPER strategy)..."
nohup python bin/hummingbot_quickstart.py \
    --config-file-name hummingbot_instance2_scalper.yml \
    --headless \
    --config-password test_password \
    > logs/hummingbot_instances/instance2_scalper.log 2>&1 &
INSTANCE2_PID=$!
echo "Instance 2 started with PID: $INSTANCE2_PID"

# Give it time to initialize
sleep 3

# Start Instance 3 - CONSERVATIVE strategy
echo "Starting Instance 3 (CONSERVATIVE strategy)..."
nohup python bin/hummingbot_quickstart.py \
    --config-file-name hummingbot_instance3_conservative.yml \
    --headless \
    --config-password test_password \
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
