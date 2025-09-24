interface WalletAuthData {
  signature: string
  message: string
  timestamp: number
}

const WALLET_AUTH_KEY = 'wallet_auth_'
const AUTH_VALIDITY_HOURS = 24

// Prevent multiple simultaneous signature requests for the same address
const pendingRequests = new Map<string, Promise<string>>()

export class WalletAuth {
  static getAuthMessage(address: string): string {
    const timestamp = Date.now()
    return `Please sign this message to authenticate with AI Trading Bot.\n\nWallet: ${address}\nTimestamp: ${timestamp}\n\nThis signature will be used for API authentication.`
  }

  static async requestSignature(address: string): Promise<string> {
    const eth = (window as any).ethereum
    if (!eth?.request) {
      throw new Error('MetaMask not available')
    }

    const message = this.getAuthMessage(address)

    try {
      const signature = await eth.request({
        method: 'personal_sign',
        params: [message, address],
      })

      // Store the signature
      this.storeAuthData(address, signature, message)

      return signature
    } catch (error) {
      console.error('Signature request failed:', error)
      throw new Error('User rejected signature request')
    }
  }

  static storeAuthData(address: string, signature: string, message: string): void {
    const authData: WalletAuthData = {
      signature,
      message,
      timestamp: Date.now()
    }

    localStorage.setItem(WALLET_AUTH_KEY + address.toLowerCase(), JSON.stringify(authData))
  }

  static getAuthData(address: string): WalletAuthData | null {
    try {
      const stored = localStorage.getItem(WALLET_AUTH_KEY + address.toLowerCase())
      if (!stored) return null

      const authData: WalletAuthData = JSON.parse(stored)

      // Check if signature is still valid (within 24 hours)
      const hoursOld = (Date.now() - authData.timestamp) / (1000 * 60 * 60)
      if (hoursOld > AUTH_VALIDITY_HOURS) {
        this.clearAuthData(address)
        return null
      }

      return authData
    } catch (error) {
      console.error('Failed to get auth data:', error)
      return null
    }
  }

  static clearAuthData(address: string): void {
    localStorage.removeItem(WALLET_AUTH_KEY + address.toLowerCase())
    // Also clear any pending requests for this address
    pendingRequests.delete(address.toLowerCase())
  }

  static clearAllAuthData(): void {
    // Clear all stored auth data
    const keys = Object.keys(localStorage)
    keys.forEach(key => {
      if (key.startsWith(WALLET_AUTH_KEY)) {
        localStorage.removeItem(key)
      }
    })
    // Clear all pending requests
    pendingRequests.clear()
  }

  static async ensureAuthenticated(address: string): Promise<string> {
    const authData = await this.getAuthDataForAPI(address)
    return authData.signature
  }

  static async getAuthDataForAPI(address: string): Promise<{ signature: string; message: string }> {
    // Get authentication data for API requests
    console.log('WalletAuth.getAuthDataForAPI: Called for address', address)
    const existingAuth = this.getAuthData(address)
    console.log('WalletAuth.getAuthDataForAPI: Existing auth', existingAuth ? 'found' : 'not found')

    if (existingAuth) {
      return {
        signature: existingAuth.signature,
        message: existingAuth.message
      }
    }

    // Check if there's already a pending request for this address
    const lowerAddress = address.toLowerCase()
    if (pendingRequests.has(lowerAddress)) {
      const signature = await pendingRequests.get(lowerAddress)!
      // Get the auth data again after the pending request completes
      const newAuth = this.getAuthData(address)
      if (!newAuth) {
        throw new Error('Authentication failed')
      }
      return {
        signature: newAuth.signature,
        message: newAuth.message
      }
    }

    // Create new signature request
    const signaturePromise = this.requestSignature(address)
    pendingRequests.set(lowerAddress, signaturePromise)

    try {
      await signaturePromise
      const authData = this.getAuthData(address)
      if (!authData) {
        throw new Error('Authentication failed')
      }
      return {
        signature: authData.signature,
        message: authData.message
      }
    } finally {
      // Clean up the pending request
      pendingRequests.delete(lowerAddress)
    }
  }

  static isAuthenticated(address: string): boolean {
    return this.getAuthData(address) !== null
  }
}