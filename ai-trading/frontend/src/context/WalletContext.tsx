'use client'

import React, { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { WalletAuth } from '@/services/walletAuth'
import { useBotAutoRecovery, type BotState } from '@/hooks/useBotAutoRecovery'
import type { SpawnedBot } from '@/services/botManager'

type WalletContextType = {
  address: string | null
  chainId: string | null
  connecting: boolean
  hasProvider: boolean
  isInitializing: boolean
  connect: () => Promise<void>
  disconnect: () => void
  copyAddress: () => Promise<void>
  switchChain: (chainIdHex: string) => Promise<void>
  ensureChain: (
    chainIdHex: string,
    params?: {
      chainName: string
      nativeCurrency: { name: string; symbol: string; decimals: number }
      rpcUrls: string[]
      blockExplorerUrls?: string[]
    }
  ) => Promise<void>
  // Bot management
  botState: BotState
  ensureBotReady: () => Promise<SpawnedBot | null>
  refreshBotStatus: () => Promise<void>
}

const WalletContext = createContext<WalletContextType | undefined>(undefined)

export function WalletProvider({ children }: { children: React.ReactNode }) {
  const [address, setAddress] = useState<string | null>(null)
  const [chainId, setChainId] = useState<string | null>(null)
  const [connecting, setConnecting] = useState(false)
  const [hasProvider, setHasProvider] = useState(false)
  const [isInitializing, setIsInitializing] = useState(true)

  // Bot auto-recovery hook
  const { botState, ensureBotReady, forceRefresh } = useBotAutoRecovery(address)

  useEffect(() => {
    const initializeWallet = async () => {
      // Wait a bit to ensure provider is fully loaded
      await new Promise(resolve => setTimeout(resolve, 100))

      const eth = (typeof window !== 'undefined' ? (window as any).ethereum : undefined)
      const isProvider = !!eth && typeof eth.request === 'function'

      console.log('Wallet provider detected:', isProvider, 'ethereum object:', !!eth)
      setHasProvider(isProvider)

      if (!isProvider) {
        console.log('No wallet provider found')
        setIsInitializing(false)
        return
      }

      try {
        // Check if already connected first
        console.log('Checking for existing wallet connection...')
        const accounts = await eth.request({ method: 'eth_accounts' })
        const chainId = await eth.request({ method: 'eth_chainId' })

        console.log('Wallet initialization - accounts:', accounts, 'chainId:', chainId)

        if (accounts && accounts.length > 0) {
          setAddress(accounts[0])
          setChainId(chainId)
          console.log('✅ Wallet connection restored:', accounts[0])
        } else {
          console.log('❌ No existing wallet connection found')
        }
      } catch (error) {
        console.error('❌ Wallet initialization error:', error)
      } finally {
        setIsInitializing(false)
      }

      const onAccountsChanged = (accounts: string[]) => {
        console.log('🔄 Accounts changed:', accounts)
        const newAddress = accounts && accounts.length > 0 ? accounts[0] : null

        // Clear auth data when account changes or disconnects
        if (address && newAddress !== address) {
          WalletAuth.clearAuthData(address)
        }
        if (!newAddress) {
          WalletAuth.clearAllAuthData()
        }

        setAddress(newAddress)
      }
      const onChainChanged = (cid: string) => {
        console.log('🔄 Chain changed:', cid)
        setChainId(cid)
      }

      eth.on?.('accountsChanged', onAccountsChanged)
      eth.on?.('chainChanged', onChainChanged)

      return () => {
        eth.removeListener?.('accountsChanged', onAccountsChanged)
        eth.removeListener?.('chainChanged', onChainChanged)
      }
    }

    initializeWallet()
  }, [])

  const connect = async () => {
    const eth = (typeof window !== 'undefined' ? (window as any).ethereum : undefined)
    if (!eth || typeof eth.request !== 'function') {
      throw new Error('No Web3 wallet detected')
    }
    setConnecting(true)
    try {
      const accounts: string[] = await eth.request({ method: 'eth_requestAccounts' })
      setAddress(accounts && accounts.length > 0 ? accounts[0] : null)
      const cid: string = await eth.request({ method: 'eth_chainId' })
      setChainId(cid)
    } finally {
      setConnecting(false)
    }
  }

  const disconnect = () => {
    // Clear auth data before disconnecting
    if (address) {
      WalletAuth.clearAuthData(address)
    }
    WalletAuth.clearAllAuthData()

    // For EIP-1193 providers, dapps usually just clear local state
    setAddress(null)
  }

  const copyAddress = async () => {
    if (!address) return
    await navigator.clipboard.writeText(address)
  }

  const switchChain = async (chainIdHex: string) => {
    const eth = (typeof window !== 'undefined' ? (window as any).ethereum : undefined)
    if (!eth?.request) throw new Error('No provider')
    await eth.request({ method: 'wallet_switchEthereumChain', params: [{ chainId: chainIdHex }] })
    const cid: string = await eth.request({ method: 'eth_chainId' })
    setChainId(cid)
  }

  const ensureChain = async (
    chainIdHex: string,
    params?: {
      chainName: string
      nativeCurrency: { name: string; symbol: string; decimals: number }
      rpcUrls: string[]
      blockExplorerUrls?: string[]
    }
  ) => {
    const eth = (typeof window !== 'undefined' ? (window as any).ethereum : undefined)
    if (!eth?.request) throw new Error('No provider')
    try {
      await switchChain(chainIdHex)
      return
    } catch (err: any) {
      // 4902: Unrecognized chain
      if (err && (err.code === 4902 || err?.data?.originalError?.code === 4902)) {
        if (!params) throw err
        await eth.request({
          method: 'wallet_addEthereumChain',
          params: [{ chainId: chainIdHex, chainName: params.chainName, nativeCurrency: params.nativeCurrency, rpcUrls: params.rpcUrls, blockExplorerUrls: params.blockExplorerUrls }],
        })
        await switchChain(chainIdHex)
        return
      }
      throw err
    }
  }

  const value = useMemo(
    () => ({
      address,
      chainId,
      connecting,
      hasProvider,
      isInitializing,
      connect,
      disconnect,
      copyAddress,
      switchChain,
      ensureChain,
      botState,
      ensureBotReady,
      refreshBotStatus: forceRefresh
    }),
    [address, chainId, connecting, hasProvider, isInitializing, botState, ensureBotReady, forceRefresh]
  )

  return <WalletContext.Provider value={value}>{children}</WalletContext.Provider>
}

export function useWallet() {
  const ctx = useContext(WalletContext)
  if (!ctx) throw new Error('useWallet must be used within WalletProvider')
  return ctx
}
