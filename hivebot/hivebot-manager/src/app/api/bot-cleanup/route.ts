import { NextRequest, NextResponse } from 'next/server';
import { spawn } from 'child_process';

// POST /api/bot-cleanup - Clean up bot instances by user address or bot ID
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { userAddress, botId, action } = body;

    if (!userAddress && !botId) {
      return NextResponse.json({
        error: 'Either userAddress or botId is required'
      }, { status: 400 });
    }

    console.log(`[Bot Cleanup] Request: ${action || 'cleanup'} for user: ${userAddress || 'N/A'}, bot: ${botId || 'N/A'}`);

    // Import the spawned bots registry from the spawn-bot API
    // For now, use a simpler approach - just stop by botId directly
    const botsToCleanup: string[] = [];

    if (botId) {
      // Clean up specific bot by ID
      botsToCleanup.push(botId);
    } else if (userAddress) {
      // For user cleanup, we need to find all bots for that user
      // Since we don't have persistent storage, we'll use a pattern-based approach
      // This could be improved by storing bot info in a database
      console.log(`[Bot Cleanup] Looking for bots matching user pattern: ${userAddress.slice(-8)}`);

      // Try common bot naming patterns for this user
      const userPattern = userAddress.slice(-8).toLowerCase();
      const possibleBotIds = [
        `bot-${userPattern}-*`, // This would need PM2 wildcard support
      ];

      // For now, we'll have to list PM2 processes to find user bots
      // But we'll keep it simple - just try to stop any bot process with the user pattern
    }

    console.log(`[Bot Cleanup] Found ${botsToCleanup.length} bot(s) to cleanup`);

    const cleanupResults = [];

    // Clean up each bot
    for (const botName of botsToCleanup) {
      try {
        console.log(`[Bot Cleanup] Stopping PM2 process: ${botName}`);

        // Stop the PM2 process
        const stopResult = await new Promise<boolean>((resolve) => {
          const stopProcess = spawn('pm2', ['delete', botName], {
            cwd: '/home/ubuntu/hummingbot'
          });

          stopProcess.on('close', (code) => {
            resolve(code === 0);
          });

          stopProcess.on('error', () => {
            resolve(false);
          });
        });

        cleanupResults.push({
          botName: botName,
          status: stopResult ? 'stopped' : 'failed',
          action: 'pm2_delete'
        });

        // Clean up temporary files
        try {
          const { unlinkSync, existsSync } = require('fs');
          const startScriptPath = `/tmp/start_${botName}.sh`;
          const ecosystemPath = `/tmp/ecosystem-${botName}.config.js`;

          if (existsSync(startScriptPath)) {
            unlinkSync(startScriptPath);
            console.log(`[Bot Cleanup] Removed start script: ${startScriptPath}`);
          }

          if (existsSync(ecosystemPath)) {
            unlinkSync(ecosystemPath);
            console.log(`[Bot Cleanup] Removed ecosystem file: ${ecosystemPath}`);
          }
        } catch (fileError) {
          console.warn(`[Bot Cleanup] Failed to clean up files for ${botName}:`, fileError);
        }

      } catch (error) {
        console.error(`[Bot Cleanup] Error cleaning up bot ${botName}:`, error);
        cleanupResults.push({
          botName: botName,
          status: 'error',
          error: error instanceof Error ? error.message : 'Unknown error'
        });
      }
    }

    // Additional cleanup: Remove any orphaned processes
    if (action === 'deep-cleanup') {
      console.log('[Bot Cleanup] Performing deep cleanup of orphaned processes...');

      try {
        // Kill any python processes that might be stuck
        const killPythonPromise = new Promise<boolean>((resolve) => {
          const killProcess = spawn('pkill', ['-f', 'hive_dynamic_core_modular.py'], {
            cwd: '/home/ubuntu/hummingbot'
          });

          killProcess.on('close', () => {
            resolve(true);
          });

          killProcess.on('error', () => {
            resolve(false);
          });
        });

        await killPythonPromise;
        console.log('[Bot Cleanup] Deep cleanup completed');
      } catch (error) {
        console.warn('[Bot Cleanup] Deep cleanup failed:', error);
      }
    }

    return NextResponse.json({
      success: true,
      message: `Cleaned up ${cleanupResults.length} bot instance(s)`,
      results: cleanupResults,
      userAddress,
      botId
    });

  } catch (error) {
    console.error('[Bot Cleanup] Error:', error);
    return NextResponse.json({
      error: 'Bot cleanup failed',
      details: error instanceof Error ? error.message : 'Unknown error'
    }, { status: 500 });
  }
}

// GET /api/bot-cleanup - List bot instances that can be cleaned up
export async function GET(request: NextRequest) {
  try {
    const url = new URL(request.url);
    const userAddress = url.searchParams.get('userAddress');

    // Get PM2 process list
    const pm2ListPromise = new Promise<string>((resolve, reject) => {
      const pm2Process = spawn('pm2', ['list', '--json'], {
        cwd: '/home/ubuntu/hummingbot'
      });

      let output = '';

      pm2Process.stdout?.on('data', (data) => {
        output += data.toString();
      });

      pm2Process.on('close', (code) => {
        if (code === 0) {
          resolve(output);
        } else {
          reject(new Error('PM2 list failed'));
        }
      });
    });

    const pm2Output = await pm2ListPromise;
    const pm2Processes = JSON.parse(pm2Output);

    // Filter bot processes
    const botProcesses = pm2Processes.filter((proc: any) => {
      const isBot = proc.name && proc.name.startsWith('bot-');

      if (userAddress) {
        return isBot && proc.name.includes(userAddress.slice(-8).toLowerCase());
      }

      return isBot;
    });

    const botInstances = botProcesses.map((proc: any) => ({
      botId: proc.name,
      pid: proc.pid,
      status: proc.pm2_env?.status || 'unknown',
      uptime: proc.pm2_env?.pm_uptime ? Date.now() - proc.pm2_env.pm_uptime : 0,
      memory: proc.monit?.memory || 0,
      cpu: proc.monit?.cpu || 0
    }));

    return NextResponse.json({
      success: true,
      bots: botInstances,
      userAddress
    });

  } catch (error) {
    console.error('[Bot Cleanup] List error:', error);
    return NextResponse.json({
      error: 'Failed to list bot instances',
      details: error instanceof Error ? error.message : 'Unknown error'
    }, { status: 500 });
  }
}