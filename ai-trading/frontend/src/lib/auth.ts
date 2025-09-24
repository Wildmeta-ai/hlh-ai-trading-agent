'use client'

import { WalletAuth } from '@/services/walletAuth'

export type AuthenticatedRequestInit = RequestInit & {
  headers?: Record<string, string>
}

// Add authentication headers to API requests
export async function withAuth(l1Address: string, options: AuthenticatedRequestInit = {}): Promise<AuthenticatedRequestInit> {
  try {
    console.log('withAuth: Starting authentication for', l1Address)
    const authData = await WalletAuth.getAuthDataForAPI(l1Address)
    console.log('withAuth: Got auth data', { signature: authData.signature.substring(0, 10) + '...', messageLength: authData.message.length })

    return {
      ...options,
      headers: {
        ...options.headers,
        'X-Wallet-Address': l1Address,
        'X-Auth-Signature': authData.signature,
        'X-Auth-Message': btoa(authData.message), // Base64 encode to handle newlines
      }
    }
  } catch (error) {
    console.error('withAuth: Authentication failed', error)
    throw error
  }
}

// Helper for authenticated fetch
export async function authenticatedFetch(l1Address: string, url: string, options: AuthenticatedRequestInit = {}) {
  try {
    console.log('authenticatedFetch: Starting fetch to', url, 'for address', l1Address)
    const authOptions = await withAuth(l1Address, options)
    console.log('authenticatedFetch: Got auth options, making request')
    console.log('authenticatedFetch: Headers being sent:', authOptions.headers)
    const response = await fetch(url, authOptions)
    console.log('authenticatedFetch: Response received', response.status, response.statusText)
    return response
  } catch (error) {
    console.error('authenticatedFetch: Failed', error)
    throw error
  }
}