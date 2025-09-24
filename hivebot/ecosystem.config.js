module.exports = {
  apps: [{
    name: 'hive-orchestrator',
    script: 'start_hive.sh',
    interpreter: 'bash',
    cwd: '/home/ubuntu/hummingbot',
    instances: 1,
    exec_mode: 'fork',
    autorestart: true,
    watch: false,
    max_memory_restart: '1G',
    env: {
      CONDA_DEFAULT_ENV: 'hummingbot',
      PATH: '/home/ubuntu/miniconda3/bin:/home/ubuntu/miniconda3/envs/hummingbot/bin:' + process.env.PATH,
      HYPERLIQUID_PRIVATE_KEY: process.env.HYPERLIQUID_PRIVATE_KEY
    },
    log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
    out_file: './logs/hive-orchestrator-out.log',
    error_file: './logs/hive-orchestrator-error.log',
    merge_logs: true
  }]
};
