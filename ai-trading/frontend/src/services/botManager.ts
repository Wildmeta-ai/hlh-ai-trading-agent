import { getHyperliquidNetwork } from '@/config/hyperliquid'

const BOT_MANAGER_URL = 'http://15.235.212.36:8091/api/spawn-bot'

export interface SpawnedBot {
  botId: string
  userAddress: string
  apiPort: number
  dbPath: string
  network: 'testnet' | 'mainnet'
  status: 'running' | 'stopped'
  createdAt: string
  apiUrl: string
  dashboardUrl?: string
}

export interface SpawnBotResponse {
  success: boolean
  bot?: SpawnedBot
  bots?: SpawnedBot[]
  message?: string
  error?: string
  results?: Array<{
    botId: string
    status: 'stopped'
    pm2Success: boolean
  }>
}

export class BotManager {
  static async checkExistingBot(userAddress: string): Promise<SpawnedBot | null> {
    try {
      const network = getHyperliquidNetwork()
      const response = await fetch(`${BOT_MANAGER_URL}?userAddress=${userAddress}&network=${network}`)
      if (!response.ok) return null

      const data: SpawnBotResponse = await response.json()
      if (data.success && data.bots && data.bots.length > 0) {
        return data.bots[0]
      }
      return null
    } catch (error) {
      console.error('Failed to check existing bot:', error)
      return null
    }
  }

  static async spawnBot(userAddress: string, agentPrivateKey: string): Promise<SpawnedBot> {
    const network = getHyperliquidNetwork()

    try {
      const response = await fetch(BOT_MANAGER_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          userAddress,
          agentWalletPrivateKey: agentPrivateKey,
          network,
        })
      })

      const data: SpawnBotResponse = await response.json()

      if (response.status === 409) {
        throw new Error('Bot already exists for this wallet. Please stop the existing bot first.')
      }

      if (!response.ok || !data.success) {
        throw new Error(data.error || data.message || 'Failed to spawn bot')
      }

      if (!data.bot) {
        throw new Error('Bot data not returned from spawn API')
      }

      return data.bot
    } catch (error) {
      console.error('Failed to spawn bot:', error)
      throw error
    }
  }

  static async stopBot(botId?: string, userAddress?: string): Promise<boolean> {
    if (!botId && !userAddress) {
      throw new Error('Either botId or userAddress must be provided')
    }

    try {
      const response = await fetch(BOT_MANAGER_URL, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(
          botId ? { botId } : { userAddress }
        )
      })

      const data: SpawnBotResponse = await response.json()

      if (!response.ok || !data.success) {
        if (response.status === 404) {
          // Bot doesn't exist, consider this a success
          return true
        }
        throw new Error(data.error || data.message || 'Failed to stop bot')
      }

      return true
    } catch (error) {
      console.error('Failed to stop bot:', error)
      throw error
    }
  }

  static async restartBot(userAddress: string, agentPrivateKey: string): Promise<SpawnedBot> {
    // First check if bot exists
    const existingBot = await this.checkExistingBot(userAddress)

    if (existingBot) {
      // Stop existing bot
      await this.stopBot(existingBot.botId)
      // Wait a moment for cleanup
      await new Promise(resolve => setTimeout(resolve, 1000))
    }

    // Spawn new bot
    return await this.spawnBot(userAddress, agentPrivateKey)
  }
}
