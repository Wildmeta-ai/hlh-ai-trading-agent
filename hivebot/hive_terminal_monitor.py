#!/usr/bin/env python3

"""
🐝 HIVE TERMINAL MONITOR
====================================================================
Real-time terminal-based monitoring system for Dynamic Hive trading

Features:
- Grid-based layout with pixel indicators
- Blinking effects for recent activity
- Color-coded status indicators
- Performance history visualization
- Low-overhead terminal rendering
====================================================================
"""

import curses
import json
import os
import sqlite3
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional, Tuple


@dataclass
class StrategyMetrics:
    """Metrics for a single strategy."""
    name: str
    total_actions: int = 0
    successful_orders: int = 0
    failed_orders: int = 0
    last_action_time: Optional[datetime] = None
    recent_actions: deque = field(default_factory=lambda: deque(maxlen=50))  # Increased to hold more history per strategy
    status: str = "IDLE"  # IDLE, ACTIVE, WAITING, ERROR
    refresh_interval: float = 5.0
    next_action_time: Optional[datetime] = None
    performance_per_min: float = 0.0


@dataclass
class MarketData:
    """Current market data snapshot."""
    symbol: str = "BTC-USD"
    price: float = 0.0
    timestamp: Optional[datetime] = None
    connection_status: str = "DISCONNECTED"


