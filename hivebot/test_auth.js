#!/usr/bin/env node

// Test script to verify authentication with the API
// Run with: node test_auth.js <wallet_address> <signature> <base64_message>

const https = require('https');
const http = require('http');

function testAuthentication(walletAddress, signature, messageBase64, apiUrl = 'https://copilot.wildmeta.ai/botapi/strategies') {
    return new Promise((resolve, reject) => {
        const url = new URL(apiUrl);
        const isHttps = url.protocol === 'https:';
        const client = isHttps ? https : http;

        const options = {
            hostname: url.hostname,
            port: url.port || (isHttps ? 443 : 80),
            path: url.pathname,
            method: 'GET',
            headers: {
                'Accept': '*/*',
                'User-Agent': 'Node.js Auth Test',
                'X-Auth-Message': messageBase64,
                'X-Auth-Signature': signature,
                'X-Wallet-Address': walletAddress
            }
        };

        const req = client.request(options, (res) => {
            let data = '';
            res.on('data', (chunk) => {
                data += chunk;
            });

            res.on('end', () => {
                resolve({
                    statusCode: res.statusCode,
                    headers: res.headers,
                    body: data
                });
            });
        });

        req.on('error', (error) => {
            reject(error);
        });

        req.setTimeout(10000, () => {
            req.destroy();
            reject(new Error('Request timeout'));
        });

        req.end();
    });
}

// Main execution
const args = process.argv.slice(2);
if (args.length < 3) {
    console.error('Usage: node test_auth.js <wallet_address> <signature> <base64_message> [api_url]');
    console.error('');
    console.error('Example:');
    console.error('  node test_auth.js 0x208... 0xabc... UGxlYXNl...');
    process.exit(1);
}

const [walletAddress, signature, messageBase64, apiUrl] = args;

console.log('=== AUTHENTICATION TEST ===');
console.log('Wallet:', walletAddress);
console.log('API URL:', apiUrl || 'https://copilot.wildmeta.ai/botapi/strategies');
console.log('');
console.log('Testing authentication...');

testAuthentication(walletAddress, signature, messageBase64, apiUrl)
    .then(response => {
        console.log('');
        console.log('RESPONSE:');
        console.log('Status Code:', response.statusCode);
        console.log('');

        if (response.statusCode === 200) {
            console.log('✅ SUCCESS: Authentication passed!');
            console.log('Response body:');
            try {
                const parsed = JSON.parse(response.body);
                console.log(JSON.stringify(parsed, null, 2));
            } catch (e) {
                console.log(response.body);
            }
        } else if (response.statusCode === 401) {
            console.log('❌ FAILED: Authentication failed (401 Unauthorized)');
            console.log('Response body:', response.body);

            if (response.body.includes('timestamp') || response.body.includes('time')) {
                console.log('');
                console.log('💡 Likely cause: Timestamp expired (>5 minutes old)');
                console.log('   Generate a fresh signature with: node generate_auth.js <wallet>');
            }
        } else {
            console.log(`⚠️  Unexpected status: ${response.statusCode}`);
            console.log('Response body:', response.body);
        }
    })
    .catch(error => {
        console.error('');
        console.error('❌ REQUEST FAILED:', error.message);
    });