import { NextResponse } from 'next/server';
import { database } from '@/lib/database';

export async function GET() {
  try {
    const client = await database.getClient();

    try {
      // Test 1: Check what's in hive_activities
      const activitiesResult = await client.query(`
        SELECT strategy_name, hive_id, COUNT(*) as count, MAX(timestamp) as latest
        FROM hive_activities
        WHERE timestamp >= NOW() - INTERVAL '24 hours'
        GROUP BY strategy_name, hive_id
        ORDER BY count DESC
        LIMIT 3
      `);

      // Test 2: Check what's in hive_strategy_configs
      const configsResult = await client.query(`
        SELECT name, hive_id
        FROM hive_strategy_configs
        WHERE enabled = true
        LIMIT 3
      `);

      // Test 3: Test the JOIN directly
      const joinResult = await client.query(`
        SELECT
          hsc.name,
          hsc.hive_id,
          activity_stats.total_actions,
          activity_stats.successful_orders
        FROM hive_strategy_configs hsc
        LEFT JOIN (
          SELECT
            strategy_name,
            hive_id,
            COUNT(*) as total_actions,
            COUNT(*) FILTER (WHERE success = true) as successful_orders
          FROM hive_activities
          WHERE timestamp >= NOW() - INTERVAL '24 hours'
          GROUP BY strategy_name, hive_id
        ) activity_stats ON hsc.name = activity_stats.strategy_name AND hsc.hive_id = activity_stats.hive_id
        WHERE hsc.enabled = true
        LIMIT 3
      `);

      return NextResponse.json({
        activities: activitiesResult.rows,
        configs: configsResult.rows,
        joinResults: joinResult.rows
      });

    } finally {
      if ('release' in client) {
        client.release();
      } else {
        await client.end();
      }
    }

  } catch (error) {
    console.error('Debug query failed:', error);
    return NextResponse.json(
      { error: 'Debug query failed', details: error.message },
      { status: 500 }
    );
  }
}
