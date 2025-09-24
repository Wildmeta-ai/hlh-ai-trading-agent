import { NextRequest, NextResponse } from 'next/server';
import { spawn } from 'child_process';
import { writeFileSync, existsSync, mkdirSync } from 'fs';
import { join } from 'path';
import crypto from 'crypto';
import { Client } from 'pg';

// Port range for spawned bot instances
const MIN_PORT = 8100;
const MAX_PORT = 8200;
const USED_PORTS = new Set<number>();

// Track spawned bot instances
const SPAWNED_BOTS = new Map<string, {
  botId: string;
  userAddress: string;
  apiPort: number;
  processName: string;
  dbPath: string;
  status: 'starting' | 'running' | 'stopped' | 'error';
  createdAt: string;
  pid?: number;
}>();

interface SpawnBotRequest {
  userAddress: string;
  agentWalletPrivateKey: string;
  network?: 'testnet' | 'mainnet';
  strategies?: any[];
}

// Validate Hyperliquid private key format
function validateHyperliquidPrivateKey(privateKey: string): boolean {
  try {
    // Basic validation: should be hex string, 64 characters (32 bytes)
    const cleanKey = privateKey.replace(/^0x/, '');
    return /^[a-fA-F0-9]{64}$/.test(cleanKey);
  } catch {
    return false;
  }
}

// Check if a port is actually in use by checking running processes
async function isPortInUse(port: number): Promise<boolean> {
  return new Promise((resolve) => {
    const netstatProcess = spawn('netstat', ['-tln'], {});

    let output = '';
    netstatProcess.stdout?.on('data', (data) => {
      output += data.toString();
    });

    netstatProcess.on('close', (code) => {
      if (code !== 0) {
        // If netstat fails, assume port is in use for safety
        resolve(true);
        return;
      }

      // Check if port is listening - be more flexible with the pattern
      const portPattern = new RegExp(`:${port}\\s`);
      const isListening = portPattern.test(output);
      resolve(isListening);
    });

    netstatProcess.on('error', () => {
      // If error, assume port is in use for safety
      resolve(true);
    });
  });
}

// Find available port in range
async function findAvailablePort(): Promise<{port: number | null, debug: any}> {
  const debugInfo = {
    checkedPorts: [],
    usedPorts: Array.from(USED_PORTS),
    minPort: MIN_PORT,
    maxPort: MAX_PORT
  };

  for (let port = MIN_PORT; port <= MAX_PORT; port++) {
    const inUse = await isPortInUse(port);
    debugInfo.checkedPorts.push({port, inUse});

    if (!inUse) {
      USED_PORTS.add(port);
      return {port, debug: debugInfo};
    }
  }
  return {port: null, debug: debugInfo};
}

// Generate unique bot ID with wallet address for better identification
function generateBotId(userAddress: string, apiPort: number): string {
  // Create short wallet identifier (first 6 + last 4 chars)
  const walletShort = `${userAddress.slice(0, 6)}...${userAddress.slice(-4)}`;
  return `hive-${walletShort}-${apiPort}`;
}

