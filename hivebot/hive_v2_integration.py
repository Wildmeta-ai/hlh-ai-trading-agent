#!/usr/bin/env python3

"""
Hive Strategy V2 Framework Integration - Modern controller-executor pattern support.
Integrates Hummingbot's V2 strategy framework with Hivebot's 1:N architecture.
"""

import asyncio
import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional, Type

# Strategy V2 Framework imports
try:
    from hummingbot.strategy_v2.controllers.directional_trading_controller import DirectionalTradingController
    from hummingbot.strategy_v2.controllers.generic_controller import GenericController
    from hummingbot.strategy_v2.controllers.market_making_controller_v2 import MarketMakingControllerV2
    from hummingbot.strategy_v2.executors.arbitrage_executor import ArbitrageExecutor
    from hummingbot.strategy_v2.executors.dca_executor import DCAExecutor

    # Executor imports
    from hummingbot.strategy_v2.executors.position_executor import PositionExecutor
    from hummingbot.strategy_v2.executors.twap_executor import TWAPExecutor

    # Models and utilities
    from hummingbot.strategy_v2.models.base import RunnableStatus
    from hummingbot.strategy_v2.models.executor_actions import CreateExecutorAction, StopExecutorAction
    from hummingbot.strategy_v2.strategy_framework import StrategyFramework
    from hummingbot.strategy_v2.utils.distributions import Distributions

    V2_AVAILABLE = True
    logging.info("✅ Strategy V2 framework available")

except ImportError as e:
    V2_AVAILABLE = False
    logging.warning(f"⚠️ Strategy V2 framework not available: {e}")

    # Create placeholder classes to prevent import errors
    class StrategyFramework:
        pass

    class MarketMakingControllerV2:
        pass

    class DirectionalTradingController:
        pass

    class GenericController:
        pass

from hive_connector_factory import ConnectorType

# Import our universal components
from hive_database import UniversalStrategyConfig
from hive_strategy_factory import StrategyType

# Core imports
from hummingbot.connector.connector_base import ConnectorBase
from hummingbot.core.data_type.trade_fee import TradeFeeBase


