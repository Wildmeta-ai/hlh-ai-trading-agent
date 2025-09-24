#!/usr/bin/env python3

"""
Hive Orchestrator Module - Main coordination and strategy management.
"""

import asyncio
import logging
import time
from typing import Dict, Optional, Union

from hive_api_server import HiveAPIServer
from hive_connector import HiveConnectorManager

# Import dashboard reporter
from hive_dashboard_reporter import HiveDashboardReporter

# Import our modules
from hive_database import DynamicStrategyConfig, HiveDynamicDatabase
from hive_position_tracker import HivePositionTracker

# Import PostgreSQL sync
from hive_postgres_sync import (
    get_postgres_sync,
    initialize_postgres_sync,
    sync_all_strategies_to_postgres,
    sync_strategy_to_postgres,
)
from hive_strategy import DynamicStrategyInfo, RealStrategyInstance

# Import monitor integration
from hive_terminal_monitor import HiveMonitorIntegration
from hummingbot.client.config.config_helpers import ClientConfigAdapter, load_client_config_map_from_file

# from hummingbot.core.data_type.common import OrderType  # Currently unused
from hummingbot.core.event.event_forwarder import EventForwarder
from hummingbot.core.event.events import MarketEvent

# Hummingbot core imports
from hummingbot.core.trading_core import TradingCore


