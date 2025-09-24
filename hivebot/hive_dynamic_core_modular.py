#!/usr/bin/env python3

"""
Hive Dynamic Strategy Core - Modular Architecture Version
Advanced 1:N architecture with dynamic strategy management using modular components.
"""

import argparse
import asyncio

# import json  # Removed - not used in this file
import logging
import os
import signal
import socket
import sys
import time

import requests

# Add current directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Import our modular components (need to be after path setup)
try:
    from hive_orchestrator import HiveDynamicCore
    from hummingbot.client.config.config_helpers import load_client_config_map_from_file
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure to activate the hummingbot conda environment first:")
    print("source ~/miniconda3/bin/activate hummingbot")
    sys.exit(1)


def load_env_file(env_path: str = ".env"):
    """Load environment variables from .env file."""
    if not os.path.exists(env_path):
        return

    try:
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
        print(f"✅ Loaded environment variables from {env_path}")
    except Exception as e:
        print(f"⚠️ Failed to load {env_path}: {e}")


def register_with_dashboard(hive, api_port, dashboard_url="http://localhost:3000"):
    """Register this hive instance with the dashboard manager."""
    try:
        hostname = socket.gethostname()

        # Get user main address if this is a spawned instance
        user_main_address = os.getenv("HIVE_USER_ADDRESS")

        # Use consistent ID generation from hive instance
        instance_id = hive._get_instance_id() if hasattr(hive, '_get_instance_id') else f"hive-{hostname}-{api_port}"

        bot_data = {
            "id": instance_id,
            "name": instance_id,
            "status": "running",
            "strategies": list(hive.strategies.keys()) if hive.strategies else ["hive_multi_strategy"],
            "uptime": int(time.time() - (hive.start_time or time.time())),
            "total_strategies": len(hive.strategies),
            "total_actions": hive.total_actions,
            "actions_per_minute": hive.total_actions / max((time.time() - (hive.start_time or time.time())) / 60, 0.1),
            "memory_usage": 150,  # Placeholder
            "cpu_usage": 25,      # Placeholder
            "api_port": api_port,
            "user_main_address": user_main_address  # Include user address for spawned instances
        }

        # Register with management dashboard
        try:
            response = requests.post(
                f"{dashboard_url}/api/bots",
                json=bot_data,
                timeout=2
            )
            if response.status_code == 200:
                print(f"📊 Registered with dashboard: {bot_data['name']}")
        except Exception as e:
            print(f"⚠️ Dashboard registration failed: {e}")
            pass  # Don't let dashboard registration errors break the main system

    except Exception:
        pass  # Don't let dashboard registration errors break the main system


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Hive Dynamic Strategy Core - Modular Architecture",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python hive_dynamic_core_modular.py                              # Default testnet trading
  python hive_dynamic_core_modular.py --network mainnet            # Use mainnet
  python hive_dynamic_core_modular.py --monitor --network mainnet  # Mainnet with monitor
  python hive_dynamic_core_modular.py --monitor --port 8081        # Custom port