// Check PM2 for running bots by user address
async function checkPM2ForRunningBot(userAddress: string): Promise<{exists: boolean, botId?: string, apiPort?: number}> {
  return new Promise((resolve) => {
    const pm2Process = spawn('pm2', ['jlist'], {
      cwd: '/home/ubuntu/hummingbot'
    });

    let output = '';
    let errorOutput = '';

    pm2Process.stdout?.on('data', (data) => {
      output += data.toString();
    });

    pm2Process.stderr?.on('data', (data) => {
      errorOutput += data.toString();
    });

    pm2Process.on('close', (code) => {
      if (code !== 0) {
        console.error(`PM2 jlist failed with code ${code}: ${errorOutput}`);
        resolve({ exists: false });
        return;
      }

      try {
        const processes = JSON.parse(output);

        // Look for online bot processes
        for (const process of processes) {
          if (process.name?.startsWith('hive-') && process.pm2_env?.status === 'online') {
            // Extract user address from bot script if available
            const envVars = process.pm2_env?.env || {};
            const scriptUserAddress = envVars.HIVE_USER_ADDRESS;

            if (scriptUserAddress && scriptUserAddress.toLowerCase() === userAddress.toLowerCase()) {
              // Extract port from script args if available
              const scriptPath = process.pm2_env?.pm_exec_path;
              let apiPort: number | undefined;

              if (scriptPath && scriptPath.includes('/tmp/start_')) {
                // Try to extract port from the bot script
                try {
                  const fs = require('fs');
                  if (fs.existsSync(scriptPath)) {
                    const scriptContent = fs.readFileSync(scriptPath, 'utf8');
                    const portMatch = scriptContent.match(/--port\s+(\d+)/);
                    if (portMatch) {
                      apiPort = parseInt(portMatch[1]);
                    }
                  }
                } catch (error) {
                  console.warn(`Failed to read script ${scriptPath}:`, error);
                }
              }

              resolve({
                exists: true,
                botId: process.name,
                apiPort
              });
              return;
            }
          }
        }

        resolve({ exists: false });
      } catch (error) {
        console.error('Failed to parse PM2 jlist output:', error);
        resolve({ exists: false });
      }
    });

    pm2Process.on('error', (error) => {
      console.error('PM2 jlist error:', error);
      resolve({ exists: false });
    });
  });
}

// Check PostgreSQL database for active bots
async function checkDatabaseForRunningBot(userAddress: string): Promise<{exists: boolean, botInfo?: any}> {
  const dbConfig = {
    host: process.env.POSTGRES_HOST || '15.235.212.36',
    port: parseInt(process.env.POSTGRES_PORT || '5432'),
    database: process.env.POSTGRES_DB || 'hummingbot_api',
    user: process.env.POSTGRES_USER || 'hbot',
    password: process.env.POSTGRES_PASSWORD || 'hummingbot-api',
    ssl: false
  };

  let client: Client | null = null;

  try {
    client = new Client(dbConfig);
    await client.connect();

    // Query for active bots with recent heartbeat
    const result = await client.query(`
      SELECT
        id,
        bot_name,
        instance_name,
        user_main_address,
        deployment_status,
        run_status,
        deployed_at,
        last_heartbeat,
        CASE
          WHEN (deployment_status = 'running' OR run_status = 'running') AND
               COALESCE(EXTRACT(EPOCH FROM (NOW() - last_heartbeat)), EXTRACT(EPOCH FROM (NOW() - deployed_at))) * 1000 <= 120000
          THEN true
          ELSE false
        END as is_active
      FROM bot_runs
      WHERE user_main_address = $1
        AND (deployment_status = 'running' OR run_status = 'running')
      ORDER BY deployed_at DESC
      LIMIT 1
    `, [userAddress]);

    if (result.rows.length > 0) {
      const bot = result.rows[0];
      if (bot.is_active) {
        return {
          exists: true,
          botInfo: {
            botId: bot.bot_name,
            instanceName: bot.instance_name,
            deploymentStatus: bot.deployment_status,
            runStatus: bot.run_status,
            deployedAt: bot.deployed_at,
            lastHeartbeat: bot.last_heartbeat
          }
        };
      }
    }

    return { exists: false };

  } catch (error) {
    console.error('Database check error:', error);
    // Don't fail the spawn request due to database issues, just log and continue
    return { exists: false };
  } finally {
    if (client) {
      try {
        await client.end();
      } catch (error) {
        console.error('Error closing database connection:', error);
      }
    }
  }
}

