#!/bin/bash
source ~/.bashrc
export PATH="/home/ubuntu/miniconda3/bin:$PATH"
source /home/ubuntu/miniconda3/etc/profile.d/conda.sh
conda activate hummingbot
cd /home/ubuntu/hummingbot
# HYPERLIQUID_PRIVATE_KEY should be set in the environment before running this script
python hive_dynamic_core_modular.py --monitor --port 8080 --dashboard-url http://15.235.212.36:8091 --network testnet
