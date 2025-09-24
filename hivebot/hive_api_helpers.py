#!/usr/bin/env python3

"""
Hive API Helpers - Shared utilities for position and strategy management.
"""

import logging
from decimal import Decimal
from typing import List, Dict, Optional, Tuple

from hummingbot.core.data_type.common import OrderType, PositionAction, TradeType


async def get_strategy_trading_pairs(strategy_name: str, hive_core) -> List[str]:
    """Get trading pairs for a strategy from database."""
    strategy_trading_pairs = []

    try:
        if hasattr(hive_core, 'postgres_sync_enabled') and hive_core.postgres_sync_enabled:
            from hive_postgres_sync import get_postgres_sync
            postgres_sync = get_postgres_sync()

            if postgres_sync and postgres_sync.connection:
                cursor = postgres_sync.connection.cursor()
                cursor.execute("SELECT trading_pairs FROM hive_strategy_configs WHERE name = %s", (strategy_name,))
                result = cursor.fetchone()
                cursor.close()

                if result:
                    import json
                    strategy_trading_pairs = json.loads(result[0]) if isinstance(result[0], str) else result[0]
                    logging.warning(f"🎯 Found trading pairs for strategy {strategy_name}: {strategy_trading_pairs}")
    except Exception as e:
        logging.error(f"❌ Failed to get trading pairs from database: {e}")

    return strategy_trading_pairs


async def get_positions_from_database(strategy_name: str = None, time_window: str = '7 days', hive_core=None) -> List[Dict]:
    """Get positions from database with optional strategy filtering."""
    positions = []

    try:
        if not (hasattr(hive_core, 'postgres_sync_enabled') and hive_core.postgres_sync_enabled):
            return positions

        from hive_postgres_sync import get_postgres_sync
        postgres_sync = get_postgres_sync()

        if not (postgres_sync and postgres_sync.connection):
            return positions

        if strategy_name:
            # Get specific strategy trading pairs
            strategy_trading_pairs = await get_strategy_trading_pairs(strategy_name, hive_core)
            if not strategy_trading_pairs:
                return positions

            # Query positions for strategy trading pairs
            trading_pairs_str = "','".join(strategy_trading_pairs)
            query = f"""
            SELECT DISTINCT trading_pair, side, exchange_size, timestamp
            FROM position_snapshots
            WHERE trading_pair IN ('{trading_pairs_str}')
            AND timestamp > NOW() - INTERVAL '{time_window}'
            AND exchange_size != 0
            AND exchange_size IS NOT NULL
            ORDER BY timestamp DESC
            """
        else:
            # Get all positions
            query = f"""
            SELECT trading_pair, side, exchange_size, timestamp
            FROM position_snapshots
            WHERE timestamp > NOW() - INTERVAL '{time_window}'
            AND exchange_size != 0
            AND exchange_size IS NOT NULL
            ORDER BY timestamp DESC
            """

        cursor = postgres_sync.connection.cursor()
        cursor.execute(query)
        db_positions = cursor.fetchall()
        cursor.close()

        # Convert to standard format
        for row in db_positions:
            if len(row) == 4:
                trading_pair, side, exchange_size, timestamp = row
            else:
                trading_pair, side, exchange_size = row
                timestamp = None

            positions.append({
                'trading_pair': trading_pair,
                'side': side,
                'amount': float(exchange_size),
                'timestamp': timestamp
            })

        logging.info(f"🔍 Found {len(positions)} positions in database")

    except Exception as e:
        logging.error(f"Failed to query database positions: {e}")

    return positions


async def close_positions_with_orders(positions: List[Dict], hive_core) -> Dict:
    """Close positions by creating market orders."""
    from decimal import Decimal

    cleanup_results = {
        "positions_closed": 0,
        "orders_cancelled": 0,
        "cleanup_errors": []
    }

    if not hasattr(hive_core, 'real_connector') or not hive_core.real_connector:
        error_msg = "No connector available for position closing"
        logging.error(f"🛑 {error_msg}")
        cleanup_results["cleanup_errors"].append(error_msg)
        return cleanup_results

    connector = hive_core.real_connector

    for position_data in positions:
        try:
            trading_pair = position_data['trading_pair']
            side = position_data['side']
            amount = position_data['amount']

            # Ensure connector supports this trading pair
            logging.warning(f"🛑 Ensuring connector supports {trading_pair} for position closing...")
            pair_supported = await hive_core.ensure_trading_pair_support(trading_pair)
            if not pair_supported:
                error_msg = f"Could not initialize {trading_pair} support in connector"
                logging.error(f"🛑 {error_msg}")
                cleanup_results["cleanup_errors"].append(error_msg)
                continue

            # Determine opposite side to close position
            if side.upper() == 'LONG' or side.upper() == 'BUY' or amount > 0:
                close_side = TradeType.SELL  # Close LONG with SELL
            else:
                close_side = TradeType.BUY   # Close SHORT with BUY
            close_amount = abs(Decimal(str(amount)))

            # Submit market order to close position
            logging.warning(f"🛑 Closing position: {trading_pair} {close_side} {close_amount}")

            if close_side == TradeType.SELL:
                order_id = await connector.sell(
                    trading_pair,
                    close_amount,
                    OrderType.MARKET,
                    position_action=PositionAction.CLOSE
                )
            else:
                order_id = await connector.buy(
                    trading_pair,
                    close_amount,
                    OrderType.MARKET,
                    position_action=PositionAction.CLOSE
                )

            cleanup_results["positions_closed"] += 1
            logging.warning(f"🛑 Position closing order submitted for {trading_pair}: {order_id}")

        except Exception as e:
            error_msg = f"Failed to close position {position_data.get('trading_pair', 'unknown')}: {e}"
            logging.error(f"🛑 {error_msg}")
            cleanup_results["cleanup_errors"].append(error_msg)

    return cleanup_results


async def ensure_trading_pair_support(trading_pair: str, hive_core) -> bool:
    """Ensure connector supports the trading pair."""
    try:
        return await hive_core.ensure_trading_pair_support(trading_pair)
    except Exception as e:
        logging.error(f"Failed to ensure trading pair support for {trading_pair}: {e}")
        return False


def identify_strategy_for_position(trading_pair: str, side: str, amount: float, hive_core) -> str:
    """Try to identify which strategy owns a position."""
    try:
        if hasattr(hive_core, 'position_tracker') and hive_core.position_tracker:
            return hive_core.position_tracker._identify_strategy_for_position(trading_pair, side, amount)
    except Exception as e:
        logging.debug(f"Could not identify strategy for position: {e}")
    return "Unknown"


def should_close_position_for_strategy(trading_pair: str, strategy_name: str) -> bool:
    """Check if a position should be closed for a given strategy."""
    # Check if strategy name contains the asset symbol
    asset_symbol = trading_pair.split('-')[0]  # BTC from BTC-USD
    return asset_symbol.upper() in strategy_name.upper()