#!/bin/bash

# Hivebot Manager - View Development Logs
# Usage: ./dev-logs.sh [lines]

APP_NAME="hivebot-manager-dev"
LINES=${1:-50}

echo "📋 Viewing last $LINES lines of development logs..."
echo "Press Ctrl+C to exit live log streaming"
echo ""

# Show recent logs and then follow
pm2 logs $APP_NAME --lines $LINES
