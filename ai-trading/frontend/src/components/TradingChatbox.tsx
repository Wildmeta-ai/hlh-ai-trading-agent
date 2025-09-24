'use client'

import { useState, useRef, useEffect } from 'react'
import Link from 'next/link'
import { Send, Bot, User, TrendingUp, BarChart3, Settings, AlertTriangle, Activity, StopCircle, RefreshCw, Lock } from 'lucide-react'
import { getApiUrl } from '@/config/api'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import ConnectWalletButton from '@/components/ConnectWalletButton'
import CreateAgentWalletButton from '@/components/CreateAgentWalletButton'
import { useWallet } from '@/context/WalletContext'
import { authenticatedFetch } from '@/lib/auth'
import { getAgentWalletStore, isAgentWalletValid } from '@/lib/hyperliquid/agent'

interface Message {
  id: string
  type: 'user' | 'assistant'
  content: string
  timestamp: Date
  data?: any
  error?: boolean
}

interface Strategy {
  name: string
  type: string
  symbol: string
  leverage: number
  position_size: number
  risk_per_trade: number
  parameters: Record<string, any>
}

interface TraderProfile {
  trader: string
  nickname: string
  story: Array<{
    symbol: string
    summary: string
  }>
  labels: string[]
  insights: string[]
  suggestion: string
}

