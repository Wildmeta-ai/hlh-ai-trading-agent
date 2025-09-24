#!/usr/bin/env python3

"""
Hive Connector Factory - Universal connector support for all Hummingbot exchange types.
Enables Hivebot to work with any exchange connector that Hummingbot supports.
"""

import logging
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Type, Union

# Hummingbot connector imports
from hummingbot.client.config.config_helpers import ClientConfigAdapter
from hummingbot.connector.connector_base import ConnectorBase

# Hyperliquid Connector - the only one we need
from hummingbot.connector.derivative.hyperliquid_perpetual.hyperliquid_perpetual_derivative import (
    HyperliquidPerpetualDerivative,
)


class ConnectorType(Enum):
    """Supported connector types - focused on Hyperliquid."""
    # Primary connector
    HYPERLIQUID_PERPETUAL = "hyperliquid_perpetual"

    # Future expansion placeholder
    # BINANCE_PERPETUAL = "binance_perpetual"  # Can be added later if needed


class ConnectorCategory(Enum):
    """Connector categories for different market types."""
    CEX_DERIVATIVE = "cex_derivative"


@dataclass
class ConnectorConfig:
    """Universal connector configuration supporting all exchange types."""

    # Basic connector info
    connector_type: ConnectorType
    trading_pairs: List[str]
    trading_required: bool = False

    # Authentication (CEX)
    api_key: str = ""
    api_secret: str = ""
    passphrase: str = ""  # For exchanges like KuCoin, OKX

    # Derivative specific
    leverage: int = 1
    position_mode: str = "ONEWAY"  # ONEWAY, HEDGE

    # DEX specific (Gateway)
    wallet_address: str = ""
    private_key: str = ""
    chain: str = "ethereum"  # ethereum, polygon, bsc, etc.
    network: str = "mainnet"  # mainnet, testnet

    # Advanced settings
    rate_limits_share_pct: float = 100.0
    max_order_update_interval: float = 10.0

    # Domain/environment
    domain: str = "com"  # com, us, testnet, etc.


