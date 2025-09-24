// API configuration for frontend
// This should match the backend server configuration

interface ApiConfig {
  baseUrl: string
  botBaseUrl: string
  endpoints: {
    chat: string
    backtest: string
    deploy: string
    health: string
    config: string
    testClaude: string
    analyzeWallet: string
    strategies: string
    traderAnalysis: string
    generateStrategies: string
    deployStrategy: string
    stopStrategy: string
    portfolio: string
  }
}

// Default configuration - should match backend config.py ServerConfig
const API_CONFIG: ApiConfig = {
  // Chat API (port 8001)
  baseUrl: process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:3004/api',
  // Bot API (port 8091)
  botBaseUrl: process.env.NEXT_PUBLIC_BOT_API_BASE_URL || 'http://localhost:8091/api',
  endpoints: {
    chat: '/chat',
    backtest: '/backtest',
    deploy: '/deploy',
    health: '/health',
    config: '/config',
    testClaude: '/test-claude',
    analyzeWallet: '/analyze-wallet',
    strategies: '/strategies',
    traderAnalysis: '/trader-analysis',
    generateStrategies: '/generate-strategies',
    deployStrategy: '/strategies',
    stopStrategy: '/strategy',
    portfolio: '/portfolio'
  }
}

// Helper function to build full API URLs
export const getApiUrl = (endpoint: keyof ApiConfig['endpoints']): string => {
  // Bot-related endpoints use the bot API
  const botEndpoints = ['strategies', 'deployStrategy', 'stopStrategy', 'portfolio']
  const baseUrl = botEndpoints.includes(endpoint) ? API_CONFIG.botBaseUrl : API_CONFIG.baseUrl
  return `${baseUrl}${API_CONFIG.endpoints[endpoint]}`
}

// Export the config for direct access if needed
export { API_CONFIG }

// Utility function to check if API is available
export const checkApiHealth = async (): Promise<boolean> => {
  try {
    const response = await fetch(getApiUrl('health'))
    return response.ok
  } catch (error) {
    console.error('API health check failed:', error)
    return false
  }
}
