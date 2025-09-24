#!/bin/bash

# Ultra-fast Development Deploy
# Usage: ./dev-deploy.sh
# Only syncs src/ and restarts - for rapid development iterations

SERVER_IP="15.235.212.36"
SERVER_USER="ubuntu"

echo "🚀 Dev sync to $SERVER_IP..."

# Quick source code sync
rsync -avz --delete \
  --exclude='*.log' \
  --exclude='node_modules' \
  --exclude='.git' \
  src/ $SERVER_USER@$SERVER_IP:/var/www/hivebot-manager/src/

# Quick restart
ssh $SERVER_USER@$SERVER_IP "cd /var/www/hivebot-manager && pm2 reload hivebot-manager --silent"

echo "✅ Dev sync complete! http://$SERVER_IP:8091/dashboard"
