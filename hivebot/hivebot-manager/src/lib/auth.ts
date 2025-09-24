// Authentication utilities for simple personal_sign verification
// Verifies x-auth-signature, x-auth-message, and x-wallet-address headers

import { NextRequest } from 'next/server';
import { verifyMessage } from 'ethers';

export interface AuthHeaders {
  signature: string;
  message: string;  // Base64 encoded message
  walletAddress: string;
}

export interface AuthResult {
  isValid: boolean;
  walletAddress?: string;
  error?: string;
}

/**
 * Extract authentication headers from request
 */
export function extractAuthHeaders(request: NextRequest): AuthHeaders | null {
  const signature = request.headers.get('x-auth-signature');
  const messageBase64 = request.headers.get('x-auth-message');
  const walletAddress = request.headers.get('x-wallet-address');

  if (!signature || !messageBase64 || !walletAddress) {
    return null;
  }

  return {
    signature,
    message: messageBase64,
    walletAddress: walletAddress.toLowerCase()
  };
}

/**
 * Verify personal_sign signature
 * Uses ethers.js to recover the signer and validate against provided address
 */
export function verifyPersonalSignature(authHeaders: AuthHeaders): AuthResult {
  try {
    const { signature, message: messageBase64, walletAddress } = authHeaders;

    // Decode the base64 message
    let decodedMessage: string;
    try {
      const buffer = Buffer.from(messageBase64, 'base64');
      decodedMessage = buffer.toString('utf-8');
    } catch (error) {
      return {
        isValid: false,
        error: 'Failed to decode base64 message'
      };
    }

    // Extract wallet address and timestamp from the message
    const walletMatch = decodedMessage.match(/Wallet:\s*(0x[a-fA-F0-9]{40})/);
    const timestampMatch = decodedMessage.match(/Timestamp:\s*(\d+)/);

    if (!walletMatch || !timestampMatch) {
      return {
        isValid: false,
        error: 'Invalid message format - missing wallet or timestamp'
      };
    }

    const messageWallet = walletMatch[1].toLowerCase();
    const messageTimestamp = parseInt(timestampMatch[1], 10);

    // Verify the wallet in the message matches the header wallet
    if (messageWallet !== walletAddress.toLowerCase()) {
      return {
        isValid: false,
        error: 'Wallet address in message does not match header'
      };
    }

    // Timestamp check disabled - signatures never expire
    // const now = Date.now();
    // const timeDiff = Math.abs(now - messageTimestamp);
    // if (timeDiff > 5 * 60 * 1000) { // 5 minutes in milliseconds
    //   return {
    //     isValid: false,
    //     error: 'Message timestamp is too old (must be within 5 minutes)'
    //   };
    // }

    // Verify signature format
    if (!signature.startsWith('0x') || signature.length !== 132) {
      return {
        isValid: false,
        error: 'Invalid signature format'
      };
    }

    // Verify wallet address format
    if (!walletAddress.startsWith('0x') || walletAddress.length !== 42) {
      return {
        isValid: false,
        error: 'Invalid wallet address format'
      };
    }

    // Recover the address from the signature
    try {
      const recoveredAddress = verifyMessage(decodedMessage, signature);

      if (recoveredAddress.toLowerCase() !== walletAddress.toLowerCase()) {
        return {
          isValid: false,
          error: 'Signature verification failed - recovered address does not match'
        };
      }

      console.log(`[Auth] Authentication successful for wallet: ${walletAddress}`);

      return {
        isValid: true,
        walletAddress
      };
    } catch (error) {
      console.error('[Auth] Failed to verify signature:', error);
      return {
        isValid: false,
        error: 'Failed to verify signature'
      };
    }

  } catch (error) {
    console.error('[Auth] Signature verification error:', error);
    return {
      isValid: false,
      error: 'Signature verification failed'
    };
  }
}

/**
 * Check if request is from admin panel using secret token
 */
export function isAdminRequest(request: NextRequest): boolean {
  const adminToken = request.headers.get('x-admin-token');
  const expectedToken = process.env.ADMIN_SECRET_TOKEN;

  if (!expectedToken) {
    console.warn('[Auth] ADMIN_SECRET_TOKEN not configured');
    return false;
  }

  if (adminToken && adminToken === expectedToken) {
    console.log('[Auth] Admin access granted via x-admin-token');
    return true;
  }

  return false;
}

/**
 * Main authentication function
 */
export function authenticateRequest(request: NextRequest): AuthResult {
  // Extract headers
  const authHeaders = extractAuthHeaders(request);
  if (!authHeaders) {
    return {
      isValid: false,
      error: 'Missing authentication headers (x-auth-signature, x-auth-message, x-wallet-address)'
    };
  }

  // Verify signature
  return verifyPersonalSignature(authHeaders);
}

/**
 * Get user ID from authenticated wallet address
 * For now, we use the wallet address as the user ID
 */
export function getUserIdFromWallet(walletAddress: string): string {
  return walletAddress.toLowerCase();
}

// Export legacy function names for backward compatibility
export { verifyPersonalSignature as verifyHyperliquidSignature };