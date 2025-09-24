import { NextRequest, NextResponse } from 'next/server';
import { BotInstance, DashboardMetrics } from '@/types';
import { database } from '@/lib/database';

// In-memory bot registry for local instances (remote data fetched via database)
const localBotRegistry: Map<string, BotInstance> = new Map();
let lastCleanup = Date.now();

// Cleanup inactive bots every 5 minutes
const CLEANUP_INTERVAL = 5 * 60 * 1000;
const BOT_TIMEOUT = 10 * 60 * 1000; // 10 minutes

function cleanupInactiveBots() {
  const now = Date.now();

  if (now - lastCleanup < CLEANUP_INTERVAL) return;

  for (const [id, bot] of localBotRegistry) {
    const lastActivity = new Date(bot.last_activity).getTime();
    if (now - lastActivity > BOT_TIMEOUT) {
      localBotRegistry.delete(id);
      console.log(`Cleaned up inactive bot: ${id}`);
    }
  }

  lastCleanup = now;
}

// GET /api/bots - List all registered bot instances
export async function GET(request: NextRequest) {
  try {
    cleanupInactiveBots();

    const url = new URL(request.url);
    const format = url.searchParams.get('format');

    if (format === 'metrics') {
      // Get metrics from database ONLY
      const metrics = await database.getDashboardMetrics();
      return NextResponse.json(metrics);
    }

    // Get bot instances from database ONLY
    const allBots = (await database.getBotInstances()).map(bot => ({
      ...bot,
      uptime_formatted: formatUptime(bot.uptime)
    }));

    return NextResponse.json({ bots: allBots });

  } catch (error) {
    console.error('Error fetching bot instances:', error);
    return NextResponse.json({ error: 'Failed to fetch bot instances' }, { status: 500 });
  }
}

// POST /api/bots - Register or heartbeat bot instance
export async function POST(request: NextRequest) {
  try {
    const botData: Partial<BotInstance> = await request.json();

    // DEBUG: Log the received data
    console.log(`[DEBUG] Bot registration data:`, {
      id: botData.id,
      name: botData.name,
      user_main_address: botData.user_main_address,
      api_port: botData.api_port
    });

    if (!botData.id || !botData.name) {
      return NextResponse.json(
        { error: 'Bot ID and name are required' },
        { status: 400 }
      );
    }

    // This endpoint now handles both registration AND heartbeat
    // If bot doesn't exist in database, treat this as registration
    // If bot exists, treat as heartbeat update

    const bot: BotInstance = {
      id: botData.id,
      name: botData.name,
      status: botData.status || 'running',
      strategies: botData.strategies || [],
      uptime: botData.uptime || 0,
      total_strategies: botData.total_strategies || 0,
      total_actions: botData.total_actions || 0,
      actions_per_minute: botData.actions_per_minute || 0,
      last_activity: new Date().toISOString(),
      memory_usage: botData.memory_usage || 0,
      cpu_usage: botData.cpu_usage || 0,
      api_port: botData.api_port || 8080,
      user_main_address: botData.user_main_address || undefined // Include user address if provided
    };

    // Try to sync with database - this will handle both new registrations and updates
    const success = await database.updateBotInstance(bot);

    if (success) {
      console.log(`Bot heartbeat/registration: ${bot.name} (${bot.id})`);
      return NextResponse.json({ success: true, bot });
    } else {
      console.warn(`Failed to register/update bot in database: ${bot.id}`);
      return NextResponse.json({ error: 'Failed to register bot instance' }, { status: 500 });
    }

  } catch (error) {
    console.error('Error registering bot instance:', error);
    return NextResponse.json({ error: 'Failed to register bot instance' }, { status: 500 });
  }
}

// PUT /api/bots/[id] - Update specific bot instance
export async function PUT(request: NextRequest) {
  try {
    const url = new URL(request.url);
    const botId = url.pathname.split('/').pop();

    if (!botId) {
      return NextResponse.json({ error: 'Bot ID is required' }, { status: 400 });
    }

    const updateData: Partial<BotInstance> = await request.json();
    const existingBot = localBotRegistry.get(botId);

    if (!existingBot) {
      return NextResponse.json({ error: 'Bot not found' }, { status: 404 });
    }

    const updatedBot: BotInstance = {
      ...existingBot,
      ...updateData,
      id: botId, // Prevent ID change
      last_activity: new Date().toISOString()
    };

    localBotRegistry.set(botId, updatedBot);

    // Sync with remote database
    await database.updateBotInstance(updatedBot);

    return NextResponse.json({ success: true, bot: updatedBot });

  } catch (error) {
    console.error('Error updating bot instance:', error);
    return NextResponse.json({ error: 'Failed to update bot instance' }, { status: 500 });
  }
}

// DELETE /api/bots/[id] - Remove bot instance
export async function DELETE(request: NextRequest) {
  try {
    const url = new URL(request.url);
    const botId = url.pathname.split('/').pop();

    if (!botId) {
      return NextResponse.json({ error: 'Bot ID is required' }, { status: 400 });
    }

    const deleted = localBotRegistry.delete(botId);

    if (!deleted) {
      return NextResponse.json({ error: 'Bot not found' }, { status: 404 });
    }

    console.log(`Bot removed from registry: ${botId}`);

    return NextResponse.json({ success: true, message: 'Bot removed successfully' });

  } catch (error) {
    console.error('Error removing bot instance:', error);
    return NextResponse.json({ error: 'Failed to remove bot instance' }, { status: 500 });
  }
}

function formatUptime(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);

  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }
  return `${minutes}m`;
}
