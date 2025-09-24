#!/bin/bash

# Hivebot Manager - Local Development Startup Script
# Usage: ./dev-start.sh

APP_NAME="hivebot-manager-dev"
APP_PORT=3000

echo "🐝 Starting Hivebot Manager - Local Development"

# Check if PM2 is installed
if ! command -v pm2 &> /dev/null; then
    echo "❌ PM2 not found. Installing PM2 globally..."
    npm install -g pm2
fi

# Stop existing dev instance if running
echo "🛑 Stopping existing dev instance (if any)..."
pm2 stop $APP_NAME 2>/dev/null || true
pm2 delete $APP_NAME 2>/dev/null || true

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Start the development server with PM2
echo "🚀 Starting development server with PM2..."
pm2 start ecosystem.dev.config.js

# Save PM2 process list
pm2 save

echo "✅ Development server started successfully!"
echo ""
echo "📊 Application Status:"
pm2 status $APP_NAME

echo ""
echo "🌐 Local Application URLs:"
echo "  - Frontend: http://localhost:$APP_PORT"
echo "  - Dashboard: http://localhost:$APP_PORT/dashboard"
echo "  - API: http://localhost:$APP_PORT/api/bots"
echo ""
echo "📋 Useful PM2 Commands:"
echo "  pm2 status                    - Check application status"
echo "  pm2 logs $APP_NAME           - View live logs"
echo "  pm2 restart $APP_NAME        - Restart application"
echo "  pm2 stop $APP_NAME           - Stop application"
echo "  pm2 delete $APP_NAME         - Remove from PM2"
echo "  pm2 monit                     - Real-time monitoring dashboard"
echo ""
echo "🔧 Development Commands:"
echo "  ./dev-stop.sh                 - Stop development server"
echo "  ./dev-restart.sh              - Restart development server"
echo "  ./dev-logs.sh                 - View logs"
