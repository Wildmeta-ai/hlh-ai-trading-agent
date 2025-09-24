#!/usr/bin/env python3

"""
Hive Database Management Module - SQLite operations for dynamic strategy configurations.
"""

import json
import logging
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from hive_connector_factory import ConnectorType

# Import our universal components
from hive_strategy_factory import StrategyType


@dataclass
class UniversalStrategyConfig:
    """Universal configuration supporting all Hummingbot strategies and connectors."""

    # Basic identification
    name: str
    strategy_type: Union[str, StrategyType] = StrategyType.PURE_MARKET_MAKING
    connector_type: Union[str, ConnectorType] = ConnectorType.HYPERLIQUID_PERPETUAL
    trading_pairs: List[str] = None

    # Core strategy parameters (Pure Market Making)
    bid_spread: float = 0.05
    ask_spread: float = 0.05
    order_amount: float = 0.001
    order_levels: int = 1
    order_refresh_time: float = 5.0
    order_level_spread: float = 0.0
    order_level_amount: float = 0.0

    # Connector authentication
    api_key: str = ""           # Main wallet address (for Hyperliquid)
    api_secret: str = ""        # Agent wallet private key (for Hyperliquid)
    passphrase: str = ""
    private_key: str = ""       # For DEX or legacy support
    use_vault: bool = False     # Hyperliquid vault mode

    # Advanced strategy parameters (stored as JSON)
    strategy_params: Dict[str, Any] = None

    # Risk management
    inventory_target_base_pct: float = 50.0
    inventory_range_multiplier: float = 1.0
    hanging_orders_enabled: bool = False
    hanging_orders_cancel_pct: float = 10.0

    # Position management (for derivatives)
    leverage: int = 1
    position_mode: str = "ONEWAY"  # ONEWAY, HEDGE

    # Order management
    order_optimization_enabled: bool = True
    ask_order_optimization_depth: float = 0.0
    bid_order_optimization_depth: float = 0.0
    price_ceiling: float = -1.0  # -1 means no ceiling
    price_floor: float = -1.0    # -1 means no floor

    # Ping pong strategy specific
    ping_pong_enabled: bool = False

    # Cross exchange market making
    min_profitability: float = 0.003  # 0.3% minimum profit

    # Arbitrage specific
    min_price_diff_pct: float = 0.1
    max_order_size: float = 1.0

    # Status and metadata
    enabled: bool = True
    created_at: str = None
    updated_at: str = None

    def __post_init__(self):
        # Convert enums to strings for database storage
        if isinstance(self.strategy_type, StrategyType):
            self.strategy_type = self.strategy_type.value
        if isinstance(self.connector_type, ConnectorType):
            self.connector_type = self.connector_type.value

        # Default trading pairs - using PURR-USDC as it's available on Hyperliquid spot
        if self.trading_pairs is None:
            self.trading_pairs = ["PURR-USDC"]

        # Initialize strategy_params if None
        if self.strategy_params is None:
            self.strategy_params = {}

        # Set timestamps
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.updated_at is None:
            self.updated_at = self.created_at

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UniversalStrategyConfig':
        """Create instance from dictionary."""
        # Handle special JSON fields
        if 'trading_pairs' in data and isinstance(data['trading_pairs'], str):
            data['trading_pairs'] = json.loads(data['trading_pairs'])
        if 'strategy_params' in data and isinstance(data['strategy_params'], str):
            data['strategy_params'] = json.loads(data['strategy_params'])
        return cls(**data)


# Keep old class for backward compatibility
@dataclass
class DynamicStrategyConfig:
    """Legacy configuration class for backward compatibility."""
    name: str
    exchange: str = "hyperliquid_perpetual"
    market: str = "PURR-USDC"
    bid_spread: float = 0.05
    ask_spread: float = 0.05
    order_amount: float = 0.001
    order_levels: int = 1
    order_refresh_time: float = 5.0
    order_level_spread: float = 0.0
    order_level_amount: float = 0.0
    enabled: bool = True
    api_key: str = ""
    created_at: str = None
    updated_at: str = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.updated_at is None:
            self.updated_at = self.created_at

    def to_universal_config(self) -> UniversalStrategyConfig:
        """Convert to universal configuration."""
        return UniversalStrategyConfig(
            name=self.name,
            strategy_type=StrategyType.PURE_MARKET_MAKING,
            connector_type=ConnectorType.HYPERLIQUID_PERPETUAL,  # Map old exchange names
            trading_pairs=[self.market],
            bid_spread=self.bid_spread,
            ask_spread=self.ask_spread,
            order_amount=self.order_amount,
            order_levels=self.order_levels,
            order_refresh_time=self.order_refresh_time,
            order_level_spread=self.order_level_spread,
            order_level_amount=self.order_level_amount,
            api_key=self.api_key,
            enabled=self.enabled,
            created_at=self.created_at,
            updated_at=self.updated_at
        )


