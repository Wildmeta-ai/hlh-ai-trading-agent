module.exports = {
  apps: [{
    name: 'hivebot-manager',
    script: 'npm',
    args: 'run dev',
    cwd: '/home/ubuntu/hummingbot/hivebot-manager',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '500M',
    env: {
      NODE_ENV: 'development',
      PORT: 3003
    },
    log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
    out_file: '/var/log/hivebot-manager/out.log',
    error_file: '/var/log/hivebot-manager/error.log',
    merge_logs: true
  }]
};
