# Hive Performance Comparison Guide

This guide shows how to use the independent performance monitor to fairly compare resource usage between Hivebot (1:N architecture) and original Hummingbot (1:1 architecture) by aggregating multiple Hummingbot instances.

## Quick Start

### 1. Monitor Current Hivebot System
```bash
# Monitor the running Hivebot system
python hive_performance_monitor.py --hive "hive_dynamic_core" --duration 10 --output "hivebot_performance.json"
```

### 2. Set Up Original Hummingbot for Comparison
```bash
# In a separate terminal, run original Hummingbot with 3 separate instances
# (This simulates the traditional 1:1 architecture)

# Terminal 1: Hummingbot instance 1
./bin/hummingbot.py

# Terminal 2: Hummingbot instance 2
./bin/hummingbot.py

# Terminal 3: Hummingbot instance 3
./bin/hummingbot.py
```

### 3. Monitor Original Hummingbot System
```bash
# Monitor all 3 Hummingbot processes
python hive_performance_monitor.py --hummingbot "hummingbot" --duration 10 --output "hummingbot_performance.json"
```

### 4. Fair Comparison (RECOMMENDED)
```bash
# Fair comparison: 1 Hivebot process vs ALL Hummingbot instances aggregated
python hive_performance_monitor.py \
    --hive "hive_dynamic_core" \
    --hummingbot "hummingbot" \
    --aggregate-hummingbot \
    --duration 15 \
    --interval 5 \
    --output "fair_comparison.json" \
    --verbose
```

### 5. Legacy Direct Comparison (Single Process vs Single Process)
```bash
# Monitor single instance of each (not recommended for architecture comparison)
python hive_performance_monitor.py \
    --hive "hive_dynamic_core" \
    --hummingbot "hummingbot" \
    --duration 15 \
    --interval 5 \
    --output "single_comparison.json" \
    --verbose
```

## Advanced Usage Examples

### Live Monitoring Dashboard (RECOMMENDED)
```bash
# Show live metrics with aggregation every 3 seconds
python hive_performance_monitor.py \
    --hive "hive_dynamic_core" \
    --hummingbot "hummingbot" \
    --aggregate-hummingbot \
    --interval 3 \
    --live
```

### Live Monitoring (Legacy - Single Instances)
```bash
# Show live metrics for single instances only
python hive_performance_monitor.py \
    --hive "hive_dynamic_core" \
    --hummingbot "hummingbot" \
    --interval 3 \
    --live
```

### Monitor Specific PIDs
```bash
# If you know the exact process IDs
python hive_performance_monitor.py \
    --hive-pid 12345 \
    --hummingbot-pid 67890 \
    --duration 30
```

### Extended Performance Test (RECOMMENDED)
```bash
# Long-term fair comparison (1 hour) with aggregation
python hive_performance_monitor.py \
    --hive "hive" \
    --hummingbot "hummingbot" \
    --aggregate-hummingbot \
    --duration 60 \
    --interval 10 \
    --output "extended_fair_comparison.json"
```

## Key Metrics Tracked

### System Resources
- **CPU Usage**: Average, peak, and minimum CPU percentage
- **Memory Usage**: RAM consumption in MB and percentage
- **Process Count**: Number of instances and child processes
- **Thread Count**: Total threads created by each system
- **File Handles**: Number of open file descriptors
- **Instance Aggregation**: Total resource usage across multiple processes (NEW)

### Performance Comparisons
- **CPU Efficiency**: Which architecture uses less CPU total
- **Memory Efficiency**: Which architecture uses less RAM total
- **Process Overhead**: 1:N vs 1:1 architecture efficiency
- **Scalability**: Resource usage per strategy across architectures
- **Fair Comparison**: Single Hivebot process vs aggregated Hummingbot instances

## Expected Results (With Aggregation)

### Hivebot Advantages (1:N Architecture)
- ✅ **Lower CPU usage** - Single process handling multiple strategies
- ✅ **Lower memory footprint** - Shared resources and single connector
- ✅ **Fewer processes** - One process vs multiple instances
- ✅ **Better resource efficiency** - Shared market data and connections
- ✅ **Linear scaling** - Resource usage grows sub-linearly with strategies

