#!/usr/bin/env python3

"""
Hive API Strategies - Strategy management endpoints.
"""

import logging
import time
from typing import Dict, List

from aiohttp import web

from hive_api_helpers import (
    get_strategy_trading_pairs,
    get_positions_from_database,
    close_positions_with_orders
)
from hive_database import DynamicStrategyConfig


class HiveAPIStrategies:
    """Strategy management API endpoints."""

    def __init__(self, hive_core=None):
        self.hive_core = hive_core

    async def api_list_strategies(self, request):
        """API endpoint: List all active strategies."""
        if not self.hive_core:
            return web.json_response({"error": "Hive core not available"}, status=500)

        try:
            strategies = []
            if hasattr(self.hive_core, 'strategy_instances') and self.hive_core.strategy_instances:
                for name, instance in self.hive_core.strategy_instances.items():
                    if instance and hasattr(instance, 'strategy'):
                        strategy_info = {
                            "name": name,
                            "type": instance.strategy.__class__.__name__,
                            "status": "running" if instance.strategy.is_running else "stopped",
                            "trading_pairs": getattr(instance.strategy, 'trading_pairs', []),
                            "created_at": getattr(instance, 'created_at', None),
                        }

                        # Add performance metrics if available
                        if hasattr(instance, 'performance_metrics'):
                            strategy_info["performance"] = instance.performance_metrics

                        strategies.append(strategy_info)

            return web.json_response({
                "strategies": strategies,
                "total_count": len(strategies),
                "timestamp": str(int(time.time()))
            })

        except Exception as e:
            logging.error(f"Error listing strategies: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def api_create_strategy(self, request):
        """API endpoint: Create a new strategy."""
        if not self.hive_core:
            return web.json_response({"error": "Hive core not available"}, status=500)

        try:
            data = await request.json()
            config = DynamicStrategyConfig(**data)

            # Validate configuration
            if not config.name:
                return web.json_response(
                    {"error": "Missing required field: name"},
                    status=400
                )

            # Create strategy instance
            success = await self.hive_core.create_strategy_instance(config)

            if success:
                return web.json_response({
                    "success": True,
                    "message": f"Strategy '{config.name}' created successfully",
                    "strategy_name": config.name
                })
            else:
                return web.json_response(
                    {"error": f"Failed to create strategy '{config.name}'"},
                    status=500
                )

        except Exception as e:
            logging.error(f"Error creating strategy: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def api_update_strategy(self, request):
        """API endpoint: Update an existing strategy."""
        if not self.hive_core:
            return web.json_response({"error": "Hive core not available"}, status=500)

        try:
            name = request.match_info['name']
            data = await request.json()

            # Update strategy configuration
            success = await self.hive_core.update_strategy_instance(name, data)

            if success:
                return web.json_response({
                    "success": True,
                    "message": f"Strategy '{name}' updated successfully"
                })
            else:
                return web.json_response(
                    {"error": f"Strategy '{name}' not found or update failed"},
                    status=404
                )

        except Exception as e:
            logging.error(f"Error updating strategy: {e}")
            return web.json_response({"error": str(e)}, status=500)

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
            close_positions = request.query.get('close_positions', 'true').lower() == 'true'
            cancel_orders = request.query.get('cancel_orders', 'true').lower() == 'true'

            logging.warning(f"🛑 DELETE STRATEGY: {name}, close_positions={close_positions}, cancel_orders={cancel_orders}")

            cleanup_results = {
                "positions_closed": 0,
                "orders_cancelled": 0,
                "cleanup_errors": []
            }

            # STEP 1: Stop the strategy
            strategy_instance = self.hive_core.strategy_instances.get(name)
            if strategy_instance:
                logging.warning(f"🛑 STEP 1: Stopping strategy {name}")
                success = await self.hive_core.remove_strategy_instance(name)
                if not success:
                    cleanup_results["cleanup_errors"].append(f"Failed to stop strategy {name}")
            else:
                logging.warning(f"🛑 Strategy {name} not found in active instances - may be inactive")

            # STEP 2: Close positions if requested
            if close_positions:
                logging.warning(f"🛑 STEP 2: Closing positions for strategy {name}")

                # Get positions for this strategy
                positions_to_close = await get_positions_from_database(
                    strategy_name=name,
                    hive_core=self.hive_core
                )

                if positions_to_close:
                    logging.warning(f"🛑 Found {len(positions_to_close)} positions to close for {name}")
                    position_cleanup = await close_positions_with_orders(positions_to_close, self.hive_core)
                    cleanup_results["positions_closed"] = position_cleanup["positions_closed"]
                    cleanup_results["cleanup_errors"].extend(position_cleanup["cleanup_errors"])
                else:
                    logging.warning(f"🛑 No positions found for strategy {name}")

            # STEP 3: Cancel orders if requested
            if cancel_orders and hasattr(self.hive_core, 'real_connector') and self.hive_core.real_connector:
                logging.warning(f"🛑 STEP 3: Cancelling orders for strategy {name}")
                try:
                    connector = self.hive_core.real_connector
                    # Get all open orders and cancel those belonging to this strategy
                    open_orders = connector.get_open_orders()
                    strategy_orders = [order for order in open_orders if hasattr(order, 'client_order_id') and name in order.client_order_id]

                    for order in strategy_orders:
                        try:
                            await connector.cancel_order(order.client_order_id)
                            cleanup_results["orders_cancelled"] += 1
                        except Exception as e:
                            cleanup_results["cleanup_errors"].append(f"Failed to cancel order {order.client_order_id}: {e}")

                except Exception as e:
                    cleanup_results["cleanup_errors"].append(f"Failed to cancel orders: {e}")

            # Return success response
            return web.json_response({
                "success": True,
                "message": f"Strategy '{name}' deleted successfully",
                "actions": {
                    "strategy_stopped": True,
                    "positions_closed": close_positions,
                    "orders_cancelled": cancel_orders
                },
                "cleanup": cleanup_results,
                "timestamp": str(int(time.time()))
            })

        except Exception as e:
            logging.error(f"Error deleting strategy: {e}")
            return web.json_response({"error": str(e)}, status=500)