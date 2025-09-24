import { NextRequest, NextResponse } from 'next/server';
import { database } from '@/lib/database';
import { authenticateRequest, getUserIdFromWallet, isAdminRequest } from '@/lib/auth';

// Strategy status cache to prevent flickering
interface CachedStrategyStatus {
  status: string;
  total_actions: number;
  successful_orders: number;
  failed_orders: number;
  performance_per_min: number;
  is_running: boolean;
  last_updated: number;
  cache_expiry: number;
}

const strategyStatusCache = new Map<string, CachedStrategyStatus>();
const CACHE_DURATION = 30000; // 30 seconds cache duration
const CACHE_STALE_AFTER = 60000; // Consider stale after 1 minute

// Helper function to clean expired cache entries
function cleanExpiredCache() {
  const now = Date.now();
  const expiredKeys: string[] = [];

  for (const [key, value] of strategyStatusCache.entries()) {
    if (now > value.last_updated + CACHE_STALE_AFTER) {
      expiredKeys.push(key);
    }
  }

  expiredKeys.forEach(key => {
    strategyStatusCache.delete(key);
    console.log(`[Strategy API] Cleaned expired cache entry: ${key}`);
  });
}

// Helper functions for bot selection
async function getAvailableBots() {
  const client = await database.getClient();
  try {
    // Get available bots with strategy count calculated from hive_strategy_configs
    const botsQuery = `
      SELECT
        hi.hive_id,
        hi.hostname,
        hi.api_port,
        hi.status,
        COALESCE(strategy_counts.strategy_count, 0) as total_strategies
      FROM hive_instances hi
      LEFT JOIN (
        SELECT hive_id, COUNT(*) as strategy_count
        FROM hive_strategy_configs
        WHERE enabled = true
        GROUP BY hive_id
      ) strategy_counts ON hi.hive_id = strategy_counts.hive_id
      WHERE hi.last_seen >= NOW() - INTERVAL '5 minutes'
        AND hi.status IN ('running', 'active')
      ORDER BY COALESCE(strategy_counts.strategy_count, 0) ASC
    `;
    const result = await client.query(botsQuery);
    console.log(`[Bot Selection] Found ${result.rows.length} available bots:`, result.rows);
    return result.rows;
  } finally {
    if ('release' in client) {
      client.release();
    } else {
      await client.end();
    }
  }
}

function selectOptimalBot(availableBots: any[]) {
  if (availableBots.length === 0) return null;

  // Simple load balancing: select bot with least strategies
  return availableBots.reduce((optimal, current) =>
    (current.total_strategies < optimal.total_strategies) ? current : optimal
  );
}

interface BotInstance {
  id: string;
  name: string;
  api_port: number;
  status: 'running' | 'offline' | 'error';
}

import { StrategyConfig, PMMStrategyConfig, DirectionalTradingConfig, AvellanedaConfig, CrossExchangeConfig } from '@/types';

interface BotStrategyConfig {
  name: string;
  exchange: string;
  market: string;
  bid_spread: number;
  ask_spread: number;
  order_amount: number;
  order_refresh_time: number;
  enabled: boolean;
}

// Helper function to convert strategy config to DynamicStrategyConfig format
function convertToBotApiFormat(strategy: StrategyConfig): any {
  // Handle both trading_pairs (array) and trading_pair (string) formats
  let market;
  if (strategy.trading_pair) {
    market = strategy.trading_pair;
  } else if (strategy.trading_pairs && strategy.trading_pairs.length > 0) {
    market = strategy.trading_pairs[0];
  }

  // Build ONLY DynamicStrategyConfig fields - no spread operations
  const config: any = {};

  // Required fields
  config.name = strategy.name;
  config.enabled = strategy.enabled !== false;

  // Optional fields - only add if they exist in the payload
  if (strategy.connector_type) config.exchange = strategy.connector_type;
  else if ((strategy as any).connector_name) config.exchange = (strategy as any).connector_name;
  if (market) config.market = market;
  if ((strategy as any).bid_spread !== undefined) config.bid_spread = (strategy as any).bid_spread;
  else if ((strategy as any).spreads && (strategy as any).spreads.length > 0) config.bid_spread = (strategy as any).spreads[0];

  if ((strategy as any).ask_spread !== undefined) config.ask_spread = (strategy as any).ask_spread;
  else if ((strategy as any).spreads && (strategy as any).spreads.length > 0) config.ask_spread = (strategy as any).spreads[0];
  if ((strategy as any).order_amount !== undefined) config.order_amount = (strategy as any).order_amount;
  if ((strategy as any).order_levels !== undefined) config.order_levels = (strategy as any).order_levels;
  if ((strategy as any).order_refresh_time !== undefined) config.order_refresh_time = (strategy as any).order_refresh_time;
  if ((strategy as any).order_level_spread !== undefined) config.order_level_spread = (strategy as any).order_level_spread;
  if ((strategy as any).order_level_amount !== undefined) config.order_level_amount = (strategy as any).order_level_amount;

  return config;
}