class UniversalConnectorFactory:
    """Factory for creating any Hummingbot connector type."""

    # Registry of supported connector classes - Hyperliquid focused
    CONNECTOR_CLASSES: Dict[ConnectorType, Type[ConnectorBase]] = {
        ConnectorType.HYPERLIQUID_PERPETUAL: HyperliquidPerpetualDerivative,
    }

    # Connector categories mapping
    CONNECTOR_CATEGORIES: Dict[ConnectorType, ConnectorCategory] = {
        ConnectorType.HYPERLIQUID_PERPETUAL: ConnectorCategory.CEX_DERIVATIVE,
    }

    def __init__(self, client_config_map: ClientConfigAdapter):
        self.client_config_map = client_config_map
        logging.info("🔧 Universal Connector Factory initialized")
        logging.info(f"🎯 Hyperliquid-focused connector factory with {len(self.CONNECTOR_CLASSES)} connector")

    def get_supported_connectors(self) -> List[ConnectorType]:
        """Get list of all supported connector types."""
        return list(self.CONNECTOR_CLASSES.keys())

    def get_connectors_by_category(self, category: ConnectorCategory) -> List[ConnectorType]:
        """Get connectors filtered by category."""
        return [
            connector_type for connector_type, cat in self.CONNECTOR_CATEGORIES.items()
            if cat == category
        ]

    def is_connector_supported(self, connector_type: ConnectorType) -> bool:
        """Check if a connector type is supported."""
        return connector_type in self.CONNECTOR_CLASSES

    def create_connector(self, config: ConnectorConfig) -> Optional[ConnectorBase]:
        """Create a connector instance from configuration."""
        try:
            if not self.is_connector_supported(config.connector_type):
                logging.error(f"❌ Unsupported connector type: {config.connector_type}")
                return None

            connector_class = self.CONNECTOR_CLASSES[config.connector_type]
            category = self.CONNECTOR_CATEGORIES[config.connector_type]

            logging.info(f"🔌 Creating {category.value} connector: {config.connector_type.value}")

            # Create Hyperliquid connector (only supported type)
            if category == ConnectorCategory.CEX_DERIVATIVE:
                return self._create_hyperliquid_connector(connector_class, config)
            else:
                logging.error(f"❌ Unsupported connector category: {category}")
                return None

        except Exception as e:
            logging.error(f"❌ Failed to create connector {config.connector_type}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _create_hyperliquid_connector(self, connector_class: Type[ConnectorBase], config: ConnectorConfig) -> Optional[ConnectorBase]:
        """Create Hyperliquid perpetual connector with agent wallet support."""
        try:
            params = {
                "client_config_map": self.client_config_map,
                "trading_pairs": config.trading_pairs,
                "trading_required": config.trading_required,
                "domain": config.domain,
            }

            # Add authentication if trading enabled
            if config.trading_required and config.api_secret:
                params.update({
                    "hyperliquid_perpetual_api_key": config.api_key,      # Main wallet or vault address
                    "hyperliquid_perpetual_api_secret": config.api_secret,  # Agent wallet private key
                    "use_vault": config.api_key != config.wallet_address if config.wallet_address else False
                })

            return connector_class(**params)

        except Exception as e:
            logging.error(f"❌ Failed to create Hyperliquid connector: {e}")
            return None

    def get_default_trading_pairs(self, connector_type: ConnectorType) -> List[str]:
        """Get default trading pairs for Hyperliquid."""
        if connector_type == ConnectorType.HYPERLIQUID_PERPETUAL:
            return ["PURR-USDC"]  # Use PURR-USDC as it's available on Hyperliquid spot
        return ["PURR-USDC"]  # Default fallback

    def validate_config(self, config: ConnectorConfig) -> bool:
        """Validate connector configuration."""
        if not self.is_connector_supported(config.connector_type):
            logging.error(f"❌ Unsupported connector: {config.connector_type}")
            return False

        if not config.trading_pairs:
            logging.error("❌ No trading pairs specified")
            return False

        if config.trading_required:
            if not config.api_secret:
                logging.error("❌ Private key required for Hyperliquid trading")
                return False

        return True


# Convenience functions for common connector creation
def create_hyperliquid_connector(
    client_config_map: ClientConfigAdapter,
    main_wallet_address: str = "",
    agent_private_key: str = "",
    trading_pairs: List[str] = None,
    trading_required: bool = False,
    use_vault: bool = False,
    domain: str = "testnet"
) -> Optional[HyperliquidPerpetualDerivative]:
    """Create Hyperliquid connector with agent wallet support (follows Hummingbot pattern)."""
    factory = UniversalConnectorFactory(client_config_map)

    config = ConnectorConfig(
        connector_type=ConnectorType.HYPERLIQUID_PERPETUAL,
        trading_pairs=trading_pairs or ["PURR-USDC"],
        trading_required=trading_required,
        api_key=main_wallet_address,        # Main wallet or vault address
        api_secret=agent_private_key,       # Agent wallet private key
        wallet_address=main_wallet_address,  # For vault detection
        domain=domain
    )

    return factory.create_connector(config)


def create_hyperliquid_connector_simple(
    client_config_map: ClientConfigAdapter,
    private_key: str = "",
    trading_pairs: List[str] = None,
    trading_required: bool = False,
    domain: str = "testnet"
) -> Optional[HyperliquidPerpetualDerivative]:
    """Legacy function - use agent private key as private_key parameter."""
    return create_hyperliquid_connector(
        client_config_map=client_config_map,
        main_wallet_address="",  # Will be extracted from private key
        agent_private_key=private_key,
        trading_pairs=trading_pairs,
        trading_required=trading_required,
        domain=domain
    )


# Removed - not needed since we only support Hyperliquid


# Export main classes and functions
__all__ = [
    "ConnectorType",
    "ConnectorCategory",
    "ConnectorConfig",
    "UniversalConnectorFactory",
    "create_hyperliquid_connector"
]
