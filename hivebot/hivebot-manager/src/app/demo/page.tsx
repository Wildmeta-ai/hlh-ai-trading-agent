'use client';

import React, { useState, useEffect, useRef } from 'react';
// Types for demo page functionality

interface DemoState {
  currentStep: 'chat' | 'strategies' | 'monitor';
  isLoading: boolean;
  message: string;
  lastAction: string;
  showStrategies: boolean;
}

interface ChatMessage {
  id: string;
  text: string;
  sender: 'user' | 'ai';
  timestamp: Date;
}

interface DemoStrategy {
  name: string;
  strategy_type: string;
  connector_type: string;
  trading_pairs: string[];
  bid_spread: number;
  ask_spread: number;
  order_amount: number;
  order_levels: number;
  order_refresh_time: number;
  enabled: boolean;
}

// Demo user configuration
const DEMO_USER = {
  id: 'user_demo_001',
  name: 'John Trader',
  email: 'john.trader@example.com'
};

export default function DemoPage() {
  const [userStrategies, setUserStrategies] = useState<any[]>([]);
  const [demoState, setDemoState] = useState<DemoState>({
    currentStep: 'chat',
    isLoading: false,
    message: 'Ask me anything about trading strategies!',
    lastAction: '',
    showStrategies: false
  });
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    {
      id: '1',
      text: 'Hello! I\'m your AI trading assistant. Ask me anything about strategies, and I\'ll help you deploy them!',
      sender: 'ai',
      timestamp: new Date()
    }
  ]);
  const [inputValue, setInputValue] = useState('');
  const chatEndRef = useRef<HTMLDivElement>(null);


  // Store user's strategy metadata in localStorage
  const [userStrategyMetadata, setUserStrategyMetadata] = useState<any[]>(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('user_strategy_metadata');
      return stored ? JSON.parse(stored) : [];
    }
    return [];
  });

  // Scroll chat to bottom
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  // AI responses based on user input
  const generateAIResponse = (userMessage: string): string => {
    const lowerMessage = userMessage.toLowerCase();

    if (lowerMessage.includes('strategy') || lowerMessage.includes('trade') || lowerMessage.includes('market')) {
      return "I can help you with trading strategies! Here are some pre-configured options I recommend. You can deploy any of these with just one click.";
    }
    if (lowerMessage.includes('bitcoin') || lowerMessage.includes('btc')) {
      return "Bitcoin trading is exciting! I have a conservative BTC market-making strategy ready to deploy. It uses tight spreads for steady profits.";
    }
    if (lowerMessage.includes('ethereum') || lowerMessage.includes('eth')) {
      return "Ethereum offers great volatility! My ETH scalping strategy can capture quick price movements with multiple order levels.";
    }
    if (lowerMessage.includes('risk') || lowerMessage.includes('safe')) {
      return "For risk management, I recommend starting with the conservative strategy. It uses wider spreads and longer refresh times for stability.";
    }
    if (lowerMessage.includes('profit') || lowerMessage.includes('money')) {
      return "To maximize profits, you need the right strategy! Let me show you some configurations that balance risk and reward perfectly.";
    }

    return "Great question! Let me show you some trading strategies that might interest you. Each one is battle-tested and ready to deploy!";
  };

  // Handle chat message submission
  const handleChatSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim()) return;

    // Add user message
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      text: inputValue,
      sender: 'user',
      timestamp: new Date()
    };

    setChatMessages(prev => [...prev, userMessage]);
    setInputValue('');

    // Show loading
    setDemoState(prev => ({ ...prev, isLoading: true }));

    // Generate AI response after delay
    setTimeout(() => {
      const aiResponse: ChatMessage = {
        id: (Date.now() + 1).toString(),
        text: generateAIResponse(inputValue),
        sender: 'ai',
        timestamp: new Date()
      };

      setChatMessages(prev => [...prev, aiResponse]);
      setDemoState(prev => ({
        ...prev,
        isLoading: false,
        showStrategies: true,
        currentStep: 'strategies',
        message: 'Choose a strategy configuration to deploy!'
      }));
    }, 1000);
  };

  // User's personal strategy templates
  const strategyTemplates: Record<string, DemoStrategy> = {
    conservative: {
      name: 'My_Conservative_BTC',
      strategy_type: 'pure_market_making',
      connector_type: 'hyperliquid_perpetual',
      trading_pairs: ['BTC-USD'],
      bid_spread: 0.002, // 0.2% - Realistic conservative spread
      ask_spread: 0.002, // 0.2% - Realistic conservative spread
      order_amount: 0.003,
      order_levels: 1,
      order_refresh_time: 100.0, // 2 minutes - True conservative approach
      enabled: true
    },
    aggressive: {
      name: 'My_Scalping_ETH',
      strategy_type: 'pure_market_making',
      connector_type: 'hyperliquid_perpetual',
      trading_pairs: ['ETH-USD'],
      bid_spread: 0.0005, // 0.1% - Tight spread for quick fills
      ask_spread: 0.001, // 0.1% - Tight spread for quick fills
      order_amount: 0.01,
      order_levels: 3,
      order_refresh_time: 30.0, // 15 seconds - Still aggressive but not excessive
      enabled: true
    },
    balanced: {
      name: 'My_Balanced_SOL',
      strategy_type: 'pure_market_making',
      connector_type: 'hyperliquid_perpetual',
      trading_pairs: ['SOL-USD'],
      bid_spread: 0.0005, // 0.3% - Balanced approach
      ask_spread: 0.003, // 0.3% - Balanced approach
      order_amount: 0.05,
      order_levels: 2,
      order_refresh_time: 60.0, // 1 minute - Balanced refresh rate
      enabled: true
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000); // 10 second updates to reduce load
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      const strategiesRes = await fetch('/api/strategies');
      const strategiesData = await strategiesRes.json();

      // Get only user's strategies from metadata stored in localStorage
      const userStrategyNames = userStrategyMetadata.map(meta => meta.name);
      console.log('[Demo] User strategy names in localStorage:', userStrategyNames);
      console.log('[Demo] All strategies from API:', (strategiesData.strategies || []).map(s => s.name));

      const filteredStrategies = (strategiesData.strategies || []).filter((strategy: any) => {
        // Show strategies that match the user's naming pattern from the demo
        const matchesUserPattern = strategy.name.includes('My_');
        console.log(`[Demo] Strategy ${strategy.name}:`, {
          matchesUserPattern,
          status: strategy.status,
          total_actions: strategy.total_actions,
          successful_orders: strategy.successful_orders,
          failed_orders: strategy.failed_orders,
          actions_per_minute: strategy.actions_per_minute
        });
        return matchesUserPattern;
      });

      setUserStrategies(filteredStrategies);

      // Bot assignment happens transparently in the backend
    } catch (error) {
      console.error('Failed to fetch data:', error);
    }
  };

  // Save strategy metadata to localStorage when deploying
  const saveStrategyMetadata = (strategy: DemoStrategy) => {
    const newMetadata = [...userStrategyMetadata, {
      name: strategy.name,
      deployed_at: new Date().toISOString(),
      user_id: DEMO_USER.id,
      demo_status: 'pending' // For demo simulation
    }];
    setUserStrategyMetadata(newMetadata);
    localStorage.setItem('user_strategy_metadata', JSON.stringify(newMetadata));
  };


  const addDemoStrategy = async (strategyTemplate: DemoStrategy) => {
    setDemoState(prev => ({
      ...prev,
      isLoading: true,
      message: '🚀 Deploying your strategy...',
      currentStep: 'strategies'
    }));

    try {
      // Add unique timestamp to strategy name
      const uniqueStrategy = {
        ...strategyTemplate,
        name: `${strategyTemplate.name}_${Date.now()}`,
        user_id: DEMO_USER.id  // Include user identification
      };

      // Client only sends strategy config - server decides bot assignment
      const response = await fetch('/api/strategies', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          strategy: uniqueStrategy
        })
      });

      const result = await response.json();

      if (result.success) {
        // Save to localStorage on successful deployment
        saveStrategyMetadata(uniqueStrategy);

        setDemoState(prev => ({
          ...prev,
          isLoading: false,
          message: `✅ Your "${uniqueStrategy.name}" strategy is deploying...`,
          lastAction: `Deployed ${uniqueStrategy.strategy_type} strategy to your bot`,
          currentStep: 'monitor'
        }));

        // Refresh data to show new strategy
        setTimeout(fetchData, 1000);

        // For demo: Simulate strategy activation after a delay
        setTimeout(() => {
          setDemoState(prev => ({
            ...prev,
            message: `🚀 Your "${uniqueStrategy.name}" strategy is now LIVE and trading!`,
            lastAction: `Strategy activated and executing trades`
          }));
          // Refresh again to show any status updates
          fetchData();
        }, 5000);
      } else {
        // Even if API reports error, the strategy might have been created
        // Check if it actually exists by refreshing data
        console.log('[Demo] API reported error, but checking if strategy was actually created...');
        setDemoState(prev => ({
          ...prev,
          isLoading: false,
          message: `⚠️ Deployment status unclear, checking...`
        }));

        // Wait a moment then check if the strategy actually exists
        setTimeout(async () => {
          await fetchData();

          // If we can find the strategy in the API response, it was actually created
          const checkResponse = await fetch('/api/strategies');
          const checkData = await checkResponse.json();
          const strategyExists = (checkData.strategies || []).some(s => s.name === uniqueStrategy.name);

          if (strategyExists) {
            // Strategy was created despite API error - add to localStorage
            saveStrategyMetadata(uniqueStrategy);
            setDemoState(prev => ({
              ...prev,
              message: `✅ Your "${uniqueStrategy.name}" strategy is actually live! (despite API error)`,
              lastAction: `Successfully deployed ${uniqueStrategy.strategy_type} strategy`,
              currentStep: 'monitor'
            }));
          } else {
            setDemoState(prev => ({
              ...prev,
              message: `❌ Failed to deploy strategy: ${result.error || 'Unknown error'}`
            }));
          }
        }, 2000);
      }
    } catch (error) {
      console.error('Strategy deployment error:', error);
      setDemoState(prev => ({
        ...prev,
        isLoading: false,
        message: `❌ Deployment failed: ${error.message || 'Network error'}`
      }));
    }
  };

  const deleteAllStrategies = async () => {
    if (userStrategies.length === 0) {
      setDemoState(prev => ({
        ...prev,
        message: '📭 No strategies to delete'
      }));
      return;
    }

    setDemoState(prev => ({
      ...prev,
      isLoading: true,
      message: `🗑️ Stopping ${userStrategies.length} strategies...`,
      currentStep: 'monitor'
    }));

    try {
      // Delete using the general strategy API - pass strategy names directly
      let deletedCount = 0;

      for (const strategy of userStrategies) {
        try {
          console.log(`[Demo] Deleting strategy: ${strategy.name}`);
          const response = await fetch(`/api/strategies?strategy_name=${strategy.name}`, {
            method: 'DELETE'
          });

          if (response.ok) {
            deletedCount++;
            console.log(`[Demo] Successfully deleted: ${strategy.name}`);
          } else {
            console.log(`[Demo] Failed to delete: ${strategy.name}`);
          }
        } catch (err) {
          console.log(`[Demo] Error deleting ${strategy.name}:`, err);
        }
      }

      // Clear localStorage for all user strategies
      setUserStrategyMetadata([]);
      localStorage.setItem('user_strategy_metadata', JSON.stringify([]));

      setDemoState(prev => ({
        ...prev,
        isLoading: false,
        message: `✅ Stopped ${deletedCount} of your strategies`,
        lastAction: `Cleaned up ${deletedCount} user strategies`,
        currentStep: 'chat',
        showStrategies: false
      }));

      // Refresh data to show updated state
      setTimeout(fetchData, 1000);

    } catch (error) {
      console.error('Strategy deletion error:', error);
      setDemoState(prev => ({
        ...prev,
        isLoading: false,
        message: `❌ Error: ${error.message || 'Network error'}`
      }));
    }
  };

  const resetDemo = () => {
    setDemoState({
      currentStep: 'chat',
      isLoading: false,
      message: 'Demo reset! Ready for next demonstration.',
      lastAction: '',
      showStrategies: false
    });
    setChatMessages([
      {
        id: '1',
        text: 'Hello! I\'m your AI trading assistant. Ask me anything about strategies, and I\'ll help you deploy them!',
        sender: 'ai',
        timestamp: new Date()
      }
    ]);
  };

  const totalStrategies = userStrategies.length;
  const activeStrategies = userStrategies;
  const totalActions = userStrategies.reduce((sum, s) => sum + (s.total_actions || 0), 0);

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 to-blue-100">
      {/* Personal Dashboard Header */}
      <header className="bg-white shadow-lg border-b-4 border-green-500">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-20">
            <div className="flex items-center space-x-4">
              <div className="w-12 h-12 bg-gradient-to-br from-green-400 to-blue-500 rounded-full flex items-center justify-center text-white font-bold text-lg">
                JT
              </div>
              <div>
                <h1 className="text-3xl font-bold text-gray-900">My Trading Dashboard</h1>
                <p className="text-sm text-gray-600">Welcome back, {DEMO_USER.name}</p>
              </div>
            </div>

            <div className="flex items-center space-x-6">
              <div className="text-right">
                <div className="text-2xl font-bold text-green-600">{totalStrategies}</div>
                <div className="text-sm text-gray-600">Active Strategies</div>
              </div>
              <div className="text-right">
                <div className="text-2xl font-bold text-blue-600">
                  {totalActions}
                </div>
                <div className="text-sm text-gray-600">Total Actions</div>
              </div>
              <div className="w-4 h-4 bg-green-500 rounded-full animate-pulse" title="Connected"></div>
            </div>
          </div>
        </div>
      </header>

      {/* Demo Status Bar */}
      <div className="bg-gray-800 text-white py-3">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center">
            <div className="flex items-center space-x-4">
              <span className="text-sm font-medium">Status:</span>
              <span className={`px-3 py-1 rounded-full text-sm ${
                demoState.isLoading ? 'bg-yellow-600' : 'bg-green-600'
              }`}>
                {demoState.isLoading ? '⏳ Processing...' : '✅ Ready'}
              </span>
              {demoState.lastAction && (
                <span className="text-sm text-gray-300">Last: {demoState.lastAction}</span>
              )}
            </div>
            <button
              onClick={resetDemo}
              className="px-4 py-1 bg-gray-700 hover:bg-gray-600 rounded text-sm"
            >
              🔄 Reset Demo
            </button>
          </div>
        </div>
      </div>

      {/* Main Demo Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

        {/* Message Banner */}
        <div className={`mb-8 p-6 rounded-lg text-center text-lg font-medium ${
          demoState.message.includes('❌') ? 'bg-red-100 text-red-800 border-2 border-red-300' :
          demoState.message.includes('✅') ? 'bg-green-100 text-green-800 border-2 border-green-300' :
          demoState.isLoading ? 'bg-yellow-100 text-yellow-800 border-2 border-yellow-300 animate-pulse' :
          'bg-blue-100 text-blue-800 border-2 border-blue-300'
        }`}>
          {demoState.message}
        </div>

        {/* Chat Interface */}
        {demoState.currentStep === 'chat' && (
          <div className="max-w-4xl mx-auto">
            <div className="bg-white rounded-lg shadow-lg">
              {/* Chat Header */}
              <div className="border-b p-4">
                <h2 className="text-xl font-bold text-gray-800 flex items-center">
                  <span className="mr-2">🤖</span>
                  AI Trading Assistant
                </h2>
                <p className="text-sm text-gray-600">Ask me anything about trading strategies!</p>
              </div>

              {/* Chat Messages */}
              <div className="h-96 overflow-y-auto p-4 space-y-4">
                {chatMessages.map((message) => (
                  <div key={message.id} className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                      message.sender === 'user'
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-100 text-gray-800'
                    }`}>
                      {message.text}
                    </div>
                  </div>
                ))}
                {demoState.isLoading && (
                  <div className="flex justify-start">
                    <div className="bg-gray-100 text-gray-800 px-4 py-2 rounded-lg">
                      <div className="flex space-x-1">
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
                      </div>
                    </div>
                  </div>
                )}
                <div ref={chatEndRef} />
              </div>

              {/* Chat Input */}
              <div className="border-t p-4">
                <form onSubmit={handleChatSubmit} className="flex space-x-2">
                  <input
                    type="text"
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    placeholder="Ask about strategies, Bitcoin, Ethereum, trading, profits..."
                    className="flex-1 p-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    disabled={demoState.isLoading}
                  />
                  <button
                    type="submit"
                    disabled={demoState.isLoading || !inputValue.trim()}
                    className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Send
                  </button>
                </form>
              </div>
            </div>
          </div>
        )}

        {/* Waterfall Flow Layout */}
        <div className="space-y-8">

          {/* Step 1: Strategy Configurations - Show when chat triggers */}
          {demoState.showStrategies && (
            <div className="bg-white rounded-lg shadow-lg p-6">
              <h2 className="text-xl font-bold text-gray-800 mb-4">Strategy Configurations</h2>

              <div className="space-y-4">
                {Object.entries(strategyTemplates).map(([key, template]) => (
                  <div
                    key={key}
                    className="border border-gray-300 rounded"
                  >
                    <div className="flex justify-between items-center p-2 bg-gray-100 border-b">
                      <span className="font-mono text-sm text-gray-800">config_{key}.json</span>
                      <button
                        onClick={() => addDemoStrategy(template)}
                        disabled={demoState.isLoading}
                        className="px-3 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700 disabled:opacity-50"
                      >
                        {demoState.isLoading ? 'DEPLOYING...' : 'DEPLOY'}
                      </button>
                    </div>

                    <pre className="text-xs font-mono text-gray-800 p-3 bg-gray-50 overflow-x-auto whitespace-pre">
{JSON.stringify({
  name: template.name,
  strategy_type: template.strategy_type,
  connector_type: template.connector_type,
  trading_pairs: template.trading_pairs,
  bid_spread: template.bid_spread,
  ask_spread: template.ask_spread,
  order_amount: template.order_amount,
  order_levels: template.order_levels,
  order_refresh_time: template.order_refresh_time,
  enabled: template.enabled
}, null, 2)}
                    </pre>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Step 2: My Active Strategies - Show combined data without duplicates */}
          {(demoState.currentStep === 'strategies' || demoState.currentStep === 'monitor') && (
            <div className="bg-white rounded-lg shadow-lg p-6">
              <h2 className="text-xl font-bold text-gray-800 mb-4 flex items-center">
                <span className="mr-2">📈</span>
                My Active Strategies
              </h2>

              <div className="space-y-3 max-h-96 overflow-y-auto">
                {/* Combine and deduplicate strategies */}
                {(() => {
                  // Get all strategies and remove duplicates by name
                  const allStrategies = [...activeStrategies];
                  const uniqueStrategies = allStrategies.filter((strategy, index, arr) =>
                    arr.findIndex(s => s.name === strategy.name) === index
                  );

                  if (uniqueStrategies.length === 0) {
                    return (
                      <div className="text-center py-6 text-gray-500">
                        <div className="text-3xl mb-2">🎯</div>
                        <p>No strategies deployed yet</p>
                        <p className="text-sm">Deploy a strategy above to start trading</p>
                      </div>
                    );
                  }

                  return uniqueStrategies.map((strategy, index) => {
                    const isActive = strategy.status === 'active' || strategy.total_actions > 0;

                    return (
                      <div key={index} className={`p-4 rounded-lg border ${
                        isActive
                          ? 'bg-gradient-to-r from-green-50 to-blue-50 border-green-200'
                          : 'bg-gradient-to-r from-yellow-50 to-orange-50 border-yellow-200'
                      }`}>
                        <div className="flex justify-between items-center">
                          <div>
                            <div className="font-semibold text-gray-800 flex items-center">
                              <span className={`w-2 h-2 rounded-full mr-2 ${
                                isActive ? 'bg-green-500 animate-pulse' : 'bg-yellow-500'
                              }`}></span>
                              {strategy.name}
                              <span className={`ml-2 px-2 py-1 text-xs rounded ${
                                isActive ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                              }`}>
                                {isActive ? 'LIVE' : 'PENDING'}
                              </span>
                            </div>
                            <div className="text-sm text-gray-600 mt-1">
                              {(strategy.strategy_type || 'pure_market_making').replace('_', ' ').toUpperCase()} • {strategy.trading_pairs?.join(', ') || 'BTC-USD'}
                            </div>
                            <div className="text-xs text-gray-500 mt-1">
                              Spread: ±{((strategy.bid_spread || 0.001) * 100).toFixed(1)}% •
                              Amount: {strategy.order_amount || 0.002} •
                              Refresh: {strategy.order_refresh_time || 100}s
                            </div>
                          </div>
                          <div className="text-right">
                            <div className="text-sm text-blue-600 font-medium">
                              📊 {strategy.total_actions || 0} actions
                            </div>
                            <div className="text-sm text-gray-600">
                              ⚡ {strategy.performance_per_min?.toFixed(1) || 0}/min
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  });
                })()}
              </div>
            </div>
          )}

          {/* Step 3: Account Management */}
          {(demoState.currentStep === 'strategies' || demoState.currentStep === 'monitor') && (
            <div className="bg-white rounded-lg shadow-lg p-6">
              <h2 className="text-xl font-bold text-gray-800 mb-4 flex items-center">
                <span className="mr-2">🔧</span>
                Account Management
              </h2>

              <div className="space-y-4">
                <button
                  onClick={deleteAllStrategies}
                  disabled={demoState.isLoading || activeStrategies.length === 0}
                  className="w-full py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
                >
                  {demoState.isLoading ? '⏳ Stopping...' : '🛑 Stop All My Strategies'}
                </button>

                <button
                  onClick={fetchData}
                  className="w-full py-3 bg-gray-600 text-white rounded-lg hover:bg-gray-700 font-medium"
                >
                  🔄 Refresh My Data
                </button>

                <div className="pt-4 border-t bg-gray-50 p-3 rounded">
                  <div className="text-sm text-gray-600 space-y-2">
                    <div className="flex justify-between">
                      <span>Active Strategies:</span>
                      <span className="font-medium text-blue-600">{activeStrategies.length}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Total Actions:</span>
                      <span className="font-medium text-blue-600">
                        {totalActions}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Account Status:</span>
                      <span className="font-medium text-green-600">
                        🟢 Connected
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

        </div>
      </main>
    </div>
  );
}
