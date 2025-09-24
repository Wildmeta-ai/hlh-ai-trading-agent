import { NextRequest, NextResponse } from 'next/server';
import { database } from '@/lib/database';

interface StrategySnapshotSummary {
  strategy_name: string;
  hive_id: string | null;
  user_id: string | null;
  total_actions: number;
  successful_actions: number;
  failed_actions: number;
  total_volume: number;
  avg_trade_size: number;
  buy_count: number;
  sell_count: number;
  last_activity: string | null;
  unrealized_pnl: number;
  realized_pnl: number;
  position_size: number;
  positions: Array<{
    trading_pair: string;
    size: number;
    entry_price: number;
    mark_price: number;
    unrealized_pnl: number;
    leverage: number | null;
    timestamp: string | null;
  }>;
}

const toNumber = (value: unknown): number => {
  if (value === null || value === undefined) {
    return 0;
  }
  if (typeof value === 'number') {
    return Number.isFinite(value) ? value : 0;
  }
  const parsed = parseFloat(String(value));
  return Number.isFinite(parsed) ? parsed : 0;
};

const toDateIso = (value: unknown): string | null => {
  if (!value) return null;
  const date = value instanceof Date ? value : new Date(value as string);
  return Number.isFinite(date.getTime()) ? date.toISOString() : null;
};

async function captureStrategySnapshot(strategyName: string): Promise<StrategySnapshotSummary | null> {
  let client: any = null;
  try {
    client = await database.getClient();

    const configResult = await client.query(
      `SELECT hive_id, user_id FROM hive_strategy_configs WHERE name = $1 LIMIT 1`,
      [strategyName]
    );
    const configRow = configResult.rows[0] || {};
    const hiveId: string | null = configRow.hive_id || null;
    const userId: string | null = configRow.user_id || null;

    const activityArgs: any[] = [strategyName];
    const activityFilter = hiveId ? ' AND hive_id = $2' : '';
    if (hiveId) {
      activityArgs.push(hiveId);
    }

    const activityResult = await client.query(
      `
        SELECT
          COUNT(*) AS total_actions,
          COUNT(*) FILTER (WHERE success) AS successful_actions,
          COUNT(*) FILTER (WHERE NOT success) AS failed_actions,
          SUM(COALESCE(price, 0) * COALESCE(amount, 0)) AS total_volume,
          AVG(NULLIF(COALESCE(price, 0) * COALESCE(amount, 0), 0)) AS avg_trade_size,
          COUNT(*) FILTER (WHERE activity_type ILIKE '%BUY%') AS buy_count,
          COUNT(*) FILTER (WHERE activity_type ILIKE '%SELL%') AS sell_count,
          MAX(timestamp) AS last_activity
        FROM hive_activities
        WHERE strategy_name = $1${activityFilter}
      `,
      activityArgs
    );

    const activityRow = activityResult.rows[0] || {};

    const positionsResult = await client.query(
      `
        SELECT
          trading_pair,
          exchange_size,
          calculated_size,
          entry_price,
          calculated_entry_price,
          mark_price,
          unrealized_pnl,
          leverage,
          timestamp
        FROM position_snapshots
        WHERE account_name = $1
        ORDER BY timestamp DESC
        LIMIT 50
      `,
      [strategyName]
    );

    const seenPairs = new Set<string>();
    const positions: StrategySnapshotSummary['positions'] = [];
    let positionSize = 0;
    let unrealizedPnL = 0;

    for (const row of positionsResult.rows) {
      const pair: string = row.trading_pair || 'UNKNOWN';
      if (seenPairs.has(pair)) {
        continue;
      }
      seenPairs.add(pair);

      const size = toNumber(row.exchange_size ?? row.calculated_size);
      const entryPrice = toNumber(row.entry_price ?? row.calculated_entry_price);
      const markPrice = toNumber(row.mark_price ?? entryPrice);
      const pnl = toNumber(row.unrealized_pnl);
      const leverage = row.leverage !== undefined && row.leverage !== null ? toNumber(row.leverage) : null;
      const timestampIso = toDateIso(row.timestamp);

      positions.push({
        trading_pair: pair,
        size,
        entry_price: entryPrice,
        mark_price: markPrice,
        unrealized_pnl: pnl,
        leverage,
        timestamp: timestampIso
      });

      positionSize += Math.abs(size);
      unrealizedPnL += pnl;
    }

    const snapshotSummary: StrategySnapshotSummary = {
      strategy_name: strategyName,
      hive_id: hiveId,
      user_id: userId,
      total_actions: parseInt(activityRow.total_actions ?? 0, 10) || 0,
      successful_actions: parseInt(activityRow.successful_actions ?? 0, 10) || 0,
      failed_actions: parseInt(activityRow.failed_actions ?? 0, 10) || 0,
      total_volume: toNumber(activityRow.total_volume),
      avg_trade_size: toNumber(activityRow.avg_trade_size),
      buy_count: parseInt(activityRow.buy_count ?? 0, 10) || 0,
      sell_count: parseInt(activityRow.sell_count ?? 0, 10) || 0,
      last_activity: toDateIso(activityRow.last_activity),
      unrealized_pnl: unrealizedPnL,
      realized_pnl: 0,
      position_size: positionSize,
      positions
    };

    await database.recordStrategySnapshot({
      strategy_name: snapshotSummary.strategy_name,
      hive_id: snapshotSummary.hive_id,
      user_id: snapshotSummary.user_id,
      total_actions: snapshotSummary.total_actions,
      successful_actions: snapshotSummary.successful_actions,
      failed_actions: snapshotSummary.failed_actions,
      total_volume: snapshotSummary.total_volume,
      avg_trade_size: snapshotSummary.avg_trade_size,
      buy_count: snapshotSummary.buy_count,
      sell_count: snapshotSummary.sell_count,
      last_activity: snapshotSummary.last_activity ? new Date(snapshotSummary.last_activity) : null,
      unrealized_pnl: snapshotSummary.unrealized_pnl,
      realized_pnl: snapshotSummary.realized_pnl,
      position_size: snapshotSummary.position_size,
      metadata: {
        positions: snapshotSummary.positions
      }
    });

    return snapshotSummary;
  } catch (error) {
    console.warn(`[Close Strategy API] Failed to capture snapshot for ${strategyName}:`, error);
    return null;
  } finally {
    if (client) {
      if ('release' in client) {
        client.release();
      } else {
        await client.end();
      }
    }
  }
}

