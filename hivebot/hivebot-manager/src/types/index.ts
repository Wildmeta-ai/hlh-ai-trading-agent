// Strategy Configuration Types

// Base strategy configuration
export interface BaseStrategyConfig {
  name: string;
  strategy_type: string;
  connector_type: string;
  trading_pair: string; // Changed from trading_pairs array to singular string
  enabled: boolean;
  created_at?: string;
  updated_at?: string;
  user_id?: string;
}

// Traditional PMM Strategy Configuration
export interface PMMStrategyConfig extends BaseStrategyConfig {
  strategy_type: 'pure_market_making';

  // Core PMM parameters
  bid_spread: number;
  ask_spread: number;
  order_amount: number;
  order_levels: number;
  order_refresh_time: number;
  total_amount_quote?: number; // Required for V2 PMM controllers

  // Advanced PMM parameters
  order_level_spread?: number;
  order_level_amount?: number;
  inventory_target_base_pct?: number;
  inventory_range_multiplier?: number;
  hanging_orders_enabled?: boolean;
  hanging_orders_cancel_pct?: number;
  order_optimization_enabled?: boolean;
  ask_order_optimization_depth?: number;
  bid_order_optimization_depth?: number;
  price_ceiling?: number;
  price_floor?: number;
  ping_pong_enabled?: boolean;
  min_profitability?: number;
  min_price_diff_pct?: number;
  max_order_size?: number;

  // Authentication
  api_key?: string;
  api_secret?: string;
  private_key?: string;

  // Risk management
  leverage?: number;
  position_mode?: 'ONEWAY' | 'HEDGE';
}

// V2 Directional Trading Strategy Configuration
export interface DirectionalTradingConfig extends BaseStrategyConfig {
  strategy_type: 'directional_trading';
  controller_type: 'directional_trading';
  controller_name: string; // e.g., 'dman_v3'

  // Core directional trading parameters
  total_amount_quote: number;
  leverage?: number;
  position_mode?: 'ONEWAY' | 'HEDGE';

  // Bollinger Bands parameters
  bb_length?: number;
  bb_long_threshold?: number;
  bb_short_threshold?: number;
  bb_std?: number;

  // Candle data configuration
  candles_connector?: string;
  candles_trading_pair?: string;
  interval?: string; // e.g., '1h', '5m'

  // Risk management
  stop_loss?: string | number;
  take_profit?: string | number;
  cooldown_time?: number; // seconds
  time_limit?: number; // seconds

  // DCA (Dollar Cost Averaging) settings
  dca_spreads?: string; // e.g., '0.02,0.04,0.06'
  max_executors_per_side?: number;
}

// Avellaneda Market Making Strategy (V2)
export interface AvellanedaConfig extends BaseStrategyConfig {
  strategy_type: 'avellaneda_market_making';
  controller_type: 'market_making';
  controller_name: 'avellaneda_market_making';

  // Core parameters
  total_amount_quote: number;
  min_spread?: number;
  risk_factor?: number;
  order_amount?: number;
  order_levels?: number;
  level_distances?: number;
  order_refresh_time?: number;

  // Advanced parameters
  inventory_target_base_pct?: number;
  add_transaction_costs?: boolean;
  volatility_sensibility?: number;
  eta?: number;
  gamma?: number;
}

// Cross Exchange Market Making Strategy (V2)
export interface CrossExchangeConfig extends BaseStrategyConfig {
  strategy_type: 'cross_exchange_market_making';
  controller_type: 'market_making';
  controller_name: 'cross_exchange_market_making';

  // Exchange configuration
  maker_market_trading_pair: string;
  taker_market_trading_pair: string;

  // Core parameters
  order_amount: number;
  min_profitability: number;
  order_refresh_time?: number;

  // Advanced parameters
  adjust_order_enabled?: boolean;
  active_order_canceling?: boolean;
  cancel_order_threshold?: number;
  limit_order_min_expiration_time?: number;
  top_depth_tolerance?: number;
  anti_hysteresis_duration?: number;
  use_oracle_conversion_rate?: boolean;
  taker_to_maker_base_conversion_rate?: number;
  taker_to_maker_quote_conversion_rate?: number;
}

// V2 Market Making Strategy Configuration (pmm_simple, pmm_dynamic, etc.)
export interface MarketMakingV2Config extends BaseStrategyConfig {
  strategy_type: 'market_making';
  controller_type: 'market_making';
  controller_name: string; // e.g., 'pmm_simple', 'pmm_dynamic', 'dman_maker_v2'

  // Required for all V2 controllers
  total_amount_quote: number;

  // PMM parameters (for pmm_simple, pmm_dynamic)
  buy_spreads?: number[];
  sell_spreads?: number[];
  order_refresh_time?: number;

  // Dynamic PMM parameters (for pmm_dynamic)
  spread_multiplier?: number;
  volatility_buffer_multiplier?: number;
  inventory_target_base_pct?: number;
  max_order_refresh_time?: number;
  min_order_refresh_time?: number;

  // Candle data (for dynamic controllers)
  candles_connector?: string;
  candles_trading_pair?: string;
  interval?: string;
}

