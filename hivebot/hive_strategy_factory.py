#!/usr/bin/env python3

"""
Hive Universal Strategy Factory - Support for all Hummingbot strategies
Provides unified interface for creating and managing any Hummingbot strategy type.
"""

import logging
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Type, Union

from hummingbot.connector.connector_base import ConnectorBase
from hummingbot.core.data_type.common import OrderType, PositionAction, TradeType

# AMM Arb strategy import - commented out due to import issues
# from hummingbot.strategy.amm_arb import AmmArbStrategy
from hummingbot.strategy.avellaneda_market_making import AvellanedaMarketMakingStrategy
from hummingbot.strategy.cross_exchange_market_making import CrossExchangeMarketMakingStrategy
from hummingbot.strategy.cross_exchange_mining import CrossExchangeMiningStrategy

# from hummingbot.strategy.liquidity_mining import LiquidityMiningStrategy  # Commented out due to import issues
from hummingbot.strategy.perpetual_market_making import PerpetualMarketMakingStrategy

# Import all supported strategies
from hummingbot.strategy.pure_market_making import PureMarketMakingStrategy

# Core Hummingbot imports
from hummingbot.strategy.strategy_py_base import StrategyPyBase

# from hummingbot.strategy.spot_perpetual_arbitrage import SpotPerpetualArbitrageStrategy  # Commented out due to import issues


# V2 Strategy framework
try:
    from hummingbot.strategy_v2.controllers.controller_base import ControllerBase
    from hummingbot.strategy_v2.controllers.directional_trading_controller_base import DirectionalTradingControllerBase
    from hummingbot.strategy_v2.controllers.market_making_controller_base import MarketMakingControllerBase
    V2_AVAILABLE = True
except ImportError:
    V2_AVAILABLE = False
    logging.warning("Strategy V2 framework not available")

# Market trading pair tuple
from hummingbot.strategy.market_trading_pair_tuple import MarketTradingPairTuple


class StrategyType(Enum):
    """Enumeration of all supported strategy types."""
    PURE_MARKET_MAKING = "pure_market_making"
    AVELLANEDA_MARKET_MAKING = "avellaneda_market_making"
    PERPETUAL_MARKET_MAKING = "perpetual_market_making"
    CROSS_EXCHANGE_MARKET_MAKING = "cross_exchange_market_making"
    CROSS_EXCHANGE_MINING = "cross_exchange_mining"
    LIQUIDITY_MINING = "liquidity_mining"
    SPOT_PERPETUAL_ARBITRAGE = "spot_perpetual_arbitrage"
    AMM_ARBITRAGE = "amm_arb"
    HEDGE = "hedge"

    # V2 Strategies
    V2_MARKET_MAKING = "v2_market_making"
    V2_DIRECTIONAL_TRADING = "v2_directional_trading"
    V2_GENERIC_CONTROLLER = "v2_generic_controller"