Environment Variables:
  HYPERLIQUID_PRIVATE_KEY  Private key for real trading (REQUIRED)
  HIVE_ENABLE_MONITOR      Auto-enable monitor (true/false)
        """
    )

    parser.add_argument('--monitor', action='store_true',
                        help='Enable terminal monitor')
    parser.add_argument('--port', type=int, default=8080,
                        help='API server port (default: 8080)')
    parser.add_argument('--db-path', type=str, default='hive_strategies.db',
                        help='SQLite database path (default: hive_strategies.db)')
    parser.add_argument('--dashboard-url', type=str, default='http://localhost:3000',
                        help='Dashboard URL for reporting (default: http://localhost:3000)')
    parser.add_argument('--network', type=str, choices=['mainnet', 'testnet'], default='testnet',
                        help='Network to use: mainnet or testnet (default: testnet)')

    return parser.parse_args()


async def run_dynamic_hive(args):
    """Run dynamic Hive with command-line arguments."""
    print("🐝 DYNAMIC HIVE - MODULAR ARCHITECTURE")
    print("=" * 60)
    print("Database-driven strategy management with hot add/remove capabilities")
    print("-" * 60)

    # Load environment variables from .env file
    load_env_file()

    # Set up signal handling for graceful shutdown
    shutdown_event = asyncio.Event()

    def signal_handler(signum, frame):
        print(f"\n📡 Received signal {signum}, initiating graceful shutdown...")
        shutdown_event.set()

    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Determine configuration from args and environment
    enable_monitor = args.monitor or os.getenv("HIVE_ENABLE_MONITOR", "").lower() == "true"

    # Initialize dynamic Hive with modular architecture
    client_config_map = load_client_config_map_from_file()
    hive = HiveDynamicCore(client_config_map, args.db_path)

    # Configure monitor
    if enable_monitor:
        print("🖥️  Enabling monitor data sharing...")
        hive.enable_monitor = True
        # Don't start the monitor UI here - it would block the main process
        # The monitor data will be saved to JSON file for separate monitor process
        print("✅ Monitor enabled! Run this in another terminal: python hive_terminal_monitor.py")

    # Configure trading - ALWAYS ENABLED FOR REAL TRADING
    private_key = os.getenv("HYPERLIQUID_PRIVATE_KEY", "")
    if not private_key:
        print("❌ HYPERLIQUID_PRIVATE_KEY not set in environment")
        print("🔑 Please set your Hyperliquid testnet private key:")
        print("   echo 'HYPERLIQUID_PRIVATE_KEY=your_key_here' >> .env")
        return False
    else:
        print("🔑 Using private key from environment variable")

        # Show main wallet address if available (for spawned instances)
        main_wallet = os.getenv("HIVE_USER_ADDRESS", "")
        if main_wallet:
            print(f"👤 Main wallet address: {main_wallet}")

        # Show agent wallet address and fetch real balance
        try:
            from eth_account import Account
            import aiohttp
            import json

            agent_account = Account.from_key(private_key)
            agent_address = agent_account.address
            print(f"🤖 Agent wallet address: {agent_address}")

            # DEBUG: Check current IP first to verify proxy
            print("🌐 DEBUG: Checking current IP...")
            try:
                import requests
                response = requests.get("http://190.7.200.14:8888", timeout=10)
                if response.status_code == 200:
                    current_ip = response.text.strip()
                    print(f"🌐 DEBUG: Current IP: {current_ip}")
                else:
                    print(f"🌐 DEBUG: IP check failed with status {response.status_code}")
            except Exception as e:
                print(f"🌐 DEBUG: IP check error: {e}")

            # Fetch balance from Hyperliquid API
            api_url = "http://15.235.212.39:8081/info"

            async def fetch_balance():
                try:
                    # DEBUG: Check if proxy is working by fetching current IP
                    async with aiohttp.ClientSession() as session:
                        try:
                            async with session.get("https://cip.cc", timeout=aiohttp.ClientTimeout(total=10)) as ip_response:
                                if ip_response.status == 200:
                                    ip_text = await ip_response.text()
                                    ip_line = ip_text.split('\n')[0]  # First line has IP
                                    print(f"🌐 DEBUG: Current IP: {ip_line}")
                                else:
                                    print(f"🌐 DEBUG: IP check failed with status {ip_response.status}")
                        except Exception as ip_error:
                            print(f"🌐 DEBUG: IP check error: {ip_error}")

                    # Use main wallet address if available (for spawned instances), otherwise agent address
                    main_address = main_wallet if main_wallet else agent_address
                    async with aiohttp.ClientSession() as session:
                        payload = {
                            "type": "clearinghouseState",
                            "user": main_address
                        }
                        async with session.post(api_url, json=payload, timeout=aiohttp.ClientTimeout(total=5)) as response:
                            if response.status == 200:
                                data = await response.json()
                                if "marginSummary" in data:
                                    account_value = float(data["marginSummary"]["accountValue"])
                                    total_margin_used = float(data["marginSummary"]["totalMarginUsed"])
                                    withdrawable = float(data["withdrawable"])  # withdrawable is at root level

                                    print(f"💰 Account Value: ${account_value:.2f}")
                                    print(f"💰 Margin Used: ${total_margin_used:.2f}")
                                    print(f"💰 Withdrawable: ${withdrawable:.2f}")
                                else:
                                    print("💰 Balance: Account not found or no positions")
                            else:
                                print(f"💰 Balance: API request failed (HTTP {response.status})")
                except Exception as e:
                    print(f"💰 Balance: Failed to fetch ({str(e)[:50]}...)")

            # Fetch balance asynchronously
            await fetch_balance()

        except Exception as e:
            print(f"⚠️ Could not derive agent wallet address: {e}")

        print(f"🌐 Network: {args.network.upper()}")

    # Start the Hive - ALWAYS with trading enabled
    success = await hive.start_hive(
        api_port=args.port,
        enable_trading=True,  # ALWAYS TRUE - no demo mode
        private_key=private_key,
        dashboard_url=args.dashboard_url,
        network=args.network
    )

    if not success:
        print("❌ Failed to start Hive")
        return False

    # Print status
    mode = "REAL TRADING"  # Always trading mode
    monitor_status = "ENABLED" if enable_monitor else "DISABLED"

    print(f"\n🎯 HIVE RUNNING! Mode: {mode} | Monitor: {monitor_status} | Port: {args.port}")
    print("   📊 Strategy list: curl http://localhost:{}/api/strategies".format(args.port))
    print("   📈 Hive status: curl http://localhost:{}/api/status".format(args.port))
    print("   🔄 Add strategy: POST http://localhost:{}/api/strategies".format(args.port))
    print("   🗑️  Remove strategy: DELETE http://localhost:{}/api/strategies/{{name}}".format(args.port))

    print("\n💰 REAL TRADING MODE ENABLED!")
    orders_url = "https://app.hyperliquid.xyz/historicalOrders/" if args.network == "mainnet" else "https://app.hyperliquid-testnet.xyz/historicalOrders/"
    print(f"   🔗 View orders: {orders_url}")

    print("\n⌨️  Controls:")
    print("   - Press Ctrl+C to stop")
    if enable_monitor:
        print("   - Monitor running in background")
    else:
        print("   - Use --monitor flag to enable terminal monitor")
    print("   - Strategies can be modified via API while running")

    try:
        # Keep running until shutdown signal received
        while not shutdown_event.is_set():
            try:
                # Wait for shutdown event or timeout after 10 seconds
                await asyncio.wait_for(shutdown_event.wait(), timeout=10.0)
                break  # Shutdown event was set
            except asyncio.TimeoutError:
                # Timeout is expected - continue with status update
                pass
            except asyncio.CancelledError:
                print("\n🔄 Sleep cancelled, shutting down gracefully...")
                break

            # Print status update every 10 seconds
            if hive.total_cycles > 0:
                uptime = (asyncio.get_event_loop().time() - (hive.start_time or 0)) / 60
                actions_per_min = hive.total_actions / max(uptime, 0.1)

                print(f"📊 Status: {len(hive.strategies)} strategies, {hive.total_actions} actions, {actions_per_min:.1f} actions/min")

                # Show active real strategies
                if hive.real_strategies:
                    real_count = sum(1 for rs in hive.real_strategies.values() if rs.is_running)
                    print(f"💰 Real trading: {real_count}/{len(hive.real_strategies)} strategies active")

                # Register with dashboard every 30 seconds (every 3rd status update)
                if hive.total_cycles % 3 == 0:
                    register_with_dashboard(hive, args.port, args.dashboard_url)

    except KeyboardInterrupt:
        print("\n👋 Shutting down Hive...")
    except asyncio.CancelledError:
        print("\n🔄 Main loop cancelled, shutting down...")
    except Exception as e:
        print(f"\n❌ Unexpected error in main loop: {e}")
    finally:
        try:
            await hive.stop_hive()
        except Exception as e:
            print(f"⚠️ Error during hive shutdown: {e}")

        total_time = (asyncio.get_event_loop().time() - (hive.start_time or 0)) / 60
        print("\n🎯 DYNAMIC HIVE DEMONSTRATION COMPLETE!")
        print(f"⚡ Total actions: {hive.total_actions}")
        print(f"🔄 Total cycles: {hive.total_cycles}")
        print(f"⏱️ Runtime: {total_time:.1f} minutes")
        print(f"📈 Average: {hive.total_actions / max(total_time, 0.1):.1f} actions/minute")

    return True


async def run_hive_with_config(
    enable_monitor: bool = False,
    api_port: int = 8080,
    db_path: str = "hive_strategies.db"
):
    """
    Run Hive with specific configuration (useful for programmatic usage).
    Trading is always enabled.

    Args:
        enable_monitor: Whether to enable terminal monitor
        api_port: Port for REST API server
        db_path: Path to SQLite database
    """
    # Load environment variables
    load_env_file()

    # Initialize Hive
    client_config_map = load_client_config_map_from_file()
    hive = HiveDynamicCore(client_config_map, db_path)

    # Configure monitor
    if enable_monitor:
        hive.enable_monitor = True
        hive.monitor.start_background_monitor()
        logging.info("✅ Terminal monitor enabled")

    # Get private key - always required for trading
    private_key = os.getenv("HYPERLIQUID_PRIVATE_KEY", "")
    if not private_key:
        logging.error("🔑 HYPERLIQUID_PRIVATE_KEY not set in environment")
        return False

    # Start Hive - always with trading enabled
    dashboard_url = os.getenv("HIVE_DASHBOARD_URL", "http://localhost:3000")
    success = await hive.start_hive(api_port, True, private_key, dashboard_url)
    if not success:
        logging.error("❌ Failed to start Hive")
        return False

    logging.info(f"🚀 Hive started successfully on port {api_port}")
    return hive


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # Parse command line arguments
    args = parse_arguments()

    # Run with command-line arguments
    asyncio.run(run_dynamic_hive(args))
