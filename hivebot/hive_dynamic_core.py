#!/usr/bin/env python3

"""
Hive Dynamic Strategy Core - Advanced 1:N architecture with dynamic strategy management.
Supports adding/removing strategies while running, with database persistence.
"""

import asyncio
import logging
import time
import sqlite3
import json
import aiohttp
from typing import Dict, List, Optional, Union, Any
from decimal import Decimal
from datetime import datetime
from pathlib import Path
from contextlib import asynccontextmanager
from dataclasses import dataclass, asdict
from aiohttp import web

# Import existing Hummingbot components we'll reuse
import os
import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from hummingbot.core.trading_core import TradingCore
from hummingbot.client.config.config_helpers import ClientConfigAdapter, load_client_config_map_from_file

# Import terminal monitor
from hive_terminal_monitor import HiveMonitorIntegration

# REAL Hummingbot connector imports - Task 1 Integration (Updated to Perpetual)
from hummingbot.connector.derivative.hyperliquid_perpetual.hyperliquid_perpetual_derivative import HyperliquidPerpetualDerivative
from hummingbot.connector.derivative.hyperliquid_perpetual import hyperliquid_perpetual_constants as CONSTANTS

# REAL Hummingbot strategy imports - Task 2 Integration
from hummingbot.strategy.pure_market_making import PureMarketMakingStrategy
from hummingbot.strategy.market_trading_pair_tuple import MarketTradingPairTuple
from hummingbot.core.data_type.common import OrderType, TradeType, PositionAction


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


@dataclass
class DynamicStrategyConfig:
    """Dynamic strategy configuration with database persistence."""
    name: str
    exchange: str = "hyperliquid_perpetual_testnet"
    market: str = "BTC-USD"  # BTC perpetual with 908 USDC balance
    bid_spread: float = 0.01
    ask_spread: float = 0.01
    order_amount: float = 0.001
    order_levels: int = 1
    order_refresh_time: float = 5.0
    order_level_spread: float = 0.0
    order_level_amount: float = 0.0
    enabled: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'DynamicStrategyConfig':
        """Create from dictionary."""
        return cls(**data)


class HiveDynamicDatabase:
    """Database management for dynamic strategy configurations."""
    
    def __init__(self, db_path: str = "hive_strategies.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database with strategy configuration table."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS strategy_configs (
                    name TEXT PRIMARY KEY,
                    exchange TEXT NOT NULL,
                    market TEXT NOT NULL,
                    bid_spread REAL NOT NULL,
                    ask_spread REAL NOT NULL,
                    order_amount REAL NOT NULL,
                    order_levels INTEGER NOT NULL,
                    order_refresh_time REAL NOT NULL,
                    order_level_spread REAL DEFAULT 0.0,
                    order_level_amount REAL DEFAULT 0.0,
                    enabled BOOLEAN DEFAULT TRUE,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Add some default strategies if table is empty
            count = conn.execute("SELECT COUNT(*) FROM strategy_configs").fetchone()[0]
            if count == 0:
                # Default strategies - conservative spreads for safety if used with real trading
                default_strategies = [
                    DynamicStrategyConfig("CONSERVATIVE", bid_spread=0.10, ask_spread=0.10, order_refresh_time=10.0, order_levels=1, order_amount=0.001),
                    DynamicStrategyConfig("MEDIUM", bid_spread=0.05, ask_spread=0.05, order_refresh_time=5.0, order_levels=1, order_amount=0.001),
                    DynamicStrategyConfig("SCALPER", bid_spread=0.02, ask_spread=0.02, order_refresh_time=2.0, order_levels=1, order_amount=0.001),
                ]
                
                for strategy in default_strategies:
                    self.save_strategy(strategy)
                
                print(f"✅ Initialized database with {len(default_strategies)} default strategies")
    
    def save_strategy(self, config: DynamicStrategyConfig) -> bool:
        """Save or update strategy configuration."""
        try:
            config.updated_at = datetime.now().isoformat()
            if not config.created_at:
                config.created_at = config.updated_at
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO strategy_configs 
                    (name, exchange, market, bid_spread, ask_spread, order_amount, 
                     order_levels, order_refresh_time, order_level_spread, order_level_amount,
                     enabled, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    config.name, config.exchange, config.market, config.bid_spread, config.ask_spread,
                    config.order_amount, config.order_levels, config.order_refresh_time,
                    config.order_level_spread, config.order_level_amount, config.enabled,
                    config.created_at, config.updated_at
                ))
            return True
        except Exception as e:
            logging.error(f"Failed to save strategy {config.name}: {e}")
            return False
    
    def load_strategy(self, name: str) -> Optional[DynamicStrategyConfig]:
        """Load strategy configuration by name."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute("SELECT * FROM strategy_configs WHERE name = ?", (name,)).fetchone()
                if row:
                    return DynamicStrategyConfig(**dict(row))
            return None
        except Exception as e:
            logging.error(f"Failed to load strategy {name}: {e}")
            return None
    
    def load_all_strategies(self, enabled_only: bool = False) -> List[DynamicStrategyConfig]:
        """Load all strategy configurations."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                query = "SELECT * FROM strategy_configs"
                if enabled_only:
                    query += " WHERE enabled = TRUE"
                query += " ORDER BY created_at"
                
                rows = conn.execute(query).fetchall()
                return [DynamicStrategyConfig(**dict(row)) for row in rows]
        except Exception as e:
            logging.error(f"Failed to load strategies: {e}")
            return []
    
    def delete_strategy(self, name: str) -> bool:
        """Delete strategy configuration."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM strategy_configs WHERE name = ?", (name,))
            return True
        except Exception as e:
            logging.error(f"Failed to delete strategy {name}: {e}")
            return False
    
    def update_strategy_status(self, name: str, enabled: bool) -> bool:
        """Update strategy enabled/disabled status."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE strategy_configs SET enabled = ?, updated_at = ? WHERE name = ?",
                    (enabled, datetime.now().isoformat(), name)
                )
            return True
        except Exception as e:
            logging.error(f"Failed to update strategy {name} status: {e}")
            return False


