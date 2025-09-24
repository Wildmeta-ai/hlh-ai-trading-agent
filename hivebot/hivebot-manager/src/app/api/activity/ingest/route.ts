import { NextResponse } from 'next/server';
import { database } from '@/lib/database';

interface ActivityData {
  time: string;
  type: string;
  success: boolean;
  strategy: string;

  // **ADDED**: Order details for complete tracking
  order_id?: string;
  price?: number;
  amount?: number;
  trading_pair?: string;
}

interface StrategyData {
  strategy: string;
  total_actions: number;
  successful_orders: number;
  failed_orders: number;
  last_action_time: string | null;
  status: 'ACTIVE' | 'IDLE' | 'WAITING' | 'ERROR';
  refresh_interval: number;
  performance_per_min: number;
  recent_actions: ActivityData[];
}

interface MarketData {
  symbol: string;
  price: number;
  timestamp: string;
  connection_status: string;
}

interface IngestPayload {
  hive_id: string;
  hostname: string;
  strategies: StrategyData[];
  activities: ActivityData[];
  market_data: MarketData;
  timestamp: string;
}

export async function POST(request: Request) {
  try {
    const payload: IngestPayload = await request.json();

    // Validate required fields
    if (!payload.hive_id || !payload.hostname || !payload.timestamp) {
      return NextResponse.json(
        { error: 'Missing required fields: hive_id, hostname, timestamp' },
        { status: 400 }
      );
    }

    // Get database client with connection pooling
    const client = await database.getClient();

    try {
      // Update hive instance heartbeat with optional api_port
      const hasApiPort = payload.api_port && typeof payload.api_port === 'number';

      if (hasApiPort) {
        // Include api_port in the update
        await client.query(`
          INSERT INTO hive_instances (
            hive_id, hostname, api_port, last_seen, market_data, status
          ) VALUES ($1, $2, $3, $4, $5, 'active')
          ON CONFLICT (hive_id)
          DO UPDATE SET
            hostname = EXCLUDED.hostname,
            api_port = EXCLUDED.api_port,
            last_seen = EXCLUDED.last_seen,
            market_data = EXCLUDED.market_data,
            status = EXCLUDED.status
        `, [
          payload.hive_id,
          payload.hostname,
          payload.api_port,
          new Date(),
          JSON.stringify(payload.market_data || {})
        ]);
      } else {
        // Don't update api_port if not provided
        await client.query(`
          INSERT INTO hive_instances (
            hive_id, hostname, last_seen, market_data, status
          ) VALUES ($1, $2, $3, $4, 'active')
          ON CONFLICT (hive_id)
          DO UPDATE SET
            hostname = EXCLUDED.hostname,
            last_seen = EXCLUDED.last_seen,
            market_data = EXCLUDED.market_data,
            status = EXCLUDED.status
        `, [
          payload.hive_id,
          payload.hostname,
          new Date(),
          JSON.stringify(payload.market_data || {})
        ]);
      }

      // Log individual activities to hive_activities table
      if (payload.activities && payload.activities.length > 0) {
        for (const activity of payload.activities) {
          try {
            await client.query(`
              INSERT INTO hive_activities (
                hive_id, strategy_name, activity_type, success, timestamp,
                order_id, price, amount, trading_pair
              ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
              ON CONFLICT (hive_id, strategy_name, activity_type, timestamp)
              DO UPDATE SET
                order_id = EXCLUDED.order_id,
                price = EXCLUDED.price,
                amount = EXCLUDED.amount,
                trading_pair = EXCLUDED.trading_pair
            `, [
              payload.hive_id,
              activity.strategy,
              activity.type,
              activity.success,
              new Date(activity.time),
              activity.order_id || null,
              activity.price || null,
              activity.amount || null,
              activity.trading_pair || null
            ]);
          } catch (activityError) {
            console.warn(`Failed to log activity for ${payload.hive_id}:`, activityError);
            // Continue processing other activities
          }
        }

        console.log(`📝 Logged ${payload.activities.length} activities to database`);
      }

      // Calculate bot-level activity rate from recent activities
      const totalActions = payload.strategies.reduce((sum, strategy) => sum + (strategy.total_actions || 0), 0);
      const totalStrategies = payload.strategies.length;

      // Calculate actions per minute from recent activities (last 5 minutes)
      const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000);
      const recentActivitiesCount = payload.activities.filter(activity =>
        new Date(activity.time) >= fiveMinutesAgo
      ).length;
      const actionsPerMinute = recentActivitiesCount / 5; // Actions in last 5 minutes ÷ 5 = actions per minute

      // Also update or create bot_runs entry for dashboard compatibility
      try {
        // Check if bot already exists (same pattern as database.ts)
        const checkQuery = `SELECT id FROM bot_runs WHERE instance_name = $1 LIMIT 1`;
        const existingBot = await client.query(checkQuery, [payload.hive_id]);

        console.log(`🔍 Bot lookup for ${payload.hive_id}: found ${existingBot.rows.length} existing records`);

        const deploymentConfig = JSON.stringify({
          active_strategies: totalStrategies,
          api_port: 8080,
          total_actions: totalActions,
          actions_per_minute: actionsPerMinute,
          memory_usage: 0,
          cpu_usage: 0
        });

        // Use UPSERT to prevent duplicates - single query handles both insert and update
        const upsertQuery = `
          INSERT INTO bot_runs (
            bot_name, instance_name, deployed_at, strategy_type, strategy_name,
            config_name, deployment_status, run_status, account_name,
            image_version, deployment_config, last_heartbeat
          ) VALUES ($1, $2, NOW(), $3, $4, $5, $6, $7, $8, $9, $10, NOW())
          ON CONFLICT (instance_name)
          DO UPDATE SET
            deployment_status = EXCLUDED.deployment_status,
            run_status = EXCLUDED.run_status,
            deployment_config = EXCLUDED.deployment_config,
            last_heartbeat = NOW()
          RETURNING id;
        `;

        await client.query(upsertQuery, [
          payload.hive_id,        // bot_name
          payload.hive_id,        // instance_name
          'multi-strategy',       // strategy_type
          'hive-orchestrator',    // strategy_name
          'live_config',          // config_name
          'running',              // deployment_status
          'running',              // run_status
          'live_account',         // account_name
          'v1.0',                 // image_version
          deploymentConfig        // deployment_config
        ]);
      } catch (botRunsError) {
        console.warn(`Failed to update bot_runs for ${payload.hive_id}:`, botRunsError);
        console.warn('Error details:', botRunsError.message);
      }

      // Log successful ingestion
      console.log(`✅ Ingested heartbeat from ${payload.hive_id}: ${payload.strategies.length} strategies, ${payload.activities.length} activities, ${actionsPerMinute.toFixed(1)} actions/min (${recentActivitiesCount} in last 5min)`);

      return NextResponse.json({
        success: true,
        message: 'Hive heartbeat recorded successfully',
        hive_id: payload.hive_id,
        strategies_count: payload.strategies.length,
        activities_count: payload.activities.length
      });

    } catch (dbError) {
      console.error('Database error in activity ingest:', dbError);
      throw dbError;
    } finally {
      // Always release the database connection back to the pool
      if ('release' in client) {
        client.release();
      } else {
        await client.end();
      }
    }

  } catch (error) {
    console.error('Failed to ingest activity data:', error);

    return NextResponse.json({
      success: false,
      error: 'Failed to ingest activity data',
      details: error instanceof Error ? error.message : 'Unknown error'
    }, { status: 500 });
  }
}

// GET method to check ingest endpoint status
export async function GET() {
  return NextResponse.json({
    endpoint: '/api/activity/ingest',
    description: 'Ingests activity data from Hive instances',
    status: 'operational',
    timestamp: new Date().toISOString()
  });
}
