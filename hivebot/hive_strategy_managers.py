#!/usr/bin/env python3

"""
Hive Strategy Managers - Specialized managers for different strategy categories.
Handles the complexity of initializing and managing different strategy types with their unique parameters.
"""

import logging
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any, Dict, List, Optional

# Import our universal configs
from hive_database import UniversalStrategyConfig
from hive_strategy_factory import StrategyType
from hummingbot.connector.connector_base import ConnectorBase
from hummingbot.strategy.amm_arb import AmmArbStrategy
from hummingbot.strategy.arbitrage import ArbitrageStrategy
from hummingbot.strategy.avellaneda_market_making import AvellanedaMarketMakingStrategy
from hummingbot.strategy.cross_exchange_market_making import CrossExchangeMarketMakingStrategy
from hummingbot.strategy.dev_simple_trade import SimpleTradeStrategy
from hummingbot.strategy.fixed_grid import FixedGridStrategy
from hummingbot.strategy.hedge import HedgeStrategy
from hummingbot.strategy.liquidity_mining import LiquidityMiningStrategy

# Hummingbot core imports
from hummingbot.strategy.market_trading_pair_tuple import MarketTradingPairTuple
from hummingbot.strategy.perpetual_market_making import PerpetualMarketMakingStrategy
from hummingbot.strategy.pure_market_making import PureMarketMakingStrategy
from hummingbot.strategy.spot_perpetual_arbitrage import SpotPerpetualArbitrageStrategy

# Hummingbot strategy imports
from hummingbot.strategy.strategy_base import StrategyBase
from hummingbot.strategy.twap import TwapTradeStrategy
from hummingbot.strategy.uniswap_v3_lp import UniswapV3LpStrategy


class StrategyManagerBase(ABC):
    """Base class for strategy-specific managers."""

    def __init__(self, strategy_type: StrategyType):
        self.strategy_type = strategy_type

    @abstractmethod
    def create_strategy(
        self,
        config: UniversalStrategyConfig,
        connectors: Dict[str, ConnectorBase]
    ) -> Optional[StrategyBase]:
        """Create and initialize a strategy instance."""
        pass

    @abstractmethod
    def validate_config(self, config: UniversalStrategyConfig) -> bool:
        """Validate strategy-specific configuration."""
        pass

    def _create_market_info(
        self,
        connector: ConnectorBase,
        trading_pair: str
    ) -> MarketTradingPairTuple:
        """Create a market trading pair tuple."""
        assets = trading_pair.split("-")
        return MarketTradingPairTuple(
            connector,
            trading_pair,
            assets[0],  # base asset
            assets[1]   # quote asset
        )


class PureMarketMakingManager(StrategyManagerBase):
    """Manager for Pure Market Making strategies."""

    def __init__(self):
        super().__init__(StrategyType.PURE_MARKET_MAKING)

    def create_strategy(
        self,
        config: UniversalStrategyConfig,
        connectors: Dict[str, ConnectorBase]
    ) -> Optional[PureMarketMakingStrategy]:
        """Create Pure Market Making strategy."""
        try:
            # Get the primary connector
            primary_connector = list(connectors.values())[0]
            primary_trading_pair = config.trading_pairs[0]

            # Create market info
            market_info = self._create_market_info(primary_connector, primary_trading_pair)

            # Create strategy instance
            strategy = PureMarketMakingStrategy()

            # Initialize with parameters
            strategy.init_params(
                market_info=market_info,
                bid_spread=Decimal(str(config.bid_spread)),
                ask_spread=Decimal(str(config.ask_spread)),
                order_amount=Decimal(str(config.order_amount)),
                order_levels=config.order_levels,
                order_refresh_time=config.order_refresh_time,
                order_level_spread=Decimal(str(config.order_level_spread)),
                order_level_amount=Decimal(str(config.order_level_amount)),
                inventory_skew_enabled=config.inventory_target_base_pct != 50.0,
                inventory_target_base_pct=Decimal(str(config.inventory_target_base_pct)),
                inventory_range_multiplier=Decimal(str(config.inventory_range_multiplier)),
                hanging_orders_enabled=config.hanging_orders_enabled,
                hanging_orders_cancel_pct=Decimal(str(config.hanging_orders_cancel_pct)),
                order_optimization_enabled=config.order_optimization_enabled,
                ask_order_optimization_depth=Decimal(str(config.ask_order_optimization_depth)),
                bid_order_optimization_depth=Decimal(str(config.bid_order_optimization_depth)),
                price_ceiling=Decimal(str(config.price_ceiling)) if config.price_ceiling > 0 else Decimal("-1"),
                price_floor=Decimal(str(config.price_floor)) if config.price_floor > 0 else Decimal("-1"),
                ping_pong_enabled=config.ping_pong_enabled,
                logging_options=PureMarketMakingStrategy.OPTION_LOG_ALL
            )

            logging.info(f"✅ Created Pure Market Making strategy: {config.name}")
            return strategy

        except Exception as e:
            logging.error(f"❌ Failed to create PMM strategy {config.name}: {e}")
            return None

    def validate_config(self, config: UniversalStrategyConfig) -> bool:
        """Validate PMM configuration."""
        if config.bid_spread <= 0 or config.ask_spread <= 0:
            logging.error("Spreads must be positive")
            return False
        if config.order_amount <= 0:
            logging.error("Order amount must be positive")
            return False
        return True


