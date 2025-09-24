import { NextResponse } from 'next/server';
import { database } from '@/lib/database';

interface ActivityData {
  time: string;
  type: string;
  success: boolean;
  strategy: string;
  hive_id?: string;

  // **ADDED**: Order details for complete activity tracking
  order_id?: string;
  price?: number;
  amount?: number;
  trading_pair?: string;
}

interface StrategyActivityData {
  strategy: string;
  recent_actions: ActivityData[];
  performance_per_min: number;
  status: 'ACTIVE' | 'IDLE' | 'WAITING' | 'ERROR';
  refresh_interval: number;
  total_actions: number;
  successful_orders: number;
  failed_orders: number;
  last_action_time: string | null;
  hive_id?: string;
  hostname?: string;
}

export async function GET() {
  try {
    // Get database client and query real activity data
    const client = await database.getClient();

    try {
      // Get recent activities (last 100)
      const activitiesQuery = `
        SELECT hive_id, strategy_name, activity_type, success, timestamp,
               order_id, price, amount, trading_pair
        FROM hive_activities
        WHERE timestamp >= NOW() - INTERVAL '1 hour'
        ORDER BY timestamp DESC
        LIMIT 100
      `;
      const activitiesResult = await client.query(activitiesQuery);

      // Get strategies with their metrics calculated from actual activities (not redundant fields)
      const strategiesQuery = `
        SELECT DISTINCT
          hsc.name as strategy_name,
          hsc.hive_id,
          hi.hostname,
          hi.market_data,

          -- Calculate actual metrics from hive_activities table
          COALESCE(activity_stats.total_actions, 0) as total_actions,
          COALESCE(activity_stats.successful_orders, 0) as successful_orders,
          COALESCE(activity_stats.failed_orders, 0) as failed_orders,
          activity_stats.last_action_time,

          -- Status based on recent activity (not redundant field)
          CASE
            WHEN activity_stats.last_action_time >= NOW() - INTERVAL '2 minutes' THEN 'ACTIVE'
            WHEN activity_stats.last_action_time >= NOW() - INTERVAL '10 minutes' THEN 'IDLE'
            WHEN activity_stats.last_action_time IS NOT NULL THEN 'WAITING'
            ELSE 'PENDING'
          END as status,

          -- Performance calculated from actual activity frequency
          COALESCE(
            ROUND(
              (activity_stats.actions_last_hour::DECIMAL / NULLIF(EXTRACT(EPOCH FROM LEAST(NOW() - activity_stats.first_action_time, INTERVAL '1 hour'))::DECIMAL / 60, 0))
            , 2), 0
          ) as performance_per_min,

          -- Default refresh interval
          COALESCE(hsc.order_refresh_time, 5.0) as refresh_interval

        FROM hive_strategy_configs hsc
        JOIN hive_instances hi ON hsc.hive_id = hi.hive_id
        LEFT JOIN (
          SELECT
            strategy_name,
            hive_id,
            COUNT(*) as total_actions,
            COUNT(*) FILTER (WHERE success = true) as successful_orders,
            COUNT(*) FILTER (WHERE success = false) as failed_orders,
            MAX(timestamp) as last_action_time,
            MIN(timestamp) as first_action_time,
            COUNT(*) FILTER (WHERE timestamp >= NOW() - INTERVAL '1 hour') as actions_last_hour
          FROM hive_activities
          WHERE timestamp >= NOW() - INTERVAL '24 hours'
          GROUP BY strategy_name, hive_id
        ) activity_stats ON hsc.name = activity_stats.strategy_name AND hsc.hive_id = activity_stats.hive_id
        WHERE hi.last_seen >= NOW() - INTERVAL '10 minutes'
          AND hsc.enabled = true
        ORDER BY activity_stats.last_action_time DESC NULLS LAST
      `;
      const strategiesResult = await client.query(strategiesQuery);

      // Convert activities to API format
      const activities: ActivityData[] = activitiesResult.rows.map((row: any) => ({
        time: row.timestamp.toISOString(),
        type: row.activity_type,
        success: row.success,
        strategy: row.strategy_name,
        hive_id: row.hive_id,

        // **ADDED**: Include order details from hive_activities table
        order_id: row.order_id,
        price: row.price ? parseFloat(row.price) : undefined,
        amount: row.amount ? parseFloat(row.amount) : undefined,
        trading_pair: row.trading_pair
      }));

      // Convert strategies to API format, building recent_actions from actual activities
      const strategies: StrategyActivityData[] = strategiesResult.rows.map((row: any) => {
        // Get recent actions for this strategy from the activities we already fetched
        const recentActions: ActivityData[] = activities
          .filter(activity =>
            activity.strategy === row.strategy_name &&
            activity.hive_id === row.hive_id
          )
          .slice(0, 32) // Last 32 actions for the activity grid
          .map(activity => ({
            time: activity.time,
            type: activity.type,
            success: activity.success,
            strategy: activity.strategy,
            hive_id: activity.hive_id,
            order_id: activity.order_id,
            price: activity.price,
            amount: activity.amount,
            trading_pair: activity.trading_pair
          }));

        console.log(`[Activity API] Strategy ${row.strategy_name} (${row.hive_id}): ${recentActions.length} recent actions`);

        return {
          strategy: row.strategy_name,
          recent_actions: recentActions,
          performance_per_min: parseFloat(row.performance_per_min) || 0,
          status: row.status as 'ACTIVE' | 'IDLE' | 'WAITING' | 'ERROR',
          refresh_interval: parseFloat(row.refresh_interval) || 5.0,
          total_actions: parseInt(row.total_actions) || 0,
          successful_orders: parseInt(row.successful_orders) || 0,
          failed_orders: parseInt(row.failed_orders) || 0,
          last_action_time: row.last_action_time ? row.last_action_time.toISOString() : null,
          hive_id: row.hive_id,
          hostname: row.hostname
        };
      });

      // Get market data from the most recent hive instance
      let marketData = {
        symbol: 'BTC-USD',
        price: 0,
        connection_status: 'DISCONNECTED',
        timestamp: new Date().toISOString()
      };

      if (strategiesResult.rows.length > 0) {
        try {
          const latestMarketData = strategiesResult.rows[0].market_data;
          if (latestMarketData) {
            marketData = {
              ...marketData,
              ...JSON.parse(JSON.stringify(latestMarketData))
            };
          }
        } catch (e) {
          console.warn('Failed to parse market data');
        }
      }

      const status = strategies.length > 0 ? 'live' : 'no_data';
      const lastUpdate = strategies.length > 0 ?
        strategies[0].last_action_time || new Date().toISOString() :
        new Date().toISOString();

      return NextResponse.json({
        activities,
        strategies,
        status,
        lastUpdate,
        marketData,
        meta: {
          total_strategies: strategies.length,
          total_activities: activities.length,
          active_hive_instances: new Set(strategies.map(s => s.hive_id)).size
        }
      });

    } finally {
      await client.end();
    }

  } catch (error) {
    console.error('Failed to fetch activity data from database:', error);

    // No fake data - return empty arrays on database error
    return NextResponse.json({
      activities: [],
      strategies: [],
      status: 'error',
      lastUpdate: new Date().toISOString(),
      marketData: {
        symbol: 'UNKNOWN',
        price: 0,
        connection_status: 'DISCONNECTED'
      },
      error: 'Database connection failed - no data available'
    });
  }
}
