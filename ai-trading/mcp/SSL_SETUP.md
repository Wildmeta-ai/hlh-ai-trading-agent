# SSL Setup Guide for Hummingbot MCP Server

This guide explains how to set up and run the Hummingbot MCP Server with SSL/HTTPS support using nginx for SSL termination.

## Quick Start

### 1. Generate SSL Certificates

```bash
# Generate self-signed certificates for development
./generate_ssl_certs.sh
```

### 2. Start Nginx SSL Server

#### Option A: Automated Setup (Recommended)

```bash
# Start server with nginx SSL termination
./start_nginx_ssl.sh
```

#### Option B: Manual Setup (Step-by-Step)

If the automated script fails, follow these detailed steps:

**Step 1: Start HTTP MCP Server**
```bash
# Start the backend HTTP server
python main_http.py &
```

**Step 2: Verify HTTP Server**
```bash
# Test if HTTP server is running
curl -s http://127.0.0.1:8002/ | head -3
```

**Step 3: Start Nginx with SSL**
```bash
# Start nginx with SSL configuration
sudo nginx -c $(pwd)/nginx_ssl.conf
```

**Step 4: Test HTTPS Connection**
```bash
# Test HTTPS endpoint (ignore self-signed cert warnings)
curl -k https://127.0.0.1:8443/mcp
```

The server will be available at: `https://127.0.0.1:8443/mcp`

## Manual Setup

### 1. Generate SSL Certificates

For development, you can use self-signed certificates:

```bash
# Create SSL directory
mkdir -p ssl

# Generate private key
openssl genrsa -out ssl/server.key 2048

# Generate certificate signing request
openssl req -new -key ssl/server.key -out ssl/server.csr \
  -subj "/C=US/ST=California/L=San Francisco/O=Hummingbot MCP/OU=Development/CN=localhost/emailAddress=admin@localhost"

# Generate self-signed certificate (valid for 365 days)
openssl x509 -req -days 365 -in ssl/server.csr -signkey ssl/server.key -out ssl/server.crt

# Clean up
rm ssl/server.csr
```

### 2. Configure Environment

Copy the example environment file and configure SSL:

```bash
cp .env.example .env
```

Edit `.env` file:

```bash
# Enable SSL
SSL_ENABLED=true

# Certificate paths (use absolute paths)
SSL_CERT_FILE=/path/to/your/ssl/server.crt
SSL_KEY_FILE=/path/to/your/ssl/server.key
SSL_CA_FILE=/path/to/your/ssl/ca_bundle.pem  # Optional

# Server configuration
MCP_TRANSPORT=streamable-http
MCP_HOST=127.0.0.1
MCP_PORT=8002
```

### 3. Start the Nginx SSL Server

```bash
# Start with nginx SSL termination
./start_nginx_ssl.sh
```

## SSL Configuration Options

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `SSL_ENABLED` | Enable/disable SSL | `false` | No |
| `SSL_CERT_FILE` | Path to SSL certificate file | `""` | Yes (if SSL enabled) |
| `SSL_KEY_FILE` | Path to SSL private key file | `""` | Yes (if SSL enabled) |
| `SSL_CA_FILE` | Path to CA bundle file | `""` | No |
| `MCP_HOST` | Server host address | `127.0.0.1` | No |
| `MCP_PORT` | Server port | `8002` | No |
| `MCP_TRANSPORT` | Transport type | `stdio` | No |

### Certificate Requirements

- **Certificate file**: Must be in PEM format
- **Private key**: Must be in PEM format, unencrypted
- **CA file**: Optional, for client certificate verification

## Production Deployment

For production use, obtain certificates from a trusted Certificate Authority (CA):

### Let's Encrypt (Recommended)

```bash
# Install certbot
sudo apt-get install certbot  # Ubuntu/Debian
brew install certbot          # macOS

# Generate certificate
sudo certbot certonly --standalone -d your-domain.com

# Update .env file
SSL_CERT_FILE=/etc/letsencrypt/live/your-domain.com/fullchain.pem
SSL_KEY_FILE=/etc/letsencrypt/live/your-domain.com/privkey.pem
```

### Commercial CA

1. Purchase SSL certificate from a trusted CA
2. Generate CSR and submit to CA
3. Download issued certificate and intermediate certificates
4. Configure paths in `.env` file

## Testing SSL Connection

### Test with curl

```bash
# Test HTTPS connection (ignore self-signed certificate warnings)
curl -k https://127.0.0.1:8002/mcp

# Test with certificate verification (for production)
curl https://your-domain.com:8002/mcp
```

### Test with Claude MCP Client

```json
{
  "mcpServers": {
    "hummingbot": {
      "type": "streamable-http",
      "url": "https://127.0.0.1:8443/mcp"
    }
  }
}
```

## Troubleshooting

### Common Issues

