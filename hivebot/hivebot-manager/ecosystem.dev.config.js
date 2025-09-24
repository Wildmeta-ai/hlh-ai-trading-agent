module.exports = {
  apps: [{
    name: 'hivebot-manager-dev',
    script: 'npm',
    args: 'run dev',
    cwd: '/Users/yoshiyuki/hummingbot/hivebot-manager',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '500M',
    env: {
      NODE_ENV: 'development',
      PORT: 3000
    },
    log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
    out_file: './logs/dev-out.log',
    error_file: './logs/dev-error.log',
    merge_logs: true,
    // Development specific settings
    min_uptime: '2s',
    max_restarts: 10
  }]
};