// Create bash start script for the bot (following the same pattern as main instance)
function createBotStartScript(botConfig: {
  botId: string;
  userAddress: string;
  apiPort: number;
  dbPath: string;
  network: string;
  privateKey: string;
}): string {
  const scriptPath = `/tmp/start_${botConfig.botId}.sh`;

  const startScript = `#!/bin/bash
source ~/.bashrc
export PATH="/home/ubuntu/miniconda3/bin:$PATH"
source /home/ubuntu/miniconda3/etc/profile.d/conda.sh
conda activate hummingbot
cd /home/ubuntu/hummingbot

# Security: Private key passed via environment
export HYPERLIQUID_PRIVATE_KEY="${botConfig.privateKey}"

# Main wallet address for this bot instance
export HIVE_USER_ADDRESS="${botConfig.userAddress}"

# Bot identification for spawned instances
export HIVE_BOT_ID="${botConfig.botId}"
export HIVE_IS_SPAWNED_INSTANCE="true"

# SOCKS proxy configuration to bypass rate limiting
export HTTP_PROXY="socks5://127.0.0.1:9999"
export HTTPS_PROXY="socks5://127.0.0.1:9999"
export http_proxy="socks5://127.0.0.1:9999"
export https_proxy="socks5://127.0.0.1:9999"

# Run the bot with specific configuration - with explicit stdout/stderr redirection
# Using unbuffered python output (-u) to ensure logs appear immediately
python -u hive_dynamic_core_modular.py --port ${botConfig.apiPort} --db-path ${botConfig.dbPath} --dashboard-url http://15.235.212.36:8091 --network ${botConfig.network} 2>&1
`;

  writeFileSync(scriptPath, startScript, { mode: 0o755 });
  return scriptPath;
}

// Create PM2 ecosystem file for the bot
function createBotEcosystemFile(botConfig: {
  botId: string;
  userAddress: string;
  apiPort: number;
  dbPath: string;
  network: string;
  privateKey: string;
}): string {
  const ecosystemPath = join('/tmp', `ecosystem-${botConfig.botId}.config.js`);
  const startScriptPath = createBotStartScript(botConfig);

  const ecosystemContent = `
module.exports = {
  apps: [{
    name: '${botConfig.botId}',
    script: '${startScriptPath}',
    cwd: '/home/ubuntu/hummingbot',
    interpreter: 'bash',
    log_file: '/home/ubuntu/hummingbot/logs/${botConfig.botId}.log',
    error_file: '/home/ubuntu/hummingbot/logs/${botConfig.botId}-error.log',
    out_file: '/home/ubuntu/hummingbot/logs/${botConfig.botId}-out.log',
    time: true,
    autorestart: true,
    max_restarts: 3,
    min_uptime: '10s',
    max_memory_restart: '1G',
    watch: false,
    ignore_watch: ['node_modules', 'logs', '*.db'],
    kill_timeout: 30000,
    env: {
      HIVE_USER_ADDRESS: '${botConfig.userAddress}',
      HIVE_BOT_ID: '${botConfig.botId}',
      HIVE_IS_SPAWNED_INSTANCE: 'true',
      HYPERLIQUID_PRIVATE_KEY: '${botConfig.privateKey}',
      HTTP_PROXY: 'socks5://127.0.0.1:9999',
      HTTPS_PROXY: 'socks5://127.0.0.1:9999',
      http_proxy: 'socks5://127.0.0.1:9999',
      https_proxy: 'socks5://127.0.0.1:9999'
    }
  }]
};
`;

  writeFileSync(ecosystemPath, ecosystemContent);
  return ecosystemPath;
}