// GET /api/strategies - List strategies (filtered by authenticated user or admin access)
export async function GET(request: NextRequest) {
  try {
    // Parse query parameters
    const url = new URL(request.url);
    const enabledStatus = url.searchParams.get('status') || 'active';

    // Determine enabled filter based on status parameter
    let enabledFilter: boolean | null = null;
    if (enabledStatus === 'active') {
      enabledFilter = true;  // Only enabled strategies
    } else if (enabledStatus === 'disabled') {
      enabledFilter = false; // Only disabled strategies
    } else if (enabledStatus === 'all') {
      enabledFilter = null;  // Both enabled and disabled
    } else {
      enabledFilter = true;  // Default to active if invalid parameter
    }

    console.log(`[Strategies API] Filtering strategies with status: ${enabledStatus}, enabled: ${enabledFilter}`);

    // Check for admin access first
    const isAdmin = isAdminRequest(request);
    let userId: string | null = null;

    let walletAddress: string | null = null;

    const sortByMostRecent = <T extends { created_at?: string; updated_at?: string }>(items: T[]): T[] => {
      return items.sort((a, b) => {
        const aTime = new Date(a.updated_at ?? a.created_at ?? 0).getTime();
        const bTime = new Date(b.updated_at ?? b.created_at ?? 0).getTime();
        return bTime - aTime;
      });
    };

    if (!isAdmin) {
      // Regular user authentication flow
      const authResult = authenticateRequest(request);
      if (!authResult.isValid) {
        return NextResponse.json(
          { error: 'Authentication failed', details: authResult.error },
          { status: 401 }
        );
      }
      userId = getUserIdFromWallet(authResult.walletAddress!);
      walletAddress = authResult.walletAddress?.toLowerCase() || null;
      console.log(`[Strategies API] Authenticated user: ${userId}`);
    } else {
      // Admin access - no user filtering
      console.log(`[Strategies API] Admin access granted - showing all strategies`);
    }

    // Clean expired cache entries
    cleanExpiredCache();

    // First try to get live strategies from Hive orchestrator
    try {
      console.log('[Strategies API] Attempting to fetch live strategies from Hive orchestrator...');
      if (walletAddress) {
        console.log(`[Strategies API] Forwarding wallet ${walletAddress} to Hive orchestrator`);
      } else {
        console.log('[Strategies API] No wallet available for Hive orchestrator request (admin or missing header)');
      }

      const hiveRequestHeaders: Record<string, string> = { 'Content-Type': 'application/json' };
      if (walletAddress) {
        hiveRequestHeaders['X-Wallet-Address'] = walletAddress;
      }

      const hiveResponse = await fetch('http://localhost:8080/api/strategies', {
        method: 'GET',
        headers: hiveRequestHeaders,
        signal: AbortSignal.timeout(5000) // 5 second timeout
      });

      if (hiveResponse.ok) {
        const hiveData = await hiveResponse.json();
        console.log(`[Strategies API] Got ${hiveData.strategies?.length || 0} live strategies from Hive orchestrator`);

        if (hiveData.strategies && hiveData.strategies.length > 0) {
          // Convert Hive orchestrator format to dashboard format
          const liveStrategies = sortByMostRecent(hiveData.strategies.map((strategy: any) => ({
            name: strategy.name,
            bot_id: 'hive-orchestrator-live',
            bot_hostname: 'localhost',
            bot_port: 8080,
            strategy_type: strategy.config?.strategy_type || 'pure_market_making',
            connector_type: strategy.config?.exchange || 'hyperliquid_perpetual',
            trading_pairs: [strategy.config?.market || 'Unknown'],
            bid_spread: parseFloat(strategy.config?.bid_spread || 0),
            ask_spread: parseFloat(strategy.config?.ask_spread || 0),
            order_amount: parseFloat(strategy.config?.order_amount || 0),
            order_levels: parseInt(strategy.config?.order_levels || 1),
            order_refresh_time: parseFloat(strategy.config?.order_refresh_time || 5.0),
            status: strategy.is_running ? 'active' : 'idle',
            is_running: strategy.is_running || false,
            total_actions: strategy.actions_count || 0,
            successful_orders: strategy.actions_count || 0,
            failed_orders: 0,
            performance_per_min: strategy.performance_metrics?.actions_per_minute || 0,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString()
          })));

          console.log('[Strategies API] Using live strategies from orchestrator');
          return NextResponse.json({
            strategies: liveStrategies,
            total_count: liveStrategies.length,
            timestamp: new Date().toISOString(),
            data_source: 'Live Hive Orchestrator'
          });
        }
      } else {
        console.log(`[Strategies API] Hive orchestrator responded with status: ${hiveResponse.status}`);
      }
    } catch (error) {
      console.log('[Strategies API] Failed to fetch from Hive orchestrator, falling back to PostgreSQL:', error);
    }

    const client = await database.getClient();

    try {
      // Get strategy configurations from PostgreSQL only for ACTIVE bots
      // For admin access, show all strategies; for users, filter by user_id
      let strategiesQuery: string;
      let queryParams: any[];

      if (isAdmin) {
        // Admin sees all strategies (with optional enabled filter)
        const enabledCondition = enabledFilter !== null ? `AND hsc.enabled = $1` : '';
        strategiesQuery = `
          SELECT
            hsc.name,
            hsc.hive_id,
            hsc.strategy_type,
            hsc.connector_type,
            hsc.trading_pairs,
            hsc.bid_spread,
            hsc.ask_spread,
            hsc.order_amount,
            hsc.order_levels,
            hsc.order_refresh_time,
            hsc.enabled,
            hsc.created_at,
            hsc.updated_at,
            hi.hostname,
            hi.api_port
          FROM hive_strategy_configs hsc
          INNER JOIN hive_instances hi ON hsc.hive_id = hi.hive_id
          WHERE hi.last_seen >= NOW() - INTERVAL '24 hours'
            AND hi.status = 'active'
            ${enabledCondition}
          ORDER BY hsc.updated_at DESC
        `;
        queryParams = enabledFilter !== null ? [enabledFilter] : [];
      } else {
        // Regular user sees only their own strategies (filtered by user_id and optional enabled filter)
        const enabledCondition = enabledFilter !== null ? `AND hsc.enabled = $2` : '';
        strategiesQuery = `
          SELECT
            hsc.name,
            hsc.hive_id,
            hsc.strategy_type,
            hsc.connector_type,
            hsc.trading_pairs,
            hsc.bid_spread,
            hsc.ask_spread,
            hsc.order_amount,
            hsc.order_levels,
            hsc.order_refresh_time,
            hsc.enabled,
            hsc.created_at,
            hsc.updated_at,
            hi.hostname,
            hi.api_port
          FROM hive_strategy_configs hsc
          INNER JOIN hive_instances hi ON hsc.hive_id = hi.hive_id
          WHERE hi.last_seen >= NOW() - INTERVAL '24 hours'
            AND hi.status = 'active'
            AND hsc.user_id = $1
            ${enabledCondition}
          ORDER BY hsc.updated_at DESC
        `;
        queryParams = enabledFilter !== null ? [userId, enabledFilter] : [userId];
      }

      const result = await client.query(strategiesQuery, queryParams);

      // Fetch real-time metrics from each bot instance with caching
      const strategiesWithMetrics = await Promise.all(result.rows.map(async (row: any) => {
        const cacheKey = `${row.name}-${row.hive_id}`;
        const now = Date.now();

        // Check if we have valid cached data
        const cached = strategyStatusCache.get(cacheKey);
        let realTimeMetrics = {
          status: row.enabled ? 'active' : 'stopped',
          total_actions: 0,
          successful_orders: 0,
          failed_orders: 0,
          performance_per_min: 0,
          is_running: !!row.enabled
        };

        // Use cached data if it's still valid
        if (cached && now < cached.cache_expiry) {
          realTimeMetrics = {
            status: cached.status,
            total_actions: cached.total_actions,
            successful_orders: cached.successful_orders,
            failed_orders: cached.failed_orders,
            performance_per_min: cached.performance_per_min,
            is_running: cached.is_running
          };
          console.log(`[Strategy API] Using cached data for ${row.name} (${cached.status})`);
        } else {
          // Try to get real metrics from activities table first
          try {
            const activityQuery = `
              SELECT
                COUNT(*) as total_actions,
                COUNT(*) FILTER (WHERE success = true) as successful_orders,
                COUNT(*) FILTER (WHERE success = false) as failed_orders,
                MAX(timestamp) as last_action_time,
                CASE
                  WHEN MAX(timestamp) >= NOW() - INTERVAL '2 minutes' THEN 'active'
                  WHEN MAX(timestamp) >= NOW() - INTERVAL '10 minutes' THEN 'idle'
                  WHEN MAX(timestamp) IS NOT NULL THEN 'waiting'
                  ELSE 'pending'
                END as status,
                COALESCE(
                  ROUND(
                    (COUNT(*) FILTER (WHERE timestamp >= NOW() - INTERVAL '1 hour')::DECIMAL /
                     NULLIF(EXTRACT(EPOCH FROM LEAST(NOW() - MIN(timestamp), INTERVAL '1 hour'))::DECIMAL / 60, 0))
                  , 2), 0
                ) as performance_per_min
              FROM hive_activities
              WHERE strategy_name = $1 AND hive_id = $2 AND timestamp >= NOW() - INTERVAL '24 hours'
            `;
            const activityResult = await client.query(activityQuery, [row.name, row.hive_id]);

            if (activityResult.rows.length > 0 && activityResult.rows[0].total_actions > 0) {
              const activityData = activityResult.rows[0];
              realTimeMetrics = {
                status: activityData.status,
                total_actions: parseInt(activityData.total_actions) || 0,
                successful_orders: parseInt(activityData.successful_orders) || 0,
                failed_orders: parseInt(activityData.failed_orders) || 0,
                performance_per_min: parseFloat(activityData.performance_per_min) || 0,
                is_running: activityData.status === 'active'
              };
              console.log(`[Strategy API] Using activity data for ${row.name}: ${realTimeMetrics.status}, ${realTimeMetrics.total_actions} actions`);
            } else {
              console.log(`[Strategy API] No activity data found for ${row.name}, trying bot API...`);
            }
          } catch (activityError) {
            console.warn(`[Strategy API] Failed to get activity data for ${row.name}:`, activityError.message);
          }

          // Only try bot API if we don't have activity data
          if (realTimeMetrics.total_actions === 0 && row.hostname && row.api_port) {
            try {
              // Map stored hostname to localhost for local API calls
              const apiHost = row.hostname.includes('local') ? 'localhost' : row.hostname;
              const botApiUrl = `http://${apiHost}:${row.api_port}/api/strategies`;
              console.log(`[Strategy API] Fetching fresh data from ${row.hostname} -> ${apiHost}:${row.api_port} for ${row.name}`);
              const botResponse = await fetch(botApiUrl, {
                method: 'GET',
                signal: AbortSignal.timeout(15000) // 15 second timeout for reliability
              });

              if (botResponse.ok) {
                const botData = await botResponse.json();
                const strategyInBot = botData.strategies?.find((s: any) => s.name === row.name);

                if (strategyInBot) {
                  realTimeMetrics = {
                    status: strategyInBot.is_running ? 'active' : 'stopped',
                    total_actions: strategyInBot.actions_count || 0,
                    successful_orders: 0, // Bot API doesn't provide order success/failure breakdown
                    failed_orders: 0, // Bot API doesn't provide order success/failure breakdown
                    performance_per_min: parseFloat(strategyInBot.performance_metrics?.actions_per_minute) || 0,
                    is_running: strategyInBot.is_running || false
                  };

                  // Cache the successful response
                  strategyStatusCache.set(cacheKey, {
                    ...realTimeMetrics,
                    last_updated: now,
                    cache_expiry: now + CACHE_DURATION
                  });
                  console.log(`[Strategy API] Cached fresh data for ${row.name}: ${realTimeMetrics.status}`);
                } else {
                  // Strategy not found in bot - mark as pending but don't override cache
                  if (cached && now < cached.last_updated + CACHE_STALE_AFTER) {
                    // Use stale cache data rather than defaulting to pending
                    realTimeMetrics = {
                      status: cached.status,
                      total_actions: cached.total_actions,
                      successful_orders: cached.successful_orders,
                      failed_orders: cached.failed_orders,
                      performance_per_min: cached.performance_per_min,
                      is_running: cached.is_running
                    };
                    console.log(`[Strategy API] Using stale cache for ${row.name} (strategy not found in bot)`);
                  }
                }
              } else {
                // Bot API failed - use cached data if available
                if (cached && now < cached.last_updated + CACHE_STALE_AFTER) {
                  realTimeMetrics = {
                    status: cached.status,
                    total_actions: cached.total_actions,
                    successful_orders: cached.successful_orders,
                    failed_orders: cached.failed_orders,
                    performance_per_min: cached.performance_per_min,
                    is_running: cached.is_running
                  };
                  console.log(`[Strategy API] Bot API failed, using stale cache for ${row.name}: ${cached.status}`);
                }
              }
            } catch (error) {
              const apiHost = row.hostname.includes('local') ? 'localhost' : row.hostname;
              console.warn(`Failed to fetch real-time data for ${row.name} from ${apiHost}:${row.api_port}:`, error.message);

              // Use cached data if available, even if stale
              if (cached && now < cached.last_updated + CACHE_STALE_AFTER) {
                realTimeMetrics = {
                  status: cached.status,
                  total_actions: cached.total_actions,
                  successful_orders: cached.successful_orders,
                  failed_orders: cached.failed_orders,
                  performance_per_min: cached.performance_per_min,
                  is_running: cached.is_running
                };
                console.log(`[Strategy API] Network error, using stale cache for ${row.name}: ${cached.status}`);
              }
            }
          } else {
            // No bot info available - use cached data if we have it
            if (cached && now < cached.last_updated + CACHE_STALE_AFTER) {
              realTimeMetrics = {
                status: cached.status,
                total_actions: cached.total_actions,
                successful_orders: cached.successful_orders,
                failed_orders: cached.failed_orders,
                performance_per_min: cached.performance_per_min,
                is_running: cached.is_running
              };
              console.log(`[Strategy API] No bot info, using stale cache for ${row.name}: ${cached.status}`);
            }
          }
        }

        return {
          name: row.name,
          bot_id: row.hive_id,
          bot_hostname: row.hostname || 'unknown',
          bot_port: row.api_port || 8080,
          strategy_type: row.strategy_type,
          connector_type: row.connector_type,
          trading_pairs: JSON.parse(row.trading_pairs || '[]'),
          bid_spread: parseFloat(row.bid_spread) || 0,
          ask_spread: parseFloat(row.ask_spread) || 0,
          order_amount: parseFloat(row.order_amount) || 0,
          order_levels: parseInt(row.order_levels) || 1,
          order_refresh_time: parseFloat(row.order_refresh_time) || 5.0,
          status: realTimeMetrics.status,
          is_running: realTimeMetrics.status === 'active', // Add is_running field for frontend
          total_actions: realTimeMetrics.total_actions,
          successful_orders: realTimeMetrics.successful_orders,
          failed_orders: realTimeMetrics.failed_orders,
          performance_per_min: realTimeMetrics.performance_per_min,
          created_at: row.created_at,
          updated_at: row.updated_at
        };
      }));

      const sortedStrategies = sortByMostRecent(strategiesWithMetrics);

      return NextResponse.json({
        strategies: sortedStrategies,
        total_count: strategiesWithMetrics.length,
        timestamp: new Date().toISOString(),
        data_source: 'PostgreSQL + Real-time Bot APIs',
        admin_view: isAdmin
      });

    } finally {
      if ('release' in client) {
        client.release();
      } else {
        await client.end();
      }
    }

  } catch (error) {
    console.error('Failed to fetch strategies from PostgreSQL:', error);
    return NextResponse.json(
      { error: 'Failed to fetch strategies', details: error.message },
      { status: 500 }
    );
  }
}