export async function POST(request: NextRequest) {
  try {
    const { strategy, closePositions = true, cancelOrders = true } = await request.json();

    if (!strategy) {
      return NextResponse.json(
        { error: 'Strategy name is required' },
        { status: 400 }
      );
    }

    console.log(`[Close Strategy API] Closing strategy: ${strategy}`);
    console.log(`[Close Strategy API] Close positions: ${closePositions}`);
    console.log(`[Close Strategy API] Cancel orders: ${cancelOrders}`);

    let snapshotSummary: StrategySnapshotSummary | null = null;
    try {
      snapshotSummary = await captureStrategySnapshot(strategy);
      if (snapshotSummary) {
        console.log(`[Close Strategy API] Snapshot recorded for ${strategy}`);
      }
    } catch (snapshotError) {
      console.warn(`[Close Strategy API] Unable to record snapshot for ${strategy}:`, snapshotError);
    }

    // Dynamically discover active bot instances from database
    let client: any = null;
    let hiveApiUrls: string[] = [];

    try {
      client = await database.getClient();
      const botsQuery = `
        SELECT DISTINCT hi.api_port, hi.hostname, hi.hive_id, hi.status, hi.last_seen
        FROM hive_instances hi
        WHERE hi.last_seen >= NOW() - INTERVAL '10 minutes'
          AND hi.status = 'active'
          AND hi.api_port IS NOT NULL
        ORDER BY hi.last_seen DESC
      `;
      const botsResult = await client.query(botsQuery);

      console.log(`[Close Strategy API] Found ${botsResult.rows.length} active bot instances:`, botsResult.rows);

      if (botsResult.rows.length === 0) {
        return NextResponse.json(
          {
            error: 'No active bot instances found',
            details: { discovered_bots: 0 },
            message: 'No running Hive orchestrators available to close strategies'
          },
          { status: 503 }
        );
      }

      // Build URLs from discovered bot instances
      for (const bot of botsResult.rows) {
        const hostname = bot.hostname.includes('local') ? 'localhost' : bot.hostname;
        hiveApiUrls.push(`http://${hostname}:${bot.api_port}`);
      }

    } catch (dbError) {
      console.error(`[Close Strategy API] Database query failed:`, dbError);
      return NextResponse.json(
        {
          error: 'Failed to discover bot instances',
          details: { database_error: dbError.message },
          message: 'Unable to query active bot instances from database'
        },
        { status: 500 }
      );
    } finally {
      if (client) {
        if ('release' in client) {
          client.release();
        } else {
          await client.end();
        }
      }
    }

    let success = false;
    let lastError = null;
    let connectionAttempts: Array<{url: string, error: string, status?: number}> = [];
    let cleanupInfo = {
      positions_closed: 0,
      orders_cancelled: 0,
      cleanup_errors: []
    };

    for (const baseUrl of hiveApiUrls) {
      try {
        console.log(`[Close Strategy API] Trying Hive API at ${baseUrl}`);

        // Step 1: Stop the strategy using the existing Hive API with cleanup options
        const queryParams = new URLSearchParams({
          close_positions: closePositions.toString(),
          cancel_orders: cancelOrders.toString()
        });

        const deleteUrl = `${baseUrl}/api/strategies/${encodeURIComponent(strategy)}?${queryParams}`;
        console.log(`[Close Strategy API] Attempting DELETE ${deleteUrl}`);

        const stopResponse = await fetch(deleteUrl, {
          method: 'DELETE',
          headers: {
            'Content-Type': 'application/json',
          },
        });

        if (stopResponse.ok) {
          const stopResult = await stopResponse.json();
          console.log(`[Close Strategy API] Strategy stopped successfully:`, stopResult);

          // Enhanced cleanup results from Hive API
          cleanupInfo = stopResult.cleanup || {
            positions_closed: 0,
            orders_cancelled: 0,
            cleanup_errors: []
          };

          console.log(`[Close Strategy API] Cleanup results:`, cleanupInfo);

          // Step 2: Force position refresh after closing
          try {
            const refreshUrl = `${baseUrl}/api/positions/force-sync`;
            console.log(`[Close Strategy API] Forcing position refresh at ${refreshUrl}`);

            const refreshResponse = await fetch(refreshUrl, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
            });

            if (refreshResponse.ok) {
              console.log(`[Close Strategy API] Position refresh triggered successfully`);
            } else {
              console.warn(`[Close Strategy API] Position refresh failed, but continuing...`);
            }
          } catch (refreshError) {
            console.warn(`[Close Strategy API] Could not trigger position refresh:`, refreshError);
          }

          success = true;
          break;
        } else {
          const errorText = await stopResponse.text();
          lastError = `HTTP ${stopResponse.status}: ${errorText}`;
          connectionAttempts.push({
            url: baseUrl,
            error: lastError,
            status: stopResponse.status
          });
          console.warn(`[Close Strategy API] Failed to stop strategy via ${baseUrl}: ${lastError}`);
        }
      } catch (error) {
        lastError = error;
        const errorMessage = error.message || String(error);
        connectionAttempts.push({
          url: baseUrl,
          error: errorMessage
        });
        console.warn(`[Close Strategy API] Connection failed to ${baseUrl}:`, error);

        // Check if it's a connection error (ECONNREFUSED, etc.)
        if (error.code === 'ECONNREFUSED' || errorMessage.includes('ECONNREFUSED')) {
          console.log(`[Close Strategy API] Connection refused to ${baseUrl} - service may not be running`);
        } else if (errorMessage.includes('fetch')) {
          console.log(`[Close Strategy API] Fetch error to ${baseUrl}: ${errorMessage}`);
        }
        continue;
      }
    }

    if (!success) {
      console.error(`[Close Strategy API] All Hive API endpoints failed. Last error:`, lastError);
      
      // FALLBACK: If normal strategy deletion failed but we want to close positions,
      // try the force close positions endpoint as a last resort
      if (closePositions) {
        console.log(`[Close Strategy API] Attempting force close positions as fallback...`);
        
        for (const baseUrl of hiveApiUrls) {
          try {
            const forceCloseUrl = `${baseUrl}/api/positions/force-close`;
            console.log(`[Close Strategy API] Trying force close at ${forceCloseUrl}`);
            
            const forceCloseResponse = await fetch(forceCloseUrl, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify({
                strategy_name: strategy
              })
            });
            
            if (forceCloseResponse.ok) {
              const forceCloseResult = await forceCloseResponse.json();
              console.log(`[Close Strategy API] Force close succeeded:`, forceCloseResult);

              // Mark strategy as disabled in database (soft delete) even in fallback case
              let dbUpdateSuccess = false;
              let dbClient: any = null;
              try {
                dbClient = await database.getClient();
                const updateQuery = `
                  UPDATE hive_strategy_configs
                  SET enabled = false,
                      updated_at = NOW()
                  WHERE name = $1
                `;
                const updateResult = await dbClient.query(updateQuery, [strategy]);
                dbUpdateSuccess = updateResult.rowCount > 0;

                if (dbUpdateSuccess) {
                  console.log(`[Close Strategy API] Strategy "${strategy}" marked as disabled in database (fallback)`);
                } else {
                  console.warn(`[Close Strategy API] Strategy "${strategy}" not found in database for disabling (fallback)`);
                }
              } catch (dbError) {
                console.error(`[Close Strategy API] Failed to disable strategy in database (fallback):`, dbError);
              } finally {
                if (dbClient) {
                  if ('release' in dbClient) {
                    dbClient.release();
                  } else {
                    await dbClient.end();
                  }
                }
              }

              // Return success with force close results
              return NextResponse.json({
                success: true,
                message: `Positions force closed for strategy "${strategy}" (strategy deletion failed)`,
                actions: {
                  strategyStopped: false,
                  positionsClosed: true,
                  ordersCancelled: false,
                  databaseDisabled: dbUpdateSuccess
                },
                cleanup: forceCloseResult.cleanup || {
                  positions_closed: 0,
                  orders_cancelled: 0,
                  cleanup_errors: []
                },
                snapshot: snapshotSummary,
                fallback_used: true,
                timestamp: new Date().toISOString()
              });
            } else {
              console.warn(`[Close Strategy API] Force close failed: ${forceCloseResponse.status}`);
            }
          } catch (forceError) {
            console.warn(`[Close Strategy API] Force close connection failed:`, forceError);
          }
        }
        
        console.error(`[Close Strategy API] Both normal deletion and force close failed`);
      }
      
      return NextResponse.json(
        {
          error: 'Failed to connect to Hive orchestrator',
          details: {
            discovered_bots: hiveApiUrls.length,
            connection_attempts: connectionAttempts,
            last_error: lastError
          },
          message: 'Please ensure the Hive orchestrator is running and accessible'
        },
        { status: 503 }
      );
    }

    // Mark strategy as disabled in database (soft delete)
    let dbUpdateSuccess = false;
    let dbClient: any = null;
    try {
      dbClient = await database.getClient();
      const updateQuery = `
        UPDATE hive_strategy_configs
        SET enabled = false,
            updated_at = NOW()
        WHERE name = $1
      `;
      const updateResult = await dbClient.query(updateQuery, [strategy]);
      dbUpdateSuccess = updateResult.rowCount > 0;

      if (dbUpdateSuccess) {
        console.log(`[Close Strategy API] Strategy "${strategy}" marked as disabled in database`);
      } else {
        console.warn(`[Close Strategy API] Strategy "${strategy}" not found in database for disabling`);
      }
    } catch (dbError) {
      console.error(`[Close Strategy API] Failed to disable strategy in database:`, dbError);
    } finally {
      if (dbClient) {
        if ('release' in dbClient) {
          dbClient.release();
        } else {
          await dbClient.end();
        }
      }
    }

    // Return success response with cleanup details
    return NextResponse.json({
      success: true,
      message: `Strategy "${strategy}" closed successfully`,
      actions: {
      strategyStopped: true,
      positionsClosed: closePositions,
      ordersCancelled: cancelOrders,
      databaseDisabled: dbUpdateSuccess
    },
      cleanup: cleanupInfo,
      snapshot: snapshotSummary,
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('[Close Strategy API] Unexpected error:', error);
    return NextResponse.json(
      {
        error: 'Internal server error',
        message: 'An unexpected error occurred while closing the strategy'
      },
      { status: 500 }
    );
  }
}
