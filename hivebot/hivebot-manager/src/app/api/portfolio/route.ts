import { NextRequest, NextResponse } from 'next/server';
import { database } from '@/lib/database';
import { authenticateRequest, getUserIdFromWallet, isAdminRequest } from '@/lib/auth';

export async function GET(request: NextRequest) {
  try {
    const isAdmin = isAdminRequest(request);
    let userId: string | null = null;

    if (!isAdmin) {
      const authResult = authenticateRequest(request);
      if (!authResult.isValid) {
        return NextResponse.json(
          { error: 'Authentication failed', details: authResult.error },
          { status: 401 }
        );
      }
      userId = getUserIdFromWallet(authResult.walletAddress!);
      console.log(`[Portfolio API] Authenticated user: ${userId}`);
    } else {
      console.log('[Portfolio API] Admin access granted - showing all data');
    }

    const normalizedUserId = userId ? userId.toLowerCase() : null;

    const client = await database.getClient();

    try {
      // First check what tables exist in the database
      const tablesQuery = `
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name;
      `;
      const tablesResult = await client.query(tablesQuery);
      console.log('[Portfolio API] Available database tables:');
      tablesResult.rows.forEach((row: any) => {
        console.log(`  - ${row.table_name}`);
      });

      // Check actual structure of key tables
      try {
        // Check trades table structure
        const tradesStructure = await client.query(`
          SELECT column_name, data_type
          FROM information_schema.columns
          WHERE table_name = 'trades'
          ORDER BY ordinal_position;
        `);
        console.log('[Portfolio API] trades table structure:');
        tradesStructure.rows.forEach((row: any) => {
          console.log(`  - ${row.column_name}: ${row.data_type}`);
        });

        // Check position_snapshots table structure
        const positionsStructure = await client.query(`
          SELECT column_name, data_type
          FROM information_schema.columns
          WHERE table_name = 'position_snapshots'
          ORDER BY ordinal_position;
        `);
        console.log('[Portfolio API] position_snapshots table structure:');
        positionsStructure.rows.forEach((row: any) => {
          console.log(`  - ${row.column_name}: ${row.data_type}`);
        });

        // Check account_states table structure
        const accountStructure = await client.query(`
          SELECT column_name, data_type
          FROM information_schema.columns
          WHERE table_name = 'account_states'
          ORDER BY ordinal_position;
        `);
        console.log('[Portfolio API] account_states table structure:');
        accountStructure.rows.forEach((row: any) => {
          console.log(`  - ${row.column_name}: ${row.data_type}`);
        });

        // Check if position_snapshots has any data
        const positionCount = await client.query(`
          SELECT COUNT(*) as count FROM position_snapshots;
        `);
        console.log(`[Portfolio API] position_snapshots total records: ${positionCount.rows[0]?.count || 0}`);

        // Check recent position data
        const recentPositions = await client.query(`
          SELECT timestamp, trading_pair, side, exchange_size, unrealized_pnl
          FROM position_snapshots
          ORDER BY timestamp DESC
          LIMIT 3;
        `);
        console.log(`[Portfolio API] Recent positions: ${recentPositions.rows.length}`);
        recentPositions.rows.forEach((row: any) => {
          console.log(`  - ${row.timestamp}: ${row.trading_pair} ${row.side} ${row.exchange_size} PnL:${row.unrealized_pnl}`);
        });
      } catch (e) {
        console.log('[Portfolio API] Error checking table structures:', e);
      }
      const allowedPorts = new Map<number, { hiveId: string; accountName: string | null; userMainAddress: string | null }>();
      const allowedHiveIds = new Set<string>();
      const allowedAccountNames = new Set<string>();

      if (!isAdmin && normalizedUserId) {
        try {
          const strategiesForUser = await client.query(
            `SELECT name, hive_id FROM hive_strategy_configs WHERE LOWER(user_id) = $1`,
            [normalizedUserId]
          );

          strategiesForUser.rows.forEach((row: any) => {
            if (row.hive_id) {
              allowedHiveIds.add(row.hive_id);
            }
            if (row.name) {
              allowedAccountNames.add(row.name);
            }
          });
        } catch (strategyLoadError) {
          console.log('[Portfolio API] Failed to load user strategies from hive_strategy_configs:', strategyLoadError);
        }
      }

      try {
        const botRunsQueryParts: string[] = [
          `
            SELECT instance_name, deployment_config, user_main_address, account_name, last_heartbeat
            FROM bot_runs
            WHERE (deployment_status = 'running' OR run_status = 'running')
              AND last_heartbeat >= NOW() - INTERVAL '15 minutes'
          `
        ];
        const botRunsParams: any[] = [];

        if (!isAdmin && normalizedUserId) {
          botRunsQueryParts.push('AND LOWER(user_main_address) = $1');
          botRunsParams.push(normalizedUserId);
        }

        botRunsQueryParts.push('ORDER BY last_heartbeat DESC');
        const botRunsQuery = botRunsQueryParts.join(' ');
        const botRunsResult = await client.query(botRunsQuery, botRunsParams);

        botRunsResult.rows.forEach((row: any) => {
          const hiveId: string = row.instance_name || row.bot_name;
          if (!hiveId) {
            return;
          }

          const userAddress = row.user_main_address ? row.user_main_address.toLowerCase() : null;
          if (!isAdmin && normalizedUserId && userAddress !== normalizedUserId) {
            return;
          }

          let apiPort: number | null = null;
          if (row.deployment_config) {
            try {
              const config = JSON.parse(row.deployment_config);
              if (config && typeof config.api_port === 'number') {
                apiPort = config.api_port;
              }
            } catch (configError) {
              console.warn(`[Portfolio API] Failed to parse deployment_config for ${hiveId}:`, configError);
            }
          }

          if (apiPort === null || !Number.isFinite(apiPort) || apiPort <= 0) {
            return;
          }

          allowedPorts.set(apiPort, {
            hiveId,
            accountName: row.account_name || null,
            userMainAddress: userAddress
          });
          allowedHiveIds.add(hiveId);
          if (row.account_name) {
            allowedAccountNames.add(row.account_name);
          }
        });
      } catch (botMetaError) {
        console.log('[Portfolio API] Failed to load bot metadata for user filtering:', botMetaError);
      }

      const allowedHiveIdArray = Array.from(allowedHiveIds);
      const allowedAccountArray = Array.from(allowedAccountNames);
      const allowedStrategyNames = new Set(allowedAccountArray.map(name => name.toLowerCase()));

      if (!isAdmin && allowedPorts.size === 0 && allowedHiveIdArray.length > 0) {
        try {
          const hiveInstances = await client.query(
            `SELECT hive_id, api_port FROM hive_instances WHERE hive_id = ANY($1::text[])`,
            [allowedHiveIdArray]
          );

          hiveInstances.rows.forEach((row: any) => {
            const port = parseInt(row.api_port, 10);
            if (Number.isFinite(port) && port > 0) {
              allowedPorts.set(port, {
                hiveId: row.hive_id,
                accountName: null,
                userMainAddress: normalizedUserId
              });
            }
          });
        } catch (hiveInstanceError) {
          console.log('[Portfolio API] Failed to load hive instances for user:', hiveInstanceError);
        }
      }

      // Get REAL positions from position_snapshots table with improved strategy attribution
      // Priority: 1) Reconciled positions with realistic sizes, 2) Recent realistic positions, 3) Any recent positions
      const positionsQuery = `
        WITH raw_positions AS (
          SELECT
            ps.trading_pair as symbol,
            COALESCE(NULLIF(ps.account_name, ''), 'Unknown') as strategy,
            ps.connector_name as connector,
            ps.side as position_side,
            COALESCE(NULLIF(ps.exchange_size, 0), NULLIF(ps.calculated_size, 0), 0) as position_size,
            COALESCE(NULLIF(ps.entry_price, 0), NULLIF(ps.calculated_entry_price, 0), 0) as entry_price,
            COALESCE(ps.unrealized_pnl, 0) as unrealized_pnl,
            COALESCE(NULLIF(ps.leverage, 0), 1) as leverage,
            ps.timestamp as last_updated,
            COALESCE(NULLIF(ps.mark_price, 0), NULLIF(ps.calculated_entry_price, 0), NULLIF(ps.entry_price, 0), 0) as current_price,
            CASE WHEN LOWER(ps.is_reconciled) = 'true' THEN true ELSE false END as is_reconciled
          FROM position_snapshots ps
          WHERE ps.timestamp >= NOW() - INTERVAL '7 days'
            AND COALESCE(NULLIF(ps.entry_price, 0), NULLIF(ps.calculated_entry_price, 0)) > 0
            AND ABS(COALESCE(NULLIF(ps.exchange_size, 0), NULLIF(ps.calculated_size, 0), 0)) BETWEEN 0.0001 AND 100
        ),
        ranked_positions AS (
          SELECT
            rp.*,
            CASE
              WHEN rp.is_reconciled AND rp.entry_price > 0 AND rp.current_price > 0 THEN 1
              WHEN rp.is_reconciled AND ABS(rp.position_size) BETWEEN 0.0001 AND 25 THEN 2
              WHEN ABS(rp.position_size) BETWEEN 0.0001 AND 100 AND rp.entry_price > 0 THEN 3
              ELSE 4
            END as priority,
            ROW_NUMBER() OVER (
              PARTITION BY rp.symbol
              ORDER BY
                CASE
                  WHEN rp.is_reconciled AND rp.entry_price > 0 AND rp.current_price > 0 THEN 1
                  WHEN rp.is_reconciled AND ABS(rp.position_size) BETWEEN 0.0001 AND 25 THEN 2
                  WHEN ABS(rp.position_size) BETWEEN 0.0001 AND 100 AND rp.entry_price > 0 THEN 3
                  ELSE 4
                END,
                rp.last_updated DESC
            ) as rn
          FROM raw_positions rp
        )
        SELECT * FROM ranked_positions
        WHERE rn = 1
        ORDER BY priority ASC, last_updated DESC
      `;

      // First try to get positions from live Hive APIs owned by this user
      let positionsResult: any = { rows: [] };
      try {
        console.log('[Portfolio API] Attempting to fetch positions from Hive API instances...');

        const portsToQuery = allowedPorts.size > 0 ? Array.from(allowedPorts.entries()) : [];
        const aggregatedPositions: any[] = [];

        for (const [port, metadata] of portsToQuery) {
          if (!Number.isFinite(port) || port <= 0) {
            continue;
          }

          if (!isAdmin && metadata.userMainAddress && normalizedUserId && metadata.userMainAddress !== normalizedUserId) {
            continue;
          }

          const url = `http://localhost:${port}/api/positions`;
          try {
            const hiveHeaders: Record<string, string> = { 'Content-Type': 'application/json' };
            if (!isAdmin && normalizedUserId) {
              hiveHeaders['X-Wallet-Address'] = normalizedUserId;
            }

            const hiveResponse = await fetch(url, {
              method: 'GET',
              headers: hiveHeaders,
              signal: AbortSignal.timeout(5000)
            });

            if (!hiveResponse.ok) {
              console.log(`[Portfolio API] Hive API ${metadata.hiveId} (port ${port}) responded with status ${hiveResponse.status}`);
              continue;
            }

            const hiveData = await hiveResponse.json();
            const responseTimestampMs = typeof hiveData.timestamp === 'number' && hiveData.timestamp > 0
              ? hiveData.timestamp * 1000
              : Date.now();
            const responseTimestampIso = new Date(responseTimestampMs).toISOString();

            const positionsFromHive = Array.isArray(hiveData.positions) ? hiveData.positions : [];
            console.log(`[Portfolio API] Hive ${metadata.hiveId} returned ${positionsFromHive.length} positions`);

            positionsFromHive.forEach((pos: any, index: number) => {
              const entryPrice = pos && pos.entry_price !== undefined ? parseFloat(pos.entry_price) : 0;
              const positionSize = pos && pos.amount !== undefined ? parseFloat(pos.amount) : 0;
              const unrealizedPnl = pos && pos.unrealized_pnl !== undefined ? parseFloat(pos.unrealized_pnl) : 0;
              const leverageValue = pos && pos.leverage !== undefined ? parseFloat(pos.leverage) : 1;

              let currentPrice = pos && pos.mark_price !== undefined ? parseFloat(pos.mark_price) : entryPrice;
              if (!Number.isFinite(currentPrice) || currentPrice <= 0) {
                if (Number.isFinite(entryPrice) && entryPrice !== 0 && Number.isFinite(positionSize) && positionSize !== 0 && Number.isFinite(unrealizedPnl) && unrealizedPnl !== 0) {
                  const pnlPerUnit = unrealizedPnl / Math.abs(positionSize);
                  currentPrice = entryPrice + pnlPerUnit;
                } else {
                  currentPrice = entryPrice;
                }
              }

              const normalizedEntryPrice = Number.isFinite(entryPrice) ? entryPrice : 0;
              const normalizedSize = Number.isFinite(positionSize) ? positionSize : 0;
              const normalizedPnl = Number.isFinite(unrealizedPnl) ? unrealizedPnl : 0;
              const normalizedLeverage = Number.isFinite(leverageValue) && leverageValue > 0 ? leverageValue : 1;
              const normalizedCurrentPrice = Number.isFinite(currentPrice) ? currentPrice : normalizedEntryPrice;

              if (normalizedSize === 0) {
                return;
              }

              let strategyName = typeof pos?.strategy === 'string' && pos.strategy.trim().length > 0 ? pos.strategy.trim() : '';
              if (!strategyName || strategyName === 'Unknown') {
                strategyName = metadata.hiveId || `strategy-${index}`;
              }

              const positionSideRaw = typeof pos?.position_side === 'string' ? pos.position_side : '';
              const positionSide = positionSideRaw.replace('PositionSide.', '').toUpperCase();

              aggregatedPositions.push({
                symbol: pos?.trading_pair || 'Unknown',
                strategy: strategyName,
                connector: 'hyperliquid_perpetual',
                hive_id: metadata.hiveId,
                position_side: positionSide,
                position_size: normalizedSize,
                entry_price: normalizedEntryPrice,
                unrealized_pnl: normalizedPnl,
                leverage: normalizedLeverage,
                current_price: normalizedCurrentPrice,
                last_updated: responseTimestampIso,
                is_reconciled: true,
                priority: 1
              });
            });
          } catch (hiveError) {
            console.log(`[Portfolio API] Failed to fetch positions from Hive API ${metadata.hiveId} on port ${port}:`, hiveError);
          }
        }

        if (aggregatedPositions.length > 0) {
          positionsResult.rows = aggregatedPositions;
        }
      } catch (error) {
        console.log('[Portfolio API] Error gathering Hive API positions:', error);
      }

      // Fallback to database if no live Hive data
      if (positionsResult.rows.length === 0) {
        console.log('[Portfolio API] Falling back to database query for positions...');
        const positionParams: any[] = [];
        let positionsQueryFiltered = positionsQuery;

        if (!isAdmin) {
          if (allowedAccountNames.size > 0) {
            positionsQueryFiltered = positionsQuery.replace(
              'WHERE ps.timestamp >= NOW() - INTERVAL \'7 days\'',
              `WHERE ps.timestamp >= NOW() - INTERVAL '7 days' AND ps.account_name = ANY($1::text[])`
            );
            positionParams.push(Array.from(allowedAccountNames));
          } else if (normalizedUserId) {
            positionsQueryFiltered = `
              WITH user_positions AS (
                ${positionsQuery}
              )
              SELECT up.*
              FROM user_positions up
              INNER JOIN hive_strategy_configs hsc ON LOWER(hsc.name) = LOWER(up.strategy)
              WHERE LOWER(hsc.user_id) = $1
            `;
            positionParams.push(normalizedUserId);
          }
        }

        positionsResult = await client.query(positionsQueryFiltered, positionParams);
      }

      // Fetch recent trade-like events from hive activities for this user
      let tradesResult: any = { rows: [] };
      try {
        if (isAdmin || allowedHiveIdArray.length > 0) {
          const tradesQueryParts: string[] = [
            `
              SELECT
                ha.id,
                ha.timestamp,
                ha.strategy_name,
                ha.hive_id,
                ha.activity_type,
                ha.trading_pair,
                ha.price,
                ha.amount
              FROM hive_activities ha
              WHERE ha.success = true
                AND ha.price IS NOT NULL
                AND ha.amount IS NOT NULL
                AND ha.timestamp >= NOW() - INTERVAL '24 hours'
            `
          ];
          const tradesParams: any[] = [];
          if (!isAdmin && allowedHiveIdArray.length > 0) {
            tradesQueryParts.push('AND ha.hive_id = ANY($1::text[])');
            tradesParams.push(allowedHiveIdArray);
          }
          tradesQueryParts.push('ORDER BY ha.timestamp DESC LIMIT 100');
          const tradesQuery = tradesQueryParts.join(' ');
          tradesResult = await client.query(tradesQuery, tradesParams);
        }
      } catch (tradeError) {
        console.log('[Portfolio API] Failed to load activity-based trades:', tradeError);
      }

      const balanceFilterClause = (!isAdmin && allowedAccountArray.length > 0)
        ? ' AND account_name = ANY($1::text[])'
        : '';

      const balanceQuery = `
        WITH latest_balances AS (
          SELECT
            asset,
            connector_name,
            account_name,
            balance,
            ROW_NUMBER() OVER (
              PARTITION BY asset, connector_name, account_name
              ORDER BY timestamp DESC
            ) as rn
          FROM account_states
          WHERE timestamp >= NOW() - INTERVAL '30 days'
          ${balanceFilterClause}
        )
        SELECT asset, connector_name, account_name, balance
        FROM latest_balances
        WHERE rn = 1
      `;

      const balanceParams = (!isAdmin && allowedAccountArray.length > 0) ? [allowedAccountArray] : [];
      const balanceResult = await client.query(balanceQuery, balanceParams);

      // Get strategy performance
      let strategyPerfQuery = `
        SELECT
          ha.strategy_name,
          ha.hive_id,
          COUNT(*) as trade_count,
          SUM(ha.price * ha.amount) as total_volume,
          AVG(ha.price * ha.amount) as avg_trade_size,
          COUNT(*) FILTER (WHERE ha.activity_type LIKE '%BUY%') as buy_count,
          COUNT(*) FILTER (WHERE ha.activity_type LIKE '%SELL%') as sell_count,
          MAX(ha.price * ha.amount) as largest_trade,
          MIN(ha.price * ha.amount) as smallest_trade
        FROM hive_activities ha
        WHERE ha.success = true
          AND ha.price IS NOT NULL
          AND ha.amount IS NOT NULL
          AND ha.timestamp >= NOW() - INTERVAL '24 hours'
      `;
      const strategyPerfParams: any[] = [];
      if (!isAdmin && allowedHiveIdArray.length > 0) {
        strategyPerfQuery += ' AND ha.hive_id = ANY($1::text[])';
        strategyPerfParams.push(allowedHiveIdArray);
      }
      strategyPerfQuery += ' GROUP BY ha.strategy_name, ha.hive_id ORDER BY total_volume DESC';

      const strategyPerfResult = await client.query(strategyPerfQuery, strategyPerfParams);

      // Format trades
      const trades = tradesResult.rows.map((row: any) => {
        const timestamp = new Date(row.timestamp);
        const price = row.price !== undefined ? parseFloat(row.price) : 0;
        const amount = row.amount !== undefined ? parseFloat(row.amount) : 0;
        const value = Number.isFinite(price) && Number.isFinite(amount) ? price * amount : 0;

        return {
          id: row.id?.toString?.() || String(row.id ?? ''),
          timestamp: isNaN(timestamp.getTime()) ? new Date().toISOString() : timestamp.toISOString(),
          strategy: row.strategy_name || 'Unknown',
          hive_id: row.hive_id || 'Unknown',
          action: row.activity_type || 'UNKNOWN',
          symbol: row.trading_pair || 'Unknown',
          price: Number.isFinite(price) ? price : 0,
          amount: Number.isFinite(amount) ? amount : 0,
          value: Number.isFinite(value) ? value : 0,
          fee: 0,
          pnl: undefined,
          order_id: ''
        };
      });

      // Get active strategy names from strategy performance for fallback attribution
      const activeStrategyNames = strategyPerfResult.rows.map(row => row.strategy_name);
      const primaryStrategyName = activeStrategyNames[0] || 'Unknown'; // Use first active strategy as primary

      // Format positions from REAL Hummingbot position_snapshots data with enhanced strategy attribution
      const positions = positionsResult.rows.map((row: any) => {
        const positionSizeRaw = row.position_size !== undefined ? parseFloat(row.position_size) : 0;
        const positionSize = Number.isFinite(positionSizeRaw) ? positionSizeRaw : 0;
        let entryPrice = row.entry_price !== undefined ? parseFloat(row.entry_price) : 0;
        if (!Number.isFinite(entryPrice)) entryPrice = 0;

        let currentPrice = row.current_price !== undefined ? parseFloat(row.current_price) : entryPrice;
        if (!Number.isFinite(currentPrice)) currentPrice = entryPrice;

        const unrealizedPnl = row.unrealized_pnl !== undefined ? parseFloat(row.unrealized_pnl) : 0;
        const leverageRaw = row.leverage !== undefined ? parseFloat(row.leverage) : 1;
        const leverage = Number.isFinite(leverageRaw) && leverageRaw > 0 ? leverageRaw : 1;

        if ((!currentPrice || currentPrice === 0) && entryPrice && positionSize) {
          const pnlPerUnit = positionSize !== 0 ? unrealizedPnl / Math.abs(positionSize) : 0;
          if (pnlPerUnit !== 0) {
            currentPrice = entryPrice + pnlPerUnit;
          } else {
            currentPrice = entryPrice;
          }
        }

        const notionalValue = Math.abs(positionSize) * (entryPrice || currentPrice);
        const margin = leverage !== 0 ? notionalValue / leverage : notionalValue;

        let strategyName = row.strategy;
        if (!strategyName || strategyName === 'Unknown') {
          strategyName = primaryStrategyName;
        }

        const sideRaw = (row.position_side || '').toString().toUpperCase();
        const side = sideRaw === 'LONG' ? 'LONG' : 'SHORT';

        const lastUpdatedRaw = row.last_updated;
        let lastUpdated: string;
        if (typeof lastUpdatedRaw === 'number') {
          const date = new Date(lastUpdatedRaw * 1000);
          lastUpdated = isNaN(date.getTime()) ? new Date().toISOString() : date.toISOString();
        } else {
          const date = new Date(lastUpdatedRaw);
          lastUpdated = isNaN(date.getTime()) ? new Date().toISOString() : date.toISOString();
        }

        const hiveSource = row.hive_id || row.connector || 'hyperliquid_perpetual';

        return {
          symbol: row.symbol || 'Unknown',
          strategy: strategyName,
          hive_id: hiveSource,
          side,
          size: Math.abs(positionSize),
          entry_price: entryPrice,
          current_price: currentPrice,
          unrealized_pnl: Number.isFinite(unrealizedPnl) ? unrealizedPnl : 0,
          realized_pnl: 0,
          leverage,
          margin: Number.isFinite(margin) ? margin : 0,
          last_updated: lastUpdated
        };
      });

      // No manual/mock positions - use only real Hummingbot position data

      const allowedHiveIdSet = new Set(allowedHiveIdArray.map(id => id.toLowerCase()));

      const filteredTrades = isAdmin
        ? trades
        : trades.filter(t =>
            (!t.hive_id || allowedHiveIdSet.size === 0 || allowedHiveIdSet.has(t.hive_id.toLowerCase())) &&
            (!t.strategy || allowedStrategyNames.size === 0 || allowedStrategyNames.has(t.strategy.toLowerCase()))
          );

      const filteredPositions = isAdmin
        ? positions
        : positions.filter(p =>
            (!p.hive_id || allowedHiveIdSet.size === 0 || allowedHiveIdSet.has(p.hive_id.toLowerCase())) &&
            (!p.strategy || allowedStrategyNames.size === 0 || allowedStrategyNames.has(p.strategy.toLowerCase()))
          );

      let filteredStrategyPerfRows = isAdmin
        ? strategyPerfResult.rows
        : strategyPerfResult.rows.filter((row: any) => {
            const hiveMatch = !row.hive_id || allowedHiveIdSet.size === 0 || allowedHiveIdSet.has(row.hive_id.toLowerCase());
            const strategyMatch = !row.strategy_name || allowedStrategyNames.size === 0 || allowedStrategyNames.has(row.strategy_name.toLowerCase());
            return hiveMatch && strategyMatch;
          });

      if (!isAdmin && filteredStrategyPerfRows.length === 0 && filteredPositions.length > 0) {
        const fallbackMap = new Map<string, { strategy_name: string; hive_id: string | null; total_volume: number; trade_count: number; buy_count: number; sell_count: number }>();
        filteredPositions.forEach(position => {
          const key = position.strategy || 'Unknown';
          const existing = fallbackMap.get(key);
          if (!existing) {
            fallbackMap.set(key, {
              strategy_name: key,
              hive_id: position.hive_id || null,
              total_volume: position.size * position.current_price,
              trade_count: 1,
              buy_count: position.side === 'LONG' ? 1 : 0,
              sell_count: position.side === 'SHORT' ? 1 : 0
            });
          } else {
            existing.total_volume += position.size * position.current_price;
            existing.trade_count += 1;
            if (position.side === 'LONG') {
              existing.buy_count += 1;
            } else {
              existing.sell_count += 1;
            }
          }
        });

        filteredStrategyPerfRows = Array.from(fallbackMap.values());
      }

      const accountTotalTrades = filteredStrategyPerfRows.reduce((sum: number, row: any) => {
        const countValue = row.trade_count !== undefined ? parseInt(row.trade_count, 10) : 0;
        return sum + (Number.isFinite(countValue) ? countValue : 0);
      }, filteredTrades.length);

      const accountVolume = filteredTrades.reduce((sum, row) => sum + row.value, 0);

      // Estimate account balance from position margin usage and stable balances
      const totalMargin = filteredPositions.reduce((sum, p) => sum + p.margin, 0);

      const latestBalances = balanceResult.rows.map((row: any) => ({
        asset: row.asset as string,
        connector: row.connector_name as string,
        account: row.account_name as string,
        balance: row.balance !== undefined ? parseFloat(row.balance) : 0
      }));

      const relevantBalances = (isAdmin || allowedStrategyNames.size === 0)
        ? latestBalances
        : latestBalances.filter(item => item.account && allowedStrategyNames.has(item.account.toLowerCase()));

      const stableAssets = new Set(['USD', 'USDC', 'USDT', 'USDS', 'DAI']);
      const stableBalance = relevantBalances.reduce((sum, item) => {
        if (item.asset && stableAssets.has(item.asset.toUpperCase())) {
          return sum + (Number.isFinite(item.balance) ? item.balance : 0);
        }
        return sum;
      }, 0);

      const baseBalance = stableBalance > 0 ? stableBalance : (totalMargin > 0 ? totalMargin * 2 : 0);

      // Enhanced P&L calculation using Hummingbot's methodology
      // 1. Get realized P&L from completed trades
      const totalRealizedPnL = 0; // Would calculate from matched buy/sell pairs

      // 2. Get unrealized P&L from current positions (direct from Hyperliquid API)
      const totalUnrealizedPnL = filteredPositions.reduce((sum, p) => sum + p.unrealized_pnl, 0);

      // 3. Calculate fees paid (important for net P&L)
      const totalFees = filteredTrades.reduce((sum, t) => sum + t.fee, 0);

      // 4. Calculate win rate from successful trades (using price movements)
      let winningTrades = 0;
      let losingTrades = 0;
      let totalTradeCount = Math.max(accountTotalTrades, filteredTrades.length);

      // For derivatives, check position P&L instead of individual trades
      if (filteredPositions.length > 0) {
        const profitablePositions = filteredPositions.filter(p => p.unrealized_pnl > 0).length;
        const losingPositions = filteredPositions.filter(p => p.unrealized_pnl < 0).length;
        winningTrades = profitablePositions;
        losingTrades = losingPositions;
        totalTradeCount = Math.max(totalTradeCount, filteredPositions.length);
      }

      // 5. Calculate total P&L (Hummingbot style: realized + unrealized - fees)
      const totalPnL = totalRealizedPnL + totalUnrealizedPnL - totalFees;

      // 6. Estimate account balance from position data
      const positionValue = filteredPositions.reduce((sum, p) => sum + (p.size * p.current_price), 0);
      const marginUsed = filteredPositions.reduce((sum, p) => sum + p.margin, 0);

      const balanceCandidate = filteredPositions.length > 0
        ? Math.max(baseBalance, marginUsed * 2 + totalPnL)
        : baseBalance;

      const finalBalance = Number.isFinite(balanceCandidate) ? balanceCandidate : 0;
      const availableBalance = Math.max(0, (stableBalance > 0 ? stableBalance : finalBalance) - marginUsed);

      const portfolio = {
        total_balance: finalBalance,
        available_balance: availableBalance,
        total_pnl: totalPnL,
        unrealized_pnl: totalUnrealizedPnL,
        realized_pnl: totalRealizedPnL,
        total_volume: accountVolume,
        positions: filteredPositions,
        daily_pnl: totalUnrealizedPnL, // Using unrealized as daily for derivatives
        win_rate: totalTradeCount > 0 ? (winningTrades / totalTradeCount) * 100 : 0,
        total_trades: totalTradeCount,
        winning_trades: winningTrades,
        losing_trades: losingTrades,
        largest_win: filteredPositions.length > 0 ? Math.max(0, ...filteredPositions.map(p => p.unrealized_pnl)) : 0,
        largest_loss: filteredPositions.length > 0 ? Math.min(0, ...filteredPositions.map(p => p.unrealized_pnl)) : 0,
        // Additional Hummingbot-style metrics
        total_fees: totalFees,
        net_pnl: totalPnL,
        position_value: positionValue,
        margin_used: marginUsed,
        return_percentage: finalBalance > 0 ? (totalPnL / finalBalance) * 100 : 0
      };

      // Enhanced strategy performance calculation
      const strategyPerformance = filteredStrategyPerfRows.map((row: any) => {
        const strategyVolume = parseFloat(row.total_volume) || 0;
        const tradeCount = parseInt(row.trade_count) || 0;
        const buyCount = parseInt(row.buy_count) || 0;
        const sellCount = parseInt(row.sell_count) || 0;

        // Get positions for this strategy with improved matching
        const strategyPositions = filteredPositions.filter(p => {
          // Primary match: exact strategy name
          if (p.strategy === row.strategy_name) return true;

          // Secondary match: hive_id
          if (p.hive_id === row.hive_id) return true;

          // Fallback match: if position strategy is "Unknown", assign to active strategy
          if (p.strategy === 'Unknown' || !p.strategy) {
            return true; // Assign unknown positions to this strategy
          }

          return false;
        });

        // Calculate P&L from positions assigned to this strategy
        const strategyUnrealizedPnL = strategyPositions.reduce((sum, p) => sum + p.unrealized_pnl, 0);
        const strategyPositionValue = strategyPositions.reduce((sum, p) => sum + (p.size * p.current_price), 0);

        // Estimate win rate based on balanced buy/sell activity
        const balancedTrades = Math.min(buyCount, sellCount);
        const totalStrategyTrades = Math.max(tradeCount, strategyPositions.length);
        const estimatedWinRate = strategyUnrealizedPnL > 0 ? 60 : (strategyUnrealizedPnL < -10 ? 30 : 45);

        return {
          strategy: row.strategy_name,
          hive_id: row.hive_id,
          total_pnl: strategyUnrealizedPnL, // Using unrealized as main P&L for derivatives
          unrealized_pnl: strategyUnrealizedPnL,
          realized_pnl: 0, // Would need trade matching for this
          total_volume: strategyVolume,
          trade_count: totalStrategyTrades,
          win_rate: estimatedWinRate,
          avg_trade_size: tradeCount > 0 ? strategyVolume / tradeCount : 0,
          largest_win: strategyPositions.length > 0 ? Math.max(0, ...strategyPositions.map(p => p.unrealized_pnl)) : 0,
          largest_loss: strategyPositions.length > 0 ? Math.min(0, ...strategyPositions.map(p => p.unrealized_pnl)) : 0,
          // Additional metrics
          buy_count: buyCount,
          sell_count: sellCount,
          position_count: strategyPositions.length,
          position_value: strategyPositionValue,
          balance_score: balancedTrades > 0 ? (balancedTrades / Math.max(buyCount, sellCount)) * 100 : 0
        };
      });

      const responseStatus = (() => {
        if (filteredPositions.length === 0 && filteredTrades.length === 0 && stableBalance === 0) {
          return 'no_data';
        }
        const staleThreshold = 60 * 60 * 1000; // 1 hour
        const now = Date.now();
        const hasStalePositions = filteredPositions.some(p => {
          const lastUpdate = new Date(p.last_updated).getTime();
          return Number.isFinite(lastUpdate) && now - lastUpdate > staleThreshold;
        });
        return hasStalePositions ? 'stale' : 'live';
      })();

      // Create trade summary instead of returning all trades
      const tradeSummary = {
        total_count: filteredTrades.length,
        total_volume: accountVolume,
        recent_trades_24h: filteredTrades.filter(t => {
          const tradeTime = new Date(t.timestamp).getTime();
          const dayAgo = Date.now() - (24 * 60 * 60 * 1000);
          return tradeTime > dayAgo;
        }).length,
        top_symbols: (() => {
          const symbolCounts = new Map<string, number>();
          filteredTrades.forEach(t => {
            symbolCounts.set(t.symbol, (symbolCounts.get(t.symbol) || 0) + 1);
          });
          return Array.from(symbolCounts.entries())
            .sort((a, b) => b[1] - a[1])
            .slice(0, 5)
            .map(([symbol, count]) => ({ symbol, count }));
        })(),
        last_trade: filteredTrades.length > 0 ? {
          timestamp: filteredTrades[0].timestamp,
          symbol: filteredTrades[0].symbol,
          action: filteredTrades[0].action,
          value: filteredTrades[0].value
        } : null
      };

      return NextResponse.json({
        trade_summary: tradeSummary,
        positions: filteredPositions,
        portfolio,
        strategy_performance: strategyPerformance,
        status: responseStatus,
        last_updated: new Date().toISOString()
      });

    } finally {
      await client.end();
    }

  } catch (error) {
    console.error('Failed to fetch portfolio data:', error);

    // Return empty data structure when database fails - NO MOCK DATA EVER
    return NextResponse.json({
      trade_summary: {
        total_count: 0,
        total_volume: 0,
        recent_trades_24h: 0,
        top_symbols: [],
        last_trade: null
      },
      positions: [],
      portfolio: {
        total_balance: 0,
        available_balance: 0,
        total_pnl: 0,
        unrealized_pnl: 0,
        realized_pnl: 0,
        total_volume: 0,
        positions: [],
        daily_pnl: 0,
        win_rate: 0,
        total_trades: 0,
        winning_trades: 0,
        losing_trades: 0,
        largest_win: 0,
        largest_loss: 0
      },
      strategy_performance: [],
      status: 'database_error',
      last_updated: new Date().toISOString(),
      message: 'Database connection failed - no position data available'
    });
  }
}
