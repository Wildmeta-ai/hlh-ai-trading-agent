'use client'

import { Wallet } from 'ethers'
import { getCurrentNetworkConfig, getHyperliquidNetwork } from '@/config/hyperliquid'

export type AgentWalletStore = {
  pk: string
  address: string
  expired: number // unix seconds
  network?: 'mainnet' | 'testnet' // Added network field
  signature?: string // Store the agent approval signature for API auth
  typedData?: any // Store the typed data used for verification
}

const STORAGE_KEY_PREFIX = 'session_hl_pk_'

export function generateAgentWallet() {
  return Wallet.createRandom()
}

export function recoverAgentWallet(pk: string) {
  return new Wallet(pk)
}

export function storageKeyFor(l1Address: string) {
  const network = getHyperliquidNetwork()
  return `${STORAGE_KEY_PREFIX}${network}_${l1Address.toLowerCase()}`
}

export function saveAgentWalletPk(l1Address: string, pk: string, address: string, days = 14, signature?: string, typedData?: any) {
  const expired = Math.floor(Date.now() / 1000) + days * 24 * 60 * 60
  const network = getHyperliquidNetwork()
  const store: AgentWalletStore = { pk, address, expired, network, signature, typedData }
  localStorage.setItem(storageKeyFor(l1Address), JSON.stringify(store))
}

export function getAgentWalletStore(l1Address: string): AgentWalletStore | null {
  const raw = localStorage.getItem(storageKeyFor(l1Address))
  if (!raw) return null

  try {
    const parsed = JSON.parse(raw) as AgentWalletStore & { privateKey?: string }

    if (!parsed.pk && parsed.privateKey) {
      const { privateKey, ...rest } = parsed
      const migrated: AgentWalletStore = {
        ...rest,
        pk: privateKey
      }
      localStorage.setItem(storageKeyFor(l1Address), JSON.stringify(migrated))
      return migrated
    }

    if (!parsed.pk) {
      return null
    }

    return parsed
  } catch {
    return null
  }
}

export function clearAgentWallet(l1Address: string) {
  localStorage.removeItem(storageKeyFor(l1Address))
}

export function isAgentWalletValid(store: AgentWalletStore | null): store is AgentWalletStore {
  if (!store) return false
  const now = Math.floor(Date.now() / 1000)
  return store.expired > now
}

// Get signature for API authentication
export function getApiAuthSignature(l1Address: string): { signature: string; typedData: any } | null {
  const store = getAgentWalletStore(l1Address)
  if (!isAgentWalletValid(store) || !store.signature || !store.typedData) {
    return null
  }
  return {
    signature: store.signature,
    typedData: store.typedData
  }
}

export function splitSignature(signature: string) {
  if (!signature.startsWith('0x')) {
    throw new Error('invalid signature')
  }
  const r = `0x${signature.slice(2, 66)}`
  const s = `0x${signature.slice(66, 130)}`
  const v = parseInt(signature.slice(130, 132), 16)
  return { r, s, v }
}

export function buildApproveAgentTypedData(agentAddress: string, chainIdHex?: string) {
  const chainHex = chainIdHex || '0xa4b1' // default Arbitrum One
  const chainDec = parseInt(chainHex, 16)
  const networkConfig = getCurrentNetworkConfig()
  const typedData = {
    domain: {
      name: 'HyperliquidSignTransaction',
      version: '1',
      chainId: chainDec, // must match active wallet chain
      verifyingContract: '0x0000000000000000000000000000000000000000',
    },
    message: {
      hyperliquidChain: networkConfig.chain,
      agentAddress,
      agentName: 'heimawildmeatai',
      nonce: Date.now(),
      signatureChainId: chainHex,
    },
    primaryType: 'HyperliquidTransaction:ApproveAgent',
    types: {
      EIP712Domain: [
        { name: 'name', type: 'string' },
        { name: 'version', type: 'string' },
        { name: 'chainId', type: 'uint256' },
        { name: 'verifyingContract', type: 'address' },
      ],
      'HyperliquidTransaction:ApproveAgent': [
        { name: 'hyperliquidChain', type: 'string' },
        { name: 'agentAddress', type: 'address' },
        { name: 'agentName', type: 'string' },
        { name: 'nonce', type: 'uint64' },
      ],
    },
  }
  return typedData
}
