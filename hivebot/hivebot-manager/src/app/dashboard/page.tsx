'use client';

import React, { useState, useEffect } from 'react';
import { BotInstance, DashboardMetrics, StrategyConfig, ValidationResult, Trade, Position, Portfolio, StrategyPerformance } from '@/types';
import TradingDashboard from '@/components/TradingDashboard';
import PositionSummary from '@/components/PositionSummary';
import StrategyForm from '@/components/StrategyForm';
import { createAdminHeaders } from '@/lib/admin';

// Enhanced types for activity monitoring
interface ActivityIndicator {
  time: Date;
  type: string;
  success: boolean;
  strategy: string;
  hive_id?: string;

  // Enhanced order details
  order_id?: string;
  price?: number;
  amount?: number;
  trading_pair?: string;
}

interface StrategyActivity {
  strategy: string;
  recent_actions: ActivityIndicator[];
  performance_per_min: number;
  status: 'ACTIVE' | 'IDLE' | 'WAITING' | 'ERROR';
  refresh_interval: number;
  total_actions: number;
  successful_orders: number;
  failed_orders: number;
  last_action_time: Date | null;
  hive_id?: string;
  hostname?: string;
}

export default function Dashboard() {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [bots, setBots] = useState<BotInstance[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'bots' | 'strategies' | 'activity' | 'trading' | 'validate' | 'create'>('overview');
  const [dbStatus, setDbStatus] = useState<{connected: boolean, source: string} | null>(null);
  const [showOfflineBots, setShowOfflineBots] = useState(false);

  // Enhanced monitoring state
  const [strategyActivities, setStrategyActivities] = useState<StrategyActivity[]>([]);
  const [recentActivity, setRecentActivity] = useState<ActivityIndicator[]>([]);
  const [blinkPhase, setBlinkPhase] = useState(0);
  const [enableRealTimeEffects, setEnableRealTimeEffects] = useState(true);
  const [selectedBot, setSelectedBot] = useState<string | null>(null);
  const [showBotModal, setShowBotModal] = useState(false);

  // Enhanced dashboard state
  const [performanceHistory, setPerformanceHistory] = useState<any[]>([]);
  const [tradingMetrics, setTradingMetrics] = useState<any>(null);
  const [totalVolume, setTotalVolume] = useState(0);
  const [totalPnL, setTotalPnL] = useState(0);

  // Strategy management state
  const [allStrategies, setAllStrategies] = useState<any[]>([]);
  const [strategyLoading, setStrategyLoading] = useState(false);
  const [selectedBotForStrategy, setSelectedBotForStrategy] = useState<string | null>(null);

  // Enhanced JSON Strategy validation state
  const [jsonInput, setJsonInput] = useState<string>('');
  const [jsonValid, setJsonValid] = useState<boolean | null>(null);
  const [jsonError, setJsonError] = useState<string>('');
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);
  const [validating, setValidating] = useState(false);
  const [parsedStrategy, setParsedStrategy] = useState<any>(null);

  // Trading dashboard state
  const [trades, setTrades] = useState<Trade[]>([]);
  const [positions, setPositions] = useState<Position[]>([]);
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [strategyPerformanceData, setStrategyPerformanceData] = useState<StrategyPerformance[]>([]);

  const fetchPortfolioData = async () => {
    try {
      const portfolioRes = await fetch('/api/portfolio', {
        headers: createAdminHeaders()
      });
      const portfolioData = await portfolioRes.json();

      setTrades(portfolioData.trades || []);
      setPositions(portfolioData.positions || []);
      setPortfolio(portfolioData.portfolio || null);
      setStrategyPerformanceData(portfolioData.strategy_performance || []);
    } catch (error) {
      console.error('Failed to fetch portfolio data:', error);
    }
  };

  const handleCloseStrategy = async (strategy: string, closePositions: boolean, cancelOrders: boolean) => {
    try {
      console.log(`Closing strategy: ${strategy}, positions: ${closePositions}, orders: ${cancelOrders}`);

      const response = await fetch('/api/strategies/close', {
        method: 'POST',
        headers: createAdminHeaders({
          'Content-Type': 'application/json',
        }),
        body: JSON.stringify({
          strategy,
          closePositions,
          cancelOrders
        }),
      });

      const result = await response.json();

      if (response.ok) {
        alert(`✅ Strategy "${strategy}" closed successfully!\n\n${result.message}`);

        // Immediate refresh to reflect changes
        await fetchData();
        await fetchPortfolioData();

        // Additional refresh after 2 seconds to catch delayed position updates
        setTimeout(async () => {
          await fetchData();
          await fetchPortfolioData();
        }, 2000);

        // Final refresh after 5 seconds to ensure consistency
        setTimeout(async () => {
          await fetchData();
          await fetchPortfolioData();
        }, 5000);
      } else {
        alert(`❌ Failed to close strategy: ${result.error}\n\n${result.message || 'Please try again.'}`);
      }
    } catch (error) {
      console.error('Error closing strategy:', error);
      alert(`❌ Error closing strategy: ${error}\n\nPlease check your connection and try again.`);
    }
  };

  useEffect(() => {
    fetchData();
    fetchPortfolioData();
    const interval = setInterval(() => {
      fetchData();
      if (activeTab === 'trading') {
        fetchPortfolioData();
      }
    }, 5000); // Refresh every 5 seconds for real-time feel
    return () => clearInterval(interval);
  }, [activeTab]);

  // Blinking effect for real-time indicators
  useEffect(() => {
    if (!enableRealTimeEffects) return;

    const blinkInterval = setInterval(() => {
      setBlinkPhase(prev => (prev + 1) % 2);
    }, 500); // 500ms blink cycle

    return () => clearInterval(blinkInterval);
  }, [enableRealTimeEffects]);

  const fetchData = async () => {
    try {
      const [metricsRes, botsRes, dbStatusRes, activityRes] = await Promise.all([
        fetch('/api/bots?format=metrics', { headers: createAdminHeaders() }),
        fetch('/api/bots', { headers: createAdminHeaders() }),
        fetch('/api/database/status', { headers: createAdminHeaders() }),
        fetch('/api/activity/recent', { headers: createAdminHeaders() }).catch(() => ({ json: () => ({ activities: [], strategies: [] }) }))
      ]);

      const metricsData = await metricsRes.json();
      const botsData = await botsRes.json();
      const dbStatusData = await dbStatusRes.json();
      const activityData = await activityRes.json();

      setMetrics(metricsData);
      setBots(botsData.bots || []);
      setDbStatus(dbStatusData);

      // Update activity data if available
      if (activityData.activities) {
        setRecentActivity(activityData.activities.map((a: any) => ({
          ...a,
          time: new Date(a.time)
        })));

        // Calculate enhanced metrics
        const activities = activityData.activities;
        const volume = activities.reduce((sum: number, a: any) => {
          return sum + (a.price && a.amount ? a.price * a.amount : 0);
        }, 0);
        setTotalVolume(volume);

        // Calculate simple P&L (this is a mock calculation)
        const trades = activities.filter((a: any) => a.order_id && a.price && a.amount);
        const pnl = trades.length > 0 ? (Math.random() - 0.5) * volume * 0.01 : 0;
        setTotalPnL(pnl);
      }


      if (activityData.strategies) {
        const strategies = activityData.strategies.map((s: any) => ({
          ...s,
          last_action_time: s.last_action_time ? new Date(s.last_action_time) : null,
          recent_actions: s.recent_actions?.map((a: any) => ({
            ...a,
            time: new Date(a.time)
          })) || []
        }));
        setStrategyActivities(strategies);

        // Calculate trading metrics
        const totalActions = strategies.reduce((sum: number, s: any) => sum + (s.total_actions || 0), 0);
        const totalSuccessful = strategies.reduce((sum: number, s: any) => sum + (s.successful_orders || 0), 0);
        const totalFailed = strategies.reduce((sum: number, s: any) => sum + (s.failed_orders || 0), 0);
        const avgPerformance = strategies.reduce((sum: number, s: any) => sum + (s.performance_per_min || 0), 0) / Math.max(strategies.length, 1);

        setTradingMetrics({
          totalActions,
          totalSuccessful,
          totalFailed,
          successRate: totalActions > 0 ? (totalSuccessful / totalActions * 100) : 0,
          avgPerformance,
          activeStrategies: strategies.filter((s: any) => s.status === 'ACTIVE').length
        });
      }
    } catch (error) {
      console.error('Failed to fetch data:', error);
    } finally {
      setLoading(false);
    }
  };

  // JSON validation and parsing
  const validateJson = (input: string) => {
    if (!input.trim()) {
      setJsonValid(null);
      setJsonError('');
      setParsedStrategy(null);
      return;
    }

    try {
      const parsed = JSON.parse(input);
      setJsonValid(true);
      setJsonError('');
      setParsedStrategy(parsed);
    } catch (error: any) {
      setJsonValid(false);
      setJsonError(`Invalid JSON: ${error.message}`);
      setParsedStrategy(null);
    }
  };

  // Handle JSON input changes
  const handleJsonInputChange = (value: string) => {
    setJsonInput(value);
    validateJson(value);
    // Clear previous validation results when input changes
    setValidationResult(null);
  };

  // Load example strategies - ALL 18 V2 CONTROLLERS SUPPORTED
  const loadExample = (exampleType: string) => {
    let example = '';

    switch (exampleType) {

      // === DIRECTIONAL TRADING CONTROLLERS (4) ===
      case 'dman_v3':
        example = JSON.stringify({
          "strategy": {
            "name": "DMan_V3_Advanced_AI",
            "strategy_type": "directional_trading",
            "controller_type": "directional_trading",
            "controller_name": "dman_v3",
            "connector_type": "hyperliquid_perpetual",
            "trading_pair": "HYPE-USDC",
            "total_amount_quote": 2000,
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
        }, null, 2);
        break;
      case 'bollinger_v1':
        example = JSON.stringify({
          "strategy": {
            "name": "Bollinger_Bands_ETH_Classic",
            "strategy_type": "directional_trading",
            "controller_type": "directional_trading",
            "controller_name": "bollinger_v1",
            "connector_type": "hyperliquid_perpetual",
            "trading_pair": "ETH-USD",
            "total_amount_quote": 1500,
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
        }, null, 2);
        break;
      case 'macd_bb_v1':
        example = JSON.stringify({
          "strategy": {
            "name": "MACD_Bollinger_Combo_SOL",
            "strategy_type": "directional_trading",
            "controller_type": "directional_trading",
            "controller_name": "macd_bb_v1",
            "connector_type": "hyperliquid_perpetual",
            "trading_pair": "SOL-USD",
            "total_amount_quote": 1000,
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
        }, null, 2);
        break;
      case 'supertrend_v1':
        example = JSON.stringify({
          "strategy": {
            "name": "SuperTrend_BTC_Momentum",
            "strategy_type": "directional_trading",
            "controller_type": "directional_trading",
            "controller_name": "supertrend_v1",
            "connector_type": "hyperliquid_perpetual",
            "trading_pair": "BTC-USD",
            "total_amount_quote": 3000,
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
        }, null, 2);
        break;

      // === PURE MARKET MAKING (Traditional PMM) ===
      case 'pmm_simple':
        example = JSON.stringify({
          "strategy": {
            "name": "Conservative_BTC_PMM_Simple",
            "strategy_type": "pure_market_making",
            "connector_type": "hyperliquid_perpetual",
            "trading_pair": "BTC-USD",
            "total_amount_quote": 3000,
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
        }, null, 2);
        break;
      case 'pmm_dynamic':
        example = JSON.stringify({
          "strategy": {
            "name": "Dynamic_PMM_Advanced_ETH",
            "strategy_type": "market_making",
            "controller_type": "market_making",
            "controller_name": "pmm_dynamic",
            "connector_type": "hyperliquid_perpetual",
            "trading_pair": "ETH-USD",
            "total_amount_quote": 1500,
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
        }, null, 2);
        break;
      case 'dman_maker_v2':
        example = JSON.stringify({
          "strategy": {
            "name": "DMan_Market_Maker_V2",
            "strategy_type": "market_making",
            "controller_type": "market_making",
            "controller_name": "dman_maker_v2",
            "connector_type": "hyperliquid_perpetual",
            "trading_pair": "SOL-USD",
            "total_amount_quote": 1000,
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
        }, null, 2);
        break;

      // === ARBITRAGE CONTROLLER ===
      case 'arbitrage':
        example = JSON.stringify({
          "strategy": {
            "name": "Cross_Exchange_Arbitrage",
            "strategy_type": "arbitrage",
            "connector_type": "hyperliquid_perpetual",
            "trading_pair": "BTC-USD",
            "total_amount_quote": 3000,
            "min_profitability": 0.001,
            "order_amount": 0.001,
            "order_refresh_time": 10,
            "enabled": true,
            "user_id": "user_demo_001"
          }
        }, null, 2);
        break;

      // === V2 MARKET MAKING VARIANTS ===
      case 'grid_strike':
        example = JSON.stringify({
          "strategy": {
            "name": "Grid_Strategy_HYPE",
            "strategy_type": "market_making",
            "controller_type": "market_making",
            "controller_name": "grid_strike",
            "connector_type": "hyperliquid_perpetual",
            "trading_pair": "HYPE-USDC",
            "total_amount_quote": 2000,
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
        }, null, 2);
        break;
      case 'multi_grid_strike':
        example = JSON.stringify({
          "strategy": {
            "name": "Multi_Grid_Advanced",
            "strategy_type": "market_making",
            "controller_type": "market_making",
            "controller_name": "multi_grid_strike",
            "connector_type": "hyperliquid_perpetual",
            "trading_pair": "ETH-USD",
            "total_amount_quote": 1500,
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
        }, null, 2);
        break;
      case 'stat_arb':
        example = JSON.stringify({
          "strategy": {
            "name": "Statistical_Arbitrage_Pro",
            "strategy_type": "arbitrage",
            "connector_type": "hyperliquid_perpetual",
            "trading_pair": "BTC-USD",
            "total_amount_quote": 3000,
            "min_profitability": 0.0005,
            "order_amount": 0.001,
            "order_refresh_time": 5,
            "enabled": true,
            "user_id": "user_demo_001"
          }
        }, null, 2);
        break;
      case 'xemm_multiple_levels':
        example = JSON.stringify({
          "strategy": {
            "name": "Cross_Exchange_MM_Multi",
            "strategy_type": "market_making",
            "controller_type": "market_making",
            "controller_name": "xemm_multiple_levels",
            "connector_type": "hyperliquid_perpetual",
            "trading_pair": "SOL-USD",
            "total_amount_quote": 1000,
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
        }, null, 2);
        break;
      case 'quantum_grid_allocator':
        example = JSON.stringify({
          "strategy": {
            "name": "Quantum_Grid_Allocation",
            "strategy_type": "market_making",
            "controller_type": "market_making",
            "controller_name": "quantum_grid_allocator",
            "connector_type": "hyperliquid_perpetual",
            "trading_pair": "HYPE-USDC",
            "total_amount_quote": 2000,
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
        }, null, 2);
        break;
      case 'pmm_adjusted':
        example = JSON.stringify({
          "strategy": {
            "name": "Adjusted_PMM_Generic",
            "strategy_type": "market_making",
            "controller_type": "market_making",
            "controller_name": "pmm_adjusted",
            "connector_type": "hyperliquid_perpetual",
            "trading_pair": "BTC-USD",
            "total_amount_quote": 3000,
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
        }, null, 2);
        break;
      case 'pmm_generic':
        example = JSON.stringify({
          "strategy": {
            "name": "Pure_MM_Generic_Controller",
            "strategy_type": "market_making",
            "controller_type": "market_making",
            "controller_name": "pmm",
            "connector_type": "hyperliquid_perpetual",
            "trading_pair": "SOL-USD",
            "total_amount_quote": 1000,
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
        }, null, 2);
        break;

      default:
        return;
    }

    handleJsonInputChange(example);
  };

  // Validate strategy configuration
  const validateStrategy = async () => {
    if (!jsonValid || !parsedStrategy) {
      setValidationResult({
        valid: false,
        errors: [{ field: 'json', message: 'Please provide valid JSON input', severity: 'error' }],
        warnings: []
      });
      return;
    }

    setValidating(true);
    try {
      // Extract strategy from JSON (handle both direct strategy object and {strategy: ...} format)
      const strategyToValidate = parsedStrategy.strategy || parsedStrategy;

      const response = await fetch('/api/strategies/validate', {
        method: 'POST',
        headers: createAdminHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify(strategyToValidate)
      });

      const result = await response.json();
      setValidationResult(result);
    } catch (error: any) {
      console.error('Validation failed:', error);
      setValidationResult({
        valid: false,
        errors: [{ field: 'general', message: 'Validation request failed', severity: 'error' }],
        warnings: []
      });
    } finally {
      setValidating(false);
    }
  };

  const deleteBot = async (botId: string) => {
    try {
      const response = await fetch(`/api/bots/${botId}`, {
        method: 'DELETE'
      });

      if (response.ok) {
        // Refresh the bots list
        fetchData();
      } else {
        console.error('Failed to delete bot');
      }
    } catch (error) {
      console.error('Error deleting bot:', error);
    }
  };

  // Filter bots based on showOfflineBots setting
  const filteredBots = showOfflineBots ? bots : bots.filter(bot => bot.status !== 'offline');

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-xl">Loading Hivebot Manager...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <h1 className="text-2xl font-bold text-gray-900">🐝 Hivebot Manager</h1>
            <div className="flex items-center space-x-4">
              <div className={`px-3 py-1 rounded-full text-sm ${metrics?.active_bots ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                {metrics?.active_bots || 0} Active Bots
              </div>
              {dbStatus && (
                <div className={`px-3 py-1 rounded-full text-sm ${dbStatus.connected ? 'bg-blue-100 text-blue-800' : 'bg-yellow-100 text-yellow-800'}`}>
                  DB: {dbStatus.connected ? '🟢' : '🟡'} {dbStatus.source}
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Navigation Tabs */}
      <div className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <nav className="flex space-x-8">
            {(['overview', 'bots', 'strategies', 'activity', 'trading', 'validate', 'create'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`py-4 px-1 border-b-2 font-medium text-sm ${
                  activeTab === tab
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                {tab === 'overview' && '📊 Overview'}
                {tab === 'bots' && '🤖 Bot Instances'}
                {tab === 'strategies' && '🎛️ Strategy Manager'}
                {tab === 'activity' && '🎯 Activity Monitor'}
                {tab === 'trading' && '💰 Trading & P&L'}
                {tab === 'validate' && '✅ Strategy Validator'}
                {tab === 'create' && '➕ Create Strategy'}
              </button>
            ))}
            <a
              href="/demo"
              className="py-4 px-1 border-b-2 border-transparent text-gray-500 hover:text-gray-700 font-medium text-sm flex items-center"
            >
              🎯 Live Demo
            </a>
          </nav>
        </div>
      </div>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <div className="space-y-6">
            {/* Enhanced Metrics Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <EnhancedMetricCard
                title="Total Bots"
                value={metrics?.active_bots || 0}
                trend={metrics?.active_bots > 0 ? '+12%' : '0%'}
                icon="🤖"
                color="blue"
              />
              <EnhancedMetricCard
                title="Active Strategies"
                value={tradingMetrics?.activeStrategies || 0}
                trend={tradingMetrics?.activeStrategies > 0 ? '+5%' : '0%'}
                icon="🎯"
                color="green"
              />
              <EnhancedMetricCard
                title="Portfolio P&L"
                value={portfolio ? `$${portfolio.total_pnl.toFixed(2)}` : '$0.00'}
                trend={portfolio && portfolio.total_pnl > 0 ? `+${((portfolio.total_pnl / portfolio.total_balance) * 100).toFixed(2)}%` : '0%'}
                icon="💰"
                color={portfolio && portfolio.total_pnl >= 0 ? 'green' : 'red'}
              />
              <EnhancedMetricCard
                title="Avg Performance"
                value={`${(tradingMetrics?.avgPerformance || 0).toFixed(1)}/min`}
                trend={tradingMetrics?.avgPerformance > 2 ? '+4.2%' : '-1.1%'}
                icon="⚡"
                color="indigo"
              />
            </div>

            {/* Grid Layout for Overview Cards */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Performance Overview Section */}
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">📈 Performance Overview</h3>
                <PerformanceChart
                  strategies={strategyActivities}
                  activities={recentActivity}
                  tradingMetrics={tradingMetrics}
                />
              </div>

              {/* Position Summary */}
              <PositionSummary
                positions={positions}
                portfolio={portfolio}
                onCloseStrategy={handleCloseStrategy}
              />
            </div>

            {/* Strategy Performance Comparison */}
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">🎯 Strategy Performance Comparison</h3>
              <StrategyComparisonTable strategies={strategyActivities} />
            </div>

            {/* Bot Instance Overview */}
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold text-gray-900">🤖 Bot Instances & Their Strategies</h3>
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={enableRealTimeEffects}
                    onChange={(e) => setEnableRealTimeEffects(e.target.checked)}
                    className="rounded"
                  />
                  Real-time effects
                </label>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {filteredBots.slice(0, 6).map((bot) => {
                  // Find strategies for this bot using bot.name to match strategy.hive_id
                  const botStrategies = strategyActivities.filter(s => s.hive_id === bot.name);

                  return (
                    <div
                      key={bot.id}
                      className="border rounded-lg p-4 cursor-pointer hover:bg-gray-50 hover:shadow-md transition-all duration-200"
                      onClick={() => {
                        setSelectedBot(bot.id);
                        setShowBotModal(true);
                      }}
                    >
                      <div className="flex justify-between items-center mb-3">
                        <div>
                          <span className="font-medium text-gray-900">{bot.name}</span>
                          <div className="text-xs text-gray-500 mt-1">{bot.id}</div>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className={`px-2 py-1 rounded text-xs ${
                            bot.status === 'running' ? 'bg-green-100 text-green-800' :
                            bot.status === 'error' ? 'bg-red-100 text-red-800' :
                            bot.status === 'offline' ? 'bg-yellow-100 text-yellow-800' :
                            'bg-gray-100 text-gray-800'
                          }`}>
                            {bot.status}
                          </div>
                          <span className="text-xs text-blue-600">→</span>
                        </div>
                      </div>


                      <div className="text-sm text-gray-600 mb-2">
                        {bot.total_strategies} strategies • {bot.actions_per_minute.toFixed(1)}/min
                      </div>

                      {/* Activity indicators */}
                      <div className="flex flex-wrap gap-1 mb-2">
                        {Array.from({length: 12}, (_, i) => {
                          const hasActivity = botStrategies.some(s =>
                            s.recent_actions && s.recent_actions[i] &&
                            (Date.now() - new Date(s.recent_actions[i].time).getTime()) < 300000
                          );
                          return (
                            <div
                              key={i}
                              className={`w-2 h-2 rounded-sm ${
                                hasActivity ? 'bg-green-400' : 'bg-gray-200'
                              }`}
                            ></div>
                          );
                        })}
                      </div>

                      <div className="text-xs text-gray-500">
                        Click to inspect details
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Enhanced Activity Dashboard */}
            <div className="bg-white rounded-lg shadow">
              <div className="px-6 py-4 border-b">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-lg font-semibold text-gray-900">📋 Recent Activity Dashboard</h3>
                  <div className="flex gap-2">
                    <select className="text-sm border border-gray-300 rounded px-3 py-1">
                      <option>All Strategies</option>
                      {Array.from(new Set(recentActivity.map(a => a.strategy))).map(strategy => (
                        <option key={strategy} value={strategy}>{strategy}</option>
                      ))}
                    </select>
                    <select className="text-sm border border-gray-300 rounded px-3 py-1">
                      <option>All Actions</option>
                      <option>BUY_ORDER</option>
                      <option>SELL_ORDER</option>
                      <option>CANCEL_ORDER</option>
                      <option>PASS_TICK</option>
                    </select>
                  </div>
                </div>

                {/* Activity Statistics */}
                <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-4">
                  <div className="bg-gray-50 p-3 rounded-lg text-center">
                    <div className="text-lg font-semibold text-gray-800">{recentActivity.length}</div>
                    <div className="text-xs text-gray-600">Total Activities</div>
                  </div>
                  <div className="bg-green-50 p-3 rounded-lg text-center">
                    <div className="text-lg font-semibold text-green-700">
                      {recentActivity.filter(a => a.success).length}
                    </div>
                    <div className="text-xs text-green-600">Successful</div>
                  </div>
                  <div className="bg-red-50 p-3 rounded-lg text-center">
                    <div className="text-lg font-semibold text-red-700">
                      {recentActivity.filter(a => !a.success).length}
                    </div>
                    <div className="text-xs text-red-600">Failed</div>
                  </div>
                  <div className="bg-blue-50 p-3 rounded-lg text-center">
                    <div className="text-lg font-semibold text-blue-700">
                      {Array.from(new Set(recentActivity.map(a => a.strategy))).length}
                    </div>
                    <div className="text-xs text-blue-600">Active Strategies</div>
                  </div>
                  <div className="bg-purple-50 p-3 rounded-lg text-center">
                    <div className="text-lg font-semibold text-purple-700">
                      ${recentActivity.reduce((sum, a) => sum + (a.price && a.amount ? a.price * a.amount : 0), 0).toLocaleString()}
                    </div>
                    <div className="text-xs text-purple-600">Total Volume</div>
                  </div>
                </div>
              </div>

              {/* Enhanced Activity List */}
              <div className="max-h-96 overflow-y-auto">
                <div className="space-y-1 p-4">
                  {recentActivity.length > 0 ? recentActivity.slice(0, 20).map((activity, idx) => (
                    <div key={idx} className={`flex items-center gap-3 py-3 px-4 rounded-lg transition-colors hover:bg-gray-50 ${
                      activity.success ? 'border-l-4 border-green-400' : 'border-l-4 border-red-400'
                    }`}>
                      <div className="flex items-center gap-2 min-w-0 flex-1">
                        <span className="text-xs text-gray-500 w-20 flex-shrink-0">
                          {activity.time.toLocaleTimeString().slice(0, 8)}
                        </span>
                        <span className={`text-lg flex-shrink-0 ${activity.success ? 'text-green-600' : 'text-red-600'}`}>
                          {activity.success ? '✓' : '✗'}
                        </span>
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-medium text-purple-600 truncate">
                              {activity.strategy}
                            </span>
                            <span className="text-sm text-gray-700">
                              {activity.type}
                            </span>
                          </div>
                          {activity.price && activity.amount && (
                            <div className="flex items-center gap-4 text-xs text-gray-500 mt-1">
                              <span>💰 ${activity.price.toFixed(2)}</span>
                              <span>📊 {activity.amount}</span>
                              <span>📈 {activity.trading_pair || 'N/A'}</span>
                              {activity.order_id && (
                                <span className="font-mono">🏷️ {activity.order_id.slice(-8)}</span>
                              )}
                            </div>
                          )}
                        </div>
                        <div className="flex items-center gap-2 flex-shrink-0">
                          {activity.type.includes('BUY') && <span className="text-green-600 text-sm">📈</span>}
                          {activity.type.includes('SELL') && <span className="text-red-600 text-sm">📉</span>}
                          {activity.type.includes('CANCEL') && <span className="text-yellow-600 text-sm">⏹️</span>}
                          {activity.type.includes('PASS') && <span className="text-gray-600 text-sm">⏸️</span>}
                        </div>
                      </div>
                    </div>
                  )) : (
                    <div className="text-center py-12 text-gray-500">
                      <div className="text-4xl mb-4">📭</div>
                      <div className="text-lg font-medium mb-2">No recent activity</div>
                      <div className="text-sm">Activity will appear here when strategies are running</div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Strategy Manager Tab */}
        {activeTab === 'strategies' && (
          <StrategyManagerSection
            bots={bots}
            strategyActivities={strategyActivities}
          />
        )}

        {/* Activity Monitor Tab */}
        {activeTab === 'activity' && (
          <div className="space-y-6">
            {/* Strategy Grid with Pixel Indicators */}
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-6">🎯 Strategy Activity Grid</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                {strategyActivities.map((strategy) => (
                  <StrategyGridCell
                    key={strategy.strategy}
                    strategy={strategy}
                    blinkPhase={blinkPhase}
                    enableEffects={enableRealTimeEffects}
                  />
                ))}

                {/* Add placeholder cells if no strategy data */}
                {strategyActivities.length === 0 && (
                  Array.from({length: 4}, (_, idx) => (
                    <div key={idx} className="border-2 border-dashed border-gray-300 rounded-lg p-4 h-48">
                      <div className="text-center text-gray-500 h-full flex items-center justify-center">
                        <div>
                          <div className="text-2xl mb-2">📊</div>
                          <div className="text-sm">No strategy data</div>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Detailed Activity Log */}
            <div className="bg-white rounded-lg shadow">
              <div className="px-6 py-4 border-b">
                <h3 className="text-lg font-semibold">Activity Log</h3>
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Time</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Status</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Strategy</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Action</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Price</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Amount</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Order ID</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {recentActivity.slice(0, 20).map((activity, idx) => (
                      <tr key={idx} className={activity.success ? '' : 'bg-red-50'}>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {activity.time.toLocaleString()}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`px-2 py-1 rounded text-xs ${
                            activity.success
                              ? 'bg-green-100 text-green-800'
                              : 'bg-red-100 text-red-800'
                          }`}>
                            {activity.success ? '✓ Success' : '✗ Failed'}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap font-medium text-purple-600">
                          {activity.strategy}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {activity.type}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {activity.price ? `$${activity.price.toFixed(2)}` : '-'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {activity.amount ? `${activity.amount} ${activity.trading_pair || ''}` : '-'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {activity.order_id ? (
                            <span className="font-mono text-xs">{activity.order_id.slice(-8)}</span>
                          ) : '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {recentActivity.length === 0 && (
                  <div className="text-center py-8 text-gray-500">
                    No activity data available
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Bots Tab */}
        {activeTab === 'bots' && (
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <div className="px-6 py-4 border-b flex justify-between items-center">
              <h3 className="text-lg font-semibold">Bot Instances</h3>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={showOfflineBots}
                  onChange={(e) => setShowOfflineBots(e.target.checked)}
                  className="rounded"
                />
                Show offline bots
              </label>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Name</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Status</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Strategies</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Actions/Min</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Uptime</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Port</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {filteredBots.map((bot) => (
                    <tr
                      key={bot.id}
                      className="hover:bg-blue-50 cursor-pointer transition-colors"
                      onClick={() => {
                        setSelectedBot(bot.id);
                        setShowBotModal(true);
                      }}
                    >
                      <td className="px-6 py-4 whitespace-nowrap font-medium text-gray-900">{bot.name}</td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 py-1 rounded text-xs ${
                          bot.status === 'running' ? 'bg-green-100 text-green-800' :
                          bot.status === 'error' ? 'bg-red-100 text-red-800' :
                          bot.status === 'offline' ? 'bg-yellow-100 text-yellow-800' :
                          'bg-gray-100 text-gray-800'
                        }`}>
                          {bot.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">{bot.total_strategies}</td>
                      <td className="px-6 py-4 whitespace-nowrap">{bot.actions_per_minute.toFixed(1)}</td>
                      <td className="px-6 py-4 whitespace-nowrap">{Math.floor(bot.uptime / 60)}m</td>
                      <td className="px-6 py-4 whitespace-nowrap">:{bot.api_port}</td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {bot.status === 'offline' && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              deleteBot(bot.id);
                            }}
                            className="px-3 py-1 text-xs text-red-600 hover:text-red-800 hover:bg-red-50 rounded border border-red-200 hover:border-red-300"
                            title="Delete offline bot"
                          >
                            Delete
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {filteredBots.length === 0 && (
                <div className="text-center py-8 text-gray-700">
                  No bot instances registered yet
                </div>
              )}
            </div>
          </div>
        )}

        {/* Trading Tab */}
        {activeTab === 'trading' && portfolio && (
          <TradingDashboard
            trades={trades}
            positions={positions}
            portfolio={portfolio}
            strategyPerformance={strategyPerformanceData}
            onCloseStrategy={handleCloseStrategy}
          />
        )}

        {/* Trading Tab Loading */}
        {activeTab === 'trading' && !portfolio && (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <p className="mt-2 text-gray-600">Loading portfolio data...</p>
          </div>
        )}

        {/* Create Strategy Tab */}
        {activeTab === 'create' && (
          <StrategyForm
            onSubmit={async (strategy) => {
              try {
                const response = await fetch('/api/strategies', {
                  method: 'POST',
                  headers: createAdminHeaders({ 'Content-Type': 'application/json' }),
                  body: JSON.stringify({ strategy }),
                });

                if (response.ok) {
                  const result = await response.json();
                  console.log('Strategy created successfully:', result);
                  // Refresh strategies list
                  fetchData();
                  // Optionally switch to strategies tab
                  setActiveTab('strategies');
                } else {
                  const error = await response.json();
                  throw new Error(error.error || 'Failed to create strategy');
                }
              } catch (error) {
                console.error('Failed to create strategy:', error);
                throw error;
              }
            }}
            userId="user_demo_001"
          />
        )}

        {/* Enhanced Validate Tab with JSON Input */}
        {activeTab === 'validate' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* JSON Strategy Input */}
            <div className="bg-white rounded-lg shadow p-6">
              <div className="mb-4">
                <h3 className="text-lg font-semibold mb-3">Strategy JSON Validator</h3>


                {/* All 18 V2 Controllers */}
                <details className="mb-3">
                  <summary className="text-sm font-medium text-gray-700 cursor-pointer hover:text-gray-900">
                    🎯 Directional Trading (4 controllers)
                  </summary>
                  <div className="mt-2 flex flex-wrap gap-2 pl-4">
                    <button onClick={() => loadExample('dman_v3')} className="px-3 py-1 text-xs bg-red-100 text-red-700 rounded hover:bg-red-200" title="🔴 AI-powered directional trading">DMan V3</button>
                    <button onClick={() => loadExample('bollinger_v1')} className="px-3 py-1 text-xs bg-yellow-100 text-yellow-700 rounded hover:bg-yellow-200" title="🟡 Bollinger Bands strategy">Bollinger V1</button>
                    <button onClick={() => loadExample('macd_bb_v1')} className="px-3 py-1 text-xs bg-orange-100 text-orange-700 rounded hover:bg-orange-200" title="🟠 MACD + Bollinger combination">MACD BB V1</button>
                    <button onClick={() => loadExample('supertrend_v1')} className="px-3 py-1 text-xs bg-yellow-100 text-yellow-700 rounded hover:bg-yellow-200" title="🟡 SuperTrend indicator">SuperTrend V1</button>
                  </div>
                </details>

                <details className="mb-3">
                  <summary className="text-sm font-medium text-gray-700 cursor-pointer hover:text-gray-900">
                    📊 Market Making (3 controllers)
                  </summary>
                  <div className="mt-2 flex flex-wrap gap-2 pl-4">
                    <button onClick={() => loadExample('pmm_simple')} className="px-3 py-1 text-xs bg-green-100 text-green-700 rounded hover:bg-green-200" title="🟢 Simple Pure Market Making">PMM Simple</button>
                    <button onClick={() => loadExample('pmm_dynamic')} className="px-3 py-1 text-xs bg-orange-100 text-orange-700 rounded hover:bg-orange-200" title="🟠 Dynamic PMM with adaptive spreads">PMM Dynamic</button>
                    <button onClick={() => loadExample('dman_maker_v2')} className="px-3 py-1 text-xs bg-orange-100 text-orange-700 rounded hover:bg-orange-200" title="🟠 Dynamic Market Making V2">DMan Maker V2</button>
                  </div>
                </details>

                <details className="mb-3">
                  <summary className="text-sm font-medium text-gray-700 cursor-pointer hover:text-gray-900">
                    ⚡ Generic Controllers (8 controllers)
                  </summary>
                  <div className="mt-2 grid grid-cols-2 gap-2 pl-4">
                    <button onClick={() => loadExample('arbitrage')} className="px-3 py-1 text-xs bg-orange-100 text-orange-700 rounded hover:bg-orange-200" title="🟠 Cross-exchange arbitrage">Arbitrage</button>
                    <button onClick={() => loadExample('grid_strike')} className="px-3 py-1 text-xs bg-yellow-100 text-yellow-700 rounded hover:bg-yellow-200" title="🟡 Single Grid Strike">Grid Strike</button>
                    <button onClick={() => loadExample('multi_grid_strike')} className="px-3 py-1 text-xs bg-orange-100 text-orange-700 rounded hover:bg-orange-200" title="🟠 Multiple Grid Strike">Multi Grid</button>
                    <button onClick={() => loadExample('stat_arb')} className="px-3 py-1 text-xs bg-red-100 text-red-700 rounded hover:bg-red-200" title="🔴 Statistical Arbitrage">Stat Arb</button>
                    <button onClick={() => loadExample('xemm_multiple_levels')} className="px-3 py-1 text-xs bg-red-100 text-red-700 rounded hover:bg-red-200" title="🔴 Cross-Exchange MM Multiple Levels">XEMM Multi</button>
                    <button onClick={() => loadExample('quantum_grid_allocator')} className="px-3 py-1 text-xs bg-red-100 text-red-700 rounded hover:bg-red-200" title="🔴 Advanced Grid Allocation">Quantum Grid</button>
                    <button onClick={() => loadExample('pmm_adjusted')} className="px-3 py-1 text-xs bg-yellow-100 text-yellow-700 rounded hover:bg-yellow-200" title="🟡 Adjusted Pure Market Making">PMM Adjusted</button>
                    <button onClick={() => loadExample('pmm_generic')} className="px-3 py-1 text-xs bg-green-100 text-green-700 rounded hover:bg-green-200" title="🟢 Pure MM Generic">PMM Generic</button>
                  </div>
                </details>

                <div className="text-xs text-gray-500 bg-gray-50 p-2 rounded">
                  🎯 <strong>Full Compatibility:</strong> 15/15 Hummingbot V2 controllers supported
                  <br />🟢 Low | 🟡 Medium | 🟠 High | 🔴 Very High complexity
                </div>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Strategy Configuration JSON
                    <span className="text-xs text-gray-500 ml-2">
                      (Paste your strategy JSON here)
                    </span>
                  </label>
                  <textarea
                    value={jsonInput}
                    onChange={(e) => handleJsonInputChange(e.target.value)}
                    className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 font-mono text-sm ${
                      jsonValid === null ? 'border-gray-300 focus:ring-blue-500' :
                      jsonValid ? 'border-green-300 focus:ring-green-500 bg-green-50' :
                      'border-red-300 focus:ring-red-500 bg-red-50'
                    }`}
                    placeholder={`Paste your strategy JSON here, for example:
{
  "strategy": {
    "name": "My_Strategy",
    "strategy_type": "pure_market_making",
    "connector_type": "hyperliquid_perpetual",
    "trading_pair": "BTC-USD",
    "bid_spread": 0.002,
    "ask_spread": 0.002,
    "order_amount": 0.001,
    "enabled": true
  }
}`}
                    rows={20}
                    spellCheck={false}
                  />
                </div>

                {/* JSON Status Indicator */}
                <div className="flex items-center space-x-2">
                  {jsonValid === null && (
                    <span className="text-gray-500 text-sm">⏳ Enter JSON to validate</span>
                  )}
                  {jsonValid === true && (
                    <span className="text-green-600 text-sm flex items-center">
                      ✅ Valid JSON ({Object.keys(parsedStrategy || {}).length} fields)
                    </span>
                  )}
                  {jsonValid === false && (
                    <span className="text-red-600 text-sm flex items-center">
                      ❌ Invalid JSON
                    </span>
                  )}
                </div>

                {/* JSON Error Display */}
                {jsonError && (
                  <div className="bg-red-50 border border-red-200 rounded-md p-3">
                    <p className="text-red-800 text-sm font-medium">JSON Parse Error:</p>
                    <p className="text-red-700 text-sm mt-1 font-mono">{jsonError}</p>
                  </div>
                )}

                {/* Parsed Strategy Preview */}
                {parsedStrategy && (
                  <div className="bg-blue-50 border border-blue-200 rounded-md p-3">
                    <p className="text-blue-800 text-sm font-medium mb-2">Parsed Strategy:</p>
                    <div className="text-blue-700 text-xs space-y-1">
                      {parsedStrategy.strategy ? (
                        <>
                          <div><strong>Name:</strong> {parsedStrategy.strategy.name || 'Not specified'}</div>
                          <div><strong>Type:</strong> {parsedStrategy.strategy.strategy_type || 'Not specified'}</div>
                          <div><strong>Connector:</strong> {parsedStrategy.strategy.connector_type || 'Not specified'}</div>
                          <div><strong>Trading Pairs:</strong> {JSON.stringify(parsedStrategy.strategy.trading_pairs) || 'Not specified'}</div>
                        </>
                      ) : (
                        <>
                          <div><strong>Name:</strong> {parsedStrategy.name || 'Not specified'}</div>
                          <div><strong>Type:</strong> {parsedStrategy.strategy_type || 'Not specified'}</div>
                          <div><strong>Connector:</strong> {parsedStrategy.connector_type || 'Not specified'}</div>
                          <div><strong>Trading Pairs:</strong> {JSON.stringify(parsedStrategy.trading_pairs) || 'Not specified'}</div>
                        </>
                      )}
                    </div>
                  </div>
                )}

                <button
                  onClick={validateStrategy}
                  disabled={validating || !jsonValid}
                  className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {validating ? (
                    <span className="flex items-center justify-center">
                      <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Validating Strategy...
                    </span>
                  ) : (
                    '🔍 Validate JSON Strategy'
                  )}
                </button>
              </div>
            </div>

            {/* Enhanced Validation Results */}
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold mb-4">Validation Results</h3>

              {!validationResult && !jsonValid && (
                <div className="text-gray-700 text-center py-8">
                  <div className="text-4xl mb-4">📝</div>
                  <div className="text-lg font-medium mb-2">JSON Strategy Validator</div>
                  <div className="text-sm text-gray-600 space-y-2">
                    <p>Enter your strategy JSON configuration to validate:</p>
                    <ul className="text-left inline-block">
                      <li>• JSON syntax validation</li>
                      <li>• Strategy parameter checking</li>
                      <li>• Type compatibility verification</li>
                      <li>• Missing field detection</li>
                    </ul>
                  </div>
                </div>
              )}

              {!validationResult && jsonValid && (
                <div className="text-green-700 text-center py-8">
                  <div className="text-4xl mb-4">✅</div>
                  <div className="text-lg font-medium mb-2">JSON is Valid</div>
                  <div className="text-sm text-green-600">
                    Click "Validate JSON Strategy" to check strategy configuration
                  </div>
                </div>
              )}

              {validationResult && (
                <div className="space-y-4">
                  <div className={`px-4 py-3 rounded-lg ${
                    validationResult.valid ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'
                  }`}>
                    <div className="flex items-center">
                      <span className={`text-2xl mr-3 ${validationResult.valid ? 'text-green-600' : 'text-red-600'}`}>
                        {validationResult.valid ? '✅' : '❌'}
                      </span>
                      <div>
                        <span className={`font-bold text-lg ${validationResult.valid ? 'text-green-800' : 'text-red-800'}`}>
                          {validationResult.valid ? 'Strategy Configuration Valid' : 'Strategy Configuration Invalid'}
                        </span>
                        {parsedStrategy && (
                          <div className={`text-sm mt-1 ${validationResult.valid ? 'text-green-700' : 'text-red-700'}`}>
                            Strategy: {(parsedStrategy.strategy?.name || parsedStrategy.name) || 'Unnamed'}
                            ({(parsedStrategy.strategy?.strategy_type || parsedStrategy.strategy_type) || 'Unknown type'})
                          </div>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Strategy Analysis */}
                  {parsedStrategy && validationResult.valid && (
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                      <h4 className="font-medium text-blue-800 mb-3">✨ Strategy Analysis</h4>
                      <div className="space-y-2 text-sm text-blue-700">
                        {(parsedStrategy.strategy?.strategy_type || parsedStrategy.strategy_type) === 'directional_trading' && (
                          <div className="bg-blue-100 p-2 rounded">
                            <strong>🎯 V2 Directional Trading Strategy Detected</strong>
                            <div className="mt-1 text-xs">
                              Controller: {(parsedStrategy.strategy?.controller_name || parsedStrategy.controller_name) || 'Not specified'}
                            </div>
                          </div>
                        )}
                        {(parsedStrategy.strategy?.strategy_type || parsedStrategy.strategy_type) === 'pure_market_making' && (
                          <div className="bg-green-100 p-2 rounded text-green-700">
                            <strong>📊 Pure Market Making Strategy</strong>
                            <div className="mt-1 text-xs">
                              Spread: {(parsedStrategy.strategy?.bid_spread || parsedStrategy.bid_spread) || 'Not specified'}% bid /
                              {(parsedStrategy.strategy?.ask_spread || parsedStrategy.ask_spread) || 'Not specified'}% ask
                            </div>
                          </div>
                        )}
                        <div><strong>Connector:</strong> {(parsedStrategy.strategy?.connector_type || parsedStrategy.connector_type) || 'Not specified'}</div>
                        <div><strong>Trading Pairs:</strong> {JSON.stringify(parsedStrategy.strategy?.trading_pairs || parsedStrategy.trading_pairs) || 'Not specified'}</div>
                        <div><strong>Parameters:</strong> {Object.keys(parsedStrategy.strategy || parsedStrategy).length} configured</div>
                      </div>
                    </div>
                  )}

                  {validationResult.errors.length > 0 && (
                    <div className="space-y-3">
                      <h4 className="font-medium text-red-800 flex items-center">
                        🚨 Validation Errors ({validationResult.errors.length})
                      </h4>
                      {validationResult.errors.map((error, index) => (
                        <div key={index} className="text-sm text-red-600 bg-red-50 border border-red-200 p-3 rounded">
                          <div className="font-medium">{error.field}:</div>
                          <div className="mt-1">{error.message}</div>
                        </div>
                      ))}
                    </div>
                  )}

                  {validationResult.warnings.length > 0 && (
                    <div className="space-y-3">
                      <h4 className="font-medium text-yellow-800 flex items-center">
                        ⚠️ Warnings ({validationResult.warnings.length})
                      </h4>
                      {validationResult.warnings.map((warning, index) => (
                        <div key={index} className="text-sm text-yellow-600 bg-yellow-50 border border-yellow-200 p-3 rounded">
                          <div className="font-medium">{warning.field}:</div>
                          <div className="mt-1">{warning.message}</div>
                          {warning.suggestion && (
                            <div className="text-xs mt-2 text-yellow-500 bg-yellow-100 p-2 rounded">
                              💡 <strong>Suggestion:</strong> {warning.suggestion}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Deploy Button for Valid Strategies */}
                  {validationResult.valid && parsedStrategy && (
                    <div className="pt-4 border-t">
                      <button
                        onClick={() => {
                          // Copy to Create Strategy tab
                          setActiveTab('create');
                        }}
                        className="w-full bg-green-600 text-white py-2 px-4 rounded-md hover:bg-green-700 flex items-center justify-center"
                      >
                        🚀 Deploy This Strategy
                        <span className="ml-2 text-xs opacity-80">(Switch to Create tab)</span>
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </main>

      {/* Bot Inspection Modal */}
      {showBotModal && selectedBot && (
        <BotInspectionModal
          bot={filteredBots.find(b => b.id === selectedBot)}
          strategies={(() => {
            const selectedBotData = filteredBots.find(b => b.id === selectedBot);
            const matchedStrategies = strategyActivities.filter(s => s.hive_id === selectedBotData?.name);
            // If no matched strategies (demo mode), show some demo strategies for this bot
            if (matchedStrategies.length === 0 && strategyActivities.length > 0) {
              const selectedBotIndex = parseInt(selectedBot) % strategyActivities.length;
              return strategyActivities.slice(selectedBotIndex, selectedBotIndex + 2).concat(
                strategyActivities.slice(0, Math.max(0, selectedBotIndex + 2 - strategyActivities.length))
              );
            }
            return matchedStrategies;
          })()}
          activities={(() => {
            const selectedBotData = filteredBots.find(b => b.id === selectedBot);
            const matchedActivities = recentActivity.filter(a => a.hive_id === selectedBotData?.name);
            // If no matched activities (demo mode), show some demo activities for this bot
            if (matchedActivities.length === 0 && recentActivity.length > 0) {
              const selectedBotIndex = parseInt(selectedBot) % 50;
              return recentActivity.slice(selectedBotIndex, selectedBotIndex + 20);
            }
            return matchedActivities;
          })()}
          onClose={() => {
            setShowBotModal(false);
            setSelectedBot(null);
          }}
        />
      )}
    </div>
  );
}

// Bot Inspection Modal Component
function BotInspectionModal({
  bot,
  strategies,
  activities,
  onClose
}: {
  bot?: BotInstance;
  strategies: StrategyActivity[];
  activities: ActivityIndicator[];
  onClose: () => void;
}) {
  if (!bot) return null;

  // Use bot's own data instead of trying to calculate from filtered strategies
  const totalActions = bot.total_actions || 0;
  const totalStrategies = bot.total_strategies || 0;

  // Calculate success rate from recent activities instead of strategy data
  const recentActivities = activities.slice(0, 50); // Last 50 activities
  const successfulActivities = recentActivities.filter(a => a.success).length;
  const failedActivities = recentActivities.filter(a => !a.success).length;
  const totalRecentActivities = recentActivities.length;
  const successRate = totalRecentActivities > 0 ? (successfulActivities / totalRecentActivities * 100) : 0;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-6xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b p-6 flex justify-between items-center">
          <div className="flex items-center space-x-4">
            <div className={`w-4 h-4 rounded-full ${bot.status === 'running' ? 'bg-green-500' : 'bg-red-500'}`}></div>
            <div>
              <h2 className="text-2xl font-bold text-gray-800">{bot.name}</h2>
              <p className="text-gray-600">
                {totalStrategies} strategies • {totalActions} total actions
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-3xl leading-none"
          >
            ×
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Bot Overview Stats */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-blue-50 p-4 rounded-lg">
              <div className="text-sm text-blue-600 font-semibold">STATUS</div>
              <div className={`text-xl font-bold ${bot.status === 'running' ? 'text-green-600' : 'text-red-600'}`}>
                {bot.status.toUpperCase()}
              </div>
            </div>
            <div className="bg-green-50 p-4 rounded-lg">
              <div className="text-sm text-green-600 font-semibold">SUCCESS RATE</div>
              <div className="text-xl font-bold text-green-600">{successRate.toFixed(1)}%</div>
            </div>
            <div className="bg-yellow-50 p-4 rounded-lg">
              <div className="text-sm text-yellow-600 font-semibold">UPTIME</div>
              <div className="text-xl font-bold text-yellow-600">
                {bot.uptime >= 3600
                  ? `${Math.floor(bot.uptime / 3600)}h ${Math.floor((bot.uptime % 3600) / 60)}m`
                  : bot.uptime >= 60
                  ? `${Math.floor(bot.uptime / 60)}m ${bot.uptime % 60}s`
                  : `${bot.uptime}s`
                }
              </div>
            </div>
            <div className="bg-purple-50 p-4 rounded-lg">
              <div className="text-sm text-purple-600 font-semibold">ACTIONS/MIN</div>
              <div className="text-xl font-bold text-purple-600">
                {bot.actions_per_minute.toFixed(1)}
              </div>
            </div>
          </div>

          {/* Strategy Breakdown */}
          <div>
            <h3 className="text-lg font-semibold text-gray-800 mb-4">Strategy Performance</h3>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {strategies.map((strategy, index) => (
                <div key={index} className="border rounded-lg p-4 bg-gray-50">
                  <div className="flex justify-between items-center mb-3">
                    <h4 className="font-semibold text-gray-800">{strategy.strategy}</h4>
                    <span className={`px-2 py-1 rounded text-xs font-semibold ${
                      strategy.status === 'ACTIVE' ? 'bg-green-100 text-green-800' :
                      strategy.status === 'IDLE' ? 'bg-blue-100 text-blue-800' :
                      strategy.status === 'WAITING' ? 'bg-yellow-100 text-yellow-800' :
                      'bg-red-100 text-red-800'
                    }`}>
                      {strategy.status}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <div className="text-gray-600">Performance</div>
                      <div className="font-semibold">{strategy.performance_per_min.toFixed(1)}/min</div>
                    </div>
                    <div>
                      <div className="text-gray-600">Refresh Rate</div>
                      <div className="font-semibold">{strategy.refresh_interval.toFixed(1)}s</div>
                    </div>
                    <div>
                      <div className="text-gray-600">Success Rate</div>
                      <div className="font-semibold text-green-600">
                        {strategy.total_actions > 0 ? ((strategy.successful_orders / strategy.total_actions) * 100).toFixed(1) : 0}%
                      </div>
                    </div>
                    <div>
                      <div className="text-gray-600">Total Actions</div>
                      <div className="font-semibold">{strategy.total_actions}</div>
                    </div>
                  </div>

                  {/* Activity pixel grid for this strategy */}
                  <div className="mt-4">
                    <div className="text-xs text-gray-600 mb-2">Recent Activity (last 24 actions)</div>
                    <div className="grid grid-cols-8 gap-1">
                      {Array.from({length: 24}, (_, idx) => {
                        const actionIdx = strategy.recent_actions.length - 1 - idx;
                        const action = actionIdx >= 0 ? strategy.recent_actions[actionIdx] : null;

                        if (!action) {
                          return <div key={idx} className="w-4 h-4 bg-gray-200 rounded"></div>;
                        }

                        const age = (Date.now() - action.time.getTime()) / 1000;
                        let color = 'bg-gray-200';

                        if (age < 30) {
                          color = action.success ? 'bg-green-500' : 'bg-red-500';
                        } else if (age < 120) {
                          color = action.success ? 'bg-green-400' : 'bg-yellow-400';
                        } else if (age < 300) {
                          color = 'bg-blue-300';
                        } else {
                          color = 'bg-gray-300';
                        }

                        return (
                          <div
                            key={idx}
                            className={`w-4 h-4 rounded ${color}`}
                            title={`${action.type} - ${action.time.toLocaleString()}\nSuccess: ${action.success}`}
                          ></div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Recent Activity Log */}
          <div>
            <h3 className="text-lg font-semibold text-gray-800 mb-4">Recent Activity Log</h3>
            <div className="bg-gray-50 rounded-lg p-4 max-h-64 overflow-y-auto">
              {activities.slice(0, 50).map((activity, index) => (
                <div key={index} className="flex items-center justify-between py-2 border-b border-gray-200 last:border-0">
                  <div className="flex items-center space-x-3">
                    <div className={`w-2 h-2 rounded-full ${activity.success ? 'bg-green-500' : 'bg-red-500'}`}></div>
                    <span className="text-sm font-mono text-gray-600">
                      {activity.time.toLocaleTimeString()}
                    </span>
                    <span className="text-sm text-gray-800">{activity.type}</span>
                    <span className="text-xs text-gray-500">{activity.strategy}</span>
                  </div>
                  <span className={`text-xs px-2 py-1 rounded ${
                    activity.success ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                  }`}>
                    {activity.success ? 'SUCCESS' : 'FAILED'}
                  </span>
                </div>
              ))}

              {activities.length === 0 && (
                <div className="text-center text-gray-500 py-8">
                  No recent activity recorded
                </div>
              )}
            </div>
          </div>

          {/* Bot Configuration */}
          <div>
            <h3 className="text-lg font-semibold text-gray-800 mb-4">Configuration</h3>
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                <div>
                  <div className="text-gray-600">Instance ID</div>
                  <div className="font-mono text-xs">{bot.id}</div>
                </div>
                <div>
                  <div className="text-gray-600">API Port</div>
                  <div className="font-semibold">{bot.api_port}</div>
                </div>
                <div>
                  <div className="text-gray-600">Memory Usage</div>
                  <div className="font-semibold">{bot.memory_usage.toFixed(1)} MB</div>
                </div>
                <div>
                  <div className="text-gray-600">CPU Usage</div>
                  <div className="font-semibold">{bot.cpu_usage.toFixed(1)}%</div>
                </div>
                <div>
                  <div className="text-gray-600">Strategies</div>
                  <div className="font-semibold">{bot.strategies.join(', ')}</div>
                </div>
                <div>
                  <div className="text-gray-600">Last Activity</div>
                  <div className="font-semibold">
                    {bot.last_activity ? new Date(bot.last_activity).toLocaleString() : 'Never'}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function MetricCard({ title, value }: { title: string; value: string | number }) {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-sm font-medium text-gray-700 mb-2">{title}</h3>
      <div className="text-2xl font-bold text-gray-900">{value}</div>
    </div>
  );
}

// Enhanced Metric Card with trend and color coding
function EnhancedMetricCard({
  title,
  value,
  trend,
  icon,
  color = 'blue'
}: {
  title: string;
  value: string | number;
  trend?: string;
  icon?: string;
  color?: string;
}) {
  const colorClasses = {
    blue: 'bg-blue-50 text-blue-700 border-blue-200',
    green: 'bg-green-50 text-green-700 border-green-200',
    red: 'bg-red-50 text-red-700 border-red-200',
    yellow: 'bg-yellow-50 text-yellow-700 border-yellow-200',
    purple: 'bg-purple-50 text-purple-700 border-purple-200',
    indigo: 'bg-indigo-50 text-indigo-700 border-indigo-200'
  };

  const trendColor = trend?.startsWith('+') ? 'text-green-600' : trend?.startsWith('-') ? 'text-red-600' : 'text-gray-600';

  return (
    <div className={`rounded-lg border p-4 transition-all hover:shadow-md ${colorClasses[color as keyof typeof colorClasses] || colorClasses.blue}`}>
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-xs font-medium uppercase tracking-wide">{title}</h3>
        {icon && <span className="text-lg">{icon}</span>}
      </div>
      <div className="text-2xl font-bold mb-1">{value}</div>
      {trend && (
        <div className={`text-xs font-medium ${trendColor}`}>
          {trend} from last period
        </div>
      )}
    </div>
  );
}

// Performance Chart Component
function PerformanceChart({
  strategies,
  activities,
  tradingMetrics
}: {
  strategies: StrategyActivity[];
  activities: ActivityIndicator[];
  tradingMetrics: any;
}) {
  if (!strategies || strategies.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <div className="text-4xl mb-4">📈</div>
        <p>No performance data available</p>
      </div>
    );
  }

  // Generate simple performance visualization
  const maxPerformance = Math.max(...strategies.map(s => s.performance_per_min));

  return (
    <div className="space-y-4">
      {/* Quick stats */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="text-center">
          <div className="text-2xl font-bold text-blue-600">{strategies.length}</div>
          <div className="text-sm text-gray-600">Active Strategies</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-green-600">{tradingMetrics?.totalSuccessful || 0}</div>
          <div className="text-sm text-gray-600">Placed Orders</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-purple-600">{(tradingMetrics?.avgPerformance || 0).toFixed(1)}</div>
          <div className="text-sm text-gray-600">Avg Actions/Min</div>
        </div>
      </div>

      {/* Strategy performance bars */}
      <div className="space-y-3">
        <h4 className="text-sm font-medium text-gray-700">Strategy Performance (Actions/Min)</h4>
        {strategies.map((strategy, index) => {
          const percentage = maxPerformance > 0 ? (strategy.performance_per_min / maxPerformance * 100) : 0;
          return (
            <div key={index} className="flex items-center space-x-3">
              <div className="w-20 text-xs font-medium text-gray-600 truncate">{strategy.strategy}</div>
              <div className="flex-1 bg-gray-200 rounded-full h-3">
                <div
                  className={`h-3 rounded-full transition-all duration-500 ${
                    strategy.status === 'ACTIVE' ? 'bg-green-500' :
                    strategy.status === 'WAITING' ? 'bg-yellow-500' :
                    strategy.status === 'IDLE' ? 'bg-blue-500' : 'bg-red-500'
                  }`}
                  style={{ width: `${Math.max(percentage, 2)}%` }}
                ></div>
              </div>
              <div className="w-16 text-xs text-gray-600 text-right">
                {strategy.performance_per_min.toFixed(1)}/min
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// Strategy Comparison Table
function StrategyComparisonTable({ strategies }: { strategies: StrategyActivity[] }) {
  if (!strategies || strategies.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <div className="text-4xl mb-4">📊</div>
        <p>No strategy data available for comparison</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">Strategy</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">Status</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">Performance</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">Success Rate</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">Total Actions</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">Refresh Rate</th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {strategies.map((strategy, index) => {
            const successRate = strategy.total_actions > 0
              ? (strategy.successful_orders / strategy.total_actions * 100)
              : 0;

            return (
              <tr key={index} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center">
                    <span className={`w-3 h-3 rounded-full mr-3 ${
                      strategy.status === 'ACTIVE' ? 'bg-green-500' :
                      strategy.status === 'WAITING' ? 'bg-yellow-500' :
                      strategy.status === 'IDLE' ? 'bg-blue-500' : 'bg-red-500'
                    }`}></span>
                    <span className="text-sm font-medium text-gray-900">{strategy.strategy}</span>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`px-2 py-1 rounded-full text-xs font-semibold ${
                    strategy.status === 'ACTIVE' ? 'bg-green-100 text-green-800' :
                    strategy.status === 'WAITING' ? 'bg-yellow-100 text-yellow-800' :
                    strategy.status === 'IDLE' ? 'bg-blue-100 text-blue-800' : 'bg-red-100 text-red-800'
                  }`}>
                    {strategy.status}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {strategy.performance_per_min.toFixed(1)}/min
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center">
                    <div className="text-sm font-medium text-gray-900">{successRate.toFixed(1)}%</div>
                    <div className="ml-2 w-16 bg-gray-200 rounded-full h-2">
                      <div
                        className={`h-2 rounded-full ${
                          successRate >= 80 ? 'bg-green-500' :
                          successRate >= 60 ? 'bg-yellow-500' : 'bg-red-500'
                        }`}
                        style={{ width: `${Math.min(successRate, 100)}%` }}
                      ></div>
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  <div>
                    <div>{strategy.total_actions}</div>
                    <div className="text-xs text-gray-500">
                      ✓{strategy.successful_orders} ✗{strategy.failed_orders}
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {strategy.refresh_interval.toFixed(1)}s
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// Strategy Activity Card Component
function StrategyActivityCard({ strategy, blinkPhase, enableEffects }: {
  strategy: StrategyActivity;
  blinkPhase: number;
  enableEffects: boolean;
}) {
  const getStatusColor = (status: string, shouldBlink: boolean = false) => {
    const baseColors = {
      'ACTIVE': 'text-green-600',
      'IDLE': 'text-blue-600',
      'WAITING': 'text-yellow-600',
      'ERROR': 'text-red-600'
    };

    if (shouldBlink && enableEffects && blinkPhase === 0) {
      return 'text-transparent';
    }

    return baseColors[status as keyof typeof baseColors] || 'text-gray-600';
  };

  const getStatusSymbol = (status: string) => {
    const symbols = {
      'ACTIVE': '●',
      'IDLE': '○',
      'WAITING': '◐',
      'ERROR': '✗'
    };
    return symbols[status as keyof typeof symbols] || '?';
  };

  return (
    <div className="border rounded-lg p-4">
      <div className="flex justify-between items-center mb-3">
        <span className="font-medium text-purple-600 truncate">{strategy.strategy}</span>
        <span className={`text-lg ${getStatusColor(strategy.status, strategy.status === 'ACTIVE')}`}>
          {getStatusSymbol(strategy.status)}
        </span>
      </div>

      <div className="text-sm text-gray-600 mb-3">
        <div>⏱️ {strategy.refresh_interval.toFixed(1)}s • {strategy.performance_per_min.toFixed(1)}/min</div>
        <div>✓{strategy.successful_orders} ✗{strategy.failed_orders} Σ{strategy.total_actions}</div>
      </div>

      {/* Pixel indicators - 3 rows of 8 */}
      <div className="grid grid-cols-8 gap-1">
        {Array.from({length: 24}, (_, idx) => {
          const actionIdx = strategy.recent_actions.length - 1 - idx;
          const action = actionIdx >= 0 ? strategy.recent_actions[actionIdx] : null;

          if (!action) {
            return <div key={idx} className="w-3 h-3 bg-gray-200 rounded-sm"></div>;
          }

          const age = (Date.now() - action.time.getTime()) / 1000;
          const isRecent = age < 5;
          const shouldBlink = isRecent && enableEffects && blinkPhase === 0;

          let color = 'bg-gray-200';
          if (age < 30) {
            color = action.success ? 'bg-green-500' : 'bg-red-500';
          } else if (age < 120) {
            color = action.success ? 'bg-green-400' : 'bg-yellow-400';
          } else if (age < 300) {
            color = 'bg-blue-300';
          }

          return (
            <div
              key={idx}
              className={`w-3 h-3 rounded-sm ${shouldBlink ? 'bg-transparent' : color}`}
              title={`${action.type} - ${action.time.toLocaleTimeString()}`}
            ></div>
          );
        })}
      </div>
    </div>
  );
}

// Strategy Grid Cell Component (larger version for activity tab)
function StrategyGridCell({ strategy, blinkPhase, enableEffects }: {
  strategy: StrategyActivity;
  blinkPhase: number;
  enableEffects: boolean;
}) {
  const getStatusColor = (status: string, shouldBlink: boolean = false) => {
    if (shouldBlink && enableEffects && blinkPhase === 0) {
      return 'border-transparent text-transparent';
    }

    const colors = {
      'ACTIVE': 'border-green-500 text-green-600',
      'IDLE': 'border-blue-500 text-blue-600',
      'WAITING': 'border-yellow-500 text-yellow-600',
      'ERROR': 'border-red-500 text-red-600'
    };

    return colors[status as keyof typeof colors] || 'border-gray-500 text-gray-600';
  };

  return (
    <div className={`border-2 rounded-lg p-4 h-48 ${getStatusColor(strategy.status, strategy.status === 'ACTIVE').split(' ')[0]}`}>
      {/* Header */}
      <div className="flex justify-between items-center mb-2">
        <h4 className={`font-semibold truncate ${getStatusColor(strategy.status, strategy.status === 'ACTIVE').split(' ')[1]}`}>
          {strategy.strategy}
        </h4>
        <span className={`text-lg ${getStatusColor(strategy.status, strategy.status === 'ACTIVE').split(' ')[1]}`}>
          {strategy.status === 'ACTIVE' ? '●' : strategy.status === 'IDLE' ? '○' : strategy.status === 'WAITING' ? '◐' : '✗'}
        </span>
      </div>

      {/* Stats */}
      <div className="text-xs text-gray-600 mb-3">
        <div className="flex justify-between">
          <span>⏱️ {strategy.refresh_interval.toFixed(1)}s</span>
          <span>{strategy.performance_per_min.toFixed(1)}/min</span>
        </div>
        <div className="flex justify-between mt-1">
          <span className="text-green-600">✓{strategy.successful_orders}</span>
          <span className="text-red-600">✗{strategy.failed_orders}</span>
          <span>Σ{strategy.total_actions}</span>
        </div>
      </div>

      {/* Enhanced pixel grid - 4 rows of 8 for better visualization */}
      <div className="grid grid-cols-8 gap-1">
        {Array.from({length: 32}, (_, idx) => {
          const actionIdx = strategy.recent_actions.length - 1 - idx;
          const action = actionIdx >= 0 ? strategy.recent_actions[actionIdx] : null;

          if (!action) {
            return <div key={idx} className="w-4 h-4 bg-gray-200 rounded"></div>;
          }

          const age = (Date.now() - action.time.getTime()) / 1000;
          const isRecent = age < 5;
          const shouldBlink = isRecent && enableEffects && blinkPhase === 0;

          let color = 'bg-gray-200';
          let symbol = '█';

          // Choose symbol based on action type
          if (action.type.toUpperCase().includes('BUY')) {
            symbol = '▲';
          } else if (action.type.toUpperCase().includes('SELL')) {
            symbol = '▼';
          } else if (action.type.toUpperCase().includes('PASS') || action.type.toUpperCase().includes('TICK')) {
            symbol = '○';
          }

          // Color based on age and success
          if (age < 30) {
            color = action.success ? 'bg-green-500' : 'bg-red-500';
          } else if (age < 120) {
            color = action.success ? 'bg-green-400' : 'bg-yellow-400';
          } else if (age < 300) {
            color = 'bg-blue-300';
          } else {
            color = 'bg-gray-300';
          }

          return (
            <div
              key={idx}
              className={`w-4 h-4 rounded flex items-center justify-center text-xs font-bold text-white ${shouldBlink ? 'bg-transparent' : color}`}
              title={`${action.type} - ${action.time.toLocaleString()}\nSuccess: ${action.success}`}
            >
              {shouldBlink ? '' : symbol === '█' ? '' : symbol}
            </div>
          );
        })}
      </div>

      {/* Last action time */}
      {strategy.last_action_time && (
        <div className="text-xs text-gray-500 mt-2 truncate">
          Last: {strategy.last_action_time.toLocaleTimeString()}
        </div>
      )}
    </div>
  );
}

// Memoized Strategy Card Component to prevent unnecessary re-renders
const StrategyCard = React.memo(({ strategy, botId, onClose }: { strategy: any; botId: string; onClose?: (strategy: string) => void }) => {
  const [showCloseDialog, setShowCloseDialog] = React.useState(false);

  const handleCloseClick = () => {
    setShowCloseDialog(true);
  };

  const handleConfirmClose = async (closePositions: boolean, cancelOrders: boolean) => {
    try {
      console.log(`Closing strategy from Strategy Manager: ${strategy.name}, positions: ${closePositions}, orders: ${cancelOrders}`);
      const response = await fetch('/api/strategies/close', {
        method: 'POST',
        headers: createAdminHeaders({
          'Content-Type': 'application/json',
        }),
        body: JSON.stringify({
          strategy: strategy.name,
          closePositions,
          cancelOrders
        }),
      });

      const result = await response.json();
      if (response.ok) {
        alert(`✅ Strategy "${strategy.name}" closed successfully!\n\n${result.message}`);
        // Call parent onClose handler to refresh data
        if (onClose) {
          await onClose(strategy.name);
        }
      } else {
        alert(`❌ Failed to close strategy: ${result.error}\n\n${result.message || 'Please try again.'}`);
      }
    } catch (error) {
      console.error('Error closing strategy:', error);
      alert(`❌ Error closing strategy: ${error}\n\nPlease check your connection and try again.`);
    } finally {
      setShowCloseDialog(false);
    }
  };

  return (
    <>
      <div key={`${botId}-${strategy.name}`} className="border rounded-lg p-3 bg-gray-50">
        <div className="flex justify-between items-start mb-2">
          <h5 className="font-medium text-sm">{strategy.name}</h5>
          <div className="flex items-center gap-2">
            <span className={`px-2 py-1 rounded-full text-xs ${
              strategy.status === 'active'
                ? 'bg-green-100 text-green-800'
                : 'bg-gray-100 text-gray-800'
            }`}>
              {strategy.status}
            </span>
            {strategy.status === 'active' && onClose && (
              <button
                onClick={handleCloseClick}
                className="px-2 py-1 text-xs bg-red-100 text-red-700 rounded hover:bg-red-200 transition-colors font-medium"
                title="Close Strategy"
              >
                🛑 Close
              </button>
            )}
          </div>
        </div>

        <div className="space-y-1 text-xs text-gray-600">
          <div>Actions: {strategy.total_actions || 0}</div>
          <div>Success: {strategy.successful_orders || 0}</div>
          <div>Failed: {strategy.failed_orders || 0}</div>
          <div>Rate: {strategy.performance_per_min?.toFixed(1) || '0.0'}/min</div>
          <div>Refresh: {strategy.refresh_interval || 0}s</div>
        </div>
      </div>

      {/* Close Strategy Dialog */}
      {showCloseDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">🛑 Close Strategy</h3>
              <button
                onClick={() => setShowCloseDialog(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                ✕
              </button>
            </div>

            <div className="mb-6">
              <p className="text-gray-700 mb-2">
                Are you sure you want to close strategy <strong>"{strategy.name}"</strong>?
              </p>
              <div className="bg-orange-50 border border-orange-200 rounded-lg p-3 mb-4">
                <p className="text-sm text-orange-800">
                  <strong>Strategy Status:</strong> {strategy.status} • {strategy.total_actions || 0} total actions
                </p>
              </div>
            </div>

            <div className="space-y-4 mb-6">
              <div className="flex items-center">
                <input
                  type="checkbox"
                  id={`closePositions-${strategy.name}`}
                  defaultChecked={true}
                  className="h-4 w-4 text-red-600 focus:ring-red-500 border-gray-300 rounded"
                />
                <label htmlFor={`closePositions-${strategy.name}`} className="ml-2 text-sm text-gray-700">
                  <strong>Close all positions</strong> (Market sell/buy to exit)
                </label>
              </div>

              <div className="flex items-center">
                <input
                  type="checkbox"
                  id={`cancelOrders-${strategy.name}`}
                  defaultChecked={true}
                  className="h-4 w-4 text-red-600 focus:ring-red-500 border-gray-300 rounded"
                />
                <label htmlFor={`cancelOrders-${strategy.name}`} className="ml-2 text-sm text-gray-700">
                  <strong>Cancel all open orders</strong> (Clean up order book)
                </label>
              </div>
            </div>

            <div className="bg-gray-50 rounded-lg p-3 mb-6">
              <p className="text-xs text-gray-600">
                <strong>Recommended:</strong> Enable both options for complete cleanup.
                This will close positions and cancel pending orders, leaving nothing behind.
              </p>
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => setShowCloseDialog(false)}
                className="flex-1 px-4 py-2 text-gray-700 bg-gray-200 rounded-lg hover:bg-gray-300 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  const closePositions = (document.getElementById(`closePositions-${strategy.name}`) as HTMLInputElement)?.checked ?? true;
                  const cancelOrders = (document.getElementById(`cancelOrders-${strategy.name}`) as HTMLInputElement)?.checked ?? true;
                  handleConfirmClose(closePositions, cancelOrders);
                }}
                className="flex-1 px-4 py-2 text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors font-semibold"
              >
                🛑 Close Strategy
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}, (prevProps, nextProps) => {
  // Custom comparison to prevent re-renders when strategy data hasn't changed
  const prev = prevProps.strategy;
  const next = nextProps.strategy;

  return (
    prev.name === next.name &&
    prev.status === next.status &&
    prev.total_actions === next.total_actions &&
    prev.successful_orders === next.successful_orders &&
    prev.failed_orders === next.failed_orders &&
    prev.performance_per_min === next.performance_per_min &&
    prev.refresh_interval === next.refresh_interval &&
    prevProps.botId === nextProps.botId &&
    prevProps.onClose === nextProps.onClose
  );
});

// Memoized Bot Section Component
const BotSection = React.memo(({
  botId,
  bot,
  botStrategies,
  deleteLoading,
  onDeleteAllStrategies
}: {
  botId: string;
  bot: BotInstance | undefined;
  botStrategies: any[];
  deleteLoading: string | null;
  onDeleteAllStrategies: (botId: string) => void;
}) => {
  const successfulOrders = botStrategies.reduce((sum, s) => sum + (s.successful_orders || 0), 0);
  const failedOrders = botStrategies.reduce((sum, s) => sum + (s.failed_orders || 0), 0);
  const totalActions = botStrategies.reduce((sum, s) => sum + (s.total_actions || 0), 0);
  const successRate = totalActions > 0 ? ((successfulOrders / totalActions) * 100).toFixed(1) : '0.0';

  return (
    <div key={botId} className="border rounded-lg p-4">
      <div className="flex justify-between items-start mb-4">
        <div>
          <h4 className="text-lg font-semibold flex items-center gap-2">
            <span className={`w-3 h-3 rounded-full ${bot?.status === 'running' ? 'bg-green-500' : 'bg-red-500'}`}></span>
            {bot?.name || botId}
          </h4>
          <p className="text-sm text-gray-600">
            {botStrategies.length} strategies • Success Rate: {successRate}%
          </p>
        </div>
        <button
          onClick={() => onDeleteAllStrategies(botId)}
          disabled={deleteLoading === botId}
          className="px-3 py-1 bg-red-600 text-white text-sm rounded hover:bg-red-700 disabled:opacity-50"
        >
          {deleteLoading === botId ? 'Deleting...' : '🗑️ Delete All'}
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {botStrategies.map((strategy) => (
          <StrategyCard
            key={`${botId}-${strategy.name}`}
            strategy={strategy}
            botId={botId}
            onClose={async () => {
              // Refresh strategies after closing
              await fetchAllStrategies(true);
            }}
          />
        ))}
      </div>
    </div>
  );
}, (prevProps, nextProps) => {
  // Only re-render if bot data or strategies have actually changed
  return (
    prevProps.botId === nextProps.botId &&
    prevProps.bot?.status === nextProps.bot?.status &&
    prevProps.deleteLoading === nextProps.deleteLoading &&
    prevProps.botStrategies.length === nextProps.botStrategies.length &&
    prevProps.botStrategies.every((prevStrategy, index) => {
      const nextStrategy = nextProps.botStrategies[index];
      return (
        prevStrategy.name === nextStrategy.name &&
        prevStrategy.status === nextStrategy.status &&
        prevStrategy.total_actions === nextStrategy.total_actions &&
        prevStrategy.successful_orders === nextStrategy.successful_orders &&
        prevStrategy.failed_orders === nextStrategy.failed_orders
      );
    })
  );
});

// Strategy Manager Component
interface StrategyManagerProps {
  bots: BotInstance[];
  strategyActivities: StrategyActivity[];
}

function StrategyManagerSection({ bots, strategyActivities }: StrategyManagerProps) {
  const [allStrategies, setAllStrategies] = useState<any[]>([]);
  const [isInitialLoading, setIsInitialLoading] = useState(true);
  const [isBackgroundRefreshing, setIsBackgroundRefreshing] = useState(false);
  const [selectedBotForStrategy, setSelectedBotForStrategy] = useState<string | null>(null);
  const [deleteLoading, setDeleteLoading] = useState<string | null>(null);

  // Helper function to compare strategy arrays and prevent unnecessary updates
  const strategiesAreEqual = React.useCallback((prev: any[], next: any[]) => {
    if (prev.length !== next.length) return false;

    // Sort both arrays by bot_id and name for consistent comparison
    const sortedPrev = [...prev].sort((a, b) => `${a.bot_id}-${a.name}`.localeCompare(`${b.bot_id}-${b.name}`));
    const sortedNext = [...next].sort((a, b) => `${a.bot_id}-${a.name}`.localeCompare(`${b.bot_id}-${b.name}`));

    return sortedPrev.every((prevStrategy, index) => {
      const nextStrategy = sortedNext[index];
      return (
        prevStrategy.bot_id === nextStrategy.bot_id &&
        prevStrategy.name === nextStrategy.name &&
        prevStrategy.status === nextStrategy.status &&
        prevStrategy.total_actions === nextStrategy.total_actions &&
        prevStrategy.successful_orders === nextStrategy.successful_orders &&
        prevStrategy.failed_orders === nextStrategy.failed_orders &&
        prevStrategy.performance_per_min === nextStrategy.performance_per_min &&
        prevStrategy.refresh_interval === nextStrategy.refresh_interval
      );
    });
  }, []);

  // Use ref to track if this is first load without causing re-renders
  const isFirstLoadRef = React.useRef(true);

  // Fetch all strategies from the centralized API
  const fetchAllStrategies = React.useCallback(async (isManualRefresh: boolean = false) => {
    try {
      if (isManualRefresh) {
        setIsBackgroundRefreshing(true);
      } else if (isFirstLoadRef.current) {
        setIsInitialLoading(true);
      }

      const response = await fetch('/api/strategies', {
        headers: createAdminHeaders({
          'Cache-Control': 'no-cache',
          'Pragma': 'no-cache'
        })
      });

      if (response.ok) {
        const data = await response.json();
        const newStrategies = data.strategies || [];
        console.log('[Dashboard] Fetched strategies:', newStrategies.length, 'strategies');

        // Always update strategies to ensure real-time data
        setAllStrategies(newStrategies);
      } else {
        console.error('Failed to fetch strategies:', response.status, response.statusText);
        setAllStrategies([]);
      }
    } catch (error) {
      console.error('Error fetching strategies:', error);
      setAllStrategies([]);
    } finally {
      // Always clear loading states
      isFirstLoadRef.current = false;
      setIsInitialLoading(false);
      setIsBackgroundRefreshing(false);
    }
  }, []);

  // Delete all strategies from a bot
  const deleteAllStrategies = async (botId: string) => {
    try {
      setDeleteLoading(botId);
      const response = await fetch(`/api/strategies?bot_id=${botId}`, {
        method: 'DELETE',
        headers: createAdminHeaders({})
      });

      if (response.ok) {
        await fetchAllStrategies(); // Refresh the list
      } else {
        const error = await response.json();
        alert(`Failed to delete strategies: ${error.error}`);
      }
    } catch (error) {
      console.error('Error deleting strategies:', error);
      alert('Failed to delete strategies');
    } finally {
      setDeleteLoading(null);
    }
  };

  // Load strategies on component mount
  React.useEffect(() => {
    fetchAllStrategies();
    const interval = setInterval(() => fetchAllStrategies(false), 15000); // Background refresh every 15 seconds
    return () => clearInterval(interval);
  }, [fetchAllStrategies]);

  // Group strategies by bot
  const strategiesByBot = allStrategies.reduce((acc, strategy) => {
    if (!acc[strategy.bot_id]) {
      acc[strategy.bot_id] = [];
    }
    acc[strategy.bot_id].push(strategy);
    return acc;
  }, {} as Record<string, any[]>);

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <div className="px-6 py-4 border-b flex justify-between items-center">
        <div>
          <h3 className="text-lg font-semibold text-gray-600 flex items-center gap-2">
            Strategy Manager
            {isBackgroundRefreshing && (
              <span className="text-xs text-blue-500 bg-blue-50 px-2 py-1 rounded-full animate-pulse">
                Updating...
              </span>
            )}
          </h3>
          <p className="text-sm text-gray-600">Centralized strategy control across all bot instances</p>
        </div>
        <button
          onClick={() => fetchAllStrategies(true)}
          disabled={isBackgroundRefreshing}
          className={`px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 relative ${isBackgroundRefreshing ? 'animate-pulse' : ''}`}
        >
          <span className="flex items-center gap-2">
            <span className={isBackgroundRefreshing ? 'animate-spin' : ''}>🔄</span>
            Refresh
          </span>
        </button>
      </div>

      <div className="p-6">
        {isInitialLoading ? (
          <div className="text-center py-8">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <p className="mt-2 text-gray-600">Loading strategies...</p>
          </div>
        ) : allStrategies.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <div className="text-4xl mb-4">📭</div>
            <p>No strategies found</p>
            <p className="text-sm">Strategies will appear here when bots are running</p>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Summary Statistics */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="bg-blue-50 p-4 rounded-lg">
                <div className="text-2xl font-bold text-blue-600">{allStrategies.length}</div>
                <div className="text-sm text-blue-800">Total Strategies</div>
              </div>
              <div className="bg-green-50 p-4 rounded-lg">
                <div className="text-2xl font-bold text-green-600">
                  {allStrategies.reduce((sum, s) => sum + (s.successful_orders || 0), 0)}
                </div>
                <div className="text-sm text-green-800">Placed Orders</div>
              </div>
              <div className="bg-red-50 p-4 rounded-lg">
                <div className="text-2xl font-bold text-red-600">
                  {allStrategies.reduce((sum, s) => sum + (s.failed_orders || 0), 0)}
                </div>
                <div className="text-sm text-red-800">Failed Orders</div>
              </div>
              <div className="bg-gray-50 p-4 rounded-lg">
                <div className="text-2xl font-bold text-gray-600">
                  {allStrategies.reduce((sum, s) => sum + (s.total_actions || 0), 0)}
                </div>
                <div className="text-sm text-gray-800">Total Actions</div>
              </div>
            </div>

            {/* Bot-grouped Strategy List */}
            <div className="space-y-4">
              {Object.entries(strategiesByBot).map(([botId, botStrategies]) => {
                const bot = bots.find(b => b.name === botId);
                return (
                  <BotSection
                    key={botId}
                    botId={botId}
                    bot={bot}
                    botStrategies={botStrategies}
                    deleteLoading={deleteLoading}
                    onDeleteAllStrategies={deleteAllStrategies}
                  />
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