1. **Certificate not found**
   ```
   SSL enabled but cert/key files not specified. Running without SSL.
   ```
   - **Solution:** Check `SSL_CERT_FILE` and `SSL_KEY_FILE` paths
   - **Fix:** Run `./generate_ssl_certs.sh` to create certificates

2. **Permission denied**
   ```
   Failed to create SSL context: [Errno 13] Permission denied
   ```
   - **Solution:** Check file permissions for certificate files
   - **Fix:** `chmod 600 ssl/server.key && chmod 644 ssl/server.crt`

3. **Invalid certificate format**
   ```
   Failed to create SSL context: PEM lib
   ```
   - **Solution:** Ensure certificates are in PEM format
   - **Fix:** Regenerate certificates with `./generate_ssl_certs.sh`

4. **Port already in use**
   ```
   [Errno 48] Address already in use
   ```
   - **Solution:** Kill existing processes and restart
   - **Fix:** `lsof -ti:8002 | xargs kill -9 && lsof -ti:8443 | xargs kill -9`

5. **Nginx configuration errors**
   ```
   nginx: [emerg] "server" directive is not allowed here
   ```
   - **Solution:** Ensure nginx.conf has proper structure with `http {}` block
   - **Fix:** Use the provided `nginx_ssl.conf` file

6. **SSL directive errors**
   ```
   nginx: [emerg] unknown directive "ssl_private_key"
   ```
   - **Solution:** Use correct nginx SSL directives
   - **Fix:** Use `ssl_certificate_key` instead of `ssl_private_key`

7. **Mime types not found**
   ```
   nginx: [emerg] open() "/etc/nginx/mime.types" failed
   ```
   - **Solution:** Update path for your system
   - **macOS Fix:** Use `/opt/homebrew/etc/nginx/mime.types`
   - **Linux Fix:** Use `/etc/nginx/mime.types`

8. **MCP server connection issues**
   ```
   Cannot connect to host localhost:8000
   ```
   - **Note:** This is normal - Hummingbot API warnings don't affect MCP functionality
   - **MCP server will still work** for client connections

### Verify Certificate

```bash
# Check certificate details
openssl x509 -in ssl/server.crt -text -noout

# Verify certificate and key match
openssl x509 -noout -modulus -in ssl/server.crt | openssl md5
openssl rsa -noout -modulus -in ssl/server.key | openssl md5
```

### Debug SSL Issues

```bash
# Test SSL connection with detailed output
openssl s_client -connect 127.0.0.1:8443 -servername localhost

# Test HTTPS with verbose curl
curl -k -v https://127.0.0.1:8443/ 2>&1 | head -20

# Check nginx status
sudo nginx -t -c $(pwd)/nginx_ssl.conf

# View nginx error logs
tail -f /opt/homebrew/var/log/nginx/error.log  # macOS
tail -f /var/log/nginx/error.log              # Linux
```

### Step-by-Step Debugging

1. **Check if certificates exist:**
   ```bash
   ls -la ssl/
   ```

2. **Verify nginx is installed:**
   ```bash
   which nginx
   nginx -v
   ```

3. **Test nginx configuration:**
   ```bash
   sudo nginx -t -c $(pwd)/nginx_ssl.conf
   ```

4. **Check port availability:**
   ```bash
   lsof -i :8002  # MCP server port
   lsof -i :8443  # HTTPS port
   lsof -i :8081  # HTTP redirect port
   ```

5. **Start services manually:**
   ```bash
   # Terminal 1: Start MCP server
   python main_http.py
   
   # Terminal 2: Start nginx
   sudo nginx -c $(pwd)/nginx_ssl.conf
   ```

6. **Test each component:**
   ```bash
   # Test HTTP backend
   curl http://127.0.0.1:8002/
   
   # Test HTTPS frontend
   curl -k https://127.0.0.1:8443/
   
   # Test MCP endpoint
   curl -k https://127.0.0.1:8443/mcp
   ```

## Security Considerations

1. **Self-signed certificates**: Only use for development
2. **Private key protection**: Secure file permissions (600)
3. **Certificate expiration**: Monitor and renew certificates
4. **Strong ciphers**: Use modern TLS versions (1.2+)
5. **Firewall**: Restrict access to necessary ports only

## File Structure

```
mcp/
├── ssl/
│   ├── server.crt          # SSL certificate
│   └── server.key          # Private key
├── .env                    # Environment configuration
├── .env.example           # Example configuration
├── generate_ssl_certs.sh  # Certificate generation script
├── start_nginx_ssl.sh     # Nginx SSL startup script
├── start_http_server.sh   # HTTP server startup script
├── nginx_ssl.conf         # Nginx SSL configuration
└── main_http.py           # HTTP server entry point
```

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Verify your SSL configuration
3. Check server logs for detailed error messages
4. Ensure all dependencies are installed