// POST /api/spawn-bot - Spawn new bot instance
export async function POST(request: NextRequest) {
  try {
    const body: SpawnBotRequest = await request.json();

    // Validate required fields
    if (!body.userAddress || !body.agentWalletPrivateKey) {
      return NextResponse.json({
        error: 'Missing required fields: userAddress and agentWalletPrivateKey'
      }, { status: 400 });
    }

    // Validate user address format (basic validation)
    if (!/^0x[a-fA-F0-9]{40}$/.test(body.userAddress)) {
      return NextResponse.json({
        error: 'Invalid user address format'
      }, { status: 400 });
    }

    // Validate private key
    if (!validateHyperliquidPrivateKey(body.agentWalletPrivateKey)) {
      return NextResponse.json({
        error: 'Invalid Hyperliquid private key format'
      }, { status: 400 });
    }

    // Multi-layer duplicate prevention check

    // 1. Check PM2 for running bots (fast, immediate)
    console.log(`Checking PM2 for existing bots for user ${body.userAddress}...`);
    const pm2Check = await checkPM2ForRunningBot(body.userAddress);
    if (pm2Check.exists) {
      return NextResponse.json({
        error: 'User already has a running bot instance in PM2',
        existingBot: {
          botId: pm2Check.botId,
          apiPort: pm2Check.apiPort,
          status: 'running',
          source: 'PM2'
        }
      }, { status: 409 });
    }

    // 2. Check PostgreSQL database for active bots (comprehensive)
    console.log(`Checking database for existing bots for user ${body.userAddress}...`);
    const dbCheck = await checkDatabaseForRunningBot(body.userAddress);
    if (dbCheck.exists) {
      return NextResponse.json({
        error: 'User already has an active bot instance in database',
        existingBot: {
          ...dbCheck.botInfo,
          status: 'running',
          source: 'Database'
        }
      }, { status: 409 });
    }

    // 3. Check in-memory tracking (backward compatibility)
    const existingBot = Array.from(SPAWNED_BOTS.values()).find(
      bot => bot.userAddress === body.userAddress && bot.status === 'running'
    );

    if (existingBot) {
      return NextResponse.json({
        error: 'User already has a running bot instance in memory',
        existingBot: {
          botId: existingBot.botId,
          apiPort: existingBot.apiPort,
          status: existingBot.status,
          source: 'Memory'
        }
      }, { status: 409 });
    }

    // Find available port
    const portResult = await findAvailablePort();
    if (!portResult.port) {
      return NextResponse.json({
        error: 'No available ports for new bot instance',
        debug: portResult.debug
      }, { status: 503 });
    }
    const apiPort = portResult.port;

    // Generate bot configuration
    const botId = generateBotId(body.userAddress, apiPort);
    const network = body.network || 'testnet';
    const dbPath = `/home/ubuntu/hummingbot/user_bots/${body.userAddress}/hive_strategies.db`;

    // Ensure user bot directory exists
    const userBotDir = `/home/ubuntu/hummingbot/user_bots/${body.userAddress}`;
    if (!existsSync(userBotDir)) {
      mkdirSync(userBotDir, { recursive: true });
    }

    // Ensure logs directory exists
    const logsDir = '/home/ubuntu/hummingbot/logs';
    if (!existsSync(logsDir)) {
      mkdirSync(logsDir, { recursive: true });
    }

    // Create bot configuration
    const botConfig = {
      botId,
      userAddress: body.userAddress,
      apiPort,
      dbPath,
      network,
      privateKey: body.agentWalletPrivateKey
    };

    // Create PM2 ecosystem file
    const ecosystemPath = createBotEcosystemFile(botConfig);

    // Track the bot instance
    SPAWNED_BOTS.set(botId, {
      botId,
      userAddress: body.userAddress,
      apiPort,
      processName: botId,
      dbPath,
      status: 'starting',
      createdAt: new Date().toISOString()
    });

    // Spawn the bot using PM2
    return new Promise<NextResponse>((resolve) => {
      const pm2Process = spawn('pm2', ['start', ecosystemPath], {
        cwd: '/home/ubuntu/hummingbot',
        env: {
          ...process.env,
          PATH: process.env.PATH
        }
      });

      let output = '';
      let errorOutput = '';

      pm2Process.stdout?.on('data', (data) => {
        output += data.toString();
      });

      pm2Process.stderr?.on('data', (data) => {
        errorOutput += data.toString();
      });

      pm2Process.on('close', (code) => {
        if (code === 0) {
          // Update bot status
          const botInfo = SPAWNED_BOTS.get(botId);
          if (botInfo) {
            botInfo.status = 'running';
            SPAWNED_BOTS.set(botId, botInfo);
          }

          console.log(`✅ Bot ${botId} spawned successfully for user ${body.userAddress}`);

          resolve(NextResponse.json({
            success: true,
            bot: {
              botId,
              userAddress: body.userAddress,
              apiPort,
              dbPath,
              network,
              status: 'running',
              createdAt: new Date().toISOString(),
              apiUrl: `http://localhost:${apiPort}`,
              dashboardUrl: `http://15.235.212.36:8091/bot/${botId}`
            },
            debug: {
              portAllocation: portResult.debug
            }
          }));
        } else {
          // Update bot status to error
          const botInfo = SPAWNED_BOTS.get(botId);
          if (botInfo) {
            botInfo.status = 'error';
            SPAWNED_BOTS.set(botId, botInfo);
          }

          // Release the port
          USED_PORTS.delete(apiPort);

          console.error(`❌ Failed to spawn bot ${botId}: PM2 exit code ${code}`);
          console.error(`PM2 output: ${output}`);
          console.error(`PM2 error: ${errorOutput}`);

          resolve(NextResponse.json({
            error: 'Failed to spawn bot instance',
            details: {
              exitCode: code,
              output: output.slice(-1000), // Last 1000 chars
              error: errorOutput.slice(-1000)
            }
          }, { status: 500 }));
        }
      });

      pm2Process.on('error', (error) => {
        // Release the port
        USED_PORTS.delete(apiPort);

        // Update bot status
        const botInfo = SPAWNED_BOTS.get(botId);
        if (botInfo) {
          botInfo.status = 'error';
          SPAWNED_BOTS.set(botId, botInfo);
        }

        console.error(`❌ Error spawning bot ${botId}:`, error);

        resolve(NextResponse.json({
          error: 'Failed to spawn bot instance',
          details: error.message
        }, { status: 500 }));
      });
    });

  } catch (error) {
    console.error('Error in spawn-bot API:', error);
    return NextResponse.json({
      error: 'Internal server error',
      details: error instanceof Error ? error.message : 'Unknown error'
    }, { status: 500 });
  }
}

