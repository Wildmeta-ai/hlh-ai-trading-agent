#!/usr/bin/env python3

"""
Hive API Server Module - REST API endpoints for dynamic strategy management.
"""

import logging
import time
from typing import Optional

from aiohttp import web
from aiohttp.web import middleware

# Import required types
from hive_database import DynamicStrategyConfig


@middleware
async def cors_handler(request, handler):
    """CORS middleware to handle cross-origin requests."""
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        response = web.Response()
    else:
        response = await handler(request)

    # Add CORS headers
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
    response.headers['Access-Control-Max-Age'] = '86400'  # 24 hours

    return response


class HiveAPIServer:
    """REST API server for dynamic strategy management."""

    def __init__(self, hive_core=None):
        """
        Initialize API server.

        Args:
            hive_core: Reference to the main HiveDynamicCore instance
        """
        self.hive_core = hive_core
        self._api_server: Optional[web.Application] = None
        self._api_runner: Optional[web.AppRunner] = None

    async def start_api_server(self, port: int):
        """Start REST API server for dynamic strategy management."""
        self._api_server = web.Application(middlewares=[cors_handler])

        # API Routes
        self._api_server.router.add_get('/api/strategies', self.api_list_strategies)
        self._api_server.router.add_post('/api/strategies', self.api_create_strategy)
        self._api_server.router.add_put('/api/strategies/{name}', self.api_update_strategy)
        self._api_server.router.add_delete('/api/strategies/{name}', self.api_delete_strategy)
        self._api_server.router.add_post('/api/positions/force-close', self.api_force_close_positions)
        self._api_server.router.add_post('/api/strategies/sync-from-postgres', self.api_sync_from_postgres)
        self._api_server.router.add_get('/api/status', self.api_hive_status)
        self._api_server.router.add_get('/api/positions', self.api_get_positions)
        self._api_server.router.add_post('/api/positions/force-sync', self.api_force_position_sync)
        self._api_server.router.add_get('/api/positions/debug', self.api_debug_positions)

        # Start server
        self._api_runner = web.AppRunner(self._api_server)
        await self._api_runner.setup()
        site = web.TCPSite(self._api_runner, '0.0.0.0', port)
        await site.start()

        logging.info(f"🌐 API server started on http://0.0.0.0:{port} (accessible via nginx proxy)")

    async def stop_api_server(self):
        """Stop the API server."""
        if self._api_runner:
            await self._api_runner.cleanup()
            logging.info("🌐 API server stopped")

    async def api_list_strategies(self, request):
        """API endpoint: List all strategies."""
        if not self.hive_core:
            return web.json_response({"error": "Hive core not available"}, status=500)

        # Extract wallet address from headers for user authentication
        wallet_address = request.headers.get('X-Wallet-Address')
        if not wallet_address:
            header_keys = sorted(request.headers.keys())
            logging.warning(
                "❌ Missing X-Wallet-Address header on %s %s. Received headers: %s",
                request.method,
                request.path,
                header_keys
            )
            return web.json_response({
                "error": "Missing X-Wallet-Address header",
                "debug": {
                    "received_header_keys": header_keys
                }
            }, status=401)

        logging.info(f"🔐 API request from wallet: {wallet_address}")

        # Filter strategies by the authenticated wallet address
        strategies_status = []
        user_strategy_count = 0

        for name, info in self.hive_core.strategies.items():
            # Only include strategies belonging to this wallet/user
            # Check if strategy's api_key (main wallet address) matches the requesting wallet
            try:
                # Get the wallet address from strategy config (stored as api_key for Hyperliquid)
                strategy_wallet = None
                if hasattr(info, 'config') and hasattr(info.config, 'api_key'):
                    strategy_wallet = info.config.api_key
                elif hasattr(info, 'api_key'):
                    strategy_wallet = info.api_key

                # Only return strategies belonging to the authenticated wallet
                if strategy_wallet and strategy_wallet.lower() == wallet_address.lower():
                    strategy_dict = info.to_status_dict()
                    strategies_status.append(strategy_dict)
                    user_strategy_count += 1
                    logging.debug(f"✅ Including strategy {name} - wallet match: {strategy_wallet}")
                elif not strategy_wallet:
                    # Skip strategies without wallet association
                    logging.debug(f"❌ Skipping strategy {name} - no wallet association")
                    continue
                else:
                    logging.debug(f"❌ Skipping strategy {name} - belongs to different wallet {strategy_wallet}")

            except Exception as e:
                logging.warning(f"Error checking strategy ownership for {name}: {e}")
                # Skip strategies we can't verify ownership for
                continue

        return web.json_response({
            "strategies": strategies_status,
            "total_count": user_strategy_count,
            "timestamp": time.time(),
            "data_source": "SQLite + Real-time Bot APIs",
            "admin_view": False,
            "wallet_address": wallet_address
        })

    async def api_create_strategy(self, request):
        """API endpoint: Create new strategy."""
        if not self.hive_core:
            return web.json_response({"error": "Hive core not available"}, status=500)

        # Extract wallet address from headers for user authentication
        wallet_address = request.headers.get('X-Wallet-Address')
        if not wallet_address:
            header_keys = sorted(request.headers.keys())
            logging.warning(
                "❌ Missing X-Wallet-Address header on %s %s. Received headers: %s",
                request.method,
                request.path,
                header_keys
            )
            return web.json_response({
                "error": "Missing X-Wallet-Address header",
                "debug": {
                    "received_header_keys": header_keys
                }
            }, status=401)

        try:
            data = await request.json()
            config = DynamicStrategyConfig(**data)

            # Ensure the strategy is created with the authenticated wallet address
            # Set api_key to the authenticated wallet address to establish ownership
            if not config.api_key or config.api_key != wallet_address:
                config.api_key = wallet_address
                logging.info(f"🔐 Setting strategy {config.name} api_key to authenticated wallet: {wallet_address}")

            success = await self.hive_core.add_strategy_dynamically(config)
            if success:
                return web.json_response({"success": True, "message": f"Strategy {config.name} added"})
            else:
                return web.json_response({"success": False, "message": "Failed to add strategy"}, status=400)

        except Exception as e:
            return web.json_response({"success": False, "message": str(e)}, status=400)

    async def api_update_strategy(self, request):
        """API endpoint: Update existing strategy."""
        if not self.hive_core:
            return web.json_response({"error": "Hive core not available"}, status=500)

        # Extract wallet address from headers for user authentication
        wallet_address = request.headers.get('X-Wallet-Address')
        if not wallet_address:
            return web.json_response({"error": "Missing X-Wallet-Address header"}, status=401)

        try:
            name = request.match_info['name']

            # Verify the strategy belongs to the authenticated wallet
            if name in self.hive_core.strategies:
                strategy_info = self.hive_core.strategies[name]
                strategy_wallet = None
                if hasattr(strategy_info, 'config') and hasattr(strategy_info.config, 'api_key'):
                    strategy_wallet = strategy_info.config.api_key
                elif hasattr(strategy_info, 'api_key'):
                    strategy_wallet = strategy_info.api_key

                if not strategy_wallet or strategy_wallet.lower() != wallet_address.lower():
                    return web.json_response({"error": "Unauthorized: Strategy belongs to different wallet"}, status=403)
            else:
                return web.json_response({"error": "Strategy not found"}, status=404)

            data = await request.json()
            data['name'] = name  # Ensure name matches URL
            config = DynamicStrategyConfig(**data)

            # Ensure the updated strategy maintains the authenticated wallet address
            config.api_key = wallet_address

            success = await self.hive_core.update_strategy_config_dynamically(name, config)
            if success:
                return web.json_response({"success": True, "message": f"Strategy {name} updated"})
            else:
                return web.json_response({"success": False, "message": "Failed to update strategy"}, status=400)

        except Exception as e:
            return web.json_response({"success": False, "message": str(e)}, status=400)

    async def api_delete_strategy(self, request):
        """API endpoint: Delete strategy with optional cleanup."""
        from decimal import Decimal
        logging.warning(f"🛑 API DELETE STRATEGY CALLED: {request.url}")
        if not self.hive_core:
            return web.json_response({"error": "Hive core not available"}, status=500)

        # Extract wallet address from headers for user authentication
        wallet_address = request.headers.get('X-Wallet-Address')
        if not wallet_address:
            return web.json_response({"error": "Missing X-Wallet-Address header"}, status=401)

        try:
            name = request.match_info['name']
            logging.warning(f"🛑 DELETE STRATEGY NAME: {name}")

            # Verify the strategy belongs to the authenticated wallet before deletion
            if name in self.hive_core.strategies:
                strategy_info = self.hive_core.strategies[name]
                strategy_wallet = None
                if hasattr(strategy_info, 'config') and hasattr(strategy_info.config, 'api_key'):
                    strategy_wallet = strategy_info.config.api_key
                elif hasattr(strategy_info, 'api_key'):
                    strategy_wallet = strategy_info.api_key

                if not strategy_wallet or strategy_wallet.lower() != wallet_address.lower():
                    logging.warning(f"🛑 UNAUTHORIZED DELETE ATTEMPT: wallet {wallet_address} tried to delete strategy {name} belonging to {strategy_wallet}")
                    return web.json_response({"error": "Unauthorized: Strategy belongs to different wallet"}, status=403)

                logging.info(f"🔐 DELETE AUTHORIZED: Strategy {name} belongs to wallet {wallet_address}")
            else:
                return web.json_response({"error": "Strategy not found"}, status=404)

            # Parse query parameters for cleanup options
            close_positions = request.query.get('close_positions', 'false').lower() == 'true'
            cancel_orders = request.query.get('cancel_orders', 'false').lower() == 'true'
            logging.warning(f"🛑 DELETE PARAMS: close_positions={close_positions}, cancel_orders={cancel_orders}")

            logging.info(f"🛑 Deleting strategy {name} (close_positions: {close_positions}, cancel_orders: {cancel_orders})")

            # Step 1: Get strategy instance for cleanup
            strategy_instance = None
            if hasattr(self.hive_core, 'real_strategies') and name in self.hive_core.real_strategies:
                strategy_instance = self.hive_core.real_strategies[name]

            cleanup_results = {
                "positions_closed": 0,
                "orders_cancelled": 0,
                "cleanup_errors": []
            }

            # Step 2: Cleanup positions if requested
            logging.warning(f"🛑 DELETE STRATEGY: Starting position cleanup for {name}")
            logging.warning(f"🛑 close_positions: {close_positions}, strategy_instance: {strategy_instance is not None}, has_connector: {hasattr(self.hive_core, 'real_connector') if hasattr(self, 'hive_core') else 'no_hive_core'}")

            # NEW APPROACH: Close positions even without active strategy by using database lookup
            if close_positions:
                try:
                    positions_to_close = []
                    strategy_trading_pairs = []

                    # STEP 1: Get strategy trading pairs from database (works for inactive strategies)
                    logging.warning(f"🛑 STEP 1: Getting trading pairs for strategy {name} from database")
                    try:
                        from hive_postgres_sync import get_postgres_sync
                        postgres_sync = get_postgres_sync()

                        if postgres_sync and postgres_sync.connection:
                            query = """
                            SELECT DISTINCT trading_pairs
                            FROM strategies
                            WHERE name = %s
                            """
                            cursor = postgres_sync.connection.cursor()
                            cursor.execute(query, (name,))
                            result = cursor.fetchone()
                            cursor.close()

                            if result and result[0]:
                                # Parse JSON trading pairs from database
                                import json
                                strategy_trading_pairs = json.loads(result[0]) if isinstance(result[0], str) else result[0]
                                logging.warning(f"🎯 Found trading pairs for strategy {name}: {strategy_trading_pairs}")
                            else:
                                logging.warning(f"⚠️  No trading pairs found for strategy {name} in database")
                    except Exception as e:
                        logging.error(f"❌ Failed to get trading pairs from database: {e}")

                    # STEP 2: Get current positions from database for these trading pairs
                    logging.warning(f"🛑 STEP 2: Getting positions from database for trading pairs: {strategy_trading_pairs}")
                    try:
                        from hive_postgres_sync import get_postgres_sync
                        postgres_sync = get_postgres_sync()

                        if postgres_sync and postgres_sync.connection and strategy_trading_pairs:
                            # Get recent positions for strategy trading pairs
                            trading_pairs_str = "','".join(strategy_trading_pairs)
                            query = f"""
                            SELECT DISTINCT trading_pair, side, exchange_size
                            FROM position_snapshots
                            WHERE trading_pair IN ('{trading_pairs_str}')
                            AND timestamp > NOW() - INTERVAL '30 minutes'
                            AND exchange_size != 0
                            AND exchange_size IS NOT NULL
                            ORDER BY timestamp DESC
                            """
                            cursor = postgres_sync.connection.cursor()
                            cursor.execute(query)
                            db_positions = cursor.fetchall()
                            cursor.close()

                            logging.warning(f"🔍 Found {len(db_positions)} positions in database for strategy trading pairs")

                            # Process each position for closing
                            for trading_pair, side, exchange_size in db_positions:
                                positions_to_close.append({
                                    'trading_pair': trading_pair,
                                    'side': side,
                                    'size': float(exchange_size)
                                })
                                logging.warning(f"🎯 Added position to close: {trading_pair} {side} {exchange_size}")

                    except Exception as e:
                        logging.error(f"❌ Failed to get positions from database: {e}")

                    # STEP 3: Try connector positions as backup (if orchestrator has active strategies)
                    if not positions_to_close and hasattr(self.hive_core, 'real_connector'):
                        connector = self.hive_core.real_connector
                        logging.warning(f"🛑 STEP 3: No database positions found, checking connector positions")
                        logging.warning(f"🛑 CONNECTOR CHECK: has_account_positions={hasattr(connector, 'account_positions')}, positions_exist={getattr(connector, 'account_positions', None) is not None}, positions_count={len(getattr(connector, 'account_positions', {}))}")
                        if hasattr(connector, 'account_positions') and connector.account_positions:
                            logging.warning(f"🔍 Found {len(connector.account_positions)} positions in connector")
                            # Find positions that belong to this strategy
                            for trading_pair, position in connector.account_positions.items():
                                # Identify if this position belongs to the strategy being closed
                                if hasattr(self.hive_core, 'position_tracker') and self.hive_core.position_tracker:
                                    try:
                                        identified_strategy = self.hive_core.position_tracker._identify_strategy_for_position(
                                            trading_pair, str(position.position_side), float(position.amount)
                                        )
                                        if identified_strategy == name:
                                            positions_to_close.append((trading_pair, position))
                                    except Exception as e:
                                        logging.debug(f"Could not identify strategy for position: {e}")
                    else:
                        # Fallback: Get positions from database if connector positions unavailable
                        logging.warning(f"🛑 FALLBACK: Connector positions unavailable for {name}, checking database positions...")
                        logging.warning(f"🛑 POSTGRES CHECK: has_postgres_sync_enabled={hasattr(self.hive_core, 'postgres_sync_enabled')}, postgres_enabled={getattr(self.hive_core, 'postgres_sync_enabled', False)}")
                        if hasattr(self.hive_core, 'postgres_sync_enabled') and self.hive_core.postgres_sync_enabled:
                            try:
                                from hive_postgres_sync import get_postgres_sync
                                postgres_sync = get_postgres_sync()

                                if postgres_sync and postgres_sync.connection:
                                    query = """
                                    SELECT DISTINCT trading_pair, side, exchange_size
                                    FROM position_snapshots
                                    WHERE timestamp > NOW() - INTERVAL '5 minutes'
                                    AND exchange_size != 0
                                    AND exchange_size IS NOT NULL
                                    ORDER BY timestamp DESC
                                    """
                                    cursor = postgres_sync.connection.cursor()
                                    cursor.execute(query)
                                    db_positions = cursor.fetchall()
                                    cursor.close()

                                    logging.info(f"🔍 Found {len(db_positions)} positions in database")

                                    # Convert database positions to position-like objects
                                    for trading_pair, side, exchange_size in db_positions:
                                        # First try strategy identification
                                        identified_strategy = "Unknown"
                                        if hasattr(self.hive_core, 'position_tracker') and self.hive_core.position_tracker:
                                            try:
                                                identified_strategy = self.hive_core.position_tracker._identify_strategy_for_position(
                                                    trading_pair, side, float(exchange_size)
                                                )
                                            except Exception as e:
                                                logging.debug(f"Could not identify strategy for DB position: {e}")

                                        # If strategy identification matches OR if we're closing all positions for this strategy
                                        # (fallback when identification fails but we know this strategy trades these pairs)
                                        should_close_position = False

                                        if identified_strategy == name:
                                            should_close_position = True
                                            logging.info(f"🎯 Position {trading_pair} matched to strategy {name} via identification")
                                        else:
                                            # Fallback: Check if strategy configuration mentions this trading pair
                                            if strategy_instance and hasattr(strategy_instance, 'trading_pairs'):
                                                if trading_pair in strategy_instance.trading_pairs:
                                                    should_close_position = True
                                                    logging.info(f"🎯 Position {trading_pair} matched to strategy {name} via trading pairs")
                                            elif strategy_instance and hasattr(strategy_instance, 'config'):
                                                config = strategy_instance.config
                                                if hasattr(config, 'market') and config.market:
                                                    if trading_pair.replace('-', '') == config.market.replace('-', ''):
                                                        should_close_position = True
                                                        logging.info(f"🎯 Position {trading_pair} matched to strategy {name} via config market")

                                        if should_close_position:
                                            # Store position data directly without mock objects
                                            positions_to_close.append({
                                                'trading_pair': trading_pair,
                                                'side': side,
                                                'amount': float(exchange_size)
                                            })
                                            logging.info(f"🎯 Found position to close from database: {trading_pair} {side} {exchange_size}")
                                        else:
                                            # AGGRESSIVE FALLBACK: If strategy name contains the asset, assume it trades that pair
                                            asset_symbol = trading_pair.split('-')[0]  # SOL from SOL-USD
                                            if asset_symbol.upper() in name.upper():
                                                positions_to_close.append({
                                                    'trading_pair': trading_pair,
                                                    'side': side,
                                                    'amount': float(exchange_size)
                                                })
                                                logging.info(f"🎯 FALLBACK: Found position to close by name matching: {trading_pair} {side} {exchange_size} (asset {asset_symbol} found in strategy name {name})")
                                            else:
                                                logging.debug(f"Position {trading_pair} does not match strategy {name} - skipping")
                            except Exception as e:
                                logging.error(f"Failed to query database positions: {e}")
                        else:
                            logging.warning("🔍 No database connection available for position lookup")

                    # ULTRA FALLBACK: If no positions found but strategy_instance is None (inactive strategy),
                    # and we're explicitly requested to close positions, try to close ALL positions
                    if not positions_to_close and strategy_instance is None:
                        logging.warning(f"🛑 ULTRA FALLBACK: No positions found for inactive strategy {name}, but close_positions=True. Attempting to close ALL positions...")

                        # Get ALL positions from database regardless of strategy
                        if hasattr(self.hive_core, 'postgres_sync_enabled') and self.hive_core.postgres_sync_enabled:
                            try:
                                from hive_postgres_sync import get_postgres_sync
                                postgres_sync = get_postgres_sync()

                                if postgres_sync and postgres_sync.connection:
                                    query = """
                                    SELECT trading_pair, side, exchange_size, timestamp
                                    FROM position_snapshots
                                    WHERE timestamp > NOW() - INTERVAL '7 days'
                                    AND exchange_size != 0
                                    AND exchange_size IS NOT NULL
                                    ORDER BY timestamp DESC
                                    """
                                    cursor = postgres_sync.connection.cursor()
                                    cursor.execute(query)
                                    all_db_positions = cursor.fetchall()
                                    cursor.close()

                                    logging.warning(f"🛑 ULTRA FALLBACK: Found {len(all_db_positions)} total positions in database")

                                    # Convert ALL database positions to closeable positions
                                    for trading_pair, side, exchange_size, timestamp in all_db_positions:
                                        positions_to_close.append({
                                            'trading_pair': trading_pair,
                                            'side': side,
                                            'amount': float(exchange_size)
                                        })
                                        logging.warning(f"🛑 ULTRA FALLBACK: Adding position to close: {trading_pair} {side} {exchange_size}")

                            except Exception as e:
                                logging.error(f"🛑 ULTRA FALLBACK failed: {e}")

                    # Close positions by creating market orders in opposite direction
                    logging.warning(f"🛑 STEP 4: Executing position closing for {len(positions_to_close)} positions")

                    # Ensure we have connector access for position closing
                    if not hasattr(self.hive_core, 'real_connector') or not self.hive_core.real_connector:
                        logging.error(f"🛑 No connector available for position closing")
                        cleanup_results["cleanup_errors"].append("No connector available for position closing")
                    else:
                        connector = self.hive_core.real_connector

                        for position_item in positions_to_close:
                            try:
                                # Handle both old format (trading_pair, position) and new dictionary format
                                if isinstance(position_item, tuple):
                                    # Old format: (trading_pair, position_object)
                                    trading_pair, position = position_item
                                    close_side = TradeType.SELL if position.amount > Decimal("0") else TradeType.BUY
                                    close_amount = abs(position.amount)
                                elif isinstance(position_item, dict):
                                    # New format: {'trading_pair': ..., 'side': ..., 'amount': ...}
                                    trading_pair = position_item['trading_pair']
                                    side = position_item['side']
                                    amount = position_item['amount']
                                    # Determine close side based on current position side
                                    if side.upper() == 'LONG' or side.upper() == 'BUY' or amount > 0:
                                        close_side = TradeType.SELL  # Close LONG with SELL
                                    else:
                                        close_side = TradeType.BUY   # Close SHORT with BUY
                                    close_amount = abs(Decimal(str(amount)))
                                else:
                                    logging.error(f"🛑 Unknown position format: {position_item}")
                                    continue

                                logging.warning(f"🎯 Processing position close: {trading_pair} {close_side} {close_amount}")

                                # DYNAMIC: Ensure connector supports this trading pair
                                logging.info(f"🎯 Ensuring connector supports {trading_pair} for position closing...")
                                pair_supported = await self.hive_core.ensure_trading_pair_support(trading_pair)
                                if not pair_supported:
                                    error_msg = f"Could not initialize {trading_pair} support in connector"
                                    logging.error(f"🛑 {error_msg}")
                                    cleanup_results["cleanup_errors"].append(error_msg)
                                    continue
                                # Create market order to close position (for derivatives)
                                from hummingbot.core.data_type.common import OrderType, PositionAction, TradeType

                                # Submit market order to close position with proper position action
                                logging.info(f"🛑 Closing position: {trading_pair} {close_side} {close_amount}")

                                # Use Hummingbot's position_action parameter to properly close derivatives
                                # For derivatives, must specify position_action=PositionAction.CLOSE
                                try:
                                    if close_side == TradeType.SELL:
                                        # Close LONG position with SELL market order
                                        order_id = connector.sell(
                                            trading_pair,
                                            close_amount,
                                            OrderType.MARKET,
                                            position_action=PositionAction.CLOSE
                                        )
                                        logging.info(f"🛑 Submitted SELL market order to close LONG position: {order_id}")
                                    else:
                                        # Close SHORT position with BUY market order
                                        order_id = connector.buy(
                                            trading_pair,
                                            close_amount,
                                            OrderType.MARKET,
                                            position_action=PositionAction.CLOSE
                                        )
                                        logging.info(f"🛑 Submitted BUY market order to close SHORT position: {order_id}")

                                    cleanup_results["positions_closed"] += 1
                                    logging.info(f"🛑 Position closing order submitted for {trading_pair}: {order_id}")

                                except Exception as order_error:
                                    error_msg = f"Failed to submit position closing order for {trading_pair}: {order_error}"
                                    logging.error(f"🛑 {error_msg}")
                                    cleanup_results["cleanup_errors"].append(error_msg)

                                # Note: Position close failed, will show in cleanup errors above

                            except Exception as e:
                                error_msg = f"Failed to close position {trading_pair}: {e}"
                                logging.error(f"🛑 {error_msg}")
                                cleanup_results["cleanup_errors"].append(error_msg)

                except Exception as e:
                    error_msg = f"Failed to access positions for cleanup: {e}"
                    logging.error(f"🛑 {error_msg}")
                    cleanup_results["cleanup_errors"].append(error_msg)

            # Step 3: Cancel orders if requested
            if cancel_orders and strategy_instance and hasattr(self.hive_core, 'real_connector'):
                try:
                    connector = self.hive_core.real_connector

                    # Cancel all active orders for trading pairs used by this strategy
                    if hasattr(strategy_instance, 'trading_pairs'):
                        for trading_pair in strategy_instance.trading_pairs:
                            try:
                                # Get active orders for this trading pair
                                active_orders = connector.get_open_orders().get(trading_pair, [])

                                for order in active_orders:
                                    try:
                                        connector.cancel(trading_pair, order.client_order_id)
                                        cleanup_results["orders_cancelled"] += 1
                                        logging.info(f"🛑 Cancelled order: {order.client_order_id}")
                                    except Exception as e:
                                        error_msg = f"Failed to cancel order {order.client_order_id}: {e}"
                                        logging.error(f"🛑 {error_msg}")
                                        cleanup_results["cleanup_errors"].append(error_msg)

                            except Exception as e:
                                error_msg = f"Failed to cancel orders for {trading_pair}: {e}"
                                logging.error(f"🛑 {error_msg}")
                                cleanup_results["cleanup_errors"].append(error_msg)

                except Exception as e:
                    error_msg = f"Failed to access orders for cleanup: {e}"
                    logging.error(f"🛑 {error_msg}")
                    cleanup_results["cleanup_errors"].append(error_msg)

            # Step 4: Remove strategy from Hive
            success = await self.hive_core.remove_strategy_dynamically(name)

            # Also consider success if we performed cleanup operations (positions closed, orders cancelled)
            cleanup_performed = cleanup_results["positions_closed"] > 0 or cleanup_results["orders_cancelled"] > 0
            logging.warning(f"🛑 CLEANUP RESULTS: positions_closed={cleanup_results['positions_closed']}, orders_cancelled={cleanup_results['orders_cancelled']}, cleanup_performed={cleanup_performed}")

            if success or cleanup_performed:
                # Step 5: Clean up positions from database
                if hasattr(self.hive_core, 'position_tracker') and self.hive_core.position_tracker:
                    try:
                        # Force cleanup of closed positions in database
                        await self.hive_core.position_tracker.cleanup_zero_size_positions()
                        await self.hive_core.position_tracker.cleanup_closed_positions()
                        logging.info("🧹 Cleaned up closed positions from database after strategy deletion")
                    except Exception as cleanup_error:
                        logging.warning(f"⚠️ Could not clean up positions from database: {cleanup_error}")

                if success:
                    message = f"Strategy {name} removed"
                    log_message = f"🛑 Strategy {name} successfully removed with cleanup: {cleanup_results}"
                else:
                    message = f"Strategy {name} cleanup completed (strategy was not actively running)"
                    log_message = f"🛑 Strategy {name} cleanup completed: {cleanup_results}"

                response_data = {
                    "success": True,
                    "message": message,
                    "cleanup": cleanup_results
                }
                logging.info(log_message)
                return web.json_response(response_data)
            else:
                return web.json_response({"success": False, "message": "Strategy not found"}, status=404)

        except Exception as e:
            logging.error(f"🛑 Error deleting strategy {name}: {e}")
            return web.json_response({"success": False, "message": str(e)}, status=400)

    async def api_sync_from_postgres(self, request):
        """API endpoint: Sync strategy from PostgreSQL to SQLite and add to Hive."""
        if not self.hive_core:
            return web.json_response({"error": "Hive core not available"}, status=500)

        try:
            data = await request.json()
            strategy_name = data.get('strategy_name')

            if not strategy_name:
                return web.json_response(
                    {"success": False, "message": "strategy_name is required"},
                    status=400
                )

            # Call the hive core to sync from PostgreSQL
            success = await self.hive_core.sync_strategy_from_postgres(strategy_name)

            if success:
                return web.json_response({
                    "success": True,
                    "message": f"Strategy {strategy_name} synced from PostgreSQL and added to Hive",
                    "flow": "PostgreSQL → SQLite → Hive Orchestrator"
                })
            else:
                return web.json_response({
                    "success": False,
                    "message": f"Failed to sync strategy {strategy_name} from PostgreSQL"
                }, status=500)

        except Exception as e:
            logging.error(f"Error in sync_from_postgres: {e}")
            return web.json_response({"success": False, "message": str(e)}, status=400)

    async def api_hive_status(self, request):
        """API endpoint: Get Hive status."""
        if not self.hive_core:
            return web.json_response({"error": "Hive core not available"}, status=500)

        current_time = time.time()
        uptime = current_time - self.hive_core.start_time if self.hive_core.start_time else 0

        # Convert market data to JSON-serializable format
        market_data = getattr(self.hive_core, 'shared_market_data', {})
        json_safe_market_data = {}

        try:
            for key, value in market_data.items():
                if hasattr(value, '__dict__'):
                    # Skip complex objects that aren't JSON serializable
                    continue
                elif isinstance(value, (int, float, str, bool, type(None))):
                    json_safe_market_data[key] = value
                else:
                    # Convert Decimal and other numeric types to float
                    try:
                        json_safe_market_data[key] = float(value)
                    except (ValueError, TypeError):
                        json_safe_market_data[key] = str(value)
        except Exception as e:
            logging.warning(f"Error processing market data for JSON: {e}")
            json_safe_market_data = {}

        return web.json_response({
            "hive_running": bool(self.hive_core._hive_running),
            "total_strategies": int(len(self.hive_core.strategies)),
            "total_cycles": int(self.hive_core.total_cycles),
            "total_actions": int(self.hive_core.total_actions),
            "uptime_seconds": float(uptime),
            "actions_per_minute": float((self.hive_core.total_actions / max(uptime / 60, 0.1)) if uptime > 0 else 0),
            "last_market_data": json_safe_market_data,
            "connector_ready": bool(self.hive_core.real_connector is not None),
            "trading_enabled": bool(self.hive_core.real_connector and hasattr(self.hive_core.real_connector, 'hyperliquid_perpetual_secret_key') and bool(getattr(self.hive_core.real_connector, 'hyperliquid_perpetual_secret_key', '')))
        })

    async def api_get_positions(self, request):
        """API endpoint: Get current positions."""
        if not self.hive_core:
            return web.json_response({"error": "Hive core not available"}, status=500)

        try:
            positions = []

            # Get positions from connector if available
            if hasattr(self.hive_core, 'real_connector') and self.hive_core.real_connector:
                connector = self.hive_core.real_connector

                # Check for account positions
                if hasattr(connector, 'account_positions') and connector.account_positions:
                    for trading_pair, position in connector.account_positions.items():
                        # Identify which strategy is responsible for this position
                        strategy_name = 'Unknown_Strategy'
                        if hasattr(self.hive_core, 'position_tracker') and self.hive_core.position_tracker:
                            try:
                                strategy_name = self.hive_core.position_tracker._identify_strategy_for_position(
                                    trading_pair, str(position.position_side), float(position.amount)
                                )
                            except Exception as e:
                                logging.debug(f"Could not identify strategy for {trading_pair}: {e}")

                        positions.append({
                            "trading_pair": trading_pair,
                            "position_side": str(position.position_side),
                            "amount": str(position.amount),
                            "entry_price": str(position.entry_price),
                            "mark_price": str(getattr(position, 'mark_price', 0)),
                            "unrealized_pnl": str(position.unrealized_pnl),
                            "leverage": str(position.leverage),
                            "position_value": str(getattr(position, 'position_value', 0)),
                            "strategy": strategy_name  # Add strategy identification
                        })

                # Also try position tracker if available
                if hasattr(self.hive_core, 'position_tracker') and self.hive_core.position_tracker:
                    try:
                        # Trigger immediate position sync
                        direct_positions = await self.hive_core.position_tracker.get_hyperliquid_positions_direct(connector)
                        if direct_positions:
                            logging.info(f"📊 Found {len(direct_positions)} positions from direct API")
                            for pos in direct_positions:
                                # Add strategy identification to direct positions too
                                if 'strategy' not in pos or not pos['strategy']:
                                    try:
                                        pos['strategy'] = self.hive_core.position_tracker._identify_strategy_for_position(
                                            pos.get('trading_pair', ''),
                                            pos.get('position_side', ''),
                                            float(pos.get('amount', 0))
                                        )
                                    except Exception as e:
                                        logging.debug(f"Could not identify strategy for direct position: {e}")
                                        pos['strategy'] = 'Unknown_Strategy'
                                positions.append(pos)
                    except Exception as e:
                        logging.warning(f"Failed to get direct positions: {e}")

            return web.json_response({
                "positions": positions,
                "total_count": len(positions),
                "connector_status": "connected" if (hasattr(self.hive_core, 'real_connector') and self.hive_core.real_connector) else "disconnected",
                "timestamp": time.time()
            })

        except Exception as e:
            logging.error(f"Error getting positions: {e}")
            return web.json_response({"success": False, "message": str(e)}, status=500)

    async def api_force_position_sync(self, request):
        """API endpoint: Force sync positions to PostgreSQL with correct strategy name."""
        if not self.hive_core:
            return web.json_response({"error": "Hive core not available"}, status=500)

        try:
            # Get current positions from connector
            positions = []
            if hasattr(self.hive_core, 'real_connector') and self.hive_core.real_connector:
                connector = self.hive_core.real_connector
                if hasattr(connector, 'account_positions') and connector.account_positions:
                    for trading_pair, position in connector.account_positions.items():
                        positions.append({
                            "trading_pair": trading_pair,
                            "position_side": str(position.position_side),
                            "amount": str(position.amount),
                            "entry_price": str(position.entry_price),
                            "unrealized_pnl": str(position.unrealized_pnl),
                            "leverage": str(position.leverage)
                        })

            # Get active strategy name
            active_strategy_name = None
            for name, info in self.hive_core.strategies.items():
                if info.is_running:
                    active_strategy_name = name
                    break

            if not active_strategy_name:
                return web.json_response({
                    "success": False,
                    "message": "No active strategy found"
                }, status=400)

            # Force sync to PostgreSQL if available
            if hasattr(self.hive_core, 'postgres_sync_enabled') and self.hive_core.postgres_sync_enabled:
                from hive_postgres_sync import get_postgres_sync
                postgres_sync = get_postgres_sync()

                if postgres_sync and postgres_sync.connection:
                    # First, clean up old position data for inactive strategies
                    try:
                        cursor = postgres_sync.connection.cursor()

                        # Delete positions from old strategies using correct column names
                        delete_old_query = """
                            DELETE FROM position_snapshots
                            WHERE connector_name = 'hyperliquid_perpetual'
                            AND account_name != %s
                        """
                        cursor.execute(delete_old_query, (active_strategy_name,))
                        deleted_rows = cursor.rowcount
                        logging.info(f"🧹 Cleaned up {deleted_rows} old position records")

                        cursor.close()
                        postgres_sync.connection.commit()
                    except Exception as e:
                        logging.error(f"Failed to cleanup old positions: {e}")

                    # Update/insert position data with correct strategy name
                    for pos in positions:
                        try:
                            query = """
                                INSERT INTO position_snapshots (
                                    account_name, connector_name, trading_pair, side, exchange_size,
                                    entry_price, unrealized_pnl, leverage, timestamp,
                                    mark_price, percentage_pnl, initial_margin, maintenance_margin,
                                    cumulative_funding_fees, fee_currency, calculated_size,
                                    calculated_entry_price, size_difference, exchange_position_id, is_reconciled
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, to_timestamp(%s), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """

                            params = (
                                active_strategy_name,  # account_name
                                'hyperliquid_perpetual',  # connector_name
                                pos['trading_pair'],  # trading_pair
                                pos['position_side'].replace('PositionSide.', ''),  # side
                                float(pos['amount']),  # exchange_size
                                float(pos['entry_price']),  # entry_price
                                float(pos['unrealized_pnl']),  # unrealized_pnl
                                float(pos['leverage']),  # leverage
                                int(time.time()),  # timestamp
                                0.0,  # mark_price
                                0.0,  # percentage_pnl
                                0.0,  # initial_margin
                                0.0,  # maintenance_margin
                                0.0,  # cumulative_funding_fees
                                'USD',  # fee_currency
                                float(pos['amount']),  # calculated_size
                                float(pos['entry_price']),  # calculated_entry_price
                                0.0,  # size_difference
                                '',  # exchange_position_id
                                True  # is_reconciled
                            )

                            cursor = postgres_sync.connection.cursor()
                            cursor.execute(query, params)
                            postgres_sync.connection.commit()
                            cursor.close()

                            logging.info(f"🔄 Force synced position to PostgreSQL: {pos['trading_pair']} for strategy {active_strategy_name}")

                        except Exception as e:
                            logging.error(f"Failed to sync position {pos['trading_pair']}: {e}")

            return web.json_response({
                "success": True,
                "message": f"Force synced {len(positions)} positions for strategy {active_strategy_name}",
                "positions": positions,
                "strategy_name": active_strategy_name
            })

        except Exception as e:
            logging.error(f"Error in force position sync: {e}")
            return web.json_response({"success": False, "message": str(e)}, status=500)

    async def api_debug_positions(self, request):
        """API endpoint: Debug positions in PostgreSQL database."""
        if not self.hive_core:
            return web.json_response({"error": "Hive core not available"}, status=500)

        try:
            debug_info = {
                "postgres_enabled": hasattr(self.hive_core, 'postgres_sync_enabled') and self.hive_core.postgres_sync_enabled,
                "position_snapshots_data": []
            }

            if hasattr(self.hive_core, 'postgres_sync_enabled') and self.hive_core.postgres_sync_enabled:
                from hive_postgres_sync import get_postgres_sync
                postgres_sync = get_postgres_sync()

                if postgres_sync and postgres_sync.connection:
                    cursor = postgres_sync.connection.cursor()

                    # Check total record count
                    cursor.execute("SELECT COUNT(*) FROM position_snapshots")
                    total_count = cursor.fetchone()[0]
                    debug_info["total_records"] = total_count

                    # Get recent position records
                    cursor.execute("""
                        SELECT account_name, connector_name, trading_pair, side, exchange_size,
                               entry_price, unrealized_pnl, leverage, timestamp
                        FROM position_snapshots
                        ORDER BY timestamp DESC
                        LIMIT 5
                    """)

                    records = cursor.fetchall()
                    debug_info["recent_positions"] = []

                    for record in records:
                        debug_info["recent_positions"].append({
                            "account_name": record[0],
                            "connector_name": record[1],
                            "trading_pair": record[2],
                            "side": record[3],
                            "exchange_size": float(record[4]) if record[4] else 0,
                            "entry_price": float(record[5]) if record[5] else 0,
                            "unrealized_pnl": float(record[6]) if record[6] else 0,
                            "leverage": float(record[7]) if record[7] else 0,
                            "timestamp": str(record[8])
                        })

                    cursor.close()

            return web.json_response(debug_info)

        except Exception as e:
            logging.error(f"Error in debug positions: {e}")
            return web.json_response({"success": False, "message": str(e)}, status=500)

    async def api_force_close_positions(self, request):
        """API endpoint: Force close all positions regardless of strategy state."""
        from decimal import Decimal
        logging.warning(f"🛑 FORCE CLOSE POSITIONS CALLED: {request.url}")
        if not self.hive_core:
            return web.json_response({"error": "Hive core not available"}, status=500)

        try:
            # Parse body to get optional strategy name filter
            body = await request.json() if request.content_type == 'application/json' else {}
            strategy_filter = body.get('strategy_name', None)

            logging.warning(f"🛑 FORCE CLOSE: strategy_filter={strategy_filter}")

            cleanup_results = {
                "positions_closed": 0,
                "orders_cancelled": 0,
                "cleanup_errors": []
            }

            # Force close positions using ULTRA FALLBACK logic
            if hasattr(self.hive_core, 'real_connector'):
                try:
                    connector = self.hive_core.real_connector
                    positions_to_close = []

                    # Get ALL positions from database regardless of strategy
                    logging.warning(f"🛑 FORCE CLOSE: Getting ALL positions from database...")

                    if hasattr(self.hive_core, 'postgres_sync_enabled') and self.hive_core.postgres_sync_enabled:
                        try:
                            from hive_postgres_sync import get_postgres_sync
                            postgres_sync = get_postgres_sync()

                            if postgres_sync and postgres_sync.connection:
                                query = """
                                SELECT trading_pair, side, exchange_size, timestamp
                                FROM position_snapshots
                                WHERE timestamp > NOW() - INTERVAL '7 days'
                                AND exchange_size != 0
                                AND exchange_size IS NOT NULL
                                ORDER BY timestamp DESC
                                """
                                cursor = postgres_sync.connection.cursor()
                                cursor.execute(query)
                                all_db_positions = cursor.fetchall()
                                cursor.close()

                                logging.warning(f"🛑 FORCE CLOSE: Found {len(all_db_positions)} total positions in database")

                                # Convert ALL database positions to closeable positions
                                for trading_pair, side, exchange_size, timestamp in all_db_positions:
                                    positions_to_close.append({
                                        'trading_pair': trading_pair,
                                        'side': side,
                                        'amount': float(exchange_size)
                                    })
                                    logging.warning(f"🛑 FORCE CLOSE: Adding position to close: {trading_pair} {side} {exchange_size}")

                        except Exception as e:
                            error_msg = f"Failed to query database positions: {e}"
                            logging.error(f"🛑 FORCE CLOSE: {error_msg}")
                            cleanup_results["cleanup_errors"].append(error_msg)

                    # Close positions by creating market orders in opposite direction
                    for position_item in positions_to_close:
                        try:
                            # Extract position data from dict format
                            trading_pair = position_item['trading_pair']
                            side = position_item['side']
                            amount = position_item['amount']

                            # DYNAMIC: Ensure connector supports this trading pair
                            logging.warning(f"🛑 FORCE CLOSE: Ensuring connector supports {trading_pair} for position closing...")
                            pair_supported = await self.hive_core.ensure_trading_pair_support(trading_pair)
                            if not pair_supported:
                                error_msg = f"Could not initialize {trading_pair} support in connector"
                                logging.error(f"🛑 FORCE CLOSE: {error_msg}")
                                cleanup_results["cleanup_errors"].append(error_msg)
                                continue

                            # Create market order to close position (for derivatives)
                            from decimal import Decimal
                            from hummingbot.core.data_type.common import OrderType, PositionAction, TradeType

                            # Determine opposite side to close position
                            if side.upper() == 'LONG' or side.upper() == 'BUY' or amount > 0:
                                close_side = TradeType.SELL  # Close LONG with SELL
                            else:
                                close_side = TradeType.BUY   # Close SHORT with BUY
                            close_amount = abs(Decimal(str(amount)))

                            # Submit market order to close position with proper position action
                            logging.warning(f"🛑 FORCE CLOSE: Closing position: {trading_pair} {close_side} {close_amount}")

                            # Use Hummingbot's position_action parameter to properly close derivatives
                            order_id = await connector.sell(
                                trading_pair,
                                close_amount,
                                OrderType.MARKET,
                                position_action=PositionAction.CLOSE
                            ) if close_side == TradeType.SELL else await connector.buy(
                                trading_pair,
                                close_amount,
                                OrderType.MARKET,
                                position_action=PositionAction.CLOSE
                            )

                            logging.warning(f"🛑 FORCE CLOSE: Submitted market order to close position: {order_id}")

                            cleanup_results["positions_closed"] += 1
                            logging.warning(f"🛑 FORCE CLOSE: Position closing order submitted for {trading_pair}: {order_id}")

                        except Exception as order_error:
                            error_msg = f"Failed to submit position closing order for {trading_pair}: {order_error}"
                            logging.error(f"🛑 FORCE CLOSE: {error_msg}")
                            cleanup_results["cleanup_errors"].append(error_msg)

                except Exception as e:
                    error_msg = f"Failed to force close positions: {e}"
                    logging.error(f"🛑 FORCE CLOSE: {error_msg}")
                    cleanup_results["cleanup_errors"].append(error_msg)
            else:
                error_msg = "No connector available for position closing"
                logging.error(f"🛑 FORCE CLOSE: {error_msg}")
                cleanup_results["cleanup_errors"].append(error_msg)

            # Return results
            response_data = {
                "success": True,
                "message": f"Force closed {cleanup_results['positions_closed']} positions",
                "cleanup": cleanup_results
            }
            logging.warning(f"🛑 FORCE CLOSE COMPLETE: {cleanup_results}")
            return web.json_response(response_data)

        except Exception as e:
            logging.error(f"🛑 Error in force close positions: {e}")
            return web.json_response({"success": False, "message": str(e)}, status=500)
