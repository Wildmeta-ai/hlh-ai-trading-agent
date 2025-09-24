#!/usr/bin/env python3

"""
Hive Simple Strategy Factory - Support for available Hummingbot strategies on Hyperliquid
Focused on strategies that actually work with the current Hummingbot installation.
"""

import logging
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Type

from hummingbot.connector.connector_base import ConnectorBase
from hummingbot.strategy.avellaneda_market_making import AvellanedaMarketMakingStrategy
from hummingbot.strategy.cross_exchange_market_making import CrossExchangeMarketMakingStrategy

# Import only available strategies
from hummingbot.strategy.pure_market_making import PureMarketMakingStrategy

# Core Hummingbot imports
from hummingbot.strategy.strategy_py_base import StrategyPyBase


class StrategyType(Enum):
    """Available strategy types for Hivebot on Hyperliquid."""
    PURE_MARKET_MAKING = "pure_market_making"
    AVELLANEDA_MARKET_MAKING = "avellaneda_market_making"
    CROSS_EXCHANGE_MARKET_MAKING = "cross_exchange_market_making"


class SimpleStrategyFactory:
    """Simple factory for creating Hummingbot strategies on Hyperliquid."""

    STRATEGY_CLASSES: Dict[StrategyType, Type[StrategyPyBase]] = {
        StrategyType.PURE_MARKET_MAKING: PureMarketMakingStrategy,
        StrategyType.AVELLANEDA_MARKET_MAKING: AvellanedaMarketMakingStrategy,
        StrategyType.CROSS_EXCHANGE_MARKET_MAKING: CrossExchangeMarketMakingStrategy,
    }

    def __init__(self):
        logging.info(f"🏭 Simple Strategy Factory initialized with {len(self.STRATEGY_CLASSES)} strategy types")

    def get_supported_strategies(self) -> List[StrategyType]:
        """Get list of supported strategy types."""
        return list(self.STRATEGY_CLASSES.keys())

    def is_strategy_supported(self, strategy_type: StrategyType) -> bool:
        """Check if a strategy type is supported."""
        if isinstance(strategy_type, str):
            try:
                strategy_type = StrategyType(strategy_type)
            except ValueError:
                return False
        return strategy_type in self.STRATEGY_CLASSES

    def get_strategy_class(self, strategy_type: StrategyType) -> Optional[Type[StrategyPyBase]]:
        """Get strategy class by type."""
        if isinstance(strategy_type, str):
            try:
                strategy_type = StrategyType(strategy_type)
            except ValueError:
                return None
        return self.STRATEGY_CLASSES.get(strategy_type)


def get_all_strategy_types() -> List[StrategyType]:
    """Get all available strategy types."""
    return list(StrategyType)


# Global factory instance
strategy_factory = SimpleStrategyFactory()


# Export main classes and functions
__all__ = [
    "StrategyType",
    "SimpleStrategyFactory",
    "strategy_factory",
    "get_all_strategy_types"
]
