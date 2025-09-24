import { NextRequest, NextResponse } from 'next/server';
import { database } from '@/lib/database';

// DELETE /api/bots/[id] - Delete specific bot instance
export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id: botId } = await params;

    if (!botId) {
      return NextResponse.json({ error: 'Bot ID is required' }, { status: 400 });
    }

    // For now, we'll just mark it as removed from the local registry
    // In a real implementation, you might want to update the database
    // to mark the bot as deleted rather than removing it entirely

    // Since we're using PostgreSQL which is read-only for bot_runs,
    // we'll just let the heartbeat logic handle marking it as offline
    // and the filtering will hide it from the UI

    console.log(`Bot deletion requested: ${botId}`);

    return NextResponse.json({
      success: true,
      message: 'Bot will be filtered out due to offline status'
    });

  } catch (error) {
    console.error('Error deleting bot instance:', error);
    return NextResponse.json(
      { error: 'Failed to delete bot instance' },
      { status: 500 }
    );
  }
}
