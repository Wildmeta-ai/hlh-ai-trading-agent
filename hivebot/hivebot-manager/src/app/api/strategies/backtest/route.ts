import { NextRequest, NextResponse } from 'next/server';
import { BacktestConfig, BacktestResult } from '@/types';

// Mock historical price data (replace with real data source)
interface PriceData {
  date: string;
  price: number;
  high: number;
  low: number;
  volume: number;
}

function generateMockPriceData(startDate: string, endDate: string, tradingPair: string): PriceData[] {
  const start = new Date(startDate);
  const end = new Date(endDate);
  const days = Math.ceil((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24));

  const prices = [];
  let basePrice = tradingPair.includes('BTC') ? 50000 :
                  tradingPair.includes('ETH') ? 3000 : 100;

  for (let i = 0; i < days; i++) {
    const date = new Date(start);
    date.setDate(date.getDate() + i);

    // Simple random walk with mean reversion
    const volatility = 0.02;
    const meanReversion = 0.001;
    const randomChange = (Math.random() - 0.5) * volatility;
    const reversion = -meanReversion * (basePrice - (tradingPair.includes('BTC') ? 50000 : 3000)) / basePrice;

    basePrice *= (1 + randomChange + reversion);

    prices.push({
      date: date.toISOString().split('T')[0],
      price: parseFloat(basePrice.toFixed(2)),
      high: parseFloat((basePrice * 1.015).toFixed(2)),
      low: parseFloat((basePrice * 0.985).toFixed(2)),
      volume: Math.floor(Math.random() * 1000000)
    });
  }

  return prices;
}

class StrategyBacktester {
  private config: BacktestConfig;
  private priceData: PriceData[];

  constructor(config: BacktestConfig) {
    this.config = config;
    this.priceData = generateMockPriceData(
      config.start_date,
      config.end_date,
      config.trading_pair
    );
  }

  runBacktest(): BacktestResult {
    const { strategy, initial_balance } = this.config;

    let balance = initial_balance;
    let basePosition = 0;
    let totalTrades = 0;
    let winningTrades = 0;
    // let totalFees = 0;
    let maxBalance = balance;
    let maxDrawdown = 0;
    const dailyReturns: Array<{ date: string; return: number; balance: number }> = [];

    const feeRate = 0.001; // 0.1% fee per trade

    for (let i = 1; i < this.priceData.length; i++) {
      // const prevPrice = this.priceData[i - 1].price;
      const currentPrice = this.priceData[i].price;
      const date = this.priceData[i].date;

      // Calculate bid/ask prices based on strategy spreads
      const bidPrice = currentPrice * (1 - strategy.bid_spread);
      const askPrice = currentPrice * (1 + strategy.ask_spread);

      // Simulate market making strategy
      const shouldTrade = Math.random() > 0.7; // 30% fill probability

      if (shouldTrade) {
        // Alternate between buy and sell orders
        const isBuyOrder = totalTrades % 2 === 0;
        const orderSize = strategy.order_amount;

        if (isBuyOrder) {
          // Buy order filled at bid price
          const cost = orderSize * bidPrice;
          const fee = cost * feeRate;

          if (balance >= cost + fee) {
            balance -= cost + fee;
            basePosition += orderSize;
            // totalFees += fee;
            totalTrades++;
          }
        } else {
          // Sell order filled at ask price
          if (basePosition >= orderSize) {
            const revenue = orderSize * askPrice;
            const fee = revenue * feeRate;

            balance += revenue - fee;
            basePosition -= orderSize;
            // totalFees += fee;
            totalTrades++;

            // Calculate if this was a winning trade
            const avgBuyPrice = (initial_balance - balance + basePosition * currentPrice) / Math.max(basePosition + orderSize, 1);
            if (askPrice > avgBuyPrice) {
              winningTrades++;
            }
          }
        }
      }

      // Calculate portfolio value
      const portfolioValue = balance + basePosition * currentPrice;
      maxBalance = Math.max(maxBalance, portfolioValue);
      const currentDrawdown = (maxBalance - portfolioValue) / maxBalance;
      maxDrawdown = Math.max(maxDrawdown, currentDrawdown);

      // Record daily returns
      const prevBalance = dailyReturns[dailyReturns.length - 1]?.balance || initial_balance;
      const dailyReturn: number = i === 1 ? 0 : (portfolioValue - prevBalance) / prevBalance;
      dailyReturns.push({
        date,
        return: dailyReturn,
        balance: portfolioValue
      });
    }

    // Final portfolio value
    const finalPrice = this.priceData[this.priceData.length - 1].price;
    const finalValue = balance + basePosition * finalPrice;
    const totalReturn = (finalValue - initial_balance) / initial_balance;

    // Calculate Sharpe ratio (simplified)
    const avgDailyReturn = dailyReturns.reduce((sum, day) => sum + day.return, 0) / dailyReturns.length;
    const returnStdDev = Math.sqrt(
      dailyReturns.reduce((sum, day) => sum + Math.pow(day.return - avgDailyReturn, 2), 0) / dailyReturns.length
    );
    const sharpeRatio = returnStdDev > 0 ? (avgDailyReturn / returnStdDev) * Math.sqrt(365) : 0;

    // Calculate profit factor
    const grossProfit = dailyReturns.filter(day => day.return > 0).reduce((sum, day) => sum + day.return, 0);
    const grossLoss = Math.abs(dailyReturns.filter(day => day.return < 0).reduce((sum, day) => sum + day.return, 0));
    const profitFactor = grossLoss > 0 ? grossProfit / grossLoss : grossProfit > 0 ? 10 : 1;

    return {
      config: this.config,
      total_return: totalReturn,
      max_drawdown: maxDrawdown,
      sharpe_ratio: parseFloat(sharpeRatio.toFixed(3)),
      win_rate: totalTrades > 0 ? winningTrades / totalTrades : 0,
      total_trades: totalTrades,
      profit_factor: parseFloat(profitFactor.toFixed(3)),
      daily_returns: dailyReturns
    };
  }
}

export async function POST(request: NextRequest) {
  try {
    const config: BacktestConfig = await request.json();

    // Validate backtest configuration
    if (!config.strategy || !config.start_date || !config.end_date) {
      return NextResponse.json(
        { error: 'Strategy, start_date, and end_date are required' },
        { status: 400 }
      );
    }

    const startDate = new Date(config.start_date);
    const endDate = new Date(config.end_date);

    if (startDate >= endDate) {
      return NextResponse.json(
        { error: 'start_date must be before end_date' },
        { status: 400 }
      );
    }

    // Limit backtest duration to prevent abuse
    const maxDays = 365;
    const daysDiff = (endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24);

    if (daysDiff > maxDays) {
      return NextResponse.json(
        { error: `Backtest duration cannot exceed ${maxDays} days` },
        { status: 400 }
      );
    }

    const backtester = new StrategyBacktester(config);
    const result = backtester.runBacktest();

    console.log(`Backtest completed for ${config.strategy.name}: ${(result.total_return * 100).toFixed(2)}% return`);

    return NextResponse.json(result);

  } catch (error) {
    console.error('Backtest error:', error);
    return NextResponse.json(
      { error: 'Failed to run backtest' },
      { status: 500 }
    );
  }
}
