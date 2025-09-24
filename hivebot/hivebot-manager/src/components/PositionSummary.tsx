'use client';

import React, { useState, useEffect } from 'react';
import { Position, Portfolio } from '@/types';
import { createAdminHeaders } from '@/lib/admin';

interface PositionSummaryProps {
  positions: Position[];
  portfolio: Portfolio | null;
  onCloseStrategy?: (strategy: string, closePositions: boolean, cancelOrders: boolean) => Promise<void>;
}

interface CloseStrategyDialogProps {
  isOpen: boolean;
  strategy: string;
  position: Position;
  onClose: () => void;
  onConfirm: (closePositions: boolean, cancelOrders: boolean) => void;
}

function CloseStrategyDialog({ isOpen, strategy, position, onClose, onConfirm }: CloseStrategyDialogProps) {
  const [closePositions, setClosePositions] = useState(true);
  const [cancelOrders, setCancelOrders] = useState(true);

  if (!isOpen) return null;

  const handleConfirm = () => {
    onConfirm(closePositions, cancelOrders);
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">🛑 Close Strategy</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            ✕
          </button>
        </div>

        <div className="mb-6">
          <p className="text-gray-700 mb-2">
            Are you sure you want to close strategy <strong>"{strategy}"</strong>?
          </p>
          <div className="bg-orange-50 border border-orange-200 rounded-lg p-3 mb-4">
            <p className="text-sm text-orange-800">
              <strong>Current Position:</strong> {position.side} {position.size.toFixed(5)} {position.symbol.split('-')[0]}
              {position.unrealized_pnl >= 0 ? ' (+' : ' ('}${position.unrealized_pnl.toFixed(2)} P&L)
            </p>
          </div>
        </div>

        <div className="space-y-4 mb-6">
          <div className="flex items-center">
            <input
              type="checkbox"
              id="closePositions"
              checked={closePositions}
              onChange={(e) => setClosePositions(e.target.checked)}
              className="h-4 w-4 text-red-600 focus:ring-red-500 border-gray-300 rounded"
            />
            <label htmlFor="closePositions" className="ml-2 text-sm text-gray-700">
              <strong>Close all positions</strong> (Market sell/buy to exit)
            </label>
          </div>

          <div className="flex items-center">
            <input
              type="checkbox"
              id="cancelOrders"
              checked={cancelOrders}
              onChange={(e) => setCancelOrders(e.target.checked)}
              className="h-4 w-4 text-red-600 focus:ring-red-500 border-gray-300 rounded"
            />
            <label htmlFor="cancelOrders" className="ml-2 text-sm text-gray-700">
              <strong>Cancel all open orders</strong> (Clean up order book)
            </label>
          </div>
        </div>

        <div className="bg-gray-50 rounded-lg p-3 mb-6">
          <p className="text-xs text-gray-600">
            <strong>Recommended:</strong> Enable both options for complete cleanup.
            This will close your position and cancel pending orders, leaving nothing behind.
          </p>
        </div>

        <div className="flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 text-gray-700 bg-gray-200 rounded-lg hover:bg-gray-300 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            className="flex-1 px-4 py-2 text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors font-semibold"
          >
            🛑 Close Strategy
          </button>
        </div>
      </div>
    </div>
  );
}