class AvellanedaMarketMakingManager(StrategyManagerBase):
    """Manager for Avellaneda Market Making strategies."""

    def __init__(self):
        super().__init__(StrategyType.AVELLANEDA_MARKET_MAKING)

    def create_strategy(
        self,
        config: UniversalStrategyConfig,
        connectors: Dict[str, ConnectorBase]
    ) -> Optional[AvellanedaMarketMakingStrategy]:
        """Create Avellaneda Market Making strategy."""
        try:
            primary_connector = list(connectors.values())[0]
            primary_trading_pair = config.trading_pairs[0]
            market_info = self._create_market_info(primary_connector, primary_trading_pair)

            strategy = AvellanedaMarketMakingStrategy()

            # Get Avellaneda-specific parameters
            risk_factor = config.strategy_params.get("risk_factor", 1.0)
            order_book_depth_factor = config.strategy_params.get("order_book_depth_factor", 0.0)
            order_amount_shape_factor = config.strategy_params.get("order_amount_shape_factor", 0.0)

            strategy.init_params(
                market_info=market_info,
                order_amount=Decimal(str(config.order_amount)),
                order_levels=config.order_levels,
                order_refresh_time=config.order_refresh_time,
                order_level_amount=Decimal(str(config.order_level_amount)),
                inventory_target_base_pct=Decimal(str(config.inventory_target_base_pct)),
                hanging_orders_enabled=config.hanging_orders_enabled,
                order_optimization_enabled=config.order_optimization_enabled,
                risk_factor=Decimal(str(risk_factor)),
                order_book_depth_factor=Decimal(str(order_book_depth_factor)),
                order_amount_shape_factor=Decimal(str(order_amount_shape_factor)),
                logging_options=AvellanedaMarketMakingStrategy.OPTION_LOG_ALL
            )

            logging.info(f"✅ Created Avellaneda Market Making strategy: {config.name}")
            return strategy

        except Exception as e:
            logging.error(f"❌ Failed to create Avellaneda strategy {config.name}: {e}")
            return None

    def validate_config(self, config: UniversalStrategyConfig) -> bool:
        """Validate Avellaneda configuration."""
        if config.order_amount <= 0:
            logging.error("Order amount must be positive")
            return False
        return True


class CrossExchangeMarketMakingManager(StrategyManagerBase):
    """Manager for Cross Exchange Market Making strategies."""

    def __init__(self):
        super().__init__(StrategyType.CROSS_EXCHANGE_MARKET_MAKING)

    def create_strategy(
        self,
        config: UniversalStrategyConfig,
        connectors: Dict[str, ConnectorBase]
    ) -> Optional[CrossExchangeMarketMakingStrategy]:
        """Create Cross Exchange Market Making strategy."""
        try:
            if len(connectors) < 2:
                logging.error("Cross exchange strategy requires at least 2 connectors")
                return None

            # Get maker and taker connectors
            connector_list = list(connectors.values())
            maker_connector = connector_list[0]
            taker_connector = connector_list[1]

            primary_trading_pair = config.trading_pairs[0]
            maker_market_info = self._create_market_info(maker_connector, primary_trading_pair)
            taker_market_info = self._create_market_info(taker_connector, primary_trading_pair)

            strategy = CrossExchangeMarketMakingStrategy()

            strategy.init_params(
                maker_market_info=maker_market_info,
                taker_market_info=taker_market_info,
                order_amount=Decimal(str(config.order_amount)),
                min_profitability=Decimal(str(config.min_profitability)),
                order_refresh_time=config.order_refresh_time,
                order_levels=config.order_levels,
                logging_options=CrossExchangeMarketMakingStrategy.OPTION_LOG_ALL
            )

            logging.info(f"✅ Created Cross Exchange Market Making strategy: {config.name}")
            return strategy

        except Exception as e:
            logging.error(f"❌ Failed to create XEMM strategy {config.name}: {e}")
            return None

    def validate_config(self, config: UniversalStrategyConfig) -> bool:
        """Validate cross exchange configuration."""
        if config.min_profitability <= 0:
            logging.error("Minimum profitability must be positive")
            return False
        return True


