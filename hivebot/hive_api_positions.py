#!/usr/bin/env python3

"""
Hive API Positions - Position management endpoints.
"""

import logging
import time
from decimal import Decimal
from typing import Dict, List

from aiohttp import web

from hive_api_helpers import (
    get_positions_from_database,
    close_positions_with_orders
)


class HiveAPIPositions:
    """Position management API endpoints."""

    def __init__(self, hive_core=None):
        self.hive_core = hive_core

    async def api_get_positions(self, request):
        """API endpoint: Get current positions from live connector and database."""
        if not self.hive_core:
            return web.json_response({"error": "Hive core not available"}, status=500)

        try:
            # Use format expected by portfolio API
            positions_data = {
                "positions": [],  # Use 'positions' key as expected by portfolio API
                "timestamp": int(time.time()),
                "total_positions": 0
            }

            # Try to get positions from live connector first
            if hasattr(self.hive_core, 'real_connector') and self.hive_core.real_connector:
                try:
                    connector = self.hive_core.real_connector
                    connector_positions = connector.account_positions

                    if connector_positions:
                        for trading_pair, position in connector_positions.items():
                            if hasattr(position, 'amount') and position.amount != 0:
                                # Format in portfolio API compatible format
                                amount = float(position.amount)
                                side = 'LONG' if amount > 0 else 'SHORT'

                                positions_data["positions"].append({
                                    "trading_pair": trading_pair,
                                    "amount": amount,
                                    "entry_price": float(getattr(position, 'entry_price', 0)),
                                    "mark_price": float(getattr(position, 'mark_price', 0)),
                                    "unrealized_pnl": float(getattr(position, 'unrealized_pnl', 0)),
                                    "leverage": float(getattr(position, 'leverage', 1)),
                                    # Additional fields for portfolio compatibility
                                    "position_side": side,
                                    "strategy": "BTC_Market_Maker_2025_01_15_025452",  # TODO: Get from strategy registry
                                    "position_size": abs(amount)
                                })
                except Exception as e:
                    logging.warning(f"Could not get connector positions: {e}")

            # Update total count
            positions_data["total_positions"] = len(positions_data["positions"])

            return web.json_response(positions_data)

        except Exception as e:
            logging.error(f"Error in get positions: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def api_force_position_sync(self, request):
        """API endpoint: Force synchronization of positions to database."""
        if not self.hive_core:
            return web.json_response({"error": "Hive core not available"}, status=500)

        try:
            sync_results = {
                "success": False,
                "positions_synced": 0,
                "errors": []
            }

            # Check if postgres sync is enabled
            if not (hasattr(self.hive_core, 'postgres_sync_enabled') and self.hive_core.postgres_sync_enabled):
                sync_results["errors"].append("PostgreSQL sync not enabled")
                return web.json_response(sync_results)

            # Get connector positions
            if not (hasattr(self.hive_core, 'real_connector') and self.hive_core.real_connector):
                sync_results["errors"].append("No connector available")
                return web.json_response(sync_results)

            connector = self.hive_core.real_connector
            positions = connector.account_positions

            if not positions:
                sync_results["success"] = True
                sync_results["positions_synced"] = 0
                return web.json_response(sync_results)

            # Sync to database
            from hive_postgres_sync import get_postgres_sync
            postgres_sync = get_postgres_sync()

            if postgres_sync and postgres_sync.connection:
                # Clear existing positions
                cursor = postgres_sync.connection.cursor()
                cursor.execute("DELETE FROM position_snapshots WHERE timestamp > NOW() - INTERVAL '1 hour'")

                # Insert current positions
                for trading_pair, position in positions.items():
                    if hasattr(position, 'amount') and position.amount != 0:
                        try:
                            side = 'LONG' if float(position.amount) > 0 else 'SHORT'
                            cursor.execute("""
                                INSERT INTO position_snapshots (
                                    trading_pair, side, exchange_size, entry_price,
                                    mark_price, unrealized_pnl, leverage, timestamp, account_name
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), %s)
                            """, (
                                trading_pair,
                                side,
                                float(position.amount),
                                float(getattr(position, 'entry_price', 0)),
                                float(getattr(position, 'mark_price', 0)),
                                float(getattr(position, 'unrealized_pnl', 0)),
                                float(getattr(position, 'leverage', 1)),
                                trading_pair  # Use trading_pair as account_name for now
                            ))
                            sync_results["positions_synced"] += 1
                        except Exception as e:
                            sync_results["errors"].append(f"Failed to sync {trading_pair}: {e}")

                postgres_sync.connection.commit()
                cursor.close()
                sync_results["success"] = True

            return web.json_response(sync_results)

        except Exception as e:
            logging.error(f"Error in force position sync: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def api_debug_positions(self, request):
        """API endpoint: Debug positions data for troubleshooting."""
        if not self.hive_core:
            return web.json_response({"error": "Hive core not available"}, status=500)

        try:
            import time
            debug_data = {
                "timestamp": str(int(time.time())),
                "connector_available": bool(hasattr(self.hive_core, 'real_connector') and self.hive_core.real_connector),
                "postgres_enabled": bool(hasattr(self.hive_core, 'postgres_sync_enabled') and self.hive_core.postgres_sync_enabled),
                "connector_positions_count": 0,
                "position_snapshots_data": []
            }

            # Check connector positions
            if debug_data["connector_available"]:
                connector = self.hive_core.real_connector
                positions = connector.account_positions
                debug_data["connector_positions_count"] = len(positions) if positions else 0

            # Check database
            if debug_data["postgres_enabled"]:
                try:
                    from hive_postgres_sync import get_postgres_sync
                    postgres_sync = get_postgres_sync()

                    if postgres_sync and postgres_sync.connection:
                        cursor = postgres_sync.connection.cursor()
                        cursor.execute("SELECT COUNT(*) FROM position_snapshots")
                        count = cursor.fetchone()[0]
                        debug_data["position_snapshots_count"] = count

                        # Get recent snapshots
                        cursor.execute("""
                            SELECT trading_pair, side, exchange_size, timestamp
                            FROM position_snapshots
                            WHERE timestamp > NOW() - INTERVAL '1 hour'
                            ORDER BY timestamp DESC
                            LIMIT 10
                        """)
                        rows = cursor.fetchall()
                        debug_data["position_snapshots_data"] = [
                            {
                                "trading_pair": row[0],
                                "side": row[1],
                                "size": float(row[2]),
                                "timestamp": str(row[3])
                            } for row in rows
                        ]
                        cursor.close()
                except Exception as e:
                    debug_data["database_error"] = str(e)

            return web.json_response(debug_data)

        except Exception as e:
            logging.error(f"Error in debug positions: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def api_force_close_positions(self, request):
        """API endpoint: Force close all positions regardless of strategy state."""
        from decimal import Decimal

        if not self.hive_core:
            return web.json_response({"error": "Hive core not available"}, status=500)

        try:
            # Parse body to get optional strategy name filter
            body = await request.json() if request.content_type == 'application/json' else {}
            strategy_filter = body.get('strategy_name', None)

            logging.warning(f"🛑 FORCE CLOSE POSITIONS: strategy_filter={strategy_filter}")

            cleanup_results = {
                "positions_closed": 0,
                "orders_cancelled": 0,
                "cleanup_errors": []
            }

            # Get positions from database
            positions_to_close = await get_positions_from_database(
                strategy_name=strategy_filter,
                hive_core=self.hive_core
            )

            if not positions_to_close:
                return web.json_response({
                    "success": True,
                    "message": "No positions found to close",
                    "cleanup": cleanup_results,
                    "timestamp": str(int(time.time()))
                })

            logging.warning(f"🛑 FORCE CLOSE: Found {len(positions_to_close)} positions to close")

            # Close all positions
            cleanup_results = await close_positions_with_orders(positions_to_close, self.hive_core)

            return web.json_response({
                "success": True,
                "message": f"Force closed {cleanup_results['positions_closed']} positions",
                "cleanup": cleanup_results,
                "timestamp": str(int(time.time()))
            })

        except Exception as e:
            logging.error(f"Error in force close positions: {e}")
            return web.json_response({"error": str(e)}, status=500)