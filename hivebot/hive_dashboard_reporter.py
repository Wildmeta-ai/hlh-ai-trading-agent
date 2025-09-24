#!/usr/bin/env python3

"""
Hive Dashboard Reporter - Reports bot status to the web dashboard database.
"""

import asyncio
import logging
import os
import socket
from datetime import datetime
from typing import Optional

import psycopg2
from psycopg2.extras import RealDictCursor


class HiveDashboardReporter:
    """
    Reports Hive bot instances to the PostgreSQL database for web dashboard visibility.
    """

    def __init__(self,
                 host: str = "15.235.212.36",
                 port: int = 5432,
                 database: str = "hummingbot_api",
                 user: str = "hbot",
                 password: str = "hummingbot-api"):
        """Initialize dashboard reporter with database connection."""
        self.db_config = {
            'host': host,
            'port': port,
            'database': database,
            'user': user,
            'password': password
        }
        self.bot_run_id: Optional[int] = None
        # Removed redundant instance_name - this was causing duplicate registrations

        logging.info(f"🔗 HiveDashboardReporter initialized")

    def _get_connection(self):
        """Create database connection."""
        try:
            return psycopg2.connect(**self.db_config)
        except Exception as e:
            logging.error(f"❌ Failed to connect to PostgreSQL: {e}")
            return None

    async def register_bot_startup(self,
                                   bot_name: str = "hive-orchestrator",
                                   strategy_type: str = "multi_strategy",
                                   strategy_name: str = "hive_dynamic",
                                   account_name: str = "default",
                                   config_name: str = "hive_config") -> bool:
        """
        Register bot startup in the bot_runs table.

        Returns:
            bool: True if registration successful, False otherwise
        """
        conn = None
        try:
            conn = self._get_connection()
            if not conn:
                return False

            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Insert new bot run record
                insert_query = """
                    INSERT INTO bot_runs (
                        bot_name,
                        instance_name,
                        strategy_type,
                        strategy_name,
                        config_name,
                        deployment_status,
                        run_status,
                        account_name,
                        image_version
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id;
                """

                values = (
                    bot_name,
                    bot_name,  # Use bot_name for instance_name too - eliminates redundancy
                    strategy_type,
                    strategy_name,
                    config_name,
                    'running',  # deployment_status
                    'running',  # run_status
                    account_name,
                    'hive-v1.0'  # image_version
                )

                cursor.execute(insert_query, values)
                result = cursor.fetchone()
                self.bot_run_id = result['id']

                conn.commit()

                logging.info(f"✅ Bot registered in dashboard: ID={self.bot_run_id}, Instance={bot_name}")
                return True

        except Exception as e:
            logging.error(f"❌ Failed to register bot startup: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()

    async def update_bot_status(self,
                                run_status: str = 'running',
                                deployment_status: str = 'running',
                                error_message: Optional[str] = None) -> bool:
        """
        Update bot status in the database.

        Args:
            run_status: Current run status (running, stopped, error)
            deployment_status: Deployment status (running, stopped, error)
            error_message: Error message if status is error
        """
        if not self.bot_run_id:
            logging.warning("⚠️ No bot run ID available for status update")
            return False

        conn = None
        try:
            conn = self._get_connection()
            if not conn:
                return False

            with conn.cursor() as cursor:
                update_query = """
                    UPDATE bot_runs
                    SET run_status = %s,
                        deployment_status = %s,
                        error_message = %s,
                        stopped_at = CASE WHEN %s IN ('stopped', 'error') THEN NOW() ELSE NULL END
                    WHERE id = %s;
                """

                cursor.execute(update_query, (run_status, deployment_status, error_message, run_status, self.bot_run_id))
                conn.commit()

                logging.debug(f"📊 Bot status updated: run_status={run_status}, deployment_status={deployment_status}")
                return True

        except Exception as e:
            logging.error(f"❌ Failed to update bot status: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()

    async def register_bot_shutdown(self, final_status: str = "stopped") -> bool:
        """
        Register bot shutdown in the database.

        Args:
            final_status: Final status message
        """
        if not self.bot_run_id:
            logging.warning("⚠️ No bot run ID available for shutdown")
            return False

        conn = None
        try:
            conn = self._get_connection()
            if not conn:
                return False

            with conn.cursor() as cursor:
                update_query = """
                    UPDATE bot_runs
                    SET run_status = 'stopped',
                        deployment_status = 'stopped',
                        stopped_at = NOW(),
                        final_status = %s
                    WHERE id = %s;
                """

                cursor.execute(update_query, (final_status, self.bot_run_id))
                conn.commit()

                logging.info(f"🛑 Bot shutdown registered: ID={self.bot_run_id}, Status={final_status}")
                return True

        except Exception as e:
            logging.error(f"❌ Failed to register bot shutdown: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()

    async def update_strategy_count(self, active_strategies: int) -> bool:
        """
        Update the number of active strategies (stored in deployment_config as JSON).

        Args:
            active_strategies: Number of currently active strategies
        """
        if not self.bot_run_id:
            return False

        conn = None
        try:
            conn = self._get_connection()
            if not conn:
                return False

            with conn.cursor() as cursor:
                # Store strategy count in deployment_config as simple JSON
                config_json = f'{{"active_strategies": {active_strategies}, "last_updated": "{datetime.now().isoformat()}"}}'

                update_query = """
                    UPDATE bot_runs
                    SET deployment_config = %s
                    WHERE id = %s;
                """

                cursor.execute(update_query, (config_json, self.bot_run_id))
                conn.commit()

                logging.debug(f"📈 Strategy count updated: {active_strategies} active strategies")
                return True

        except Exception as e:
            logging.error(f"❌ Failed to update strategy count: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()

    async def heartbeat(self) -> bool:
        """
        Send heartbeat to keep the bot record alive and update last activity.
        """
        if not self.bot_run_id:
            return False

        # For now, just update the deployment_config with a timestamp
        # In a more advanced setup, you might have a separate heartbeat table
        return await self.update_strategy_count(len(getattr(self, '_strategies', {})))
