#!/bin/bash

# Hivebot Manager - Stop Local Development Server
# Usage: ./dev-stop.sh

APP_NAME="hivebot-manager-dev"

echo "🛑 Stopping Hivebot Manager - Local Development"

# Stop the PM2 process
pm2 stop $APP_NAME

echo "✅ Development server stopped!"
echo ""
echo "📊 Current PM2 Status:"
pm2 status