class UniversalStrategyConfig:
    """Universal configuration class supporting all strategy parameters."""

    def __init__(self, **kwargs):
        # Basic parameters (all strategies)
        self.strategy_type = kwargs.get('strategy_type', 'pure_market_making')
        self.exchange = kwargs.get('exchange', 'hyperliquid_perpetual_testnet')
        self.market = kwargs.get('market', 'PURR-USDC')
        self.enabled = kwargs.get('enabled', True)

        # Market making parameters
        self.bid_spread = kwargs.get('bid_spread', 0.01)
        self.ask_spread = kwargs.get('ask_spread', 0.01)
        self.order_amount = kwargs.get('order_amount', 0.001)
        self.order_refresh_time = kwargs.get('order_refresh_time', 5.0)
        self.minimum_spread = kwargs.get('minimum_spread', 0.001)
        self.order_levels = kwargs.get('order_levels', 1)
        self.order_level_amount = kwargs.get('order_level_amount', 0.0)
        self.order_level_spread = kwargs.get('order_level_spread', 0.01)

        # Advanced market making
        self.filled_order_delay = kwargs.get('filled_order_delay', 60.0)
        self.hanging_orders_enabled = kwargs.get('hanging_orders_enabled', False)
        self.hanging_orders_cancel_pct = kwargs.get('hanging_orders_cancel_pct', 0.1)
        self.order_optimization_enabled = kwargs.get('order_optimization_enabled', False)
        self.add_transaction_costs = kwargs.get('add_transaction_costs', True)

        # Price and inventory management
        self.price_ceiling = kwargs.get('price_ceiling', -1)
        self.price_floor = kwargs.get('price_floor', -1)
        self.moving_price_band_enabled = kwargs.get('moving_price_band_enabled', False)
        self.price_band_refresh_time = kwargs.get('price_band_refresh_time', 86400)
        self.inventory_skew_enabled = kwargs.get('inventory_skew_enabled', False)
        self.inventory_target_base_pct = kwargs.get('inventory_target_base_pct', 50.0)
        self.inventory_range_multiplier = kwargs.get('inventory_range_multiplier', 1.0)

        # Cross-exchange parameters
        self.maker_market = kwargs.get('maker_market', self.market)
        self.taker_market = kwargs.get('taker_market', self.market)
        self.min_profitability = kwargs.get('min_profitability', 0.01)
        self.order_size_taker_volume_pct = kwargs.get('order_size_taker_volume_pct', 25.0)
        self.order_size_portfolio_ratio_limit = kwargs.get('order_size_portfolio_ratio_limit', 0.1667)

        # Arbitrage parameters
        self.min_trade_size = kwargs.get('min_trade_size', 0.001)
        self.max_trade_size = kwargs.get('max_trade_size', 1.0)
        self.market_1 = kwargs.get('market_1', self.market)
        self.market_2 = kwargs.get('market_2', self.market)

        # Risk management
        self.stop_loss_pct = kwargs.get('stop_loss_pct', 0.0)
        self.take_profit_pct = kwargs.get('take_profit_pct', 0.0)
        self.max_order_age = kwargs.get('max_order_age', 600.0)
        self.cancel_order_threshold = kwargs.get('cancel_order_threshold', 0.05)

        # V2 Strategy parameters
        self.controller_name = kwargs.get('controller_name', '')
        self.executor_refresh_time = kwargs.get('executor_refresh_time', 1.0)

        # Store all original kwargs for strategy-specific parameters
        self.raw_config = kwargs

    def get_strategy_specific_params(self, strategy_type: StrategyType) -> Dict[str, Any]:
        """Get parameters specific to a strategy type."""
        if strategy_type == StrategyType.PURE_MARKET_MAKING:
            return self._get_pure_market_making_params()
        elif strategy_type == StrategyType.AVELLANEDA_MARKET_MAKING:
            return self._get_avellaneda_params()
        elif strategy_type == StrategyType.PERPETUAL_MARKET_MAKING:
            return self._get_perpetual_market_making_params()
        elif strategy_type == StrategyType.CROSS_EXCHANGE_MARKET_MAKING:
            return self._get_cross_exchange_params()
        elif strategy_type == StrategyType.SPOT_PERPETUAL_ARBITRAGE:
            return self._get_spot_perpetual_arb_params()
        # Add more strategy types as needed
        else:
            return {}

    def _get_pure_market_making_params(self) -> Dict[str, Any]:
        """Pure Market Making specific parameters."""
        return {
            'bid_spread': Decimal(str(self.bid_spread)),
            'ask_spread': Decimal(str(self.ask_spread)),
            'order_amount': Decimal(str(self.order_amount)),
            'order_refresh_time': float(self.order_refresh_time),
            'minimum_spread': Decimal(str(self.minimum_spread)),
            'order_levels': int(self.order_levels),
            'order_level_amount': Decimal(str(self.order_level_amount)),
            'order_level_spread': Decimal(str(self.order_level_spread)),
            'filled_order_delay': float(self.filled_order_delay),
            'hanging_orders_enabled': bool(self.hanging_orders_enabled),
            'hanging_orders_cancel_pct': Decimal(str(self.hanging_orders_cancel_pct)),
            'order_optimization_enabled': bool(self.order_optimization_enabled),
            'add_transaction_costs_to_orders': bool(self.add_transaction_costs),
            'price_ceiling': Decimal(str(self.price_ceiling)) if self.price_ceiling > 0 else Decimal('-1'),
            'price_floor': Decimal(str(self.price_floor)) if self.price_floor > 0 else Decimal('-1'),
            'moving_price_band_enabled': bool(self.moving_price_band_enabled),
            'price_band_refresh_time': float(self.price_band_refresh_time),
            'inventory_skew_enabled': bool(self.inventory_skew_enabled),
            'inventory_target_base_pct': Decimal(str(self.inventory_target_base_pct)),
            'inventory_range_multiplier': Decimal(str(self.inventory_range_multiplier)),
        }

    def _get_avellaneda_params(self) -> Dict[str, Any]:
        """Avellaneda Market Making specific parameters."""
        return {
            'order_amount': Decimal(str(self.order_amount)),
            'order_refresh_time': float(self.order_refresh_time),
            'inventory_target_base_pct': Decimal(str(self.inventory_target_base_pct)),
            'add_transaction_costs_to_orders': bool(self.add_transaction_costs),
            # Avellaneda-specific
            'execution_timeframe': self.raw_config.get('execution_timeframe', '1d'),
            'creation_timestamp_format': self.raw_config.get('creation_timestamp_format', '%Y-%m-%d %H:%M:%S'),
            'risk_factor': Decimal(str(self.raw_config.get('risk_factor', 0.5))),
            'order_book_depth_factor': Decimal(str(self.raw_config.get('order_book_depth_factor', 0.0))),
        }

    def _get_perpetual_market_making_params(self) -> Dict[str, Any]:
        """Perpetual Market Making specific parameters."""
        params = self._get_pure_market_making_params()
        params.update({
            'position_management_enabled': bool(self.raw_config.get('position_management_enabled', True)),
            'long_profit_taking_factor': Decimal(str(self.raw_config.get('long_profit_taking_factor', 1.0))),
            'short_profit_taking_factor': Decimal(str(self.raw_config.get('short_profit_taking_factor', 1.0))),
        })
        return params

    def _get_cross_exchange_params(self) -> Dict[str, Any]:
        """Cross Exchange Market Making specific parameters."""
        return {
            'order_amount': Decimal(str(self.order_amount)),
            'min_profitability': Decimal(str(self.min_profitability)),
            'order_size_taker_volume_pct': Decimal(str(self.order_size_taker_volume_pct)),
            'order_size_portfolio_ratio_limit': Decimal(str(self.order_size_portfolio_ratio_limit)),
            'limit_order_min_expiration': float(self.raw_config.get('limit_order_min_expiration', 130.0)),
            'cancel_order_threshold': Decimal(str(self.cancel_order_threshold)),
            'active_order_canceling': bool(self.raw_config.get('active_order_canceling', True)),
        }

    def _get_spot_perpetual_arb_params(self) -> Dict[str, Any]:
        """Spot Perpetual Arbitrage specific parameters."""
        return {
            'order_amount': Decimal(str(self.order_amount)),
            'derivative_market': str(self.raw_config.get('derivative_market', self.market)),
            'min_opening_arbitrage_pct': Decimal(str(self.raw_config.get('min_opening_arbitrage_pct', 0.01))),
            'min_closing_arbitrage_pct': Decimal(str(self.raw_config.get('min_closing_arbitrage_pct', 0.01))),
            'spot_market_slippage_buffer': Decimal(str(self.raw_config.get('spot_market_slippage_buffer', 0.05))),
            'derivative_market_slippage_buffer': Decimal(str(self.raw_config.get('derivative_market_slippage_buffer', 0.05))),
        }


