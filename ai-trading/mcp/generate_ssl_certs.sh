#!/bin/bash

# SSL Certificate Generation Script for Hummingbot MCP Server
# This script generates self-signed SSL certificates for development use

set -e

echo "🔐 Generating SSL certificates for Hummingbot MCP Server..."
echo "================================================"

# Create ssl directory if it doesn't exist
SSL_DIR="./ssl"
mkdir -p "$SSL_DIR"

# Certificate configuration
COUNTRY="US"
STATE="California"
CITY="San Francisco"
ORGANIZATION="Hummingbot MCP"
ORGANIZATIONAL_UNIT="Development"
COMMON_NAME="localhost"
EMAIL="admin@localhost"

# Certificate files
PRIVATE_KEY="$SSL_DIR/server.key"
CERTIFICATE="$SSL_DIR/server.crt"
CSR_FILE="$SSL_DIR/server.csr"

echo "📁 Creating SSL directory: $SSL_DIR"
echo "🔑 Generating private key..."

# Generate private key
openssl genrsa -out "$PRIVATE_KEY" 2048

echo "📝 Creating certificate signing request..."

# Create certificate signing request
openssl req -new -key "$PRIVATE_KEY" -out "$CSR_FILE" -subj "/C=$COUNTRY/ST=$STATE/L=$CITY/O=$ORGANIZATION/OU=$ORGANIZATIONAL_UNIT/CN=$COMMON_NAME/emailAddress=$EMAIL"

echo "📜 Generating self-signed certificate..."

# Generate self-signed certificate (valid for 365 days)
openssl x509 -req -days 365 -in "$CSR_FILE" -signkey "$PRIVATE_KEY" -out "$CERTIFICATE"

# Clean up CSR file
rm "$CSR_FILE"

echo "✅ SSL certificates generated successfully!"
echo "================================================"
echo "📁 Certificate files created:"
echo "   Private Key: $PRIVATE_KEY"
echo "   Certificate: $CERTIFICATE"
echo ""
echo "🔧 To use these certificates:"
echo "   1. Copy .env.example to .env"
echo "   2. Edit .env and set:"
echo "      SSL_ENABLED=true"
echo "      SSL_CERT_FILE=$(pwd)/$CERTIFICATE"
echo "      SSL_KEY_FILE=$(pwd)/$PRIVATE_KEY"
echo ""
echo "⚠️  Note: These are self-signed certificates for development only."
echo "   For production, use certificates from a trusted CA."
echo ""
echo "🚀 Ready to start MCP server with SSL!"