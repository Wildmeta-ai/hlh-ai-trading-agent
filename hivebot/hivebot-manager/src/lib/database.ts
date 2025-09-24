// Database connection for Hivebot Manager
// Connects to PostgreSQL database on the test server

import { Client, Pool } from 'pg';
import { BotInstance, DashboardMetrics } from '@/types';

interface DatabaseConfig {
  type: 'remote' | 'local';
  postgresql?: {
    host: string;
    port: number;
    database: string;
    user: string;
    password: string;
    ssl?: {
      rejectUnauthorized: boolean;
    };
  };
  localPath?: string;
}

// Configuration - can be overridden via environment variables
const dbConfig: DatabaseConfig = {
  type: (process.env.DATABASE_TYPE as 'remote' | 'local') || 'remote', // Always use remote PostgreSQL unless explicitly set
  postgresql: {
    host: process.env.POSTGRES_HOST || '15.235.212.36',
    port: parseInt(process.env.POSTGRES_PORT || '5432'),
    database: process.env.POSTGRES_DB || 'hummingbot_api',
    user: process.env.POSTGRES_USER || 'hbot',
    password: process.env.POSTGRES_PASSWORD || 'hummingbot-api',
    ssl: false  // Server does not support SSL
  },
  localPath: process.env.LOCAL_DB_PATH || '/Users/yoshiyuki/hummingbot/hive_strategies.db'
};

class DatabaseClient {
  private config: DatabaseConfig;
  private pool: Pool | null = null;

  constructor(config: DatabaseConfig) {
    this.config = config;
    // TEMPORARILY DISABLE connection pooling to test direct connections
    // The other working web app might not be using connection pooling
    if (this.config.type === 'remote' && this.config.postgresql) {
      console.log('[Database] Using direct connections (pooling disabled for debugging)');
      this.pool = null;  // Force direct connections
    }
  }

  // Create PostgreSQL client connection
  private async createPostgreSQLClient(): Promise<Client> {
    if (!this.config.postgresql) {
      throw new Error('PostgreSQL configuration not found');
    }

    const client = new Client(this.config.postgresql);
    await client.connect();
    return client;
  }

  // Public method to get a client for direct database operations
  async getClient(): Promise<Client> {
    if (this.pool) {
      // Use connection pool to get a client
      return this.pool.connect();
    } else {
      // Fallback to direct connection
      return this.createPostgreSQLClient();
    }
  }

