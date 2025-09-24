'use client'

import { useEffect, useMemo, useState } from 'react'
import { useWallet } from '@/context/WalletContext'
import {
  buildApproveAgentTypedData,
  clearAgentWallet,
  generateAgentWallet,
  getAgentWalletStore,
  isAgentWalletValid,
  saveAgentWalletPk,
  splitSignature,
} from '@/lib/hyperliquid/agent'
import { getCurrentNetworkConfig, getHyperliquidNetwork } from '@/config/hyperliquid'
import { BotManager } from '@/services/botManager'
import { getApiUrl } from '@/config/api'
import { authenticatedFetch } from '@/lib/auth'

function truncate(addr: string) {
  return `${addr.slice(0, 6)}...${addr.slice(-4)}`
}

export default function CreateAgentWalletButton() {
  const { address: l1Address, hasProvider, connect, ensureChain, botState } = useWallet()
  const [busy, setBusy] = useState(false)
  const [agentAddress, setAgentAddress] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const [currentNetwork, setCurrentNetwork] = useState<'mainnet' | 'testnet'>('testnet')
  const [showConfirmDialog, setShowConfirmDialog] = useState(false)
  const valid = useMemo(() => {
    if (!l1Address) return false
    return isAgentWalletValid(getAgentWalletStore(l1Address))
  }, [l1Address])

  useEffect(() => {
    const checkWallet = () => {
      if (!l1Address) {
        setAgentAddress(null)
        return
      }
      const network = getHyperliquidNetwork()
      setCurrentNetwork(network)
      const store = getAgentWalletStore(l1Address)
      if (isAgentWalletValid(store)) {
        setAgentAddress(store.address)
      } else {
        setAgentAddress(null)
      }
    }

    checkWallet()

    // Listen for network changes
    const handleNetworkChange = () => {
      checkWallet()
    }

    window.addEventListener('hyperliquid-network-change', handleNetworkChange)
    return () => {
      window.removeEventListener('hyperliquid-network-change', handleNetworkChange)
    }
  }, [l1Address])


  const createPortfolioSnapshot = async () => {
    if (!l1Address) return

    try {
      // Call strategies/close to create portfolio snapshots for all strategies
      const response = await authenticatedFetch(l1Address, `${getApiUrl('strategies')}/close`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          closePositions: true,
          cancelOrders: true
        })
      })

      if (!response.ok) {
        console.warn('Failed to create portfolio snapshot')
      }
    } catch (error) {
      console.error('Error creating portfolio snapshot:', error)
      // Continue with bot management even if portfolio snapshot fails
    }
  }

  const handleCreate = async (skipBotCheck = false) => {
    if (!hasProvider) {
      window.open('https://metamask.io/download/', '_blank')
      return
    }
    if (!l1Address) {
      await connect()
      return
    }

    // Check for existing bot before creating agent wallet
    if (!skipBotCheck && botState.status === 'ready') {
      setShowConfirmDialog(true)
      return
    }

    // Ensure Arbitrum One for Hyperliquid approval signature
    const targetChainHex = '0xa4b1'
    try {
      await ensureChain(targetChainHex, {
        chainName: 'Arbitrum One',
        nativeCurrency: { name: 'Ether', symbol: 'ETH', decimals: 18 },
        rpcUrls: ['https://arb1.arbitrum.io/rpc'],
        blockExplorerUrls: ['https://arbiscan.io/'],
      })
    } catch (switchErr) {
      console.warn('Chain switch/add failed; user may cancel.', switchErr)
      // If switching fails, we will still attempt signing against current chain
    }
    const eth = (window as any).ethereum
    if (!eth?.request) return
    setBusy(true)
    try {
      const agent = generateAgentWallet()
      // Build typed data with active chain (after attempted switch)
      const activeChainHex: string = (await eth.request({ method: 'eth_chainId' })) as string
      const typedData = buildApproveAgentTypedData(agent.address, activeChainHex)
      const payload = JSON.stringify(typedData)
      // EIP-712 v4 signing
      const signature: string = await eth.request({
        method: 'eth_signTypedData_v4',
        params: [l1Address, payload],
      })
      // Submit approval to Hyperliquid exchange endpoint
      try {
        const networkConfig = getCurrentNetworkConfig()
        const action: any = { ...typedData.message, type: 'approveAgent' }
        if (action.agentName === '') delete action.agentName
        await fetch(networkConfig.apiUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            action,
            signature: splitSignature(signature),
            nonce: action.nonce,
          }),
          mode: 'cors',
        })
      } catch (hlErr) {
        console.warn('Hyperliquid approval submission failed:', hlErr)
      }
      // Persist agent pk and signature for 14 days
      saveAgentWalletPk(l1Address, agent.privateKey, agent.address, 14, signature, typedData)
      setAgentAddress(agent.address)

      // Note: Bot creation is now decoupled from agent wallet approval
      // Bot will be created automatically when needed via the auto-recovery effect
    } catch (e) {
      console.error(e)
      // no-op UI for brevity; could add toast
    } finally {
      setBusy(false)
      setShowConfirmDialog(false)
    }
  }

  const handleConfirmReplace = async () => {
    // Create portfolio snapshot before stopping bot
    await createPortfolioSnapshot()

    // Stop existing bot
    if (l1Address) {
      try {
        await BotManager.stopBot(undefined, l1Address)
      } catch (error) {
        console.error('Failed to stop existing bot:', error)
      }
    }

    // Proceed with creating new agent wallet and bot
    await handleCreate(true)
  }

  const handleClear = async () => {
    if (!l1Address) return

    // Create portfolio snapshot and stop bot when clearing agent wallet
    if (botState.status === 'ready') {
      await createPortfolioSnapshot()
      try {
        await BotManager.stopBot(undefined, l1Address)
      } catch (error) {
        console.error('Failed to stop bot when clearing agent wallet:', error)
      }
    }

    clearAgentWallet(l1Address)
    setAgentAddress(null)
  }

  if (!l1Address) {
    return (
      <button
        onClick={connect}
        className="w-full px-4 py-2.5 rounded-lg bg-[#FEE45D]/15 hover:bg-[#FEE45D]/25 text-[#FEE45D] border border-[#FEE45D]/30 text-sm font-medium"
      >
        Connect to Create Agent
      </button>
    )
  }

  // Confirmation dialog for replacing existing bot
  if (showConfirmDialog) {
    return (
      <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
        <div className="bg-[#1A1B23] border border-[#91F4B5]/30 rounded-lg p-6 max-w-md mx-4">
          <h3 className="text-[#FEE45D] font-semibold text-lg mb-3">⚠️ Warning: Existing Bot Detected</h3>
          <p className="text-gray-300 text-sm mb-4">
            You have an active bot running strategies. Creating a new agent wallet will:
          </p>
          <ul className="list-disc list-inside text-gray-400 text-sm mb-4 space-y-1">
            <li>Stop all currently running strategies</li>
            <li>Create portfolio snapshots for existing strategies</li>
            <li>Terminate the existing bot</li>
            <li>Create a new bot with the new agent wallet</li>
          </ul>
          <p className="text-[#DA373B] text-sm font-medium mb-4">
            This action cannot be undone. Are you sure you want to continue?
          </p>
          <div className="flex gap-3">
            <button
              onClick={() => setShowConfirmDialog(false)}
              className="flex-1 px-4 py-2 rounded-lg bg-gray-700/50 hover:bg-gray-700 text-white border border-gray-600 text-sm"
            >
              Cancel
            </button>
            <button
              onClick={handleConfirmReplace}
              disabled={busy}
              className="flex-1 px-4 py-2 rounded-lg bg-[#DA373B]/15 hover:bg-[#DA373B]/25 text-[#DA373B] border border-[#DA373B]/30 text-sm disabled:opacity-60"
            >
              {busy ? 'Processing…' : 'Replace Bot'}
            </button>
          </div>
        </div>
      </div>
    )
  }

  if (valid || agentAddress) {
    return (
      <div className="flex items-center gap-2">
        <span className="text-xs text-gray-300 flex-shrink-0">Agent:</span>
        <span className={`text-xs px-2 py-1 rounded flex-shrink-0 ${
          currentNetwork === 'testnet'
            ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30'
            : 'bg-green-500/20 text-green-400 border border-green-500/30'
        }`}>
          {currentNetwork === 'testnet' ? 'Testnet' : 'Mainnet'}
        </span>
        <button
          type="button"
          title={agentAddress || undefined}
          onClick={async () => {
            if (!agentAddress) return
            await navigator.clipboard.writeText(agentAddress)
            setCopied(true)
            setTimeout(() => setCopied(false), 1200)
          }}
          className="bg-[#AEFEC3]/15 hover:bg-[#AEFEC3]/25 text-[#AEFEC3] px-3 py-2 rounded-lg border border-[#AEFEC3]/30 text-sm font-medium transition-colors whitespace-nowrap"
        >
          {agentAddress ? (copied ? 'Copied!' : truncate(agentAddress)) : 'Available'}
        </button>
        <button
          onClick={handleClear}
          className="px-3 py-2 rounded-lg bg-[#DA373B]/15 hover:bg-[#DA373B]/25 text-[#DA373B] border border-[#DA373B]/30 text-sm flex-shrink-0 font-medium"
        >
          Clear
        </button>
      </div>
    )
  }

  return (
    <button
      onClick={handleCreate}
      disabled={busy}
      className="w-full px-4 py-2.5 rounded-lg bg-[#AEFEC3]/15 hover:bg-[#AEFEC3]/25 text-[#AEFEC3] border border-[#AEFEC3]/30 text-sm disabled:opacity-60 font-medium"
    >
      {busy ? 'Creating…' : `Create ${currentNetwork === 'testnet' ? 'Testnet' : 'Mainnet'} Agent`}
    </button>
  )
}
