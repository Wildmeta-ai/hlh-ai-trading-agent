#!/bin/bash

# Start Hummingbot MCP Server with Nginx SSL Termination
# This script starts the HTTP MCP server and configures nginx for SSL

set -e

echo "🔒 Starting Hummingbot MCP Server with Nginx SSL..."
echo "================================================"

# Check if SSL certificates exist
SSL_DIR="./ssl"
CERT_FILE="$SSL_DIR/server.crt"
KEY_FILE="$SSL_DIR/server.key"

if [ ! -f "$CERT_FILE" ] || [ ! -f "$KEY_FILE" ]; then
    echo "❌ SSL certificates not found!"
    echo "📝 Generating SSL certificates first..."
    ./generate_ssl_certs.sh
fi

# Check if nginx is installed
if ! command -v nginx &> /dev/null; then
    echo "❌ Nginx is not installed!"
    echo "📦 Please install nginx:"
    echo "   macOS: brew install nginx"
    echo "   Ubuntu: sudo apt install nginx"
    echo "   CentOS: sudo yum install nginx"
    exit 1
fi

# Update nginx configuration with correct certificate paths
echo "🔧 Updating nginx SSL configuration..."
sed -i.bak "s|ssl_certificate .*|ssl_certificate $(pwd)/$CERT_FILE;|" nginx_ssl.conf
sed -i.bak "s|ssl_private_key .*|ssl_private_key $(pwd)/$KEY_FILE;|" nginx_ssl.conf

echo "✅ Nginx SSL configuration updated"
echo ""
echo "📋 SSL Configuration:"
echo "   Certificate: $(pwd)/$CERT_FILE"
echo "   Private Key: $(pwd)/$KEY_FILE"
echo "   Nginx Config: $(pwd)/nginx_ssl.conf"
echo ""
echo "🌐 URLs:"
echo "   HTTP (redirect): http://127.0.0.1:8080 → https://127.0.0.1:8443"
echo "   HTTPS (SSL): https://127.0.0.1:8443/mcp"
echo "   Health Check: https://127.0.0.1:8443/health"
echo ""
echo "🚀 Starting services..."
echo "================================================"

# Start HTTP MCP server in background
echo "📡 Starting HTTP MCP server on port 8002..."
./start_http_server.sh &
MCP_PID=$!

# Wait for MCP server to start
echo "⏳ Waiting for MCP server to start..."
sleep 3

# Check if MCP server is running
if ! curl -s http://127.0.0.1:8002/ > /dev/null; then
    echo "❌ MCP server failed to start!"
    kill $MCP_PID 2>/dev/null || true
    exit 1
fi

echo "✅ MCP server started successfully"

# Start nginx with SSL configuration
echo "🔒 Starting nginx with SSL configuration..."
sudo nginx -c "$(pwd)/nginx_ssl.conf" -t
if [ $? -eq 0 ]; then
    sudo nginx -c "$(pwd)/nginx_ssl.conf"
    echo "✅ Nginx started with SSL termination"
else
    echo "❌ Nginx configuration test failed!"
    kill $MCP_PID 2>/dev/null || true
    exit 1
fi

echo ""
echo "🎉 Setup complete!"
echo "================================================"
echo "🔗 Access your secure MCP server at:"
echo "   https://127.0.0.1:8443/mcp"
echo ""
echo "📊 Service Status:"
echo "   MCP Server (HTTP): http://127.0.0.1:8002 (backend)"
echo "   Nginx (HTTPS): https://127.0.0.1:8443 (frontend)"
echo ""
echo "🛑 To stop services:"
echo "   sudo nginx -s stop"
echo "   kill $MCP_PID"
echo ""
echo "📝 Logs:"
echo "   Nginx: /usr/local/var/log/nginx/ (macOS) or /var/log/nginx/ (Linux)"
echo "   MCP: Check terminal output"

# Keep script running to monitor services
echo "🔍 Monitoring services (Ctrl+C to stop)..."
trap 'echo "\n🛑 Stopping services..."; sudo nginx -s stop 2>/dev/null || true; kill $MCP_PID 2>/dev/null || true; echo "✅ Services stopped"; exit 0' INT

while true; do
    sleep 10
    if ! kill -0 $MCP_PID 2>/dev/null; then
        echo "❌ MCP server stopped unexpectedly!"
        sudo nginx -s stop 2>/dev/null || true
        exit 1
    fi
done