// GET /api/spawn-bot - List spawned bot instances
export async function GET(request: NextRequest) {
  try {
    const url = new URL(request.url);
    const userAddress = url.searchParams.get('userAddress');

    let bots = Array.from(SPAWNED_BOTS.values());

    // Filter by user address if provided
    if (userAddress) {
      bots = bots.filter(bot => bot.userAddress === userAddress);
    }

    return NextResponse.json({
      success: true,
      bots: bots.map(bot => ({
        botId: bot.botId,
        userAddress: bot.userAddress,
        apiPort: bot.apiPort,
        status: bot.status,
        createdAt: bot.createdAt,
        apiUrl: `http://localhost:${bot.apiPort}`,
        dbPath: bot.dbPath
      }))
    });

  } catch (error) {
    console.error('Error listing spawned bots:', error);
    return NextResponse.json({
      error: 'Failed to list spawned bots',
      details: error instanceof Error ? error.message : 'Unknown error'
    }, { status: 500 });
  }
}

// DELETE /api/spawn-bot - Delete bot by botId or userAddress (via POST body)
export async function DELETE(request: NextRequest) {
  try {
    const body = await request.json();
    const { botId, userAddress } = body;

    if (!botId && !userAddress) {
      return NextResponse.json({
        error: 'Either botId or userAddress is required'
      }, { status: 400 });
    }

    let botsToDelete: string[] = [];

    if (botId) {
      // Delete specific bot by ID - check both memory and PM2

      // 1. Check in-memory bots
      if (SPAWNED_BOTS.has(botId)) {
        botsToDelete.push(botId);
      }

      // 2. Check PM2 for this specific bot ID
      await new Promise<void>((resolve) => {
        const pm2List = spawn('pm2', ['jlist'], { cwd: '/home/ubuntu/hummingbot' });
        let output = '';

        pm2List.stdout?.on('data', (data) => {
          output += data.toString();
        });

        pm2List.on('close', (code) => {
          if (code === 0) {
            try {
              const processes = JSON.parse(output);
              console.log(`PM2 check for ${botId}: Found ${processes.length} processes`);
              const foundProcess = processes.find((p: any) => p.name === botId);
              console.log(`PM2 process search result:`, foundProcess ? 'FOUND' : 'NOT FOUND');
              if (foundProcess && !botsToDelete.includes(botId)) {
                botsToDelete.push(botId);
                console.log(`Added bot ${botId} to deletion list from PM2`);
              }
            } catch (error) {
              console.error('Failed to parse PM2 output:', error);
            }
          } else {
            console.error(`PM2 jlist failed with code ${code}`);
          }
          resolve();
        });

        pm2List.on('error', (error) => {
          console.error('PM2 jlist error:', error);
          resolve();
        });
      });

    } else if (userAddress) {
      // Delete all bots for user - check both memory and PM2

      // 1. Check in-memory bots
      for (const [id, bot] of SPAWNED_BOTS.entries()) {
        if (bot.userAddress === userAddress) {
          botsToDelete.push(id);
        }
      }

      // 2. Check PM2 processes for this user address
      const pm2Check = await checkPM2ForRunningBot(userAddress);
      if (pm2Check.exists && pm2Check.botId && !botsToDelete.includes(pm2Check.botId)) {
        botsToDelete.push(pm2Check.botId);
      }

      // 3. Additional PM2 scan for any bot processes with this user address
      await new Promise<void>((resolve) => {
        const pm2List = spawn('pm2', ['jlist'], { cwd: '/home/ubuntu/hummingbot' });
        let output = '';

        pm2List.stdout?.on('data', (data) => {
          output += data.toString();
        });

        pm2List.on('close', (code) => {
          if (code === 0) {
            try {
              const processes = JSON.parse(output);
              for (const process of processes) {
                if (process.name?.startsWith('hive-')) {
                  // Check if this bot belongs to the user
                  const envVars = process.pm2_env?.env || {};
                  const scriptUserAddress = envVars.HIVE_USER_ADDRESS;

                  if (scriptUserAddress && scriptUserAddress.toLowerCase() === userAddress.toLowerCase()) {
                    if (!botsToDelete.includes(process.name)) {
                      botsToDelete.push(process.name);
                    }
                  }
                }
              }
            } catch (error) {
              console.error('Failed to parse PM2 output for user scan:', error);
            }
          }
          resolve();
        });

        pm2List.on('error', () => resolve());
      });
    }

    if (botsToDelete.length === 0) {
      // Add debugging info - get PM2 process list for debugging
      let pm2ProcessNames: string[] = [];
      try {
        const pm2Output = await new Promise<string>((resolve) => {
          const pm2List = spawn('pm2', ['jlist'], { cwd: '/home/ubuntu/hummingbot' });
          let output = '';
          pm2List.stdout?.on('data', (data) => { output += data.toString(); });
          pm2List.on('close', () => resolve(output));
          pm2List.on('error', () => resolve('[]'));
        });

        const processes = JSON.parse(pm2Output);
        pm2ProcessNames = processes.map((p: any) => p.name).filter((name: string) => name?.startsWith('hive-'));
      } catch (error) {
        pm2ProcessNames = ['Error reading PM2 processes'];
      }

      const debugInfo = {
        checkedBotId: botId,
        checkedUserAddress: userAddress,
        inMemoryBots: Array.from(SPAWNED_BOTS.keys()),
        memoryBotsForUser: userAddress ? Array.from(SPAWNED_BOTS.values()).filter(bot => bot.userAddress === userAddress).map(bot => bot.botId) : [],
        pm2BotProcesses: pm2ProcessNames,
        botsToDeleteFound: botsToDelete
      };

      return NextResponse.json({
        error: 'No bots found to delete',
        debug: debugInfo
      }, { status: 404 });
    }

    const deleteResults = [];

    // Delete each bot
    for (const botId of botsToDelete) {
      const botInfo = SPAWNED_BOTS.get(botId);

      try {
        // Stop the bot using PM2
        const pm2Result = await new Promise<boolean>((resolve) => {
          const pm2Process = spawn('pm2', ['delete', botId], {
            cwd: '/home/ubuntu/hummingbot'
          });

          pm2Process.on('close', (code) => {
            resolve(code === 0);
          });

          pm2Process.on('error', () => {
            resolve(false);
          });
        });

        // Update database to mark bot as stopped
        let dbUpdateResult = false;
        try {
          const dbConfig = {
            host: process.env.POSTGRES_HOST || '15.235.212.36',
            port: parseInt(process.env.POSTGRES_PORT || '5432'),
            database: process.env.POSTGRES_DB || 'hummingbot_api',
            user: process.env.POSTGRES_USER || 'hbot',
            password: process.env.POSTGRES_PASSWORD || 'hummingbot-api',
            ssl: false
          };

          const client = new Client(dbConfig);
          await client.connect();

          // Update bot_runs table to mark as stopped
          const updateResult = await client.query(`
            UPDATE bot_runs
            SET deployment_status = 'stopped',
                run_status = 'stopped',
                updated_at = NOW()
            WHERE bot_name = $1 OR instance_name = $1
          `, [botId]);

          await client.end();
          dbUpdateResult = updateResult.rowCount > 0;

          if (dbUpdateResult) {
            console.log(`✅ Database updated for bot ${botId}: marked as stopped`);
          } else {
            console.warn(`⚠️ No database records found to update for bot ${botId}`);
          }

        } catch (dbError) {
          console.error(`❌ Failed to update database for bot ${botId}:`, dbError);
          // Don't fail the entire deletion if database update fails
        }

        // Clean up registry and ports if bot was in memory
        if (botInfo) {
          USED_PORTS.delete(botInfo.apiPort);
          SPAWNED_BOTS.delete(botId);
        }

        // Clean up temporary files
        try {
          const { unlinkSync } = require('fs');
          const startScriptPath = `/tmp/start_${botId}.sh`;
          const ecosystemPath = `/tmp/ecosystem-${botId}.config.js`;

          if (existsSync(startScriptPath)) {
            unlinkSync(startScriptPath);
          }
          if (existsSync(ecosystemPath)) {
            unlinkSync(ecosystemPath);
          }
        } catch (fileError) {
          console.warn(`Failed to clean up files for ${botId}:`, fileError);
        }

        deleteResults.push({
          botId: botId,
          status: pm2Result ? 'stopped' : 'registry_cleaned',
          pm2Success: pm2Result,
          dbUpdated: dbUpdateResult
        });

        console.log(`✅ Bot ${botId} cleaned up (PM2: ${pm2Result ? 'success' : 'failed'}, Registry: cleaned, DB: ${dbUpdateResult ? 'updated' : 'failed'})`);

      } catch (error) {
        // Still clean up registry to prevent orphaned entries
        const botInfo = SPAWNED_BOTS.get(botId);
        if (botInfo) {
          USED_PORTS.delete(botInfo.apiPort);
          SPAWNED_BOTS.delete(botId);
        }

        deleteResults.push({
          botId: botId,
          status: 'error',
          error: error instanceof Error ? error.message : 'Unknown error'
        });

        console.error(`❌ Error cleaning up bot ${botId}:`, error);
      }
    }

    return NextResponse.json({
      success: true,
      message: `Cleaned up ${deleteResults.length} bot(s)`,
      results: deleteResults
    });

  } catch (error) {
    console.error('Error in DELETE spawn-bot:', error);
    return NextResponse.json({
      error: 'Failed to delete bot instance(s)',
      details: error instanceof Error ? error.message : 'Unknown error'
    }, { status: 500 });
  }
}