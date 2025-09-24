#!/bin/bash

# Start Hummingbot MCP Server with HTTP
# This script configures and starts the MCP server in HTTP mode

set -e

echo "🚀 Starting Hummingbot MCP Server with HTTP..."
echo "=============================================="

# Check if SSL certificates exist
SSL_DIR="./ssl"
CERT_FILE="$SSL_DIR/server.crt"
KEY_FILE="$SSL_DIR/server.key"

if [ ! -f "$CERT_FILE" ] || [ ! -f "$KEY_FILE" ]; then
    echo "❌ SSL certificates not found!"
    echo "📝 Generating SSL certificates first..."
    ./generate_ssl_certs.sh
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "📋 Creating .env file from .env.example..."
    cp .env.example .env
fi

# Update .env file with SSL configuration
echo "🔧 Configuring HTTP server settings..."

# Function to update or add environment variable
update_env_var() {
    local var_name="$1"
    local var_value="$2"
    local env_file=".env"
    
    if grep -q "^${var_name}=" "$env_file"; then
        # Variable exists, update it
        sed -i.bak "s|^${var_name}=.*|${var_name}=${var_value}|" "$env_file"
    else
        # Variable doesn't exist, add it
        echo "${var_name}=${var_value}" >> "$env_file"
    fi
}

# Configure HTTP server settings
update_env_var "SSL_ENABLED" "false"
update_env_var "MCP_TRANSPORT" "streamable-http"
update_env_var "MCP_HOST" "127.0.0.1"
update_env_var "MCP_PORT" "8002"

echo "✅ HTTP server configuration updated in .env file"
echo ""
echo "📋 Current Configuration:"
echo "   SSL_ENABLED=false"
echo "   MCP_TRANSPORT=streamable-http"
echo "   MCP_HOST=127.0.0.1"
echo "   MCP_PORT=8002"
echo ""
echo "ℹ️  HTTP Server Features:"
echo "   ✅ Fast HTTP transport"
echo "   ✅ No SSL overhead"
echo "   ✅ Perfect for development"
echo "   ✅ WebSocket support (WS)"
echo "   ✅ Simple debugging"
echo ""
echo "🌐 HTTP server will be available at: http://127.0.0.1:8002/mcp"
echo "🔒 For HTTPS, use: ./start_nginx_ssl.sh"
echo ""
echo "🚀 Starting HTTP MCP server..."
echo "==============================================="

# Start the server
python main_http.py