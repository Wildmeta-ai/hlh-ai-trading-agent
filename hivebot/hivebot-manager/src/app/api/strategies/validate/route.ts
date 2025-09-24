import { NextRequest, NextResponse } from 'next/server';
import { z } from 'zod';
import { StrategyConfig, ValidationResult, ValidationError, ValidationWarning } from '@/types';

// Base schema for all strategies
const BaseStrategySchema = z.object({
  name: z.string().min(1, "Strategy name is required").max(50, "Strategy name too long"),
  strategy_type: z.string().min(1, "Strategy type is required"),
  connector_type: z.string().min(1, "Connector type is required"),
  trading_pair: z.string().min(1, "Trading pair is required"), // Changed from trading_pairs array to singular string
  enabled: z.boolean().default(true),
});

// PMM-specific schema
const PMMStrategySchema = BaseStrategySchema.extend({
  strategy_type: z.literal("pure_market_making"),
  bid_spread: z.number().min(0.0001, "Bid spread must be positive").max(0.5, "Bid spread too high (>50%)"),
  ask_spread: z.number().min(0.0001, "Ask spread must be positive").max(0.5, "Ask spread too high (>50%)"),
  order_amount: z.number().min(0.001, "Order amount must be positive").max(100, "Order amount too large"),
  order_levels: z.number().int().min(1, "At least 1 order level required").max(10, "Too many order levels (>10)").optional().default(1),
  order_refresh_time: z.number().min(1, "Refresh time must be at least 1 second").max(3600, "Refresh time too long (>1 hour)").optional().default(30),
  leverage: z.number().int().min(1).max(100).optional(),
  position_mode: z.enum(["ONEWAY", "HEDGE"]).optional(),
});

// Directional Trading schema
const DirectionalTradingSchema = BaseStrategySchema.extend({
  strategy_type: z.literal("directional_trading"),
  controller_type: z.literal("directional_trading"),
  controller_name: z.string().min(1, "Controller name is required"),
  total_amount_quote: z.number().min(1, "Total amount must be positive").max(1000000, "Total amount too large"),
  leverage: z.number().int().min(1, "Leverage must be at least 1x").max(100, "Leverage too high (>100x)").optional().default(1),
  position_mode: z.enum(["ONEWAY", "HEDGE"]).optional().default("HEDGE"),

  // Technical indicator parameters (optional)
  bb_length: z.number().int().min(5, "BB length too small").max(200, "BB length too large").optional(),
  bb_long_threshold: z.number().min(0, "BB threshold must be >= 0").max(1, "BB threshold must be <= 1").optional(),
  bb_short_threshold: z.number().min(0, "BB threshold must be >= 0").max(1, "BB threshold must be <= 1").optional(),
  bb_std: z.number().min(0.5, "BB std too small").max(5, "BB std too large").optional(),

  // Risk management parameters (optional)
  stop_loss: z.union([z.string(), z.number()]).optional(),
  take_profit: z.union([z.string(), z.number()]).optional(),
  cooldown_time: z.number().int().min(0, "Cooldown time must be positive").optional(),
  time_limit: z.number().int().min(0, "Time limit must be positive").optional(),

  // DCA parameters (optional)
  dca_spreads: z.string().optional(),
  dca_amounts_pct: z.any().optional(), // Can be null or string
  max_executors_per_side: z.number().int().min(1, "At least 1 executor required").max(20, "Too many executors").optional(),

  // Advanced DMan V3 parameters (optional)
  trailing_stop: z.string().optional(),
  dynamic_order_spread: z.boolean().optional(),
  dynamic_target: z.boolean().optional(),
  activation_bounds: z.any().optional(), // Can be null or string
  take_profit_order_type: z.string().optional(),

  // Candle data parameters (optional)
  candles_connector: z.string().optional(),
  candles_trading_pair: z.string().optional(),
  interval: z.string().optional(),

  // User identification (optional)
  user_id: z.string().optional(),
});