  // Get bot instances from PostgreSQL database
  async getBotInstances(): Promise<BotInstance[]> {
    if (this.config.type === 'remote') {
      let client: Client | null = null;
      try {
        client = await this.createPostgreSQLClient();

        // Query bot_runs table with heartbeat calculation done in SQL
        const result = await client.query(`
          SELECT
            id,
            bot_name,
            instance_name,
            deployed_at,
            strategy_type,
            strategy_name,
            config_name,
            stopped_at,
            deployment_status,
            run_status,
            account_name,
            image_version,
            error_message,
            deployment_config,
            user_main_address,
            -- Calculate heartbeat status in SQL to avoid timezone issues
            CASE
              WHEN (deployment_status = 'running' OR run_status = 'running') AND
                   COALESCE(EXTRACT(EPOCH FROM (NOW() - last_heartbeat)), EXTRACT(EPOCH FROM (NOW() - deployed_at))) * 1000 <= 120000 -- 2 minutes in milliseconds
              THEN 'running'
              ELSE 'offline'
            END as calculated_status,
            -- Use last_heartbeat if available, otherwise deployed_at
            COALESCE(last_heartbeat, deployed_at) as last_heartbeat
          FROM bot_runs
          WHERE deployment_status = 'running' OR run_status = 'running'
          ORDER BY deployed_at DESC
        `);

        console.log(`[Database] Found ${result.rows.length} bot runs in PostgreSQL`);

        // Convert PostgreSQL results to BotInstance format - use SQL-calculated status
        return result.rows.map((row: any) => {
          const deployedAt = new Date(row.deployed_at);
          const uptime = row.stopped_at ? 0 : Math.floor((Date.now() - deployedAt.getTime()) / 1000);

          // Use the status calculated by PostgreSQL (no more JavaScript timezone issues!)
          const isRunning = row.calculated_status === 'running';

          // Parse deployment_config to get actual data - no defaults, unknown is unknown
          let totalStrategies = 0;
          let totalActions = 0;
          let actionsPerMinute = 0;
          let strategyNames: string[] = [];
          let apiPort: number | undefined = undefined; // No fake defaults

          if (row.deployment_config) {
            try {
              const config = JSON.parse(row.deployment_config);
              if (config.active_strategies && typeof config.active_strategies === 'number') {
                totalStrategies = config.active_strategies;
                // Generate strategy names based on count for better display
                if (totalStrategies > 1) {
                  strategyNames = [`${row.strategy_type || 'hive_trading_multi'}`];
                }
              }
              // Extract activity metrics from config
              if (config.total_actions && typeof config.total_actions === 'number') {
                totalActions = config.total_actions;
              }
              if (config.actions_per_minute && typeof config.actions_per_minute === 'number') {
                actionsPerMinute = config.actions_per_minute;
              }
              // Extract API port from config - only if actually present
              if (config.api_port && typeof config.api_port === 'number') {
                apiPort = config.api_port;
              }
            } catch (e) {
              console.warn(`[Database] Failed to parse deployment_config for bot ${row.id}:`, e);
            }
          }

          return {
            id: row.id.toString(),
            name: row.instance_name || row.bot_name,
            status: row.calculated_status, // Use SQL-calculated status directly
            strategies: strategyNames,
            uptime,
            total_strategies: totalStrategies,
            total_actions: totalActions,
            actions_per_minute: actionsPerMinute,
            last_activity: row.last_heartbeat, // Use SQL-calculated heartbeat timestamp
            memory_usage: 0,
            cpu_usage: 0,
            api_port: apiPort || 0, // 0 if unknown, no fake data
            user_main_address: row.user_main_address || undefined // User main wallet address
          } as BotInstance;
        });

      } catch (error) {
        console.error('[Database] PostgreSQL query failed:', error);
        return [];
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

    // Return empty array for local mode (would implement SQLite here)
    return [];
  }

  // Get dashboard metrics
  async getDashboardMetrics(): Promise<DashboardMetrics> {
    const bots = await this.getBotInstances();
    const activeBots = bots.filter(bot => bot.status === 'running');

    return {
      total_bots: bots.length,
      active_bots: activeBots.length,
      total_strategies: bots.reduce((sum, bot) => sum + bot.total_strategies, 0),
      active_strategies: activeBots.reduce((sum, bot) => sum + bot.total_strategies, 0),
      total_actions_24h: bots.reduce((sum, bot) => sum + bot.total_actions, 0),
      error_rate: bots.filter(bot => bot.status === 'error').length / Math.max(bots.length, 1),
      uptime_percentage: activeBots.length > 0 ?
        activeBots.reduce((sum, bot) => sum + (bot.uptime / (bot.uptime + 1)), 0) / activeBots.length * 100 : 0
    };
  }

  // Initialize activity-related database tables
  async initializeActivityTables(): Promise<void> {
    let client: Client | null = null;
    try {
      client = await this.createPostgreSQLClient();

      // Create hive_instances table
      await client.query(`
        CREATE TABLE IF NOT EXISTS hive_instances (
          hive_id VARCHAR(255) PRIMARY KEY,
          hostname VARCHAR(255) NOT NULL,
          api_port INTEGER DEFAULT 8080,
          last_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
          market_data JSONB,
          status VARCHAR(50) DEFAULT 'active',
          created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
      `);

      // Add api_port column if it doesn't exist (for existing installations)
      await client.query(`
        ALTER TABLE hive_instances
        ADD COLUMN IF NOT EXISTS api_port INTEGER DEFAULT 8080
      `);

      // Add last_heartbeat column to bot_runs table if it doesn't exist (for heartbeat tracking)
      await client.query(`
        ALTER TABLE bot_runs
        ADD COLUMN IF NOT EXISTS last_heartbeat TIMESTAMP WITH TIME ZONE
      `);

      // Add user_main_address column to bot_runs table if it doesn't exist (for user filtering)
      await client.query(`
        ALTER TABLE bot_runs
        ADD COLUMN IF NOT EXISTS user_main_address VARCHAR(255)
      `);

      // Create hive_strategies table
      await client.query(`
        CREATE TABLE IF NOT EXISTS hive_strategies (
          id SERIAL PRIMARY KEY,
          hive_id VARCHAR(255) NOT NULL,
          strategy_name VARCHAR(255) NOT NULL,
          status VARCHAR(50) NOT NULL,
          total_actions INTEGER DEFAULT 0,
          successful_orders INTEGER DEFAULT 0,
          failed_orders INTEGER DEFAULT 0,
          last_action_time TIMESTAMP WITH TIME ZONE,
          refresh_interval FLOAT DEFAULT 5.0,
          performance_per_min FLOAT DEFAULT 0.0,
          recent_actions JSONB,
          created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
          updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
          UNIQUE(hive_id, strategy_name),
          FOREIGN KEY (hive_id) REFERENCES hive_instances(hive_id) ON DELETE CASCADE
        )
      `);

      // Create strategy configuration table (master table for strategy definitions)
      await client.query(`
        CREATE TABLE IF NOT EXISTS hive_strategy_configs (
          name VARCHAR(255) PRIMARY KEY,
          hive_id VARCHAR(255),
          strategy_type VARCHAR(100) NOT NULL DEFAULT 'pure_market_making',
          connector_type VARCHAR(100) NOT NULL,
          trading_pairs TEXT NOT NULL,  -- JSON array

          -- Core strategy parameters
          bid_spread REAL DEFAULT 0.05,
          ask_spread REAL DEFAULT 0.05,
          order_amount REAL DEFAULT 0.001,
          order_levels INTEGER DEFAULT 1,
          order_refresh_time REAL DEFAULT 5.0,
          order_level_spread REAL DEFAULT 0.0,
          order_level_amount REAL DEFAULT 0.0,

          -- Authentication
          api_key TEXT DEFAULT '',
          api_secret TEXT DEFAULT '',
          passphrase TEXT DEFAULT '',
          private_key TEXT DEFAULT '',

          -- Advanced parameters (JSON)
          strategy_params TEXT DEFAULT '{}',

          -- Risk management
          inventory_target_base_pct REAL DEFAULT 50.0,
          inventory_range_multiplier REAL DEFAULT 1.0,
          hanging_orders_enabled BOOLEAN DEFAULT FALSE,
          hanging_orders_cancel_pct REAL DEFAULT 10.0,

          -- Position management
          leverage INTEGER DEFAULT 1,
          position_mode VARCHAR(20) DEFAULT 'ONEWAY',

          -- Order management
          order_optimization_enabled BOOLEAN DEFAULT TRUE,
          ask_order_optimization_depth REAL DEFAULT 0.0,
          bid_order_optimization_depth REAL DEFAULT 0.0,
          price_ceiling REAL DEFAULT -1.0,
          price_floor REAL DEFAULT -1.0,

          -- Strategy-specific
          ping_pong_enabled BOOLEAN DEFAULT FALSE,
          min_profitability REAL DEFAULT 0.003,
          min_price_diff_pct REAL DEFAULT 0.1,
          max_order_size REAL DEFAULT 1.0,

          -- Metadata
          enabled BOOLEAN DEFAULT TRUE,
          created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
          updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
          FOREIGN KEY (hive_id) REFERENCES hive_instances(hive_id) ON DELETE SET NULL
        )
      `);

      // Create hive_activities table
      await client.query(`
        CREATE TABLE IF NOT EXISTS hive_activities (
          id SERIAL PRIMARY KEY,
          hive_id VARCHAR(255) NOT NULL,
          strategy_name VARCHAR(255) NOT NULL,
          activity_type VARCHAR(100) NOT NULL,
          success BOOLEAN NOT NULL,
          timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
          created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

          -- **ADDED**: Order details for better tracking
          order_id VARCHAR(255),
          price DECIMAL(20, 8),
          amount DECIMAL(20, 8),
          trading_pair VARCHAR(50),

          UNIQUE(hive_id, strategy_name, activity_type, timestamp),
          FOREIGN KEY (hive_id) REFERENCES hive_instances(hive_id) ON DELETE CASCADE
        )
      `);

      // **MIGRATION**: Add new columns to existing hive_activities table
      try {
        await client.query(`
          ALTER TABLE hive_activities
          ADD COLUMN IF NOT EXISTS order_id VARCHAR(255),
          ADD COLUMN IF NOT EXISTS price DECIMAL(20, 8),
          ADD COLUMN IF NOT EXISTS amount DECIMAL(20, 8),
          ADD COLUMN IF NOT EXISTS trading_pair VARCHAR(50)
        `);
        console.log('✅ Applied hive_activities schema migration');
      } catch (migrationError) {
        console.log('⚠️ Migration may have already been applied:', migrationError);
      }

      // Create indexes for better performance
      await client.query(`CREATE INDEX IF NOT EXISTS idx_hive_instances_last_seen ON hive_instances(last_seen)`);
      await client.query(`CREATE INDEX IF NOT EXISTS idx_hive_strategies_hive_id ON hive_strategies(hive_id)`);
      await client.query(`CREATE INDEX IF NOT EXISTS idx_hive_strategy_configs_hive_id ON hive_strategy_configs(hive_id)`);
      await client.query(`CREATE INDEX IF NOT EXISTS idx_hive_strategy_configs_enabled ON hive_strategy_configs(enabled)`);
      await client.query(`CREATE INDEX IF NOT EXISTS idx_hive_activities_hive_id_timestamp ON hive_activities(hive_id, timestamp DESC)`);
      await client.query(`CREATE INDEX IF NOT EXISTS idx_hive_activities_strategy_timestamp ON hive_activities(strategy_name, timestamp DESC)`);

      await client.query(`
        CREATE TABLE IF NOT EXISTS hive_strategy_snapshots (
          id SERIAL PRIMARY KEY,
          strategy_name VARCHAR(255) NOT NULL,
          hive_id VARCHAR(255),
          user_id VARCHAR(255),
          taken_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
          total_actions INTEGER DEFAULT 0,
          successful_actions INTEGER DEFAULT 0,
          failed_actions INTEGER DEFAULT 0,
          total_volume NUMERIC(30, 10) DEFAULT 0,
          avg_trade_size NUMERIC(30, 10) DEFAULT 0,
          buy_count INTEGER DEFAULT 0,
          sell_count INTEGER DEFAULT 0,
          last_activity TIMESTAMP WITH TIME ZONE,
          unrealized_pnl NUMERIC(30, 10) DEFAULT 0,
          realized_pnl NUMERIC(30, 10) DEFAULT 0,
          position_size NUMERIC(30, 10) DEFAULT 0,
          metadata JSONB DEFAULT '{}'
        )
      `);

      await client.query(`CREATE INDEX IF NOT EXISTS idx_hive_strategy_snapshots_strategy ON hive_strategy_snapshots(strategy_name)`);
      await client.query(`CREATE INDEX IF NOT EXISTS idx_hive_strategy_snapshots_taken_at ON hive_strategy_snapshots(taken_at DESC)`);

      console.log('✅ Activity database tables initialized');

    } catch (error) {
      console.error('❌ Failed to initialize activity tables:', error);
      throw error;
    } finally {
      if (client) {
        await client.end();
      }
    }
  }

  // Register/update bot instance (UPSERT into database)
  async updateBotInstance(bot: Partial<BotInstance>): Promise<boolean> {
    if (this.config.type === 'remote' && bot.id) {
      let client: Client | null = null;
      try {
        client = await this.createPostgreSQLClient();

        // DEBUG: Log what we're trying to save
        console.log(`[DEBUG] Saving bot to database:`, {
          name: bot.name,
          user_main_address: bot.user_main_address,
          api_port: bot.api_port
        });

        // UPSERT bot instance into bot_runs table
        // This handles both new registrations and heartbeat updates
        const deploymentConfig = JSON.stringify({
          active_strategies: bot.total_strategies || 0,
          api_port: bot.api_port || 8080,
          total_actions: bot.total_actions || 0,
          actions_per_minute: bot.actions_per_minute || 0,
          memory_usage: bot.memory_usage || 0,
          cpu_usage: bot.cpu_usage || 0
        });

        // Check if bot already exists
        const checkQuery = `SELECT id FROM bot_runs WHERE instance_name = $1 LIMIT 1`;
        const existingBot = await client.query(checkQuery, [bot.name]);

        if (existingBot.rows.length > 0) {
          // Update existing bot
          const updateQuery = `
            UPDATE bot_runs SET
              deployment_status = $1,
              run_status = $2,
              deployment_config = $3,
              last_heartbeat = NOW(),
              user_main_address = $4
            WHERE instance_name = $5
            RETURNING id;
          `;

          const result = await client.query(updateQuery, [
            bot.status === 'running' ? 'running' : 'stopped', // deployment_status
            bot.status === 'running' ? 'running' : 'stopped', // run_status
            deploymentConfig,                                  // deployment_config
            bot.user_main_address || null,                     // user_main_address
            bot.name                                           // instance_name
          ]);
        } else {
          // Insert new bot
          const insertQuery = `
            INSERT INTO bot_runs (
              bot_name, instance_name, deployed_at, strategy_type, strategy_name,
              config_name, deployment_status, run_status, account_name,
              image_version, deployment_config, last_heartbeat, user_main_address
            ) VALUES ($1, $2, NOW(), $3, $4, $5, $6, $7, $8, $9, $10, NOW(), $11)
            RETURNING id;
          `;

          const result = await client.query(insertQuery, [
            bot.name,                                    // bot_name
            bot.name,                                    // instance_name
            'hive_multi_strategy',                       // strategy_type
            (bot.strategies || []).join(',') || 'multi', // strategy_name
            'live_config',                               // config_name
            bot.status === 'running' ? 'running' : 'stopped', // deployment_status
            bot.status === 'running' ? 'running' : 'stopped', // run_status
            'live_account',                              // account_name
            '1.0.0',                                     // image_version
            deploymentConfig,                            // deployment_config
            bot.user_main_address || null                // user_main_address
          ]);
        }

        console.log(`[Database] Bot ${bot.id} registered/updated successfully`);
        return true;
      } catch (error) {
        console.error('[Database] Failed to update bot instance:', error);
        return false;
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
    return false;
  }

  // Create strategy configuration in PostgreSQL (master source)
  async createStrategyConfig(strategyConfig: any): Promise<{success: boolean, strategy_name: string}> {
    let client: Client | null = null;
    try {
      client = await this.createPostgreSQLClient();

      // Insert strategy configuration into PostgreSQL
      const insertQuery = `
        INSERT INTO hive_strategy_configs (
          name, hive_id, user_id, strategy_type, connector_type, trading_pairs,
          bid_spread, ask_spread, order_amount, order_levels, order_refresh_time,
          order_level_spread, order_level_amount, strategy_params,
          inventory_target_base_pct, inventory_range_multiplier,
          hanging_orders_enabled, hanging_orders_cancel_pct,
          leverage, position_mode, order_optimization_enabled,
          ask_order_optimization_depth, bid_order_optimization_depth,
          price_ceiling, price_floor, ping_pong_enabled,
          min_profitability, min_price_diff_pct, max_order_size,
          enabled, created_at, updated_at
        ) VALUES (
          $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15,
          $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26, $27, $28,
          $29, $30, NOW(), NOW()
        ) ON CONFLICT (name) DO UPDATE SET
          hive_id = EXCLUDED.hive_id,
          user_id = EXCLUDED.user_id,
          strategy_type = EXCLUDED.strategy_type,
          connector_type = EXCLUDED.connector_type,
          trading_pairs = EXCLUDED.trading_pairs,
          bid_spread = EXCLUDED.bid_spread,
          ask_spread = EXCLUDED.ask_spread,
          order_amount = EXCLUDED.order_amount,
          order_levels = EXCLUDED.order_levels,
          order_refresh_time = EXCLUDED.order_refresh_time,
          order_level_spread = EXCLUDED.order_level_spread,
          order_level_amount = EXCLUDED.order_level_amount,
          strategy_params = EXCLUDED.strategy_params,
          inventory_target_base_pct = EXCLUDED.inventory_target_base_pct,
          inventory_range_multiplier = EXCLUDED.inventory_range_multiplier,
          hanging_orders_enabled = EXCLUDED.hanging_orders_enabled,
          hanging_orders_cancel_pct = EXCLUDED.hanging_orders_cancel_pct,
          leverage = EXCLUDED.leverage,
          position_mode = EXCLUDED.position_mode,
          order_optimization_enabled = EXCLUDED.order_optimization_enabled,
          ask_order_optimization_depth = EXCLUDED.ask_order_optimization_depth,
          bid_order_optimization_depth = EXCLUDED.bid_order_optimization_depth,
          price_ceiling = EXCLUDED.price_ceiling,
          price_floor = EXCLUDED.price_floor,
          ping_pong_enabled = EXCLUDED.ping_pong_enabled,
          min_profitability = EXCLUDED.min_profitability,
          min_price_diff_pct = EXCLUDED.min_price_diff_pct,
          max_order_size = EXCLUDED.max_order_size,
          enabled = EXCLUDED.enabled,
          updated_at = NOW()
        RETURNING name;
      `;

      const result = await client.query(insertQuery, [
        strategyConfig.name,
        strategyConfig.hive_id || null,
        strategyConfig.user_id || null,
        strategyConfig.strategy_type || 'pure_market_making',
        strategyConfig.connector_type,
        JSON.stringify(strategyConfig.trading_pairs),
        strategyConfig.bid_spread || 0.05,
        strategyConfig.ask_spread || 0.05,
        strategyConfig.order_amount || 0.001,
        strategyConfig.order_levels || 1,
        strategyConfig.order_refresh_time || 5.0,
        strategyConfig.order_level_spread || 0.0,
        strategyConfig.order_level_amount || 0.0,
        JSON.stringify(strategyConfig.strategy_params || {}),
        strategyConfig.inventory_target_base_pct || 50.0,
        strategyConfig.inventory_range_multiplier || 1.0,
        strategyConfig.hanging_orders_enabled || false,
        strategyConfig.hanging_orders_cancel_pct || 10.0,
        strategyConfig.leverage || 1,
        strategyConfig.position_mode || 'ONEWAY',
        strategyConfig.order_optimization_enabled || true,
        strategyConfig.ask_order_optimization_depth || 0.0,
        strategyConfig.bid_order_optimization_depth || 0.0,
        strategyConfig.price_ceiling || -1.0,
        strategyConfig.price_floor || -1.0,
        strategyConfig.ping_pong_enabled || false,
        strategyConfig.min_profitability || 0.003,
        strategyConfig.min_price_diff_pct || 0.1,
        strategyConfig.max_order_size || 1.0,
        strategyConfig.enabled !== false
      ]);

      console.log(`[Database] Strategy config ${strategyConfig.name} created/updated in PostgreSQL (user: ${strategyConfig.user_id || 'unknown'})`);
      return { success: true, strategy_name: result.rows[0].name };

    } catch (error) {
      console.error('[Database] Failed to create strategy config:', error);
      console.error('[Database] Error details:', {
        message: error.message,
        code: error.code,
        detail: error.detail,
        hint: error.hint,
        position: error.position,
        stack: error.stack
      });
      console.error('[Database] Strategy config being inserted:', {
        name: strategyConfig.name,
        hive_id: strategyConfig.hive_id,
        user_id: strategyConfig.user_id,
        strategy_type: strategyConfig.strategy_type,
        connector_type: strategyConfig.connector_type,
        trading_pairs: strategyConfig.trading_pairs
      });

      // If user_id column doesn't exist, try without it (graceful fallback)
      if (error.message && error.message.includes('user_id')) {
        console.log('[Database] Attempting fallback without user_id column');
        try {
          const fallbackQuery = `
            INSERT INTO hive_strategy_configs (
              name, hive_id, strategy_type, connector_type, trading_pairs,
              bid_spread, ask_spread, order_amount, order_levels, order_refresh_time,
              enabled, created_at, updated_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, NOW(), NOW())
            ON CONFLICT (name) DO UPDATE SET hive_id = EXCLUDED.hive_id, updated_at = NOW()
            RETURNING name;
          `;

          const fallbackResult = await client.query(fallbackQuery, [
            strategyConfig.name,
            strategyConfig.hive_id || null,
            strategyConfig.strategy_type || 'pure_market_making',
            strategyConfig.connector_type,
            JSON.stringify(strategyConfig.trading_pairs),
            strategyConfig.bid_spread || 0.05,
            strategyConfig.ask_spread || 0.05,
            strategyConfig.order_amount || 0.001,
            strategyConfig.order_levels || 1,
            strategyConfig.order_refresh_time || 5.0,
            strategyConfig.enabled !== false
          ]);

          console.log(`[Database] Fallback success: ${strategyConfig.name} created without user_id`);
          return { success: true, strategy_name: fallbackResult.rows[0].name };

        } catch (fallbackError) {
          console.error('[Database] Fallback also failed:', fallbackError);
        }
      }

      return {
        success: false,
        strategy_name: strategyConfig.name,
        error_details: {
          message: error.message,
          code: error.code,
          detail: error.detail,
          hint: error.hint,
          query_attempted: 'main_insert_with_user_id'
        }
      };
    } finally {
      if (client) {
        if ('release' in client) {
          (client as any).release();
        } else {
          await client.end();
        }
      }
    }
  }

  // Get strategy configurations from PostgreSQL
  async getStrategyConfigs(): Promise<any[]> {
    let client: Client | null = null;
    try {
      client = await this.createPostgreSQLClient();

      const query = `
        SELECT * FROM hive_strategy_configs
        WHERE enabled = true
        ORDER BY created_at DESC
      `;

      const result = await client.query(query);
      return result.rows;

    } catch (error) {
      console.error('[Database] Failed to get strategy configs:', error);
      return [];
    } finally {
      if (client) {
        if ('release' in client) {
          (client as any).release();
        } else {
          await client.end();
        }
      }
    }
  }

  // Update strategy performance metrics by aggregating from activities
  async updateStrategyMetricsFromActivities(): Promise<boolean> {
    let client: Client | null = null;
    try {
      client = await this.createPostgreSQLClient();

      // First, calculate metrics from activities for each strategy
      const metricsQuery = `
        WITH strategy_metrics AS (
          SELECT
            ha.strategy_name,
            hi.hive_id,
            COUNT(*) as total_actions,
            COUNT(*) FILTER (WHERE ha.success = true) as successful_orders,
            COUNT(*) FILTER (WHERE ha.success = false) as failed_orders,
            CASE
              WHEN EXTRACT(EPOCH FROM (NOW() - MIN(ha.timestamp)))/60 > 0
              THEN COUNT(*)::float / (EXTRACT(EPOCH FROM (NOW() - MIN(ha.timestamp)))/60)
              ELSE 0
            END as performance_per_min
          FROM hive_activities ha
          JOIN hive_instances hi ON ha.hive_id = hi.hive_id
          WHERE ha.timestamp >= NOW() - INTERVAL '24 hours'  -- Only count recent activities
          GROUP BY ha.strategy_name, hi.hive_id
        )
        UPDATE hive_strategies hs
        SET
          total_actions = sm.total_actions,
          successful_orders = sm.successful_orders,
          failed_orders = sm.failed_orders,
          performance_per_min = sm.performance_per_min,
          updated_at = NOW()
        FROM strategy_metrics sm
        WHERE hs.strategy_name = sm.strategy_name
          AND hs.hive_id = sm.hive_id
        RETURNING hs.strategy_name, hs.total_actions, hs.successful_orders;
      `;

      const result = await client.query(metricsQuery);

      console.log(`[Database] ✅ Updated metrics for ${result.rows.length} strategies from activities`);
      for (const row of result.rows) {
        console.log(`[Database]   ${row.strategy_name}: ${row.total_actions} actions, ${row.successful_orders} successful`);
      }

      return result.rows.length > 0;

    } catch (error) {
      console.error('[Database] Failed to update strategy metrics:', error);
      return false;
    } finally {
      if (client) {
        if ('release' in client) {
          (client as any).release();
        } else {
          await client.end();
        }
      }
    }
  }

  async recordStrategySnapshot(snapshot: {
    strategy_name: string;
    hive_id?: string | null;
    user_id?: string | null;
    total_actions: number;
    successful_actions: number;
    failed_actions: number;
    total_volume: number;
    avg_trade_size: number;
    buy_count: number;
    sell_count: number;
    last_activity?: Date | null;
    unrealized_pnl: number;
    realized_pnl: number;
    position_size: number;
    metadata?: Record<string, unknown>;
  }): Promise<void> {
    let client: Client | null = null;
    try {
      client = await this.createPostgreSQLClient();

      await client.query(
        `
          INSERT INTO hive_strategy_snapshots (
            strategy_name,
            hive_id,
            user_id,
            total_actions,
            successful_actions,
            failed_actions,
            total_volume,
            avg_trade_size,
            buy_count,
            sell_count,
            last_activity,
            unrealized_pnl,
            realized_pnl,
            position_size,
            metadata
          )
          VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
        `,
        [
          snapshot.strategy_name,
          snapshot.hive_id || null,
          snapshot.user_id || null,
          snapshot.total_actions,
          snapshot.successful_actions,
          snapshot.failed_actions,
          snapshot.total_volume,
          snapshot.avg_trade_size,
          snapshot.buy_count,
          snapshot.sell_count,
          snapshot.last_activity || null,
          snapshot.unrealized_pnl,
          snapshot.realized_pnl,
          snapshot.position_size,
          JSON.stringify(snapshot.metadata || {})
        ]
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
  }
}

// Export singleton database client
export const database = new DatabaseClient(dbConfig);

// Initialize database tables on startup
if (dbConfig.type === 'remote') {
  database.initializeActivityTables().catch(error => {
    console.error('Failed to initialize activity tables on startup:', error);
  });
}

// Helper function to check database connection
export async function testDatabaseConnection(): Promise<{connected: boolean, source: string}> {
  if (dbConfig.type === 'remote') {
    let client: Client | null = null;
    console.log(`[Database] Testing connection to ${dbConfig.postgresql?.host}:${dbConfig.postgresql?.port}/${dbConfig.postgresql?.database}`);
    try {
      console.log('[Database] Getting client from pool...');
      client = await database.getClient();
      console.log('[Database] Client acquired, executing test query...');
      const result = await client.query('SELECT version()');
      console.log('[Database] Test query successful:', result.rows[0]?.version?.substring(0, 50));
      return {
        connected: true,
        source: `PostgreSQL (${dbConfig.postgresql?.host}:${dbConfig.postgresql?.port})`
      };
    } catch (error) {
      console.error('[Database] PostgreSQL connection test failed:', error);
      return {
        connected: false,
        source: 'PostgreSQL connection failed',
        error: error instanceof Error ? error.message : String(error)
      };
    } finally {
      if (client) {
        // Use release() for pooled connections, not end()
        if ('release' in client) {
          client.release();
        } else {
          await client.end();
        }
      }
    }
  } else {
    return {
      connected: false,
      source: `Local SQLite (${dbConfig.localPath})`
    };
  }
}