class HiveTerminalMonitor:
    """Terminal-based monitoring system with grid display and pixel indicators."""

    def __init__(self, db_path: str = "hive_strategies.db", live_mode: bool = True):
        self.db_path = db_path
        self.live_mode = live_mode  # Whether to load real data or simulate
        self.monitor_data_file = "hive_monitor_data.json"  # Shared data file
        self.strategies: Dict[str, StrategyMetrics] = {}
        self.market_data = MarketData()
        self.running = False
        self.stdscr = None
        self.blink_phase = 0  # For blinking effects
        self.last_update = time.time()

        # Grid layout configuration
        self.grid_rows = 3
        self.grid_cols = 4
        self.cell_height = 8
        self.cell_width = 20

        # Color pairs (defined in init_colors)
        self.colors = {}

        # Activity tracking for blinking - increase to 200 for better history
        self.recent_activity = deque(maxlen=200)

    def init_colors(self):
        """Initialize color pairs for terminal display."""
        if not curses.has_colors():
            return

        curses.start_color()
        curses.use_default_colors()

        # Define color pairs
        curses.init_pair(1, curses.COLOR_GREEN, -1)    # Success
        curses.init_pair(2, curses.COLOR_RED, -1)      # Error/Failure
        curses.init_pair(3, curses.COLOR_YELLOW, -1)   # Waiting/Warning
        curses.init_pair(4, curses.COLOR_BLUE, -1)     # Info
        curses.init_pair(5, curses.COLOR_MAGENTA, -1)  # Strategy name
        curses.init_pair(6, curses.COLOR_CYAN, -1)     # Market data
        curses.init_pair(7, curses.COLOR_WHITE, -1)    # Default

        # Blinking variants (for activity indicators)
        curses.init_pair(11, curses.COLOR_GREEN, -1)   # Blinking success
        curses.init_pair(12, curses.COLOR_RED, -1)     # Blinking error
        curses.init_pair(13, curses.COLOR_YELLOW, -1)  # Blinking warning

        self.colors = {
            'success': curses.color_pair(1),
            'error': curses.color_pair(2),
            'warning': curses.color_pair(3),
            'info': curses.color_pair(4),
            'strategy': curses.color_pair(5),
            'market': curses.color_pair(6),
            'default': curses.color_pair(7),
            'blink_success': curses.color_pair(11) | curses.A_BLINK,
            'blink_error': curses.color_pair(12) | curses.A_BLINK,
            'blink_warning': curses.color_pair(13) | curses.A_BLINK,
        }

    def load_strategies_from_db(self):
        """Load strategy configurations from database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT name, refresh_interval FROM strategies WHERE is_active = 1")
            strategies = cursor.fetchall()

            for name, refresh_interval in strategies:
                if name not in self.strategies:
                    self.strategies[name] = StrategyMetrics(
                        name=name,
                        refresh_interval=refresh_interval
                    )
                else:
                    self.strategies[name].refresh_interval = refresh_interval

            conn.close()

        except sqlite3.Error:
            # Create dummy strategies for demonstration if DB not available
            if not self.strategies:
                self.strategies = {
                    "CONSERVATIVE": StrategyMetrics("CONSERVATIVE", refresh_interval=15.0),
                    "MEDIUM": StrategyMetrics("MEDIUM", refresh_interval=5.0),
                    "SCALPER": StrategyMetrics("SCALPER", refresh_interval=2.0),
                }

    def update_strategy_activity(self, strategy_name: str, action_type: str, success: bool = True):
        """Update strategy activity with new action."""
        if strategy_name not in self.strategies:
            return

        strategy = self.strategies[strategy_name]
        now = datetime.now()

        # Update metrics
        strategy.total_actions += 1
        strategy.last_action_time = now

        if success:
            strategy.successful_orders += 1
        else:
            strategy.failed_orders += 1

        # Add to recent actions
        strategy.recent_actions.append({
            'time': now,
            'type': action_type,
            'success': success
        })

        # Update status
        strategy.status = "ACTIVE" if success else "ERROR"

        # Calculate performance
        if strategy.last_action_time and strategy.total_actions > 0:
            time_diff = (now - strategy.last_action_time).total_seconds() / 60.0
            if time_diff > 0:
                strategy.performance_per_min = strategy.total_actions / time_diff

        # Add to global activity tracking
        self.recent_activity.append({
            'strategy': strategy_name,
            'action': action_type,
            'success': success,
            'time': now
        })

        # Save to shared file for other monitor instances
        self.save_monitor_data()

    def update_market_data(self, symbol: str, price: float, connected: bool = True):
        """Update market data information."""
        self.market_data.symbol = symbol
        self.market_data.price = price
        self.market_data.timestamp = datetime.now()
        self.market_data.connection_status = "CONNECTED" if connected else "DISCONNECTED"

        # Save to shared file
        self.save_monitor_data()

    def save_monitor_data(self):
        """Save current monitor state to shared file."""
        if not self.live_mode:
            return  # Don't save simulated data

        try:
            # Convert strategies to serializable format
            strategy_data = {}
            for name, strategy in self.strategies.items():
                # Convert recent_actions deque to list with serializable timestamps
                recent_actions = []
                for action in strategy.recent_actions:
                    recent_actions.append({
                        'time': action['time'].isoformat() if action['time'] else None,
                        'type': action['type'],
                        'success': action['success']
                    })

                strategy_data[name] = {
                    'name': strategy.name,
                    'total_actions': strategy.total_actions,
                    'successful_orders': strategy.successful_orders,
                    'failed_orders': strategy.failed_orders,
                    'last_action_time': strategy.last_action_time.isoformat() if strategy.last_action_time else None,
                    'recent_actions': recent_actions,
                    'status': strategy.status,
                    'refresh_interval': strategy.refresh_interval,
                    'performance_per_min': strategy.performance_per_min
                }

            # Convert recent activity to serializable format
            recent_activity = []
            for activity in self.recent_activity:
                recent_activity.append({
                    'strategy': activity['strategy'],
                    'action': activity['action'],
                    'success': activity['success'],
                    'time': activity['time'].isoformat() if activity['time'] else None
                })

            data = {
                'strategies': strategy_data,
                'market_data': {
                    'symbol': self.market_data.symbol,
                    'price': self.market_data.price,
                    'timestamp': self.market_data.timestamp.isoformat() if self.market_data.timestamp else None,
                    'connection_status': self.market_data.connection_status
                },
                'recent_activity': recent_activity,
                'last_update': datetime.now().isoformat()
            }

            with open(self.monitor_data_file, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception:
            # Don't crash the monitor if saving fails
            pass

    def load_monitor_data(self):
        """Load monitor state from shared file."""
        try:
            if not os.path.exists(self.monitor_data_file):
                return False

            with open(self.monitor_data_file, 'r') as f:
                data = json.load(f)

            # Check if data is recent (within last 30 seconds)
            last_update = datetime.fromisoformat(data.get('last_update', ''))
            if (datetime.now() - last_update).total_seconds() > 30:
                return False  # Data is stale

            # Load strategies
            for name, strategy_data in data.get('strategies', {}).items():
                strategy = StrategyMetrics(name=name)
                strategy.total_actions = strategy_data.get('total_actions', 0)
                strategy.successful_orders = strategy_data.get('successful_orders', 0)
                strategy.failed_orders = strategy_data.get('failed_orders', 0)
                strategy.status = strategy_data.get('status', 'IDLE')
                strategy.refresh_interval = strategy_data.get('refresh_interval', 5.0)
                strategy.performance_per_min = strategy_data.get('performance_per_min', 0.0)

                # Load last action time
                if strategy_data.get('last_action_time'):
                    strategy.last_action_time = datetime.fromisoformat(strategy_data['last_action_time'])

                # Load recent actions
                strategy.recent_actions.clear()
                for action_data in strategy_data.get('recent_actions', []):
                    action_time = None
                    if action_data.get('time'):
                        action_time = datetime.fromisoformat(action_data['time'])

                    strategy.recent_actions.append({
                        'time': action_time,
                        'type': action_data.get('type', ''),
                        'success': action_data.get('success', True)
                    })

                self.strategies[name] = strategy

            # Load market data
            market_data = data.get('market_data', {})
            self.market_data.symbol = market_data.get('symbol', 'BTC-USD')
            self.market_data.price = market_data.get('price', 0.0)
            self.market_data.connection_status = market_data.get('connection_status', 'DISCONNECTED')
            if market_data.get('timestamp'):
                self.market_data.timestamp = datetime.fromisoformat(market_data['timestamp'])

            # Load recent activity
            self.recent_activity.clear()
            for activity_data in data.get('recent_activity', []):
                activity_time = None
                if activity_data.get('time'):
                    activity_time = datetime.fromisoformat(activity_data['time'])

                self.recent_activity.append({
                    'strategy': activity_data.get('strategy', ''),
                    'action': activity_data.get('action', ''),
                    'success': activity_data.get('success', True),
                    'time': activity_time
                })

            return True

        except Exception:
            return False

    def draw_header(self):
        """Draw the header section with overall system status."""
        if not self.stdscr:
            return

        try:
            # Clear header area
            for i in range(3):
                self.stdscr.move(i, 0)
                self.stdscr.clrtoeol()

            # Title
            title = "🐝 DYNAMIC HIVE MONITOR"
            self.stdscr.addstr(0, 2, title, self.colors.get('strategy', 0))

            # Timestamp
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.stdscr.addstr(0, 50, f"⏰ {timestamp}", self.colors.get('info', 0))

            # Market data
            market_color = self.colors.get('success' if self.market_data.connection_status == "CONNECTED" else 'error', 0)
            market_info = f"📡 {self.market_data.symbol} ${self.market_data.price:.2f} | {self.market_data.connection_status}"
            self.stdscr.addstr(1, 2, market_info, market_color)

            # Strategy count
            active_strategies = len([s for s in self.strategies.values() if s.status == "ACTIVE"])
            total_strategies = len(self.strategies)
            strategy_info = f"⚡ Strategies: {active_strategies}/{total_strategies} active"
            self.stdscr.addstr(2, 2, strategy_info, self.colors.get('info', 0))

            # Separator
            self.stdscr.addstr(3, 0, "=" * 80, self.colors.get('default', 0))

        except curses.error:
            pass

    def draw_strategy_grid(self):
        """Draw the main strategy grid with pixel indicators."""
        if not self.stdscr:
            return

        start_row = 5
        strategies_list = list(self.strategies.items())

        for idx, (name, strategy) in enumerate(strategies_list):
            try:
                # Calculate grid position
                grid_row = idx // self.grid_cols
                grid_col = idx % self.grid_cols

                cell_start_row = start_row + (grid_row * self.cell_height)
                cell_start_col = grid_col * self.cell_width

                # Draw strategy cell
                self._draw_strategy_cell(strategy, cell_start_row, cell_start_col)

            except curses.error:
                continue

    def _draw_strategy_cell(self, strategy: StrategyMetrics, start_row: int, start_col: int):
        """Draw a single strategy cell with pixel indicators."""
        if not self.stdscr:
            return

        try:
            # Strategy name header
            name_color = self.colors.get('strategy', 0)
            if strategy.status == "ACTIVE" and self.blink_phase % 2 == 0:
                name_color = self.colors.get('blink_success', name_color)
            elif strategy.status == "ERROR" and self.blink_phase % 2 == 0:
                name_color = self.colors.get('blink_error', name_color)

            self.stdscr.addstr(start_row, start_col, f"┌{'─' * 18}┐", self.colors.get('default', 0))
            self.stdscr.addstr(start_row + 1, start_col, f"│ {strategy.name[:16]:<16} │", name_color)

            # Status indicators line
            status_char = {
                'ACTIVE': '●',
                'WAITING': '○',
                'IDLE': '◦',
                'ERROR': '✗'
            }.get(strategy.status, '?')

            status_color = {
                'ACTIVE': self.colors.get('success', 0),
                'WAITING': self.colors.get('warning', 0),
                'IDLE': self.colors.get('info', 0),
                'ERROR': self.colors.get('error', 0)
            }.get(strategy.status, self.colors.get('default', 0))

            self.stdscr.addstr(start_row + 2, start_col, f"│ {status_char} ", status_color)
            self.stdscr.addstr(f"{strategy.refresh_interval:>3.0f}s ", self.colors.get('info', 0))
            self.stdscr.addstr(f"{strategy.performance_per_min:>6.1f}/min │", self.colors.get('info', 0))

            # Pixel activity indicators (3 rows of 8 pixels each)
            for pixel_row in range(3):
                self.stdscr.addstr(start_row + 3 + pixel_row, start_col, "│ ", self.colors.get('default', 0))

                # Draw 8 pixels per row
                for pixel_col in range(8):
                    pixel_idx = pixel_row * 8 + pixel_col
                    pixel_char, pixel_color = self._get_pixel_indicator(strategy, pixel_idx)
                    self.stdscr.addstr(pixel_char, pixel_color)
                    self.stdscr.addstr(" ")

                self.stdscr.addstr(" │", self.colors.get('default', 0))

            # Statistics line
            self.stdscr.addstr(start_row + 6, start_col, f"│ ✓{strategy.successful_orders:>3} ", self.colors.get('success', 0))
            self.stdscr.addstr(f"✗{strategy.failed_orders:>3} ", self.colors.get('error', 0))
            self.stdscr.addstr(f"Σ{strategy.total_actions:>4} │", self.colors.get('info', 0))

            # Bottom border
            self.stdscr.addstr(start_row + 7, start_col, f"└{'─' * 18}┘", self.colors.get('default', 0))

        except curses.error:
            pass

    def _get_pixel_indicator(self, strategy: StrategyMetrics, pixel_idx: int) -> Tuple[str, int]:
        """Get pixel character and color for activity visualization."""
        # Use recent actions to determine pixel states
        recent_actions = list(strategy.recent_actions)

        # If strategy recent_actions is empty, try to get from global recent_activity
        if not recent_actions:
            strategy_activities = [
                activity for activity in self.recent_activity
                if activity['strategy'] == strategy.name
            ]
            # Convert to the expected format - take last 24 activities to fill all pixels (3 rows x 8 cols)
            recent_actions = [
                {
                    'time': activity['time'],
                    'type': activity['action'],
                    'success': activity['success']
                }
                for activity in strategy_activities[-24:]  # Last 24 activities to fill all 24 pixels
            ]

        if pixel_idx < len(recent_actions):
            action = recent_actions[-(pixel_idx + 1)]  # Most recent first
            if not action['time']:
                return "·", self.colors.get('info', 0)

            age = (datetime.now() - action['time']).total_seconds()
            action_type = action.get('type', '')

            # Choose symbol based on action type
            if 'BUY' in action_type.upper():
                symbol = "▲"  # Triangle up for buy
            elif 'SELL' in action_type.upper():
                symbol = "▼"  # Triangle down for sell
            elif 'PASS' in action_type.upper() or 'TICK' in action_type.upper():
                symbol = "○"  # Circle for no-action tick
            else:
                symbol = "█"  # Block for other actions

            # Blinking for very recent actions (< 5 seconds)
            if age < 5 and self.blink_phase % 2 == 0:
                if action['success']:
                    return symbol, self.colors.get('blink_success', 0)
                else:
                    return symbol, self.colors.get('blink_error', 0)

            # Fading colors based on age - much longer retention for better visualization
            if age < 30:  # 0-30 seconds: bright colors with original symbols
                return symbol, self.colors.get('success' if action['success'] else 'error', 0)
            elif age < 120:  # 30-120 seconds (2 minutes): keep symbols with medium brightness
                return symbol, self.colors.get('success' if action['success'] else 'warning', 0)
            elif age < 300:  # 2-5 minutes: keep symbols but dim color
                return symbol, self.colors.get('info', 0)
            elif age < 600:  # 5-10 minutes: very faint symbols
                # Keep directional symbols visible longer
                if symbol in ['▲', '▼', '○']:
                    return symbol, self.colors.get('default', 0)
                else:
                    return "·", self.colors.get('info', 0)
            else:  # > 10 minutes: finally fade to dots
                return "·", self.colors.get('default', 0)
        else:
            # No activity for this pixel
            return "·", self.colors.get('info', 0)

    def draw_activity_log(self):
        """Draw recent activity log at the bottom."""
        if not self.stdscr:
            return

        try:
            max_row, max_col = self.stdscr.getmaxyx()
            log_start_row = max_row - 8

            # Activity log header
            self.stdscr.addstr(log_start_row, 0, "=" * 80, self.colors.get('default', 0))
            self.stdscr.addstr(log_start_row + 1, 2, "📋 RECENT ACTIVITY", self.colors.get('info', 0))

            # Show last 5 activities
            recent = list(self.recent_activity)[-5:]
            for i, activity in enumerate(recent):
                try:
                    row = log_start_row + 2 + i
                    time_str = activity['time'].strftime("%H:%M:%S")
                    status_char = "✓" if activity['success'] else "✗"
                    status_color = self.colors.get('success' if activity['success'] else 'error', 0)

                    self.stdscr.addstr(row, 2, f"{time_str} ", self.colors.get('info', 0))
                    self.stdscr.addstr(f"{status_char} ", status_color)
                    self.stdscr.addstr(f"{activity['strategy']:>12} ", self.colors.get('strategy', 0))
                    self.stdscr.addstr(f"{activity['action']}", self.colors.get('default', 0))

                except curses.error:
                    break

        except curses.error:
            pass

    def monitor_loop(self, stdscr):
        """Main monitoring loop (runs in curses context)."""
        self.stdscr = stdscr
        self.init_colors()

        # Configure curses
        curses.curs_set(0)  # Hide cursor
        stdscr.nodelay(True)  # Non-blocking input
        stdscr.timeout(100)  # 100ms timeout

        self.running = True
        last_blink_update = time.time()

        while self.running:
            try:
                # Handle input
                key = stdscr.getch()
                if key == ord('q') or key == ord('Q'):
                    break
                elif key == ord('r') or key == ord('R'):
                    self.load_strategies_from_db()

                # Load live data if available (every 2 seconds in live mode)
                if self.live_mode and time.time() - self.last_update > 2.0:
                    if self.load_monitor_data():
                        # Successfully loaded live data
                        self.last_update = time.time()
                    else:
                        # No live data available, show connection status
                        self.market_data.connection_status = "DISCONNECTED"

                # Update blink phase
                if time.time() - last_blink_update > 0.5:
                    self.blink_phase = (self.blink_phase + 1) % 2
                    last_blink_update = time.time()

                # Clear screen
                stdscr.clear()

                # Draw all sections
                self.draw_header()
                self.draw_strategy_grid()
                self.draw_activity_log()

                # Instructions
                max_row, max_col = stdscr.getmaxyx()
                stdscr.addstr(max_row - 1, 2, "Press 'Q' to quit, 'R' to reload strategies", self.colors.get('info', 0))

                # Refresh screen
                stdscr.refresh()

                # Small delay to prevent excessive CPU usage
                time.sleep(0.1)

            except KeyboardInterrupt:
                break
            except curses.error:
                continue

        self.running = False

    def start_monitor(self):
        """Start the terminal monitor."""
        try:
            # Load initial data
            self.load_strategies_from_db()

            # Try to load live data first
            if self.live_mode and not self.load_monitor_data():
                print("ℹ️  No live trading data found - monitor will start clean")
                print("   Start the Hive trading system to see real activity")
                # Start with clean data, no simulation
            elif self.live_mode:
                print("✅ Connected to live trading data")

            # Start curses interface
            curses.wrapper(self.monitor_loop)

        except Exception as e:
            print(f"❌ Monitor error: {e}")
            return False

        return True

    def stop_monitor(self):
        """Stop the monitoring system."""
        self.running = False

# Integration methods for the main Hive system


class HiveMonitorIntegration:
    """Integration layer between Hive system and terminal monitor."""

    def __init__(self):
        self.monitor = None
        self.monitor_thread = None

    def start_background_monitor(self, db_path: str = "hive_strategies.db"):
        """Start monitor in background thread."""
        if self.monitor_thread and self.monitor_thread.is_alive():
            return False

        self.monitor = HiveTerminalMonitor(db_path, live_mode=True)

        def monitor_worker():
            self.monitor.start_monitor()

        self.monitor_thread = threading.Thread(target=monitor_worker, daemon=True)
        self.monitor_thread.start()

        return True

    def update_activity(self, strategy_name: str, action_type: str, success: bool = True):
        """Update activity from Hive system."""
        if self.monitor:
            self.monitor.update_strategy_activity(strategy_name, action_type, success)

    def update_market_data(self, symbol: str, price: float, connected: bool = True):
        """Update market data from Hive system."""
        if self.monitor:
            self.monitor.update_market_data(symbol, price, connected)

    def stop_monitor(self):
        """Stop the background monitor."""
        if self.monitor:
            self.monitor.stop_monitor()
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)


if __name__ == "__main__":
    """Standalone monitor for testing."""
    print("🐝 Starting Hive Terminal Monitor...")
    print("Press Ctrl+C to exit")

    monitor = HiveTerminalMonitor()

    try:
        monitor.start_monitor()
    except KeyboardInterrupt:
        print("\n👋 Monitor stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")