export default function TradingChatbox() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isClient, setIsClient] = useState(false)
  const [showStrategies, setShowStrategies] = useState(false)
  const [strategies, setStrategies] = useState<any[]>([])
  const [deployingStrategy, setDeployingStrategy] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const { address, botState, ensureBotReady } = useWallet()

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    setIsClient(true)
    setMessages([
      {
        id: '1',
        type: 'assistant',
        content: 'Hello! I\'m your AI Trading Agent. Enter a wallet address to analyze trading behavior and generate personalized strategies.',
        timestamp: new Date(),
      }
    ])
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const parseStrategyResponse = (content: string) => {
    const jsonMatch = content.match(/```json\s*([\s\S]*?)\s*```/)
    const hasStrategyKeywords = /RSI|strategy|backtest|accumulation|portfolio|risk management/i.test(content)
    
    if (hasStrategyKeywords) {
      return {
        type: 'strategy_response',
        parsedStrategy: jsonMatch ? jsonMatch[1].trim() : null,
        hasActionableStrategy: true
      }
    }
    return null
  }

  const handleBacktest = async (strategyData: any) => {
    // Generate a message to run backtesting using the strategy name and include strategy data
    const backtestMessage = `Run backtesting for strategy: ${strategyData.name}`
    
    // Create a synthetic form event and call handleSubmit
    const syntheticEvent = {
      preventDefault: () => {}
    } as React.FormEvent
    await handleSubmit(syntheticEvent, backtestMessage)
  }



  const handleDeploy = async (strategyData: any) => {
    const strategyId = strategyData.name || strategyData.controller_config?.name || `strategy_${Date.now()}`
    setIsLoading(true)
    setDeployingStrategy(strategyId)

    // Pre-deployment validation
    if (!address) {
      const errorMessage: Message = {
        id: Date.now().toString(),
        type: 'assistant',
        content: `🔐 **Wallet Connection Required**\n\nPlease connect your wallet before deploying strategies.\n\n[Connect Wallet Button should be available in the sidebar]`,
        timestamp: new Date(),
      }
      setMessages(prev => [...prev, errorMessage])
      setIsLoading(false)
      setDeployingStrategy(null)
      return
    }

    const agentStore = getAgentWalletStore(address)
    if (!isAgentWalletValid(agentStore)) {
      const errorMessage: Message = {
        id: Date.now().toString(),
        type: 'assistant',
        content: `🤖 **Agent Wallet Required**\n\nYou need to create an Agent Wallet before deploying strategies.\n\n**Steps:**\n1. Look for the "Create Agent Wallet" button in the sidebar\n2. Click it and follow the setup process\n3. Sign the required transactions\n4. Return here to deploy your strategy\n\n**Why needed?** The Agent Wallet allows the trading bot to execute trades on your behalf securely.`,
        timestamp: new Date(),
      }
      setMessages(prev => [...prev, errorMessage])
      setIsLoading(false)
      setDeployingStrategy(null)
      return
    }

    try {
      // Silently ensure bot is ready before deploying strategy
      console.log('🚀 Ensuring bot is ready for strategy deployment...')
      await ensureBotReady()
      console.log('✅ Bot ready, proceeding with strategy deployment')

      // Extract controller_config from strategyData
      const controllerConfig = strategyData.controller_config || strategyData

      // Transform controller_config to the required API schema
      const deployPayload = {
        strategy: {
          ...controllerConfig,
        }
      }

      console.log('Deploying to:', getApiUrl('deployStrategy'))
      console.log('Deploy payload:', deployPayload)

      const response = await authenticatedFetch(address, getApiUrl('deployStrategy'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(deployPayload)
      })
      
      if (response.ok) {
        const data = await response.json()
        const strategyName = deployPayload.strategy?.name || 'Your Strategy'
        const deployMessage: Message = {
          id: Date.now().toString(),
          type: 'assistant',
          content: `🎉 **Strategy Deployed Successfully!**\n\n**Strategy Name:** ${strategyName}\n\n✅ Your strategy is now live and ready to trade!\n\nYou can monitor its performance in the [Strategies](/strategies) page.`,
          timestamp: new Date(),
        }
        setMessages(prev => [...prev, deployMessage])
      } else {
        // Handle HTTP error responses
        let errorDetail = `HTTP ${response.status}: ${response.statusText}`
        try {
          const errorData = await response.json()
          errorDetail = errorData.detail || errorData.message || errorData.error || errorDetail
        } catch (e) {
          // If we can't parse the error response, use the status text
        }

        const errorMessage: Message = {
          id: Date.now().toString(),
          type: 'assistant',
          content: `❌ **Deployment Failed**\n\n**Error:** ${errorDetail}\n\n**Endpoint:** ${getApiUrl('deployStrategy')}\n\nPlease check your strategy configuration and try again.`,
          timestamp: new Date(),
        }
        setMessages(prev => [...prev, errorMessage])
      }
    } catch (error) {
      console.error('Deployment error:', error)
      const errorMessage: Message = {
        id: Date.now().toString(),
        type: 'assistant',
        content: `❌ **Deployment Failed**\n\n**Error:** ${error instanceof Error ? error.message : 'Network or connection error'}\n\n**Endpoint:** ${getApiUrl('deployStrategy')}\n\nPlease check your network connection and try again.`,
        timestamp: new Date(),
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
      setDeployingStrategy(null)
    }
  }

  const handleSubmit = async (e: React.FormEvent, message?: string) => {
    e.preventDefault()
    if ((!input.trim() && !message) || isLoading) return

    // Check if wallet is connected
    if (!address) {
      const assistantMessage: Message = {
        id: Date.now().toString(),
        type: 'assistant',
        content: 'Please connect your wallet to use the chat feature. You can connect using the button in the top right corner.',
        timestamp: new Date(),
      }
      setMessages(prev => [...prev, assistantMessage])
      return
    }

    const inputMessage = message ?? input

    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: inputMessage,
      timestamp: new Date(),
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    try {
      // Prepare conversation history for API call
      const conversationHistory = messages
        .filter((msg) => msg.error !== true)
        .map((msg) => ({
          role: msg.type === "user" ? "user" : "assistant",
          content: msg.content,
          timestamp: msg.timestamp.toISOString(),
        }));

      conversationHistory.push({
        role: 'user',
        content: `My wallet address is: ${address}`,
        timestamp: userMessage.timestamp.toISOString()
      })

      const response = await fetch(getApiUrl('chat'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: inputMessage,
          conversation_history: conversationHistory
        })
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()

      // Check if the response contains an error
      if (data.error) {
        // Display generic error message without adding to history
        console.error('API Error:', data.error, data.message)
        
        // Show generic error message in UI
        const errorMessage: Message = {
          id: (Date.now() + 1).toString(),
          type: 'assistant',
          content: 'I apologize, but I encountered an issue processing your request. Please try again.',
          timestamp: new Date(),
        }
        setMessages(prev => [...prev, errorMessage])
        return
      }
      
      const responseContent = data.content || 'I processed your request.'
      let responseData = data.data || null

      // Check if response contains strategy data with controller_config
      if (data.payload && data.payload.strategies && data.payload.strategies.length > 0) {
        console.log('🚀 GENERATED STRATEGIES:', JSON.stringify(data.payload.strategies, null, 2))

        responseData = {
          type: 'strategy_generated',
          strategies: data.payload.strategies,
          user_preferences: data.payload.user_preferences,
          meta: data.meta
        }
      } else if (data.type === 'analysis' && responseData) {
        if (responseData.strategies && responseData.strategies.length > 0) {
          console.log('📊 ANALYSIS STRATEGIES:', JSON.stringify(responseData.strategies, null, 2))
        }

        if (responseData.behavior_analysis || responseData.strategies) {
          responseData = {
            type: 'analysis',
            profile: responseData.trader_analysis?.ai_profile || {
              trader: "Trader analysis completed",
              nickname: "Unknown Trader",
              story: [],
              labels: [],
              insights: [],
              suggestion: ""
            },
            strategies: responseData.strategies || []
          }
        }
      } else if (data.type === 'backtest' && responseData) {

        responseData = {
          type: 'backtest',
          results: responseData
        }
      } else {
        const strategyData = parseStrategyResponse(responseContent)
        if (strategyData) {
          responseData = strategyData
        }
      }

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: responseContent,
        timestamp: new Date(),
        data: responseData
      }

      setMessages(prev => [...prev, assistantMessage])
    } catch (error) {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date(),
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const fetchStrategies = async () => {
    if (!address) return
    try {
      const response = await authenticatedFetch(address, getApiUrl('strategies'))
      if (response.ok) {
        const data = await response.json()
        setStrategies(data.strategies)
      }
    } catch (error) {
      console.error('Failed to fetch strategies:', error)
    }
  }

  const stopStrategy = async (deploymentId: string) => {
    if (!address) return
    try {
      const response = await authenticatedFetch(address, `${getApiUrl('stopStrategy')}/${deploymentId}/stop`, {
          method: 'POST'
        })
      if (response.ok) {
        fetchStrategies()
      }
    } catch (error) {
      console.error('Failed to stop strategy:', error)
    }
  }

  const renderTraderProfile = (profile: TraderProfile) => (
    <div className="bg-gradient-to-br from-[#AEFEC3]/20 to-[#91F4B5]/20 rounded-lg p-4 border border-[#AEFEC3]/30 mt-3">
      <div className="flex items-center gap-2 mb-3">
        <User className="w-5 h-5 text-[#91F4B5]" />
        <h3 className="font-semibold text-white">Trader Profile: {profile.nickname}</h3>
      </div>
      
      <p className="text-gray-300 mb-3 text-sm leading-relaxed">{profile.trader}</p>
      
      <div className="grid md:grid-cols-2 gap-4">
        <div>
          <h4 className="text-[#FEE45D] font-medium mb-2 text-sm">Trading Stories</h4>
          <div className="space-y-2">
            {profile.story.map((story, idx) => (
              <div key={idx} className="bg-black/20 rounded p-2">
                <div className="text-[#FFFF49] font-medium text-sm">{story.symbol}</div>
                <div className="text-gray-300 text-xs">{story.summary}</div>
              </div>
            ))}
          </div>
        </div>
        
        <div>
          <h4 className="text-[#FEE45D] font-medium mb-2 text-sm">Labels</h4>
          <div className="flex flex-wrap gap-1 mb-3">
            {profile.labels.map((label, idx) => (
              <span key={idx} className="bg-[#DA373B]/20 text-[#DA373B] px-2 py-1 rounded text-xs border border-[#DA373B]/30">
                {label}
              </span>
            ))}
          </div>
          
          <div className="bg-[#DA373B]/10 border border-[#DA373B]/30 rounded p-2">
            <div className="flex items-center gap-1 mb-1">
              <AlertTriangle className="w-4 h-4 text-[#DA373B]" />
              <span className="text-[#DA373B] font-medium text-sm">Warning</span>
            </div>
            <p className="text-gray-300 text-xs">{profile.suggestion}</p>
          </div>
        </div>
      </div>
    </div>
  )

  const renderStrategies = (strategies: Strategy[]) => (
    <div className="mt-3 space-y-3">
      <div className="flex items-center gap-2 mb-2">
        <TrendingUp className="w-5 h-5 text-[#91F4B5]" />
        <h3 className="font-semibold text-white">Generated Strategies</h3>
      </div>
      
      {strategies.map((strategy, idx) => (
        <div key={idx} className="bg-gradient-to-r from-[#91F4B5]/10 to-[#AEFEC3]/10 rounded-lg p-4 border border-[#91F4B5]/30">
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-[#AEFEC3] font-semibold">{strategy.name}</h4>
            <div className="flex gap-2">
              <button 
                onClick={() => handleBacktest(strategy)}
                className="bg-[#91F4B5]/20 hover:bg-[#91F4B5]/30 text-[#91F4B5] px-3 py-1 rounded text-sm border border-[#91F4B5]/30 transition-colors"
              >
                <BarChart3 className="w-4 h-4 inline mr-1" />
                Backtest
              </button>
              <button className="bg-[#FEE45D]/20 hover:bg-[#FEE45D]/30 text-[#FEE45D] px-3 py-1 rounded text-sm border border-[#FEE45D]/30 transition-colors">
                <Settings className="w-4 h-4 inline mr-1" />
                Deploy
              </button>
            </div>
          </div>
          
          <div className="grid md:grid-cols-3 gap-4 text-sm">
            <div>
              <div className="text-gray-400 mb-1">Symbol</div>
              <div className="text-white font-medium">{strategy.symbol}</div>
            </div>
            <div>
              <div className="text-gray-400 mb-1">Leverage</div>
              <div className="text-white font-medium">{strategy.leverage}x</div>
            </div>
            <div>
              <div className="text-gray-400 mb-1">Position Size</div>
              <div className="text-white font-medium">${strategy.position_size}</div>
            </div>
          </div>
          
          <div className="mt-3 grid md:grid-cols-2 gap-2 text-xs">
            {Object.entries(strategy.parameters).slice(0, 4).map(([key, value]) => (
              <div key={key} className="flex justify-between">
                <span className="text-gray-400">{key.replace(/_/g, ' ')}:</span>
                <span className="text-white">{typeof value === 'number' ? (value < 1 ? `${(value * 100).toFixed(2)}%` : value) : value}</span>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )

  const renderGeneratedStrategies = (strategies: any[]) => (
    <div className="mt-3 space-y-3">
      <div className="flex items-center gap-2 mb-2">
        <TrendingUp className="w-5 h-5 text-[#91F4B5]" />
        <h3 className="font-semibold text-white">Generated Strategies</h3>
      </div>
      
      {strategies.map((strategy, idx) => (
        <div key={idx} className="bg-gradient-to-r from-[#91F4B5]/10 to-[#AEFEC3]/10 rounded-lg p-4 border border-[#91F4B5]/30">
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-[#AEFEC3] font-semibold">{strategy.name}</h4>
            <div className="flex gap-2">
              <button 
                className="bg-[#91F4B5]/20 hover:bg-[#91F4B5]/30 text-[#91F4B5] px-3 py-1 rounded text-sm border border-[#91F4B5]/30 transition-colors"
                onClick={() => handleBacktest(strategy)}>
                <BarChart3 className="w-4 h-4 inline mr-1" />
                Backtest
              </button>
              <button 
                onClick={() => handleDeploy(strategy)}
                disabled={deployingStrategy === strategy.name}
                className={`px-3 py-1 rounded text-sm border transition-colors flex items-center gap-1 ${
                  deployingStrategy === strategy.name
                    ? 'bg-[#FEE45D]/10 text-[#FEE45D]/70 border-[#FEE45D]/20 cursor-wait'
                    : 'bg-[#FEE45D]/20 hover:bg-[#FEE45D]/30 text-[#FEE45D] border-[#FEE45D]/30'
                }`}
              >
                {deployingStrategy === strategy.name ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Deploying...
                  </>
                ) : (
                  <>
                    <Settings className="w-4 h-4" />
                    Deploy
                  </>
                )}
              </button>
            </div>
          </div>
          
          <div className="grid md:grid-cols-1 gap-4 text-sm mb-3">
            {/* <div>
              <div className="text-gray-400 mb-1">Type</div>
              <div className="text-white font-medium">{strategy.type}</div>
            </div> */}
            <div>
              <div className="text-gray-400 mb-1">Symbol</div>
              <div className="text-white font-medium">{strategy.symbol}</div>
            </div>
          </div>
          
          {strategy.controller_config && (
            <div className="mt-3">
              <h5 className="text-[#AEFEC3] font-medium mb-2">Strategy Configuration</h5>
              <div className="grid md:grid-cols-2 gap-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-gray-400">Bid Spread:</span>
                  <span className="text-white">{(strategy.controller_config.bid_spread * 100).toFixed(2)}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Ask Spread:</span>
                  <span className="text-white">{(strategy.controller_config.ask_spread * 100).toFixed(2)}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Order Amount:</span>
                  <span className="text-white">{strategy.controller_config.order_amount}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Order Levels:</span>
                  <span className="text-white">{strategy.controller_config.order_levels}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Refresh Time:</span>
                  <span className="text-white">{strategy.controller_config.order_refresh_time}s</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Trading Pairs:</span>
                  <span className="text-white">{strategy.controller_config.trading_pairs?.join(', ') || 'N/A'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Position Size:</span>
                  <span className="text-white">${strategy.controller_config.position_size || 'N/A'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Leverage:</span>
                  <span className="text-white">{strategy.controller_config.leverage || 'N/A'}x</span>
                </div>
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  )

  const renderCapabilities = (data: any) => (
    <div className="bg-gradient-to-br from-[#91F4B5]/10 to-[#AEFEC3]/10 rounded-lg p-4 border border-[#91F4B5]/30 mt-3">
      <div className="flex items-center gap-2 mb-3">
        <Bot className="w-5 h-5 text-[#91F4B5]" />
        <h3 className="font-semibold text-white">AI Trading Agent Capabilities</h3>
      </div>
      
      {data.core_functions && (
        <div className="space-y-4">
          {data.core_functions.map((func: any, idx: number) => (
            <div key={idx} className="bg-black/20 rounded-lg p-3">
              <h4 className="text-[#AEFEC3] font-medium mb-2">{func.name}</h4>
              <p className="text-gray-300 text-sm mb-2">{func.description}</p>
              {func.capabilities && (
                <div className="flex flex-wrap gap-2">
                  {func.capabilities.map((cap: string, capIdx: number) => (
                    <span key={capIdx} className="bg-[#91F4B5]/20 text-[#91F4B5] px-2 py-1 rounded text-xs border border-[#91F4B5]/30">
                      {cap}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
          
          {data.key_principles && (
            <div className="bg-[#FEE45D]/10 border border-[#FEE45D]/30 rounded-lg p-3 mt-4">
              <h4 className="text-[#FEE45D] font-medium mb-2">Key Principles</h4>
              <ul className="space-y-1">
                {data.key_principles.map((principle: string, idx: number) => (
                  <li key={idx} className="text-gray-300 text-sm flex items-center gap-2">
                    <span className="w-1 h-1 bg-[#FEE45D] rounded-full"></span>
                    {principle}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )

  const renderStrategyResponse = (content: string, data: any) => {
    const sections = content.split(/\n(?=\d+\.|[A-Z][^:]*:|WARNING:)/)

    return (
      <div className="mt-3">
        {sections.map((section, idx) => {
          if (section.includes('```json')) {
            const jsonMatch = section.match(/```json\s*([\s\S]*?)\s*```/)
            if (jsonMatch) {
              if (jsonMatch[1].trim()) {
                return (
                  <div key={idx} className="bg-gray-800/30 rounded-lg p-3 mb-3 border border-gray-600/30">
                    <div className="text-[#AEFEC3] text-sm font-medium mb-2">Strategy Configuration</div>
                    <pre className="text-gray-300 text-xs overflow-x-auto whitespace-pre-wrap">
                      {JSON.stringify(JSON.parse(jsonMatch[1].trim()), null, 2)}
                    </pre>
                  </div>
                )
              }
              return null
            }
          }
          
          if (section.includes('WARNING:')) {
            return (
              <div key={idx} className="bg-[#DA373B]/10 border border-[#DA373B]/30 rounded-lg p-3 mb-3">
                <div className="flex items-center gap-2 mb-2">
                  <AlertTriangle className="w-4 h-4 text-[#DA373B]" />
                  <span className="text-[#DA373B] font-medium text-sm">Warning</span>
                </div>
                <div className="text-gray-300 text-sm leading-relaxed prose prose-invert prose-sm max-w-none">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {section.replace('WARNING:', '').trim()}
                  </ReactMarkdown>
                </div>
              </div>
            )
          }
          
          if (/^\d+\./.test(section.trim())) {
            return (
              <div key={idx} className="bg-[#91F4B5]/10 rounded-lg p-3 mb-3 border border-[#91F4B5]/20">
                <div className="text-gray-300 text-sm leading-relaxed prose prose-invert prose-sm max-w-none">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {section.trim()}
                  </ReactMarkdown>
                </div>
              </div>
            )
          }
          
          return section.trim() ? (
            <div key={idx} className="bg-gray-800/20 rounded-lg p-3 mb-3">
              <div className="text-gray-300 text-sm leading-relaxed prose prose-invert prose-sm max-w-none">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {section.trim()}
                </ReactMarkdown>
              </div>
            </div>
          ) : null
        })}
        
        {data?.hasActionableStrategy && data?.parsedStrategy && (
          <div className="flex gap-3 mt-4 p-4 bg-gradient-to-r from-[#91F4B5]/5 to-[#AEFEC3]/5 rounded-lg border border-[#91F4B5]/20">
            <button
              onClick={() => handleDeploy({ controller_config: data.parsedStrategy || content })}
              disabled={deployingStrategy !== null}
              className={`px-4 py-2 rounded-lg text-sm border transition-colors flex items-center gap-2 font-medium ${
                deployingStrategy !== null
                  ? 'bg-[#FEE45D]/10 text-[#FEE45D]/70 border-[#FEE45D]/20 cursor-wait'
                  : 'bg-[#FEE45D]/20 hover:bg-[#FEE45D]/30 text-[#FEE45D] border-[#FEE45D]/30'
              }`}
            >
              {deployingStrategy !== null ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Deploying Strategy...
                </>
              ) : (
                <>
                  <Settings className="w-4 h-4" />
                  Deploy Strategy
                </>
              )}
            </button>
          </div>
        )}
      </div>
    )
  }

  const renderBacktest = (results: any) => (
    <div className="bg-gradient-to-br from-[#FEE45D]/20 to-[#FFFF49]/20 rounded-lg p-4 border border-[#FEE45D]/30 mt-3">
      <div className="flex items-center gap-2 mb-3">
        <BarChart3 className="w-5 h-5 text-[#FEE45D]" />
        <h3 className="font-semibold text-white">Backtest Results: {results.strategy_name}</h3>
      </div>
      
      <div className="grid md:grid-cols-4 gap-4 mb-4">
        <div className="text-center">
          <div className="text-2xl font-bold text-[#AEFEC3]">+{(results.total_return * 100).toFixed(1)}%</div>
          <div className="text-gray-400 text-sm">Total Return</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-[#91F4B5]">{results.sharpe_ratio}</div>
          <div className="text-gray-400 text-sm">Sharpe Ratio</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-[#DA373B]">{(results.max_drawdown * 100).toFixed(1)}%</div>
          <div className="text-gray-400 text-sm">Max Drawdown</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-[#FEE45D]">{(results.win_rate * 100).toFixed(0)}%</div>
          <div className="text-gray-400 text-sm">Win Rate</div>
        </div>
      </div>
      
      <div className="text-center">
        <div className="text-gray-300 text-sm">
          Period: {results.period} • Total Trades: {results.total_trades}
        </div>
      </div>
    </div>
  )

  return (
    <div className="flex flex-col h-full bg-gradient-to-br from-gray-900 via-black to-gray-900">
      {/* Header */}
      <div className="bg-black/50 border-b border-[#91F4B5]/20 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-[#AEFEC3] to-[#91F4B5] rounded-lg flex items-center justify-center">
              <Bot className="w-6 h-6 text-black" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white font-['Poppins']">AI Trading Agent</h1>
              <p className="text-gray-400 text-sm">Hyperliquid Strategy Generator</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Link
              href="/strategies"
              className="bg-[#91F4B5]/20 hover:bg-[#91F4B5]/30 text-[#91F4B5] px-4 py-2.5 rounded-lg text-sm border border-[#91F4B5]/30 transition-colors flex items-center gap-2 font-medium whitespace-nowrap"
            >
              <Activity className="w-4 h-4" />
              View Strategies
            </Link>
            <div className="flex items-center gap-2">
              <ConnectWalletButton />
            </div>
            <div className="flex items-center gap-2">
              <CreateAgentWalletButton />
            </div>
          </div>
        </div>
      </div>

      {/* Strategies Panel */}
      {showStrategies && (
        <div className="bg-gray-900/50 border-b border-gray-700/50 p-4 max-h-64 overflow-y-auto">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-[#91F4B5]" />
              Active Strategies
            </h2>
            <button
              onClick={fetchStrategies}
              className="text-[#91F4B5] hover:text-white transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
          
          {strategies.length === 0 ? (
            <div className="text-center py-8">
              <Activity className="w-8 h-8 text-gray-500 mx-auto mb-2" />
              <p className="text-gray-400 text-sm">No deployed strategies</p>
            </div>
          ) : (
            <div className="space-y-3">
              {strategies.map((strategy) => (
                <div key={strategy.deployment_id} className="bg-black/30 rounded-lg p-3 border border-gray-700/50">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <div className={`w-2 h-2 rounded-full ${
                        strategy.status === 'active' ? 'bg-[#AEFEC3]' : 'bg-[#DA373B]'
                      }`}></div>
                      <span className="text-white font-medium text-sm">ID: {strategy.deployment_id}</span>
                      <span className={`px-2 py-1 rounded text-xs ${
                        strategy.status === 'active' 
                          ? 'bg-[#AEFEC3]/20 text-[#AEFEC3] border border-[#AEFEC3]/30' 
                          : 'bg-[#DA373B]/20 text-[#DA373B] border border-[#DA373B]/30'
                      }`}>
                        {strategy.status}
                      </span>
                    </div>
                    {strategy.status === 'active' && (
                      <button
                        onClick={() => stopStrategy(strategy.deployment_id)}
                        className="bg-[#DA373B]/20 hover:bg-[#DA373B]/30 text-[#DA373B] px-2 py-1 rounded text-xs border border-[#DA373B]/30 transition-colors flex items-center gap-1"
                      >
                        <StopCircle className="w-3 h-3" />
                        Stop
                      </button>
                    )}
                  </div>
                  
                  <div className="grid grid-cols-3 gap-4 text-xs">
                    <div>
                      <div className="text-gray-400 mb-1">P&L</div>
                      <div className={`font-medium ${
                        strategy.performance.pnl >= 0 ? 'text-[#AEFEC3]' : 'text-[#DA373B]'
                      }`}>
                        ${strategy.performance.pnl >= 0 ? '+' : ''}${strategy.performance.pnl}
                      </div>
                    </div>
                    <div>
                      <div className="text-gray-400 mb-1">Trades</div>
                      <div className="text-white font-medium">{strategy.performance.trades}</div>
                    </div>
                    <div>
                      <div className="text-gray-400 mb-1">Win Rate</div>
                      <div className="text-white font-medium">{(strategy.performance.win_rate * 100).toFixed(0)}%</div>
                    </div>
                  </div>
                  
                  <div className="mt-2 text-xs text-gray-500 truncate">
                    {strategy.strategy}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-4xl rounded-lg p-4 ${
                message.type === 'user'
                  ? 'bg-[#91F4B5]/20 text-white border border-[#91F4B5]/30'
                  : 'bg-gray-800/50 text-gray-100 border border-gray-700/50'
              }`}
            >
              <div className="flex items-start gap-3">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                  message.type === 'user' 
                    ? 'bg-[#91F4B5] text-black' 
                    : 'bg-gradient-to-br from-[#AEFEC3] to-[#91F4B5] text-black'
                }`}>
                  {message.type === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                </div>
                <div className="flex-1 min-w-0">
                  {message.data?.type === 'strategy_response' ? (
                    renderStrategyResponse(message.content, message.data)
                  ) : (
                    <div className="font-['Poppins'] leading-relaxed prose prose-invert prose-sm max-w-none">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {message.content}
                      </ReactMarkdown>
                    </div>
                  )}
                  
                  {message.data?.type === 'analysis' && (
                    <>
                      {renderTraderProfile(message.data.profile)}
                      {renderStrategies(message.data.strategies)}
                    </>
                  )}
                  
                  {message.data?.type === 'strategy_generated' && renderGeneratedStrategies(message.data.strategies)}
                  
                  {message.data?.type === 'backtest' && renderBacktest(message.data.results)}
                  
                  {message.data?.core_functions && renderCapabilities(message.data)}
                  
                  {isClient && (
                    <div className="text-xs text-gray-500 mt-2">
                      {message.timestamp.toLocaleTimeString()}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        ))}
        
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-4 max-w-xs">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-gradient-to-br from-[#AEFEC3] to-[#91F4B5] rounded-full flex items-center justify-center">
                  <Bot className="w-4 h-4 text-black" />
                </div>
                <div className="flex items-center gap-1">
                  <div className="w-2 h-2 bg-[#91F4B5] rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-[#91F4B5] rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                  <div className="w-2 h-2 bg-[#91F4B5] rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                </div>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="bg-black/50 border-t border-[#91F4B5]/20 p-4">
        {!address ? (
          <div className="flex items-center justify-between bg-[#FEE45D]/10 border border-[#FEE45D]/30 rounded-lg p-4">
            <div className="flex items-center gap-3">
              <Lock className="w-5 h-5 text-[#FEE45D]" />
              <span className="text-gray-300">Connect your wallet to enable chat</span>
            </div>
            <ConnectWalletButton />
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Hi I'm Heima Wildmeat AI, your Hyperliquid trading agent. How can I help you today?"
              className="flex-1 bg-gray-800/50 border border-gray-700/50 rounded-lg px-4 py-3 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[#91F4B5]/50 focus:border-[#91F4B5]/50 font-['Poppins']"
              disabled={isLoading}
            />
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className="bg-gradient-to-r from-[#AEFEC3] to-[#91F4B5] text-black px-6 py-3 rounded-lg font-medium hover:from-[#91F4B5] hover:to-[#AEFEC3] transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              <Send className="w-4 h-4" />
              Send
            </button>
          </form>
        )}
      </div>
    </div>
  )
}