// Generic V2 Strategy Configuration (arbitrage, grid_strike, etc.)
export interface GenericV2Config extends BaseStrategyConfig {
  strategy_type: 'arbitrage' | 'grid_trading' | 'generic';
  controller_type: 'generic';
  controller_name: string; // e.g., 'arbitrage_controller', 'grid_strike', etc.

  // Required for all V2 controllers
  total_amount_quote: number;

  // Common generic parameters
  buy_spreads?: number[];
  sell_spreads?: number[];
  min_profitability?: number;

  // Grid parameters
  grid_price_ceiling?: number;
  grid_price_floor?: number;

  // Multi-exchange parameters
  maker_connector?: string;
  taker_connector?: string;
  maker_trading_pair?: string;
  taker_trading_pair?: string;
}

// Union type for all strategy configurations
export type StrategyConfig =
  | PMMStrategyConfig
  | DirectionalTradingConfig
  | AvellanedaConfig
  | CrossExchangeConfig
  | MarketMakingV2Config
  | GenericV2Config;

// Strategy parameter definition for dynamic form generation
export interface StrategyParameter {
  key: string;
  label: string;
  type: 'string' | 'number' | 'boolean' | 'select' | 'multiselect' | 'textarea';
  required?: boolean;
  default?: unknown;
  min?: number;
  max?: number;
  step?: number;
  options?: { value: string | number; label: string }[];
  description?: string;
  tooltip?: string;
  validation?: {
    pattern?: string;
    message?: string;
  };
}

// Strategy template definition
export interface StrategyTemplate {
  type: string;
  name: string;
  description: string;
  category: 'market_making' | 'directional_trading' | 'arbitrage' | 'other';
  parameters: StrategyParameter[];
  defaultValues: Partial<StrategyConfig>;
  examples?: {
    name: string;
    description: string;
    config: Partial<StrategyConfig>;
  }[];
}

// Strategy Validation Types
export interface ValidationRule {
  field: string;
  rule: 'required' | 'min' | 'max' | 'range';
  value?: number | string;
  min_value?: number;
  max_value?: number;
  message: string;
}

export interface ValidationResult {
  valid: boolean;
  errors: ValidationError[];
  warnings: ValidationWarning[];
}

export interface ValidationError {
  field: string;
  message: string;
  severity: 'error' | 'warning';
}

export interface ValidationWarning {
  field: string;
  message: string;
  suggestion?: string;
}

// Bot Instance Types
export interface BotInstance {
  id: string;
  name: string;
  status: 'running' | 'stopped' | 'error' | 'offline';
  strategies: string[];
  uptime: number;
  total_strategies: number;
  total_actions: number;
  actions_per_minute: number;
  last_activity: string;
  memory_usage: number;
  cpu_usage: number;
  api_port: number;
  user_main_address?: string; // Main wallet address for user filtering
}

// Dashboard Types
export interface DashboardMetrics {
  total_bots: number;
  active_bots: number;
  total_strategies: number;
  active_strategies: number;
  total_actions_24h: number;
  error_rate: number;
  uptime_percentage: number;
}

// Backtesting Types
export interface BacktestConfig {
  strategy: StrategyConfig;
  start_date: string;
  end_date: string;
  initial_balance: number;
  trading_pair: string;
}

export interface BacktestResult {
  config: BacktestConfig;
  total_return: number;
  max_drawdown: number;
  sharpe_ratio: number;
  win_rate: number;
  total_trades: number;
  profit_factor: number;
  daily_returns: Array<{ date: string; return: number; balance: number }>;
}

// Financial tracking types
export interface Trade {
  id: string;
  timestamp: string;
  strategy: string;
  hive_id: string;
  action: 'BUY' | 'SELL';
  symbol: string;
  price: number;
  amount: number;
  value: number;
  fee: number;
  pnl?: number;
  order_id: string;
}

export interface Position {
  symbol: string;
  strategy: string;
  hive_id: string;
  side: 'LONG' | 'SHORT' | 'NONE';
  size: number;
  entry_price: number;
  current_price: number;
  unrealized_pnl: number;
  realized_pnl: number;
  leverage: number;
  margin: number;
  last_updated: string;
}

export interface Portfolio {
  total_balance: number;
  available_balance: number;
  total_pnl: number;
  unrealized_pnl: number;
  realized_pnl: number;
  total_volume: number;
  positions: Position[];
  daily_pnl: number;
  win_rate: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  largest_win: number;
  largest_loss: number;
  // Additional Hummingbot-style metrics
  total_fees?: number;
  net_pnl?: number;
  position_value?: number;
  margin_used?: number;
  return_percentage?: number;
}

export interface StrategyPerformance {
  strategy: string;
  hive_id: string;
  total_pnl: number;
  unrealized_pnl: number;
  realized_pnl: number;
  total_volume: number;
  trade_count: number;
  win_rate: number;
  avg_trade_size: number;
  largest_win: number;
  largest_loss: number;
  sharpe_ratio?: number;
  max_drawdown?: number;
  // Additional metrics for enhanced performance tracking
  buy_count?: number;
  sell_count?: number;
  position_count?: number;
  position_value?: number;
  balance_score?: number;
}