export function PositionSummary({ positions, portfolio, onCloseStrategy }: PositionSummaryProps) {
  const [closeDialogOpen, setCloseDialogOpen] = useState(false);
  const [selectedPosition, setSelectedPosition] = useState<Position | null>(null);
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
    // Refresh every 30 seconds
    const interval = setInterval(fetchActiveStrategies, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleCloseStrategy = (position: Position) => {
    setSelectedPosition(position);
    setCloseDialogOpen(true);
  };

  const handleConfirmClose = async (closePositions: boolean, cancelOrders: boolean) => {
    if (selectedPosition && onCloseStrategy) {
      await onCloseStrategy(selectedPosition.strategy, closePositions, cancelOrders);
    }
  };

  if (!portfolio && positions.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-4">
        <h4 className="text-lg font-semibold text-gray-900 mb-3">💰 Positions & P&L</h4>
        <div className="text-center py-8 text-gray-500">
          <div className="text-3xl mb-2">📊</div>
          <div className="text-sm">No position data available</div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <div className="flex justify-between items-center mb-4">
        <h4 className="text-lg font-semibold text-gray-900">💰 Positions & P&L</h4>
        <button className="text-blue-600 hover:text-blue-800 text-sm font-medium">
          View All →
        </button>
      </div>

      {/* Quick Portfolio Stats */}
      {portfolio && (
        <div className="grid grid-cols-3 gap-4 mb-4">
          <div className="text-center">
            <div className={`text-lg font-bold ${portfolio.total_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {portfolio.total_pnl >= 0 ? '+' : ''}${portfolio.total_pnl.toFixed(2)}
            </div>
            <div className="text-xs text-gray-600">Total P&L</div>
          </div>
          <div className="text-center">
            <div className={`text-lg font-bold ${portfolio.unrealized_pnl >= 0 ? 'text-blue-600' : 'text-orange-600'}`}>
              ${portfolio.unrealized_pnl.toFixed(2)}
            </div>
            <div className="text-xs text-gray-600">Unrealized</div>
          </div>
          <div className="text-center">
            <div className="text-lg font-bold text-purple-600">
              {portfolio.win_rate.toFixed(0)}%
            </div>
            <div className="text-xs text-gray-600">Win Rate</div>
          </div>
        </div>
      )}

      {/* Active Positions */}
      <div className="space-y-2">
        <div className="text-sm font-medium text-gray-700 mb-2">
          Open Positions ({positions.length})
        </div>
        {positions.length > 0 ? (
          positions.slice(0, 3).map((position, index) => (
            <div key={index} className="border rounded-lg p-3 bg-gray-50">
              <div className="flex justify-between items-start">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-sm">{position.symbol}</span>
                  <span className={`px-1.5 py-0.5 rounded text-xs font-semibold ${
                    position.side === 'LONG'
                      ? 'bg-green-100 text-green-800'
                      : position.side === 'SHORT'
                      ? 'bg-red-100 text-red-800'
                      : 'bg-gray-100 text-gray-800'
                  }`}>
                    {position.side}
                  </span>
                  <span className="text-xs text-gray-500">{position.leverage}x</span>
                </div>
                <div className={`text-sm font-mono ${position.unrealized_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {position.unrealized_pnl >= 0 ? '+' : ''}${position.unrealized_pnl.toFixed(2)}
                </div>
              </div>
              <div className="flex justify-between text-xs text-gray-600 mt-1">
                <span>{position.size.toFixed(5)} {position.symbol.split('-')[0]}</span>
                <span>
                  <span className="font-semibold">${position.current_price.toLocaleString()}</span>
                  <span className="text-gray-400 mx-1">current</span>
                  <span className="text-gray-500">/ ${position.entry_price.toLocaleString()}</span>
                  <span className="text-gray-400 ml-1">entry</span>
                </span>
              </div>
              <div className="flex justify-between items-center mt-2">
                <div className="text-xs text-gray-500 truncate flex-1">
                  {position.strategy}
                </div>
                {activeStrategies.includes(position.strategy) && (
                  <button
                    onClick={() => handleCloseStrategy(position)}
                    className="ml-2 px-2 py-1 text-xs bg-red-100 text-red-700 rounded hover:bg-red-200 transition-colors font-medium"
                    title="Close Active Strategy"
                  >
                    🛑 Close
                  </button>
                )}
              </div>
            </div>
          ))
        ) : (
          <div className="text-center py-4 text-gray-500">
            <div className="text-sm">No open positions</div>
          </div>
        )}

        {positions.length > 3 && (
          <div className="text-center py-2">
            <span className="text-xs text-gray-500">
              +{positions.length - 3} more positions
            </span>
          </div>
        )}
      </div>

      {/* Close Strategy Dialog */}
      {selectedPosition && (
        <CloseStrategyDialog
          isOpen={closeDialogOpen}
          strategy={selectedPosition.strategy}
          position={selectedPosition}
          onClose={() => setCloseDialogOpen(false)}
          onConfirm={handleConfirmClose}
        />
      )}
    </div>
  );
}

export default PositionSummary;