class HiveV2StrategyWrapper:
    """Wrapper for Strategy V2 instances to integrate with Hive's 1:N architecture."""

    def __init__(
        self,
        name: str,
        config: UniversalStrategyConfig,
        connectors: Dict[str, ConnectorBase]
    ):
        self.name = name
        self.config = config
        self.connectors = connectors
        self.strategy_framework: Optional[StrategyFramework] = None
        self.is_running = False
        self.start_time = None

        # V2 metrics
        self.total_executors_created = 0
        self.active_executors = {}
        self.completed_executors = []

        logging.info(f"🆕 Created V2 Strategy Wrapper: {name}")

    def initialize_strategy(self) -> bool:
        """Initialize the V2 strategy framework."""
        if not V2_AVAILABLE:
            logging.error("❌ Strategy V2 framework not available")
            return False

        try:
            # Create the strategy framework instance
            self.strategy_framework = StrategyFramework()

            # Configure based on strategy type
            success = self._configure_v2_strategy()

            if success:
                logging.info(f"✅ V2 Strategy initialized: {self.name}")
                return True
            else:
                logging.error(f"❌ Failed to configure V2 strategy: {self.name}")
                return False

        except Exception as e:
            logging.error(f"❌ Failed to initialize V2 strategy {self.name}: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _configure_v2_strategy(self) -> bool:
        """Configure the V2 strategy based on type."""
        try:
            # DynamicStrategyConfig doesn't have strategy_type field, default to PMM
            strategy_type = getattr(self.config, 'strategy_type', None)
            if strategy_type:
                strategy_type = StrategyType(strategy_type)
            else:
                strategy_type = StrategyType.PURE_MARKET_MAKING

            if strategy_type == StrategyType.PURE_MARKET_MAKING:
                return self._configure_market_making_v2()
            elif strategy_type == StrategyType.DIRECTIONAL_TRADING:
                return self._configure_directional_trading_v2()
            elif strategy_type == StrategyType.DCA:
                return self._configure_dca_v2()
            elif strategy_type == StrategyType.TWAP:
                return self._configure_twap_v2()
            else:
                # Use generic controller for unsupported types
                return self._configure_generic_v2()

        except Exception as e:
            logging.error(f"❌ Failed to configure V2 strategy: {e}")
            return False

    def _configure_market_making_v2(self) -> bool:
        """Configure V2 market making controller."""
        try:
            # Get primary connector and trading pair
            primary_connector = list(self.connectors.values())[0]
            primary_trading_pair = self.config.trading_pairs[0]

            # Create market making controller
            controller = MarketMakingControllerV2()

            # Configure controller parameters
            controller_config = {
                "connector_name": primary_connector.name,
                "trading_pair": primary_trading_pair,
                "order_amount": Decimal(str(self.config.order_amount)),
                "bid_spread": Decimal(str(self.config.bid_spread)),
                "ask_spread": Decimal(str(self.config.ask_spread)),
                "order_levels": self.config.order_levels,
                "order_refresh_time": self.config.order_refresh_time,
                "inventory_target_base_pct": Decimal(str(self.config.inventory_target_base_pct)),
                "hanging_orders_enabled": self.config.hanging_orders_enabled,
            }

            # Initialize controller
            controller.init_params(**controller_config)

            # Add to strategy framework
            self.strategy_framework.add_controller(controller)

            logging.info(f"✅ Configured V2 Market Making controller for {self.name}")
            return True

        except Exception as e:
            logging.error(f"❌ Failed to configure V2 market making: {e}")
            return False

    def _configure_directional_trading_v2(self) -> bool:
        """Configure V2 directional trading controller."""
        try:
            primary_connector = list(self.connectors.values())[0]
            primary_trading_pair = self.config.trading_pairs[0]

            controller = DirectionalTradingController()

            # Get directional trading parameters from strategy_params
            params = self.config.strategy_params or {}

            controller_config = {
                "connector_name": primary_connector.name,
                "trading_pair": primary_trading_pair,
                "order_amount": Decimal(str(self.config.order_amount)),
                "leverage": self.config.leverage,
                "side": params.get("side", "BUY"),  # BUY or SELL
                "entry_price": Decimal(str(params.get("entry_price", 0))),
                "take_profit": Decimal(str(params.get("take_profit", 0.02))),  # 2% default
                "stop_loss": Decimal(str(params.get("stop_loss", 0.01))),     # 1% default
            }

            controller.init_params(**controller_config)
            self.strategy_framework.add_controller(controller)

            logging.info(f"✅ Configured V2 Directional Trading controller for {self.name}")
            return True

        except Exception as e:
            logging.error(f"❌ Failed to configure V2 directional trading: {e}")
            return False

    def _configure_dca_v2(self) -> bool:
        """Configure V2 DCA (Dollar Cost Averaging) strategy."""
        try:
            primary_connector = list(self.connectors.values())[0]
            primary_trading_pair = self.config.trading_pairs[0]

            # Create DCA executor directly
            params = self.config.strategy_params or {}

            executor = DCAExecutor(
                strategy=self.strategy_framework,
                connector=primary_connector,
                trading_pair=primary_trading_pair,
                order_amount=Decimal(str(self.config.order_amount)),
                n_levels=params.get("n_levels", 5),
                spread_between_levels=Decimal(str(params.get("spread_between_levels", 0.01))),
                time_delay=params.get("time_delay", 60),  # seconds
                mode="BUY"  # or SELL
            )

            # Add executor to framework
            self.active_executors["dca_main"] = executor

            logging.info(f"✅ Configured V2 DCA executor for {self.name}")
            return True

        except Exception as e:
            logging.error(f"❌ Failed to configure V2 DCA: {e}")
            return False

    def _configure_twap_v2(self) -> bool:
        """Configure V2 TWAP (Time-Weighted Average Price) strategy."""
        try:
            primary_connector = list(self.connectors.values())[0]
            primary_trading_pair = self.config.trading_pairs[0]

            params = self.config.strategy_params or {}

            executor = TWAPExecutor(
                strategy=self.strategy_framework,
                connector=primary_connector,
                trading_pair=primary_trading_pair,
                order_amount=Decimal(str(self.config.order_amount)),
                total_amount=Decimal(str(params.get("total_amount", self.config.order_amount * 10))),
                time_delay=params.get("time_delay", 60),
                side="BUY"  # or SELL
            )

            self.active_executors["twap_main"] = executor

            logging.info(f"✅ Configured V2 TWAP executor for {self.name}")
            return True

        except Exception as e:
            logging.error(f"❌ Failed to configure V2 TWAP: {e}")
            return False

    def _configure_generic_v2(self) -> bool:
        """Configure generic V2 controller for unsupported strategy types."""
        try:
            controller = GenericController()

            # Basic configuration
            controller_config = {
                "connectors": self.connectors,
                "trading_pairs": self.config.trading_pairs,
                "refresh_time": self.config.order_refresh_time,
            }

            controller.init_params(**controller_config)
            self.strategy_framework.add_controller(controller)

            logging.info(f"✅ Configured V2 Generic controller for {self.name}")
            return True

        except Exception as e:
            logging.error(f"❌ Failed to configure V2 generic controller: {e}")
            return False

    async def start(self) -> bool:
        """Start the V2 strategy."""
        if not self.strategy_framework:
            logging.error(f"❌ Strategy framework not initialized for {self.name}")
            return False

        try:
            # Start the strategy framework
            await self.strategy_framework.start()
            self.is_running = True
            self.start_time = asyncio.get_event_loop().time()

            logging.info(f"🚀 Started V2 strategy: {self.name}")
            return True

        except Exception as e:
            logging.error(f"❌ Failed to start V2 strategy {self.name}: {e}")
            return False

    async def stop(self) -> bool:
        """Stop the V2 strategy."""
        if not self.strategy_framework:
            return True

        try:
            await self.strategy_framework.stop()
            self.is_running = False

            logging.info(f"🛑 Stopped V2 strategy: {self.name}")
            return True

        except Exception as e:
            logging.error(f"❌ Failed to stop V2 strategy {self.name}: {e}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """Get strategy status information."""
        if not self.strategy_framework:
            return {"status": "not_initialized", "is_running": False}

        try:
            return {
                "status": "running" if self.is_running else "stopped",
                "is_running": self.is_running,
                "strategy_type": getattr(self.config, 'strategy_type', 'pure_market_making'),
                "connector_type": self.config.connector_type,
                "trading_pairs": self.config.trading_pairs,
                "active_executors": len(self.active_executors),
                "total_executors_created": self.total_executors_created,
                "completed_executors": len(self.completed_executors),
                "framework_status": getattr(self.strategy_framework, "status", "unknown"),
            }

        except Exception as e:
            logging.error(f"❌ Failed to get V2 strategy status: {e}")
            return {"status": "error", "error": str(e)}


class HiveV2StrategyManager:
    """Manager for Strategy V2 instances in Hive architecture."""

    def __init__(self):
        self.v2_strategies: Dict[str, HiveV2StrategyWrapper] = {}
        self.is_v2_available = V2_AVAILABLE

        if self.is_v2_available:
            logging.info("🆕 Hive V2 Strategy Manager initialized")
        else:
            logging.warning("⚠️ V2 Strategy Manager initialized without V2 framework")

    def is_v2_strategy_supported(self, strategy_type: StrategyType) -> bool:
        """Check if a strategy type is supported in V2."""
        if not self.is_v2_available:
            return False

        v2_supported_types = {
            StrategyType.PURE_MARKET_MAKING,
            StrategyType.DIRECTIONAL_TRADING,
            StrategyType.DCA,
            StrategyType.TWAP,
            # Add more as V2 framework expands
        }

        return strategy_type in v2_supported_types

    def create_v2_strategy(
        self,
        config: UniversalStrategyConfig,
        connectors: Dict[str, ConnectorBase]
    ) -> Optional[HiveV2StrategyWrapper]:
        """Create a V2 strategy wrapper."""
        if not self.is_v2_available:
            logging.error("❌ V2 framework not available")
            return None

        try:
            # DynamicStrategyConfig doesn't have strategy_type field, default to PMM
            strategy_type = getattr(config, 'strategy_type', None)
            if strategy_type:
                strategy_type = StrategyType(strategy_type)
            else:
                strategy_type = StrategyType.PURE_MARKET_MAKING

            if not self.is_v2_strategy_supported(strategy_type):
                logging.error(f"❌ V2 strategy type not supported: {strategy_type}")
                return None

            # Create wrapper
            wrapper = HiveV2StrategyWrapper(config.name, config, connectors)

            # Initialize
            if wrapper.initialize_strategy():
                self.v2_strategies[config.name] = wrapper
                logging.info(f"✅ Created V2 strategy: {config.name}")
                return wrapper
            else:
                logging.error(f"❌ Failed to initialize V2 strategy: {config.name}")
                return None

        except Exception as e:
            logging.error(f"❌ Failed to create V2 strategy {config.name}: {e}")
            return None

    def get_v2_strategy(self, name: str) -> Optional[HiveV2StrategyWrapper]:
        """Get a V2 strategy by name."""
        return self.v2_strategies.get(name)

    def remove_v2_strategy(self, name: str) -> bool:
        """Remove a V2 strategy."""
        if name in self.v2_strategies:
            del self.v2_strategies[name]
            logging.info(f"🗑️ Removed V2 strategy: {name}")
            return True
        return False

    def get_all_v2_strategies(self) -> Dict[str, HiveV2StrategyWrapper]:
        """Get all V2 strategies."""
        return self.v2_strategies.copy()

    async def start_all_v2_strategies(self) -> int:
        """Start all V2 strategies. Returns number of successfully started."""
        started_count = 0

        for name, wrapper in self.v2_strategies.items():
            try:
                if await wrapper.start():
                    started_count += 1
                    logging.info(f"✅ Started V2 strategy: {name}")
                else:
                    logging.error(f"❌ Failed to start V2 strategy: {name}")
            except Exception as e:
                logging.error(f"❌ Error starting V2 strategy {name}: {e}")

        return started_count

    async def stop_all_v2_strategies(self) -> int:
        """Stop all V2 strategies. Returns number of successfully stopped."""
        stopped_count = 0

        for name, wrapper in self.v2_strategies.items():
            try:
                if await wrapper.stop():
                    stopped_count += 1
                    logging.info(f"🛑 Stopped V2 strategy: {name}")
                else:
                    logging.error(f"❌ Failed to stop V2 strategy: {name}")
            except Exception as e:
                logging.error(f"❌ Error stopping V2 strategy {name}: {e}")

        return stopped_count


# Global V2 manager instance
v2_manager = HiveV2StrategyManager()


# Convenience functions
def is_v2_available() -> bool:
    """Check if V2 framework is available."""
    return V2_AVAILABLE


def get_supported_v2_strategies() -> List[StrategyType]:
    """Get list of supported V2 strategy types."""
    if not V2_AVAILABLE:
        return []

    return [
        StrategyType.PURE_MARKET_MAKING,
        StrategyType.DIRECTIONAL_TRADING,
        StrategyType.DCA,
        StrategyType.TWAP,
    ]


# Export main classes and functions
__all__ = [
    "HiveV2StrategyWrapper",
    "HiveV2StrategyManager",
    "v2_manager",
    "is_v2_available",
    "get_supported_v2_strategies",
    "V2_AVAILABLE"
]
