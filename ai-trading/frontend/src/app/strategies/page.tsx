'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Activity, TrendingUp, RefreshCw, StopCircle, Bot, ArrowLeft, Lock } from 'lucide-react'
import { getApiUrl } from '@/config/api'
import { useWallet } from '@/context/WalletContext'
import { getAgentWalletStore, isAgentWalletValid } from '@/lib/hyperliquid/agent'
import { authenticatedFetch } from '@/lib/auth'
import ConnectWalletButton from '@/components/ConnectWalletButton'

export default function StrategiesPage() {
  const [strategies, setStrategies] = useState<any[]>([])
  const [portfolioData, setPortfolioData] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [portfolioLoading, setPortfolioLoading] = useState(false)
  const [initialLoading, setInitialLoading] = useState(true)
  const { address, hasProvider, connect, isInitializing } = useWallet()
  const router = useRouter()

  const fetchStrategies = async () => {
    console.log('fetchStrategies: Called with address', address)
    if (!address) {
      console.log('fetchStrategies: No address, returning')
      return
    }
    try {
      console.log('fetchStrategies: Setting loading true')
      setLoading(true)
      console.log('fetchStrategies: About to call authenticatedFetch')
      const response = await authenticatedFetch(address, getApiUrl('strategies'))
      console.log('fetchStrategies: Got response', response.status)
      if (response.ok) {
        const data = await response.json()
        console.log('Raw strategies data:', data)
        setStrategies(data.strategies || [])
      }
    } catch (err) {
      console.error('Failed to fetch strategies:', err)
    } finally {
      console.log('fetchStrategies: Setting loading false')
      setLoading(false)
      setInitialLoading(false)
    }
  }

  const fetchPortfolioData = async () => {
    if (!address) return
    try {
      setPortfolioLoading(true)
      const response = await authenticatedFetch(address, getApiUrl('portfolio'))
      if (response.ok) {
        const data = await response.json()
        console.log('Portfolio data:', data)
        setPortfolioData(data)
      }
    } catch (err) {
      console.error('Failed to fetch portfolio data:', err)
    } finally {
      setPortfolioLoading(false)
    }
  }

  const stopStrategyByName = async (name?: string, deploymentId?: string) => {
    if (!address) return
    try {
      let ok = false
      if (name) {
        const response = await authenticatedFetch(address, `${getApiUrl('strategies')}/close`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            strategy: name,
            closePositions: true,
            cancelOrders: true
          })
        })
        ok = response.ok
        if (ok) {
          const data = await response.json()
          console.log('Strategy closed:', data)
        }
      } else if (deploymentId) {
        const response = await authenticatedFetch(address, `${getApiUrl('stopStrategy')}/${deploymentId}/stop`, { method: 'POST' })
        ok = response.ok
      }
      if (ok) fetchStrategies()
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error('Failed to stop strategy:', err)
    }
  }

  // Stop all active strategies
  const stopAllStrategies = async () => {
    if (!strategies || strategies.length === 0 || !address) return

    const stopPromises = strategies
      .filter((s:any) => s.status === 'active')
      .map(async (s:any) => {
        const name = s.name || s.strategy_name || undefined
        try {
          if (name) {
            const response = await authenticatedFetch(address, `${getApiUrl('strategies')}/close`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify({
                strategy: name,
                closePositions: true,
                cancelOrders: true
              })
            })
            if (response.ok) {
              const data = await response.json()
              console.log(`Strategy ${name} closed:`, data)
            }
            return response.ok
          } else if (s.deployment_id) {
            const response = await authenticatedFetch(address, `${getApiUrl('stopStrategy')}/${s.deployment_id}/stop`, {
              method: 'POST'
            })
            return response.ok
          }
        } catch (error) {
          console.error(`Failed to stop strategy ${name || s.deployment_id}:`, error)
          return false
        }
      })

    // Wait for all stop requests to complete
    await Promise.all(stopPromises)

    // Refresh strategies list
    await fetchStrategies()
  }


  useEffect(() => {
    console.log('useEffect: address changed', { address, isInitializing })
    if (address) {
      console.log('useEffect: Calling fetchStrategies and fetchPortfolioData')
      fetchStrategies()
      fetchPortfolioData()
    } else if (!isInitializing) {
      console.log('useEffect: No address and not initializing, setting loading false')
      setInitialLoading(false)
    }
  }, [address, isInitializing])

  // Show loading during wallet initialization
  if (isInitializing) {
    return (
      <div className="flex flex-col h-full items-center justify-center">
        <div className="max-w-md mx-auto text-center p-8">
          <div className="w-8 h-8 border-2 border-[#91F4B5] border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <h2 className="text-xl font-semibold text-white mb-2">Initializing Wallet</h2>
          <p className="text-gray-400 text-sm">
            Checking wallet connection...
          </p>
        </div>
      </div>
    )
  }

  // Require wallet connection
  if (!address) {
    return (
      <div className="flex flex-col h-full items-center justify-center">
        <div className="max-w-md mx-auto text-center p-8">
          <Lock className="w-12 h-12 text-[#FEE45D] mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-white mb-3">Wallet Connection Required</h2>
          <p className="text-gray-400 mb-6">
            Please connect your wallet to access the strategies page and manage your trading strategies.
          </p>
          <ConnectWalletButton />
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      <div className="bg-black/50 border-b border-[#91F4B5]/20 p-4">
        <div className="flex items-center justify-between">
          <h1 className="text-lg font-semibold text-white flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-[#91F4B5]" />
            Active Strategies
          </h1>
          <button
            onClick={() => {
              fetchStrategies()
              fetchPortfolioData()
            }}
            disabled={loading || portfolioLoading}
            className="text-[#91F4B5] hover:text-white transition-colors disabled:opacity-50 flex items-center gap-2"
          >
            <RefreshCw className={`w-4 h-4 ${(loading || portfolioLoading) ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      <div className="flex-1 p-6 overflow-y-auto">
        <div className="max-w-5xl mx-auto">
          {initialLoading ? (
            // Loading skeleton
            <>
              {/* Summary metrics skeleton */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-4">
                <div className="bg-[#91F4B5]/10 border border-[#91F4B5]/30 rounded-lg p-3">
                  <div className="text-xs text-gray-400">Active Strategies</div>
                  <div className="h-8 bg-[#91F4B5]/20 rounded animate-pulse"></div>
                </div>
                <div className="bg-[#AEFEC3]/10 border border-[#AEFEC3]/30 rounded-lg p-3">
                  <div className="text-xs text-gray-400">Total P&L</div>
                  <div className="h-8 bg-[#AEFEC3]/20 rounded animate-pulse"></div>
                </div>
              </div>

              {/* Actions skeleton */}
              <div className="flex items-center justify-between mb-4">
                <div className="h-4 bg-gray-700/50 rounded w-64 animate-pulse"></div>
                <div className="h-8 bg-[#DA373B]/20 rounded w-20 animate-pulse"></div>
              </div>

              {/* Content skeleton - centered empty state style */}
              <div className="flex flex-col items-center justify-center py-12">
                <div className="bg-black/30 rounded-lg p-8 border border-gray-700/50 max-w-md text-center">
                  <div className="flex items-center justify-center gap-2 mb-4">
                    <div className="w-8 h-8 bg-[#91F4B5]/20 rounded animate-pulse"></div>
                    <div className="h-6 bg-gray-700/50 rounded w-40 animate-pulse"></div>
                  </div>
                  <div className="space-y-2 mb-6">
                    <div className="h-4 bg-gray-700/50 rounded w-full animate-pulse"></div>
                    <div className="h-4 bg-gray-700/50 rounded w-3/4 mx-auto animate-pulse"></div>
                    <div className="h-4 bg-gray-700/50 rounded w-5/6 mx-auto animate-pulse"></div>
                  </div>
                  <div className="h-10 bg-[#91F4B5]/20 rounded-lg w-full animate-pulse"></div>
                </div>
              </div>
            </>
          ) : (
            <>
              {/* Summary metrics */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-4">
                <div className="bg-[#91F4B5]/10 border border-[#91F4B5]/30 rounded-lg p-3">
                  <div className="text-xs text-gray-400">Active Strategies</div>
                  <div className="text-2xl font-bold text-[#91F4B5]">
                    {portfolioData?.strategy_performance ?
                      portfolioData.strategy_performance.filter((strategyPerf: any) => {
                        const deployedStrategy = strategies.find((s: any) =>
                          (s.name || s.strategy_name)?.includes(strategyPerf.strategy) ||
                          strategyPerf.strategy.includes(s.name || s.strategy_name || '')
                        );
                        return deployedStrategy; // Count if strategy exists in both endpoints
                      }).length :
                      strategies.filter((s:any)=>s.status==='active' || s.status==='ACTIVE').length
                    }
                  </div>
                </div>
                <div className="bg-[#AEFEC3]/10 border border-[#AEFEC3]/30 rounded-lg p-3">
                  <div className="text-xs text-gray-400">Total P&L</div>
                  <div className={`text-2xl font-bold ${
                    portfolioData?.portfolio ?
                      (Number(portfolioData.portfolio.total_pnl) >= 0 ? 'text-[#AEFEC3]' : 'text-[#DA373B]') :
                      'text-[#AEFEC3]'
                  }`}>
                    {portfolioData?.portfolio ? (
                      `${Number(portfolioData.portfolio.total_pnl) >= 0 ? '+' : ''}$${Number(portfolioData.portfolio.total_pnl).toFixed(2)}`
                    ) : (
                      '$0.00'
                    )}
                  </div>
                </div>
              </div>


              {/* Actions */}
              <div className="flex items-center justify-between mb-4">
                <div className="text-gray-400 text-sm">Manage and monitor your deployed strategies.</div>
                <button
                  onClick={stopAllStrategies}
                  className="bg-[#DA373B]/20 hover:bg-[#DA373B]/30 text-[#DA373B] px-3 py-2 rounded-lg text-sm border border-[#DA373B]/30 transition-colors"
                >
                  Stop All
                </button>
              </div>

              {strategies.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12">
                  <div className="bg-black/30 rounded-lg p-8 border border-gray-700/50 max-w-md text-center">
                    <div className="flex items-center justify-center gap-2 mb-4">
                      <Bot className="w-8 h-8 text-[#91F4B5]" />
                      <h3 className="text-xl font-semibold text-white">AI-Powered Trading</h3>
                    </div>
                    <p className="text-gray-400 text-sm mb-6 leading-relaxed">
                      No strategies deployed yet. Use our AI assistant to generate custom trading strategies
                      tailored to your preferences and market conditions.
                    </p>
                    <a
                      href="/"
                      className="inline-flex items-center gap-2 bg-[#91F4B5]/20 hover:bg-[#91F4B5]/30 text-[#91F4B5] px-6 py-3 rounded-lg text-sm border border-[#91F4B5]/30 transition-colors font-medium"
                    >
                      <Bot className="w-4 h-4" />
                      Generate Strategies with AI
                    </a>
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  {(portfolioData?.strategy_performance && portfolioData.strategy_performance.length > 0) ? portfolioData.strategy_performance
                    .filter((strategyPerf: any) => {
                      // Only show strategies that have a matching strategy in the strategies endpoint (ignore status)
                      const deployedStrategy = strategies.find((s: any) =>
                        (s.name || s.strategy_name)?.includes(strategyPerf.strategy) ||
                        strategyPerf.strategy.includes(s.name || s.strategy_name || '')
                      );
                      return deployedStrategy; // Show if strategy exists in both endpoints
                    })
                    .map((strategyPerf: any) => {
                    // Find matching position data
                    const positionData = portfolioData?.positions?.find((pos: any) => pos.strategy === strategyPerf.strategy) ||
                                        portfolioData?.portfolio?.positions?.find((pos: any) => pos.strategy === strategyPerf.strategy);

                    // Find matching deployed strategy
                    const deployedStrategy = strategies.find((s: any) =>
                      (s.name || s.strategy_name)?.includes(strategyPerf.strategy) ||
                      strategyPerf.strategy.includes(s.name || s.strategy_name || '')
                    );

                    const isActive = deployedStrategy ? true : false; // Active if strategy exists in both endpoints

                    return (
                      <div key={strategyPerf.strategy} className="bg-black/30 rounded-lg p-5 border border-gray-700/50">
                        {/* Header */}
                        <div className="flex items-center justify-between mb-4">
                          <div className="flex items-center gap-3">
                            <div className={`w-3 h-3 rounded-full ${isActive ? 'bg-[#AEFEC3]' : 'bg-[#DA373B]'}`}></div>
                            <div>
                              <h3 className="text-white font-semibold text-base">{strategyPerf.strategy}</h3>
                              <div className="text-xs text-gray-400 mt-1">
                                {positionData ? `${positionData.symbol} • ${positionData.side} • ${positionData.leverage}x` : 'Market Making Strategy'}
                              </div>
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                              isActive ? 'bg-[#AEFEC3]/20 text-[#AEFEC3] border border-[#AEFEC3]/30' : 'bg-[#DA373B]/20 text-[#DA373B] border border-[#DA373B]/30'
                            }`}>
                              {isActive ? 'Active' : 'Inactive'}
                            </span>
                            {isActive && (
                              <button
                                onClick={() => stopStrategyByName(deployedStrategy.name || deployedStrategy.strategy_name, deployedStrategy.deployment_id || deployedStrategy.id)}
                                className="bg-[#DA373B]/20 hover:bg-[#DA373B]/30 text-[#DA373B] px-3 py-1 rounded text-xs border border-[#DA373B]/30 transition-colors flex items-center gap-1"
                              >
                                <StopCircle className="w-3 h-3" />
                                Stop
                              </button>
                            )}
                          </div>
                        </div>

                        {/* Key Metrics - Enhanced Grid */}
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-4">
                          <div className="bg-black/20 rounded-lg p-3 border border-gray-600/20">
                            <div className="text-xs text-gray-400 mb-1">Total P&L</div>
                            <div className={`text-xl font-bold ${Number(strategyPerf.total_pnl) >= 0 ? 'text-[#AEFEC3]' : 'text-[#DA373B]'}`}>
                              {Number(strategyPerf.total_pnl) >= 0 ? '+' : ''}${Number(strategyPerf.total_pnl).toFixed(4)}
                            </div>
                          </div>
                          <div className="bg-black/20 rounded-lg p-3 border border-gray-600/20">
                            <div className="text-xs text-gray-400 mb-1">Total Orders Placed</div>
                            <div className="text-xl font-bold text-white">
                              ${Number(strategyPerf.total_volume).toFixed(2)}
                            </div>
                          </div>
                          <div className="bg-black/20 rounded-lg p-3 border border-gray-600/20">
                            <div className="text-xs text-gray-400 mb-1">Orders Placed</div>
                            <div className="text-xl font-bold text-[#91F4B5]">
                              {strategyPerf.trade_count}
                            </div>
                          </div>
                        </div>

                        {/* Trading Statistics */}
                        <div className="grid grid-cols-2 gap-3 mb-4">
                          <div className="bg-black/10 rounded p-2 border border-gray-700/30">
                            <div className="text-xs text-gray-400">Avg Trade Size</div>
                            <div className="text-sm font-semibold text-white">
                              ${Number(strategyPerf.avg_trade_size).toFixed(2)}
                            </div>
                          </div>
                          <div className="bg-black/10 rounded p-2 border border-gray-700/30">
                            <div className="text-xs text-gray-400">Buy/Sell Ratio</div>
                            <div className="text-sm font-semibold text-white">
                              {strategyPerf.buy_count}/{strategyPerf.sell_count}
                            </div>
                          </div>
                        </div>

                        {/* Position Details */}
                        {positionData && (
                          <div className="border-t border-gray-600/30 pt-4">
                            <h4 className="text-sm font-medium text-[#FEE45D] mb-3">Current Position</h4>
                            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 text-sm">
                              <div>
                                <div className="text-gray-400 mb-1">Size</div>
                                <div className="text-white font-medium">
                                  {Number(positionData.size).toFixed(4)} {positionData.symbol?.split('-')[0] || ''}
                                </div>
                              </div>
                              <div>
                                <div className="text-gray-400 mb-1">Entry Price</div>
                                <div className="text-white font-medium">${Number(positionData.entry_price).toFixed(2)}</div>
                              </div>
                              <div>
                                <div className="text-gray-400 mb-1">Current Price</div>
                                <div className="text-white font-medium">${Number(positionData.current_price).toFixed(2)}</div>
                              </div>
                              <div>
                                <div className="text-gray-400 mb-1">Unrealized P&L</div>
                                <div className={`font-medium ${Number(positionData.unrealized_pnl) >= 0 ? 'text-[#AEFEC3]' : 'text-[#DA373B]'}`}>
                                  {Number(positionData.unrealized_pnl) >= 0 ? '+' : ''}${Number(positionData.unrealized_pnl).toFixed(2)}
                                </div>
                              </div>
                              <div>
                                <div className="text-gray-400 mb-1">Margin</div>
                                <div className="text-white font-medium">${Number(positionData.margin).toFixed(2)}</div>
                              </div>
                            </div>
                          </div>
                        )}

                        {/* P&L Breakdown and Additional Metrics */}
                        <div className="border-t border-gray-600/30 pt-4 mt-4">
                          <h4 className="text-sm font-medium text-[#FEE45D] mb-3">Performance Breakdown</h4>
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                            <div className="bg-black/10 rounded p-2 border border-gray-700/30">
                              <div className="text-xs text-gray-400">Unrealized P&L</div>
                              <div className={`text-sm font-semibold ${Number(strategyPerf.unrealized_pnl) >= 0 ? 'text-[#AEFEC3]' : 'text-[#DA373B]'}`}>
                                {Number(strategyPerf.unrealized_pnl) >= 0 ? '+' : ''}${Number(strategyPerf.unrealized_pnl).toFixed(4)}
                              </div>
                            </div>
                            <div className="bg-black/10 rounded p-2 border border-gray-700/30">
                              <div className="text-xs text-gray-400">Realized P&L</div>
                              <div className={`text-sm font-semibold ${Number(strategyPerf.realized_pnl) >= 0 ? 'text-[#AEFEC3]' : 'text-[#DA373B]'}`}>
                                {Number(strategyPerf.realized_pnl) >= 0 ? '+' : ''}${Number(strategyPerf.realized_pnl).toFixed(4)}
                              </div>
                            </div>
                            {strategyPerf.largest_win > 0 && (
                              <div className="bg-black/10 rounded p-2 border border-gray-700/30">
                                <div className="text-xs text-gray-400">Largest Win</div>
                                <div className="text-sm font-semibold text-[#AEFEC3]">
                                  +${Number(strategyPerf.largest_win).toFixed(4)}
                                </div>
                              </div>
                            )}
                            {Number(strategyPerf.position_value) > 0 && (
                              <div className="bg-black/10 rounded p-2 border border-gray-700/30">
                                <div className="text-xs text-gray-400">Position Value</div>
                                <div className="text-sm font-semibold text-white">
                                  ${Number(strategyPerf.position_value).toFixed(2)}
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    )
                  }) :
                  // Fallback to original strategy display if no portfolio data or empty strategy_performance
                  strategies.map((strategy: any) => (
                    <div key={strategy.deployment_id || strategy.id || strategy.name} className="bg-black/30 rounded-lg p-4 border border-gray-700/50">
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <div className={`w-2 h-2 rounded-full ${
                            (strategy.status === 'active' || strategy.status === 'ACTIVE') ? 'bg-[#AEFEC3]' :
                            strategy.status === 'pending' ? 'bg-[#FEE45D]' : 'bg-[#DA373B]'
                          }`}></div>
                          <span className="text-white font-medium text-sm">
                            {strategy.name || strategy.strategy_name || strategy.strategy || `ID: ${strategy.deployment_id || strategy.id}`}
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                            (strategy.status === 'active' || strategy.status === 'ACTIVE') ? 'bg-[#AEFEC3]/20 text-[#AEFEC3] border border-[#AEFEC3]/30' :
                            strategy.status === 'pending' ? 'bg-[#FEE45D]/20 text-[#FEE45D] border border-[#FEE45D]/30' :
                            'bg-[#DA373B]/20 text-[#DA373B] border border-[#DA373B]/30'
                          }`}>
                            {strategy.status || 'Unknown'}
                          </span>
                          {(strategy.status === 'active' || strategy.status === 'ACTIVE') && (
                            <button
                              onClick={() => stopStrategyByName(strategy.name || strategy.strategy_name, strategy.deployment_id || strategy.id)}
                              className="bg-[#DA373B]/20 hover:bg-[#DA373B]/30 text-[#DA373B] px-2 py-1 rounded text-xs border border-[#DA373B]/30 transition-colors flex items-center gap-1"
                            >
                              <StopCircle className="w-3 h-3" />
                              Stop
                            </button>
                          )}
                        </div>
                      </div>
                      <div className="space-y-2 text-sm">
                        <div className="text-gray-400">
                          Type: <span className="text-white">{strategy.strategy_type || 'Unknown'}</span>
                          {strategy.trading_pairs && strategy.trading_pairs.length > 0 && (
                            <> • Pairs: <span className="text-white">{strategy.trading_pairs.join(', ')}</span></>
                          )}
                        </div>
                        {strategy.connector_type && (
                          <div className="text-gray-400">
                            Connector: <span className="text-white">{strategy.connector_type}</span>
                          </div>
                        )}
                        {(strategy.total_actions > 0 || strategy.successful_orders > 0 || strategy.failed_orders > 0) && (
                          <div className="text-gray-400">
                            Orders: <span className="text-[#AEFEC3]">{strategy.successful_orders}</span> success,
                            <span className="text-[#DA373B]"> {strategy.failed_orders}</span> failed
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