// POST /api/strategies - Add new strategy (server chooses bot)
export async function POST(request: NextRequest) {
  try {
    console.log('[Strategy API] POST request received');
    const incomingHeadersSnapshot = {
      wallet: request.headers.get('x-wallet-address'),
      adminTokenPresent: request.headers.get('x-admin-token') ? true : false,
      signaturePresent: request.headers.get('x-auth-signature') ? true : false,
      messagePresent: request.headers.get('x-auth-message') ? true : false,
    };
    console.log('[Strategy API] Incoming auth headers snapshot:', {
      wallet: incomingHeadersSnapshot.wallet ? `${incomingHeadersSnapshot.wallet.slice(0, 10)}...` : 'missing',
      adminTokenPresent: incomingHeadersSnapshot.adminTokenPresent,
      signaturePresent: incomingHeadersSnapshot.signaturePresent,
      messagePresent: incomingHeadersSnapshot.messagePresent,
    });

    const body = await request.json();
    console.log('[Strategy API] Request body:', JSON.stringify(body, null, 2));
    const { strategy } = body;

    if (!strategy) {
      console.log('[Strategy API] ERROR: No strategy in request body');
      return NextResponse.json(
        { error: 'strategy configuration is required' },
        { status: 400 }
      );
    }

    console.log('[Strategy API] Strategy config received:', JSON.stringify(strategy, null, 2));

    const normalizeWallet = (value?: string | null): string | null => {
      if (!value) return null;
      const trimmed = value.trim();
      return /^0x[a-fA-F0-9]{40}$/.test(trimmed) ? trimmed.toLowerCase() : null;
    };

    const walletHeader = normalizeWallet(incomingHeadersSnapshot.wallet);
    let forwardedWallet = walletHeader;
    let walletSource: 'header' | 'strategy_user_id' | null = walletHeader ? 'header' : null;

    if (!forwardedWallet && typeof strategy?.user_id === 'string') {
      const fallbackWallet = normalizeWallet(strategy.user_id);
      if (fallbackWallet) {
        forwardedWallet = fallbackWallet;
        walletSource = 'strategy_user_id';
        console.log(`[Strategy API] Wallet header missing; using strategy.user_id fallback: ${fallbackWallet}`);
      }
    }

    const derivedUserId = (() => {
      if (typeof strategy?.user_id === 'string' && strategy.user_id.trim()) {
        return strategy.user_id.trim().toLowerCase();
      }
      if (forwardedWallet) {
        return forwardedWallet;
      }
      return null;
    })();

    if (!forwardedWallet) {
      console.warn('[Strategy API] No wallet information available. Requests to Hive will omit X-Wallet-Address header.');
    }

    const orchestratorHeaders: Record<string, string> = { 'Content-Type': 'application/json' };
    if (forwardedWallet) {
      orchestratorHeaders['X-Wallet-Address'] = forwardedWallet;
    }
    console.log('[Strategy API] Forwarding headers to bot:', orchestratorHeaders);

    const debugContext = {
      incomingWalletHeader: walletHeader,
      walletSource,
      forwardedWallet,
      derivedUserId,
    };

    // Server automatically selects appropriate bot based on load balancing
    // This is where the manager center makes the decision, not the client
    console.log('[Strategy API] Looking for available bots...');
    const availableBots = await getAvailableBots();
    console.log('[Strategy API] Available bots:', availableBots);

    let selectedBot = selectOptimalBot(availableBots);

    if (!selectedBot) {
      console.log('[Strategy API] No running bots found, trying fallback...');
      // Fallback: try to find any bot regardless of last_seen time
      const fallbackClient = await database.getClient();
      try {
        const fallbackQuery = `
          SELECT hive_id, hostname, api_port, status
          FROM hive_instances
          WHERE status IN ('running', 'active', 'stopped')
          ORDER BY
            CASE
              WHEN status = 'running' THEN 1
              WHEN status = 'active' THEN 2
              ELSE 3
            END,
            last_seen DESC
          LIMIT 1
        `;
        const fallbackResult = await fallbackClient.query(fallbackQuery);
        console.log('[Strategy API] Fallback query result:', fallbackResult.rows);

        if (fallbackResult.rows.length > 0) {
          selectedBot = {
            ...fallbackResult.rows[0],
            total_strategies: 0
          };
          console.log('[Strategy API] Using fallback bot:', selectedBot);
        }
      } finally {
        if ('release' in fallbackClient) {
          fallbackClient.release();
        } else {
          await fallbackClient.end();
        }
      }
    }

    // Allow strategy creation even without bot instance - save to database for later deployment
    let bot_id = selectedBot?.hive_id || null;
    let botInfo = selectedBot || null;

    if (!selectedBot) {
      console.log('[Strategy API] WARNING: No bot instances available, creating strategy config only');
      bot_id = null; // Will be assigned when bot becomes available
    } else {
      console.log('[Strategy API] Selected bot:', bot_id, 'with', selectedBot.total_strategies, 'strategies');
    }

    // STEP 1: Create strategy configuration in PostgreSQL (master source)
    console.log(`[Strategy Manager] Server selected bot ${bot_id} for user strategy ${strategy.name}`);

    // Handle both trading_pairs (array) and trading_pair (string) formats
    let tradingPairs = ['BTC-USD']; // default
    if (strategy.trading_pair) {
      tradingPairs = [strategy.trading_pair];
    } else if (strategy.trading_pairs && strategy.trading_pairs.length > 0) {
      tradingPairs = strategy.trading_pairs;
    }

    // Generate strategy name if not provided
    let strategyName = strategy.name;
    if (!strategyName || strategyName.trim() === '') {
      // Generate name from controller_name, connector, and trading pair
      const controller = strategy.controller_name || strategy.strategy_type || 'strategy';
      const connector = strategy.connector_name || strategy.connector_type || 'unknown';
      const pair = strategy.trading_pair || (strategy.trading_pairs && strategy.trading_pairs[0]) || 'BTC-USD';
      const timestamp = Date.now();
      strategyName = `${controller}_${connector}_${pair.replace('-', '_').toLowerCase()}_${timestamp}`;
      console.log(`[Strategy Manager] Generated strategy name: ${strategyName}`);
    }

    // Ensure unique strategy name by appending random suffix if needed
    let uniqueName = strategyName;
    const checkClient = await database.getClient();
    try {
      const nameCheckQuery = `SELECT name FROM hive_strategy_configs WHERE name = $1`;
      const nameCheckResult = await checkClient.query(nameCheckQuery, [uniqueName]);

      if (nameCheckResult.rows.length > 0) {
        // Name already exists, generate unique name with timestamp + random
        const timestamp = Date.now();
        const randomSuffix = Math.floor(Math.random() * 1000).toString().padStart(3, '0');
        uniqueName = `${strategy.name}_${timestamp}_${randomSuffix}`;
        console.log(`[Strategy Manager] Name conflict detected. Changed ${strategy.name} to ${uniqueName}`);
      }
    } finally {
      if ('release' in checkClient) {
        checkClient.release();
      } else {
        await checkClient.end();
      }
    }

    // Create flexible strategy configuration that supports all strategy types
    const strategyConfig = {
      name: uniqueName,
      hive_id: bot_id,
      user_id: derivedUserId,
      strategy_type: strategy.strategy_type || 'pure_market_making',
      connector_type: strategy.connector_type || 'hyperliquid_perpetual',
      trading_pairs: tradingPairs,
      enabled: strategy.enabled !== false,

      // Store all strategy parameters as JSON for flexibility
      strategy_params: {
        ...strategy, // Store the entire strategy config
        // Ensure we don't duplicate these fields
        name: undefined,
        hive_id: undefined,
        user_id: undefined,
        strategy_type: undefined,
        connector_type: undefined,
        trading_pairs: undefined,
        enabled: undefined
      },

      // Legacy PMM fields for backward compatibility
      bid_spread: (strategy as any).bid_spread || 0.05,
      ask_spread: (strategy as any).ask_spread || 0.05,
      order_amount: (strategy as any).order_amount || (strategy as any).total_amount_quote || 0.001,
      order_levels: (strategy as any).order_levels || 1,
      order_refresh_time: (strategy as any).order_refresh_time || 5.0,
      order_level_spread: (strategy as any).order_level_spread || 0.0,
      order_level_amount: (strategy as any).order_level_amount || 0.0,
      inventory_target_base_pct: (strategy as any).inventory_target_base_pct || 50.0,
      inventory_range_multiplier: (strategy as any).inventory_range_multiplier || 1.0,
      hanging_orders_enabled: (strategy as any).hanging_orders_enabled || false,
      hanging_orders_cancel_pct: (strategy as any).hanging_orders_cancel_pct || 10.0,
      leverage: (strategy as any).leverage || 1,
      position_mode: (strategy as any).position_mode || 'ONEWAY',
      order_optimization_enabled: (strategy as any).order_optimization_enabled || true,
      ask_order_optimization_depth: (strategy as any).ask_order_optimization_depth || 0.0,
      bid_order_optimization_depth: (strategy as any).bid_order_optimization_depth || 0.0,
      price_ceiling: (strategy as any).price_ceiling || -1.0,
      price_floor: (strategy as any).price_floor || -1.0,
      ping_pong_enabled: (strategy as any).ping_pong_enabled || false,
      min_profitability: (strategy as any).min_profitability || 0.003,
      min_price_diff_pct: (strategy as any).min_price_diff_pct || 0.1,
      max_order_size: (strategy as any).max_order_size || 1.0
    };

    const createResult = await database.createStrategyConfig(strategyConfig);
    if (!createResult.success) {
      console.error('[Strategy API] Database creation failed for strategy:', strategy.name);
      console.error('[Strategy API] User ID being used:', derivedUserId);
      console.error('[Strategy API] Bot ID being used:', bot_id);
      return NextResponse.json(
        {
          error: 'Failed to create strategy in PostgreSQL',
          debug: {
            strategy_name: strategy.name,
            user_id: derivedUserId,
            bot_id: bot_id,
            wallet_source: walletSource,
            timestamp: new Date().toISOString(),
            database_error: createResult.error_details || 'No detailed error available'
          }
        },
        { status: 500 }
      );
    }

    console.log(`[Strategy Manager] ✅ Strategy ${uniqueName} created in PostgreSQL`);

    // Only sync to bot instance if one is available
    if (!botInfo || !botInfo.api_port) {
      console.log(`[Strategy Manager] No bot instance available, strategy saved for later deployment`);
      return NextResponse.json({
        success: true,
        strategy: uniqueName,
        original_name: strategyName !== uniqueName ? strategyName : undefined,
        user_id: derivedUserId,
        message: `Strategy saved successfully (no bot instance available for immediate deployment)${strategyName !== uniqueName ? ` (renamed to ${uniqueName} due to name conflict)` : ''}`,
        status: 'pending_deployment',
        debug: {
          ...debugContext,
          botAvailable: false
        }
      });
    }

    // Now sync to bot instance
    console.log(`[Strategy Manager] Attempting to sync strategy to bot instance...`);

    const syncApiUrl = `http://localhost:${botInfo.api_port}/api/strategies/sync-from-postgres`;
    const syncResponse = await fetch(syncApiUrl, {
      method: 'POST',
      headers: orchestratorHeaders,
      body: JSON.stringify({ strategy_name: uniqueName }),
    });

    if (!syncResponse.ok) {
      // Fallback: try the old direct method with proper bot API format
      console.log('[Strategy Manager] Sync endpoint failed, trying direct method...');

      // Convert to bot API format using actual payload data only
      // Override name in a separate object to avoid polluting the original
      const strategyWithName = Object.assign({}, strategy, { name: uniqueName });
      const botApiStrategy = convertToBotApiFormat(strategyWithName as StrategyConfig);

      // The convertToBotApiFormat already handles all DynamicStrategyConfig fields
      const enhancedBotApiStrategy = botApiStrategy;

      console.log('[Strategy Manager] Original strategy object keys:', Object.keys(strategy));
      console.log('[Strategy Manager] Strategy with name keys:', Object.keys(strategyWithName));
      console.log('[Strategy Manager] Bot API strategy keys:', Object.keys(botApiStrategy));
      console.log('[Strategy Manager] Enhanced bot API strategy keys:', Object.keys(enhancedBotApiStrategy));
      console.log('[Strategy Manager] Sending to bot API:', JSON.stringify(enhancedBotApiStrategy, null, 2));

      const botApiUrl = `http://localhost:${botInfo.api_port}/api/strategies`;
      const requestBody = JSON.stringify(enhancedBotApiStrategy);
      const botResponse = await fetch(botApiUrl, {
        method: 'POST',
        headers: orchestratorHeaders,
        body: requestBody,
      });

      if (!botResponse.ok) {
        const errorText = await botResponse.text();
        console.error(`[Strategy Manager] Bot API failed with status ${botResponse.status}:`, errorText);
        return NextResponse.json(
          {
            error: `Bot API error: ${errorText}`,
            debug_connection: {
              bot_api_url: botApiUrl,
              bot_info: botInfo,
              headers_sent: orchestratorHeaders,
              request_body: requestBody,
              response_status: botResponse.status,
              response_status_text: botResponse.statusText,
              manual_test_curl: `curl -X POST "${botApiUrl}" -H "Content-Type: application/json" ${orchestratorHeaders['X-Wallet-Address'] ? `-H "X-Wallet-Address: ${orchestratorHeaders['X-Wallet-Address']}"` : ''} -d '${requestBody}'`
            }
          },
          { status: 502 }
        );
      }

      const botResult = await botResponse.json();
      console.log('[Strategy Manager] Bot API response:', JSON.stringify(botResult, null, 2));

      if (botResult.success) {
        return NextResponse.json({
          success: true,
          assigned_bot: bot_id,
          strategy: uniqueName,
          original_name: strategyName !== uniqueName ? strategyName : undefined,
          user_id: derivedUserId,
          message: `Strategy deployed successfully to bot ${bot_id}${strategyName !== uniqueName ? ` (renamed to ${uniqueName} due to name conflict)` : ''}`,
          bot_response: botResult,
          debug: {
            ...debugContext,
            syncEndpointUsed: false,
            botResponseStatus: botResponse.status,
          }
        });
      } else {
        console.error('[Strategy Manager] Bot returned failure:', botResult);
        return NextResponse.json({
          error: `Bot deployment failed: ${botResult.message || 'Unknown bot error'}`,
          bot_details: botResult,
          user_id: derivedUserId,
          debug: {
            ...debugContext,
            syncEndpointUsed: false,
            botResponseStatus: botResponse.status,
          }
        }, { status: 422 });
      }
    } else {
      // Sync endpoint succeeded
      const syncResult = await syncResponse.json();
      console.log('[Strategy Manager] Sync successful:', JSON.stringify(syncResult, null, 2));
      return NextResponse.json({
        success: true,
        assigned_bot: bot_id,
        strategy: uniqueName,
        original_name: strategyName !== uniqueName ? strategyName : undefined,
        user_id: derivedUserId,
        message: `Strategy deployed successfully to bot ${bot_id} (sync method)${strategyName !== uniqueName ? ` (renamed to ${uniqueName} due to name conflict)` : ''}`,
        sync_response: syncResult,
        debug: {
          ...debugContext,
          syncEndpointUsed: true,
          botResponseStatus: syncResponse.status,
        }
      });
    }

  } catch (error) {
    console.error('Failed to add strategy - Full error details:', error);
    return NextResponse.json(
      {
        error: 'Failed to add strategy',
        details: error.message,
        stack: error.stack,
        debug_connection: {
          bot_selected: botInfo,
          bot_api_url: botInfo ? `http://localhost:${botInfo.api_port}/api/strategies` : 'no_bot_selected',
          headers_sent: orchestratorHeaders,
          error_type: error.constructor.name,
          error_cause: error.cause,
          error_code: error.code
        }
      },
      { status: 500 }
    );
  }
}