// Market Making V2 schema
const MarketMakingV2Schema = BaseStrategySchema.extend({
  strategy_type: z.enum(["market_making", "pmm_dynamic", "pmm_simple"]),
  controller_type: z.literal("market_making"),
  controller_name: z.string().min(1, "Controller name is required"),
  total_amount_quote: z.number().min(1, "Total amount must be positive").max(1000000, "Total amount too large"),
  spread_multiplier: z.number().min(0.1, "Spread multiplier too small").max(10, "Spread multiplier too large").optional(),
  volatility_buffer_multiplier: z.number().min(0.1, "Volatility buffer too small").max(5, "Volatility buffer too large").optional(),
});

// Arbitrage schema
const ArbitrageSchema = BaseStrategySchema.extend({
  strategy_type: z.literal("arbitrage"),
  controller_type: z.literal("generic"),
  controller_name: z.literal("arbitrage_controller"),
  total_amount_quote: z.number().min(1, "Total amount must be positive").max(1000000, "Total amount too large"),
  min_profit_threshold: z.number().min(0.0001, "Minimum profit threshold too small").max(0.1, "Minimum profit threshold too large").optional(),
});

// Get appropriate schema based on strategy type
function getValidationSchema(strategyType: string) {
  switch (strategyType) {
    case 'pure_market_making':
      return PMMStrategySchema;
    case 'directional_trading':
      return DirectionalTradingSchema;
    case 'market_making':
    case 'pmm_dynamic':
    case 'pmm_simple':
      return MarketMakingV2Schema;
    case 'arbitrage':
      return ArbitrageSchema;
    default:
      // Fallback to base schema for unknown types
      return BaseStrategySchema;
  }
}

class StrategyValidator {
  private errors: ValidationError[] = [];
  private warnings: ValidationWarning[] = [];

  validate(config: StrategyConfig): ValidationResult {
    this.errors = [];
    this.warnings = [];

    // Get appropriate schema for strategy type
    const schema = getValidationSchema(config.strategy_type);

    // Schema validation
    try {
      schema.parse(config);
    } catch (error) {
      if (error instanceof z.ZodError) {
        this.errors.push(...error.errors.map(err => ({
          field: err.path.join('.'),
          message: err.message,
          severity: 'error' as const
        })));
      }
    }

    // Strategy-specific business logic validations
    if (config.strategy_type === 'pure_market_making') {
      this.validatePMMLogic(config as any);
    } else if (config.strategy_type === 'directional_trading') {
      this.validateDirectionalTradingLogic(config as any);
    } else if (['market_making', 'pmm_dynamic', 'pmm_simple'].includes(config.strategy_type)) {
      this.validateV2MarketMakingLogic(config as any);
    }

    // General validations for all strategy types
    this.validateTradingPairs(config);
    this.validateConnector(config);

    return {
      valid: this.errors.length === 0,
      errors: this.errors,
      warnings: this.warnings
    };
  }

  private validatePMMLogic(config: any) {
    // Check if spreads are reasonable for PMM
    if (config.bid_spread && config.bid_spread > 0.1) {
      this.warnings.push({
        field: 'bid_spread',
        message: 'High bid spread (>10%) may reduce fill rate',
        suggestion: 'Consider reducing to 1-5% for better performance'
      });
    }

    if (config.ask_spread && config.ask_spread > 0.1) {
      this.warnings.push({
        field: 'ask_spread',
        message: 'High ask spread (>10%) may reduce fill rate',
        suggestion: 'Consider reducing to 1-5% for better performance'
      });
    }

    // Check for asymmetric spreads
    if (config.bid_spread && config.ask_spread) {
      const spreadDiff = Math.abs(config.bid_spread - config.ask_spread);
      if (spreadDiff > 0.05) {
        this.warnings.push({
          field: 'spreads',
          message: 'Large difference between bid/ask spreads detected',
          suggestion: 'Consider using symmetric spreads for market making'
        });
      }
    }

    // Order refresh time validation for PMM
    if (config.order_refresh_time && config.order_refresh_time < 2) {
      this.warnings.push({
        field: 'order_refresh_time',
        message: 'Very fast refresh time may trigger rate limits',
        suggestion: 'Consider 2-5 seconds for stable operation'
      });
    }
  }

