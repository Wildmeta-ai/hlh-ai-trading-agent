#!/usr/bin/env python3
"""
PostgreSQL synchronization module for Hive Orchestrator
Syncs strategy data from local SQLite to remote PostgreSQL for dashboard consumption
"""

import json
import logging
import os
import socket
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import psycopg2
from psycopg2.extras import RealDictCursor


@dataclass
class PostgreSQLConfig:
    host: str = "15.235.212.36"
    port: int = 5432
    database: str = "hummingbot_api"
    user: str = "hbot"
    password: str = "hummingbot-api"


class HivePostgreSQLSync:
    """Handles synchronization between local SQLite and remote PostgreSQL"""

    def __init__(self, config: Optional[PostgreSQLConfig] = None, hive_id: Optional[str] = None):
        self.config = config or PostgreSQLConfig()
        self.connection = None
        self.hive_id = hive_id or self._generate_hive_id()
        self.last_sync_time = 0
        self.sync_interval = 30  # Sync every 30 seconds

    def _generate_hive_id(self) -> str:
        """Generate unique hive ID - should match orchestrator format"""
        # Try to get from environment first (set by spawned instances)
        if os.environ.get('HIVE_BOT_ID'):
            return os.environ.get('HIVE_BOT_ID')

        # Fallback to old behavior for backwards compatibility
        hostname = socket.gethostname()
        api_port = os.environ.get('HIVE_API_PORT', '8080')
        return f"hive-{hostname}-{api_port}"

    def connect(self) -> bool:
        """Establish connection to PostgreSQL"""
        try:
            self.connection = psycopg2.connect(
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.user,
                password=self.config.password,
                cursor_factory=RealDictCursor
            )
            logging.info(f"✅ Connected to PostgreSQL: {self.config.host}:{self.config.port}")
            return True
        except Exception as e:
            logging.error(f"❌ PostgreSQL connection failed: {e}")
            self.connection = None
            return False

    def disconnect(self):
        """Close PostgreSQL connection"""
        if self.connection:
            self.connection.close()
            self.connection = None

    async def execute_query(self, query: str, params: tuple = None):
        """Execute a query with parameters"""
        if not self.connection:
            raise Exception("Not connected to PostgreSQL")

        try:
            cursor = self.connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            self.connection.commit()
            cursor.close()
        except Exception as e:
            if self.connection:
                self.connection.rollback()
            raise e

    def create_missing_tables(self):
        """Create tables that don't exist yet"""
        if not self.connection:
            return False

        try:
            cursor = self.connection.cursor()

            # Create position_snapshots table if it doesn't exist
            create_position_snapshots = """
            CREATE TABLE IF NOT EXISTS position_snapshots (
                id SERIAL PRIMARY KEY,
                account_name VARCHAR(255),
                connector_name VARCHAR(255),
                trading_pair VARCHAR(255),
                timestamp TIMESTAMP WITH TIME ZONE,
                side VARCHAR(10),
                exchange_size DECIMAL(20, 10),
                entry_price DECIMAL(20, 10),
                mark_price DECIMAL(20, 10),
                unrealized_pnl DECIMAL(20, 10),
                percentage_pnl DECIMAL(10, 4),
                leverage DECIMAL(10, 4),
                initial_margin DECIMAL(20, 10),
                maintenance_margin DECIMAL(20, 10),
                cumulative_funding_fees DECIMAL(20, 10),
                fee_currency VARCHAR(10),
                calculated_size DECIMAL(20, 10),
                calculated_entry_price DECIMAL(20, 10),
                size_difference DECIMAL(20, 10),
                exchange_position_id VARCHAR(255),
                is_reconciled VARCHAR(10)
            )
            """

            # Add missing columns to account_states table
            alter_account_states = """
            ALTER TABLE account_states
            ADD COLUMN IF NOT EXISTS asset VARCHAR(20),
            ADD COLUMN IF NOT EXISTS balance DECIMAL(20, 10)
            """

            cursor.execute(create_position_snapshots)
            cursor.execute(alter_account_states)

            self.connection.commit()
            cursor.close()
            logging.info("✅ Created missing database tables")
            return True

        except Exception as e:
            logging.error(f"❌ Failed to create tables: {e}")
            if self.connection:
                self.connection.rollback()
            return False

    def register_hive_instance(self, api_port: int = None) -> bool:
        """Register/update this hive instance in PostgreSQL"""
        if not self.connection:
            return False

        try:
            cursor = self.connection.cursor()

            if api_port is not None:
                # UPSERT hive instance with api_port
                upsert_query = """
                    INSERT INTO hive_instances (hive_id, hostname, api_port, last_seen, status)
                    VALUES (%s, %s, %s, NOW(), 'active')
                    ON CONFLICT (hive_id)
                    DO UPDATE SET
                        last_seen = NOW(),
                        status = 'active',
                        api_port = EXCLUDED.api_port
                """
                cursor.execute(upsert_query, (
                    self.hive_id,
                    socket.gethostname(),
                    api_port
                ))
            else:
                # UPSERT hive instance without updating api_port
                upsert_query = """
                    INSERT INTO hive_instances (hive_id, hostname, last_seen, status)
                    VALUES (%s, %s, NOW(), 'active')
                    ON CONFLICT (hive_id)
                    DO UPDATE SET
                        last_seen = NOW(),
                        status = 'active'
                """
                cursor.execute(upsert_query, (
                    self.hive_id,
                    socket.gethostname()
                ))

            self.connection.commit()
            print(f"✅ Hive instance registered: {self.hive_id}")
            return True

        except Exception as e:
            print(f"❌ Failed to register hive instance: {e}")
            if self.connection:
                self.connection.rollback()
            return False

    def sync_strategy_data(self, strategy_data: Dict[str, Any]) -> bool:
        """Sync strategy data from orchestrator to PostgreSQL"""
        if not self.connection:
            return False

        try:
            cursor = self.connection.cursor()

            # UPSERT strategy data
            upsert_query = """
                INSERT INTO hive_strategies (
                    hive_id, strategy_name, status, total_actions,
                    successful_orders, failed_orders, refresh_interval,
                    performance_per_min, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (hive_id, strategy_name)
                DO UPDATE SET
                    status = EXCLUDED.status,
                    total_actions = EXCLUDED.total_actions,
                    successful_orders = EXCLUDED.successful_orders,
                    failed_orders = EXCLUDED.failed_orders,
                    refresh_interval = EXCLUDED.refresh_interval,
                    performance_per_min = EXCLUDED.performance_per_min,
                    updated_at = NOW()
            """

            cursor.execute(upsert_query, (
                self.hive_id,
                strategy_data['name'],
                strategy_data.get('status', 'active'),
                strategy_data.get('total_actions', 0),
                strategy_data.get('successful_orders', 0),
                strategy_data.get('failed_orders', 0),
                strategy_data.get('refresh_interval', 5.0),
                strategy_data.get('performance_per_min', 0.0)
            ))

            self.connection.commit()
            return True

        except Exception as e:
            print(f"❌ Failed to sync strategy {strategy_data.get('name', 'unknown')}: {e}")
            if self.connection:
                self.connection.rollback()
            return False

    def sync_all_strategies(self, strategies: List[Dict[str, Any]]) -> int:
        """Sync all strategy data in batch"""
        if not self.connection:
            return 0

        synced_count = 0
        for strategy in strategies:
            if self.sync_strategy_data(strategy):
                synced_count += 1

        print(f"📊 Synced {synced_count}/{len(strategies)} strategies to PostgreSQL")
        return synced_count

    def remove_strategy(self, strategy_name: str) -> bool:
        """Remove strategy from PostgreSQL when deleted locally"""
        if not self.connection:
            return False

        try:
            cursor = self.connection.cursor()

            delete_query = """
                DELETE FROM hive_strategies
                WHERE hive_id = %s AND strategy_name = %s
            """

            cursor.execute(delete_query, (self.hive_id, strategy_name))
            self.connection.commit()

            print(f"🗑️ Removed strategy {strategy_name} from PostgreSQL")
            return True

        except Exception as e:
            print(f"❌ Failed to remove strategy {strategy_name}: {e}")
            if self.connection:
                self.connection.rollback()
            return False

    def should_sync(self) -> bool:
        """Check if it's time to sync based on interval"""
        current_time = time.time()
        if current_time - self.last_sync_time >= self.sync_interval:
            self.last_sync_time = current_time
            return True
        return False

    def get_strategy_from_postgres(self, strategy_name: str) -> Optional[Dict[str, Any]]:
        """Get strategy data from PostgreSQL (for debugging/verification)"""
        if not self.connection:
            return None

        try:
            cursor = self.connection.cursor()

            query = """
                SELECT * FROM hive_strategies
                WHERE hive_id = %s AND strategy_name = %s
            """

            cursor.execute(query, (self.hive_id, strategy_name))
            result = cursor.fetchone()

            return dict(result) if result else None

        except Exception as e:
            print(f"❌ Failed to get strategy {strategy_name}: {e}")
            return None

    def cleanup_inactive_strategies(self, active_strategy_names: List[str]) -> int:
        """Remove strategies from PostgreSQL that are no longer active locally"""
        if not self.connection:
            return 0

        try:
            cursor = self.connection.cursor()

            # Get current strategies in PostgreSQL for this hive
            cursor.execute(
                "SELECT strategy_name FROM hive_strategies WHERE hive_id = %s",
                (self.hive_id,)
            )
            pg_strategies = [row['strategy_name'] for row in cursor.fetchall()]

            # Find strategies to remove
            strategies_to_remove = [name for name in pg_strategies if name not in active_strategy_names]

            removed_count = 0
            for strategy_name in strategies_to_remove:
                if self.remove_strategy(strategy_name):
                    removed_count += 1

            if removed_count > 0:
                print(f"🧹 Cleaned up {removed_count} inactive strategies from PostgreSQL")

            return removed_count

        except Exception as e:
            print(f"❌ Failed to cleanup inactive strategies: {e}")
            return 0


