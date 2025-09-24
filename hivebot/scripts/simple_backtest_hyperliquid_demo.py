#!/usr/bin/env python3
"""
Simple Hyperliquid Backtesting Demo

This script demonstrates Hummingbot's backtesting capabilities using:
- Real historical market data from Hyperliquid
- Simple market making strategy
- Paper trading simulation

Purpose: Show inputs/outputs of Hummingbot backtesting system before adding to Hivebot
"""

import asyncio
import logging
from datetime import datetime

import pandas as pd

from hummingbot import data_path
from hummingbot.data_feed.candles_feed.candles_factory import CandlesFactory
from hummingbot.data_feed.candles_feed.data_types import CandlesConfig
from hummingbot.strategy.script_strategy_base import ScriptStrategyBase


class HyperliquidBacktestDemo(ScriptStrategyBase):
    """
    Simple backtesting demo for Hyperliquid using market making strategy
    Shows how backtesting inputs/outputs work in original Hummingbot
    """

    # ========== BACKTESTING INPUTS ==========
    # These are the configuration parameters that define the backtest

    # Market Configuration
    exchange = "hyperliquid"          # Use Hyperliquid for candles data
    trading_pair = "BTC-USD"         # Use BTC-USD (more reliable for testing)

    # Strategy Parameters
    order_amount = 10.0                # Order size in base asset
    bid_spread_bps = 20               # Bid spread in basis points (0.2%)
    ask_spread_bps = 20               # Ask spread in basis points (0.2%)
    fee_bps = 2.5                     # Trading fee in basis points (0.025%)

    # Time Period
    days = 3                          # Number of days to backtest
    interval = "1m"                   # Candle interval

    # Execution Mode
    paper_trade_enabled = True        # Use paper trading for backtesting

    # ========== SYSTEM SETUP ==========

    precision = 4
    base, quote = trading_pair.split("-")
    execution_exchange = f"{exchange}_paper_trade" if paper_trade_enabled else exchange

    # Initialize candles feed for historical data
    candle = CandlesFactory.get_candle(
        CandlesConfig(
            connector=exchange,
            trading_pair=trading_pair,
            interval=interval,
            max_records=days * 60 * 24  # Total candles needed
        )
    )
    candle.start()

    # Output file for results
    csv_path = data_path() + f"/backtest_demo_{trading_pair}_{days}days.csv"
    markets = {f"{execution_exchange}": {trading_pair}}
    results_df = None

    def on_tick(self):
        """
        Main backtesting logic - processes each time tick
        """
        if not self.candle.ready:
            missing_candles = self.candle._candles.maxlen - len(self.candle._candles)
            self.logger().info(f"Loading historical data... Missing {missing_candles} candles")
            return

        if self.candle.ready and self.results_df is None:
            # Process all historical candles at once for backtesting
            df = self.candle.candles_df.copy()

            # ========== STRATEGY SIMULATION ==========
            # Simulate market making strategy on historical data

            # Calculate bid/ask prices based on spreads
            df['bid_price'] = df["close"] * (1 - self.bid_spread_bps / 10000)
            df['ask_price'] = df["close"] * (1 + self.ask_spread_bps / 10000)

            # Simulate order fills based on price action
            # Buy order fills when market price hits or goes below bid
            df['buy_fill'] = df['low'] <= df['bid_price']
            df['sell_fill'] = df['high'] >= df['ask_price']

            # Calculate filled amounts
            df['buy_amount'] = df['buy_fill'] * self.order_amount
            df['sell_amount'] = df['sell_fill'] * self.order_amount

            # Calculate fees and P&L
            df['fees_paid'] = (df['buy_amount'] * df['bid_price'] +
                               df['sell_amount'] * df['ask_price']) * self.fee_bps / 10000

            # Portfolio changes
            df['base_delta'] = df['buy_amount'] - df['sell_amount']  # Net base asset change
            df['quote_delta'] = (df['sell_amount'] * df['ask_price'] -
                                 df['buy_amount'] * df['bid_price'] - df['fees_paid'])  # Net quote change

            # Cumulative tracking
            df['cumulative_base'] = df['base_delta'].cumsum()
            df['cumulative_quote'] = df['quote_delta'].cumsum()
            df['cumulative_fees'] = df['fees_paid'].cumsum()

            # ========== SAVE RESULTS ==========
            df.to_csv(self.csv_path, index=False)
            self.results_df = df

            msg = f"✅ Backtesting complete! Results saved to {self.csv_path}"
            self.log_with_clock(logging.INFO, msg)
            self.notify_hb_app_with_timestamp(msg)

    async def on_stop(self):
        """Cleanup when backtesting stops"""
        self.candle.stop()

    def get_summary_stats(self, df):
        """Calculate summary statistics from backtest results"""
        total_trades = df['buy_amount'].ne(0).sum() + df['sell_amount'].ne(0).sum()
        total_volume = (df['buy_amount'] + df['sell_amount']).sum()
        total_fees = df['fees_paid'].sum()
        net_pnl = df['quote_delta'].sum()

        start_time = pd.to_datetime(df.iloc[0]['timestamp'], unit='ms')
        end_time = pd.to_datetime(df.iloc[-1]['timestamp'], unit='ms')
        duration = end_time - start_time

        return {
            'start_time': start_time,
            'end_time': end_time,
            'duration': duration,
            'total_trades': total_trades,
            'total_volume': total_volume,
            'total_fees': total_fees,
            'net_pnl': net_pnl,
            'final_base_position': df['base_delta'].sum(),
            'final_quote_balance': df['quote_delta'].sum()
        }

    def format_status(self) -> str:
        """
        Format and display backtesting results - this is the main OUTPUT
        """
        if not self.ready_to_trade:
            return "❌ Market connectors not ready"

        if not self.candle.ready:
            missing = self.candle._candles.maxlen - len(self.candle._candles)
            return f"⏳ Loading historical data... {missing} candles remaining"

        if self.results_df is None:
            return "⏳ Processing backtest..."

        # ========== BACKTESTING OUTPUTS ==========
        # This section shows what the backtesting system produces

        df = self.results_df
        stats = self.get_summary_stats(df)

        lines = []
        lines.append("=" * 60)
        lines.append("🧪 HYPERLIQUID BACKTESTING DEMO RESULTS")
        lines.append("=" * 60)

        # Input Parameters Section
        lines.append("\n📊 INPUT PARAMETERS:")
        lines.append(f"  Exchange: {self.exchange}")
        lines.append(f"  Trading Pair: {self.trading_pair}")
        lines.append(f"  Period: {stats['start_time'].strftime('%Y-%m-%d')} to {stats['end_time'].strftime('%Y-%m-%d')}")
        lines.append(f"  Duration: {stats['duration']}")
        lines.append(f"  Order Amount: {self.order_amount} {self.base}")
        lines.append(f"  Bid Spread: {self.bid_spread_bps} bps")
        lines.append(f"  Ask Spread: {self.ask_spread_bps} bps")
        lines.append(f"  Fee Rate: {self.fee_bps} bps")

        # Performance Outputs Section
        lines.append("\n💰 PERFORMANCE OUTPUTS:")
        lines.append(f"  Total Trades: {int(stats['total_trades'])}")
        lines.append(f"  Total Volume: {stats['total_volume']:.4f} {self.base}")
        lines.append(f"  Total Fees Paid: {stats['total_fees']:.4f} {self.quote}")
        lines.append(f"  Net P&L: {stats['net_pnl']:.4f} {self.quote}")
        lines.append(f"  Final Base Position: {stats['final_base_position']:.4f} {self.base}")
        lines.append(f"  Final Quote Balance: {stats['final_quote_balance']:.4f} {self.quote}")

        # Market Data Analysis
        start_price = df.iloc[0]['open']
        end_price = df.iloc[-1]['close']
        price_change = ((end_price - start_price) / start_price) * 100

        lines.append("\n📈 MARKET DATA:")
        lines.append(f"  Start Price: {start_price:.6f} {self.quote}")
        lines.append(f"  End Price: {end_price:.6f} {self.quote}")
        lines.append(f"  Price Change: {price_change:+.2f}%")
        lines.append(f"  Candles Processed: {len(df)}")

        # File Output Info
        lines.append(f"\n💾 DETAILED RESULTS: {self.csv_path}")
        lines.append("=" * 60)

        return "\n".join(lines)


async def main():
    """
    Demo function showing how to run backtesting programmatically
    """
    print("🚀 Starting Hyperliquid Backtesting Demo...")
    print("This will:")
    print("1. Fetch historical PURR-USDC data from Hyperliquid")
    print("2. Simulate a simple market making strategy")
    print("3. Show backtesting inputs and outputs")
    print("4. Save detailed results to CSV")
    print("\n" + "=" * 50)

    # Note: In real usage, this would be run through Hummingbot CLI
    # This is just to show the concept
    print("💡 To run this backtest:")
    print("1. Copy this file to /scripts/ directory")
    print("2. Run 'start --script simple_backtest_hyperliquid_demo.py' in Hummingbot")
    print("3. Use 'status' command to see results")
    print("4. Check the CSV output for detailed trade-by-trade data")

if __name__ == "__main__":
    asyncio.run(main())