class UniversalStrategyFactory:
    """Factory for creating any supported Hummingbot strategy."""

    # Registry of all supported strategies
    STRATEGY_CLASSES = {
        StrategyType.PURE_MARKET_MAKING: PureMarketMakingStrategy,
        StrategyType.AVELLANEDA_MARKET_MAKING: AvellanedaMarketMakingStrategy,
        StrategyType.PERPETUAL_MARKET_MAKING: PerpetualMarketMakingStrategy,
        StrategyType.CROSS_EXCHANGE_MARKET_MAKING: CrossExchangeMarketMakingStrategy,
        StrategyType.CROSS_EXCHANGE_MINING: CrossExchangeMiningStrategy,
        # StrategyType.LIQUIDITY_MINING: LiquidityMiningStrategy,  # Commented out due to import issues
        # StrategyType.SPOT_PERPETUAL_ARBITRAGE: SpotPerpetualArbitrageStrategy,  # Commented out due to import issues
        # StrategyType.AMM_ARBITRAGE: AmmArbStrategy,  # Commented out due to import issues
    }

    @classmethod
    def create_strategy(
        cls,
        strategy_type: Union[str, StrategyType],
        config: UniversalStrategyConfig,
        connectors: Dict[str, ConnectorBase]
    ) -> Optional[StrategyPyBase]:
        """
        Create a strategy instance of the specified type.

        Args:
            strategy_type: The type of strategy to create
            config: Universal configuration object
            connectors: Dictionary of initialized connectors

        Returns:
            Configured strategy instance or None if creation failed
        """
        try:
            # Convert string to enum if needed
            if isinstance(strategy_type, str):
                try:
                    strategy_type = StrategyType(strategy_type)
                except ValueError:
                    logging.error(f"Unsupported strategy type: {strategy_type}")
                    return None

            # Check if strategy class is available
            if strategy_type not in cls.STRATEGY_CLASSES:
                logging.error(f"Strategy class not registered: {strategy_type}")
                return None

            strategy_class = cls.STRATEGY_CLASSES[strategy_type]

            # Create market trading pairs based on strategy requirements
            market_infos = cls._create_market_infos(strategy_type, config, connectors)
            if not market_infos:
                logging.error(f"Failed to create market info for {strategy_type}")
                return None

            # Get strategy-specific parameters
            strategy_params = config.get_strategy_specific_params(strategy_type)

            # Create the strategy instance
            logging.info(f"Creating {strategy_type.value} strategy with {len(market_infos)} markets")
            strategy = strategy_class()

            # Initialize the strategy with appropriate parameters
            cls._initialize_strategy(strategy, strategy_type, market_infos, strategy_params)

            logging.info(f"✅ Successfully created {strategy_type.value} strategy")
            return strategy

        except Exception as e:
            logging.error(f"Failed to create strategy {strategy_type}: {e}")
            return None

    @classmethod
    def _create_market_infos(
        cls,
        strategy_type: StrategyType,
        config: UniversalStrategyConfig,
        connectors: Dict[str, ConnectorBase]
    ) -> Optional[Dict[str, MarketTradingPairTuple]]:
        """Create market trading pair tuples for the strategy."""
        try:
            market_infos = {}

            if strategy_type in [StrategyType.PURE_MARKET_MAKING,
                                 StrategyType.AVELLANEDA_MARKET_MAKING,
                                 StrategyType.PERPETUAL_MARKET_MAKING]:
                # Single market strategies
                connector = connectors.get(config.exchange)
                if not connector:
                    logging.error(f"Connector not found: {config.exchange}")
                    return None

                trading_pair = config.market
                assets = trading_pair.split('-')
                if len(assets) != 2:
                    logging.error(f"Invalid trading pair format: {trading_pair}")
                    return None

                market_info = MarketTradingPairTuple(
                    market=connector,
                    trading_pair=trading_pair,
                    base_asset=assets[0],
                    quote_asset=assets[1]
                )
                market_infos[config.exchange] = market_info

            elif strategy_type == StrategyType.CROSS_EXCHANGE_MARKET_MAKING:
                # Two market strategy
                maker_connector = connectors.get(config.exchange)
                taker_connector = connectors.get(config.raw_config.get('taker_exchange', config.exchange))

                if not maker_connector or not taker_connector:
                    logging.error("Missing connectors for cross-exchange strategy")
                    return None

                # Create market infos for both exchanges
                for exchange, connector in [('maker', maker_connector), ('taker', taker_connector)]:
                    trading_pair = config.market
                    assets = trading_pair.split('-')
                    market_info = MarketTradingPairTuple(
                        market=connector,
                        trading_pair=trading_pair,
                        base_asset=assets[0],
                        quote_asset=assets[1]
                    )
                    market_infos[exchange] = market_info

            # Add more market creation logic for other strategy types as needed

            return market_infos if market_infos else None

        except Exception as e:
            logging.error(f"Error creating market infos: {e}")
            return None

    @classmethod
    def _initialize_strategy(
        cls,
        strategy: StrategyPyBase,
        strategy_type: StrategyType,
        market_infos: Dict[str, MarketTradingPairTuple],
        params: Dict[str, Any]
    ):
        """Initialize the strategy with appropriate parameters."""
        try:
            if strategy_type in [StrategyType.PURE_MARKET_MAKING,
                                 StrategyType.AVELLANEDA_MARKET_MAKING,
                                 StrategyType.PERPETUAL_MARKET_MAKING]:
                # Single market strategies
                market_info = list(market_infos.values())[0]
                strategy.init_params(
                    market_info=market_info,
                    **params
                )
            elif strategy_type == StrategyType.CROSS_EXCHANGE_MARKET_MAKING:
                # Cross-exchange strategy
                maker_market_info = market_infos.get('maker')
                taker_market_info = market_infos.get('taker')
                if maker_market_info and taker_market_info:
                    strategy.init_params(
                        maker_market_trading_pair_tuple=maker_market_info,
                        taker_market_trading_pair_tuple=taker_market_info,
                        **params
                    )

            # Add more initialization logic for other strategy types

        except Exception as e:
            logging.error(f"Error initializing strategy: {e}")
            raise

    @classmethod
    def get_supported_strategies(cls) -> List[str]:
        """Get list of all supported strategy types."""
        return [strategy_type.value for strategy_type in cls.STRATEGY_CLASSES.keys()]

    @classmethod
    def is_strategy_supported(cls, strategy_type: str) -> bool:
        """Check if a strategy type is supported."""
        try:
            StrategyType(strategy_type)
            return True
        except ValueError:
            return False


# Convenience functions
def create_strategy(strategy_type: str, config_dict: Dict[str, Any], connectors: Dict[str, ConnectorBase]) -> Optional[StrategyPyBase]:
    """Convenience function to create a strategy from config dictionary."""
    config = UniversalStrategyConfig(**config_dict)
    return UniversalStrategyFactory.create_strategy(strategy_type, config, connectors)


def get_strategy_parameters(strategy_type: str) -> Dict[str, str]:
    """Get the expected parameters for a strategy type with descriptions."""
    # This would return a dictionary of parameter names and descriptions
    # Implementation depends on strategy requirements
    if strategy_type == "pure_market_making":
        return {
            "bid_spread": "Bid spread percentage (e.g., 0.01 for 1%)",
            "ask_spread": "Ask spread percentage (e.g., 0.01 for 1%)",
            "order_amount": "Order amount in base asset",
            "order_refresh_time": "Time in seconds to refresh orders",
            "minimum_spread": "Minimum spread to maintain",
            "order_levels": "Number of order levels",
        }
    # Add more strategy types as implemented
    return {}