### Traditional Hummingbot (1:1 Architecture, Aggregated)
- ❌ **Higher CPU usage** - Multiple separate processes (now properly measured)
- ❌ **Higher memory usage** - Duplicated resources per strategy (aggregated total)
- ❌ **More processes** - N separate instances for N strategies
- ❌ **Resource duplication** - Multiple connectors and market data feeds
- ❌ **Linear scaling** - Resource usage grows linearly with each new instance

### Why Aggregation Matters
With 100 strategies:
- **Hivebot**: 1 process consuming X CPU and Y RAM
- **Hummingbot**: 100 processes consuming 100×X CPU and 100×Y RAM (now properly measured)

## Sample Output (With Aggregation)
```
📈 PERFORMANCE SUMMARY
==================================================
Processes monitored: 2
Total CPU usage: 15.8%
Total memory usage: 245.2MB
Monitoring duration: 15 minutes

🔸 HIVEBOT
   PID: 12345 | CPU: 8.5% | RAM: 128.4MB (2.1%) | Threads: 45 | Children: 2

🔸 HUMMINGBOT
   Instances: 3 | CPU: 24.3% | RAM: 387.6MB (6.4%) | Threads: 135 | Children: 9

🆚 PERFORMANCE COMPARISON
==================================================

HIVEBOT VS HUMMINGBOT (AGGREGATED):
  CPU Advantage: HIVEBOT (15.8% savings)
  Memory Advantage: HIVEBOT (259.2MB savings)
  Process Efficiency: HIVEBOT (1 vs 3 instances)
  Scalability Advantage: HIVEBOT (sub-linear resource growth)
```

## Interpreting Results

### CPU Efficiency
- Lower percentage = better efficiency
- Look for consistent low usage, not just peaks
- Consider CPU per strategy (total CPU ÷ number of strategies)

### Memory Efficiency
- Lower MB usage = better efficiency
- Check both RSS (physical) and VMS (virtual) memory
- Memory per strategy is key metric

### Process Efficiency
- Fewer child processes = better architecture
- Single process handling multiple strategies shows efficiency
- Thread count should scale better in 1:N architecture

## Troubleshooting

### Monitor Not Finding Processes
```bash
# List all processes to find exact names
ps aux | grep -i hummingbot
ps aux | grep -i hive

# Use exact process name found
python hive_performance_monitor.py --hive "exact_process_name"
```

### No Data Collected
- Ensure processes are running during monitoring period
- Check process permissions (may need sudo for some metrics)
- Verify process names match running processes
- **For Hummingbot aggregation**: Ensure multiple instances are running

### Comparison Shows No Difference
- **Use --aggregate-hummingbot for fair comparison!**
- Ensure you're comparing equivalent workloads (same number of strategies)
- Run for longer duration (minimum 10 minutes recommended)
- Check that both systems are actively trading/processing
- Verify Hummingbot instances are actually separate processes

### Aggregation Not Working
- Check that multiple Hummingbot instances are running: `ps aux | grep hummingbot`
- Ensure process names match exactly
- Try without specific PID (aggregation requires process name search)

## Integration with CI/CD

```bash
# Automated performance regression testing with fair comparison
python hive_performance_monitor.py \
    --hive "hive" \
    --hummingbot "hummingbot" \
    --aggregate-hummingbot \
    --duration 5 \
    --output "ci_performance.json" && \
python -c "
import json
with open('ci_performance.json') as f:
    data = json.load(f)

    # Get Hivebot metrics
    hivebot_cpu = data['processes']['HIVEBOT']['cpu']['avg_percent']
    hummingbot_cpu = data['processes']['HUMMINGBOT']['cpu']['avg_percent']

    # Ensure Hivebot is more efficient
    if hivebot_cpu >= hummingbot_cpu:
        print(f'❌ Performance regression: Hivebot {hivebot_cpu}% >= Hummingbot {hummingbot_cpu}%')
        exit(1)

    efficiency_gain = ((hummingbot_cpu - hivebot_cpu) / hummingbot_cpu) * 100
    print(f'✅ Performance test passed: {efficiency_gain:.1f}% CPU efficiency gain')
"
```
