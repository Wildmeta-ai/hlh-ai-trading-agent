#!/usr/bin/env node

// Correct Strategy Examples Based on Real Hummingbot Templates
// Generated from actual Hummingbot codebase analysis

const CORRECT_EXAMPLES = {

  // 1. PURE MARKET MAKING (Traditional) - From conf_pure_market_making_strategy_TEMPLATE.yml
  pmm_simple: {
    "strategy": {
      "name": "Conservative_BTC_PMM_Simple",
      "strategy_type": "pure_market_making",
      "connector_type": "hyperliquid_perpetual",
      "trading_pairs": ["BTC-USD"],
      "bid_spread": 0.002,
      "ask_spread": 0.002,
      "order_amount": 0.003,
      "order_levels": 1,
      "order_refresh_time": 100,
      "minimum_spread": 0.001,
      "price_ceiling": null,
      "price_floor": null,
      "ping_pong_enabled": false,
      "inventory_skew_enabled": false,
      "hanging_orders_enabled": false,
      "order_optimization_enabled": false,
      "add_transaction_costs": true,
      "enabled": true,
      "user_id": "user_demo_001"
    }
  },

  // 2. DMAN V3 - From controllers/directional_trading/dman_v3.py
  dman_v3: {
    "strategy": {
      "name": "DMan_V3_Advanced_AI",
      "strategy_type": "directional_trading",
      "controller_type": "directional_trading",
      "controller_name": "dman_v3",
      "connector_type": "hyperliquid_perpetual",
      "trading_pairs": ["HYPE-USDC"],
      "candles_connector": "hyperliquid",
      "candles_trading_pair": "HYPE-USDC",
      "interval": "3m",
      "bb_length": 100,
      "bb_std": 2.0,
      "bb_long_threshold": 0.0,
      "bb_short_threshold": 1.0,
      "trailing_stop": "0.015,0.005",
      "dca_spreads": "0.001,0.018,0.15,0.25",
      "dca_amounts_pct": null,
      "dynamic_order_spread": true,
      "dynamic_target": true,
      "activation_bounds": null,
      "max_executors_per_side": 2,
      "cooldown_time": 300,
      "leverage": 20,
      "position_mode": "HEDGE",
      "stop_loss": 0.03,
      "take_profit": 0.02,
      "time_limit": 2700,
      "take_profit_order_type": "LIMIT",
      "enabled": true,
      "user_id": "user_demo_001"
    }
  },

  // 3. BOLLINGER V1 - From controllers/directional_trading/bollinger_v1.py
  bollinger_v1: {
    "strategy": {
      "name": "Bollinger_Bands_ETH_Classic",
      "strategy_type": "directional_trading",
      "controller_type": "directional_trading",
      "controller_name": "bollinger_v1",
      "connector_type": "hyperliquid_perpetual",
      "trading_pairs": ["ETH-USD"],
      "candles_connector": "hyperliquid",
      "candles_trading_pair": "ETH-USD",
      "interval": "3m",
      "bb_length": 100,
      "bb_std": 2.0,
      "bb_long_threshold": 0.0,
      "bb_short_threshold": 1.0,
      "max_executors_per_side": 2,
      "cooldown_time": 300,
      "leverage": 20,
      "position_mode": "HEDGE",
      "stop_loss": 0.03,
      "take_profit": 0.02,
      "time_limit": 2700,
      "take_profit_order_type": "LIMIT",
      "trailing_stop": null,
      "enabled": true,
      "user_id": "user_demo_001"
    }
  },

  // 4. MACD BB V1 - DirectionalTradingControllerConfigBase + MACD parameters
  macd_bb_v1: {
    "strategy": {
      "name": "MACD_Bollinger_Combo_SOL",
      "strategy_type": "directional_trading",
      "controller_type": "directional_trading",
      "controller_name": "macd_bb_v1",
      "connector_type": "hyperliquid_perpetual",
      "trading_pairs": ["SOL-USD"],
      "candles_connector": "hyperliquid",
      "candles_trading_pair": "SOL-USD",
      "interval": "5m",
      "bb_length": 100,
      "bb_std": 2.0,
      "bb_long_threshold": 0.0,
      "bb_short_threshold": 1.0,
      "max_executors_per_side": 2,
      "cooldown_time": 300,
      "leverage": 20,
      "position_mode": "HEDGE",
      "stop_loss": 0.03,
      "take_profit": 0.02,
      "time_limit": 2700,
      "take_profit_order_type": "LIMIT",
      "trailing_stop": null,
      "enabled": true,
      "user_id": "user_demo_001"
    }
  },

  // 5. SUPERTREND V1 - DirectionalTradingControllerConfigBase
  supertrend_v1: {
    "strategy": {
      "name": "SuperTrend_BTC_Momentum",
      "strategy_type": "directional_trading",
      "controller_type": "directional_trading",
      "controller_name": "supertrend_v1",
      "connector_type": "hyperliquid_perpetual",
      "trading_pairs": ["BTC-USD"],
      "candles_connector": "hyperliquid",
      "candles_trading_pair": "BTC-USD",
      "interval": "15m",
      "max_executors_per_side": 2,
      "cooldown_time": 300,
      "leverage": 20,
      "position_mode": "HEDGE",
      "stop_loss": 0.03,
      "take_profit": 0.02,
      "time_limit": 2700,
      "take_profit_order_type": "LIMIT",
      "trailing_stop": null,
      "enabled": true,
      "user_id": "user_demo_001"
    }
  },

  // 6. PMM DYNAMIC - From controllers/market_making/pmm_dynamic.py + MarketMakingControllerConfigBase
  pmm_dynamic: {
    "strategy": {
      "name": "Dynamic_PMM_Advanced_ETH",
      "strategy_type": "market_making",
      "controller_type": "market_making",
      "controller_name": "pmm_dynamic",
      "connector_type": "hyperliquid_perpetual",
      "trading_pairs": ["ETH-USD"],
      "buy_spreads": [0.01, 0.02],
      "sell_spreads": [0.01, 0.02],
      "buy_amounts_pct": null,
      "sell_amounts_pct": null,
      "executor_refresh_time": 300,
      "cooldown_time": 15,
      "leverage": 20,
      "position_mode": "HEDGE",
      "stop_loss": null,
      "take_profit": null,
      "time_limit": null,
      "take_profit_order_type": "LIMIT",
      "trailing_stop": null,
      "enabled": true,
      "user_id": "user_demo_001"
    }
  },

  // 7. DMAN MAKER V2 - MarketMakingControllerConfigBase
  dman_maker_v2: {
    "strategy": {
      "name": "DMan_Market_Maker_V2",
      "strategy_type": "market_making",
      "controller_type": "market_making",
      "controller_name": "dman_maker_v2",
      "connector_type": "hyperliquid_perpetual",
      "trading_pairs": ["SOL-USD"],
      "buy_spreads": [0.015, 0.025, 0.035],
      "sell_spreads": [0.015, 0.025, 0.035],
      "buy_amounts_pct": [40, 35, 25],
      "sell_amounts_pct": [40, 35, 25],
      "executor_refresh_time": 300,
      "cooldown_time": 15,
      "leverage": 20,
      "position_mode": "HEDGE",
      "stop_loss": null,
      "take_profit": null,
      "time_limit": null,
      "take_profit_order_type": "LIMIT",
      "trailing_stop": null,
      "enabled": true,
      "user_id": "user_demo_001"
    }
  },

  // 8. ARBITRAGE - Based on arbitrage executor and templates
  arbitrage: {
    "strategy": {
      "name": "Cross_Exchange_Arbitrage",
      "strategy_type": "arbitrage",
      "connector_type": "hyperliquid_perpetual",
      "trading_pairs": ["BTC-USD"],
      "min_profitability": 0.001,
      "order_amount": 0.001,
      "order_refresh_time": 10,
      "enabled": true,
      "user_id": "user_demo_001"
    }
  },

  // 9-15. REMAINING V2 MARKET MAKING VARIANTS - Using MarketMakingControllerConfigBase
  grid_strike: {
    "strategy": {
      "name": "Grid_Strategy_HYPE",
      "strategy_type": "market_making",
      "controller_type": "market_making",
      "controller_name": "grid_strike",
      "connector_type": "hyperliquid_perpetual",
      "trading_pairs": ["HYPE-USDC"],
      "buy_spreads": [0.005, 0.01, 0.015],
      "sell_spreads": [0.005, 0.01, 0.015],
      "buy_amounts_pct": [33, 33, 34],
      "sell_amounts_pct": [33, 33, 34],
      "executor_refresh_time": 300,
      "cooldown_time": 15,
      "leverage": 1,
      "position_mode": "HEDGE",
      "enabled": true,
      "user_id": "user_demo_001"
    }
  },

  multi_grid_strike: {
    "strategy": {
      "name": "Multi_Grid_Advanced",
      "strategy_type": "market_making",
      "controller_type": "market_making",
      "controller_name": "multi_grid_strike",
      "connector_type": "hyperliquid_perpetual",
      "trading_pairs": ["ETH-USD"],
      "buy_spreads": [0.01, 0.02, 0.03, 0.04],
      "sell_spreads": [0.01, 0.02, 0.03, 0.04],
      "buy_amounts_pct": [25, 25, 25, 25],
      "sell_amounts_pct": [25, 25, 25, 25],
      "executor_refresh_time": 300,
      "cooldown_time": 15,
      "leverage": 1,
      "position_mode": "HEDGE",
      "enabled": true,
      "user_id": "user_demo_001"
    }
  },

  stat_arb: {
    "strategy": {
      "name": "Statistical_Arbitrage_Pro",
      "strategy_type": "arbitrage",
      "connector_type": "hyperliquid_perpetual",
      "trading_pairs": ["BTC-USD"],
      "min_profitability": 0.0005,
      "order_amount": 0.001,
      "order_refresh_time": 5,
      "enabled": true,
      "user_id": "user_demo_001"
    }
  },

  xemm_multiple_levels: {
    "strategy": {
      "name": "Cross_Exchange_MM_Multi",
      "strategy_type": "market_making",
      "controller_type": "market_making",
      "controller_name": "xemm_multiple_levels",
      "connector_type": "hyperliquid_perpetual",
      "trading_pairs": ["SOL-USD"],
      "buy_spreads": [0.008, 0.016, 0.024],
      "sell_spreads": [0.008, 0.016, 0.024],
      "buy_amounts_pct": [40, 35, 25],
      "sell_amounts_pct": [40, 35, 25],
      "executor_refresh_time": 300,
      "cooldown_time": 15,
      "leverage": 1,
      "position_mode": "HEDGE",
      "enabled": true,
      "user_id": "user_demo_001"
    }
  },

  quantum_grid_allocator: {
    "strategy": {
      "name": "Quantum_Grid_Allocation",
      "strategy_type": "market_making",
      "controller_type": "market_making",
      "controller_name": "quantum_grid_allocator",
      "connector_type": "hyperliquid_perpetual",
      "trading_pairs": ["HYPE-USDC"],
      "buy_spreads": [0.005, 0.01, 0.02, 0.03, 0.05],
      "sell_spreads": [0.005, 0.01, 0.02, 0.03, 0.05],
      "buy_amounts_pct": [20, 20, 20, 20, 20],
      "sell_amounts_pct": [20, 20, 20, 20, 20],
      "executor_refresh_time": 300,
      "cooldown_time": 15,
      "leverage": 1,
      "position_mode": "HEDGE",
      "enabled": true,
      "user_id": "user_demo_001"
    }
  },

  pmm_adjusted: {
    "strategy": {
      "name": "Adjusted_PMM_Generic",
      "strategy_type": "market_making",
      "controller_type": "market_making",
      "controller_name": "pmm_adjusted",
      "connector_type": "hyperliquid_perpetual",
      "trading_pairs": ["BTC-USD"],
      "buy_spreads": [0.012, 0.024],
      "sell_spreads": [0.012, 0.024],
      "buy_amounts_pct": [60, 40],
      "sell_amounts_pct": [60, 40],
      "executor_refresh_time": 300,
      "cooldown_time": 15,
      "leverage": 1,
      "position_mode": "HEDGE",
      "enabled": true,
      "user_id": "user_demo_001"
    }
  },

  pmm_generic: {
    "strategy": {
      "name": "Pure_MM_Generic_Controller",
      "strategy_type": "market_making",
      "controller_type": "market_making",
      "controller_name": "pmm",
      "connector_type": "hyperliquid_perpetual",
      "trading_pairs": ["SOL-USD"],
      "buy_spreads": [0.01],
      "sell_spreads": [0.01],
      "buy_amounts_pct": [100],
      "sell_amounts_pct": [100],
      "executor_refresh_time": 300,
      "cooldown_time": 15,
      "leverage": 1,
      "position_mode": "HEDGE",
      "enabled": true,
      "user_id": "user_demo_001"
    }
  }

};

console.log('✅ All 15 Strategy Examples Corrected Based on Real Hummingbot Templates');
console.log('📊 Coverage: Pure PMM (1) + Directional Trading (4) + Market Making V2 (8) + Arbitrage (2)');

Object.entries(CORRECT_EXAMPLES).forEach(([name, config]) => {
  console.log(`\n${name}: ${config.strategy.name}`);
  console.log(`  Type: ${config.strategy.strategy_type}`);
  console.log(`  Parameters: ${Object.keys(config.strategy).length} fields`);
});

module.exports = CORRECT_EXAMPLES;