// DELETE /api/strategies - Delete specific strategy by name or all strategies from a bot
export async function DELETE(request: NextRequest) {
  try {
    const url = new URL(request.url);
    const bot_id = url.searchParams.get('bot_id');
    const strategy_name = url.searchParams.get('strategy_name');

    // Support both deletion patterns:
    // 1. Delete specific strategy by name (user-friendly)
    // 2. Delete all strategies from specific bot (admin function)

    if (strategy_name) {
      // User-friendly: Delete specific strategy by name
      return await deleteStrategyByName(strategy_name);
    } else if (bot_id) {
      // Admin function: Delete all strategies from specific bot
      return await deleteAllStrategiesFromBot(bot_id);
    } else {
      return NextResponse.json(
        { error: 'Either strategy_name or bot_id parameter is required' },
        { status: 400 }
      );
    }
  } catch (error) {
    console.error('Failed to delete strategy:', error);
    return NextResponse.json(
      { error: 'Failed to delete strategy' },
      { status: 500 }
    );
  }
}

// Helper function: Delete specific strategy by name (user-friendly)
async function deleteStrategyByName(strategyName: string) {
  try {
    console.log(`[Strategy API] Deleting strategy by name: ${strategyName}`);

    // First, find which bot this strategy belongs to
    const client = await database.getClient();
    let strategyInfo: any = null;

    try {
      const strategyQuery = `
        SELECT hsc.name, hsc.hive_id, hi.hostname, hi.api_port, hi.status
        FROM hive_strategy_configs hsc
        LEFT JOIN hive_instances hi ON hsc.hive_id = hi.hive_id
        WHERE hsc.name = $1
      `;
      const result = await client.query(strategyQuery, [strategyName]);

      if (result.rows.length === 0) {
        return NextResponse.json(
          { error: 'Strategy not found' },
          { status: 404 }
        );
      }

      strategyInfo = result.rows[0];
      console.log(`[Strategy API] Found strategy on bot: ${strategyInfo.hive_id}`);
    } finally {
      if ('release' in client) {
        client.release();
      } else {
        await client.end();
      }
    }

    // Delete from database first
    const deleteClient = await database.getClient();
    try {
      const deleteQuery = `DELETE FROM hive_strategy_configs WHERE name = $1`;
      const deleteResult = await deleteClient.query(deleteQuery, [strategyName]);

      if (deleteResult.rowCount === 0) {
        return NextResponse.json(
          { error: 'Strategy not found in database' },
          { status: 404 }
        );
      }

      console.log(`[Strategy API] Deleted ${strategyName} from database`);
    } finally {
      if ('release' in deleteClient) {
        deleteClient.release();
      } else {
        await deleteClient.end();
      }
    }

    // If bot is available, also delete from bot instance
    if (strategyInfo.api_port) {
      try {
        const botApiUrl = `http://localhost:${strategyInfo.api_port}/api/strategies/${strategyName}`;
        const botResponse = await fetch(botApiUrl, { method: 'DELETE' });

        if (botResponse.ok) {
          console.log(`[Strategy API] Successfully deleted ${strategyName} from bot`);
        } else {
          console.log(`[Strategy API] Failed to delete from bot, but database cleanup completed`);
        }
      } catch (error) {
        console.log(`[Strategy API] Bot deletion failed, but database cleanup completed:`, error);
      }
    }

    return NextResponse.json({
      success: true,
      message: `Strategy ${strategyName} deleted successfully`,
      strategy: strategyName
    });

  } catch (error) {
    console.error(`Failed to delete strategy ${strategyName}:`, error);
    return NextResponse.json(
      { error: 'Failed to delete strategy' },
      { status: 500 }
    );
  }
}