# Global sync instance
_postgres_sync: Optional[HivePostgreSQLSync] = None


def get_postgres_sync(hive_id: Optional[str] = None) -> HivePostgreSQLSync:
    """Get global PostgreSQL sync instance"""
    global _postgres_sync
    if _postgres_sync is None:
        _postgres_sync = HivePostgreSQLSync(hive_id=hive_id)
    return _postgres_sync


def initialize_postgres_sync(api_port: int = 8080, hive_id: Optional[str] = None) -> bool:
    """Initialize PostgreSQL sync and register hive instance"""
    sync = get_postgres_sync(hive_id=hive_id)
    if sync.connect():
        # Create missing tables first
        sync.create_missing_tables()
        return sync.register_hive_instance(api_port)
    return False


def sync_strategy_to_postgres(strategy_data: Dict[str, Any]) -> bool:
    """Convenience function to sync single strategy"""
    sync = get_postgres_sync()
    return sync.sync_strategy_data(strategy_data)


def sync_all_strategies_to_postgres(strategies: List[Dict[str, Any]]) -> int:
    """Convenience function to sync all strategies"""
    sync = get_postgres_sync()
    return sync.sync_all_strategies(strategies)


if __name__ == "__main__":
    # Test the PostgreSQL sync
    sync = HivePostgreSQLSync()

    if sync.connect():
        print("✅ PostgreSQL connection successful")

        # Test registration
        if sync.register_hive_instance():
            print("✅ Hive instance registration successful")

        # Test strategy sync
        test_strategy = {
            'name': 'TEST_STRATEGY',
            'status': 'active',
            'total_actions': 100,
            'successful_orders': 80,
            'failed_orders': 20,
            'refresh_interval': 10.0,
            'performance_per_min': 5.5
        }

        if sync.sync_strategy_data(test_strategy):
            print("✅ Strategy sync successful")

        sync.disconnect()
    else:
        print("❌ PostgreSQL sync test failed")
