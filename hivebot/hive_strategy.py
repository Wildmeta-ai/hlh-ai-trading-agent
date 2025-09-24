#!/usr/bin/env python3

"""
Hive Strategy Management Module - Strategy instances and performance tracking.
"""

import logging
import time
from decimal import Decimal
from typing import Any, Dict, List, Optional

# Import the database config class
from hive_database import DynamicStrategyConfig
from hummingbot.connector.derivative.hyperliquid_perpetual.hyperliquid_perpetual_derivative import (
    HyperliquidPerpetualDerivative,
)
from hummingbot.strategy.market_trading_pair_tuple import MarketTradingPairTuple

# Hummingbot imports
from hummingbot.strategy.pure_market_making import PureMarketMakingStrategy


class DynamicStrategyInfo:
    """Information about a dynamically managed strategy."""

    def __init__(self, config: DynamicStrategyConfig):
        self.config = config
        self.name = config.name
        self.is_running = False
        self.start_time: Optional[float] = None
        self.actions_count = 0
        self.last_action_time = 0
        self.total_runtime = 0.0
        self.performance_metrics = {
            "actions_per_minute": 0.0,
            "avg_spread": 0.0,
            "uptime_percentage": 0.0
        }

    def update_config(self, new_config: DynamicStrategyConfig):
        """Update strategy configuration dynamically."""
        old_refresh_time = self.config.order_refresh_time
        self.config = new_config

        # Log significant changes
        if abs(new_config.order_refresh_time - old_refresh_time) > 0.1:
            logging.info(f"Strategy {self.name}: Refresh time changed from {old_refresh_time}s to {new_config.order_refresh_time}s")

    def calculate_performance_metrics(self, current_time: float):
        """Calculate real-time performance metrics."""
        if self.start_time:
            runtime_minutes = (current_time - self.start_time) / 60.0
            self.performance_metrics["actions_per_minute"] = self.actions_count / max(runtime_minutes, 0.1)
            self.performance_metrics["avg_spread"] = (self.config.bid_spread + self.config.ask_spread) / 2
            self.performance_metrics["uptime_percentage"] = min(100.0, runtime_minutes / max(runtime_minutes, 1.0) * 100)

    def to_status_dict(self) -> dict:
        """Convert to status dictionary for API responses."""
        return {
            "name": self.name,
            "config": self.config.__dict__,
            "is_running": self.is_running,
            "actions_count": self.actions_count,
            "performance_metrics": self.performance_metrics,
            "last_action_time": self.last_action_time,
            "start_time": self.start_time
        }


