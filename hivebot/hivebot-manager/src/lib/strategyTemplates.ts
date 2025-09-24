import { StrategyTemplate, StrategyParameter } from '@/types';

// Pure Market Making Strategy Template
const pureMarketMakingTemplate: StrategyTemplate = {
  type: 'pure_market_making',
  name: 'Pure Market Making',
  description: 'Traditional market making strategy that places buy and sell orders around the current market price',
  category: 'market_making',
  defaultValues: {
    strategy_type: 'pure_market_making',
    connector_type: 'hyperliquid_perpetual',
    trading_pairs: ['BTC-USD'],
    bid_spread: 0.002,
    ask_spread: 0.002,
    order_amount: 0.001,
    order_levels: 1,
    order_refresh_time: 30.0,
    enabled: true
  },
  parameters: [
    {
      key: 'name',
      label: 'Strategy Name',
      type: 'string',
      required: true,
      description: 'Unique name for this strategy instance'
    },
    {
      key: 'connector_type',
      label: 'Exchange Connector',
      type: 'select',
      required: true,
      options: [
        { value: 'hyperliquid_perpetual', label: 'Hyperliquid Perpetual' },
        { value: 'binance_perpetual', label: 'Binance Perpetual' },
        { value: 'okx_perpetual', label: 'OKX Perpetual' }
      ],
      default: 'hyperliquid_perpetual'
    },
    {
      key: 'trading_pairs',
      label: 'Trading Pair',
      type: 'select',
      required: true,
      options: [
        { value: 'BTC-USD', label: 'BTC-USD' },
        { value: 'ETH-USD', label: 'ETH-USD' },
        { value: 'HYPE-USDC', label: 'HYPE-USDC' },
        { value: 'PURR-USDC', label: 'PURR-USDC' }
      ],
      default: 'BTC-USD'
    },
    {
      key: 'bid_spread',
      label: 'Bid Spread (%)',
      type: 'number',
      required: true,
      min: 0.001,
      max: 0.1,
      step: 0.001,
      default: 0.002,
      description: 'How far from mid price to place bid orders (as percentage)'
    },
    {
      key: 'ask_spread',
      label: 'Ask Spread (%)',
      type: 'number',
      required: true,
      min: 0.001,
      max: 0.1,
      step: 0.001,
      default: 0.002,
      description: 'How far from mid price to place ask orders (as percentage)'
    },
    {
      key: 'order_amount',
      label: 'Order Amount',
      type: 'number',
      required: true,
      min: 0.001,
      step: 0.001,
      default: 0.001,
      description: 'Size of each order in base currency'
    },
    {
      key: 'order_levels',
      label: 'Order Levels',
      type: 'number',
      required: true,
      min: 1,
      max: 10,
      step: 1,
      default: 1,
      description: 'Number of order levels on each side'
    },
    {
      key: 'order_refresh_time',
      label: 'Order Refresh Time (s)',
      type: 'number',
      required: true,
      min: 1,
      max: 300,
      step: 0.1,
      default: 30.0,
      description: 'How often to refresh orders in seconds'
    },
    {
      key: 'leverage',
      label: 'Leverage',
      type: 'number',
      min: 1,
      max: 100,
      step: 1,
      default: 1,
      description: 'Leverage for perpetual trading (1 = no leverage)'
    },
    {
      key: 'position_mode',
      label: 'Position Mode',
      type: 'select',
      options: [
        { value: 'ONEWAY', label: 'One-Way' },
        { value: 'HEDGE', label: 'Hedge' }
      ],
      default: 'ONEWAY',
      description: 'Position mode for perpetual trading'
    }
  ],
  examples: [
    {
      name: 'Conservative BTC',
      description: 'Low-risk BTC market making with tight spreads',
      config: {
        name: 'Conservative_BTC_MM',
        bid_spread: 0.001,
        ask_spread: 0.001,
        order_amount: 0.001,
        order_refresh_time: 60.0
      }
    },
    {
      name: 'Aggressive ETH',
      description: 'Higher frequency ETH market making',
      config: {
        name: 'Aggressive_ETH_MM',
        trading_pairs: ['ETH-USD'],
        bid_spread: 0.003,
        ask_spread: 0.003,
        order_amount: 0.01,
        order_refresh_time: 10.0
      }
    }
  ]
};