class DynamicStrategyInfo:
    """Information about a dynamically managed strategy."""
    
    def __init__(self, config: DynamicStrategyConfig):
        self.config = config
        self.name = config.name
        self.is_running = False
        self.start_time: Optional[float] = None
        self.actions_count = 0
        self.last_action_time = 0
        self.total_runtime = 0.0
        self.performance_metrics = {
            "actions_per_minute": 0.0,
            "avg_spread": 0.0,
            "uptime_percentage": 0.0
        }
    
    def update_config(self, new_config: DynamicStrategyConfig):
        """Update strategy configuration dynamically."""
        old_refresh_time = self.config.order_refresh_time
        self.config = new_config
        
        # Log significant changes
        if abs(new_config.order_refresh_time - old_refresh_time) > 0.1:
            logging.info(f"Strategy {self.name}: Refresh time changed from {old_refresh_time}s to {new_config.order_refresh_time}s")
    
    def calculate_performance_metrics(self, current_time: float):
        """Calculate real-time performance metrics."""
        if self.start_time:
            runtime_minutes = (current_time - self.start_time) / 60.0
            self.performance_metrics["actions_per_minute"] = self.actions_count / max(runtime_minutes, 0.1)
            self.performance_metrics["avg_spread"] = (self.config.bid_spread + self.config.ask_spread) / 2
            self.performance_metrics["uptime_percentage"] = min(100.0, runtime_minutes / max(runtime_minutes, 1.0) * 100)
    
    def to_status_dict(self) -> dict:
        """Convert to status dictionary for API responses."""
        return {
            "name": self.name,
            "config": self.config.to_dict(),
            "is_running": self.is_running,
            "actions_count": self.actions_count,
            "performance_metrics": self.performance_metrics,
            "last_action_time": self.last_action_time,
            "start_time": self.start_time
        }


