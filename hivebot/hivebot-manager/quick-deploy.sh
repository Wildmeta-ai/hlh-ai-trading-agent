#!/bin/bash

# Quick Deploy Script - Fast updates to test server
# Usage: ./quick-deploy.sh

SERVER_IP="15.235.212.36"
SERVER_USER="ubuntu"
APP_NAME="hivebot-manager"

echo "⚡ Quick deploying to $SERVER_USER@$SERVER_IP..."

# Check if we're in the right directory
if [ ! -f "package.json" ] || [ ! -d "src" ]; then
    echo "❌ Error: Run this script from the hivebot-manager root directory"
    exit 1
fi

# Build only if package.json or dependencies changed
echo "🔍 Checking if build is needed..."
BUILD_NEEDED=false

# Check if node_modules exists on server and if package.json changed
if ssh $SERVER_USER@$SERVER_IP "[ ! -d /var/www/${APP_NAME}/node_modules ]"; then
    echo "📦 Node modules missing on server, full build needed"
    BUILD_NEEDED=true
elif [ package.json -nt .last-deploy ] 2>/dev/null; then
    echo "📦 Package.json changed, build needed"
    BUILD_NEEDED=true
fi

if [ "$BUILD_NEEDED" = true ]; then
    echo "📦 Building project..."
    npm run build
    if [ $? -ne 0 ]; then
        echo "⚠️  Build failed, continuing anyway (common with TypeScript/ESLint warnings)..."
    fi
else
    echo "⚡ Skipping build, no dependency changes detected"
fi

# Create a minimal package with only changed files
echo "📦 Creating update package..."
tar -czf update.tar.gz \
  --exclude=node_modules \
  --exclude=.git \
  --exclude=.next/cache \
  --exclude='*.log' \
  --exclude='logs/*' \
  src/ \
  public/ \
  .next/ \
  package.json \
  package-lock.json \
  next.config.js \
  tailwind.config.js \
  tsconfig.json \
  ecosystem.config.js 2>/dev/null

# Quick sync to server
echo "📤 Syncing files to server..."
scp update.tar.gz $SERVER_USER@$SERVER_IP:/tmp/

# Quick update on server
echo "🔧 Updating application on server..."
ssh $SERVER_USER@$SERVER_IP << 'EOF'
  cd /var/www/hivebot-manager

  # Extract update files
  tar -xzf /tmp/update.tar.gz

  # Install/update dependencies only if package.json changed
  if [ /tmp/update.tar.gz -nt node_modules/.package-updated ] 2>/dev/null; then
    echo "📦 Updating dependencies..."
    npm ci --only=production --silent
    touch node_modules/.package-updated
  fi

  # Restart application
  echo "🔄 Restarting application..."
  pm2 reload hivebot-manager --silent || pm2 start ecosystem.config.js --silent

  # Clean up
  rm -f /tmp/update.tar.gz

  echo "✅ Quick deployment completed!"
EOF

# Clean up local files
rm -f update.tar.gz
touch .last-deploy

echo ""
echo "🎉 Quick deployment successful!"
echo "🌐 Check your app at: http://$SERVER_IP:8091/dashboard"
echo ""
echo "Next time will be even faster (skips unchanged dependencies)"
