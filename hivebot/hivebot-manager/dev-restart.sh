#!/bin/bash

# Hivebot Manager - Restart Local Development Server
# Usage: ./dev-restart.sh

APP_NAME="hivebot-manager-dev"

echo "🔄 Restarting Hivebot Manager - Local Development"

# Restart the PM2 process
pm2 restart $APP_NAME

echo "✅ Development server restarted!"
echo ""
echo "📊 Application Status:"
pm2 status $APP_NAME

echo ""
echo "🌐 Application available at: http://localhost:3000"