class ArbitrageManager(StrategyManagerBase):
    """Manager for Arbitrage strategies."""

    def __init__(self):
        super().__init__(StrategyType.ARBITRAGE)

    def create_strategy(
        self,
        config: UniversalStrategyConfig,
        connectors: Dict[str, ConnectorBase]
    ) -> Optional[ArbitrageStrategy]:
        """Create Arbitrage strategy."""
        try:
            if len(connectors) < 2:
                logging.error("Arbitrage strategy requires at least 2 connectors")
                return None

            connector_list = list(connectors.values())
            primary_connector = connector_list[0]
            secondary_connector = connector_list[1]

            primary_trading_pair = config.trading_pairs[0]
            primary_market_info = self._create_market_info(primary_connector, primary_trading_pair)
            secondary_market_info = self._create_market_info(secondary_connector, primary_trading_pair)

            strategy = ArbitrageStrategy()

            strategy.init_params(
                primary_market_info=primary_market_info,
                secondary_market_info=secondary_market_info,
                min_profitability=Decimal(str(config.min_profitability)),
                max_order_size=Decimal(str(config.max_order_size)),
                logging_options=ArbitrageStrategy.OPTION_LOG_ALL
            )

            logging.info(f"✅ Created Arbitrage strategy: {config.name}")
            return strategy

        except Exception as e:
            logging.error(f"❌ Failed to create Arbitrage strategy {config.name}: {e}")
            return None

    def validate_config(self, config: UniversalStrategyConfig) -> bool:
        """Validate arbitrage configuration."""
        if config.min_profitability <= 0:
            logging.error("Minimum profitability must be positive")
            return False
        return True


class StrategyManagerRegistry:
    """Registry of all strategy managers."""

    def __init__(self):
        self.managers: Dict[StrategyType, StrategyManagerBase] = {
            StrategyType.PURE_MARKET_MAKING: PureMarketMakingManager(),
            StrategyType.AVELLANEDA_MARKET_MAKING: AvellanedaMarketMakingManager(),
            StrategyType.CROSS_EXCHANGE_MARKET_MAKING: CrossExchangeMarketMakingManager(),
            StrategyType.ARBITRAGE: ArbitrageManager(),
            # Add more managers as needed
        }

        logging.info(f"🏭 Strategy Manager Registry initialized with {len(self.managers)} managers")

    def get_manager(self, strategy_type: StrategyType) -> Optional[StrategyManagerBase]:
        """Get a strategy manager by type."""
        if isinstance(strategy_type, str):
            try:
                strategy_type = StrategyType(strategy_type)
            except ValueError:
                logging.error(f"Unknown strategy type: {strategy_type}")
                return None

        return self.managers.get(strategy_type)

    def is_supported(self, strategy_type: StrategyType) -> bool:
        """Check if a strategy type is supported."""
        if isinstance(strategy_type, str):
            try:
                strategy_type = StrategyType(strategy_type)
            except ValueError:
                return False

        return strategy_type in self.managers

    def get_supported_strategies(self) -> List[StrategyType]:
        """Get list of supported strategy types."""
        return list(self.managers.keys())

    def create_strategy(
        self,
        config: UniversalStrategyConfig,
        connectors: Dict[str, ConnectorBase]
    ) -> Optional[StrategyBase]:
        """Create a strategy using the appropriate manager."""
        try:
            # Convert string to enum if needed - DynamicStrategyConfig doesn't have strategy_type
            strategy_type = getattr(config, 'strategy_type', None)
            if strategy_type and isinstance(strategy_type, str):
                strategy_type = StrategyType(strategy_type)
            elif not strategy_type:
                strategy_type = StrategyType.PURE_MARKET_MAKING  # Default for DynamicStrategyConfig

            # Get the appropriate manager
            manager = self.get_manager(strategy_type)
            if not manager:
                logging.error(f"❌ No manager found for strategy type: {strategy_type}")
                return None

            # Validate configuration
            if not manager.validate_config(config):
                logging.error(f"❌ Invalid configuration for strategy: {config.name}")
                return None

            # Create the strategy
            return manager.create_strategy(config, connectors)

        except Exception as e:
            logging.error(f"❌ Failed to create strategy {config.name}: {e}")
            import traceback
            traceback.print_exc()
            return None


# Global strategy manager registry instance
strategy_registry = StrategyManagerRegistry()


# Convenience functions
def create_strategy_from_config(
    config: UniversalStrategyConfig,
    connectors: Dict[str, ConnectorBase]
) -> Optional[StrategyBase]:
    """Create a strategy from universal configuration."""
    return strategy_registry.create_strategy(config, connectors)


def get_supported_strategy_types() -> List[StrategyType]:
    """Get all supported strategy types."""
    return strategy_registry.get_supported_strategies()


def is_strategy_supported(strategy_type: StrategyType) -> bool:
    """Check if a strategy type is supported."""
    return strategy_registry.is_supported(strategy_type)


# Export main classes and functions
__all__ = [
    "StrategyManagerBase",
    "PureMarketMakingManager",
    "AvellanedaMarketMakingManager",
    "CrossExchangeMarketMakingManager",
    "ArbitrageManager",
    "StrategyManagerRegistry",
    "strategy_registry",
    "create_strategy_from_config",
    "get_supported_strategy_types",
    "is_strategy_supported"
]
