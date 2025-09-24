import { NextResponse } from 'next/server';
import { database } from '@/lib/database';

// POST /api/strategies/refresh-metrics - Refresh strategy metrics from activities
export async function POST() {
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
