#!/bin/bash

# Hivebot Manager Deployment Script
# Usage: ./deploy.sh [server_ip] [server_user]

SERVER_IP=${1:-"15.235.212.36"}
SERVER_USER=${2:-"ubuntu"}
APP_NAME="hivebot-manager"
APP_PORT=3002
NGINX_PORT=8091

echo "🚀 Starting deployment to $SERVER_USER@$SERVER_IP"

# Build the project locally
echo "📦 Building project locally..."
npm run build

# Create deployment package
echo "📦 Creating deployment package..."
tar -czf ${APP_NAME}.tar.gz \
  --exclude=node_modules \
  --exclude=.git \
  --exclude=.next/cache \
  --exclude=deploy.sh \
  .

# Copy files to server
echo "📤 Copying files to server..."
scp ${APP_NAME}.tar.gz $SERVER_USER@$SERVER_IP:/tmp/
scp ecosystem.config.js $SERVER_USER@$SERVER_IP:/tmp/

# Deploy on server
echo "🔧 Setting up on server..."
ssh $SERVER_USER@$SERVER_IP << EOF
  # Update system
  sudo apt update

  # Install Node.js 20 and PM2 if not already installed
  if ! command -v node &> /dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y nodejs
  fi

  if ! command -v pm2 &> /dev/null; then
    sudo npm install -g pm2
  fi

  # Install nginx if not already installed
  if ! command -v nginx &> /dev/null; then
    sudo apt install -y nginx
  fi

  # Create application directory
  sudo mkdir -p /var/www/${APP_NAME}
  sudo mkdir -p /var/log/${APP_NAME}

  # Set ownership
  sudo chown -R $SERVER_USER:$SERVER_USER /var/www/${APP_NAME}
  sudo chown -R $SERVER_USER:$SERVER_USER /var/log/${APP_NAME}

  # Extract application
  cd /var/www/${APP_NAME}
  tar -xzf /tmp/${APP_NAME}.tar.gz

  # Install dependencies
  echo "📦 Installing dependencies on server..."
  npm ci --only=production

  # Copy PM2 config
  cp /tmp/ecosystem.config.js .

  # Stop existing PM2 process if running
  pm2 stop ${APP_NAME} 2>/dev/null || true
  pm2 delete ${APP_NAME} 2>/dev/null || true

  # Start application with PM2
  echo "🚀 Starting application with PM2..."
  pm2 start ecosystem.config.js
  pm2 save

  # Create nginx configuration
  echo "🌐 Setting up nginx..."
  sudo tee /etc/nginx/sites-available/${APP_NAME} > /dev/null << NGINX_EOF
server {
    listen ${NGINX_PORT};
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:${APP_PORT};
        proxy_http_version 1.1;
        proxy_set_header Upgrade \\\$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \\\$host;
        proxy_set_header X-Real-IP \\\$remote_addr;
        proxy_set_header X-Forwarded-For \\\$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \\\$scheme;
        proxy_cache_bypass \\\$http_upgrade;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # API routes with longer timeout
    location /api/ {
        proxy_pass http://127.0.0.1:${APP_PORT};
        proxy_http_version 1.1;
        proxy_set_header Upgrade \\\$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \\\$host;
        proxy_set_header X-Real-IP \\\$remote_addr;
        proxy_set_header X-Forwarded-For \\\$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \\\$scheme;
        proxy_cache_bypass \\\$http_upgrade;
        proxy_read_timeout 600s;
        proxy_connect_timeout 75s;
    }
}
NGINX_EOF

  # Enable nginx site
  sudo ln -sf /etc/nginx/sites-available/${APP_NAME} /etc/nginx/sites-enabled/
  sudo rm -f /etc/nginx/sites-enabled/default

  # Test nginx configuration
  sudo nginx -t

  # Restart nginx
  sudo systemctl restart nginx
  sudo systemctl enable nginx

  # Setup PM2 startup
  pm2 startup systemd -u $SERVER_USER --hp /home/$SERVER_USER

  # Clean up
  rm -f /tmp/${APP_NAME}.tar.gz /tmp/ecosystem.config.js

  echo "✅ Deployment completed successfully!"
  echo "🌐 Application available at: http://$SERVER_IP"
  echo "📊 PM2 status:"
  pm2 status

EOF

# Clean up local files
rm -f ${APP_NAME}.tar.gz

echo "✅ Deployment script completed!"
echo "🌐 Your Hivebot Manager should be available at: http://$SERVER_IP"
echo ""
echo "Useful commands on server:"
echo "  pm2 status              - Check application status"
echo "  pm2 logs ${APP_NAME}    - View application logs"
echo "  pm2 restart ${APP_NAME} - Restart application"
echo "  sudo nginx -t           - Test nginx configuration"
echo "  sudo systemctl status nginx - Check nginx status"
