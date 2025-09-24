'use client';

import React, { useState, useEffect } from 'react';
import { Trade, Position, Portfolio, StrategyPerformance } from '@/types';
import { createAdminHeaders } from '@/lib/admin';

interface TradingDashboardProps {
  trades: Trade[];
  positions: Position[];
  portfolio: Portfolio;
  strategyPerformance: StrategyPerformance[];
  onCloseStrategy?: (strategy: string, closePositions: boolean, cancelOrders: boolean) => Promise<void>;
}

export function TradingDashboard({ trades, positions, portfolio, strategyPerformance, onCloseStrategy }: TradingDashboardProps) {
  const [activeStrategies, setActiveStrategies] = useState<string[]>([]);

  // Fetch active strategies to determine which ones can be closed
  useEffect(() => {
    const fetchActiveStrategies = async () => {
      try {
        const response = await fetch('/api/strategies', {
          headers: createAdminHeaders()
        });
        const data = await response.json();
        if (data.strategies) {
          const activeNames = data.strategies
            .filter((s: any) => s.is_running)
            .map((s: any) => s.name);
          setActiveStrategies(activeNames);
        }
      } catch (error) {
        console.error('Failed to fetch active strategies:', error);
      }
    };

    fetchActiveStrategies();
    const interval = setInterval(fetchActiveStrategies, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-6">
      {/* Portfolio Overview */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">💼 Portfolio Overview</h3>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-blue-50 p-4 rounded-lg">
            <div className="text-sm text-blue-600 font-semibold">TOTAL BALANCE</div>
            <div className="text-xl font-bold text-blue-900">
              ${portfolio.total_balance.toLocaleString()}
            </div>
          </div>
          <div className={`p-4 rounded-lg ${portfolio.total_pnl >= 0 ? 'bg-green-50' : 'bg-red-50'}`}>
            <div className={`text-sm font-semibold ${portfolio.total_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              TOTAL P&L
            </div>
            <div className={`text-xl font-bold ${portfolio.total_pnl >= 0 ? 'text-green-900' : 'text-red-900'}`}>
              {portfolio.total_pnl >= 0 ? '+' : ''}${portfolio.total_pnl.toFixed(2)}
            </div>
            <div className="text-xs text-gray-600 mt-1">
              Unrealized: ${portfolio.unrealized_pnl.toFixed(2)}
              {portfolio.total_fees && <span> | Fees: ${portfolio.total_fees.toFixed(2)}</span>}
            </div>
          </div>
          <div className="bg-purple-50 p-4 rounded-lg">
            <div className="text-sm text-purple-600 font-semibold">WIN RATE</div>
            <div className="text-xl font-bold text-purple-900">
              {portfolio.win_rate.toFixed(1)}%
            </div>
            <div className="text-xs text-purple-600">
              {portfolio.winning_trades}W / {portfolio.losing_trades}L
            </div>
          </div>
          <div className="bg-gray-50 p-4 rounded-lg">
            <div className="text-sm text-gray-600 font-semibold">24H VOLUME</div>
            <div className="text-xl font-bold text-gray-900">
              ${portfolio.total_volume.toLocaleString()}
            </div>
          </div>
        </div>

        {/* Additional P&L Breakdown */}
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mt-4">
          <div className="bg-gray-50 p-3 rounded-lg">
            <div className="text-xs text-gray-600 font-semibold">MARGIN USED</div>
            <div className="text-lg font-bold text-gray-900">
              {portfolio.margin_used ? `$${portfolio.margin_used.toFixed(2)}` : 'N/A'}
            </div>
            <div className="text-xs text-gray-500">
              Available: ${portfolio.available_balance.toFixed(2)}
            </div>
          </div>
          <div className="bg-indigo-50 p-3 rounded-lg">
            <div className="text-xs text-indigo-600 font-semibold">POSITION VALUE</div>
            <div className="text-lg font-bold text-indigo-900">
              {portfolio.position_value ? `$${portfolio.position_value.toFixed(2)}` : '$0.00'}
            </div>
          </div>
          <div className={`p-3 rounded-lg ${portfolio.return_percentage >= 0 ? 'bg-green-50' : 'bg-red-50'}`}>
            <div className={`text-xs font-semibold ${portfolio.return_percentage >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              RETURN %
            </div>
            <div className={`text-lg font-bold ${portfolio.return_percentage >= 0 ? 'text-green-900' : 'text-red-900'}`}>
              {portfolio.return_percentage >= 0 ? '+' : ''}{portfolio.return_percentage ? portfolio.return_percentage.toFixed(2) : '0.00'}%
            </div>
          </div>
          <div className="bg-orange-50 p-3 rounded-lg">
            <div className="text-xs text-orange-600 font-semibold">LARGEST WIN</div>
            <div className="text-lg font-bold text-orange-900">
              +${portfolio.largest_win.toFixed(2)}
            </div>
          </div>
          <div className="bg-red-50 p-3 rounded-lg">
            <div className="text-xs text-red-600 font-semibold">LARGEST LOSS</div>
            <div className="text-lg font-bold text-red-900">
              ${portfolio.largest_loss.toFixed(2)}
            </div>
          </div>
        </div>
      </div>

      {/* Positions */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b">
          <h3 className="text-lg font-semibold text-gray-900">📊 Open Positions</h3>
        </div>
        <div className="overflow-x-auto">
          {positions.length > 0 ? (
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Symbol</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Side</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Size</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Entry Price</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Current Price</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">P&L</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Leverage</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Margin</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Strategy</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {positions.map((position, index) => (
                  <tr key={index} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap font-medium text-gray-900">
                      {position.symbol}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 rounded text-xs font-semibold ${
                        position.side === 'LONG'
                          ? 'bg-green-100 text-green-800'
                          : position.side === 'SHORT'
                          ? 'bg-red-100 text-red-800'
                          : 'bg-gray-100 text-gray-800'
                      }`}>
                        {position.side}
                      </span>
                      <div className="text-xs text-gray-500 mt-1">
                        {position.leverage}x
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="font-mono text-sm">{position.size.toFixed(5)} {position.symbol.split('-')[0]}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="font-mono text-sm">${position.entry_price.toLocaleString()}</div>
                      <div className="text-xs text-gray-500">Entry Price</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="font-mono text-sm">${position.current_price.toLocaleString()}</div>
                      <div className="text-xs text-gray-500">Market Price</div>
                      <div className={`text-xs font-semibold ${position.current_price >= position.entry_price ? 'text-green-600' : 'text-red-600'}`}>
                        {position.current_price >= position.entry_price ? '+' : ''}${(position.current_price - position.entry_price).toFixed(2)} vs Entry
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className={`font-mono text-sm ${position.unrealized_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {position.unrealized_pnl >= 0 ? '+' : ''}${position.unrealized_pnl.toFixed(2)}
                      </div>
                      <div className={`text-xs ${position.unrealized_pnl >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                        ({position.unrealized_pnl >= 0 ? '+' : ''}{((position.unrealized_pnl / position.margin) * 100).toFixed(2)}%)
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {position.leverage}x
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="font-mono text-sm">${position.margin.toFixed(2)}</div>
                      <div className="text-xs text-gray-500">(Cross)</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 max-w-32 truncate">
                      {position.strategy}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {onCloseStrategy && activeStrategies.includes(position.strategy) && (
                        <button
                          onClick={() => {
                            if (confirm(`Close strategy "${position.strategy}"?\n\nThis will stop the strategy and optionally close positions and cancel orders.`)) {
                              onCloseStrategy(position.strategy, true, true);
                            }
                          }}
                          className="px-3 py-1 text-xs bg-red-100 text-red-700 rounded hover:bg-red-200 transition-colors font-medium"
                          title="Close Active Strategy with full cleanup"
                        >
                          🛑 Close
                        </button>
                      )}
                      {!activeStrategies.includes(position.strategy) && (
                        <span className="text-xs text-gray-400">Inactive</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="text-center py-12 text-gray-500">
              <div className="text-4xl mb-4">📈</div>
              <div className="text-lg font-medium mb-2">No Open Positions</div>
              <div className="text-sm">Positions will appear here when strategies are actively trading</div>
            </div>
          )}
        </div>
      </div>

      {/* Trade History */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b">
          <h3 className="text-lg font-semibold text-gray-900">📋 Trade History</h3>
        </div>
        <div className="overflow-x-auto">
          {trades.length > 0 ? (
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Time</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Symbol</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Action</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Price</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Size</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Value</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Fee</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">P&L</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Strategy</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {trades.slice(0, 20).map((trade) => (
                  <tr key={trade.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {new Date(trade.timestamp).toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap font-medium text-gray-900">
                      {trade.symbol}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 rounded text-xs font-semibold ${
                        trade.action === 'BUY'
                          ? 'bg-green-100 text-green-800'
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {trade.action === 'BUY' ? 'Open Long' : 'Open Short'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap font-mono text-sm">
                      ${trade.price.toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap font-mono text-sm">
                      {trade.amount.toFixed(5)} {trade.symbol.split('-')[0]}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap font-mono text-sm">
                      {trade.value.toFixed(2)} USDC
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap font-mono text-sm">
                      {trade.fee.toFixed(2)} USDC
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {trade.pnl !== undefined ? (
                        <span className={`font-mono text-sm ${trade.pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {trade.pnl >= 0 ? '+' : ''}{trade.pnl.toFixed(2)} USDC
                        </span>
                      ) : (
                        <span className="text-gray-400 text-sm">-</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 max-w-32 truncate">
                      {trade.strategy}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="text-center py-12 text-gray-500">
              <div className="text-4xl mb-4">📈</div>
              <div className="text-lg font-medium mb-2">No Trade History</div>
              <div className="text-sm">Trades will appear here when strategies execute orders</div>
            </div>
          )}
        </div>
      </div>

      {/* Strategy Performance */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b">
          <h3 className="text-lg font-semibold text-gray-900">🎯 Strategy Performance</h3>
        </div>
        <div className="overflow-x-auto">
          {strategyPerformance.length > 0 ? (
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Strategy</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Positions</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Trades</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Volume</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Win Rate</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Total P&L</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Balance Score</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {strategyPerformance.map((perf, index) => (
                  <tr key={index} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="font-medium text-gray-900">{perf.strategy}</div>
                      <div className="text-xs text-gray-500">{perf.hive_id}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {perf.position_count || 0}
                      <div className="text-xs text-gray-500">
                        {perf.position_value ? `$${perf.position_value.toFixed(0)}` : '$0'}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {perf.trade_count}
                      <div className="text-xs text-gray-500">
                        {perf.buy_count || 0}B / {perf.sell_count || 0}S
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap font-mono text-sm">
                      ${perf.total_volume.toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <div className={`font-semibold ${perf.win_rate >= 50 ? 'text-green-600' : 'text-red-600'}`}>
                        {perf.win_rate.toFixed(1)}%
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className={`font-mono text-sm ${perf.total_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {perf.total_pnl >= 0 ? '+' : ''}${perf.total_pnl.toFixed(2)}
                      </div>
                      <div className="text-xs text-gray-500">
                        Unrealized: ${(perf.unrealized_pnl || 0).toFixed(2)}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className={`text-sm ${(perf.balance_score || 0) >= 80 ? 'text-green-600' : (perf.balance_score || 0) >= 50 ? 'text-yellow-600' : 'text-red-600'}`}>
                        {(perf.balance_score || 0).toFixed(0)}%
                      </div>
                      <div className="text-xs text-gray-500">
                        Buy/Sell Balance
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="text-center py-12 text-gray-500">
              <div className="text-4xl mb-4">📊</div>
              <div className="text-lg font-medium mb-2">No Strategy Performance Data</div>
              <div className="text-sm">Performance metrics will appear when strategies have trading history</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default TradingDashboard;
