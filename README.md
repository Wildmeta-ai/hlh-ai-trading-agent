# 🤖 HLH AI Trading Agent

AI-powered trading system that combines intelligent strategy generation with real-time trading execution.

## 🚀 Quick Start

### 1. Start Hive Manager (Backend Bot Management)

```bash
cd hivebot/hivebot-manager
npm install
npm run dev
```

**Access:** http://localhost:3000

### 2. Start AI Frontend

```bash
cd ai-trading/frontend

# Configure environment
cp .env.example .env
# Fill in the .env file:
# NEXT_PUBLIC_API_BASE_URL=https://copilot.wildmeta.ai/chatapi/
# NEXT_PUBLIC_BOT_API_BASE_URL=https://copilot.wildmeta.ai/botapi/
# NEXT_PUBLIC_HYPERLIQUID_NETWORK=mainnet

npm install
npm run dev
```

**Access:** http://localhost:3001

> **💡 Recommended:** Use our AI endpoint (configured above). Full backend setup is complex and requires LLM configuration.

**Test wallet:** `0x37a45AdBb275d5d3F8100f4cF16977cd4B0f9Fb7`

---

## 📋 Architecture

```
┌─────────────────────────┐    ┌─────────────────────────┐
│    AI-Trading Core      │    │       Hivebot          │
│  (Strategy Generation)  │    │  (Trading Execution)   │
├─────────────────────────┤    ├─────────────────────────┤
│ • Frontend (Port 3001)  │    │ • Hive Manager (3000)   │
│ • AI Backend (8001)     │◄──►│ • Hummingbot Core       │
│ • Claude LLM Core       │    │ • Strategy Controllers  │
│ • Strategy Templates    │    │ • Risk Management       │
│ • Backtesting Engine    │    │ • Performance Monitor   │
└─────────────────────────┘    └─────────────────────────┘
              │                            │
              └──────────┬─────────────────┘
                         ▼
              ┌─────────────────────────┐
              │   Hyperliquid Exchange  │
              │    (Live Trading)       │
              └─────────────────────────┘
```

---

## 🏗️ Technology Stack

- **Frontend**: Next.js 15, React 19, TailwindCSS
- **Backend**: FastAPI, Claude AI, Hummingbot V2
- **Trading**: Hyperliquid connector, PM2 management
- **Infrastructure**: Multi-strategy execution, risk management

---

## 📊 Strategy Templates

| Strategy | Leverage | Risk/Trade | Best For |
|----------|----------|------------|----------|
| **Conservative Market Maker** | 2x | 1% | Steady income, low risk |
| **Aggressive Scalper** | 5x | 0.5% | High frequency, quick profits |
| **RSI Directional** | 3x | 2% | Technical analysis followers |
| **MACD Trend** | 4x | 1.5% | Trend following traders |

---

## 🚦 Process Management

```bash
# Hivebot Core
pm2 start ecosystem.config.js
pm2 logs hive-orchestrator --nostream
pm2 restart hive-orchestrator

# Hive Manager
cd hivebot/hivebot-manager
./dev-start.sh
./dev-logs.sh
```

---

## 📝 License

Internal Use Only - HLH AI Trading System