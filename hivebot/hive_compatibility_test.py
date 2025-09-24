#!/usr/bin/env python3

"""
Hive Compatibility Test Suite - Comprehensive testing of strategy and connector compatibility.
Validates that Hivebot can successfully instantiate and manage all supported Hummingbot strategies.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Import our universal components
try:
    from hive_connector_factory import ConnectorConfig, ConnectorType, UniversalConnectorFactory
    from hive_database import HiveDynamicDatabase, UniversalStrategyConfig
    from hive_risk_management import HiveRiskManager, RiskLimits
    from hive_strategy_factory import StrategyType, UniversalStrategyFactory, get_all_strategy_types
    from hive_strategy_managers import create_strategy_from_config, strategy_registry
    from hive_v2_integration import get_supported_v2_strategies, is_v2_available, v2_manager

    # Hummingbot imports
    from hummingbot.client.config.config_helpers import ClientConfigAdapter, load_client_config_map_from_file

    IMPORTS_AVAILABLE = True
    logging.info("✅ All Hive components imported successfully")

except ImportError as e:
    IMPORTS_AVAILABLE = False
    logging.error(f"❌ Import error: {e}")
    logging.error("Make sure to activate the hummingbot conda environment first:")
    logging.error("source ~/miniconda3/bin/activate hummingbot")


@dataclass
class CompatibilityTestResult:
    """Results from a compatibility test."""
    component_name: str
    test_type: str  # "strategy", "connector", "v2_strategy", "risk_manager"
    success: bool
    error_message: str = ""
    details: Dict[str, Any] = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}


class HiveCompatibilityTester:
    """Comprehensive compatibility testing suite for Hivebot."""

    def __init__(self):
        if not IMPORTS_AVAILABLE:
            raise RuntimeError("Required imports not available")

        self.client_config_map = load_client_config_map_from_file()
        self.test_results: List[CompatibilityTestResult] = []

        # Test components
        self.strategy_factory = UniversalStrategyFactory()
        self.connector_factory = UniversalConnectorFactory(self.client_config_map)
        self.database = HiveDynamicDatabase(":memory:")  # In-memory for tests
        self.risk_manager = HiveRiskManager()

        logging.info("🧪 Hive Compatibility Tester initialized")

    async def run_full_compatibility_test(self) -> Dict[str, Any]:
        """Run complete compatibility test suite."""
        logging.info("🚀 Starting comprehensive Hivebot compatibility tests...")

        # Clear previous results
        self.test_results = []

        # Test all components
        await self._test_strategy_compatibility()
        await self._test_connector_compatibility()
        await self._test_v2_strategy_compatibility()
        await self._test_database_compatibility()
        await self._test_risk_management_compatibility()

        # Generate summary
        summary = self._generate_test_summary()

        logging.info("✅ Compatibility testing complete!")
        return summary

    async def _test_strategy_compatibility(self):
        """Test all V1 strategy types for compatibility."""
        logging.info("📋 Testing V1 strategy compatibility...")

        # Get all supported strategy types
        try:
            all_strategies = get_all_strategy_types()
            supported_strategies = strategy_registry.get_supported_strategies()

            logging.info(f"📊 Testing {len(supported_strategies)}/{len(all_strategies)} strategy types")

            for strategy_type in supported_strategies:
                await self._test_single_strategy(strategy_type)

        except Exception as e:
            self.test_results.append(CompatibilityTestResult(
                component_name="strategy_system",
                test_type="strategy",
                success=False,
                error_message=f"Failed to test strategies: {e}"
            ))

    async def _test_single_strategy(self, strategy_type: StrategyType):
        """Test a single strategy type."""
        try:
            # Create test configuration
            config = self._create_test_strategy_config(strategy_type)

            # Create test connector (Hyperliquid for simplicity)
            connector_config = ConnectorConfig(
                connector_type=ConnectorType.HYPERLIQUID_PERPETUAL,
                trading_pairs=["BTC-USD"],
                trading_required=False  # Market data only for tests
            )

            test_connector = self.connector_factory.create_connector(connector_config)
            if not test_connector:
                raise Exception("Failed to create test connector")

            connectors = {"test": test_connector}

            # Test strategy creation
            strategy = create_strategy_from_config(config, connectors)

            if strategy:
                self.test_results.append(CompatibilityTestResult(
                    component_name=strategy_type.value,
                    test_type="strategy",
                    success=True,
                    details={
                        "strategy_class": strategy.__class__.__name__,
                        "trading_pairs": config.trading_pairs,
                        "connector_type": connector_config.connector_type.value
                    }
                ))
                logging.info(f"✅ Strategy {strategy_type.value}: PASS")
            else:
                self.test_results.append(CompatibilityTestResult(
                    component_name=strategy_type.value,
                    test_type="strategy",
                    success=False,
                    error_message="Strategy creation returned None"
                ))
                logging.warning(f"❌ Strategy {strategy_type.value}: FAIL - Creation returned None")

        except Exception as e:
            self.test_results.append(CompatibilityTestResult(
                component_name=strategy_type.value,
                test_type="strategy",
                success=False,
                error_message=str(e)
            ))
            logging.warning(f"❌ Strategy {strategy_type.value}: FAIL - {e}")

    def _create_test_strategy_config(self, strategy_type: StrategyType) -> UniversalStrategyConfig:
        """Create a test configuration for a strategy type."""
        # Base configuration
        config = UniversalStrategyConfig(
            name=f"TEST_{strategy_type.value}",
            strategy_type=strategy_type,
            connector_type=ConnectorType.HYPERLIQUID_PERPETUAL,
            trading_pairs=["BTC-USD"],
            bid_spread=0.05,
            ask_spread=0.05,
            order_amount=0.001,
            order_refresh_time=5.0
        )

        # Add strategy-specific parameters
        if strategy_type == StrategyType.AVELLANEDA_MARKET_MAKING:
            config.strategy_params = {
                "risk_factor": 0.5,
                "order_book_depth_factor": 0.1,
                "order_amount_shape_factor": 0.0
            }
        elif strategy_type == StrategyType.CROSS_EXCHANGE_MARKET_MAKING:
            config.min_profitability = 0.003
        elif strategy_type == StrategyType.ARBITRAGE:
            config.min_profitability = 0.005
            config.max_order_size = 1.0
        elif strategy_type == StrategyType.PERPETUAL_MARKET_MAKING:
            config.leverage = 2
            config.position_mode = "ONEWAY"

        return config

    async def _test_connector_compatibility(self):
        """Test Hyperliquid connector compatibility."""
        logging.info("🎯 Testing Hyperliquid connector compatibility...")

        supported_connectors = self.connector_factory.get_supported_connectors()
        logging.info(f"📊 Testing {len(supported_connectors)} connector (Hyperliquid)")

        for connector_type in supported_connectors:
            await self._test_single_connector(connector_type)

    async def _test_single_connector(self, connector_type: ConnectorType):
        """Test a single connector type."""
        try:
            # Create test configuration (market data only)
            config = ConnectorConfig(
                connector_type=connector_type,
                trading_pairs=self.connector_factory.get_default_trading_pairs(connector_type),
                trading_required=False
            )

            # Validate configuration
            if not self.connector_factory.validate_config(config):
                raise Exception("Invalid connector configuration")

            # Create connector (this tests the factory logic without requiring real credentials)
            connector = self.connector_factory.create_connector(config)

            if connector:
                self.test_results.append(CompatibilityTestResult(
                    component_name=connector_type.value,
                    test_type="connector",
                    success=True,
                    details={
                        "connector_class": connector.__class__.__name__,
                        "trading_pairs": config.trading_pairs,
                        "category": self.connector_factory.CONNECTOR_CATEGORIES.get(connector_type, "unknown").value
                    }
                ))
                logging.info(f"✅ Connector {connector_type.value}: PASS")
            else:
                self.test_results.append(CompatibilityTestResult(
                    component_name=connector_type.value,
                    test_type="connector",
                    success=False,
                    error_message="Connector creation returned None"
                ))
                logging.warning(f"❌ Connector {connector_type.value}: FAIL - Creation returned None")

        except Exception as e:
            self.test_results.append(CompatibilityTestResult(
                component_name=connector_type.value,
                test_type="connector",
                success=False,
                error_message=str(e)
            ))
            logging.warning(f"❌ Connector {connector_type.value}: FAIL - {e}")

    async def _test_v2_strategy_compatibility(self):
        """Test Strategy V2 framework compatibility."""
        logging.info("🆕 Testing Strategy V2 compatibility...")

        if not is_v2_available():
            self.test_results.append(CompatibilityTestResult(
                component_name="v2_framework",
                test_type="v2_strategy",
                success=False,
                error_message="Strategy V2 framework not available"
            ))
            logging.warning("⚠️ Strategy V2 framework not available")
            return

        supported_v2_strategies = get_supported_v2_strategies()
        logging.info(f"📊 Testing {len(supported_v2_strategies)} V2 strategy types")

        for strategy_type in supported_v2_strategies:
            await self._test_single_v2_strategy(strategy_type)

    async def _test_single_v2_strategy(self, strategy_type: StrategyType):
        """Test a single V2 strategy type."""
        try:
            # Create test configuration
            config = self._create_test_strategy_config(strategy_type)

            # Add V2-specific parameters
            if strategy_type == StrategyType.DCA:
                config.strategy_params = {
                    "n_levels": 5,
                    "spread_between_levels": 0.01,
                    "time_delay": 60
                }
            elif strategy_type == StrategyType.TWAP:
                config.strategy_params = {
                    "total_amount": config.order_amount * 10,
                    "time_delay": 60
                }
            elif strategy_type == StrategyType.DIRECTIONAL_TRADING:
                config.strategy_params = {
                    "side": "BUY",
                    "entry_price": 45000,
                    "take_profit": 0.02,
                    "stop_loss": 0.01
                }

            # Create test connector
            connector_config = ConnectorConfig(
                connector_type=ConnectorType.HYPERLIQUID_PERPETUAL,
                trading_pairs=["BTC-USD"],
                trading_required=False
            )
            test_connector = self.connector_factory.create_connector(connector_config)
            connectors = {"test": test_connector}

            # Test V2 strategy creation
            v2_wrapper = v2_manager.create_v2_strategy(config, connectors)

            if v2_wrapper:
                self.test_results.append(CompatibilityTestResult(
                    component_name=f"v2_{strategy_type.value}",
                    test_type="v2_strategy",
                    success=True,
                    details={
                        "wrapper_class": v2_wrapper.__class__.__name__,
                        "strategy_framework": v2_wrapper.strategy_framework is not None,
                        "trading_pairs": config.trading_pairs
                    }
                ))
                logging.info(f"✅ V2 Strategy {strategy_type.value}: PASS")
            else:
                self.test_results.append(CompatibilityTestResult(
                    component_name=f"v2_{strategy_type.value}",
                    test_type="v2_strategy",
                    success=False,
                    error_message="V2 strategy creation returned None"
                ))
                logging.warning(f"❌ V2 Strategy {strategy_type.value}: FAIL - Creation returned None")

        except Exception as e:
            self.test_results.append(CompatibilityTestResult(
                component_name=f"v2_{strategy_type.value}",
                test_type="v2_strategy",
                success=False,
                error_message=str(e)
            ))
            logging.warning(f"❌ V2 Strategy {strategy_type.value}: FAIL - {e}")

    async def _test_database_compatibility(self):
        """Test database operations."""
        logging.info("💾 Testing database compatibility...")

        try:
            # Test universal strategy config save/load
            test_config = UniversalStrategyConfig(
                name="TEST_DB_STRATEGY",
                strategy_type=StrategyType.PURE_MARKET_MAKING,
                connector_type=ConnectorType.HYPERLIQUID_PERPETUAL,
                trading_pairs=["BTC-USD"],
                bid_spread=0.05,
                ask_spread=0.05,
                order_amount=0.001
            )

            # Save
            save_success = self.database.save_universal_strategy(test_config)
            if not save_success:
                raise Exception("Failed to save strategy to database")

            # Load
            loaded_config = self.database.load_universal_strategy("TEST_DB_STRATEGY")
            if not loaded_config:
                raise Exception("Failed to load strategy from database")

            # Verify
            if loaded_config.name != test_config.name:
                raise Exception("Loaded strategy name mismatch")

            # Load all
            all_strategies = self.database.load_all_universal_strategies()
            if len(all_strategies) == 0:
                raise Exception("Failed to load all strategies")

            self.test_results.append(CompatibilityTestResult(
                component_name="database_operations",
                test_type="database",
                success=True,
                details={
                    "save_success": save_success,
                    "load_success": loaded_config is not None,
                    "total_strategies": len(all_strategies)
                }
            ))
            logging.info("✅ Database operations: PASS")

        except Exception as e:
            self.test_results.append(CompatibilityTestResult(
                component_name="database_operations",
                test_type="database",
                success=False,
                error_message=str(e)
            ))
            logging.warning(f"❌ Database operations: FAIL - {e}")

    async def _test_risk_management_compatibility(self):
        """Test risk management functionality."""
        logging.info("🛡️ Testing risk management compatibility...")

        try:
            # Test risk limits
            test_limits = RiskLimits(
                max_drawdown_pct=15.0,
                max_order_size_pct=5.0
            )

            update_success = self.risk_manager.update_risk_limits(test_limits)
            if not update_success:
                raise Exception("Failed to update risk limits")

            # Test risk summary generation
            risk_summary = self.risk_manager.get_risk_summary()
            if "portfolio_metrics" not in risk_summary:
                raise Exception("Invalid risk summary format")

            # Test portfolio metrics (with empty connectors)
            metrics_success = self.risk_manager.update_portfolio_metrics({})

            self.test_results.append(CompatibilityTestResult(
                component_name="risk_management",
                test_type="risk_manager",
                success=True,
                details={
                    "limits_update": update_success,
                    "summary_generation": "portfolio_metrics" in risk_summary,
                    "metrics_update": metrics_success
                }
            ))
            logging.info("✅ Risk management: PASS")

        except Exception as e:
            self.test_results.append(CompatibilityTestResult(
                component_name="risk_management",
                test_type="risk_manager",
                success=False,
                error_message=str(e)
            ))
            logging.warning(f"❌ Risk management: FAIL - {e}")

    def _generate_test_summary(self) -> Dict[str, Any]:
        """Generate comprehensive test summary."""
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r.success])
        failed_tests = total_tests - passed_tests

        # Group by test type
        test_types = {}
        for result in self.test_results:
            test_type = result.test_type
            if test_type not in test_types:
                test_types[test_type] = {"total": 0, "passed": 0, "failed": 0}

            test_types[test_type]["total"] += 1
            if result.success:
                test_types[test_type]["passed"] += 1
            else:
                test_types[test_type]["failed"] += 1

        # Calculate success rate
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

        # Get failed tests
        failed_results = [r for r in self.test_results if not r.success]

        summary = {
            "overall": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "success_rate": f"{success_rate:.1f}%",
                "status": "PASS" if failed_tests == 0 else "FAIL"
            },
            "by_type": test_types,
            "failed_tests": [
                {
                    "component": r.component_name,
                    "type": r.test_type,
                    "error": r.error_message
                }
                for r in failed_results
            ],
            "detailed_results": [
                {
                    "component": r.component_name,
                    "type": r.test_type,
                    "success": r.success,
                    "error": r.error_message if not r.success else None,
                    "details": r.details
                }
                for r in self.test_results
            ]
        }

        return summary

    def print_summary_report(self, summary: Dict[str, Any]):
        """Print a formatted summary report."""
        print("\n" + "=" * 80)
        print("🧪 HIVEBOT COMPATIBILITY TEST RESULTS")
        print("=" * 80)

        overall = summary["overall"]
        print(f"📊 Overall Status: {overall['status']}")
        print(f"✅ Tests Passed: {overall['passed']}/{overall['total']} ({overall['success_rate']})")
        print(f"❌ Tests Failed: {overall['failed']}")

        print("\n📋 Results by Component Type:")
        for test_type, stats in summary["by_type"].items():
            status = "✅" if stats["failed"] == 0 else "❌"
            print(f"  {status} {test_type.title()}: {stats['passed']}/{stats['total']} passed")

        if summary["failed_tests"]:
            print(f"\n❌ Failed Tests ({len(summary['failed_tests'])}):")
            for failed in summary["failed_tests"]:
                print(f"  - {failed['component']} ({failed['type']}): {failed['error']}")

        print("\n" + "=" * 80)


async def main():
    """Run the compatibility test suite."""
    if not IMPORTS_AVAILABLE:
        print("❌ Cannot run tests - imports failed")
        return

    try:
        tester = HiveCompatibilityTester()
        summary = await tester.run_full_compatibility_test()
        tester.print_summary_report(summary)

        # Log final status
        if summary["overall"]["status"] == "PASS":
            logging.info("🎉 ALL COMPATIBILITY TESTS PASSED! Hivebot is fully compatible with Hummingbot features.")
        else:
            failed_count = summary["overall"]["failed"]
            logging.warning(f"⚠️ {failed_count} compatibility issues found. See report above for details.")

    except Exception as e:
        logging.error(f"❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
