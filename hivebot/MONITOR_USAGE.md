# 🐝 Hive Terminal Monitor Usage Guide

## Overview

The Hive Terminal Monitor provides real-time visual feedback on your Dynamic Hive trading system with a grid-based terminal interface, pixel indicators for activity, and blinking effects for recent actions.

## Features

### 📊 Visual Components
- **Grid Layout**: Each strategy gets its own cell with detailed metrics
- **Pixel Indicators**: 24 pixels per strategy showing recent activity history
- **Color Coding**: Green (success), Red (failure), Yellow (waiting), Blue (info)
- **Blinking Effects**: Recent activity blinks to draw attention
- **Real-time Updates**: Live market data and order status

### 🎮 Interactive Controls
- **Q**: Quit monitor
- **R**: Reload strategies from database
- **Real-time refresh**: Updates every 100ms

## Usage Methods

### Method 1: Integrated with Hive System

Run the main Hive system and enable monitoring when prompted:

```bash
# Set environment variable for auto-enable (optional)
export HIVE_ENABLE_MONITOR=true
export HIVE_AUTO_TRADE=true

# Run Hive system
source ~/miniconda3/bin/activate hummingbot
python hive_dynamic_core.py
```

When prompted:
- `📊 Enable terminal monitor? (y/N):` → Type `y`
- System will start background monitoring

### Method 2: Standalone Monitor

For testing or monitoring existing data:

```bash
# Run standalone monitor
python hive_terminal_monitor.py
```

### Method 3: Dual Terminal Setup

**Terminal 1 (Trading System):**
```bash
export HIVE_AUTO_TRADE=true
export HIVE_ENABLE_MONITOR=true
python hive_dynamic_core.py
```

**Terminal 2 (Monitor Display):**
```bash
python hive_terminal_monitor.py
```

## Monitor Display Layout

```
🐝 DYNAMIC HIVE MONITOR                    ⏰ 14:25:30
📡 BTC-USD $112985.50 | CONNECTED         ⚡ Strategies: 3/3 active
================================================================================

┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ CONSERVATIVE     │  │ MEDIUM           │  │ SCALPER          │
│ ● 15s    20.5/min│  │ ● 5s     45.2/min│  │ ● 2s     85.1/min│
│ █ █ ▓ ▒ ░ · · ·  │  │ █ █ █ █ ▓ ▒ ░ ·  │  │ █ █ █ █ █ █ █ █  │
│ █ ▓ ▒ ░ · · · ·  │  │ █ █ ▓ ▓ ▒ ░ · ·  │  │ █ █ █ ▓ ▓ ▒ ▒ ░  │
│ ▓ ▒ ░ · · · · ·  │  │ █ ▓ ▒ ░ · · · ·  │  │ █ █ ▓ ▓ ▒ ▒ ░ ·  │
│ ✓ 45 ✗ 3  Σ 48  │  │ ✓123 ✗ 8  Σ131  │  │ ✓287 ✗12  Σ299  │
└──────────────────┘  └──────────────────┘  └──────────────────┘

================================================================================
📋 RECENT ACTIVITY
14:25:28 ✓    SCALPER BUY_ORDER
14:25:26 ✓     MEDIUM SELL_ORDER
14:25:25 ✗    SCALPER BUY_ORDER
14:25:23 ✓ CONSERVATIVE SELL_ORDER
14:25:21 ✓    SCALPER BUY_ORDER

Press 'Q' to quit, 'R' to reload strategies
```

## Pixel Indicator Legend

### Symbols
- `█` Full block: Very recent activity (0-10 seconds)
- `▓` Dark shade: Recent activity (10-30 seconds)
- `▒` Medium shade: Older activity (30-60 seconds)
- `░` Light shade: Old activity (60+ seconds)
- `·` Dot: No activity for this slot

### Colors
- **Green**: Successful orders
- **Red**: Failed orders  
- **Yellow**: Waiting/Warning states
- **Blue**: Information/Status
- **Blinking**: Activity within last 5 seconds

## Strategy Cell Information

Each strategy cell shows:
- **Name**: Strategy identifier (CONSERVATIVE, MEDIUM, SCALPER)
- **Status**: ● (Active), ○ (Waiting), ◦ (Idle), ✗ (Error)
- **Refresh Rate**: Time interval between actions (e.g., 15s, 5s, 2s)
- **Performance**: Actions per minute rate
- **Pixel Grid**: 3x8 grid of recent activity indicators
- **Statistics**: ✓ Successful, ✗ Failed, Σ Total actions

## Environment Variables

Control monitor behavior with environment variables:

```bash
# Auto-enable monitor (skip prompt)
export HIVE_ENABLE_MONITOR=true

# Auto-enable trading (skip prompt)  
export HIVE_AUTO_TRADE=true

# Monitor database path
export HIVE_DB_PATH="custom_hive_strategies.db"
```

## Performance Considerations

The monitor is designed for minimal performance impact:
- **Low CPU Usage**: Efficient terminal rendering
- **Memory Efficient**: Limited history buffers
- **Background Operation**: Runs in separate thread
- **Configurable Updates**: Adjustable refresh rates

## Troubleshooting

### Common Issues

**Monitor not starting:**
```bash
# Check if terminal supports colors
python -c "import curses; print(curses.has_colors())"

# Run with error details
python hive_terminal_monitor.py 2>&1
```

**No activity showing:**
- Ensure strategies are active in database
- Check that trading is enabled
- Verify connector connectivity

**Display corruption:**
- Resize terminal window
- Press 'R' to refresh
- Restart monitor

**Colors not working:**
- Use modern terminal (Terminal.app, iTerm2, etc.)
- Check terminal color support
- Set TERM environment variable

### Terminal Requirements

- **Minimum Size**: 80x25 characters
- **Color Support**: 8+ colors preferred
- **Unicode Support**: For best symbol display
- **Modern Terminal**: Terminal.app, iTerm2, gnome-terminal

## Integration Examples

### Custom Activity Tracking

```python
from hive_terminal_monitor import HiveMonitorIntegration

# Initialize monitor
monitor = HiveMonitorIntegration()
monitor.start_background_monitor()

# Update activity
monitor.update_activity("MY_STRATEGY", "CUSTOM_ACTION", success=True)
monitor.update_market_data("BTC-USD", 45000.0, connected=True)
```

### API Integration

Monitor data can be accessed via the existing REST API:

```bash
# Get strategy status
curl http://localhost:8080/api/strategies

# Get strategy performance
curl http://localhost:8080/api/strategies/SCALPER
```

## Advanced Usage

### Multiple Trading Pairs
The monitor can track multiple trading pairs by updating market data:

```python
monitor.update_market_data("ETH-USD", 2500.0, True)
monitor.update_market_data("SOL-USD", 100.0, True)
```

### Custom Strategy Types
Add new strategies to the database and they'll appear automatically:

```sql
INSERT INTO strategies (name, refresh_interval, is_active) 
VALUES ('HIGH_FREQ', 0.5, 1);
```

### Historical Analysis
The monitor keeps recent activity history for analysis:
- Last 10 actions per strategy
- Last 50 global actions
- Performance calculations
- Success/failure rates

This monitoring system provides comprehensive visibility into your Dynamic Hive operations with minimal performance overhead and rich visual feedback.