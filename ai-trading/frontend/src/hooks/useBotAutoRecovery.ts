'use client'

import { useEffect, useRef, useState } from 'react'
import { getAgentWalletStore, isAgentWalletValid } from '@/lib/hyperliquid/agent'
import { BotManager, type SpawnedBot } from '@/services/botManager'

export type BotStatus = 'checking' | 'ready' | 'spawning' | 'error' | 'none'

export interface BotState {
  status: BotStatus
  bot: SpawnedBot | null
  error: string | null
  lastChecked: number | null
}

export function useBotAutoRecovery(address: string | null) {
  const [botState, setBotState] = useState<BotState>({
    status: 'none',
    bot: null,
    error: null,
    lastChecked: null
  })

  const intervalRef = useRef<NodeJS.Timeout>()
  const isSpawningRef = useRef(false)


  const spawnBotIfNeeded = async (userAddress: string): Promise<SpawnedBot | null> => {
    const agentStore = getAgentWalletStore(userAddress)
    console.log('🔍 Checking agent wallet for address:', userAddress)

    if (!isAgentWalletValid(agentStore) || !agentStore?.pk) {
      console.log('🔑 No valid agent wallet found, skipping bot spawn')
      return null
    }

    // Prevent multiple concurrent spawn attempts
    if (isSpawningRef.current) {
      console.log('⏳ Bot spawn already in progress, skipping...')
      return null
    }

    // Double-check that no bot exists before spawning
    console.log('🔄 Double-checking bot status before spawning...')
    const existingBot = await BotManager.checkExistingBot(userAddress)
    if (existingBot) {
      console.log('✅ Bot found during double-check, no need to spawn:', existingBot.botId)
      setBotState({
        status: 'ready',
        bot: existingBot,
        error: null,
        lastChecked: Date.now()
      })
      return existingBot
    }

    isSpawningRef.current = true

    try {
      setBotState(prev => ({ ...prev, status: 'spawning' }))
      console.log('🚀 No bot found after double-check, spawning bot for user:', userAddress)

      const bot = await BotManager.spawnBot(userAddress, agentStore.pk)
      console.log('✅ Bot spawned successfully:', {
        botId: bot.botId,
        apiUrl: bot.apiUrl,
        network: bot.network,
        status: bot.status
      })

      setBotState({
        status: 'ready',
        bot,
        error: null,
        lastChecked: Date.now()
      })
      return bot
    } catch (error) {
      console.error('❌ Failed to spawn bot:', error)
      // Check if error is about bot already existing
      if (error instanceof Error && error.message.includes('already exists')) {
        console.log('🔄 Bot already exists, checking status...')
        const existingBot = await BotManager.checkExistingBot(userAddress)
        if (existingBot) {
          setBotState({
            status: 'ready',
            bot: existingBot,
            error: null,
            lastChecked: Date.now()
          })
          return existingBot
        }
      }

      setBotState(prev => ({
        ...prev,
        status: 'error',
        error: error instanceof Error ? error.message : 'Failed to spawn bot',
        lastChecked: Date.now()
      }))
      return null
    } finally {
      isSpawningRef.current = false
    }
  }

  const performBotCheck = async (userAddress: string, allowSpawn = false): Promise<SpawnedBot | null> => {
    try {
      console.log('🤖 Checking bot status for user:', userAddress)
      const existingBot = await BotManager.checkExistingBot(userAddress)
      const now = Date.now()

      if (existingBot) {
        console.log('✅ Bot found and ready:', existingBot.botId, 'API:', existingBot.apiUrl)
        setBotState({
          status: 'ready',
          bot: existingBot,
          error: null,
          lastChecked: now
        })
        return existingBot
      } else {
        console.log('❌ No bot found for user:', userAddress)
        setBotState({
          status: 'none',
          bot: null,
          error: null,
          lastChecked: now
        })

        // Only attempt to spawn on initial check or when explicitly allowed
        if (allowSpawn) {
          console.log('🚀 Attempting to spawn bot (spawn allowed)...')
          return await spawnBotIfNeeded(userAddress)
        } else {
          console.log('⏸️ Spawn not allowed for this check (periodic check)')
          return null
        }
      }
    } catch (error) {
      console.error('❌ Failed to check bot status:', error)
      setBotState(prev => ({
        ...prev,
        status: 'error',
        error: error instanceof Error ? error.message : 'Failed to check bot status',
        lastChecked: Date.now()
      }))
      return null
    }
  }

  const ensureBotReady = async (): Promise<SpawnedBot | null> => {
    if (!address) return null

    const agentStore = getAgentWalletStore(address)
    if (!isAgentWalletValid(agentStore) || !agentStore?.pk) {
      throw new Error('Agent wallet not available. Please create an agent wallet first.')
    }

    // If bot is already ready, return it
    if (botState.status === 'ready' && botState.bot) {
      console.log('✅ Bot already ready, returning existing bot:', botState.bot.botId)
      return botState.bot
    }

    // Force a fresh check and spawn if needed
    console.log('🔄 Forcing bot check for strategy deployment...')
    const bot = await performBotCheck(address, true) // Allow spawn for strategy deployment

    // Return the bot directly from the check result
    return bot
  }

  const forceRefresh = async (): Promise<void> => {
    if (!address) return
    await performBotCheck(address, true) // Allow spawn for manual refresh
  }

  useEffect(() => {
    if (!address) {
      console.log('🔌 No wallet address, clearing bot monitoring')
      setBotState({
        status: 'none',
        bot: null,
        error: null,
        lastChecked: null
      })
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = undefined
      }
      return
    }

    console.log('🔄 Starting bot auto-recovery monitoring for:', address)

    // Initial check with spawn allowed
    performBotCheck(address, true)

    // Set up periodic checks every 2 minutes (without spawning)
    intervalRef.current = setInterval(() => {
      console.log('⏰ Periodic bot status check (no spawn)...')
      performBotCheck(address, false) // Periodic checks don't spawn new bots
    }, 120000) // 2 minutes instead of 30 seconds

    return () => {
      console.log('🛑 Stopping bot monitoring for:', address)
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = undefined
      }
    }
  }, [address])

  useEffect(() => {
    // Clean up spawning ref when component unmounts
    return () => {
      isSpawningRef.current = false
    }
  }, [])

  return {
    botState,
    ensureBotReady,
    forceRefresh
  }
}