// Directional Trading Strategy Template
const directionalTradingTemplate: StrategyTemplate = {
  type: 'directional_trading',
  name: 'Directional Trading',
  description: 'V2 strategy that trades based on market direction using technical indicators',
  category: 'directional_trading',
  defaultValues: {
    strategy_type: 'directional_trading',
    controller_type: 'directional_trading',
    controller_name: 'dman_v3',
    connector_type: 'hyperliquid_perpetual',
    trading_pairs: ['HYPE-USDC'],
    total_amount_quote: 500,
    leverage: 2,
    position_mode: 'HEDGE',
    enabled: true
  },
  parameters: [
    {
      key: 'name',
      label: 'Strategy Name',
      type: 'string',
      required: true,
      description: 'Unique name for this strategy instance'
    },
    {
      key: 'controller_name',
      label: 'Controller',
      type: 'select',
      required: true,
      options: [
        // Directional Trading Controllers
        { value: 'dman_v3', label: 'DMan V3 (Advanced AI)' },
        { value: 'bollinger_v1', label: 'Bollinger Bands V1' },
        { value: 'macd_bb_v1', label: 'MACD + Bollinger V1' },
        { value: 'supertrend_v1', label: 'SuperTrend V1' },
        { value: 'ai_livestream', label: 'AI Livestream' },
        // Market Making Controllers
        { value: 'pmm_simple', label: 'PMM Simple' },
        { value: 'pmm_dynamic', label: 'PMM Dynamic' },
        { value: 'dman_maker_v2', label: 'DMan Maker V2' },
        // Generic Controllers
        { value: 'arbitrage_controller', label: 'Arbitrage Controller' },
        { value: 'grid_strike', label: 'Grid Strike' },
        { value: 'multi_grid_strike', label: 'Multi Grid Strike' },
        { value: 'stat_arb', label: 'Statistical Arbitrage' }
      ],
      default: 'dman_v3',
      description: 'V2 Trading controller algorithm (18 available)'
    },
    {
      key: 'connector_type',
      label: 'Exchange Connector',
      type: 'select',
      required: true,
      options: [
        { value: 'hyperliquid_perpetual', label: 'Hyperliquid Perpetual' },
        { value: 'binance_perpetual', label: 'Binance Perpetual' }
      ],
      default: 'hyperliquid_perpetual'
    },
    {
      key: 'trading_pairs',
      label: 'Trading Pair',
      type: 'select',
      required: true,
      options: [
        { value: 'HYPE-USDC', label: 'HYPE-USDC' },
        { value: 'BTC-USD', label: 'BTC-USD' },
        { value: 'ETH-USD', label: 'ETH-USD' }
      ],
      default: 'HYPE-USDC'
    },
    {
      key: 'total_amount_quote',
      label: 'Total Amount (Quote Currency)',
      type: 'number',
      required: true,
      min: 10,
      max: 10000,
      step: 10,
      default: 500,
      description: 'Total amount in quote currency to use for trading'
    },
    {
      key: 'leverage',
      label: 'Leverage',
      type: 'number',
      min: 1,
      max: 20,
      step: 1,
      default: 2,
      description: 'Trading leverage (1-20x)'
    },
    {
      key: 'position_mode',
      label: 'Position Mode',
      type: 'select',
      required: true,
      options: [
        { value: 'HEDGE', label: 'Hedge Mode' },
        { value: 'ONEWAY', label: 'One-Way Mode' }
      ],
      default: 'HEDGE',
      description: 'Position mode for directional trading'
    },
    {
      key: 'bb_length',
      label: 'Bollinger Bands Length',
      type: 'number',
      min: 5,
      max: 50,
      step: 1,
      default: 14,
      description: 'Number of periods for Bollinger Bands calculation'
    },
    {
      key: 'bb_long_threshold',
      label: 'BB Long Threshold',
      type: 'number',
      min: 0.1,
      max: 1.0,
      step: 0.1,
      default: 0.7,
      description: 'Bollinger Band threshold for long positions'
    },
    {
      key: 'bb_short_threshold',
      label: 'BB Short Threshold',
      type: 'number',
      min: 0.1,
      max: 1.0,
      step: 0.1,
      default: 0.3,
      description: 'Bollinger Band threshold for short positions'
    },
    {
      key: 'bb_std',
      label: 'BB Standard Deviations',
      type: 'number',
      min: 1.0,
      max: 3.0,
      step: 0.1,
      default: 2.0,
      description: 'Standard deviations for Bollinger Bands'
    },
    {
      key: 'interval',
      label: 'Candle Interval',
      type: 'select',
      options: [
        { value: '1m', label: '1 minute' },
        { value: '5m', label: '5 minutes' },
        { value: '15m', label: '15 minutes' },
        { value: '1h', label: '1 hour' },
        { value: '4h', label: '4 hours' },
        { value: '1d', label: '1 day' }
      ],
      default: '1h',
      description: 'Candlestick interval for technical analysis'
    },
    {
      key: 'candles_connector',
      label: 'Candles Data Source',
      type: 'select',
      options: [
        { value: 'hyperliquid', label: 'Hyperliquid' },
        { value: 'binance', label: 'Binance' }
      ],
      default: 'hyperliquid',
      description: 'Data source for candlestick data'
    },
    {
      key: 'candles_trading_pair',
      label: 'Candles Trading Pair',
      type: 'string',
      default: 'HYPE-USDC',
      description: 'Trading pair for candlestick data (can differ from execution pair)'
    },
    {
      key: 'stop_loss',
      label: 'Stop Loss (%)',
      type: 'number',
      min: 0.01,
      max: 0.5,
      step: 0.01,
      default: 0.1,
      description: 'Stop loss percentage (0.1 = 10%)'
    },
    {
      key: 'take_profit',
      label: 'Take Profit (%)',
      type: 'number',
      min: 0.01,
      max: 1.0,
      step: 0.01,
      default: 0.15,
      description: 'Take profit percentage (0.15 = 15%)'
    },
    {
      key: 'cooldown_time',
      label: 'Cooldown Time (seconds)',
      type: 'number',
      min: 60,
      max: 86400,
      step: 60,
      default: 10800,
      description: 'Cooldown period between trades in seconds'
    },
    {
      key: 'time_limit',
      label: 'Time Limit (seconds)',
      type: 'number',
      min: 3600,
      max: 604800,
      step: 3600,
      default: 259200,
      description: 'Maximum time to hold a position in seconds'
    },
    {
      key: 'dca_spreads',
      label: 'DCA Spreads',
      type: 'string',
      default: '0.02,0.04,0.06',
      description: 'Dollar-cost averaging spreads (comma separated, e.g., "0.02,0.04,0.06")',
      validation: {
        pattern: '^[0-9.,]+$',
        message: 'Enter comma-separated decimal values'
      }
    },
    {
      key: 'max_executors_per_side',
      label: 'Max Executors Per Side',
      type: 'number',
      min: 1,
      max: 10,
      step: 1,
      default: 3,
      description: 'Maximum number of executors per side (long/short)'
    }
  ],
  examples: [
    {
      name: 'Conservative HYPE Trading',
      description: 'Low-risk directional trading on HYPE with tight risk management',
      config: {
        name: 'Conservative_HYPE_Direction',
        total_amount_quote: 200,
        leverage: 1,
        stop_loss: 0.05,
        take_profit: 0.08,
        cooldown_time: 14400
      }
    },
    {
      name: 'Aggressive BTC Scalping',
      description: 'High-frequency BTC directional trading',
      config: {
        name: 'Aggressive_BTC_Scalping',
        trading_pairs: ['BTC-USD'],
        total_amount_quote: 1000,
        leverage: 5,
        interval: '5m',
        stop_loss: 0.02,
        take_profit: 0.03,
        cooldown_time: 3600
      }
    }
  ]
};

