import { NextResponse } from 'next/server';
import { database } from '@/lib/database';

export async function POST() {
  try {
    const client = await database.getClient();

    try {
      // Clear activities with fake order IDs or wrong hive_id
      const result = await client.query(`
        DELETE FROM hive_activities
        WHERE order_id LIKE '393712894%'
           OR order_id LIKE '705669%'
           OR order_id LIKE '712894%'
           OR hive_id = 'hive-solana-rpc-node-sg-2-8080'
      `);

      // Show remaining activities
      const remaining = await client.query('SELECT COUNT(*) as count FROM hive_activities');

      return NextResponse.json({
        success: true,
        deleted: result.rowCount,
        remaining: parseInt(remaining.rows[0].count)
      });

    } finally {
      if ('release' in client) {
        client.release();
      } else {
        await client.end();
      }
    }

  } catch (error) {
    console.error('Failed to clear fake activities:', error);
    return NextResponse.json({
      success: false,
      error: 'Failed to clear activities',
      details: error instanceof Error ? error.message : 'Unknown error'
    }, { status: 500 });
  }
}
