#!/usr/bin/env node

// Script to generate fresh authentication headers for the API
// Run with: node generate_auth.js <wallet_address>

const crypto = require('crypto');

function generateAuthMessage(walletAddress) {
    const timestamp = Date.now();
    const message = `Please sign this message to authenticate with AI Trading Bot.

Wallet: ${walletAddress}
Timestamp: ${timestamp}

This signature will be used for API authentication.`;

    return {
        message,
        timestamp,
        messageBase64: Buffer.from(message).toString('base64')
    };
}

function generateCurlCommand(walletAddress, messageBase64, signature) {
    return `curl 'https://copilot.wildmeta.ai/botapi/strategies' \\
  -H 'Accept: */*' \\
  -H 'Accept-Language: zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7' \\
  -H 'Connection: keep-alive' \\
  -H 'DNT: 1' \\
  -H 'Origin: http://localhost:3000' \\
  -H 'Referer: http://localhost:3000/' \\
  -H 'Sec-Fetch-Dest: empty' \\
  -H 'Sec-Fetch-Mode: cors' \\
  -H 'Sec-Fetch-Site: cross-site' \\
  -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36' \\
  -H 'X-Auth-Message: ${messageBase64}' \\
  -H 'X-Auth-Signature: ${signature}' \\
  -H 'X-Wallet-Address: ${walletAddress}' \\
  -H 'sec-ch-ua: "Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"' \\
  -H 'sec-ch-ua-mobile: ?0' \\
  -H 'sec-ch-ua-platform: "macOS"'`;
}

// Main execution
const args = process.argv.slice(2);
if (args.length < 1) {
    console.error('Usage: node generate_auth.js <wallet_address> [signature]');
    console.error('');
    console.error('Example:');
    console.error('  node generate_auth.js 0x208cbd782d8cfd050f796492a2c64f3a86d11815');
    console.error('');
    console.error('This will generate a message for you to sign. After signing:');
    console.error('  node generate_auth.js 0x208cbd782d8cfd050f796492a2c64f3a86d11815 0x<your_signature>');
    process.exit(1);
}

const walletAddress = args[0];
const signature = args[1];

// Validate wallet address format
if (!walletAddress.startsWith('0x') || walletAddress.length !== 42) {
    console.error('Error: Invalid wallet address format. Must be 0x followed by 40 hex characters.');
    process.exit(1);
}

const authData = generateAuthMessage(walletAddress);

console.log('=== AUTHENTICATION MESSAGE GENERATOR ===');
console.log('');
console.log('Wallet Address:', walletAddress);
console.log('Timestamp:', authData.timestamp);
console.log('');
console.log('MESSAGE TO SIGN:');
console.log('---');
console.log(authData.message);
console.log('---');
console.log('');
console.log('BASE64 ENCODED MESSAGE:');
console.log(authData.messageBase64);
console.log('');

if (!signature) {
    console.log('NEXT STEPS:');
    console.log('1. Copy the message above');
    console.log('2. Use your wallet (MetaMask, etc.) to sign this message with personal_sign');
    console.log('3. Run this script again with the signature:');
    console.log(`   node generate_auth.js ${walletAddress} 0x<your_signature>`);
    console.log('');
    console.log('Note: You have 5 minutes from now to use the signature before it expires.');
} else {
    // Validate signature format
    if (!signature.startsWith('0x') || signature.length !== 132) {
        console.error('Error: Invalid signature format. Must be 0x followed by 130 hex characters.');
        process.exit(1);
    }

    console.log('SIGNATURE:', signature);
    console.log('');
    console.log('READY TO USE CURL COMMAND:');
    console.log('');
    console.log(generateCurlCommand(walletAddress, authData.messageBase64, signature));
    console.log('');
    console.log('Headers for other tools:');
    console.log(`X-Auth-Message: ${authData.messageBase64}`);
    console.log(`X-Auth-Signature: ${signature}`);
    console.log(`X-Wallet-Address: ${walletAddress}`);
    console.log('');
    console.log('⚠️  Remember: This signature expires in 5 minutes from generation time!');
}