// Bollinger Bands V1 Strategy Template
const bollingerV1Template: StrategyTemplate = {
  type: 'bollinger_v1',
  name: 'Bollinger Bands V1',
  description: 'Classic Bollinger Bands directional trading strategy',
  category: 'directional_trading',
  defaultValues: {
    strategy_type: 'directional_trading',
    controller_type: 'directional_trading',
    controller_name: 'bollinger_v1',
    connector_type: 'hyperliquid_perpetual',
    trading_pairs: ['BTC-USD'],
    total_amount_quote: 1000,
    enabled: true
  },
  parameters: [
    {
      key: 'name',
      label: 'Strategy Name',
      type: 'string',
      required: true,
      description: 'Unique name for this strategy instance'
    },
    {
      key: 'controller_name',
      label: 'Controller',
      type: 'select',
      required: true,
      options: [{ value: 'bollinger_v1', label: 'Bollinger Bands V1' }],
      default: 'bollinger_v1'
    },
    {
      key: 'connector_type',
      label: 'Exchange Connector',
      type: 'select',
      required: true,
      options: [
        { value: 'hyperliquid_perpetual', label: 'Hyperliquid Perpetual' },
        { value: 'binance_perpetual', label: 'Binance Perpetual' }
      ],
      default: 'hyperliquid_perpetual'
    },
    {
      key: 'trading_pairs',
      label: 'Trading Pair',
      type: 'select',
      required: true,
      options: [
        { value: 'BTC-USD', label: 'BTC-USD' },
        { value: 'ETH-USD', label: 'ETH-USD' },
        { value: 'HYPE-USDC', label: 'HYPE-USDC' }
      ],
      default: 'BTC-USD'
    },
    {
      key: 'total_amount_quote',
      label: 'Total Amount (Quote Currency)',
      type: 'number',
      required: true,
      min: 10,
      max: 10000,
      step: 10,
      default: 1000,
      description: 'Total amount in quote currency to use for trading'
    },
    {
      key: 'bb_length',
      label: 'Bollinger Bands Length',
      type: 'number',
      min: 5,
      max: 200,
      step: 1,
      default: 100,
      description: 'Number of periods for Bollinger Bands calculation'
    },
    {
      key: 'bb_std',
      label: 'BB Standard Deviations',
      type: 'number',
      min: 1.0,
      max: 3.0,
      step: 0.1,
      default: 2.0,
      description: 'Standard deviations for Bollinger Bands'
    },
    {
      key: 'bb_long_threshold',
      label: 'BB Long Threshold',
      type: 'number',
      min: 0.0,
      max: 1.0,
      step: 0.1,
      default: 0.0,
      description: 'Threshold for long positions (0.0 = lower band)'
    },
    {
      key: 'bb_short_threshold',
      label: 'BB Short Threshold',
      type: 'number',
      min: 0.0,
      max: 1.0,
      step: 0.1,
      default: 1.0,
      description: 'Threshold for short positions (1.0 = upper band)'
    },
    {
      key: 'interval',
      label: 'Candle Interval',
      type: 'select',
      options: [
        { value: '1m', label: '1 minute' },
        { value: '3m', label: '3 minutes' },
        { value: '5m', label: '5 minutes' },
        { value: '15m', label: '15 minutes' },
        { value: '1h', label: '1 hour' }
      ],
      default: '3m',
      description: 'Candlestick interval for Bollinger Bands'
    }
  ],
  examples: [
    {
      name: 'Conservative BB Strategy',
      description: 'Safe Bollinger Bands with tight thresholds',
      config: {
        name: 'Conservative_BB_BTC',
        bb_length: 50,
        bb_std: 1.5,
        bb_long_threshold: 0.2,
        bb_short_threshold: 0.8,
        total_amount_quote: 500
      }
    }
  ]
};

