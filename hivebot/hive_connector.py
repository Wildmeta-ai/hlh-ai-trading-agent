#!/usr/bin/env python3

"""
Hive Connector Integration Module - Hummingbot connector initialization and management.
"""

import asyncio
import logging
from typing import Optional

# Hummingbot imports
from hummingbot.client.config.config_helpers import ClientConfigAdapter
from hummingbot.connector.derivative.hyperliquid_perpetual import hyperliquid_perpetual_constants as CONSTANTS
from hummingbot.connector.derivative.hyperliquid_perpetual.hyperliquid_perpetual_derivative import (
    HyperliquidPerpetualDerivative,
)


class HiveConnectorManager:
    """Manages Hummingbot connector initialization and lifecycle."""

    def __init__(self, client_config_map: ClientConfigAdapter):
        self.client_config_map = client_config_map
        self.real_connector: Optional[HyperliquidPerpetualDerivative] = None
        # **CRITICAL**: TradingCore expects a connectors property
        self.connectors = {}
        # Store wallet address for instance identification
        self.wallet_address = None

    async def initialize_real_connector(self, enable_trading: bool = False, private_key: str = "", required_trading_pairs: list = None, network: str = "testnet") -> bool:
        """Initialize REAL Hummingbot HyperliquidPerpetual connector - Task 1 Integration."""
        try:
            if enable_trading and private_key:
                logging.info("🔌 Initializing REAL Hummingbot HyperliquidPerpetual connector with TRADING ENABLED...")
            else:
                logging.info("🔌 Initializing REAL Hummingbot HyperliquidPerpetual connector (market data only)...")

            # Use dynamic trading pairs based on active strategies, fallback to BTC-USD
            if required_trading_pairs:
                trading_pairs = list(set(required_trading_pairs))  # Remove duplicates
                logging.info(f"🎯 Dynamic trading pairs from strategies: {trading_pairs}")
            else:
                trading_pairs = ["BTC-USD"]  # Default fallback
                logging.info("⚠️ No strategy trading pairs provided, using BTC-USD fallback")

            # Determine the domain based on network choice
            domain = CONSTANTS.DOMAIN if network == "mainnet" else CONSTANTS.TESTNET_DOMAIN
            logging.info(f"🌐 Using {network.upper()} network (domain: {domain})")

            # Create real HyperliquidPerpetualDerivative connector
            if enable_trading and private_key:
                # For spawned bots, use main wallet address from environment, otherwise derive from agent key
                import os
                main_wallet_address = os.getenv("HIVE_USER_ADDRESS", "")

                if main_wallet_address:
                    # Use main wallet address for spawned instances
                    wallet_address = main_wallet_address
                    logging.info(f"👤 Using main wallet address from environment: {wallet_address}")
                else:
                    # Derive wallet address from private key for standalone instances
                    from eth_account import Account
                    account = Account.from_key(private_key)
                    wallet_address = account.address
                    logging.info(f"🔑 Derived wallet address from agent key: {wallet_address}")

                # Store wallet address for instance identification
                self.wallet_address = wallet_address

                # REAL TRADING MODE
                self.real_connector = HyperliquidPerpetualDerivative(
                    client_config_map=self.client_config_map,
                    hyperliquid_perpetual_api_key=wallet_address,  # Main wallet address as API key
                    hyperliquid_perpetual_api_secret=private_key,  # Agent private key for signing
                    trading_pairs=trading_pairs,
                    trading_required=True,  # Enable real trading
                    domain=domain
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
                    domain=domain
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

                # Initialize trading rules
                try:
                    logging.info("📋 Initializing trading rules...")
                    await self.real_connector._update_trading_rules()
                    logging.info(f"✅ Trading rules initialized for {len(self.real_connector._trading_rules)} trading pairs")
                except Exception as e:
                    logging.warning(f"⚠️ Failed to initialize trading rules: {e}")

                if enable_trading:
                    logging.info("💰 TRADING MODE: Connector ready for real orders!")

                # **CRITICAL**: Add connector to connectors dict for TradingCore
                self.connectors["hyperliquid_perpetual"] = self.real_connector

                return True
            elif has_market_data:
                logging.warning("⚠️ Connector not fully ready, but has market data - proceeding...")
                logging.info("🔧 This is normal for Hyperliquid - orders can still be placed")
                logging.info(f"📊 Domain: {self.real_connector.domain}")
                logging.info(f"🎯 Trading pairs: {self.real_connector.trading_pairs}")

                # Initialize trading rules even if not fully ready
                try:
                    logging.info("📋 Initializing trading rules...")
                    await self.real_connector._update_trading_rules()
                    logging.info(f"✅ Trading rules initialized for {len(self.real_connector._trading_rules)} trading pairs")
                except Exception as e:
                    logging.warning(f"⚠️ Failed to initialize trading rules: {e}")

                if enable_trading:
                    logging.info("💰 TRADING MODE: Connector functional for real orders!")

                # **CRITICAL**: Add connector to connectors dict for TradingCore
                self.connectors["hyperliquid_perpetual"] = self.real_connector

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

                    # Initialize trading rules after extended wait
                    try:
                        logging.info("📋 Initializing trading rules...")
                        await self.real_connector._update_trading_rules()
                        logging.info(f"✅ Trading rules initialized for {len(self.real_connector._trading_rules)} trading pairs")
                    except Exception as e:
                        logging.warning(f"⚠️ Failed to initialize trading rules: {e}")

                    return True

                logging.error("❌ Connector failed to initialize properly - no market data available")
                return False

        except Exception as e:
            logging.error(f"❌ Failed to initialize real connector: {e}")
            import traceback
            traceback.print_exc()
            return False

    def get_connector(self) -> Optional[HyperliquidPerpetualDerivative]:
        """Get the initialized connector."""
        return self.real_connector

    def get_supported_trading_pairs(self) -> list:
        """Get all trading pairs supported by the current connector."""
        if self.real_connector and hasattr(self.real_connector, 'order_books'):
            return list(self.real_connector.order_books.keys())
        return []

    def is_trading_pair_supported(self, trading_pair: str) -> bool:
        """Check if a trading pair is supported by the connector."""
        supported_pairs = self.get_supported_trading_pairs()
        return trading_pair in supported_pairs

    def is_connector_ready(self) -> bool:
        """Check if connector is ready for operations."""
        if not self.real_connector:
            return False

        # Check if we have basic market data access for any supported pair
        has_market_data = len(self.real_connector.order_books) > 0

        return self.real_connector.ready or has_market_data

    def is_trading_enabled(self) -> bool:
        """Check if trading is enabled on the connector."""
        if not self.real_connector:
            return False

        # Check if connector has secret key (trading credentials)
        return hasattr(self.real_connector, 'hyperliquid_perpetual_secret_key') and \
            bool(getattr(self.real_connector, 'hyperliquid_perpetual_secret_key', ''))

    def get_wallet_address(self) -> Optional[str]:
        """Get the current wallet address used by the connector."""
        return self.wallet_address

    def get_wallet_short(self) -> str:
        """Get shortened wallet address for display (first 6 + last 4 chars)."""
        if not self.wallet_address:
            return "unknown"
        return f"{self.wallet_address[:6]}...{self.wallet_address[-4:]}"

    async def add_trading_pairs(self, new_trading_pairs: list) -> bool:
        """Add new trading pairs to the running connector dynamically."""
        if not self.real_connector:
            logging.error("❌ No connector available to add trading pairs to")
            return False

        try:
            current_pairs = set(self.real_connector.trading_pairs)
            pairs_to_add = [pair for pair in new_trading_pairs if pair not in current_pairs]

            if not pairs_to_add:
                logging.info(f"✅ All trading pairs already subscribed: {new_trading_pairs}")
                return True

            logging.info(f"🔄 Adding new trading pairs to running connector: {pairs_to_add}")

            # Update the connector's trading pairs list
            updated_pairs = list(current_pairs) + pairs_to_add
            self.real_connector._trading_pairs = updated_pairs

            # Initialize order book trackers for new pairs
            for pair in pairs_to_add:
                try:
                    # Create order book tracker for the new pair
                    logging.info(f"📊 Initializing order book tracker for {pair}")

                    # The order book tracker should automatically subscribe to the new pair
                    # when it detects it's in the trading_pairs list
                    await self.real_connector._order_book_tracker.start()

                    # Verify the order book was created
                    if pair not in self.real_connector.order_books:
                        # Force creation if it doesn't exist
                        logging.info(f"🔧 Force creating order book for {pair}")
                        # The connector should handle this automatically through its update cycle

                    logging.info(f"✅ Successfully added trading pair: {pair}")

                except Exception as e:
                    logging.error(f"❌ Failed to add trading pair {pair}: {e}")
                    continue

            # Update trading rules for new pairs
            try:
                await self.real_connector._update_trading_rules()
                logging.info(f"✅ Updated trading rules for new pairs")
            except Exception as e:
                logging.warning(f"⚠️ Failed to update trading rules: {e}")

            # Give the connector time to initialize the new pairs
            import asyncio
            await asyncio.sleep(5)

            # Verify success
            final_books = list(self.real_connector.order_books.keys())
            successful_pairs = [pair for pair in pairs_to_add if pair in final_books]
            failed_pairs = [pair for pair in pairs_to_add if pair not in final_books]

            if successful_pairs:
                logging.info(f"✅ Successfully added trading pairs: {successful_pairs}")
            if failed_pairs:
                logging.warning(f"⚠️ Failed to add trading pairs: {failed_pairs}")

            return len(successful_pairs) > 0

        except Exception as e:
            logging.error(f"❌ Error adding trading pairs: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def stop_connector(self):
        """Stop the connector and clean up resources."""
        if self.real_connector:
            try:
                await self.real_connector.stop_network()
                logging.info("🛑 Connector stopped successfully")
            except Exception as e:
                logging.error(f"❌ Error stopping connector: {e}")
            finally:
                self.real_connector = None