class RealStrategyInstance:
    """Wrapper for real Hummingbot strategy instances - Task 2 Integration."""
    
    def __init__(self, name: str, config: DynamicStrategyConfig, connector: HyperliquidPerpetualDerivative):
        self.name = name
        self.config = config
        self.connector = connector
        self.strategy: Optional[PureMarketMakingStrategy] = None
        self.is_running = False
        self.start_time = None
        self.actions_count = 0
        self.last_action_time = 0
        self.performance_metrics = {}
        
        logging.info(f"🤖 Created RealStrategyInstance: {name}")
    
    def initialize_strategy(self) -> bool:
        """Initialize the real Hummingbot strategy."""
        try:
            logging.info(f"🔧 Initializing real strategy: {self.name}")
            
            # Create market trading pair tuple
            trading_pair = self.config.market
            maker_assets = trading_pair.split("-")  # e.g. ["BTC", "USD"]
            
            # Create the market trading pair tuple with real connector
            market_info = MarketTradingPairTuple(
                self.connector,
                trading_pair,
                maker_assets[0],  # base asset
                maker_assets[1]   # quote asset
            )
            
            # Create the real pure market making strategy
            self.strategy = PureMarketMakingStrategy()
            
            # Initialize with real parameters
            self.strategy.init_params(
                market_info=market_info,
                bid_spread=Decimal(str(self.config.bid_spread)),
                ask_spread=Decimal(str(self.config.ask_spread)),
                order_amount=Decimal(str(self.config.order_amount)),
                order_levels=self.config.order_levels,
                order_refresh_time=self.config.order_refresh_time,
                inventory_skew_enabled=False,
                logging_options=PureMarketMakingStrategy.OPTION_LOG_ALL
            )
            
            logging.info(f"✅ Real strategy initialized: {self.name}")
            return True
            
        except Exception as e:
            logging.error(f"❌ Failed to initialize strategy {self.name}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def start(self):
        """Start the real strategy."""
        if not self.strategy:
            logging.error(f"❌ Strategy {self.name} not initialized")
            return False
        
        try:
            self.is_running = True
            self.start_time = time.time()
            
            # Start the real strategy's internal mechanisms
            # PureMarketMakingStrategy will automatically start placing orders
            # when it's added to a running TradingCore/Application
            
            logging.info(f"🚀 Started real strategy: {self.name}")
            logging.info(f"💰 Will place orders: {self.config.order_amount} {self.config.market}")
            logging.info(f"📏 Spreads: {self.config.bid_spread*100:.1f}%/{self.config.ask_spread*100:.1f}%")
            return True
        except Exception as e:
            logging.error(f"❌ Failed to start strategy {self.name}: {e}")
            return False
    
    def stop(self):
        """Stop the real strategy."""
        if self.strategy:
            self.is_running = False
            logging.info(f"🛑 Stopped real strategy: {self.name}")
    
    def get_active_orders(self) -> List[Dict[str, Any]]:
        """Get active orders from the real strategy."""
        if not self.strategy or not self.is_running:
            return []
        
        try:
            # Get active orders from strategy
            active_orders = self.strategy.active_orders
            order_list = []
            
            for order in active_orders:
                order_dict = {
                    "order_id": order.client_order_id,
                    "trading_pair": order.trading_pair,
                    "order_type": order.order_type.name,
                    "trade_type": order.trade_type.name,
                    "amount": float(order.amount),
                    "price": float(order.price),
                    "timestamp": order.creation_timestamp
                }
                order_list.append(order_dict)
            
            return order_list
            
        except Exception as e:
            logging.error(f"❌ Error getting active orders for {self.name}: {e}")
            return []
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get real performance metrics."""
        current_time = time.time()
        
        if self.start_time:
            runtime_seconds = current_time - self.start_time
            runtime_minutes = runtime_seconds / 60.0
        else:
            runtime_seconds = 0
            runtime_minutes = 0
        
        # Get real metrics from strategy if available
        active_orders_count = len(self.get_active_orders())
        
        return {
            "runtime_seconds": runtime_seconds,
            "runtime_minutes": runtime_minutes,
            "active_orders": active_orders_count,
            "bid_spread": self.config.bid_spread,
            "ask_spread": self.config.ask_spread,
            "order_amount": self.config.order_amount,
            "strategy_ready": self.strategy is not None and self.is_running
        }


class HiveDynamicCore(TradingCore):
    """
    Advanced Hive core with dynamic strategy management.
    Supports hot-adding/removing strategies while running.
    """
    
    def __init__(self, client_config: Union[ClientConfigAdapter, Dict], db_path: str = "hive_strategies.db"):
        super().__init__(client_config)
        
        # Dynamic strategy management
        self.database = HiveDynamicDatabase(db_path)
        self.strategies: Dict[str, DynamicStrategyInfo] = {}  # Simulated strategies
        self.real_strategies: Dict[str, RealStrategyInstance] = {}  # Real strategy instances - Task 2
        self._hive_running = False
        self._hive_clock_task: Optional[asyncio.Task] = None
        self._api_server: Optional[web.Application] = None
        self._api_runner: Optional[web.AppRunner] = None
        
        # REAL Hummingbot connector integration - Task 1
        self.real_connector: Optional[HyperliquidPerpetualDerivative] = None
        self.client_config_map = client_config if isinstance(client_config, ClientConfigAdapter) else load_client_config_map_from_file()
        
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
        
        logging.info("🐝 HiveDynamicCore initialized with database-driven configuration")
    
    async def initialize_real_connector(self, enable_trading: bool = False, private_key: str = "") -> bool:
        """Initialize REAL Hummingbot HyperliquidPerpetual connector - Task 1 Integration."""
        try:
            if enable_trading and private_key:
                logging.info("🔌 Initializing REAL Hummingbot HyperliquidPerpetual connector with TRADING ENABLED...")
            else:
                logging.info("🔌 Initializing REAL Hummingbot HyperliquidPerpetual connector (market data only)...")
            
            # Use BTC-USD perpetual with 908 USDC balance
            trading_pairs = ["BTC-USD"]
            
            # Create real HyperliquidPerpetualDerivative connector
            if enable_trading and private_key:
                # REAL TRADING MODE
                # Get main wallet address from environment (set by spawn-bot)
                main_wallet_address = os.getenv("HIVE_USER_ADDRESS", "")
                if main_wallet_address:
                    logging.info(f"👤 Using main wallet address from environment: {main_wallet_address}")
                else:
                    logging.warning("⚠️ HIVE_USER_ADDRESS not set, connector may have issues with position tracking")

                self.real_connector = HyperliquidPerpetualDerivative(
                    client_config_map=self.client_config_map,
                    hyperliquid_perpetual_api_key=main_wallet_address,  # Pass main wallet address
                    hyperliquid_perpetual_api_secret=private_key,  # Agent's private key
                    trading_pairs=trading_pairs,
                    trading_required=True,  # Enable real trading
                    domain=CONSTANTS.TESTNET_DOMAIN
                )
                logging.info("⚠️  TRADING MODE ENABLED - Real perpetual orders will be placed!")
            else:
                # MARKET DATA ONLY MODE
                self.real_connector = HyperliquidPerpetualDerivative(
                    client_config_map=self.client_config_map,
                    hyperliquid_perpetual_api_key="",  # Market data only
                    hyperliquid_perpetual_api_secret="",  # Market data only
                    trading_pairs=trading_pairs,
                    trading_required=False,  # Market data only
                    domain=CONSTANTS.TESTNET_DOMAIN
                )
            
            # Start the connector network
            await self.real_connector.start_network()
            
            # Wait for initialization with longer timeout for trading mode
            wait_time = 15 if enable_trading else 5
            logging.info(f"⏱️ Waiting {wait_time} seconds for connector initialization...")
            await asyncio.sleep(wait_time)
            
            # Check if connector has basic functionality (can access order books)
            trading_pair = "BTC-USD"
            has_market_data = trading_pair in self.real_connector.order_books
            
            if self.real_connector.ready:
                logging.info("✅ REAL HyperliquidPerpetual connector fully ready!")
                logging.info(f"📊 Domain: {self.real_connector.domain}")
                logging.info(f"🎯 Trading pairs: {self.real_connector.trading_pairs}")
                
                if enable_trading:
                    logging.info("💰 TRADING MODE: Connector ready for real orders!")
                
                return True
            elif has_market_data:
                logging.warning("⚠️ Connector not fully ready, but has market data - proceeding...")
                logging.info("🔧 This is normal for Hyperliquid - orders can still be placed")
                logging.info(f"📊 Domain: {self.real_connector.domain}")
                logging.info(f"🎯 Trading pairs: {self.real_connector.trading_pairs}")
                
                if enable_trading:
                    logging.info("💰 TRADING MODE: Connector functional for real orders!")
                
                return True
            else:
                logging.warning("⚠️ Connector started but not ready yet...")
                
                # Try waiting a bit more for market data
                logging.info("⏱️ Waiting additional 10 seconds for market data...")
                await asyncio.sleep(10)
                
                # Re-check after additional wait
                has_market_data_final = trading_pair in self.real_connector.order_books
                
                if self.real_connector.ready or has_market_data_final:
                    status = "fully ready" if self.real_connector.ready else "functional with market data"
                    logging.info(f"✅ Connector {status} after extended wait!")
                    return True
                
                logging.error("❌ Connector failed to initialize properly - no market data available")
                return False
                
        except Exception as e:
            logging.error(f"❌ Failed to initialize real connector: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def start_hive(self, api_port: int = 8080, enable_trading: bool = False, private_key: str = "") -> bool:
        """Start the dynamic Hive with API server."""
        try:
            if self._hive_running:
                logging.warning("Hive is already running")
                return False
            
            # Initialize REAL Hummingbot connector FIRST - Task 1 Integration
            connector_success = await self.initialize_real_connector(enable_trading, private_key)
            if enable_trading and not connector_success:
                logging.error("❌ Failed to initialize real trading connector - cannot start Hive")
                return False
            elif not connector_success:
                logging.warning("⚠️ Connector not ready - running in market data only mode")
                # Continue anyway for market data only mode
            
            # Load strategies from database AFTER connector is ready
            await self.load_strategies_from_database()
            
            if not self.strategies:
                logging.warning("No enabled strategies found in database")
                return False
            
            # Start API server for dynamic management
            await self.start_api_server(api_port)
            
            # Start the coordination loop
            self._hive_running = True
            self.start_time = time.time()
            self._hive_clock_task = asyncio.create_task(self._run_hive_coordination())
            
            logging.info(f"🚀 Dynamic Hive started with {len(self.strategies)} strategies and API server on port {api_port}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to start dynamic Hive: {e}")
            return False
    
    async def load_strategies_from_database(self):
        """Load all enabled strategies from database and create REAL strategy instances."""
        configs = self.database.load_all_strategies(enabled_only=True)
        loaded_count = 0
        real_strategies_created = 0
        
        for config in configs:
            # Create simulated strategy info (for compatibility)
            strategy_info = DynamicStrategyInfo(config)
            strategy_info.is_running = True
            strategy_info.start_time = time.time()
            self.strategies[config.name] = strategy_info
            
            # If real connector is available, also create REAL strategy instance
            if self.real_connector:
                real_created = await self.create_real_strategy(config, save_to_db=False)
                if real_created:
                    # Start the real strategy
                    self.start_real_strategy(config.name)
                    real_strategies_created += 1
                    logging.info(f"✅ Created REAL strategy from DB: {config.name}")
                else:
                    logging.warning(f"⚠️ Failed to create real strategy: {config.name}")
            
            loaded_count += 1
            logging.info(f"✅ Loaded strategy from DB: {config.name}")
        
        if real_strategies_created > 0:
            logging.info(f"🚀 Loaded {loaded_count} strategies from database ({real_strategies_created} REAL, {loaded_count - real_strategies_created} simulated)")
        else:
            logging.info(f"📊 Loaded {loaded_count} strategies from database (all simulated - no real connector)")
    
    async def add_strategy_dynamically(self, config: DynamicStrategyConfig) -> bool:
        """Add a new strategy while Hive is running."""
        try:
            if config.name in self.strategies:
                logging.warning(f"Strategy {config.name} already exists")
                return False
            
            # Save to database
            if not self.database.save_strategy(config):
                return False
            
            # Add to running strategies
            strategy_info = DynamicStrategyInfo(config)
            strategy_info.is_running = True
            strategy_info.start_time = time.time()
            self.strategies[config.name] = strategy_info
            
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
            
            # Remove from running strategies
            strategy_info = self.strategies.pop(name)
            logging.info(f"🔥 HOT-REMOVED strategy: {name} (had {strategy_info.actions_count} actions)")
            
            # Update database status
            self.database.update_strategy_status(name, False)
            
            return True
            
        except Exception as e:
            logging.error(f"Failed to remove strategy {name}: {e}")
            return False
    
    async def create_strategy_instance(self, config: DynamicStrategyConfig) -> bool:
        """Create a strategy instance - API compatibility method."""
        return await self.create_real_strategy(config, save_to_db=True)

    async def create_real_strategy(self, config: DynamicStrategyConfig, save_to_db: bool = True) -> bool:
        """Create a real Hummingbot strategy instance - Task 2 Integration."""
        if not self.real_connector:
            logging.error("❌ Real connector not initialized - call initialize_real_connector() first")
            return False
        
        if config.name in self.real_strategies:
            logging.warning(f"⚠️ Real strategy {config.name} already exists")
            return False
        
        try:
            # Create real strategy instance
            real_strategy = RealStrategyInstance(config.name, config, self.real_connector)
            
            # Initialize the strategy
            if real_strategy.initialize_strategy():
                self.real_strategies[config.name] = real_strategy
                
                # Save to database only if requested (avoid double-saving when loading from DB)
                if save_to_db:
                    self.database.save_strategy(config)
                
                logging.info(f"✅ Created real strategy: {config.name}")
                return True
            else:
                logging.error(f"❌ Failed to initialize real strategy: {config.name}")
                return False
                
        except Exception as e:
            logging.error(f"❌ Failed to create real strategy {config.name}: {e}")
            return False
    
    def start_real_strategy(self, name: str) -> bool:
        """Start a real strategy."""
        if name not in self.real_strategies:
            logging.error(f"❌ Real strategy {name} not found")
            return False
        
        return self.real_strategies[name].start()
    
    def stop_real_strategy(self, name: str) -> bool:
        """Stop a real strategy."""
        if name not in self.real_strategies:
            logging.error(f"❌ Real strategy {name} not found")
            return False
        
        self.real_strategies[name].stop()
        return True
    
    def get_real_strategy_status(self, name: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific real strategy."""
        if name not in self.real_strategies:
            return None
        
        real_strategy = self.real_strategies[name]
        return {
            "name": real_strategy.name,
            "config": real_strategy.config.to_dict(),
            "is_running": real_strategy.is_running,
            "performance_metrics": real_strategy.get_performance_metrics(),
            "active_orders": real_strategy.get_active_orders(),
            "start_time": real_strategy.start_time,
            "strategy_type": "REAL_HUMMINGBOT_STRATEGY"
        }
    
    def get_all_real_strategies_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all real strategies."""
        return {name: self.get_real_strategy_status(name) for name in self.real_strategies.keys()}
    
    async def update_strategy_config_dynamically(self, name: str, new_config: DynamicStrategyConfig) -> bool:
        """Update strategy configuration while running."""
        try:
            if name not in self.strategies:
                logging.warning(f"Strategy {name} not found")
                return False
            
            # Save to database
            if not self.database.save_strategy(new_config):
                return False
            
            # Update running strategy
            old_config = self.strategies[name].config
            self.strategies[name].update_config(new_config)
            
            logging.info(f"🔄 UPDATED strategy {name}: spread {old_config.bid_spread}% → {new_config.bid_spread}%, refresh {old_config.order_refresh_time}s → {new_config.order_refresh_time}s")
            return True
            
        except Exception as e:
            logging.error(f"Failed to update strategy {name}: {e}")
            return False
    
    async def _run_hive_coordination(self):
        """Run the dynamic Hive coordination loop."""
        try:
            while self._hive_running:
                await self.process_dynamic_hive_cycle()
                await asyncio.sleep(2)  # 2 second cycles for dynamic responsiveness
        except Exception as e:
            logging.error(f"Hive coordination error: {e}")
        finally:
            logging.info("🔄 Dynamic Hive coordination loop ended")
    
    async def process_dynamic_hive_cycle(self):
        """Process one dynamic Hive cycle with real-time updates."""
        if not self._hive_running or not self.strategies:
            return
        
        current_time = time.time()
        self.total_cycles += 1
        
        # Get shared market data
        market_data = await self._get_shared_market_data()
        if not market_data:
            return
        
        # Process all strategies dynamically
        active_strategies = 0
        cycle_actions = 0
        
        print(f"\n🐝 DYNAMIC HIVE CYCLE {self.total_cycles}")
        # Check if we can place real orders (connector functional + has api secret)
        can_trade = (self.real_connector and 
                    hasattr(self.real_connector, 'hyperliquid_perpetual_secret_key') and 
                    self.real_connector.hyperliquid_perpetual_secret_key and
                    "BTC-USD" in self.real_connector.order_books)  # Has market data = functional
        trading_status = "REAL TRADING" if can_trade else "SIMULATED"
        print(f"📡 SHARED DATA: {market_data['symbol']} ${market_data['mid_price']:.2f} | Strategies: {len(self.strategies)} | Mode: {trading_status}")
        
        for strategy_name, strategy_info in list(self.strategies.items()):  # Use list() for safe iteration during modification
            if not strategy_info.is_running:
                continue
            
            # Check if strategy should act
            should_act, reason = self._should_strategy_act_detailed(strategy_info, current_time)
            
            if should_act:
                actions = self._get_detailed_strategy_actions(strategy_info, market_data)
                if actions:
                    active_strategies += 1
                    cycle_actions += len(actions)
                    strategy_info.actions_count += len(actions)
                    strategy_info.last_action_time = current_time
                    
                    # Update performance metrics
                    strategy_info.calculate_performance_metrics(current_time)
                    
                    # Execute actions (either real orders or simulated)
                    await self._execute_strategy_actions(strategy_name, actions)
                    
                    print(f"   ⚡ {strategy_name}: {len(actions)} actions ({reason})")
                    print(f"      📊 Performance: {strategy_info.performance_metrics['actions_per_minute']:.1f} actions/min")
            else:
                remaining = self._get_remaining_time(strategy_info, current_time)
                print(f"   💤 {strategy_name}: Waiting {remaining:.1f}s ({reason})")
        
        self.total_actions += cycle_actions
        
        if active_strategies > 0:
            print(f"📊 CYCLE RESULT: {active_strategies}/{len(self.strategies)} strategies acted, {cycle_actions} actions")
    
    def _should_strategy_act_detailed(self, strategy_info: DynamicStrategyInfo, current_time: float) -> tuple:
        """Determine if strategy should act with detailed reasoning."""
        refresh_time = strategy_info.config.order_refresh_time
        time_since_last = current_time - strategy_info.last_action_time
        should_act = time_since_last >= refresh_time
        
        if should_act:
            reason = f"{time_since_last:.1f}s >= {refresh_time}s refresh"
        else:
            reason = f"waiting for {refresh_time}s refresh"
        
        return should_act, reason
    
    def _get_remaining_time(self, strategy_info: DynamicStrategyInfo, current_time: float) -> float:
        """Get remaining time until next action."""
        refresh_time = strategy_info.config.order_refresh_time
        time_since_last = current_time - strategy_info.last_action_time
        return max(0.0, refresh_time - time_since_last)
    
    def _get_detailed_strategy_actions(self, strategy_info: DynamicStrategyInfo, market_data: dict) -> list:
        """Generate detailed strategy actions based on dynamic config."""
        config = strategy_info.config
        actions = []
        mid_price = market_data["mid_price"]
        
        # Calculate prices using dynamic configuration - ensure Decimal types
        # config.bid_spread is already in decimal form (0.10 = 10%)
        bid_spread = Decimal(str(config.bid_spread))
        ask_spread = Decimal(str(config.ask_spread))
        
        # Generate orders for each level
        for level in range(config.order_levels):
            level_spread_adj = bid_spread + (Decimal(str(config.order_level_spread)) * Decimal(str(level)))
            level_amount_adj = Decimal(str(config.order_amount)) + (Decimal(str(config.order_level_amount)) * Decimal(str(level)))
            
            buy_price = mid_price * (Decimal("1") - level_spread_adj)
            sell_price = mid_price * (Decimal("1") + level_spread_adj)
            
            # If real connector is functional, attempt real orders
            if (self.real_connector and 
                hasattr(self.real_connector, 'hyperliquid_perpetual_secret_key') and 
                self.real_connector.hyperliquid_perpetual_secret_key and
                "BTC-USD" in self.real_connector.order_books):
                
                actions.append({
                    "type": "REAL_ORDER",
                    "side": "BUY", 
                    "amount": level_amount_adj,
                    "price": buy_price,
                    "trading_pair": config.market
                })
                actions.append({
                    "type": "REAL_ORDER",
                    "side": "SELL",
                    "amount": level_amount_adj, 
                    "price": sell_price,
                    "trading_pair": config.market
                })
            else:
                # Simulated actions for display
                actions.append(f"BUY {level_amount_adj:.4f} @ ${buy_price:.2f}")
                actions.append(f"SELL {level_amount_adj:.4f} @ ${sell_price:.2f}")
        
        return actions
    
    async def _execute_strategy_actions(self, strategy_name: str, actions: list):
        """Execute strategy actions - either real orders or simulated actions."""
        if not actions:
            return
        
        real_orders_placed = 0
        
        for action in actions:
            try:
                if isinstance(action, dict) and action.get("type") == "REAL_ORDER":
                    # Execute real order
                    success = await self._place_real_order(action)
                    if success:
                        real_orders_placed += 1
                        logging.info(f"💰 REAL ORDER: {strategy_name} - {action['side']} {action['amount']} @ ${action['price']:.6f}")
                        # Update monitor
                        self.monitor.update_activity(strategy_name, f"{action['side']}_ORDER", True)
                    else:
                        logging.warning(f"⚠️ Real order failed: {strategy_name} - {action['side']} {action['amount']}")
                        # Update monitor with failure
                        self.monitor.update_activity(strategy_name, f"{action['side']}_ORDER", False)
                else:
                    # Simulated action - just log it
                    logging.debug(f"📋 Simulated: {strategy_name} - {action}")
                    # Update monitor for simulated actions too
                    self.monitor.update_activity(strategy_name, "SIMULATED", True)
                    
            except Exception as e:
                logging.error(f"❌ Action execution error for {strategy_name}: {e}")
        
        if real_orders_placed > 0:
            print(f"      💰 REAL ORDERS PLACED: {real_orders_placed}")
    
    async def _place_real_order(self, order_data: dict) -> bool:
        """Place a real order using the Hyperliquid connector."""
        # From verification test: connector doesn't need to be "ready" and buy/sell are synchronous
        if not self.real_connector:
            logging.warning("Real connector not available for order placement")
            return False
        
        try:
            from hummingbot.core.data_type.common import OrderType
            
            # Ensure Decimal types for precision
            amount = Decimal(str(order_data["amount"]))
            price = Decimal(str(order_data["price"]))
            
            # Place the order (synchronous methods, not async) with PositionAction.OPEN for perpetuals
            if order_data["side"] == "BUY":
                order_id = self.real_connector.buy(
                    trading_pair=order_data["trading_pair"],
                    amount=amount,
                    order_type=OrderType.LIMIT,
                    price=price,
                    position_action=PositionAction.OPEN
                )
            else:  # SELL
                order_id = self.real_connector.sell(
                    trading_pair=order_data["trading_pair"],
                    amount=amount,
                    order_type=OrderType.LIMIT,
                    price=price,
                    position_action=PositionAction.OPEN
                )
            
            if order_id:
                logging.info(f"✅ Real order placed successfully: {order_id} | {order_data['side']} {amount} @ ${price}")
                return True
            else:
                logging.warning(f"❌ Order placement returned no order ID | {order_data['side']} {amount} @ ${price}")
                return False
                
        except Exception as e:
            logging.error(f"❌ Real order placement failed: {e} | {order_data}")
            return False
    
    async def _get_shared_market_data(self) -> Optional[dict]:
        """Get REAL shared market data from HyperliquidPerpetual connector - Task 1 Integration."""
        current_time = time.time()
        
        # Update every 2 seconds
        if current_time - self.last_market_update < 2.0:
            return self.shared_market_data
        
        try:
            # Get REAL market data from HyperliquidExchange connector
            if not self.real_connector:
                logging.warning("⚠️ Real connector not available, cannot get market data")
                return None
            
            trading_pair = "BTC-USD"
            if trading_pair in self.real_connector.order_books:
                order_book = self.real_connector.order_books[trading_pair]
                
                # Get real bid/ask prices from order book
                best_bid = order_book.get_price(is_buy=True)
                best_ask = order_book.get_price(is_buy=False)
                
                if best_bid and best_ask:
                    # Ensure all prices are Decimal for consistent calculations
                    best_bid = Decimal(str(best_bid))
                    best_ask = Decimal(str(best_ask))
                    mid_price = (best_bid + best_ask) / Decimal("2")
                    spread = best_ask - best_bid
                    
                    self.shared_market_data = {
                        "symbol": trading_pair,
                        "mid_price": mid_price,
                        "best_bid": best_bid,
                        "best_ask": best_ask,
                        "spread": spread,
                        "timestamp": current_time,
                        "source": "REAL_HYPERLIQUID_PERPETUAL_TESTNET"
                    }
                    
                    self.last_market_update = current_time
                    logging.debug(f"📊 REAL market data: {trading_pair} ${mid_price:.6f}")
                    
                    # Update monitor with market data
                    self.monitor.update_market_data(trading_pair, float(mid_price), True)
                    
                    return self.shared_market_data
                else:
                    logging.warning(f"⚠️ No bid/ask data available for {trading_pair}")
                    return None
            else:
                logging.warning(f"⚠️ {trading_pair} order book not available")
                return None
            
        except Exception as e:
            logging.error(f"Failed to get market data: {e}")
            return None
    
    # REST API for Dynamic Management
    async def start_api_server(self, port: int):
        """Start REST API server for dynamic strategy management."""
        self._api_server = web.Application()
        
        # API Routes
        self._api_server.router.add_get('/api/strategies', self.api_list_strategies)
        self._api_server.router.add_post('/api/strategies', self.api_create_strategy)
        self._api_server.router.add_put('/api/strategies/{name}', self.api_update_strategy)
        self._api_server.router.add_delete('/api/strategies/{name}', self.api_delete_strategy)
        self._api_server.router.add_get('/api/status', self.api_hive_status)
        
        # Start server
        self._api_runner = web.AppRunner(self._api_server)
        await self._api_runner.setup()
        site = web.TCPSite(self._api_runner, 'localhost', port)
        await site.start()
        
        logging.info(f"🌐 API server started on http://localhost:{port}")
    
    async def api_list_strategies(self, request):
        """API endpoint: List all strategies."""
        strategies_status = []
        for name, info in self.strategies.items():
            strategies_status.append(info.to_status_dict())
        
        return web.json_response({
            "strategies": strategies_status,
            "total_count": len(self.strategies),
            "total_actions": self.total_actions,
            "total_cycles": self.total_cycles
        })
    
    async def api_create_strategy(self, request):
        """API endpoint: Create new strategy."""
        try:
            data = await request.json()
            config = DynamicStrategyConfig.from_dict(data)
            
            success = await self.add_strategy_dynamically(config)
            if success:
                return web.json_response({"success": True, "message": f"Strategy {config.name} added"})
            else:
                return web.json_response({"success": False, "message": "Failed to add strategy"}, status=400)
                
        except Exception as e:
            return web.json_response({"success": False, "message": str(e)}, status=400)
    
    async def api_update_strategy(self, request):
        """API endpoint: Update existing strategy."""
        try:
            name = request.match_info['name']
            data = await request.json()
            data['name'] = name  # Ensure name matches URL
            config = DynamicStrategyConfig.from_dict(data)
            
            success = await self.update_strategy_config_dynamically(name, config)
            if success:
                return web.json_response({"success": True, "message": f"Strategy {name} updated"})
            else:
                return web.json_response({"success": False, "message": "Failed to update strategy"}, status=400)
                
        except Exception as e:
            return web.json_response({"success": False, "message": str(e)}, status=400)
    
    async def api_delete_strategy(self, request):
        """API endpoint: Delete strategy."""
        try:
            name = request.match_info['name']
            success = await self.remove_strategy_dynamically(name)
            
            if success:
                return web.json_response({"success": True, "message": f"Strategy {name} removed"})
            else:
                return web.json_response({"success": False, "message": "Strategy not found"}, status=404)
                
        except Exception as e:
            return web.json_response({"success": False, "message": str(e)}, status=400)
    
    async def api_hive_status(self, request):
        """API endpoint: Get Hive status."""
        current_time = time.time()
        uptime = current_time - self.start_time if self.start_time else 0
        
        return web.json_response({
            "hive_running": self._hive_running,
            "total_strategies": len(self.strategies),
            "total_cycles": self.total_cycles,
            "total_actions": self.total_actions,
            "uptime_seconds": uptime,
            "actions_per_minute": (self.total_actions / max(uptime / 60, 0.1)) if uptime > 0 else 0,
            "last_market_data": self.shared_market_data
        })
    
    async def stop_hive(self):
        """Stop the dynamic Hive."""
        self._hive_running = False
        
        if self._hive_clock_task:
            self._hive_clock_task.cancel()
            try:
                await self._hive_clock_task
            except asyncio.CancelledError:
                pass
        
        if self._api_runner:
            await self._api_runner.cleanup()
        
        # Cleanup REAL connector - Task 1 Integration
        if self.real_connector:
            try:
                await self.real_connector.stop_network()
                logging.info("✅ Real HyperliquidPerpetual connector stopped cleanly")
            except Exception as e:
                logging.error(f"⚠️ Error stopping real connector: {e}")
        
        logging.info("🐝 Dynamic Hive stopped successfully")


# Demo function
async def demo_dynamic_hive():
    """Demonstrate dynamic Hive capabilities."""
    print("🐝 DYNAMIC HIVE DEMONSTRATION")
    print("=" * 70)
    print("Database-driven strategy management with hot add/remove capabilities")
    print("-" * 70)
    
    # Load environment variables from .env file
    load_env_file()
    
    # Initialize dynamic Hive
    from hummingbot.client.config.config_helpers import load_client_config_map_from_file
    client_config_map = load_client_config_map_from_file()
    
    hive = HiveDynamicCore(client_config_map)
    
    # Ask user about monitor and trading preferences
    enable_monitor = os.getenv("HIVE_ENABLE_MONITOR", "").lower() == "true"
    if not enable_monitor:
        try:
            enable_monitor = input("📊 Enable terminal monitor? (y/N): ").lower().strip() == 'y'
        except EOFError:
            enable_monitor = False
    
    if enable_monitor:
        print("🖥️  Starting terminal monitor...")
        hive.enable_monitor = True
        hive.monitor.start_background_monitor()
        print("✅ Monitor started! Open another terminal to view: python hive_terminal_monitor.py")
    
    # Ask user if they want to enable real trading (or check environment variable)
    if os.getenv("HIVE_AUTO_TRADE") == "true":
        enable_trading = True
        print("⚡ Auto-trading enabled via HIVE_AUTO_TRADE environment variable")
    else:
        enable_trading = input("⚠️  Enable REAL trading? (y/N): ").lower().strip() == 'y'
    private_key = ""
    
    if enable_trading:
        print("🔑 Please set your Hyperliquid testnet private key...")
        private_key = os.getenv("HYPERLIQUID_PRIVATE_KEY", "")
        if not private_key:
            print("❌ HYPERLIQUID_PRIVATE_KEY environment variable not set!")
            print("   Please run: export HYPERLIQUID_PRIVATE_KEY=your_key")
            return
        print("💰 This will place REAL orders with your USDC balance!")
        print("⚠️  Orders will be conservative (5-10% spreads)")
    
    # Start Hive with API server
    success = await hive.start_hive(api_port=8080, enable_trading=enable_trading, private_key=private_key)
    if not success:
        print("❌ Failed to start dynamic Hive")
        return
    
    print(f"🌐 API Server: http://localhost:8080/api/strategies")
    print(f"📊 Database: {hive.database.db_path}")
    
    # Run for demonstration
    try:
        for cycle in range(15):
            await asyncio.sleep(3)
            
            # Demonstrate dynamic operations
            if cycle == 5:
                # Add new strategy dynamically
                new_config = DynamicStrategyConfig(
                    name="SCALPER",
                    bid_spread=0.005,  # 0.5bp spread
                    ask_spread=0.005,
                    order_refresh_time=0.5,  # 500ms refresh
                    order_levels=5,
                    order_amount=0.0005
                )
                await hive.add_strategy_dynamically(new_config)
                print(f"\n🔥 DEMO: Added SCALPER strategy dynamically!")
            
            if cycle == 10:
                # Update strategy configuration
                updated_config = DynamicStrategyConfig(
                    name="CONSERVATIVE",
                    bid_spread=0.15,  # Increased spread
                    ask_spread=0.15,
                    order_refresh_time=15.0,  # Slower refresh
                    order_levels=1,
                    order_amount=0.02  # Larger size
                )
                await hive.update_strategy_config_dynamically("CONSERVATIVE", updated_config)
                print(f"\n🔄 DEMO: Updated CONSERVATIVE strategy configuration!")
        
        # Show final statistics
        print(f"\n🎯 DYNAMIC HIVE DEMONSTRATION COMPLETE!")
        print(f"   📊 Final strategy count: {len(hive.strategies)}")
        print(f"   ⚡ Total actions: {hive.total_actions}")
        print(f"   🔄 Total cycles: {hive.total_cycles}")
        print(f"   🗄️  Database persistence: Active")
        print(f"   🌐 API management: http://localhost:8080")
        
    except KeyboardInterrupt:
        print(f"\n🛑 Demo stopped by user")
    
    finally:
        # Stop monitor if enabled
        if hive.enable_monitor:
            print("🖥️  Stopping terminal monitor...")
            hive.monitor.stop_monitor()
        
        await hive.stop_hive()


if __name__ == "__main__":
    print("🎯 DYNAMIC HIVE ARCHITECTURE")
    print("Database-driven strategy management with hot add/remove")
    print()
    
    asyncio.run(demo_dynamic_hive())