// PMM Dynamic Strategy Template
const pmmDynamicTemplate: StrategyTemplate = {
  type: 'pmm_dynamic',
  name: 'PMM Dynamic',
  description: 'Dynamic Pure Market Making with adaptive spreads',
  category: 'market_making',
  defaultValues: {
    strategy_type: 'market_making',
    controller_type: 'market_making',
    controller_name: 'pmm_dynamic',
    connector_type: 'hyperliquid_perpetual',
    trading_pairs: ['BTC-USD'],
    total_amount_quote: 1000,
    enabled: true
  },
  parameters: [
    {
      key: 'name',
      label: 'Strategy Name',
      type: 'string',
      required: true,
      description: 'Unique name for this strategy instance'
    },
    {
      key: 'controller_name',
      label: 'Controller',
      type: 'select',
      required: true,
      options: [{ value: 'pmm_dynamic', label: 'PMM Dynamic' }],
      default: 'pmm_dynamic'
    },
    {
      key: 'connector_type',
      label: 'Exchange Connector',
      type: 'select',
      required: true,
      options: [
        { value: 'hyperliquid_perpetual', label: 'Hyperliquid Perpetual' },
        { value: 'binance_perpetual', label: 'Binance Perpetual' }
      ],
      default: 'hyperliquid_perpetual'
    },
    {
      key: 'total_amount_quote',
      label: 'Total Amount (Quote Currency)',
      type: 'number',
      required: true,
      min: 100,
      max: 50000,
      step: 100,
      default: 1000,
      description: 'Total amount for market making'
    },
    {
      key: 'spread_multiplier',
      label: 'Spread Multiplier',
      type: 'number',
      min: 0.5,
      max: 3.0,
      step: 0.1,
      default: 1.0,
      description: 'Multiplier for dynamic spread calculation'
    },
    {
      key: 'volatility_buffer_multiplier',
      label: 'Volatility Buffer Multiplier',
      type: 'number',
      min: 0.5,
      max: 2.0,
      step: 0.1,
      default: 1.0,
      description: 'Buffer for volatility-based adjustments'
    }
  ]
};

