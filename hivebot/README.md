# 🐝 HiveBot - Multi-Strategy Hummingbot Extension

**High-performance modification of Hummingbot enabling multiple trading strategies to run in a single container with shared resources.**

---

## 🎯 Project Overview

HiveBot extends the official [Hummingbot](https://github.com/hummingbot/hummingbot) framework to support **multi-strategy execution** with **shared network resources**. Instead of running N containers for N strategies, HiveBot runs **1 container for N strategies** with multiplexed WebSocket connections and coordinated resource management.

### Current Architecture (Hummingbot)
```
Strategy 1 → Container 1 → Exchange Connection 1
Strategy 2 → Container 2 → Exchange Connection 2  
Strategy N → Container N → Exchange Connection N
```

### HiveBot Architecture (Target)
```
[Strategy 1, Strategy 2, ..., Strategy N] → Single Container → Shared Exchange Connections
```

## 🚀 Phase 1: Flow Verification ✅ COMPLETE

**Objective**: Verify the complete data flow is ready for multi-strategy modifications.

### ✅ Accomplishments

**Environment & Infrastructure**:
- ✅ Development environment setup with conda + Cython compilation
- ✅ Hyperliquid testnet integration and testing  
- ✅ Real market data connection verification
- ✅ Official Hummingbot production approach analysis

**Flow Verification**:
- ✅ **Real data flow proven**: Hyperliquid testnet → Hummingbot → Strategy → Actions
- ✅ **Aggressive test strategy**: `hyper_test_strategy.yml` with 1bp spreads, 1s refresh
- ✅ **Live market testing**: ETH $4418-$4421 price range with real market movements
- ✅ **Performance metrics**: 20 market updates → 20 strategy triggers → 140 actions

**Architecture Foundation**:
- ✅ **Extension framework**: `bin/hive_quickstart.py` extends official `hummingbot_quickstart.py`  
- ✅ **Production compatibility**: Uses same Docker deployment patterns
- ✅ **Multi-strategy CLI**: `--hive-strategies` flag for comma-separated strategy configs

### 📁 Key Files

| File | Purpose | Status |
|------|---------|--------|
| `simple_connector_test.py` | **Final working test** - Proves real market data flow | ✅ Working |
| `conf/strategies/hyper_test_strategy.yml` | Aggressive test strategy configuration | ✅ Working |  
| `bin/hive_quickstart.py` | Multi-strategy extension of official quickstart | ✅ Complete |
| `HIVE_PROJECT_PLAN.md` | Complete architecture transformation plan | ✅ Current |

### 🧪 Testing the Flow

**Quick verification** (uses real Hyperliquid testnet data):
```bash
source /Users/yoshiyuki/miniconda3/bin/activate hummingbot
python simple_connector_test.py
```

**Expected output**: Real ETH prices, strategy trigger analysis, action simulation

## 📈 Verification Results

**Real Market Data Integration**:
- **API Endpoint**: `https://api.hyperliquid-testnet.xyz/info` (same as production)
- **Market Updates**: 20 updates in 60 seconds with live ETH price movements
- **Strategy Response**: 7 actions per update (1 cancellation + 6 orders across 3 levels)
- **Price Analysis**: ETH $4418.30 → $4421.95 with varying spreads

**Key Insights**:
- ✅ **Data Flow Works**: Market data correctly triggers strategy decisions
- ✅ **Real Integration**: Uses same API calls as production Hummingbot connector
- ✅ **Aggressive Parameters**: 1 basis point spreads create immediate market orders
- ✅ **Foundation Ready**: Current 1:1 flow proven, ready for 1:N transformation

## 🛠 Development Setup

**Prerequisites**:
```bash
# Install Hummingbot environment
./install

# Activate environment  
source /Users/yoshiyuki/miniconda3/bin/activate hummingbot

# Compile Cython extensions
./compile
```

**Testing**:
```bash
# Verify environment
python simple_connector_test.py

# Test multi-strategy extension (when ready)
./bin/hive_quickstart.py --hive-strategies "strategy1.yml,strategy2.yml"
```

## 🗺 Roadmap

### ✅ Phase 1: Flow Verification (Complete)
- Environment setup and real data integration
- Complete flow verification with aggressive test strategy
- Foundation architecture for multi-strategy support

### 🔄 Phase 2: Multi-Strategy Core (Next)
- **WebSocket Multiplexing**: Share connections across strategies
- **Clock System Modification**: Support multiple TimeIterator instances
- **Strategy Scheduler**: Coordinate execution across multiple strategies  
- **Resource Management**: Shared memory and network resources

### 🎯 Phase 3: Production Ready
- **Load Testing**: Multiple strategies under realistic market conditions
- **Performance Optimization**: Latency and memory optimization
- **Production Deployment**: Docker integration and monitoring

## 📊 Architecture Components

### Current Focus Areas
- **`hummingbot/core/clock.pyx`**: Timing system requiring 1:N support
- **`hummingbot/strategy/strategy_base.py`**: Strategy instances needing coordination  
- **`hummingbot/connector/`**: Network layer requiring multiplexing
- **`bin/hummingbot_quickstart.py`**: Production entry point for extension

### Target Modifications
- **WebSocket Multiplexing Service**: Single connection → Multiple strategies
- **Multi-Strategy Scheduler**: Fair resource allocation across strategies
- **Shared Context System**: Cross-strategy state and resource management
- **Enhanced Clock System**: Support multiple concurrent TimeIterator instances

---

## 🔗 Links

- **Base Project**: [Official Hummingbot](https://github.com/hummingbot/hummingbot)
- **Documentation**: [Hummingbot Docs](https://hummingbot.org)
- **Community**: [Discord](https://discord.gg/hummingbot)

---

*Based on Hummingbot open-source framework under Apache 2.0 license*