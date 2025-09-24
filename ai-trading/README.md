# AI Trading Agent - Minimal Viable Product

A comprehensive AI trading agent that analyzes trader behavior and generates customized Hyperliquid perpetual trading strategies.

## 🏗️ Architecture

The system follows a 4-layer architecture:

### 1. Data Layer (`backend/data/`)
- Fetches trader analysis from three APIs:
  - TradeStory: `https://test-dex-api.heima.network/ai-analyze/tradestory/{address}`
  - TechnicalMetrics: `https://test-dex-api.heima.network/ai-analyze/analyze/{address}`
  - AI Profile: `https://test-dex-api.heima.network/ai-analyze/profile/{address}`

### 2. AI Agent Processing (`backend/ai-agent/`)
- **Strategy Templates**: 4 specialized templates for different trading styles
  - Conservative Market Maker: Low leverage, wide spreads
  - Aggressive Scalper: High frequency, tight spreads  
  - RSI Directional: Technical trend following
  - MACD Trend: Multi-timeframe positioning
- **AI Processor**: Analyzes trader behavior and customizes strategies

### 3. MCP Server (`backend/mcp-server/`)
- **Hyperliquid Connector**: Direct API integration with fallback to mock
- **Strategy Management**: Configuration generation, deployment, monitoring
- **Risk Controls**: Backtest, performance monitoring, emergency stops

### 4. Frontend Interface (`frontend/`)
- Next.js chatbox with dark theme
- JSON response styling for strategies, profiles, and backtests
- Real-time strategy visualization and controls

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- Node.js 18+
- npm or yarn

### Complete Setup & Demo

#### 1. Clone and Navigate to Project
```bash
cd ai-trading
```

#### 2. Backend Setup (Python)
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the Claude integration server
python start_server.py
```

**Server will be available at:** http://localhost:8000

**Test the integration:**
```bash
# Test health endpoint
curl http://localhost:8000/health

# Test Claude integration
curl -X POST http://localhost:8000/test-claude
```

**Expected Output:**
```
🔍 Testing Hyperliquid API connectivity...
✅ Hyperliquid API accessible - 403 markets available

🚀 AI Trading Agent - Minimal Viable Product
==================================================

1. Initializing MCP Server...
✅ MCP Server initialized successfully

2. Fetching trader analysis for 0x37a45AdBb275d5d3F8100f4cF16977cd4B0f9Fb7...
✅ Trader analysis data fetched

3. Processing trader data and generating strategies...
✅ Strategies generated successfully

🧠 Trader Profile: Leverage Lunatic
📊 Behavior Analysis: Risk Level: high, Win Rate: 64.0%
🎯 Generated Strategies (2): Aggressive Scalper, MACD Trend
🎉 AI Trading Agent MVP completed successfully!
```

#### 3. Frontend Setup (Next.js)
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

**Frontend will be available at:** http://localhost:3001 (or 3000 if available)

#### 4. Testing the Complete System

**Backend Test:**
- ✅ Hyperliquid API connectivity
- ✅ Trader analysis processing
- ✅ Strategy generation
- ✅ MCP server functions
- ✅ Backtest simulation

**Frontend Test:**
1. Open http://localhost:3001
2. Enter test wallet: `0x37a45AdBb275d5d3F8100f4cF16977cd4B0f9Fb7`
3. View AI-generated trader profile
4. See personalized strategies with backtest options
5. Test strategy deployment simulation

### 🎯 Demo Wallet
Use this wallet address for testing:
```
0x37a45AdBb275d5d3F8100f4cF16977cd4B0f9Fb7
```

### 📱 Usage Examples

**In the frontend chatbox, try:**
- `0x37a45AdBb275d5d3F8100f4cF16977cd4B0f9Fb7` - Analyze trader
- `backtest the aggressive scalper strategy` - Run backtest
- `show me conservative strategies` - Get different strategy types

## 🧪 Testing

### Test with Example Wallet
Use the provided test wallet address:
```
0x37a45AdBb275d5d3F8100f4cF16977cd4B0f9Fb7
```

### Expected Flow
1. Enter wallet address in the chatbox
2. AI analyzes trader profile and generates strategies
3. View customized strategy configurations
4. Test backtest functionality
5. Deploy strategies (simulated)

## 📊 Features Implemented

✅ **Data Layer**
- API client with trader analysis fetching
- Optimized token usage (excludes tradeAction field)
- Error handling and fallback mechanisms

✅ **AI Agent**
- Behavioral analysis from trader profiles
- Strategy customization based on risk tolerance
- 4 template strategies with parameter tuning

✅ **MCP Server**
- Hyperliquid API integration with mock fallback
- Strategy configuration generation
- Backtest simulation with performance metrics
- Risk control parameter management

✅ **Frontend**
- Dark-themed chatbox interface
- JSON response styling for different data types
- Real-time strategy visualization
- Backtest chart display

## 🎯 Strategy Templates

### 1. Conservative Market Maker
- **Leverage**: 2x
- **Spreads**: 0.2% bid/ask
- **Risk**: 1% per trade
- **Best for**: Low-risk, steady income traders

### 2. Aggressive Scalper  
- **Leverage**: 5x
- **Spreads**: 0.05% bid/ask
- **Risk**: 0.5% per trade
- **Best for**: High-frequency, quick profit traders

### 3. RSI Directional
- **Leverage**: 3x
- **Strategy**: RSI overbought/oversold signals
- **Risk**: 2% per trade
- **Best for**: Technical analysis followers

### 4. MACD Trend
- **Leverage**: 4x
- **Strategy**: MACD crossover signals
- **Risk**: 1.5% per trade
- **Best for**: Trend following traders

## 🔧 Configuration

### Hyperliquid API
The system uses these credentials for testing:
- **Wallet**: `0x2eC15793D6171c1815B006e3D027f92F7E57B36F`
- **API Key**: `0x3e1327394da35a1ff08485d4c4d810dc8d385833ed8b595a11b4f81837780e11`

### Design Colors
- **Dominant**: `#AEFEC3`, `#91F4B5`, `#FEE45D`, `#FFFF49`
- **Dark**: `#DA373B`
- **Light**: `#FFFFFF`
- **Font**: Poppins

## 🚧 Limitations & Next Steps

### Current Limitations
- Mock backtesting (not real historical data)
- Simulated strategy deployment
- Limited Hummingbot V2 integration
- Basic risk management

### Production Readiness Tasks
- [ ] Implement real backtesting engine
- [ ] Integrate with actual Hummingbot V2 controller
- [ ] Add comprehensive risk management
- [ ] Implement live trading monitoring
- [ ] Add user authentication and portfolio management

## 📝 API Endpoints

### Data Layer
- `GET /ai-analyze/tradestory/{address}` - Trading stories
- `GET /ai-analyze/analyze/{address}` - Technical metrics  
- `GET /ai-analyze/profile/{address}` - AI profile analysis

### MCP Functions
- `profile_info(address)` - Get trading profile
- `generate_config(strategy)` - Generate Hummingbot config
- `backtest_strategy(config, start, end)` - Run backtest
- `deploy_strategy(config_id)` - Deploy strategy
- `monitor_performance(deployment_id)` - Monitor performance

## 🎉 Demo Results

The system successfully:
1. ✅ Fetches and analyzes trader data
2. ✅ Generates personalized strategies
3. ✅ Creates Hummingbot-compatible configurations
4. ✅ Simulates backtesting with realistic metrics
5. ✅ Provides risk warnings and recommendations
6. ✅ Displays results in an intuitive chat interface

Perfect for testing the complete AI trading workflow before production deployment!