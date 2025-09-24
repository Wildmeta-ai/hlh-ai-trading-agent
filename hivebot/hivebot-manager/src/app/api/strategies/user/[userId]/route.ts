import { NextRequest, NextResponse } from 'next/server';
import { database } from '@/lib/database';

// DELETE /api/strategies/user/[userId] - Delete all strategies for a specific user
export async function DELETE(
  request: NextRequest,
  { params }: { params: { userId: string } }
) {
  try {
    const userId = params.userId;

    if (!userId) {
      return NextResponse.json(
        { error: 'User ID is required' },
        { status: 400 }
      );
    }

    console.log(`[Strategy Manager] Deleting all strategies for user: ${userId}`);

    const client = await database.getClient();
    let userStrategies: any[] = [];

    try {
      // Get all strategies for this user
      const strategiesQuery = `
        SELECT 
          hsc.name,
          hsc.hive_id,
          hi.hostname,
          hi.api_port
        FROM hive_strategy_configs hsc
        LEFT JOIN hive_instances hi ON hsc.hive_id = hi.hive_id
        WHERE hsc.name LIKE $1 OR hsc.user_id = $2
      `;
      
      // Match strategies by user ID or name pattern (for demo)
      const userPattern = `%${userId.split('_')[0]}%`; // Match user part of strategy names
      const result = await client.query(strategiesQuery, [userPattern, userId]);
      userStrategies = result.rows;

    } finally {
      if ('release' in client) {
        client.release();
      } else {
        await client.end();
      }
    }

    if (userStrategies.length === 0) {
      return NextResponse.json({
        success: true,
        message: 'No strategies found for user',
        deleted_strategies: []
      });
    }

    // Group strategies by bot and delete them
    const botGroups = userStrategies.reduce((groups: any, strategy: any) => {
      const botId = strategy.hive_id;
      if (!groups[botId]) {
        groups[botId] = {
          bot_info: {
            hive_id: botId,
            hostname: strategy.hostname,
            api_port: strategy.api_port
          },
          strategies: []
        };
      }
      groups[botId].strategies.push(strategy);
      return groups;
    }, {});

    const deleteResults: any[] = [];

    // Delete strategies from each bot
    for (const [botId, botGroup] of Object.entries(botGroups) as [string, any][]) {
      const { bot_info, strategies } = botGroup;

      for (const strategy of strategies) {
        try {
          // Delete from bot instance
          if (bot_info.api_port) {
            const deleteUrl = `http://localhost:${bot_info.api_port}/api/strategies/${strategy.name}`;
            const deleteResponse = await fetch(deleteUrl, { method: 'DELETE' });

            deleteResults.push({
              name: strategy.name,
              bot_id: botId,
              success: deleteResponse.ok,
              status: deleteResponse.status
            });
          }

          // Delete from PostgreSQL
          const client = await database.getClient();
          try {
            await client.query(
              'DELETE FROM hive_strategy_configs WHERE name = $1 AND hive_id = $2',
              [strategy.name, botId]
            );
          } finally {
            if ('release' in client) {
              client.release();
            } else {
              await client.end();
            }
          }

        } catch (error) {
          deleteResults.push({
            name: strategy.name,
            bot_id: botId,
            success: false,
            error: String(error)
          });
        }
      }
    }

    const successfulDeletes = deleteResults.filter(r => r.success);
    const failedDeletes = deleteResults.filter(r => !r.success);

    console.log(`[Strategy Manager] ✅ Deleted ${successfulDeletes.length} strategies for user ${userId}`);
    if (failedDeletes.length > 0) {
      console.log(`[Strategy Manager] ❌ Failed to delete ${failedDeletes.length} strategies`);
    }

    return NextResponse.json({
      success: true,
      user_id: userId,
      deleted_strategies: deleteResults,
      summary: {
        total: deleteResults.length,
        successful: successfulDeletes.length,
        failed: failedDeletes.length
      },
      message: `Deleted ${successfulDeletes.length} strategies for user`
    });

  } catch (error) {
    console.error('Failed to delete user strategies:', error);
    return NextResponse.json(
      { error: 'Failed to delete user strategies', details: error.message },
      { status: 500 }
    );
  }
}