// Arbitrage Controller Template
const arbitrageTemplate: StrategyTemplate = {
  type: 'arbitrage_controller',
  name: 'Arbitrage Controller',
  description: 'Cross-exchange arbitrage opportunities detection',
  category: 'arbitrage',
  defaultValues: {
    strategy_type: 'arbitrage',
    controller_type: 'generic',
    controller_name: 'arbitrage_controller',
    connector_type: 'hyperliquid_perpetual',
    trading_pairs: ['BTC-USD'],
    enabled: true
  },
  parameters: [
    {
      key: 'name',
      label: 'Strategy Name',
      type: 'string',
      required: true,
      description: 'Unique name for this strategy instance'
    },
    {
      key: 'connector_type',
      label: 'Exchange Connector',
      type: 'select',
      required: true,
      options: [
        { value: 'hyperliquid_perpetual', label: 'Hyperliquid Perpetual' },
        { value: 'binance_perpetual', label: 'Binance Perpetual' }
      ],
      default: 'hyperliquid_perpetual'
    },
    {
      key: 'trading_pairs',
      label: 'Trading Pair',
      type: 'select',
      required: true,
      options: [
        { value: 'BTC-USD', label: 'BTC-USD' },
        { value: 'ETH-USD', label: 'ETH-USD' },
        { value: 'HYPE-USDC', label: 'HYPE-USDC' }
      ],
      default: 'BTC-USD'
    },
    {
      key: 'total_amount_quote',
      label: 'Total Amount (Quote Currency)',
      type: 'number',
      required: true,
      min: 100,
      max: 50000,
      step: 100,
      default: 1000,
      description: 'Total amount in quote currency for market making'
    },
    {
      key: 'min_spread',
      label: 'Minimum Spread',
      type: 'number',
      min: 0.0001,
      max: 0.01,
      step: 0.0001,
      default: 0.002,
      description: 'Minimum spread between bid and ask'
    },
    {
      key: 'risk_factor',
      label: 'Risk Factor',
      type: 'number',
      min: 0.1,
      max: 2.0,
      step: 0.1,
      default: 0.5,
      description: 'Risk aversion parameter (higher = more conservative)'
    },
    {
      key: 'order_amount',
      label: 'Order Amount',
      type: 'number',
      min: 0.001,
      step: 0.001,
      default: 0.01,
      description: 'Size of each order in base currency'
    },
    {
      key: 'order_levels',
      label: 'Order Levels',
      type: 'number',
      min: 1,
      max: 5,
      step: 1,
      default: 1,
      description: 'Number of order levels on each side'
    },
    {
      key: 'order_refresh_time',
      label: 'Order Refresh Time (s)',
      type: 'number',
      min: 1,
      max: 300,
      step: 1,
      default: 30,
      description: 'How often to refresh orders'
    }
  ],
  examples: [
    {
      name: 'Standard Arbitrage Setup',
      description: 'Basic cross-exchange arbitrage configuration',
      config: {
        name: 'Arbitrage_BTC_Cross',
        min_profit_threshold: 0.005,
        max_order_size: 0.1
      }
    }
  ]
};

