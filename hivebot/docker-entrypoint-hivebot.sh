#!/bin/bash

# Activate conda environment
source ~/miniconda3/bin/activate hummingbot

# Clear any existing strategies from database if requested
if [ "$HIVE_STRATEGIES" = "0" ]; then
    echo "Starting with 0 strategies - clearing strategy database..."
    rm -f /app/hummingbot/hive_strategies.db
fi

# Run hivebot with specified port
echo "Starting hivebot on port ${HIVE_PORT:-8082}..."
python hive_dynamic_core_modular.py --trading --port ${HIVE_PORT:-8082}
