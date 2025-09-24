#!/usr/bin/env python3

"""
Hive Risk Management Module - Portfolio monitoring and risk control for the 1:N architecture.
Provides comprehensive risk management across all strategies and connectors in the Hive system.
"""

import logging
import time
from dataclasses import asdict, dataclass
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

# Import our components
from hive_database import UniversalStrategyConfig

# Hummingbot imports
from hummingbot.connector.connector_base import ConnectorBase
from hummingbot.core.data_type.common import OrderType, TradeType
from hummingbot.core.data_type.order_candidate import OrderCandidate


class RiskLevel(Enum):
    """Risk severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PortfolioMetrics:
    """Portfolio-wide metrics and balances."""

    # Total portfolio values
    total_value_usd: Decimal = Decimal("0")
    total_base_value: Decimal = Decimal("0")
    total_quote_value: Decimal = Decimal("0")

    # Per-asset balances
    asset_balances: Dict[str, Decimal] = None
    asset_values_usd: Dict[str, Decimal] = None

    # Performance metrics
    unrealized_pnl_usd: Decimal = Decimal("0")
    realized_pnl_24h: Decimal = Decimal("0")
    total_fees_24h: Decimal = Decimal("0")

    # Risk metrics
    max_drawdown_pct: Decimal = Decimal("0")
    sharpe_ratio: Decimal = Decimal("0")
    win_rate_pct: Decimal = Decimal("0")

    # Exposure metrics
    net_exposure_pct: Decimal = Decimal("0")  # Long - Short positions
    gross_exposure_pct: Decimal = Decimal("0")  # |Long| + |Short| positions

    def __post_init__(self):
        if self.asset_balances is None:
            self.asset_balances = {}
        if self.asset_values_usd is None:
            self.asset_values_usd = {}


@dataclass
class RiskAlert:
    """Risk alert/warning."""

    level: RiskLevel
    category: str  # "balance", "exposure", "drawdown", "volatility", etc.
    message: str
    current_value: Any
    threshold: Any
    strategy_name: Optional[str] = None
    connector_name: Optional[str] = None
    timestamp: float = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


@dataclass
class RiskLimits:
    """Configurable risk limits for the portfolio."""

    # Balance limits
    min_base_balance: Decimal = Decimal("0.001")
    min_quote_balance: Decimal = Decimal("10.0")
    max_position_size_pct: Decimal = Decimal("20.0")  # % of portfolio

    # Exposure limits
    max_net_exposure_pct: Decimal = Decimal("80.0")
    max_gross_exposure_pct: Decimal = Decimal("200.0")

    # Drawdown limits
    max_drawdown_pct: Decimal = Decimal("10.0")
    daily_loss_limit_pct: Decimal = Decimal("5.0")

    # Order limits
    max_order_size_pct: Decimal = Decimal("10.0")  # % of portfolio per order
    max_orders_per_strategy: int = 20
    max_orders_total: int = 100

    # Strategy limits
    max_strategies_per_connector: int = 10
    max_total_strategies: int = 50


class HiveRiskManager:
    """Comprehensive risk management for the Hive 1:N architecture."""

    def __init__(self, risk_limits: Optional[RiskLimits] = None):
        self.risk_limits = risk_limits or RiskLimits()
        self.portfolio_metrics = PortfolioMetrics()
        self.active_alerts: List[RiskAlert] = []
        self.alert_history: List[RiskAlert] = []

        # Risk monitoring state
        self.last_update_time = 0.0
        self.update_interval = 1.0  # seconds

        # Performance tracking
        self.daily_pnl_history: List[Tuple[float, Decimal]] = []  # (timestamp, pnl)
        self.max_portfolio_value = Decimal("0")

        logging.info("🛡️ Hive Risk Manager initialized")

    def update_portfolio_metrics(
        self,
        connectors: Dict[str, ConnectorBase],
        strategies: Dict[str, Any] = None
    ) -> bool:
        """Update portfolio metrics from all connectors and strategies."""
        try:
            current_time = time.time()

            # Skip if updated too recently
            if current_time - self.last_update_time < self.update_interval:
                return True

            # Reset metrics
            self.portfolio_metrics = PortfolioMetrics()

            # Aggregate balances from all connectors
            for connector_name, connector in connectors.items():
                self._update_connector_metrics(connector_name, connector)

            # Update performance metrics
            self._update_performance_metrics()

            # Check risk limits
            self._check_risk_limits(connectors, strategies)

            self.last_update_time = current_time
            return True

        except Exception as e:
            logging.error(f"❌ Failed to update portfolio metrics: {e}")
            return False

    def _update_connector_metrics(self, connector_name: str, connector: ConnectorBase):
        """Update metrics for a specific connector."""
        try:
            # Get all balances
            all_balances = connector.get_all_balances()

            for asset, balance in all_balances.items():
                if balance > 0:
                    self.portfolio_metrics.asset_balances[asset] = \
                        self.portfolio_metrics.asset_balances.get(asset, Decimal("0")) + balance

                    # Estimate USD value (simplified - would need price feeds in production)
                    usd_value = self._estimate_usd_value(asset, balance, connector)
                    self.portfolio_metrics.asset_values_usd[asset] = \
                        self.portfolio_metrics.asset_values_usd.get(asset, Decimal("0")) + usd_value

                    self.portfolio_metrics.total_value_usd += usd_value

            # Get active orders for exposure calculation
            active_orders = connector.get_active_orders()
            for order in active_orders:
                self._update_exposure_from_order(order)

        except Exception as e:
            logging.warning(f"⚠️ Failed to update metrics for {connector_name}: {e}")

    def _estimate_usd_value(self, asset: str, balance: Decimal, connector: ConnectorBase) -> Decimal:
        """Estimate USD value of an asset (simplified implementation)."""
        try:
            # For major stablecoins, assume 1:1 with USD
            if asset.upper() in ["USDT", "USDC", "BUSD", "DAI", "USD"]:
                return balance

            # For other assets, try to get price from order book
            # This is simplified - production would use dedicated price feeds
            possible_pairs = [f"{asset}-USDT", f"{asset}-USDC", f"{asset}-USD"]

            for trading_pair in possible_pairs:
                if trading_pair in connector.trading_pairs:
                    try:
                        order_book = connector.get_order_book(trading_pair)
                        if order_book and order_book.best_bid_price:
                            return balance * order_book.best_bid_price
                    except:
                        continue

            # Default fallback (would be more sophisticated in production)
            if asset.upper() == "BTC":
                return balance * Decimal("45000")  # Rough BTC price
            elif asset.upper() == "ETH":
                return balance * Decimal("2500")   # Rough ETH price

            return Decimal("0")  # Unknown asset

        except Exception:
            return Decimal("0")

    def _update_exposure_from_order(self, order):
        """Update exposure metrics from active orders."""
        try:
            order_value = order.amount * order.price

            if order.trade_type == TradeType.BUY:
                # Long exposure
                self.portfolio_metrics.net_exposure_pct += \
                    self._calculate_position_pct(order_value)
            else:
                # Short exposure
                self.portfolio_metrics.net_exposure_pct -= \
                    self._calculate_position_pct(order_value)

            # Gross exposure (absolute values)
            self.portfolio_metrics.gross_exposure_pct += \
                self._calculate_position_pct(order_value)

        except Exception as e:
            logging.warning(f"⚠️ Failed to update exposure from order: {e}")

    def _calculate_position_pct(self, order_value: Decimal) -> Decimal:
        """Calculate position as percentage of total portfolio."""
        if self.portfolio_metrics.total_value_usd > 0:
            return (order_value / self.portfolio_metrics.total_value_usd) * Decimal("100")
        return Decimal("0")

    def _update_performance_metrics(self):
        """Update performance and drawdown metrics."""
        try:
            current_value = self.portfolio_metrics.total_value_usd

            # Update max portfolio value
            if current_value > self.max_portfolio_value:
                self.max_portfolio_value = current_value

            # Calculate drawdown
            if self.max_portfolio_value > 0:
                drawdown = (self.max_portfolio_value - current_value) / self.max_portfolio_value * Decimal("100")
                self.portfolio_metrics.max_drawdown_pct = max(
                    self.portfolio_metrics.max_drawdown_pct,
                    drawdown
                )

            # Store daily PnL point
            current_time = time.time()
            self.daily_pnl_history.append((current_time, current_value))

            # Clean old history (keep last 24 hours)
            cutoff_time = current_time - 86400  # 24 hours
            self.daily_pnl_history = [
                (t, pnl) for t, pnl in self.daily_pnl_history
                if t > cutoff_time
            ]

        except Exception as e:
            logging.warning(f"⚠️ Failed to update performance metrics: {e}")

    def _check_risk_limits(
        self,
        connectors: Dict[str, ConnectorBase],
        strategies: Dict[str, Any] = None
    ):
        """Check all risk limits and generate alerts."""
        try:
            # Clear old alerts
            self.active_alerts = []

            # Check balance limits
            self._check_balance_limits()

            # Check exposure limits
            self._check_exposure_limits()

            # Check drawdown limits
            self._check_drawdown_limits()

            # Check order limits
            self._check_order_limits(connectors)

            # Check strategy limits
            if strategies:
                self._check_strategy_limits(strategies)

            # Archive alerts
            self.alert_history.extend(self.active_alerts)

            # Log critical alerts
            critical_alerts = [alert for alert in self.active_alerts if alert.level == RiskLevel.CRITICAL]
            if critical_alerts:
                logging.error(f"🚨 {len(critical_alerts)} CRITICAL risk alerts!")
                for alert in critical_alerts:
                    logging.error(f"   {alert.message}")

        except Exception as e:
            logging.error(f"❌ Failed to check risk limits: {e}")

    def _check_balance_limits(self):
        """Check minimum balance requirements."""
        # Check for major quote currencies
        quote_assets = ["USD", "USDT", "USDC", "BUSD"]
        total_quote_balance = Decimal("0")

        for asset in quote_assets:
            balance = self.portfolio_metrics.asset_balances.get(asset, Decimal("0"))
            total_quote_balance += balance

        if total_quote_balance < self.risk_limits.min_quote_balance:
            self.active_alerts.append(RiskAlert(
                level=RiskLevel.HIGH,
                category="balance",
                message=f"Low quote balance: ${total_quote_balance:.2f} < ${self.risk_limits.min_quote_balance:.2f}",
                current_value=total_quote_balance,
                threshold=self.risk_limits.min_quote_balance
            ))

    def _check_exposure_limits(self):
        """Check position exposure limits."""
        # Net exposure check
        abs_net_exposure = abs(self.portfolio_metrics.net_exposure_pct)
        if abs_net_exposure > self.risk_limits.max_net_exposure_pct:
            self.active_alerts.append(RiskAlert(
                level=RiskLevel.HIGH,
                category="exposure",
                message=f"High net exposure: {abs_net_exposure:.1f}% > {self.risk_limits.max_net_exposure_pct:.1f}%",
                current_value=abs_net_exposure,
                threshold=self.risk_limits.max_net_exposure_pct
            ))

        # Gross exposure check
        if self.portfolio_metrics.gross_exposure_pct > self.risk_limits.max_gross_exposure_pct:
            self.active_alerts.append(RiskAlert(
                level=RiskLevel.MEDIUM,
                category="exposure",
                message=f"High gross exposure: {self.portfolio_metrics.gross_exposure_pct:.1f}% > {self.risk_limits.max_gross_exposure_pct:.1f}%",
                current_value=self.portfolio_metrics.gross_exposure_pct,
                threshold=self.risk_limits.max_gross_exposure_pct
            ))

    def _check_drawdown_limits(self):
        """Check drawdown limits."""
        if self.portfolio_metrics.max_drawdown_pct > self.risk_limits.max_drawdown_pct:
            self.active_alerts.append(RiskAlert(
                level=RiskLevel.CRITICAL,
                category="drawdown",
                message=f"Max drawdown exceeded: {self.portfolio_metrics.max_drawdown_pct:.2f}% > {self.risk_limits.max_drawdown_pct:.2f}%",
                current_value=self.portfolio_metrics.max_drawdown_pct,
                threshold=self.risk_limits.max_drawdown_pct
            ))

    def _check_order_limits(self, connectors: Dict[str, ConnectorBase]):
        """Check order count limits."""
        total_orders = 0

        for connector_name, connector in connectors.items():
            try:
                active_orders = connector.get_active_orders()
                order_count = len(active_orders)
                total_orders += order_count

                # Check per-connector order size limits
                for order in active_orders:
                    order_value = order.amount * order.price
                    order_pct = self._calculate_position_pct(order_value)

                    if order_pct > self.risk_limits.max_order_size_pct:
                        self.active_alerts.append(RiskAlert(
                            level=RiskLevel.HIGH,
                            category="order_size",
                            message=f"Large order on {connector_name}: {order_pct:.1f}% > {self.risk_limits.max_order_size_pct:.1f}%",
                            current_value=order_pct,
                            threshold=self.risk_limits.max_order_size_pct,
                            connector_name=connector_name
                        ))

            except Exception as e:
                logging.warning(f"⚠️ Failed to check orders for {connector_name}: {e}")

        # Check total order limit
        if total_orders > self.risk_limits.max_orders_total:
            self.active_alerts.append(RiskAlert(
                level=RiskLevel.MEDIUM,
                category="order_count",
                message=f"Too many total orders: {total_orders} > {self.risk_limits.max_orders_total}",
                current_value=total_orders,
                threshold=self.risk_limits.max_orders_total
            ))

    def _check_strategy_limits(self, strategies: Dict[str, Any]):
        """Check strategy count limits."""
        total_strategies = len(strategies)

        if total_strategies > self.risk_limits.max_total_strategies:
            self.active_alerts.append(RiskAlert(
                level=RiskLevel.MEDIUM,
                category="strategy_count",
                message=f"Too many strategies: {total_strategies} > {self.risk_limits.max_total_strategies}",
                current_value=total_strategies,
                threshold=self.risk_limits.max_total_strategies
            ))

    def should_block_order(self, order_candidate: OrderCandidate, strategy_name: str) -> Tuple[bool, str]:
        """Check if an order should be blocked due to risk limits."""
        try:
            # Calculate order value and percentage
            order_value = order_candidate.amount * order_candidate.price
            order_pct = self._calculate_position_pct(order_value)

            # Check order size limit
            if order_pct > self.risk_limits.max_order_size_pct:
                return True, f"Order size {order_pct:.1f}% exceeds limit {self.risk_limits.max_order_size_pct:.1f}%"

            # Check balance availability (simplified)
            required_balance = order_candidate.amount if order_candidate.order_type == OrderType.MARKET else order_value
            # Would need more sophisticated balance checking in production

            # Check if this would exceed exposure limits
            projected_exposure = abs(self.portfolio_metrics.net_exposure_pct)
            if order_candidate.trade_type == TradeType.BUY:
                projected_exposure += order_pct
            else:
                projected_exposure += order_pct  # Gross exposure

            if projected_exposure > self.risk_limits.max_gross_exposure_pct:
                return True, f"Order would exceed exposure limit: {projected_exposure:.1f}% > {self.risk_limits.max_gross_exposure_pct:.1f}%"

            return False, ""

        except Exception as e:
            logging.error(f"❌ Error checking order risk for {strategy_name}: {e}")
            return True, f"Risk check error: {str(e)}"

    def get_risk_summary(self) -> Dict[str, Any]:
        """Get comprehensive risk summary."""
        try:
            return {
                "portfolio_metrics": asdict(self.portfolio_metrics),
                "risk_limits": asdict(self.risk_limits),
                "active_alerts": [asdict(alert) for alert in self.active_alerts],
                "alert_counts": {
                    "critical": len([a for a in self.active_alerts if a.level == RiskLevel.CRITICAL]),
                    "high": len([a for a in self.active_alerts if a.level == RiskLevel.HIGH]),
                    "medium": len([a for a in self.active_alerts if a.level == RiskLevel.MEDIUM]),
                    "low": len([a for a in self.active_alerts if a.level == RiskLevel.LOW]),
                },
                "last_update": self.last_update_time,
                "portfolio_health": self._calculate_portfolio_health(),
            }
        except Exception as e:
            logging.error(f"❌ Failed to generate risk summary: {e}")
            return {"error": str(e)}

    def _calculate_portfolio_health(self) -> str:
        """Calculate overall portfolio health score."""
        critical_count = len([a for a in self.active_alerts if a.level == RiskLevel.CRITICAL])
        high_count = len([a for a in self.active_alerts if a.level == RiskLevel.HIGH])
        medium_count = len([a for a in self.active_alerts if a.level == RiskLevel.MEDIUM])

        if critical_count > 0:
            return "CRITICAL"
        elif high_count > 2:
            return "HIGH_RISK"
        elif high_count > 0 or medium_count > 3:
            return "MODERATE_RISK"
        elif medium_count > 0:
            return "LOW_RISK"
        else:
            return "HEALTHY"

    def update_risk_limits(self, new_limits: RiskLimits) -> bool:
        """Update risk limits configuration."""
        try:
            self.risk_limits = new_limits
            logging.info("✅ Risk limits updated")
            return True
        except Exception as e:
            logging.error(f"❌ Failed to update risk limits: {e}")
            return False


# Export main classes
__all__ = [
    "RiskLevel",
    "PortfolioMetrics",
    "RiskAlert",
    "RiskLimits",
    "HiveRiskManager"
]
