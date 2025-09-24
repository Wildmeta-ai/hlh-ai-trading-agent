module.exports = {
  apps: [{
    name: 'hive-orchestrator-2',
    script: 'hive_instance2_launcher.py',
    interpreter: '/Users/yoshiyuki/miniconda3/envs/hummingbot/bin/python',
    cwd: '/Users/yoshiyuki/hummingbot',
    args: '--trading --port 8082',
    env: {
      NODE_ENV: 'production',
      PYTHONUNBUFFERED: '1',
      CONFIG_PASSWORD: 'test_password',
      HIVE_PORT: '8082',
      HIVE_DB_FILE: 'hive_strategies_instance2.db',
      HIVE_INSTANCE: '2',
      HIVE_STRATEGIES: '0'  // Start with 0 strategies
    },
    max_memory_restart: '2G',
    error_file: './logs/hive-orchestrator-2-error.log',
    out_file: './logs/hive-orchestrator-2-out.log',
    log_date_format: 'YYYY-MM-DD HH:mm:ss',
    merge_logs: true,
    autorestart: true,
    watch: false,
    instance_var: 'INSTANCE_ID'
  }]
}