// Helper function: Delete all strategies from specific bot (admin function)
async function deleteAllStrategiesFromBot(botId: string) {
  try {
    console.log(`[Strategy API] Deleting all strategies from bot: ${botId}`);

    // Get bot info and strategies from database
    const client = await database.getClient();
    let botInfo: any = null;
    let strategies: any[] = [];

    try {
      // Get bot info with more lenient time constraint
      const botQuery = `
        SELECT hive_id, hostname, api_port, status
        FROM hive_instances
        WHERE hive_id = $1
        ORDER BY last_seen DESC
        LIMIT 1
      `;
      const botResult = await client.query(botQuery, [botId]);

      if (botResult.rows.length === 0) {
        console.log(`[Strategy API] Bot ${botId} not found in hive_instances`);
        return NextResponse.json(
          { error: `Bot ${botId} not found` },
          { status: 404 }
        );
      }

      botInfo = botResult.rows[0];
      console.log(`[Strategy API] Found bot info:`, botInfo);

      // Get strategies from database for this bot
      const strategiesQuery = `
        SELECT name, hive_id
        FROM hive_strategy_configs
        WHERE hive_id = $1 AND enabled = true
      `;
      const strategiesResult = await client.query(strategiesQuery, [botId]);
      strategies = strategiesResult.rows;
      console.log(`[Strategy API] Found ${strategies.length} strategies in database for bot ${botId}`);

    } finally {
      if ('release' in client) {
        client.release();
      } else {
        await client.end();
      }
    }

    // Delete each strategy from database first, then try bot API
    const deleteResults = [];
    const deleteClient = await database.getClient();

    try {
      for (const strategy of strategies) {
        try {
          // Delete from database
          const deleteQuery = `DELETE FROM hive_strategy_configs WHERE name = $1 AND hive_id = $2`;
          const deleteResult = await deleteClient.query(deleteQuery, [strategy.name, botId]);

          let botDeletionSuccess = false;
          let botError = null;

          // Try to delete from bot API if bot info is available
          if (botInfo && botInfo.api_port) {
            try {
              // Map hostname correctly - use localhost for local calls from server
              const apiHost = botInfo.hostname.includes('local') || botInfo.hostname.includes('localhost') ? 'localhost' : botInfo.hostname;
              const deleteUrl = `http://${apiHost}:${botInfo.api_port}/api/strategies/${strategy.name}`;
              console.log(`[Strategy API] Attempting to delete ${strategy.name} from ${deleteUrl}`);

              const botDeleteResponse = await fetch(deleteUrl, {
                method: 'DELETE',
                timeout: 10000 // 10 second timeout
              });

              botDeletionSuccess = botDeleteResponse.ok;
              if (!botDeleteResponse.ok) {
                const errorText = await botDeleteResponse.text();
                botError = `Bot API error: ${botDeleteResponse.status} - ${errorText}`;
              }
            } catch (error) {
              botError = `Bot API connection failed: ${error.message}`;
            }
          }

          deleteResults.push({
            name: strategy.name,
            database_success: deleteResult.rowCount > 0,
            bot_success: botDeletionSuccess,
            bot_error: botError,
            overall_success: deleteResult.rowCount > 0 // Consider successful if DB deletion worked
          });

          console.log(`[Strategy API] Deleted ${strategy.name}: DB=${deleteResult.rowCount > 0}, Bot=${botDeletionSuccess}`);

        } catch (error) {
          console.error(`[Strategy API] Failed to delete ${strategy.name}:`, error);
          deleteResults.push({
            name: strategy.name,
            database_success: false,
            bot_success: false,
            error: String(error),
            overall_success: false
          });
        }
      }
    } finally {
      if ('release' in deleteClient) {
        deleteClient.release();
      } else {
        await deleteClient.end();
      }
    }

    const successCount = deleteResults.filter(r => r.overall_success).length;
    const message = `Successfully deleted ${successCount}/${deleteResults.length} strategies from bot ${botId}`;

    console.log(`[Strategy API] ${message}`);

    return NextResponse.json({
      success: true,
      bot_id: botId,
      deleted_strategies: deleteResults,
      success_count: successCount,
      total_count: deleteResults.length,
      message: message
    });

  } catch (error) {
    console.error('Failed to delete strategies from bot:', error);
    return NextResponse.json(
      { error: 'Failed to delete strategies', details: error.message },
      { status: 500 }
    );
  }
}

// PUT /api/strategies/refresh-metrics - Refresh strategy metrics from activities
export async function PUT() {
  try {
    console.log('[Strategy Manager] Refreshing strategy metrics from activities...');

    const success = await database.updateStrategyMetricsFromActivities();

    if (success) {
      return NextResponse.json({
        success: true,
        message: 'Strategy metrics refreshed successfully from activities',
        timestamp: new Date().toISOString()
      });
    } else {
      return NextResponse.json(
        { success: false, message: 'No strategies updated or update failed' },
        { status: 500 }
      );
    }

  } catch (error) {
    console.error('Failed to refresh strategy metrics:', error);
    return NextResponse.json(
      { error: 'Failed to refresh strategy metrics', details: error.message },
      { status: 500 }
    );
  }
}