class RealStrategyInstance:
    """Wrapper for real Hummingbot strategy instances - Task 2 Integration."""

    def __init__(self, name: str, config: DynamicStrategyConfig, connector: HyperliquidPerpetualDerivative):
        self.name = name
        self.config = config
        self.connector = connector
        self.strategy: Optional[PureMarketMakingStrategy] = None
        self.is_running = False
        self.start_time = None
        self.actions_count = 0
        self.last_action_time = 0
        self.performance_metrics = {}

        logging.info(f"🤖 Created RealStrategyInstance: {name}")

    def initialize_strategy(self) -> bool:
        """Initialize the real Hummingbot strategy."""
        try:
            logging.info(f"🔧 Initializing real strategy: {self.name}")

            # Create market trading pair tuple
            trading_pair = self.config.market
            maker_assets = trading_pair.split("-")  # e.g. ["BTC", "USD"]

            # Create the market trading pair tuple with real connector
            market_info = MarketTradingPairTuple(
                self.connector,
                trading_pair,
                maker_assets[0],  # base asset
                maker_assets[1]   # quote asset
            )

            # Create the real pure market making strategy
            self.strategy = PureMarketMakingStrategy()

            # Initialize with real parameters - full Hummingbot configuration
            self.strategy.init_params(
                market_info=market_info,
                bid_spread=Decimal(str(self.config.bid_spread)),
                ask_spread=Decimal(str(self.config.ask_spread)),
                order_amount=Decimal(str(self.config.order_amount)),
                order_levels=self.config.order_levels,
                order_refresh_time=self.config.order_refresh_time,
                order_refresh_tolerance_pct=Decimal("0.001"),  # 0.1% tolerance
                filled_order_delay=60.0,  # Wait 60s after fill before new orders
                inventory_skew_enabled=False,
                inventory_target_base_pct=Decimal("50"),  # Keep 50% base asset
                inventory_range_multiplier=Decimal("1"),
                minimum_spread=Decimal(str(self.config.bid_spread * 0.5)),  # Minimum spread protection
                price_ceiling=Decimal("-1"),  # No price ceiling
                price_floor=Decimal("-1"),   # No price floor
                ping_pong_enabled=False,     # Don't use ping pong
                order_optimization_enabled=True,  # Enable optimization
                add_transaction_costs_to_orders=True,  # Include fees in pricing
                logging_options=PureMarketMakingStrategy.OPTION_LOG_ALL
            )

            logging.info(f"✅ Real strategy initialized: {self.name}")
            return True

        except Exception as e:
            logging.error(f"❌ Failed to initialize strategy {self.name}: {e}")
            import traceback
            traceback.print_exc()
            return False

    def start(self, trading_core=None):
        """Start the real strategy and register it with the TradingCore."""
        if not self.strategy:
            logging.error(f"❌ Strategy {self.name} not initialized")
            return False

        try:
            self.is_running = True
            self.start_time = time.time()

            # **COMPLETE INTEGRATION**: Properly register strategy and market with TradingCore
            if trading_core:
                # First, ensure the market is registered with the TradingCore
                if hasattr(trading_core, 'add_markets'):
                    trading_core.add_markets([self.connector])
                    logging.info(f"✅ Added connector {self.connector.__class__.__name__} to TradingCore")

                # **CRITICAL**: Also register the market with TradingCore's _sb_markets list
                if hasattr(trading_core, '_sb_markets'):
                    if self.connector not in trading_core._sb_markets:
                        trading_core._sb_markets.append(self.connector)
                        logging.info(f"✅ Added connector to TradingCore _sb_markets list")

                # Add this strategy to the trading core's strategy list
                if hasattr(trading_core, '_sb_strategies'):
                    if self.strategy not in trading_core._sb_strategies:
                        trading_core._sb_strategies.append(self.strategy)
                        logging.info(f"✅ Added {self.name} to TradingCore strategy list")

                # Add the strategy's markets to the trading core markets list
                if hasattr(trading_core, '_sb_markets') and hasattr(self.strategy, '_sb_markets'):
                    for market in self.strategy._sb_markets:
                        if market not in trading_core._sb_markets:
                            trading_core._sb_markets.append(market)
                            logging.info(f"✅ Added market {market.__class__.__name__} to TradingCore")

                # Check if markets are ready and log detailed status
                if hasattr(self.strategy, 'all_markets_ready'):
                    markets_ready = self.strategy.all_markets_ready()
                    logging.info(f"📊 Markets ready status for {self.name}: {markets_ready}")

                    if hasattr(self.strategy, '_sb_markets'):
                        for market in self.strategy._sb_markets:
                            logging.info(f"🔍 Market {market.__class__.__name__}:")
                            logging.info(f"   📡 Ready: {market.ready}")
                            if hasattr(market, 'trading_pairs'):
                                logging.info(f"   📈 Trading pairs: {list(market.trading_pairs)}")
                            if hasattr(market, 'network_status'):
                                logging.info(f"   🌐 Network status: {market.network_status}")
                            if hasattr(market, '_trading_rules'):
                                pairs_with_rules = list(market._trading_rules.keys()) if market._trading_rules else []
                                logging.info(f"   ⚖️ Trading rules available for: {pairs_with_rules}")
                else:
                    logging.warning(f"⚠️ Strategy {self.name} has no all_markets_ready method")

                # Start the strategy with the trading core's clock (essential for PMM to work)
                if hasattr(trading_core, 'clock') and trading_core.clock:
                    self.strategy.start(trading_core.clock)
                    logging.info(f"✅ Started {self.name} with TradingCore clock")

                    # **ADD EVENT LISTENERS**: Capture actual order creation events from PMM
                    self._setup_order_event_listeners()

                    # **CRITICAL FIX**: Force market readiness for Hyperliquid
                    # Hyperliquid connector is functional even when not "ready" status
                    if hasattr(self.strategy, '_sb_markets'):
                        for market in self.strategy._sb_markets:
                            if hasattr(market, '_ready'):
                                original_ready = market._ready
                                # Force market to be ready if it has order books
                                if hasattr(market, 'order_books') and market.order_books:
                                    market._ready = True
                                    logging.info(f"🔧 Force-enabled market readiness for {market.__class__.__name__} (was {original_ready}, has {len(market.order_books)} order books)")

                    # Re-check market readiness after forcing
                    if hasattr(self.strategy, 'all_markets_ready'):
                        markets_ready_after = self.strategy.all_markets_ready()
                        logging.info(f"📊 Markets ready after force-enable: {markets_ready_after}")

                    # Verify clock is ticking by checking the strategy's tick method
                    if hasattr(self.strategy, 'tick'):
                        logging.info(f"🕐 Strategy {self.name} has tick method - will receive clock updates")
                else:
                    logging.error(f"❌ TradingCore has no clock - PMM strategy will not work properly")

            logging.info(f"🚀 Started real strategy: {self.name}")
            logging.info(f"💰 Will place orders: {self.config.order_amount} {self.config.market}")
            logging.info(f"📏 Spreads: {self.config.bid_spread * 100:.1f}%/{self.config.ask_spread * 100:.1f}%")
            return True
        except Exception as e:
            logging.error(f"❌ Failed to start strategy {self.name}: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _setup_order_event_listeners(self):
        """Setup event listeners to capture PMM order creation events."""
        try:
            logging.info(f"🔧 Setting up order event listeners for {self.name}")

            # Import required event classes
            from hummingbot.core.event.event_listener import EventListener
            from hummingbot.core.event.events import MarketEvent

            # Get the market from the strategy
            if hasattr(self.strategy, '_sb_markets') and self.strategy._sb_markets:
                market = self.strategy._sb_markets[0]  # Primary market
                logging.info(f"🔍 Found market: {market.__class__.__name__} for {self.name}")

                # Create event listeners for order creation
                buy_order_listener = EventListener()
                sell_order_listener = EventListener()
                order_filled_listener = EventListener()
                order_cancelled_listener = EventListener()

                # Set up callback functions
                buy_order_listener.callback = self._on_buy_order_created
                sell_order_listener.callback = self._on_sell_order_created
                order_filled_listener.callback = self._on_order_filled
                order_cancelled_listener.callback = self._on_order_cancelled

                # Add listeners to the market
                market.add_listener(MarketEvent.BuyOrderCreated, buy_order_listener)
                market.add_listener(MarketEvent.SellOrderCreated, sell_order_listener)
                market.add_listener(MarketEvent.OrderFilled, order_filled_listener)
                market.add_listener(MarketEvent.OrderCancelled, order_cancelled_listener)

                logging.info(f"✅ Added order event listeners for {self.name}")
            else:
                logging.warning(f"⚠️ No markets found in strategy {self.name} for event listeners")

        except Exception as e:
            logging.error(f"❌ Failed to setup event listeners for {self.name}: {e}")
            import traceback
            traceback.print_exc()

    def _on_buy_order_created(self, event):
        """Handle buy order creation event."""
        try:
            # Notify orchestrator about the actual order
            if hasattr(self, '_orchestrator_callback') and self._orchestrator_callback:
                self._orchestrator_callback(self.name, "BUY_ORDER", True, {
                    'order_id': event.order_id,
                    'price': float(event.price),
                    'amount': float(event.amount),
                    'trading_pair': event.trading_pair
                })
            logging.info(f"📈 {self.name}: PMM created BUY order {event.order_id} @ {event.price}")
        except Exception as e:
            logging.error(f"❌ Error handling buy order created event: {e}")

    def _on_sell_order_created(self, event):
        """Handle sell order creation event."""
        try:
            # Notify orchestrator about the actual order
            if hasattr(self, '_orchestrator_callback') and self._orchestrator_callback:
                self._orchestrator_callback(self.name, "SELL_ORDER", True, {
                    'order_id': event.order_id,
                    'price': float(event.price),
                    'amount': float(event.amount),
                    'trading_pair': event.trading_pair
                })
            logging.info(f"📉 {self.name}: PMM created SELL order {event.order_id} @ {event.price}")
        except Exception as e:
            logging.error(f"❌ Error handling sell order created event: {e}")

    def _on_order_filled(self, event):
        """Handle order filled event."""
        try:
            if hasattr(self, '_orchestrator_callback') and self._orchestrator_callback:
                self._orchestrator_callback(self.name, "ORDER_FILLED", True, {
                    'order_id': event.order_id,
                    'price': float(event.price),
                    'amount': float(event.amount),
                    'trading_pair': event.trading_pair,
                    'trade_type': event.trade_type.name
                })
            logging.info(f"✅ {self.name}: Order {event.order_id} filled at {event.price}")
        except Exception as e:
            logging.error(f"❌ Error handling order filled event: {e}")

    def _on_order_cancelled(self, event):
        """Handle order cancellation event."""
        try:
            if hasattr(self, '_orchestrator_callback') and self._orchestrator_callback:
                self._orchestrator_callback(self.name, "ORDER_CANCELLED", True, {
                    'order_id': event.order_id,
                    'trading_pair': getattr(event, 'trading_pair', 'N/A')
                })
            logging.info(f"🚫 {self.name}: Order {event.order_id} cancelled")
        except Exception as e:
            logging.error(f"❌ Error handling order cancelled event: {e}")

    def set_orchestrator_callback(self, callback):
        """Set callback function to notify orchestrator of order events."""
        self._orchestrator_callback = callback

    def stop(self):
        """Stop the real strategy."""
        if self.strategy:
            self.is_running = False
            logging.info(f"🛑 Stopped real strategy: {self.name}")

    def get_active_orders(self) -> List[Dict[str, Any]]:
        """Get active orders from the real strategy."""
        if not self.strategy or not self.is_running:
            return []

        try:
            # Get active orders from strategy
            active_orders = self.strategy.active_orders
            order_list = []

            for order in active_orders:
                order_dict = {
                    "order_id": order.client_order_id,
                    "trading_pair": order.trading_pair,
                    "order_type": order.order_type.name,
                    "trade_type": order.trade_type.name,
                    "amount": float(order.amount),
                    "price": float(order.price),
                    "timestamp": order.creation_timestamp
                }
                order_list.append(order_dict)

            return order_list

        except Exception as e:
            logging.error(f"❌ Error getting active orders for {self.name}: {e}")
            return []

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get real performance metrics."""
        current_time = time.time()

        if self.start_time:
            runtime_seconds = current_time - self.start_time
            runtime_minutes = runtime_seconds / 60.0
        else:
            runtime_seconds = 0
            runtime_minutes = 0

        # Get real metrics from strategy if available
        active_orders_count = len(self.get_active_orders())

        return {
            "runtime_seconds": runtime_seconds,
            "runtime_minutes": runtime_minutes,
            "active_orders": active_orders_count,
            "bid_spread": self.config.bid_spread,
            "ask_spread": self.config.ask_spread,
            "order_amount": self.config.order_amount,
            "strategy_ready": self.strategy is not None and self.is_running
        }
