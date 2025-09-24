#!/usr/bin/env python3

"""
Hive API Status - System monitoring and health check endpoints.
"""

import logging
import time

from aiohttp import web


class HiveAPIStatus:
    """System status and monitoring API endpoints."""

    def __init__(self, hive_core=None):
        self.hive_core = hive_core

    async def api_hive_status(self, request):
        """API endpoint: Get comprehensive Hive system status."""
        if not self.hive_core:
            return web.json_response({"error": "Hive core not available"}, status=500)

        try:
            status_data = {
                "timestamp": str(int(time.time())),
                "system": {
                    "hive_core_available": True,
                    "connector_available": bool(hasattr(self.hive_core, 'real_connector') and self.hive_core.real_connector),
                    "postgres_enabled": bool(hasattr(self.hive_core, 'postgres_sync_enabled') and self.hive_core.postgres_sync_enabled),
                },
                "strategies": {
                    "active_count": 0,
                    "running_count": 0,
                    "total_instances": 0
                },
                "connector": {
                    "status": "unknown",
                    "balance": "unknown",
                    "positions_count": 0
                },
                "database": {
                    "connected": False,
                    "last_sync": "unknown"
                }
            }

            # Check strategy status
            if hasattr(self.hive_core, 'strategy_instances') and self.hive_core.strategy_instances:
                status_data["strategies"]["total_instances"] = len(self.hive_core.strategy_instances)

                running_count = 0
                for name, instance in self.hive_core.strategy_instances.items():
                    if instance and hasattr(instance, 'strategy'):
                        status_data["strategies"]["active_count"] += 1
                        if instance.strategy.is_running:
                            running_count += 1

                status_data["strategies"]["running_count"] = running_count

            # Check connector status
            if status_data["system"]["connector_available"]:
                try:
                    connector = self.hive_core.real_connector
                    status_data["connector"]["status"] = "connected"

                    # Get balance if available
                    try:
                        balances = connector.get_all_balances()
                        if balances:
                            total_usd = sum(float(balance.get('total', 0)) for balance in balances.values())
                            status_data["connector"]["balance"] = f"${total_usd:.2f}"
                    except:
                        status_data["connector"]["balance"] = "unavailable"

                    # Get positions count
                    try:
                        positions = connector.account_positions
                        status_data["connector"]["positions_count"] = len(positions) if positions else 0
                    except:
                        status_data["connector"]["positions_count"] = 0

                except Exception as e:
                    status_data["connector"]["status"] = f"error: {e}"

            # Check database status
            if status_data["system"]["postgres_enabled"]:
                try:
                    from hive_postgres_sync import get_postgres_sync
                    postgres_sync = get_postgres_sync()

                    if postgres_sync and postgres_sync.connection:
                        status_data["database"]["connected"] = True

                        # Check last sync time
                        cursor = postgres_sync.connection.cursor()
                        cursor.execute("SELECT MAX(timestamp) FROM position_snapshots")
                        last_sync = cursor.fetchone()[0]
                        if last_sync:
                            status_data["database"]["last_sync"] = str(last_sync)
                        cursor.close()

                except Exception as e:
                    status_data["database"]["error"] = str(e)

            return web.json_response(status_data)

        except Exception as e:
            logging.error(f"Error getting hive status: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def api_sync_from_postgres(self, request):
        """API endpoint: Sync strategy configurations from PostgreSQL."""
        if not self.hive_core:
            return web.json_response({"error": "Hive core not available"}, status=500)

        try:
            sync_results = {
                "success": False,
                "strategies_loaded": 0,
                "strategies_created": 0,
                "errors": []
            }

            # Check if postgres sync is enabled
            if not (hasattr(self.hive_core, 'postgres_sync_enabled') and self.hive_core.postgres_sync_enabled):
                sync_results["errors"].append("PostgreSQL sync not enabled")
                return web.json_response(sync_results)

            # Load strategy configurations from database
            try:
                from hive_postgres_sync import get_postgres_sync
                postgres_sync = get_postgres_sync()

                if not (postgres_sync and postgres_sync.connection):
                    sync_results["errors"].append("No PostgreSQL connection available")
                    return web.json_response(sync_results)

                cursor = postgres_sync.connection.cursor()
                cursor.execute("""
                    SELECT name, strategy_type, parameters, trading_pairs,
                           enabled, created_at, updated_at
                    FROM hive_strategy_configs
                    WHERE enabled = true
                """)

                configs = cursor.fetchall()
                cursor.close()

                sync_results["strategies_loaded"] = len(configs)

                # Create strategy instances from configurations
                for config_row in configs:
                    try:
                        name, strategy_type, parameters, trading_pairs, enabled, created_at, updated_at = config_row

                        # Convert to DynamicStrategyConfig
                        from hive_database import DynamicStrategyConfig
                        import json

                        config = DynamicStrategyConfig(
                            name=name,
                            strategy_type=strategy_type,
                            parameters=json.loads(parameters) if isinstance(parameters, str) else parameters,
                            trading_pairs=json.loads(trading_pairs) if isinstance(trading_pairs, str) else trading_pairs,
                            enabled=enabled
                        )

                        # Check if strategy already exists
                        if name not in self.hive_core.strategy_instances:
                            success = await self.hive_core.create_strategy_instance(config)
                            if success:
                                sync_results["strategies_created"] += 1
                            else:
                                sync_results["errors"].append(f"Failed to create strategy: {name}")

                    except Exception as e:
                        sync_results["errors"].append(f"Failed to process config {name}: {e}")

                sync_results["success"] = sync_results["strategies_created"] > 0 or len(configs) == 0

            except Exception as e:
                sync_results["errors"].append(f"Database query failed: {e}")

            return web.json_response(sync_results)

        except Exception as e:
            logging.error(f"Error syncing from postgres: {e}")
            return web.json_response({"error": str(e)}, status=500)