class HiveDynamicCore(TradingCore):
    """
    Advanced Hive core with dynamic strategy management.
    Supports hot-adding/removing strategies while running.
    """

    def __init__(self, client_config: Union[ClientConfigAdapter, Dict], db_path: str = "hive_strategies.db"):
        super().__init__(client_config)

        # Initialize modules
        self.database = HiveDynamicDatabase(db_path)
        self.connector_manager = HiveConnectorManager(
            client_config if isinstance(client_config, ClientConfigAdapter) else load_client_config_map_from_file()
        )
        self.api_server = HiveAPIServer(self)

        # Dynamic strategy management
        self.strategies: Dict[str, DynamicStrategyInfo] = {}  # Simulated strategies
        self.real_strategies: Dict[str, RealStrategyInstance] = {}  # Real strategy instances
        self._hive_running = False
        self._hive_clock_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None

        # Shared resources
        self.shared_market_data = {}
        self.last_market_update = 0

        # Performance tracking
        self.total_cycles = 0
        self.total_actions = 0
        self.start_time = None

        # Terminal monitor integration
        self.monitor = HiveMonitorIntegration()
        self.enable_monitor = False

        # Dashboard reporter for web visibility
        self.dashboard_reporter = HiveDashboardReporter()

        # PostgreSQL sync for centralized management
        self.postgres_sync_enabled = False

        # Order tracking for events
        self.pending_orders: Dict[str, str] = {}  # order_id -> strategy_name

        # Position tracking for real P&L
        self.position_tracker = HivePositionTracker()
        self.position_tracking_task: Optional[asyncio.Task] = None

        logging.info("🐝 HiveDynamicCore initialized with modular architecture")

    def _get_instance_id(self) -> str:
        """Generate consistent instance ID with wallet info for all dashboard/heartbeat operations."""
        # Get wallet address from connector if available
        wallet_short = "unknown"
        if hasattr(self, 'connector_manager') and self.connector_manager:
            wallet_address = self.connector_manager.get_wallet_address()
            if wallet_address:
                wallet_short = f"{wallet_address[:6]}...{wallet_address[-4:]}"

        # Use actual api_port, no fallback
        api_port = self.api_port if hasattr(self, 'api_port') else None
        if api_port is None:
            logging.error("ERROR: api_port not set when generating instance ID!")
            api_port = 0  # Use 0 to indicate error instead of misleading 8080
        return f"hive-{wallet_short}-{api_port}"

    def _get_required_trading_pairs(self) -> list:
        """Collect all trading pairs from loaded strategies AND existing positions."""
        trading_pairs = []

        # Collect from database-loaded strategies
        configs = self.database.load_all_strategies(enabled_only=True)
        for config in configs:
            if config.market and config.market not in trading_pairs:
                trading_pairs.append(config.market)

        # Collect from currently running strategies
        for strategy_info in self.strategies.values():
            if strategy_info.config.market and strategy_info.config.market not in trading_pairs:
                trading_pairs.append(strategy_info.config.market)

        # DYNAMIC: Only include BTC to avoid rate limiting
        # Based on Hyperliquid connector, trading pairs must be in "ASSET-USD" format
        btc_pair = "BTC-USD"
        if btc_pair not in trading_pairs:
            trading_pairs.append(btc_pair)
            logging.info(f"🎯 Added {btc_pair} for market data support")

        # DYNAMIC: Collect from existing positions if connector is available
        try:
            if hasattr(self, 'real_connector') and self.real_connector:
                # Check if connector has positions
                if hasattr(self.real_connector, 'account_positions') and self.real_connector.account_positions:
                    for trading_pair, position in self.real_connector.account_positions.items():
                        if position.amount != 0 and trading_pair not in trading_pairs:
                            trading_pairs.append(trading_pair)
                            logging.info(f"🎯 Added {trading_pair} from existing position (amount: {position.amount})")

        except Exception as e:
            logging.debug(f"Could not check existing positions for trading pairs: {e}")

        logging.info(f"🎯 Required trading pairs from strategies + positions: {trading_pairs}")
        return trading_pairs

    async def ensure_trading_pair_support(self, trading_pair: str):
        """Ensure the connector supports a specific trading pair, reinitialize if needed."""
        if not self.real_connector:
            logging.warning(f"⚠️ Cannot ensure {trading_pair} support - no connector initialized")
            return False

        # Check if trading pair is already supported
        if hasattr(self.real_connector, 'trading_pairs') and trading_pair in self.real_connector.trading_pairs:
            logging.info(f"✅ {trading_pair} already supported by connector")
            return True

        logging.info(f"🔄 {trading_pair} not supported, reinitializing connector...")

        # Get current required pairs plus the new one
        current_pairs = self._get_required_trading_pairs()
        if trading_pair not in current_pairs:
            current_pairs.append(trading_pair)

        # Reinitialize connector with expanded trading pairs
        try:
            # Stop current connector cleanly
            if hasattr(self.real_connector, 'stop_network'):
                await self.real_connector.stop_network()

            # Reinitialize with new trading pairs
            private_key = getattr(self, '_private_key', "")
            result = await self.connector_manager.initialize_real_connector(
                enable_trading=True,
                private_key=private_key,
                required_trading_pairs=current_pairs
            )

            if result:
                logging.info(f"✅ Connector reinitialized with {trading_pair} support")
                return True
            else:
                logging.error(f"❌ Failed to reinitialize connector with {trading_pair}")
                return False

        except Exception as e:
            logging.error(f"❌ Error reinitializing connector for {trading_pair}: {e}")
            return False

    def _select_market_data_pair(self, available_pairs: list) -> str:
        """Select the best trading pair for shared market data based on strategy priorities."""
        # Get pairs needed by active strategies
        strategy_pairs = [info.config.market for info in self.strategies.values() if info.is_running]

        # Prioritize pairs used by strategies
        for strategy_pair in strategy_pairs:
            if strategy_pair in available_pairs:
                logging.info(f"✅ Using {strategy_pair} for shared market data (required by active strategy)")
                return strategy_pair

        # Fallback to BTC if available
        if "BTC" in available_pairs:
            logging.info("✅ Using BTC for shared market data (fallback)")
            return "BTC"

        # Use first available pair
        selected = available_pairs[0]
        logging.info(f"✅ Using {selected} for shared market data (first available)")
        return selected

    @property
    def real_connector(self):
        """Get the real connector from connector manager."""
        return self.connector_manager.get_connector()

    def _setup_event_listeners(self):
        """Set up event listeners for order tracking."""
        if not self.real_connector:
            return

        # Set up comprehensive order event listeners using EventForwarder
        order_failure_forwarder = EventForwarder(self._handle_order_failure)
        order_created_forwarder = EventForwarder(self._handle_order_created)
        order_rejected_forwarder = EventForwarder(self._handle_order_rejected)

        self.real_connector.add_listener(MarketEvent.OrderFailure, order_failure_forwarder)
        self.real_connector.add_listener(MarketEvent.BuyOrderCreated, order_created_forwarder)
        self.real_connector.add_listener(MarketEvent.SellOrderCreated, order_created_forwarder)

        # OrderRejected might be what we need for "Failed to submit" cases
        try:
            self.real_connector.add_listener(MarketEvent.OrderRejected, order_rejected_forwarder)
        except Exception:
            pass  # OrderRejected might not exist

        logging.debug("✅ Set up comprehensive order event listeners")

    def _handle_order_failure(self, event):
        """Handle order failure events from Hummingbot."""
        try:
            order_id = event.order_id
            logging.info(f"🔴 ORDER FAILURE EVENT: {order_id}")
            # Find which strategy this order belongs to
            if order_id in self.pending_orders:
                strategy_name = self.pending_orders[order_id]
                logging.info(f"🔴 Order {order_id} FAILED for strategy {strategy_name}")

                # Update monitor with real failure
                self._update_monitor_activity(strategy_name, "ORDER_FAILED", False)

                # Remove from pending orders
                del self.pending_orders[order_id]
            else:
                logging.debug(f"⚠️ Received failure event for unknown order: {order_id}")
        except Exception as e:
            logging.error(f"Error handling order failure event: {e}")

    def _handle_order_created(self, event):
        """Handle order created events from Hummingbot."""
        try:
            order_id = event.order_id
            logging.info(f"✅ ORDER CREATED EVENT: {order_id}")
        except Exception as e:
            logging.error(f"Error handling order created event: {e}")

    def _handle_order_rejected(self, event):
        """Handle order rejected events from Hummingbot."""
        try:
            order_id = getattr(event, 'order_id', 'unknown')
            logging.info(f"❌ ORDER REJECTED EVENT: {order_id}")
            # This might be what we need for "Failed to submit" cases
            if order_id != 'unknown' and order_id in self.pending_orders:
                strategy_name = self.pending_orders[order_id]
                logging.info(f"❌ Order {order_id} REJECTED for strategy {strategy_name}")

                # Update monitor with rejection as failure
                self._update_monitor_activity(strategy_name, "ORDER_REJECTED", False)

                # Remove from pending orders
                del self.pending_orders[order_id]
        except Exception as e:
            logging.error(f"Error handling order rejected event: {e}")

    def _cleanup_old_pending_orders(self):
        """Periodically clean up old pending orders to prevent memory leaks."""
        try:
            # Keep only the most recent 1000 pending orders
            if len(self.pending_orders) > 1000:
                # Convert to list of tuples, sort by key (order_id), keep last 1000
                recent_orders = dict(list(self.pending_orders.items())[-1000:])
                self.pending_orders.clear()
                self.pending_orders.update(recent_orders)
                logging.debug(f"🧹 Cleaned up old pending orders, kept {len(self.pending_orders)}")
        except Exception as e:
            logging.debug(f"Error cleaning up pending orders: {e}")

    async def initialize_real_connector(self, enable_trading: bool = False, private_key: str = "", network: str = "testnet") -> bool:
        """Initialize REAL Hummingbot connector."""
        # Collect trading pairs from all loaded strategies
        required_trading_pairs = self._get_required_trading_pairs()
        logging.info(f"🎯 Initializing connector with required trading pairs: {required_trading_pairs}")
        result = await self.connector_manager.initialize_real_connector(enable_trading, private_key, required_trading_pairs, network)

        # Set up event listeners after connector is initialized
        if result and self.real_connector:
            self._setup_event_listeners()

        return result

    async def _register_with_dashboard(self, enable_trading: bool, api_port: int):
        """DEPRECATED: Registration now handled by activity/ingest heartbeat."""
        # Registration is now handled entirely by the activity/ingest heartbeat
        # This prevents duplicate entries in bot_runs table
        logging.debug("📊 Dashboard registration handled by activity/ingest heartbeat")
        pass

    async def _update_dashboard_status(self):
        """DEPRECATED: Status updates now handled by activity/ingest heartbeat."""
        # All dashboard status updates are now handled by the activity/ingest heartbeat
        # This prevents conflicts and duplicate updates
        pass

    async def start_hive(self, api_port: int = 8080, enable_trading: bool = False, private_key: str = "", dashboard_url: str = "http://localhost:3000", network: str = "testnet") -> bool:
        """Start the dynamic Hive with all components."""
        try:
            logging.info("🐝 Starting Dynamic Hive with 1:N architecture")
            self._hive_running = True
            self.network = network  # Store network choice
            self.start_time = time.time()
            self.api_port = api_port  # Store API port for identification
            self.dashboard_url = dashboard_url  # Store dashboard URL for reporting

            # Initialize REAL Hummingbot connector FIRST
            connector_success = await self.initialize_real_connector(enable_trading, private_key, network)
            if enable_trading and not connector_success:
                logging.error("❌ Failed to initialize real trading connector - cannot start Hive")
                return False
            elif not connector_success:
                logging.warning("⚠️ Connector not ready - running in market data only mode")

            # Initialize PostgreSQL sync for centralized management
            logging.info("🔍 Attempting to initialize PostgreSQL sync...")
            instance_id = self._get_instance_id()
            if initialize_postgres_sync(api_port, hive_id=instance_id):
                self.postgres_sync_enabled = True
                logging.info(f"✅ PostgreSQL sync enabled for centralized dashboard with hive_id: {instance_id}")

                # Initialize position tracker with PostgreSQL connection
                logging.info("🔍 Attempting to get PostgreSQL sync for position tracker...")
                postgres_sync = get_postgres_sync()
                if postgres_sync:
                    logging.info("🔍 PostgreSQL sync obtained, initializing position tracker...")
                    self.position_tracker = HivePositionTracker(postgres_sync)
                    logging.info("🎯 Position tracker initialized with database connection")
                else:
                    logging.error("❌ Failed to get PostgreSQL sync for position tracker")

                # Send immediate heartbeat to dashboard after successful registration
                try:
                    import socket

                    import requests
                    hostname = socket.gethostname()
                    instance_id = self._get_instance_id()
                    bot_data = {
                        "id": instance_id,
                        "name": instance_id,
                        "status": "running",
                        "strategies": [],
                        "uptime": 0,
                        "total_strategies": 0,
                        "total_actions": 0,
                        "actions_per_minute": 0,
                        "memory_usage": 150,
                        "cpu_usage": 25,
                        "api_port": api_port
                    }
                    response = requests.post(
                        "http://15.235.212.36:8091/api/bots",
                        json=bot_data,
                        timeout=2
                    )
                    if response.status_code == 200:
                        logging.info(f"📊 Immediate heartbeat sent to dashboard: {bot_data['name']}")

                        # Start background heartbeat task to keep bot online
                        self._start_heartbeat_task(api_port)

                        # Start position tracking if we have a real connector
                        logging.info(f"🔍 Checking position tracking prerequisites: real_connector={self.real_connector is not None}, position_tracker={self.position_tracker is not None}")
                        if self.real_connector and self.position_tracker:
                            logging.info("🔍 Starting position tracking task...")
                            self.position_tracking_task = asyncio.create_task(
                                self.position_tracker.start_position_tracking(
                                    self.real_connector,
                                    account_name="main",
                                    strategy_registry=self.real_strategies
                                )
                            )
                            logging.info("🎯 Started real-time position tracking")
                        else:
                            if not self.real_connector:
                                logging.warning("⚠️ Cannot start position tracking - real_connector not available")
                            if not self.position_tracker:
                                logging.warning("⚠️ Cannot start position tracking - position_tracker not initialized")

                except Exception as e:
                    logging.warning(f"⚠️ Initial dashboard heartbeat failed: {e}")
            else:
                logging.warning("⚠️ PostgreSQL sync disabled - will run in local mode")
                logging.warning("❌ Position tracking will not be available without PostgreSQL sync")

            # **CRITICAL**: Start TradingCore Clock System for proper Hummingbot environment
            logging.info("🕐 Starting TradingCore clock system...")
            try:
                # Start the clock system using the correct TradingCore method
                await self.start_clock()
                logging.info("✅ TradingCore clock started successfully")

                # Verify clock is running
                if hasattr(self, 'clock') and self.clock:
                    # Clock object exists and is ready
                    logging.info(f"🕐 Clock created successfully with mode: {self.clock.clock_mode}")
                    if hasattr(self.clock, '_started'):
                        logging.info(f"🕐 Clock started: {self.clock._started}")
                else:
                    logging.error("❌ Clock not properly initialized")

            except Exception as e:
                logging.error(f"❌ Failed to start TradingCore clock: {e}")
                import traceback
                traceback.print_exc()

            # Load strategies from database
            await self.load_strategies_from_database()

            if not self.strategies:
                logging.warning("⚠️ No strategies loaded - add some strategies to the database")
            else:
                # **DEBUG**: Log strategy creation status
                logging.info(f"📊 Loaded {len(self.strategies)} simulated strategies")
                logging.info(f"💰 Created {len(self.real_strategies)} real strategies")
                if len(self.real_strategies) == 0 and len(self.strategies) > 0:
                    logging.error("❌ CRITICAL: Simulated strategies exist but no real strategies were created!")
                    logging.error("   This means PMM strategies won't be able to place orders")
                    logging.error("   Check real strategy creation errors above")

                    # **EMERGENCY FIX**: Try to create a real strategy manually
                    logging.info("🆘 ATTEMPTING EMERGENCY REAL STRATEGY CREATION...")
                    for strategy_name, strategy_info in self.strategies.items():
                        if strategy_name not in self.real_strategies:
                            logging.info(f"🔧 Emergency creating real strategy: {strategy_name}")
                            try:
                                emergency_created = await self.create_real_strategy(strategy_info.config, save_to_db=False)
                                if emergency_created:
                                    emergency_started = self.start_real_strategy(strategy_name)
                                    if emergency_started:
                                        logging.info(f"✅ EMERGENCY SUCCESS: Created real strategy {strategy_name}")
                                        break
                                    else:
                                        logging.error(f"❌ Emergency start failed: {strategy_name}")
                                else:
                                    logging.error(f"❌ Emergency creation failed: {strategy_name}")
                            except Exception as e:
                                logging.error(f"❌ Emergency creation exception: {e}")
                                import traceback
                                traceback.print_exc()

            # Start API server
            await self.api_server.start_api_server(api_port)

            # Start the coordination loop
            self._hive_clock_task = asyncio.create_task(self._run_hive_coordination())

            # Skip dashboard registration - handled by activity/ingest heartbeat
            # await self._register_with_dashboard(enable_trading, api_port)
            logging.info("📊 Dashboard registration handled by activity/ingest heartbeat")

            mode_str = "REAL TRADING" if (enable_trading and connector_success) else "SIMULATION"
            logging.info(f"🚀 Dynamic Hive started successfully in {mode_str} mode!")
            logging.info(f"🌐 API available at: http://localhost:{api_port}")
            logging.info(f"📊 Loaded {len(self.strategies)} strategies from database")

            return True

        except Exception as e:
            logging.error(f"❌ Failed to start Hive: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def load_strategies_from_database(self):
        """Load all enabled strategies from database and create strategy instances."""
        logging.info("📚 LOADING STRATEGIES FROM DATABASE...")
        configs = self.database.load_all_strategies(enabled_only=True)
        logging.info(f"📚 Found {len(configs)} enabled strategies in database")
        loaded_count = 0
        real_strategies_created = 0

        for config in configs:
            # Create simulated strategy info (for compatibility)
            strategy_info = DynamicStrategyInfo(config)
            strategy_info.is_running = True
            strategy_info.start_time = time.time()
            self.strategies[config.name] = strategy_info

            # If real connector is available, also create REAL strategy instance
            connector = self.real_connector  # Get connector reference
            logging.info(f"🔧 Real connector status: {connector is not None} (type: {type(connector).__name__ if connector else 'None'})")

            if connector:
                logging.info(f"🔧 Attempting to create REAL strategy: {config.name}")
                real_created = await self.create_real_strategy(config, save_to_db=False)
                if real_created:
                    # Start the real strategy
                    logging.info(f"🚀 Starting REAL strategy: {config.name}")
                    start_success = self.start_real_strategy(config.name)
                    if start_success:
                        real_strategies_created += 1
                        logging.info(f"✅ Created and started REAL strategy: {config.name}")
                    else:
                        logging.error(f"❌ Failed to START real strategy: {config.name}")
                else:
                    logging.error(f"❌ Failed to CREATE real strategy: {config.name}")
            else:
                logging.warning(f"⚠️ No real connector available for strategy: {config.name}")

            loaded_count += 1
            logging.info(f"✅ Loaded strategy from DB: {config.name}")

        if real_strategies_created > 0:
            logging.info(f"🚀 Loaded {loaded_count} strategies from database ({real_strategies_created} REAL, {loaded_count - real_strategies_created} simulated)")
        else:
            logging.info(f"📊 Loaded {loaded_count} strategies from database (all simulated - no real connector)")

    async def add_strategy_dynamically(self, config: DynamicStrategyConfig) -> bool:
        """Add a new strategy while Hive is running."""
        try:
            logging.info(f"🚀 DYNAMIC STRATEGY ADD CALLED: {config.name} with market {config.market}")
            if config.name in self.strategies:
                logging.warning(f"Strategy {config.name} already exists")
                return False

            # Check if new trading pair is needed and add it dynamically
            current_supported_pairs = self.connector_manager.get_supported_trading_pairs()
            logging.info(f"🔍 Strategy {config.name} requests {config.market}, currently available: {current_supported_pairs}")

            if config.market not in current_supported_pairs:
                logging.info(f"🔄 New trading pair {config.market} needed - adding to running connector")
                try:
                    # Add the new trading pair to the running connector
                    success = await self.connector_manager.add_trading_pairs([config.market])
                    if success:
                        logging.info(f"✅ Successfully added trading pair {config.market} to running connector")
                        # Update current pairs list after successful addition
                        updated_pairs = self.connector_manager.get_supported_trading_pairs()
                        logging.info(f"📊 Updated available pairs: {updated_pairs}")
                    else:
                        logging.warning(f"⚠️ Failed to add trading pair {config.market} to connector, strategy may not work properly")
                except Exception as e:
                    logging.error(f"❌ Error adding trading pair {config.market}: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                logging.info(f"✅ Trading pair {config.market} already available")

            # Save to database
            if not self.database.save_strategy(config):
                return False

            # Add to running strategies
            strategy_info = DynamicStrategyInfo(config)
            strategy_info.is_running = True
            strategy_info.start_time = time.time()
            self.strategies[config.name] = strategy_info

            # Create real strategy if connector available
            if self.real_connector:
                await self.create_real_strategy(config, save_to_db=False)
                self.start_real_strategy(config.name)

            # Sync to PostgreSQL for dashboard
            if self.postgres_sync_enabled:
                strategy_data = {
                    'name': config.name,
                    'status': 'active',
                    'total_actions': 0,
                    'successful_orders': 0,
                    'failed_orders': 0,
                    'refresh_interval': config.order_refresh_time,
                    'performance_per_min': 0.0
                }
                sync_strategy_to_postgres(strategy_data)

            logging.info(f"🔥 HOT-ADDED strategy: {config.name} (spread: {config.bid_spread}%, refresh: {config.order_refresh_time}s)")
            return True

        except Exception as e:
            logging.error(f"Failed to add strategy {config.name}: {e}")
            return False

    async def remove_strategy_dynamically(self, name: str) -> bool:
        """Remove a strategy while Hive is running."""
        try:
            if name not in self.strategies:
                logging.warning(f"Strategy {name} not found")
                return False

            # Stop and remove real strategy if exists
            if name in self.real_strategies:
                self.stop_real_strategy(name)
                del self.real_strategies[name]

            # Remove from running strategies
            strategy_info = self.strategies.pop(name)
            logging.info(f"🔥 HOT-REMOVED strategy: {name} (had {strategy_info.actions_count} actions)")

            # Update database status
            self.database.update_strategy_status(name, False)

            # Remove from PostgreSQL
            if self.postgres_sync_enabled:
                postgres_sync = get_postgres_sync()
                postgres_sync.remove_strategy(name)

            return True

        except Exception as e:
            logging.error(f"Failed to remove strategy {name}: {e}")
            return False

    async def update_strategy_config_dynamically(self, name: str, new_config: DynamicStrategyConfig) -> bool:
        """Update strategy configuration while running."""
        try:
            if name not in self.strategies:
                logging.warning(f"Strategy {name} not found")
                return False

            # Update database
            if not self.database.save_strategy(new_config):
                return False

            # Update running strategy
            self.strategies[name].update_config(new_config)

            # Update real strategy if exists
            if name in self.real_strategies:
                # For now, log the update - in future could implement hot config updates
                logging.info(f"🔄 Real strategy {name} config updated (requires restart for full effect)")

            logging.info(f"🔄 Updated strategy config: {name}")
            return True

        except Exception as e:
            logging.error(f"Failed to update strategy {name}: {e}")
            return False

    async def create_strategy_instance(self, config: DynamicStrategyConfig) -> bool:
        """Create a strategy instance - API compatibility method."""
        return await self.create_real_strategy(config, save_to_db=True)

    async def create_real_strategy(self, config: DynamicStrategyConfig, save_to_db: bool = True) -> bool:
        """Create a real Hummingbot strategy instance."""
        if not self.real_connector:
            logging.error("❌ Real connector not initialized")
            return False

        if config.name in self.real_strategies:
            logging.warning(f"⚠️ Real strategy {config.name} already exists")
            return False

        try:
            # Create real strategy instance
            logging.info(f"🔧 Creating RealStrategyInstance for {config.name}")
            real_strategy = RealStrategyInstance(config.name, config, self.real_connector)

            # Initialize the strategy
            logging.info(f"🔧 Initializing real strategy: {config.name}")
            if real_strategy.initialize_strategy():
                self.real_strategies[config.name] = real_strategy
                logging.info(f"✅ Real strategy initialized and added to registry: {config.name}")

                # Save to database only if requested
                if save_to_db:
                    self.database.save_strategy(config)

                logging.info(f"✅ Created real strategy: {config.name}")
                return True
            else:
                logging.error(f"❌ Failed to initialize real strategy: {config.name}")
                logging.error("   Check RealStrategyInstance.initialize_strategy() method errors above")
                return False

        except Exception as e:
            logging.error(f"❌ Failed to create real strategy {config.name}: {e}")
            import traceback
            traceback.print_exc()
            return False

    def start_real_strategy(self, name: str) -> bool:
        """Start a real strategy."""
        if name not in self.real_strategies:
            logging.error(f"❌ Real strategy {name} not found")
            return False

        # Set up callback for order events
        self.real_strategies[name].set_orchestrator_callback(self._on_strategy_order_event)
        logging.info(f"🔗 Set up order event callback for strategy {name}")

        # **FIXED**: Pass the trading core to properly register strategy
        return self.real_strategies[name].start(trading_core=self)

    def stop_real_strategy(self, name: str) -> bool:
        """Stop a real strategy."""
        if name not in self.real_strategies:
            logging.error(f"❌ Real strategy {name} not found")
            return False

        self.real_strategies[name].stop()
        return True

    def _on_strategy_order_event(self, strategy_name: str, action: str, success: bool, event_data: dict):
        """Handle order events from real strategies."""
        try:
            # Extract order details from event
            order_id = event_data.get('order_id', 'N/A')
            price = event_data.get('price', 0)
            amount = event_data.get('amount', 0)
            trading_pair = event_data.get('trading_pair', 'N/A')

            # Update monitoring with real order details
            self._update_monitor_activity(
                strategy_name,
                action,
                success,
                order_id=order_id,
                price=price,
                amount=amount,
                trading_pair=trading_pair
            )

            # Track the order in pending orders if it's a creation event
            if action in ["BUY_ORDER", "SELL_ORDER"] and success and order_id != 'N/A':
                self.pending_orders[order_id] = strategy_name
                logging.info(f"📊 {strategy_name}: {action} {order_id} @ ${price:.2f}")

        except Exception as e:
            logging.error(f"❌ Error handling strategy order event: {e}")

    async def _run_hive_coordination(self):
        """Main coordination loop."""
        logging.info("🔄 Starting Hive coordination loop")

        while self._hive_running:
            try:
                await self.process_dynamic_hive_cycle()

                # Clean up old pending orders every 100 cycles (roughly every 1.5 minutes)
                if self.total_cycles % 100 == 0:
                    self._cleanup_old_pending_orders()

                # Update dashboard every 60 cycles (about once per minute)
                if self.total_cycles % 60 == 0:
                    await self._update_dashboard_status()

                # Sync to PostgreSQL every 30 cycles (about every 30 seconds)
                if self.postgres_sync_enabled and self.total_cycles % 30 == 0:
                    await self._sync_all_strategies_to_postgres()

                # Send activities to dashboard every 10 cycles (about every 10 seconds)
                if self.total_cycles % 10 == 0:
                    try:
                        self._save_monitor_data_to_api()
                        logging.debug(f"📤 Activity data sent to dashboard (cycle {self.total_cycles})")
                    except Exception as e:
                        logging.debug(f"⚠️ Activity sync error: {e}")

                await asyncio.sleep(1.0)  # 1-second coordination cycle
            except Exception as e:
                logging.error(f"❌ Hive coordination error: {e}")
                await asyncio.sleep(5.0)

    async def process_dynamic_hive_cycle(self):
        """Process one cycle of the dynamic Hive."""
        self.total_cycles += 1
        current_time = time.time()

        # Update market data if we have a connector
        if self.real_connector:
            try:
                # Get available trading pairs and select the best one for shared market data
                available_books = list(self.real_connector.order_books.keys())
                if available_books:
                    logging.info(f"📊 Available trading pairs from connector: {available_books}")

                    # Select trading pair based on strategy priorities
                    trading_pair = self._select_market_data_pair(available_books)
                    logging.info(f"📊 Selected trading pair for shared data: {trading_pair}")

                    # Validate that strategy pairs are available
                    strategy_pairs = [info.config.market for info in self.strategies.values() if info.is_running]
                    missing_pairs = [pair for pair in strategy_pairs if pair not in available_books]
                    if missing_pairs:
                        logging.warning(f"⚠️ Missing trading pairs for strategies: {missing_pairs}")
                        logging.info(f"💡 Available pairs: {available_books}")
                        logging.info("💡 Consider updating strategies to use available pairs")
                    order_book = self.real_connector.order_books[trading_pair]

                    # Get real bid/ask prices from order book - CORRECT METHOD CALLS
                    best_bid = order_book.get_price(is_buy=True)  # Fixed: use is_buy parameter
                    best_ask = order_book.get_price(is_buy=False)  # Fixed: use is_buy parameter

                    logging.info(f"📊 Using order book for {trading_pair}: bid=${best_bid}, ask=${best_ask}")

                    if best_bid and best_ask:
                        # Ensure all prices are Decimal for consistent calculations
                        from decimal import Decimal
                        best_bid = Decimal(str(best_bid))
                        best_ask = Decimal(str(best_ask))
                        mid_price = (best_bid + best_ask) / Decimal("2")
                        spread = best_ask - best_bid

                        self.shared_market_data = {
                            "symbol": trading_pair,
                            "price": float(mid_price),  # For monitor compatibility
                            "mid_price": mid_price,     # For order calculations
                            "best_bid": best_bid,
                            "best_ask": best_ask,
                            "spread": spread,
                            "timestamp": current_time,
                            "source": "REAL_HYPERLIQUID_PERPETUAL_TESTNET"
                        }

                        self.last_market_update = current_time
                        logging.debug(f"📊 REAL market data: {trading_pair} ${mid_price:.6f}")
                    else:
                        logging.debug(f"⚠️ No bid/ask data available for {trading_pair}")
                else:
                    logging.debug("📊 No order books available yet - connector still initializing")
            except Exception as e:
                logging.debug(f"Market data update failed: {e}")
                import traceback
                logging.debug(f"Traceback: {traceback.format_exc()}")

        # Process each strategy
        for name, strategy_info in list(self.strategies.items()):
            if not strategy_info.is_running:
                continue

            # Check if it's time for this strategy to act
            time_since_last_action = current_time - strategy_info.last_action_time

            if time_since_last_action >= strategy_info.config.order_refresh_time:
                await self._execute_strategy_action(strategy_info)
                strategy_info.last_action_time = current_time
                strategy_info.actions_count += 1
                self.total_actions += 1

        # Update monitor if enabled
        if self.enable_monitor:
            self._update_monitor()

        # Calculate performance metrics
        for strategy_info in self.strategies.values():
            strategy_info.calculate_performance_metrics(current_time)

    async def _execute_strategy_action(self, strategy_info: DynamicStrategyInfo):
        """Execute action for a strategy."""
        try:
            config = strategy_info.config

            # Get market data specific to this strategy's trading pair
            if not self.real_connector or not self.real_connector.order_books:
                logging.debug(f"No connector or order books for {strategy_info.name}")
                return

            strategy_pair = config.market
            if strategy_pair not in self.real_connector.order_books:
                logging.warning(f"⚠️ Trading pair {strategy_pair} not available for strategy {strategy_info.name}")
                available_pairs = list(self.real_connector.order_books.keys())
                logging.warning(f"⚠️ Available pairs: {available_pairs}")

                # Try to find a similar pair or suggest alternatives
                base_asset = strategy_pair.split('-')[0] if '-' in strategy_pair else strategy_pair
                similar_pairs = [p for p in available_pairs if p.startswith(base_asset)]
                if similar_pairs:
                    logging.info(f"💡 Similar pairs found: {similar_pairs}")
                    logging.info(f"💡 Consider updating strategy {strategy_info.name} to use one of these pairs")

                return

            # Get real-time market data for THIS strategy's trading pair
            order_book = self.real_connector.order_books[strategy_pair]
            best_bid = order_book.get_price(is_buy=True)
            best_ask = order_book.get_price(is_buy=False)

            if not best_bid or not best_ask:
                logging.debug(f"No bid/ask data for {strategy_pair} in strategy {strategy_info.name}")
                return

            from decimal import Decimal
            best_bid = Decimal(str(best_bid))
            best_ask = Decimal(str(best_ask))
            mid_price = (best_bid + best_ask) / Decimal("2")

            logging.debug(f"📊 Strategy {strategy_info.name} using {strategy_pair}: ${mid_price}")

            # Note: Spread calculations available if needed for future enhancements
            # bid_spread = Decimal(str(config.bid_spread))
            # ask_spread = Decimal(str(config.ask_spread))
            # bid_price = mid_price * (Decimal("1") - bid_spread)
            # ask_price = mid_price * (Decimal("1") + ask_spread)

            # Add realistic pass conditions based on strategy type
            # Determine if strategy should pass this tick based on its characteristics
            # **DISABLED FOR DEBUGGING**: Force execution to test order placement
            should_pass = False
            pass_reason = "FORCED_EXECUTION_FOR_DEBUG"

            # If strategy decides to pass this tick, record it and return
            if should_pass:
                self._update_monitor_activity(strategy_info.name, "PASS", True)
                logging.debug(f"⏸️ {strategy_info.name}: Pass - {pass_reason}")
                return

            # Execute real orders if we have a real strategy
            if strategy_info.name in self.real_strategies:
                real_strategy = self.real_strategies[strategy_info.name]
                if real_strategy.is_running:
                    # If strategy decides to pass this tick, record it and return
                    if should_pass:
                        self._update_monitor_activity(strategy_info.name, "PASS", True)
                        logging.debug(f"⏸️ {strategy_info.name}: Pass (real trading) - {pass_reason}")
                        return

                    try:
                        # **NATIVE PMM APPROACH**: Use PMM's native tick() method for proper order lifecycle
                        import time
                        current_timestamp = time.time()

                        # Let PMM strategy handle its own tick cycle with native cancellation logic
                        if hasattr(real_strategy, 'strategy') and real_strategy.strategy:
                            pmm_strategy = real_strategy.strategy

                            # Ensure PMM strategy has proper timing
                            if hasattr(pmm_strategy, '_current_timestamp'):
                                pmm_strategy._current_timestamp = current_timestamp

                            # Call PMM's native tick method - this handles:
                            # 1. Order age checking (max_order_age)
                            # 2. Price tolerance checking (order_refresh_tolerance_pct)
                            # 3. Automatic cancellation of outdated orders
                            # 4. Creation of new orders based on refresh_time
                            try:
                                # **PRE-DEBUG**: Check PMM state before tick
                                markets_ready = pmm_strategy.all_markets_ready() if hasattr(pmm_strategy, 'all_markets_ready') else False
                                active_orders_before = len(pmm_strategy.active_orders) if hasattr(pmm_strategy, 'active_orders') else 0

                                # PMM's tick method handles all order lifecycle management
                                pmm_strategy.tick(current_timestamp)

                                # **DEBUG**: Check if orders were created by PMM
                                active_orders = []
                                active_orders_after = 0
                                if hasattr(pmm_strategy, 'active_orders'):
                                    active_orders = pmm_strategy.active_orders
                                    active_orders_after = len(active_orders)

                                # **DIAGNOSTIC**: Log PMM state and balance info
                                if active_orders_after != active_orders_before:
                                    logging.info(f"🎯 {strategy_info.name}: Orders changed from {active_orders_before} to {active_orders_after}")

                                    # **BALANCE CHECK**: See if we have both BTC and USD for both sides
                                    if hasattr(pmm_strategy, '_sb_markets') and pmm_strategy._sb_markets:
                                        market = pmm_strategy._sb_markets[0]
                                        if hasattr(market, 'get_balance'):
                                            try:
                                                base_balance = market.get_balance('BTC')
                                                quote_balance = market.get_balance('USD')
                                                logging.info(f"💰 {strategy_info.name}: BTC balance: {base_balance}, USD balance: {quote_balance}")
                                            except Exception:
                                                pass

                                    # **ORDER ANALYSIS**: Check what types of orders exist
                                    if active_orders_after > 0:
                                        buy_orders = sum(1 for order in active_orders if hasattr(order, 'is_buy') and order.is_buy)
                                        sell_orders = sum(1 for order in active_orders if hasattr(order, 'is_buy') and not order.is_buy)
                                        logging.info(f"📊 {strategy_info.name}: {buy_orders} BUY orders, {sell_orders} SELL orders")

                                        # **CANCELLATION CHECK**: See if PMM is trying to cancel orders
                                        if hasattr(pmm_strategy, '_sb_order_tracker') and pmm_strategy._sb_order_tracker:
                                            in_flight_cancels = getattr(pmm_strategy._sb_order_tracker, 'in_flight_cancels', {})
                                            if len(in_flight_cancels) > 0:
                                                logging.info(f"🚫 {strategy_info.name}: {len(in_flight_cancels)} cancellation requests in flight")
                                            else:
                                                logging.warning(f"⚠️ {strategy_info.name}: No cancellation requests found - PMM may not be cancelling old orders!")

                                    # **SIMPLE SOLUTION**: If order count increased, assume new orders were placed
                                    if active_orders_after > active_orders_before:
                                        orders_added = active_orders_after - active_orders_before
                                        # Simulate order creation events for monitoring
                                        for i in range(orders_added):
                                            if i % 2 == 0:
                                                self._update_monitor_activity(strategy_info.name, "BUY_ORDER", True,
                                                                              order_id="PMM_BUY", price=0, amount=0, trading_pair=config.market)
                                            else:
                                                self._update_monitor_activity(strategy_info.name, "SELL_ORDER", True,
                                                                              order_id="PMM_SELL", price=0, amount=0, trading_pair=config.market)
                                        logging.info(f"📊 {strategy_info.name}: Detected {orders_added} new orders via count change")

                                if not markets_ready:
                                    logging.debug(f"⚠️ {strategy_info.name}: Markets not ready, PMM may not place orders")

                                # **FALLBACK**: If PMM created orders but events didn't fire, log them manually
                                if len(active_orders) > 0:
                                    for order in active_orders[-2:]:  # Get the last 2 orders
                                        if hasattr(order, 'client_order_id') and hasattr(order, 'creation_timestamp'):
                                            # Check if this is a new order (created in last 35 seconds - covers order_refresh_time)
                                            if current_timestamp - order.creation_timestamp < 35:
                                                action = "BUY_ORDER" if order.is_buy else "SELL_ORDER"
                                                # Use exchange order ID if available, fallback to client order ID
                                                order_id = getattr(order, 'exchange_order_id', None) or order.client_order_id
                                                self._update_monitor_activity(
                                                    strategy_info.name,
                                                    action,
                                                    True,
                                                    order_id=order_id,
                                                    price=float(order.price),
                                                    amount=float(order.quantity),
                                                    trading_pair=order.trading_pair
                                                )
                                                logging.info(f"📊 Manual capture: {action} {order.client_order_id} @ ${float(order.price):.2f}")

                                # **ENHANCED MONITORING**: Show PMM activity with current order count
                                pmm_action = f"PMM_ACTIVE_{active_orders_after}_ORDERS" if active_orders_after > 0 else "PMM_TICK"
                                self._update_monitor_activity(strategy_info.name, pmm_action, True)

                                # Update last action time
                                strategy_info.last_action_time = current_timestamp

                                logging.debug(f"✅ {strategy_info.name}: PMM tick executed successfully")

                            except Exception as tick_error:
                                logging.error(f"❌ {strategy_info.name}: PMM tick failed: {tick_error}")
                                import traceback
                                traceback.print_exc()

                                # Fallback: Emergency order cleanup if PMM tick fails
                                try:
                                    active_orders = []
                                    # Use order tracker to get active orders
                                    if hasattr(self.real_connector, '_order_tracker') and self.real_connector._order_tracker:
                                        for order_id in list(self.real_connector._order_tracker.active_orders.keys()):
                                            active_orders.append({"order_id": order_id})

                                    if active_orders:
                                        logging.warning(f"🚨 PMM tick failed, emergency cleanup of {len(active_orders)} orders")
                                        for order in active_orders:
                                            try:
                                                await self.real_connector.cancel_order(order["order_id"])
                                            except Exception:
                                                pass

                                except Exception as cleanup_error:
                                    logging.error(f"❌ Emergency cleanup failed: {cleanup_error}")
                        else:
                            logging.error(f"❌ {strategy_info.name}: No PMM strategy object found")
                            return

                    except Exception as e:
                        # Update monitor with failed activity
                        self._update_monitor_activity(strategy_info.name, "STRATEGY_ERROR", False)
                        logging.error(f"❌ Strategy execution failed for {strategy_info.name}: {e}")
            else:
                # For demo mode, also apply realistic pass conditions
                if should_pass:
                    self._update_monitor_activity(strategy_info.name, "PASS", True)
                    logging.debug(f"⏸️ {strategy_info.name}: Pass (simulated) - {pass_reason}")
                else:
                    # Demo mode: Only log basic action without creating fake order data
                    action_type = "BUY_ORDER" if strategy_info.actions_count % 2 == 0 else "SELL_ORDER"
                    logging.debug(f"📊 {strategy_info.name}: Demo {action_type} (no activity recorded)")
                    # No _update_monitor_activity call - only real orders create activities

        except Exception as e:
            logging.error(f"❌ Strategy execution error for {strategy_info.name}: {e}")

    def _update_monitor(self):
        """Update the terminal monitor data file."""
        if not self.enable_monitor:
            return

        try:
            # Save monitor data directly to file for external monitor process
            logging.info("🔄 Updating monitor data...")
            self._save_monitor_data_to_api()
        except Exception as e:
            logging.error(f"Monitor update error: {e}")

    def _update_monitor_activity(self, strategy_name: str, action_type: str, success: bool,
                                 order_id: str = None, price: float = None, amount: float = None,
                                 trading_pair: str = None):
        """Record activity data (always active, independent of monitor feature)."""

        try:
            # Add activity to recent activity tracking
            from datetime import datetime
            if not hasattr(self, 'recent_activity'):
                from collections import deque
                self.recent_activity = deque(maxlen=200)  # Increased to 200 for rich history

            activity_data = {
                'strategy': strategy_name,
                'action': action_type,
                'success': success,
                'time': datetime.now()
            }

            # Add order details if available
            if order_id:
                activity_data['order_id'] = order_id
            if price is not None:
                activity_data['price'] = price
            if amount is not None:
                activity_data['amount'] = amount
            if trading_pair:
                activity_data['trading_pair'] = trading_pair

            self.recent_activity.append(activity_data)

            # Update strategy metrics on strategy_info object
            if strategy_name in self.strategies:
                strategy_info = self.strategies[strategy_name]

                # Initialize counters if missing (helps with restarts)
                if not hasattr(strategy_info, 'successful_orders'):
                    strategy_info.successful_orders = 0
                if not hasattr(strategy_info, 'failed_orders'):
                    strategy_info.failed_orders = 0

                if success:
                    strategy_info.successful_orders += 1
                else:
                    strategy_info.failed_orders += 1

                # Ensure success + failed never exceeds total actions
                total_recorded = strategy_info.successful_orders + strategy_info.failed_orders
                if total_recorded > strategy_info.actions_count:
                    logging.warning(f"⚠️ Strategy {strategy_name} has more recorded actions ({total_recorded}) than total actions ({strategy_info.actions_count}). Adjusting...")
                    # Cap the counts to match total actions
                    if success:
                        strategy_info.successful_orders = min(strategy_info.successful_orders, strategy_info.actions_count)
                    else:
                        strategy_info.failed_orders = min(strategy_info.failed_orders, strategy_info.actions_count)

            # Sync to PostgreSQL for dashboard
            if self.postgres_sync_enabled and strategy_name in self.strategies:
                strategy_info = self.strategies[strategy_name]
                strategy_data = {
                    'name': strategy_name,
                    'status': 'active' if strategy_info.is_running else 'inactive',
                    'total_actions': strategy_info.actions_count,
                    'successful_orders': getattr(strategy_info, 'successful_orders', 0),
                    'failed_orders': getattr(strategy_info, 'failed_orders', 0),
                    'refresh_interval': strategy_info.config.order_refresh_time,
                    'performance_per_min': strategy_info.actions_per_minute
                }
                sync_strategy_to_postgres(strategy_data)

            # Always send activities to dashboard API (independent of monitor)
            self._save_monitor_data_to_api()
        except Exception as e:
            logging.debug(f"Activity update error: {e}")

    async def _sync_all_strategies_to_postgres(self):
        """Periodically sync all active strategies to PostgreSQL"""
        try:
            if not self.postgres_sync_enabled or not self.strategies:
                return

            strategies_data = []
            for name, strategy_info in self.strategies.items():
                if strategy_info.is_running:
                    strategy_data = {
                        'name': name,
                        'status': 'active',
                        'total_actions': strategy_info.actions_count,
                        'successful_orders': getattr(strategy_info, 'successful_orders', 0),
                        'failed_orders': getattr(strategy_info, 'failed_orders', 0),
                        'refresh_interval': strategy_info.config.order_refresh_time,
                        'performance_per_min': strategy_info.actions_per_minute
                    }
                    strategies_data.append(strategy_data)

            if strategies_data:
                synced_count = sync_all_strategies_to_postgres(strategies_data)
                if synced_count > 0:
                    logging.debug(f"📊 Synced {synced_count} strategies to PostgreSQL")

                # Cleanup inactive strategies
                postgres_sync = get_postgres_sync()
                active_names = [s['name'] for s in strategies_data]
                postgres_sync.cleanup_inactive_strategies(active_names)

        except Exception as e:
            logging.debug(f"PostgreSQL sync error: {e}")

    def _save_monitor_data_to_api(self):
        """Send monitor data to hivebot-manager API for centralized storage."""
        try:
            import socket
            from datetime import datetime

            import requests

            hostname = socket.gethostname()
            # Get hive instance identifier
            hive_id = self._get_instance_id()

            # Prepare strategy data
            strategies = []
            for name, strategy_info in self.strategies.items():
                # Prepare recent actions for this strategy from global activity
                strategy_actions = []
                if hasattr(self, 'recent_activity'):
                    # Get last 50 actions for this strategy
                    for activity in list(self.recent_activity):
                        if activity['strategy'] == name:
                            action_data = {
                                'time': activity['time'].isoformat(),
                                'type': activity['action'],
                                'success': activity['success']
                            }
                            # **FIXED**: Include order details if available
                            if 'order_id' in activity:
                                action_data['order_id'] = activity['order_id']
                            if 'price' in activity:
                                action_data['price'] = activity['price']
                            if 'amount' in activity:
                                action_data['amount'] = activity['amount']
                            if 'trading_pair' in activity:
                                action_data['trading_pair'] = activity['trading_pair']

                            strategy_actions.append(action_data)
                    # Keep only last 50 actions per strategy for pixel grid
                    strategy_actions = strategy_actions[-50:]

                strategies.append({
                    'strategy': name,
                    'total_actions': strategy_info.actions_count,
                    'successful_orders': getattr(strategy_info, 'successful_orders', 0),
                    'failed_orders': getattr(strategy_info, 'failed_orders', 0),
                    'last_action_time': datetime.now().isoformat() if strategy_info.actions_count > 0 else None,
                    'status': 'ACTIVE' if strategy_info.is_running else 'IDLE',
                    'refresh_interval': strategy_info.config.order_refresh_time,
                    'performance_per_min': strategy_info.performance_metrics.get('actions_per_minute', 0.0),
                    'recent_actions': strategy_actions
                })

            # Prepare recent activity data
            recent_activities = []
            if hasattr(self, 'recent_activity'):
                for activity in list(self.recent_activity)[-100:]:  # Last 100 global activities
                    activity_payload = {
                        'time': activity['time'].isoformat(),
                        'type': activity['action'],
                        'success': activity['success'],
                        'strategy': activity['strategy']
                    }
                    # Include order details if available
                    if 'order_id' in activity:
                        activity_payload['order_id'] = activity['order_id']
                    if 'price' in activity:
                        activity_payload['price'] = activity['price']
                    if 'amount' in activity:
                        activity_payload['amount'] = activity['amount']
                    if 'trading_pair' in activity:
                        activity_payload['trading_pair'] = activity['trading_pair']

                    recent_activities.append(activity_payload)

            # Prepare payload for API
            payload = {
                'hive_id': hive_id,
                'hostname': hostname,
                'api_port': getattr(self, 'api_port', None),
                'strategies': strategies,
                'activities': recent_activities,
                'market_data': {
                    'symbol': self.shared_market_data.get('symbol', 'BTC'),
                    'price': self.shared_market_data.get('price', 0.0),
                    'timestamp': datetime.now().isoformat(),
                    'connection_status': 'CONNECTED' if self.shared_market_data else 'DISCONNECTED'
                },
                'timestamp': datetime.now().isoformat()
            }

            # Send to hivebot-manager API (management center only)
            dashboard_base_url = getattr(self, 'dashboard_url', 'http://localhost:3000')
            success = False

            try:
                response = requests.post(
                    f"{dashboard_base_url}/api/activity/ingest",
                    json=payload,
                    timeout=15  # Increased timeout for large payloads with activity data
                )
                if response.status_code == 200:
                    success = True
                    logging.info(f"✅ Monitor data sent to dashboard at {dashboard_base_url}")
                else:
                    logging.warning(f"❌ Dashboard {dashboard_base_url} returned status {response.status_code}: {response.text}")
            except Exception as dashboard_error:
                logging.warning(f"❌ Failed to send to dashboard {dashboard_base_url}: {dashboard_error}")

            if not success:
                logging.warning("❌ Dashboard activity ingest failed, no data sent")

        except Exception as e:
            logging.error(f"❌ Failed to send monitor data to API: {e}")
            # No fallback - keep trying API only

    def _save_monitor_data_to_file_fallback(self, payload=None):
        """Fallback: Save monitor data to JSON file when API is unavailable."""
        try:
            import json
            from datetime import datetime

            if not payload:
                # Recreate payload if not provided
                payload = self._prepare_monitor_data_payload()

            # Convert to legacy format for file compatibility
            monitor_data = {
                'strategies': {s['strategy']: s for s in payload.get('strategies', [])},
                'market_data': payload.get('market_data', {}),
                'recent_activity': payload.get('activities', []),
                'last_update': payload.get('timestamp', datetime.now().isoformat())
            }

            # Write to monitor data file
            with open('hive_monitor_data.json', 'w') as f:
                json.dump(monitor_data, f, indent=2)

            logging.debug("📁 Monitor data saved to fallback file")

        except Exception as e:
            logging.debug(f"Failed to save monitor data to file: {e}")

    def _prepare_monitor_data_payload(self):
        """Prepare monitor data payload (helper for fallback)."""
        import socket
        from datetime import datetime

        hive_id = self._get_instance_id()

        strategies = []
        for name, strategy_info in self.strategies.items():
            strategies.append({
                'strategy': name,
                'total_actions': strategy_info.actions_count,
                'successful_orders': getattr(strategy_info, 'successful_orders', 0),
                'failed_orders': getattr(strategy_info, 'failed_orders', 0),
                'last_action_time': datetime.now().isoformat() if strategy_info.actions_count > 0 else None,
                'status': 'ACTIVE' if strategy_info.is_running else 'IDLE',
                'refresh_interval': strategy_info.config.order_refresh_time,
                'performance_per_min': strategy_info.performance_metrics.get('actions_per_minute', 0.0),
                'recent_actions': []
            })

        recent_activities = []
        if hasattr(self, 'recent_activity'):
            for activity in list(self.recent_activity)[-100:]:
                recent_activities.append({
                    'time': activity['time'].isoformat(),
                    'type': activity['action'],
                    'success': activity['success'],
                    'strategy': activity['strategy']
                })

        return {
            'hive_id': hive_id,
            'hostname': hostname,
            'strategies': strategies,
            'activities': recent_activities,
            'market_data': {
                'symbol': self.shared_market_data.get('symbol', 'BTC'),
                'price': self.shared_market_data.get('price', 0.0),
                'timestamp': datetime.now().isoformat(),
                'connection_status': 'CONNECTED' if self.shared_market_data else 'DISCONNECTED'
            },
            'timestamp': datetime.now().isoformat()
        }

    async def stop_hive(self):
        """Stop the dynamic Hive and clean up all Hummingbot components."""
        logging.info("🛑 Stopping Dynamic Hive...")
        self._hive_running = False

        # Stop all real strategies first
        for strategy_name in list(self.real_strategies.keys()):
            self.stop_real_strategy(strategy_name)

        # Stop TradingCore (this stops the clock)
        try:
            if hasattr(self, 'clock') and self.clock:
                await self.stop_clock()  # Use the correct async method to stop clock
                logging.info("✅ TradingCore clock stopped")
        except Exception as e:
            logging.error(f"❌ Error stopping TradingCore clock: {e}")

        if self._hive_clock_task:
            self._hive_clock_task.cancel()
            try:
                await self._hive_clock_task
            except asyncio.CancelledError:
                pass

        # Stop heartbeat task
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        # Stop position tracking task
        if self.position_tracking_task:
            self.position_tracking_task.cancel()
            try:
                await self.position_tracking_task
            except asyncio.CancelledError:
                pass
            logging.info("🎯 Position tracking stopped")

        # Stop API server
        await self.api_server.stop_api_server()
        logging.info("✅ Hive shutdown complete")

        # Stop connector
        await self.connector_manager.stop_connector()

        # Shutdown registration handled by activity/ingest stopping heartbeat
        logging.debug("🛑 Bot shutdown - heartbeat will stop automatically")

        logging.info("🐝 Dynamic Hive stopped successfully")

    async def sync_strategy_from_postgres(self, strategy_name: str) -> bool:
        """Sync strategy from PostgreSQL to SQLite and add to Hive."""
        try:
            logging.info(f"🔄 Attempting to sync strategy {strategy_name} from PostgreSQL")

            # For now, this is a placeholder since PostgreSQL sync is not fully implemented
            # In a full implementation, this would:
            # 1. Connect to PostgreSQL
            # 2. Fetch strategy configuration by name
            # 3. Save to local SQLite database
            # 4. Add to running Hive

            logging.warning(f"⚠️ PostgreSQL sync not implemented for {strategy_name}")
            return False

        except Exception as e:
            logging.error(f"❌ Error syncing strategy from PostgreSQL: {e}")
            return False

    def _start_heartbeat_task(self, api_port: int):
        """Start background heartbeat task to keep bot online in dashboard"""
        if self._heartbeat_task is None or self._heartbeat_task.done():
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop(api_port))
            logging.info("💓 Background heartbeat task started")

    async def _heartbeat_loop(self, api_port: int):
        """Background task that sends periodic heartbeats to dashboard"""
        import socket

        import requests

        while self._hive_running:
            try:
                await asyncio.sleep(30)  # Send heartbeat every 30 seconds

                instance_id = self._get_instance_id()
                bot_data = {
                    "id": instance_id,
                    "name": instance_id,
                    "status": "running",
                    "strategies": list(self.strategies.keys()),
                    "uptime": int(time.time() - (self.start_time or time.time())),
                    "total_strategies": len(self.strategies),
                    "total_actions": self.total_actions,
                    "actions_per_minute": self.total_actions / max((time.time() - (self.start_time or time.time())) / 60, 0.1),
                    "memory_usage": 150,
                    "cpu_usage": 25,
                    "api_port": api_port
                }

                response = requests.post(
                    "http://15.235.212.36:8091/api/bots",
                    json=bot_data,
                    timeout=2
                )

                if response.status_code == 200:
                    logging.debug("💓 Heartbeat sent successfully")
                else:
                    logging.warning(f"⚠️ Heartbeat failed with status {response.status_code}")

            except asyncio.CancelledError:
                logging.info("💓 Heartbeat task cancelled")
                break
            except Exception as e:
                logging.warning(f"⚠️ Heartbeat error: {e}")
                # Continue the loop even on errors