  private validateDirectionalTradingLogic(config: any) {
    // Validate controller name
    const validControllers = ['dman_v3', 'bollinger_v1', 'macd_bb_v1', 'supertrend_v1', 'ai_livestream'];
    if (config.controller_name && !validControllers.includes(config.controller_name)) {
      this.warnings.push({
        field: 'controller_name',
        message: `Unknown controller: ${config.controller_name}`,
        suggestion: `Consider using: ${validControllers.join(', ')}`
      });
    }

    // Leverage warnings
    if (config.leverage && config.leverage > 5) {
      this.warnings.push({
        field: 'leverage',
        message: 'High leverage (>5x) increases risk significantly',
        suggestion: 'Start with 1-3x leverage for safer trading'
      });
    }

    // Bollinger Bands logic validation
    if (config.bb_long_threshold && config.bb_short_threshold) {
      if (config.bb_long_threshold >= config.bb_short_threshold) {
        this.warnings.push({
          field: 'bb_thresholds',
          message: 'Long threshold should be less than short threshold',
          suggestion: 'Set bb_long_threshold < bb_short_threshold (e.g., 0.3 and 0.7)'
        });
      }
    }

    // Risk management validation
    if (config.stop_loss) {
      const stopLoss = typeof config.stop_loss === 'string' ? parseFloat(config.stop_loss) : config.stop_loss;
      if (stopLoss > 0.2) {
        this.warnings.push({
          field: 'stop_loss',
          message: 'Large stop loss (>20%) may result in significant losses',
          suggestion: 'Consider 5-15% stop loss for better risk management'
        });
      }
    }

    // DCA spreads validation
    if (config.dca_spreads) {
      const spreads = config.dca_spreads.split(',').map((s: string) => parseFloat(s.trim()));
      if (spreads.some((s: number) => isNaN(s) || s <= 0)) {
        this.errors.push({
          field: 'dca_spreads',
          message: 'Invalid DCA spreads format',
          severity: 'error'
        });
      } else if (spreads.length > 10) {
        this.warnings.push({
          field: 'dca_spreads',
          message: 'Too many DCA levels may complicate management',
          suggestion: 'Consider 2-5 DCA levels for optimal performance'
        });
      }
    }
  }

  private validateV2MarketMakingLogic(config: any) {
    // Validate total amount
    if (config.total_amount_quote < 100) {
      this.warnings.push({
        field: 'total_amount_quote',
        message: 'Small total amount may limit trading effectiveness',
        suggestion: 'Consider at least $100-500 for meaningful market making'
      });
    }

    // Validate spread multiplier
    if (config.spread_multiplier && config.spread_multiplier > 3) {
      this.warnings.push({
        field: 'spread_multiplier',
        message: 'High spread multiplier may reduce competitiveness',
        suggestion: 'Consider 1.0-2.0 for balanced performance'
      });
    }
  }

  private validateConnector(config: StrategyConfig) {
    // Connector-specific validations
    if (config.connector_type === 'hyperliquid_perpetual') {
      const validPairs = ['BTC-USD', 'ETH-USD', 'SOL-USD', 'HYPE-USDC', 'PURR-USDC'];
      if (!validPairs.includes(config.trading_pair)) {
        this.warnings.push({
          field: 'trading_pair',
          message: `${config.trading_pair} may not be available on Hyperliquid`,
          suggestion: `Consider using: ${validPairs.join(', ')}`
        });
      }
    }
  }


  private validateTradingPairs(config: StrategyConfig) {
    // Check trading pair format
    if (!config.trading_pair.includes('-') && !config.trading_pair.includes('/')) {
      this.errors.push({
        field: 'trading_pair',
        message: `Invalid trading pair format: ${config.trading_pair}`,
        severity: 'error'
      });
    }
  }

}

export async function POST(request: NextRequest) {
  try {
    const config: StrategyConfig = await request.json();

    const validator = new StrategyValidator();
    const result = validator.validate(config);

    return NextResponse.json(result);

  } catch (error) {
    console.error('Strategy validation error:', error);
    return NextResponse.json(
      {
        valid: false,
        errors: [{
          field: 'general',
          message: 'Failed to validate strategy configuration',
          severity: 'error' as const
        }],
        warnings: []
      },
      { status: 500 }
    );
  }
}
