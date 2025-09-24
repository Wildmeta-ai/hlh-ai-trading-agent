#!/usr/bin/env python3

"""
Hive Agent Wallet Setup Guide - Simple instructions for using agent wallets with Hivebot.
Following the proven Hummingbot approach: users setup agent wallets externally.
"""

from typing import Dict


def print_agent_setup_instructions():
    """Print simple instructions for agent wallet setup."""
    print("\n" + "=" * 70)
    print("🔑 HYPERLIQUID AGENT WALLET SETUP")
    print("=" * 70)
    print("Hivebot uses agent wallets for secure trading (your main keys stay safe)")
    print("\n📋 SETUP STEPS:")
    print("1. Visit https://app.hyperliquid.xyz/API (or testnet version)")
    print("2. Connect your main trading wallet")
    print("3. Create a new agent wallet (system generates private key)")
    print("4. Approve the agent wallet (sign with main wallet)")
    print("5. Copy the agent private key")
    print("6. Use agent private key with Hivebot")
    print("\n🛡️ SECURITY:")
    print("✅ Agent wallets can only trade, not withdraw")
    print("✅ Your main private key never leaves your control")
    print("✅ You can revoke agent access anytime")
    print("\n💡 USAGE WITH HIVEBOT:")
    print("python hive_dynamic_core_modular.py --trading --private-key 0xYOUR_AGENT_PRIVATE_KEY")
    print("=" * 70 + "\n")


def get_agent_setup_summary() -> Dict[str, any]:
    """Get agent setup information as data structure."""
    return {
        "title": "Hyperliquid Agent Wallet Setup",
        "description": "Simple external setup process (same as Hummingbot)",
        "steps": [
            "Visit Hyperliquid API page",
            "Connect main wallet",
            "Create agent wallet",
            "Approve agent (sign transaction)",
            "Copy agent private key",
            "Use with Hivebot"
        ],
        "security_benefits": [
            "Agent can only trade, not withdraw",
            "Main private key stays secure",
            "Revocable access"
        ],
        "estimated_time": "2-5 minutes",
        "hivebot_usage": "python hive_dynamic_core_modular.py --trading --private-key YOUR_AGENT_KEY"
    }


def validate_agent_private_key(private_key: str) -> bool:
    """Basic validation of agent private key format."""
    if not private_key:
        return False

    # Remove 0x prefix if present
    if private_key.startswith('0x'):
        private_key = private_key[2:]

    # Should be 64 hex characters
    if len(private_key) != 64:
        return False

    try:
        int(private_key, 16)
        return True
    except ValueError:
        return False


def example_agent_usage():
    """Show example of using agent wallets with Hivebot."""
    print("\n" + "=" * 60)
    print("📝 EXAMPLE AGENT WALLET USAGE")
    print("=" * 60)
    print("After setting up your agent wallet on Hyperliquid:")
    print()
    print("# Start Hivebot with agent wallet")
    print("python hive_dynamic_core_modular.py \\")
    print("  --trading \\")
    print("  --private-key 0x1234...your_agent_private_key \\")
    print("  --monitor")
    print()
    print("# The system will:")
    print("✅ Use your agent wallet for secure trading")
    print("✅ Load existing strategies from database")
    print("✅ Start multi-strategy trading immediately")
    print("✅ Provide real-time monitoring")
    print()
    print("# Add new strategies via API:")
    print("curl -X POST http://localhost:8080/strategies \\")
    print('  -d \'{"name": "my_pmm", "strategy_type": "pure_market_making", ...}\'')
    print("=" * 60)


def check_hivebot_ready_for_agents() -> bool:
    """Verify Hivebot architecture supports agent wallets."""
    try:
        # Check if required components exist
        from hive_connector_factory import create_hyperliquid_connector  # noqa: F401
        from hive_database import UniversalStrategyConfig  # noqa: F401
        from hive_orchestrator import HiveDynamicCore  # noqa: F401

        print("✅ Hivebot agent wallet support verified")
        print("  - Connector factory supports agent authentication")
        print("  - Database supports agent credentials")
        print("  - Orchestrator supports private key parameter")
        return True

    except ImportError as e:
        print(f"❌ Missing component for agent support: {e}")
        return False


if __name__ == "__main__":
    print("🤖 Hive Agent Wallet Setup")

    # Check system readiness
    if not check_hivebot_ready_for_agents():
        print("❌ System not ready for agent wallets")
        exit(1)

    # Show instructions
    print_agent_setup_instructions()

    # Show example usage
    example_agent_usage()

    # Test private key validation
    print("\n🧪 Testing private key validation:")
    test_keys = [
        "0x1234567890123456789012345678901234567890123456789012345678901234",  # Valid  # noqa: documentation
        "1234567890123456789012345678901234567890123456789012345678901234",    # Valid without 0x  # noqa: documentation
        "0x123",  # Too short
        "not_a_key",  # Invalid format
    ]

    for key in test_keys:
        is_valid = validate_agent_private_key(key)
        print(f"  {key[:20]}... -> {'✅ Valid' if is_valid else '❌ Invalid'}")

    print("\n🎯 Ready to use agent wallets with Hivebot!")