class HiveDynamicDatabase:
    """Database management for universal strategy configurations."""

    def __init__(self, db_path: str = "hive_strategies.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize SQLite database with universal strategy configuration table."""
        with sqlite3.connect(self.db_path) as conn:
            # Create new universal table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS universal_strategy_configs (
                    name TEXT PRIMARY KEY,
                    strategy_type TEXT NOT NULL,
                    connector_type TEXT NOT NULL,
                    trading_pairs TEXT NOT NULL,  -- JSON array

                    -- Core strategy parameters
                    bid_spread REAL DEFAULT 0.05,
                    ask_spread REAL DEFAULT 0.05,
                    order_amount REAL DEFAULT 0.001,
                    order_levels INTEGER DEFAULT 1,
                    order_refresh_time REAL DEFAULT 5.0,
                    order_level_spread REAL DEFAULT 0.0,
                    order_level_amount REAL DEFAULT 0.0,

                    -- Authentication
                    api_key TEXT DEFAULT '',
                    api_secret TEXT DEFAULT '',
                    passphrase TEXT DEFAULT '',
                    private_key TEXT DEFAULT '',

                    -- Advanced parameters (JSON)
                    strategy_params TEXT DEFAULT '{}',

                    -- Risk management
                    inventory_target_base_pct REAL DEFAULT 50.0,
                    inventory_range_multiplier REAL DEFAULT 1.0,
                    hanging_orders_enabled BOOLEAN DEFAULT FALSE,
                    hanging_orders_cancel_pct REAL DEFAULT 10.0,

                    -- Position management
                    leverage INTEGER DEFAULT 1,
                    position_mode TEXT DEFAULT 'ONEWAY',

                    -- Order management
                    order_optimization_enabled BOOLEAN DEFAULT TRUE,
                    ask_order_optimization_depth REAL DEFAULT 0.0,
                    bid_order_optimization_depth REAL DEFAULT 0.0,
                    price_ceiling REAL DEFAULT -1.0,
                    price_floor REAL DEFAULT -1.0,

                    -- Strategy-specific
                    ping_pong_enabled BOOLEAN DEFAULT FALSE,
                    min_profitability REAL DEFAULT 0.003,
                    min_price_diff_pct REAL DEFAULT 0.1,
                    max_order_size REAL DEFAULT 1.0,

                    -- Metadata
                    enabled BOOLEAN DEFAULT TRUE,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Keep legacy table for backward compatibility
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
                    api_key TEXT DEFAULT '',
                    enabled BOOLEAN DEFAULT TRUE,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Ensure legacy table has api_key column when migrating existing databases
            try:
                conn.execute("ALTER TABLE strategy_configs ADD COLUMN api_key TEXT DEFAULT ''")
            except sqlite3.OperationalError as e:
                if "duplicate column name" not in str(e).lower():
                    raise

            # Check if we need to migrate from legacy table
            self._migrate_legacy_data()

            # No default strategies - empty is empty
            # Spawned bots should start completely clean with no fake data

    def _migrate_legacy_data(self):
        """Migrate data from legacy strategy_configs table to universal table."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            legacy_strategies = conn.execute("SELECT * FROM strategy_configs").fetchall()

            for row in legacy_strategies:
                legacy_config = DynamicStrategyConfig(**dict(row))
                universal_config = legacy_config.to_universal_config()
                self.save_universal_strategy(universal_config)
                logging.info(f"🔄 Migrated legacy strategy: {legacy_config.name}")

    def _create_default_strategies(self):
        """Create default strategies showcasing different strategy types."""
        default_strategies = [
            # Pure Market Making strategies
            UniversalStrategyConfig(
                name="PMM_CONSERVATIVE",
                strategy_type=StrategyType.PURE_MARKET_MAKING,
                connector_type=ConnectorType.HYPERLIQUID_PERPETUAL,
                bid_spread=0.20, ask_spread=0.20,
                order_refresh_time=300.0, order_amount=0.001  # 5 minutes
            ),
            UniversalStrategyConfig(
                name="PMM_MODERATE",
                strategy_type=StrategyType.PURE_MARKET_MAKING,
                connector_type=ConnectorType.HYPERLIQUID_PERPETUAL,
                bid_spread=0.15, ask_spread=0.15,
                order_refresh_time=180.0, order_amount=0.001  # 3 minutes
            ),
            # Avellaneda Market Making
            UniversalStrategyConfig(
                name="AVELLANEDA_BTC",
                strategy_type=StrategyType.AVELLANEDA_MARKET_MAKING,
                connector_type=ConnectorType.HYPERLIQUID_PERPETUAL,
                trading_pairs=["PURR-USDC"],
                order_amount=0.001,
                strategy_params={
                    "risk_factor": 0.5,
                    "order_book_depth_factor": 0.1,
                    "order_amount_shape_factor": 0.0
                }
            ),
        ]

        for strategy in default_strategies:
            self.save_universal_strategy(strategy)

        print(f"✅ Initialized database with {len(default_strategies)} default strategies")

    def save_universal_strategy(self, config: UniversalStrategyConfig) -> bool:
        """Save or update universal strategy configuration."""
        try:
            config.updated_at = datetime.now().isoformat()
            if not config.created_at:
                config.created_at = config.updated_at

            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO universal_strategy_configs
                    (name, strategy_type, connector_type, trading_pairs,
                     bid_spread, ask_spread, order_amount, order_levels, order_refresh_time,
                     order_level_spread, order_level_amount,
                     api_key, api_secret, passphrase, private_key, strategy_params,
                     inventory_target_base_pct, inventory_range_multiplier,
                     hanging_orders_enabled, hanging_orders_cancel_pct,
                     leverage, position_mode,
                     order_optimization_enabled, ask_order_optimization_depth, bid_order_optimization_depth,
                     price_ceiling, price_floor,
                     ping_pong_enabled, min_profitability, min_price_diff_pct, max_order_size,
                     enabled, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    config.name, config.strategy_type, config.connector_type,
                    json.dumps(config.trading_pairs),
                    config.bid_spread, config.ask_spread, config.order_amount,
                    config.order_levels, config.order_refresh_time,
                    config.order_level_spread, config.order_level_amount,
                    config.api_key, config.api_secret, config.passphrase, config.private_key,
                    json.dumps(config.strategy_params),
                    config.inventory_target_base_pct, config.inventory_range_multiplier,
                    config.hanging_orders_enabled, config.hanging_orders_cancel_pct,
                    config.leverage, config.position_mode,
                    config.order_optimization_enabled, config.ask_order_optimization_depth,
                    config.bid_order_optimization_depth, config.price_ceiling, config.price_floor,
                    config.ping_pong_enabled, config.min_profitability,
                    config.min_price_diff_pct, config.max_order_size,
                    config.enabled, config.created_at, config.updated_at
                ))
            return True
        except Exception as e:
            logging.error(f"Failed to save universal strategy {config.name}: {e}")
            return False

    def load_universal_strategy(self, name: str) -> Optional[UniversalStrategyConfig]:
        """Load universal strategy configuration by name."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    "SELECT * FROM universal_strategy_configs WHERE name = ?",
                    (name,)
                ).fetchone()
                if row:
                    return UniversalStrategyConfig.from_dict(dict(row))
            return None
        except Exception as e:
            logging.error(f"Failed to load universal strategy {name}: {e}")
            return None

    def load_all_universal_strategies(self, enabled_only: bool = False) -> List[UniversalStrategyConfig]:
        """Load all universal strategy configurations."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                query = "SELECT * FROM universal_strategy_configs"
                if enabled_only:
                    query += " WHERE enabled = TRUE"
                query += " ORDER BY created_at"

                rows = conn.execute(query).fetchall()
                return [UniversalStrategyConfig.from_dict(dict(row)) for row in rows]
        except Exception as e:
            logging.error(f"Failed to load universal strategies: {e}")
            return []

    def delete_universal_strategy(self, name: str) -> bool:
        """Delete universal strategy configuration."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM universal_strategy_configs WHERE name = ?", (name,))
            return True
        except Exception as e:
            logging.error(f"Failed to delete universal strategy {name}: {e}")
            return False

    # Legacy methods for backward compatibility
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
                     api_key, enabled, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    config.name, config.exchange, config.market, config.bid_spread, config.ask_spread,
                    config.order_amount, config.order_levels, config.order_refresh_time,
                    config.order_level_spread, config.order_level_amount, config.api_key,
                    config.enabled, config.created_at, config.updated_at
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