// Export all strategy templates
export const STRATEGY_TEMPLATES: StrategyTemplate[] = [
  pureMarketMakingTemplate,
  directionalTradingTemplate,
  bollingerV1Template,
  pmmDynamicTemplate,
  arbitrageTemplate
];

// Helper function to get template by type
export function getStrategyTemplate(type: string): StrategyTemplate | undefined {
  return STRATEGY_TEMPLATES.find(template => template.type === type);
}

// Helper function to get parameters for a strategy type
export function getStrategyParameters(type: string): StrategyParameter[] {
  const template = getStrategyTemplate(type);
  return template?.parameters || [];
}

// Helper function to get default values for a strategy type
export function getStrategyDefaults(type: string): Record<string, unknown> {
  const template = getStrategyTemplate(type);
  return template?.defaultValues || {};
}

// Strategy categories for grouping (expanded)
export const STRATEGY_CATEGORIES = [
  { value: 'market_making', label: 'Market Making', icon: '📊', count: 8 },
  { value: 'directional_trading', label: 'Directional Trading', icon: '📈', count: 5 },
  { value: 'arbitrage', label: 'Arbitrage', icon: '⚡', count: 3 },
  { value: 'grid_trading', label: 'Grid Trading', icon: '🔲', count: 2 },
  { value: 'other', label: 'Other', icon: '🔧', count: 0 }
];

// Complete controller registry (18 total)
export const AVAILABLE_CONTROLLERS = {
  // Directional Trading (5)
  directional_trading: [
    'dman_v3',
    'bollinger_v1',
    'macd_bb_v1',
    'supertrend_v1',
    'ai_livestream'
  ],
  // Market Making (3)
  market_making: [
    'pmm_simple',
    'pmm_dynamic',
    'dman_maker_v2'
  ],
  // Generic (10)
  generic: [
    'pmm',
    'pmm_adjusted',
    'grid_strike',
    'multi_grid_strike',
    'arbitrage_controller',
    'stat_arb',
    'xemm_multiple_levels',
    'quantum_grid_allocator',
    'basic_order_example',
    'basic_order_open_close_example'
  ]
};

// Controller descriptions
export const CONTROLLER_DESCRIPTIONS = {
  // Directional Trading
  'dman_v3': 'Advanced AI-powered directional trading with 20+ parameters',
  'bollinger_v1': 'Classic Bollinger Bands mean reversion strategy',
  'macd_bb_v1': 'MACD combined with Bollinger Bands for trend confirmation',
  'supertrend_v1': 'SuperTrend indicator for trend following',
  'ai_livestream': 'AI-powered livestream trading with real-time analysis',

  // Market Making
  'pmm_simple': 'Simple Pure Market Making with basic bid/ask spreads',
  'pmm_dynamic': 'Dynamic PMM with adaptive spreads based on volatility',
  'dman_maker_v2': 'Advanced market making with dynamic pricing',

  // Generic
  'arbitrage_controller': 'Cross-exchange arbitrage opportunity detection',
  'grid_strike': 'Single-level grid trading strategy',
  'multi_grid_strike': 'Multi-level grid trading with complex allocation',
  'stat_arb': 'Statistical arbitrage based on price relationships'
};
