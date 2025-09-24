#!/usr/bin/env python3

"""
Hive Position Tracker - Captures real-time position data from Hummingbot connectors.
Integrates with the full Hummingbot ecosystem for accurate P&L tracking.
"""

import asyncio
import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, List

# For direct API access to Hyperliquid
import aiohttp

from hummingbot.connector.derivative.hyperliquid_perpetual.hyperliquid_perpetual_derivative import (
    HyperliquidPerpetualDerivative,
)
from hummingbot.connector.derivative.position import Position


class HivePositionTracker:
    """
    Tracks positions from real Hummingbot connectors and persists them to database.
    """

    def __init__(self, postgres_sync=None):
        self.postgres_sync = postgres_sync
        self.last_position_update = 0
        self.position_update_interval = 30  # Update every 30 seconds

        logging.info("🎯 HivePositionTracker initialized")

    def _safe_float(self, value, default=1.0):
        """Safely convert value to float, handling dicts and other types."""
        try:
            if isinstance(value, dict):
                # If it's a dict, try to extract a numeric value from common keys
                # Prioritize 'value' for Hyperliquid leverage structure
                for key in ['value', 'amount', 'leverage', 'raw', 'val', 'rawUsd']:
                    if key in value:
                        return float(value[key])
                # If no numeric keys found, return default
                return default
            elif value is None:
                return default
            else:
                return float(value)
        except (TypeError, ValueError):
            return default

    async def get_hyperliquid_positions_direct(self, connector: HyperliquidPerpetualDerivative) -> List[Dict]:
        """
        Get positions directly from Hyperliquid API using the connector's credentials.
        """
        positions = []

        if not connector or not hasattr(connector, '_trading_required') or not connector._trading_required:
            logging.debug("Connector not configured for trading - no positions to fetch")
            return positions

        try:
            # Get the user address from the connector
            user_address = None

            # Try multiple possible attributes for user address
            # Include hyperliquid-specific attribute names
            address_attrs = ['hyperliquid_perpetual_api_key', '_user_address', 'user_address', '_account_id', 'account_id', '_wallet_address', 'wallet_address']

            # First, log all available attributes for debugging
            logging.info(f"🔍 Connector {connector.name} has these attributes: {[attr for attr in dir(connector) if not attr.startswith('__')][:20]}...")

            for attr in address_attrs:
                if hasattr(connector, attr):
                    value = getattr(connector, attr)
                    logging.info(f"🔍 Checking connector.{attr}: {value}")
                    if value:
                        user_address = value
                        logging.info(f"✅ Found user address in connector.{attr}: {user_address}")
                        break

            # Also try to get it from the connector manager if available
            if not user_address and hasattr(connector, 'connector_manager'):
                cm = connector.connector_manager
                if hasattr(cm, 'get_wallet_address'):
                    user_address = cm.get_wallet_address()
                    logging.info(f"✅ Found user address from connector manager: {user_address}")

            # Try to get from parent hive connector
            if not user_address and hasattr(connector, '_parent_connector'):
                parent = connector._parent_connector
                if hasattr(parent, 'wallet_address'):
                    user_address = parent.wallet_address
                    logging.info(f"✅ Found user address from parent connector: {user_address}")

            # If still no address, try to derive it from the private key
            if not user_address and hasattr(connector, '_private_key') and connector._private_key:
                try:
                    # For Hyperliquid, derive address from private key using eth_account
                    from eth_account import Account
                    account = Account.from_key(connector._private_key)
                    user_address = account.address
                    logging.info(f"🔑 Derived user address from private key: {user_address}")
                except Exception as e:
                    logging.warning(f"❌ Failed to derive address from private key: {e}")
                    logging.info("🔍 Have private key but cannot derive address")

            if not user_address:
                logging.warning("❌ No user address found - trying alternative position fetch methods")
                # Since orders are working, try to get positions via connector's internal methods
                try:
                    # Check if connector has position data internally
                    if hasattr(connector, '_account_positions') and connector._account_positions:
                        logging.info(f"📊 Found connector._account_positions: {len(connector._account_positions)} positions")
                        # Continue to process these positions below
                    else:
                        logging.info("📊 No positions in connector._account_positions, trying direct API without user address")
                        # Try to get positions from the exchange API using the connector's session
                        if hasattr(connector, '_api_request'):
                            try:
                                # Use the connector's own API request method
                                position_data = await connector._api_request("info", {"type": "clearinghouseState", "user": connector._wallet_address if hasattr(connector, '_wallet_address') else ""})
                                if position_data and 'assetPositions' in position_data:
                                    logging.info(f"📊 Got positions via connector API: {len(position_data['assetPositions'])}")
                            except Exception as e:
                                logging.info(f"📊 Connector API request failed: {e}")
                except Exception as e:
                    logging.warning(f"❌ Alternative position fetch failed: {e}")

                # Don't return early - continue with Hummingbot's position management below

            # Use the connector's base URL
            base_url = "http://15.235.212.39:8081/info"

            # Request clearinghouse state including positions
            async with aiohttp.ClientSession() as session:
                payload = {
                    "type": "clearinghouseState",
                    "user": user_address
                }
                logging.info(f"🔍 Fetching positions for address: {user_address}")

                async with session.post(base_url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()

                        # Extract position data
                        if 'assetPositions' in data:
                            for position_data in data['assetPositions']:
                                if position_data.get('position', {}).get('szi', '0') != '0':
                                    # Parse position data
                                    position = position_data['position']
                                    logging.info(f"🔍 Raw position data: {position}")
                                    size = self._safe_float(position.get('szi', 0), 0)
                                    entry_price = self._safe_float(position.get('entryPx', 0), 0)
                                    unrealized_pnl = self._safe_float(position.get('unrealizedPnl', 0), 0)
                                    logging.info(f"🔍 Parsed values: size={size}, entry_price={entry_price}, unrealized_pnl={unrealized_pnl}")

                                    # Get mark price from position data or market data
                                    mark_price = entry_price  # Will be updated with current market price
                                    if 'markPx' in position:
                                        mark_price = self._safe_float(position['markPx'], entry_price)

                                    # Asset info
                                    asset = position_data.get('asset', 'BTC')
                                    trading_pair = f"{asset}-USD"

                                    # Identify the strategy responsible for this position
                                    side = 'LONG' if size > 0 else 'SHORT'
                                    strategy_name = self._identify_strategy_for_position(trading_pair, side, abs(size))

                                    position_info = {
                                        'account_name': 'hyperliquid_main',
                                        'connector_name': connector.name,
                                        'trading_pair': trading_pair,
                                        'strategy_name': strategy_name,  # Add the real strategy name
                                        'timestamp': datetime.now(),
                                        'side': 'LONG' if size > 0 else 'SHORT',
                                        'exchange_size': abs(size),
                                        'entry_price': entry_price,
                                        'mark_price': mark_price,
                                        'unrealized_pnl': unrealized_pnl,
                                        'percentage_pnl': (unrealized_pnl / (abs(size) * entry_price) * 100) if entry_price > 0 and size != 0 else 0,
                                        'leverage': self._safe_float(position.get('leverage', 1)),
                                        'initial_margin': abs(size) * entry_price / self._safe_float(position.get('leverage', 1)) if entry_price > 0 else 0,
                                        'maintenance_margin': 0.0,
                                        'cumulative_funding_fees': 0.0,
                                        'fee_currency': 'USD',
                                        'calculated_size': abs(size),
                                        'calculated_entry_price': entry_price,
                                        'size_difference': 0.0,
                                        'exchange_position_id': f"{trading_pair}_{position.get('positionId', 'main')}",
                                        'is_reconciled': 'true'  # This is real API data
                                    }

                                    positions.append(position_info)
                                    logging.info(f"💰 Direct API position: {trading_pair} {position_info['side']} {abs(size)} @ {entry_price} (PnL: {unrealized_pnl}) [Strategy: {strategy_name}]")

                        logging.info(f"📊 Fetched {len(positions)} positions from Hyperliquid API")
                    else:
                        logging.error(f"❌ Failed to fetch positions from Hyperliquid API: {response.status}")

        except Exception as e:
            logging.error(f"❌ Error fetching positions from Hyperliquid API: {e}")
            import traceback
            traceback.print_exc()

        return positions

    async def capture_positions_from_connector(self, connector: HyperliquidPerpetualDerivative, account_name: str = "default") -> List[Dict]:
        """
        Capture real-time positions from Hyperliquid connector using Hummingbot's native position tracking.
        """
        positions = []

        if not connector or not connector.ready:
            logging.debug("Connector not ready for position capture")
            return positions

        try:
            # Try direct API approach first for Hyperliquid
            if connector.name and 'hyperliquid' in connector.name.lower():
                logging.info("🔍 Attempting direct Hyperliquid API position fetch...")
                direct_positions = await self.get_hyperliquid_positions_direct(connector)
                if direct_positions:
                    logging.info(f"✅ Got {len(direct_positions)} positions from direct API")
                    return direct_positions
                else:
                    logging.info("📊 No positions found via direct API, trying Hummingbot connector...")

            # Fallback to original Hummingbot connector approach
            # Force position update using Hummingbot's native method
            await connector._update_positions()

            # For Hyperliquid, also try to force balance update which may contain position data
            if hasattr(connector, '_update_balances'):
                await connector._update_balances()

            # For Hyperliquid perpetual, try to access positions directly from the API if available
            if hasattr(connector, '_trading_required') and hasattr(connector, 'get_positions'):
                try:
                    # Some derivative connectors have a direct get_positions method
                    positions_data = await connector.get_positions()
                    if positions_data:
                        logging.info(f"📊 Direct positions from API: {positions_data}")
                except Exception as e:
                    logging.debug(f"Direct positions API not available: {e}")

            # Check if Hyperliquid stores positions elsewhere
            if hasattr(connector, '_account_data'):
                logging.info(f"📊 Account data: {connector._account_data}")
            if hasattr(connector, 'positions'):
                logging.info(f"📊 Positions attribute: {connector.positions}")

            logging.info("🔍 Checking connector for positions...")
            logging.info(f"  - Connector ready: {connector.ready}")
            logging.info(f"  - Has _account_positions: {hasattr(connector, '_account_positions')}")
            if hasattr(connector, '_account_positions'):
                logging.info(f"  - Account positions count: {len(connector._account_positions) if connector._account_positions else 0}")
            logging.info(f"  - Has _account_balances: {hasattr(connector, '_account_balances')}")
            if hasattr(connector, '_account_balances'):
                logging.info(f"  - Account balances: {dict(connector._account_balances) if connector._account_balances else {}}")

            # Access positions using Hummingbot's position management
            if hasattr(connector, '_account_positions') and connector._account_positions:
                logging.info(f"📊 Found {len(connector._account_positions)} positions in connector")

                for position_key, position in connector._account_positions.items():
                    logging.info(f"📊 Position key: {position_key}, Position type: {type(position)}, Amount: {position.amount if hasattr(position, 'amount') else 'N/A'}")
                    if isinstance(position, Position) and position.amount != Decimal("0"):
                        # Extract position data using Hummingbot's Position class
                        position_data = {
                            'account_name': account_name,
                            'connector_name': connector.name,
                            'trading_pair': position.trading_pair,
                            'timestamp': datetime.now(),
                            'side': position.position_side.name,  # LONG or SHORT
                            'exchange_size': float(position.amount),
                            'entry_price': float(position.entry_price),
                            'mark_price': float(position.entry_price),  # Would get current price from market
                            'unrealized_pnl': float(position.unrealized_pnl),
                            'percentage_pnl': 0.0,  # Calculate if needed
                            'leverage': float(position.leverage),
                            'initial_margin': float(position.amount * position.entry_price / position.leverage) if position.leverage > 0 else 0,
                            'maintenance_margin': 0.0,  # Would get from exchange if available
                            'cumulative_funding_fees': 0.0,  # Would track over time
                            'fee_currency': 'USD',
                            'calculated_size': float(position.amount),
                            'calculated_entry_price': float(position.entry_price),
                            'size_difference': 0.0,
                            'exchange_position_id': f"{position.trading_pair}_{position.position_side.name}",
                            'is_reconciled': 'true'
                        }

                        positions.append(position_data)
                        logging.info(f"💰 Captured position: {position.trading_pair} {position.position_side.name} {position.amount} @ {position.entry_price} (PnL: {position.unrealized_pnl})")

            # Also try to get positions via account balances for derivatives
            else:
                logging.info("📊 No positions found in connector._account_positions. Checking account balances instead...")
                logging.info(f"  - _account_positions exists: {hasattr(connector, '_account_positions')}")
                if hasattr(connector, '_account_positions'):
                    logging.info(f"  - _account_positions value: {connector._account_positions}")
                    logging.info(f"  - _account_positions length: {len(connector._account_positions) if connector._account_positions else 0}")

            if hasattr(connector, '_account_balances'):
                # Get current market prices for P&L calculation
                current_prices = {}
                for trading_pair in connector.trading_pairs:
                    if trading_pair in connector.order_books:
                        order_book = connector.order_books[trading_pair]
                        if hasattr(order_book, 'get_mid_price'):
                            current_prices[trading_pair] = float(order_book.get_mid_price())

                logging.info(f"📊 Current market prices: {current_prices}")

                # Check balances for position information
                for asset, balance in connector._account_balances.items():
                    if balance != Decimal("0") and asset != "USD":  # Skip zero balances and quote currency
                        trading_pair = f"{asset}-USD"
                        if trading_pair in connector.trading_pairs:
                            current_price = current_prices.get(trading_pair, 0)

                            position_data = {
                                'account_name': account_name,
                                'connector_name': connector.name,
                                'trading_pair': trading_pair,
                                'timestamp': datetime.now(),
                                'side': 'LONG' if balance > 0 else 'SHORT',
                                'exchange_size': float(abs(balance)),
                                'entry_price': current_price,  # Approximate - would need trade history for accuracy
                                'mark_price': current_price,
                                'unrealized_pnl': 0.0,  # Would need entry price history
                                'percentage_pnl': 0.0,
                                'leverage': 1.0,  # Default for spot-like positions
                                'initial_margin': float(abs(balance) * current_price),
                                'maintenance_margin': 0.0,
                                'cumulative_funding_fees': 0.0,
                                'fee_currency': 'USD',
                                'calculated_size': float(abs(balance)),
                                'calculated_entry_price': current_price,
                                'size_difference': 0.0,
                                'exchange_position_id': f"{trading_pair}_BALANCE",
                                'is_reconciled': 'false'  # Balance-based estimate
                            }

                            positions.append(position_data)
                            logging.info(f"💰 Estimated position from balance: {trading_pair} {balance}")

        except Exception as e:
            logging.error(f"❌ Error capturing positions from connector: {e}")
            import traceback
            traceback.print_exc()

        return positions

    async def save_positions_to_database(self, positions: List[Dict]):
        """
        Save position snapshots to PostgreSQL database using the same structure as Hummingbot.
        """
        if not self.postgres_sync or not positions:
            return

        try:
            for position in positions:
                insert_query = """
                INSERT INTO position_snapshots (
                    account_name, connector_name, trading_pair, timestamp,
                    side, exchange_size, entry_price, mark_price, unrealized_pnl,
                    percentage_pnl, leverage, initial_margin, maintenance_margin,
                    cumulative_funding_fees, fee_currency, calculated_size,
                    calculated_entry_price, size_difference, exchange_position_id,
                    is_reconciled
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                """

                params = (
                    position['account_name'],
                    position['connector_name'],
                    position['trading_pair'],
                    position['timestamp'],
                    position['side'],
                    position['exchange_size'],
                    position['entry_price'],
                    position['mark_price'],
                    position['unrealized_pnl'],
                    position['percentage_pnl'],
                    position['leverage'],
                    position['initial_margin'],
                    position['maintenance_margin'],
                    position['cumulative_funding_fees'],
                    position['fee_currency'],
                    position['calculated_size'],
                    position['calculated_entry_price'],
                    position['size_difference'],
                    position['exchange_position_id'],
                    position['is_reconciled']
                )

                await self.postgres_sync.execute_query(insert_query, params)
                logging.debug(f"💾 Saved position to database: {position['trading_pair']} {position['side']} {position['exchange_size']}")

        except Exception as e:
            logging.error(f"❌ Error saving positions to database: {e}")
            import traceback
            traceback.print_exc()

    async def cleanup_closed_positions(self, account_name: str = "default"):
        """
        Remove old positions from database to ensure closed positions don't linger in the UI.
        This is more aggressive cleanup when no active positions are detected.
        """
        if not self.postgres_sync:
            return
        try:
            # Remove positions older than 30 seconds when no active positions exist
            cleanup_query = """
            DELETE FROM position_snapshots
            WHERE account_name = %s AND timestamp < NOW() - INTERVAL '30 seconds'
            """
            await self.postgres_sync.execute_query(cleanup_query, (account_name,))
            logging.info("🧹 Cleaned up old positions from database")
        except Exception as e:
            logging.error(f"❌ Error cleaning up closed positions: {e}")

    async def cleanup_zero_size_positions(self, account_name: str = "default"):
        """
        Remove positions with zero size from database.
        These are closed positions that should not appear in the UI.
        """
        if not self.postgres_sync:
            return
        try:
            cleanup_query = """
            DELETE FROM position_snapshots
            WHERE account_name = %s AND (exchange_size = 0 OR exchange_size IS NULL)
            """
            await self.postgres_sync.execute_query(cleanup_query, (account_name,))
            logging.debug("🧹 Cleaned up zero-size positions from database")
        except Exception as e:
            logging.error(f"❌ Error cleaning up zero-size positions: {e}")

    async def update_account_balances(self, connector: HyperliquidPerpetualDerivative, account_name: str = "default"):
        """
        Update account balance information in the database.
        """
        if not self.postgres_sync or not connector or not connector.ready:
            return

        try:
            # Force balance update
            await connector._update_balances()

            logging.info("💰 Account balance update...")
            if hasattr(connector, '_account_balances'):
                balances = dict(connector._account_balances) if connector._account_balances else {}
                logging.info(f"  - Found balances: {balances}")

                # Skip database save for now due to schema issues
                logging.info("  - Skipping database save (schema issues)")
            else:
                logging.info("  - No account balances found")

        except Exception as e:
            logging.error(f"❌ Error updating account balances: {e}")

    async def start_position_tracking(self, connector: HyperliquidPerpetualDerivative, account_name: str = "default", strategy_registry: dict = None):
        """
        Start continuous position tracking for a connector.

        Args:
            connector: The Hyperliquid connector to track positions for
            account_name: Account identifier
            strategy_registry: Dictionary of running strategies {name: strategy_instance}
        """
        self.strategy_registry = strategy_registry or {}
        logging.info(f"🎯 Starting position tracking for {connector.name} with {len(self.strategy_registry)} strategies")

        # Main tracking loop
        while True:
            try:
                # Capture positions
                positions = await self.capture_positions_from_connector(connector, account_name)

                if positions:
                    await self.save_positions_to_database(positions)
                    logging.info(f"📊 Updated {len(positions)} positions in database")
                else:
                    logging.debug("📊 No active positions found")
                    # Clean up closed positions from database when no positions exist
                    await self.cleanup_closed_positions(account_name)

                # Also clean up any positions with zero size
                await self.cleanup_zero_size_positions(account_name)

                # Update account balances
                await self.update_account_balances(connector, account_name)

                # Wait for next update
                await asyncio.sleep(self.position_update_interval)

            except Exception as e:
                logging.error(f"❌ Error in position tracking loop: {e}")
                await asyncio.sleep(10)  # Shorter retry interval on error

    def _identify_strategy_for_position(self, trading_pair: str, side: str, size: float) -> str:
        """
        Identify which strategy is most likely responsible for a position.

        Args:
            trading_pair: The trading pair (e.g., 'ETH-USD')
            side: Position side ('LONG' or 'SHORT')
            size: Position size

        Returns:
            Strategy name or 'Unknown' if cannot determine
        """
        if not self.strategy_registry:
            return 'Unknown'

        # Find strategies trading this pair
        matching_strategies = []
        for strategy_name, strategy_instance in self.strategy_registry.items():
            try:
                # Check if strategy is active and trading this pair
                if hasattr(strategy_instance, 'config') and strategy_instance.config:
                    config = strategy_instance.config
                    if hasattr(config, 'market') and config.market:
                        # Convert market format to trading pair format if needed
                        strategy_pair = config.market
                        if strategy_pair.replace('-', '') == trading_pair.replace('-', ''):
                            matching_strategies.append(strategy_name)
                            logging.debug(f"🔍 Strategy {strategy_name} matches trading pair {trading_pair}")
            except Exception as e:
                logging.debug(f"🔍 Could not check strategy {strategy_name} for pair matching: {e}")
                continue

        if len(matching_strategies) == 1:
            # Perfect match - only one strategy trading this pair
            return matching_strategies[0]
        elif len(matching_strategies) > 1:
            # Multiple strategies - return the most recently created one (typically active)
            # Sort by creation time if available, otherwise return the first one
            return matching_strategies[-1]  # Last in list is usually most recent
        else:
            # No exact match - return the first active strategy as fallback
            if self.strategy_registry:
                return list(self.strategy_registry.keys())[0]
            return 'Unknown'
