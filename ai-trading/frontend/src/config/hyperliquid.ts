export type HyperliquidNetwork = 'mainnet' | 'testnet'

interface NetworkConfig {
  name: string
  apiUrl: string
  chain: 'Mainnet' | 'Testnet'
}

export const HYPERLIQUID_NETWORKS: Record<HyperliquidNetwork, NetworkConfig> = {
  mainnet: {
    name: 'Mainnet',
    apiUrl: 'https://api.hyperliquid.xyz/exchange',
    chain: 'Mainnet'
  },
  testnet: {
    name: 'Testnet',
    apiUrl: 'https://api.hyperliquid-testnet.xyz/exchange',
    chain: 'Testnet'
  }
}

// Always return mainnet (testnet/mainnet switching removed)
export const getHyperliquidNetwork = (): HyperliquidNetwork => {
  return 'mainnet'
}

// Set network preference
export const setHyperliquidNetwork = (network: HyperliquidNetwork) => {
  if (typeof window !== 'undefined') {
    localStorage.setItem('hyperliquid_network', network)
    // Trigger storage event for other components to react
    window.dispatchEvent(new Event('hyperliquid-network-change'))
  }
}

// Get current network config
export const getCurrentNetworkConfig = (): NetworkConfig => {
  const network = getHyperliquidNetwork()
  return HYPERLIQUID_NETWORKS[network]
}