import { NextRequest, NextResponse } from 'next/server';
import { database } from '@/lib/database';

// GET /api/strategies/[name] - Get specific strategy details
export async function GET(
  request: NextRequest,
  { params }: { params: { name: string } }
) {
  try {
    const strategyName = params.name;
    const client = await database.getClient();

    try {
      const strategyQuery = `
        SELECT
          hs.hive_id,
          hs.strategy_name,
          hs.status,
          hs.total_actions,
          hs.successful_orders,
          hs.failed_orders,
          hs.refresh_interval,
          hs.performance_per_min,
          hs.updated_at,
          hi.hostname,
          hi.api_port,
          hi.last_seen
        FROM hive_strategies hs
        JOIN hive_instances hi ON hs.hive_id = hi.hive_id
        WHERE hs.strategy_name = $1 AND hi.last_seen >= NOW() - INTERVAL '5 minutes'
        ORDER BY hs.updated_at DESC
        LIMIT 1
      `;

      const result = await client.query(strategyQuery, [strategyName]);

      if (result.rows.length === 0) {
        return NextResponse.json(
          { error: 'Strategy not found or bot offline' },
          { status: 404 }
        );
      }

      const row = result.rows[0];
      const strategy = {
        bot_id: row.hive_id,
        bot_hostname: row.hostname,
        bot_port: row.api_port,
        bot_last_seen: row.last_seen,
        name: row.strategy_name,
        status: row.status,
        total_actions: parseInt(row.total_actions) || 0,
        successful_orders: parseInt(row.successful_orders) || 0,
        failed_orders: parseInt(row.failed_orders) || 0,
        refresh_interval: parseFloat(row.refresh_interval) || 0,
        performance_per_min: parseFloat(row.performance_per_min) || 0,
        updated_at: row.updated_at
      };

      return NextResponse.json({
        strategy,
        timestamp: new Date().toISOString()
      });

    } finally {
      if ('release' in client) {
        client.release();
      } else {
        await client.end();
      }
    }

  } catch (error) {
    console.error('Failed to fetch strategy:', error);
    return NextResponse.json(
      { error: 'Failed to fetch strategy' },
      { status: 500 }
    );
  }
}

// DELETE /api/strategies/[name] - Delete specific strategy from its bot
export async function DELETE(
  request: NextRequest,
  { params }: { params: { name: string } }
) {
  try {
    const strategyName = params.name;
    const client = await database.getClient();
    let botInfo: any = null;

    try {
      // First find which bot has this strategy
      // For DELETE operations with position closing, allow offline bots for cleanup
      const url = new URL(request.url);
      const closePositions = url.searchParams.get('close_positions') === 'true';
      
      const strategyQuery = closePositions 
        ? `
          SELECT
            hsc.hive_id,
            hi.hostname,
            hi.api_port,
            hi.status
          FROM hive_strategy_configs hsc
          JOIN hive_instances hi ON hsc.hive_id = hi.hive_id
          WHERE hsc.name = $1
          ORDER BY hi.last_seen DESC
          LIMIT 1
        `
        : `
          SELECT
            hsc.hive_id,
            hi.hostname,
            hi.api_port,
            hi.status
          FROM hive_strategy_configs hsc
          JOIN hive_instances hi ON hsc.hive_id = hi.hive_id
          WHERE hsc.name = $1 AND hi.last_seen >= NOW() - INTERVAL '5 minutes'
          LIMIT 1
        `;

      const strategyResult = await client.query(strategyQuery, [strategyName]);

      if (strategyResult.rows.length === 0) {
        return NextResponse.json(
          { error: closePositions ? 'Strategy not found' : 'Strategy not found or bot offline' },
          { status: 404 }
        );
      }

      botInfo = strategyResult.rows[0];
    } finally {
      if ('release' in client) {
        client.release();
      } else {
        await client.end();
      }
    }

    // Call bot instance API to delete strategy with cleanup parameters
    const url = new URL(request.url);
    const queryParams = url.searchParams.toString();
    const botApiUrl = `http://localhost:${botInfo.api_port}/api/strategies/${strategyName}${queryParams ? `?${queryParams}` : ''}`;
    console.log(`[Dashboard DELETE] Forwarding to bot API: ${botApiUrl}`);

    const botResponse = await fetch(botApiUrl, {
      method: 'DELETE',
    });

    if (!botResponse.ok) {
      const errorText = await botResponse.text();
      return NextResponse.json(
        { error: `Bot API error: ${errorText}` },
        { status: 500 }
      );
    }

    const botResult = await botResponse.json();

    // Update PostgreSQL to remove strategy record
    const pgClient = await database.getClient();
    try {
      const deleteQuery = `
        DELETE FROM hive_strategy_configs
        WHERE name = $1 AND hive_id = $2
      `;
      await pgClient.query(deleteQuery, [strategyName, botInfo.hive_id]);
    } finally {
      if ('release' in pgClient) {
        pgClient.release();
      } else {
        await pgClient.end();
      }
    }

    return NextResponse.json({
      success: true,
      bot_id: botInfo.hive_id,
      strategy_name: strategyName,
      message: 'Strategy deleted successfully',
      bot_response: botResult
    });

  } catch (error) {
    console.error('Failed to delete strategy:', error);
    return NextResponse.json(
      { error: 'Failed to delete strategy' },
      { status: 500 }
    );
  }
}

// PUT /api/strategies/[name] - Update specific strategy configuration
export async function PUT(
  request: NextRequest,
  { params }: { params: { name: string } }
) {
  try {
    const strategyName = params.name;
    const body = await request.json();
    const { config } = body;

    if (!config) {
      return NextResponse.json(
        { error: 'config parameter is required' },
        { status: 400 }
      );
    }

    const client = await database.getClient();
    let botInfo: any = null;

    try {
      // Find which bot has this strategy
      const strategyQuery = `
        SELECT
          hs.hive_id,
          hi.hostname,
          hi.api_port,
          hi.status
        FROM hive_strategies hs
        JOIN hive_instances hi ON hs.hive_id = hi.hive_id
        WHERE hs.strategy_name = $1 AND hi.last_seen >= NOW() - INTERVAL '5 minutes'
        LIMIT 1
      `;

      const strategyResult = await client.query(strategyQuery, [strategyName]);

      if (strategyResult.rows.length === 0) {
        return NextResponse.json(
          { error: 'Strategy not found or bot offline' },
          { status: 404 }
        );
      }

      botInfo = strategyResult.rows[0];
    } finally {
      if ('release' in client) {
        client.release();
      } else {
        await client.end();
      }
    }

    // Call bot instance API to update strategy
    const botApiUrl = `http://localhost:${botInfo.api_port}/api/strategies/${strategyName}`;
    const botResponse = await fetch(botApiUrl, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    });

    if (!botResponse.ok) {
      const errorText = await botResponse.text();
      return NextResponse.json(
        { error: `Bot API error: ${errorText}` },
        { status: 500 }
      );
    }

    const botResult = await botResponse.json();

    return NextResponse.json({
      success: true,
      bot_id: botInfo.hive_id,
      strategy_name: strategyName,
      message: 'Strategy updated successfully',
      bot_response: botResult
    });

  } catch (error) {
    console.error('Failed to update strategy:', error);
    return NextResponse.json(
      { error: 'Failed to update strategy' },
      { status: 500 }
    );
  }
}
