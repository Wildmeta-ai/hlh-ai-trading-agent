# 🐝 Hivebot Manager

A Next.js web application for managing Hive trading strategies, validation, backtesting, and bot monitoring.

## Features

- **📊 Strategy Validation** - Parameter validation with business logic checks
- **🤖 Bot Instance Registry** - Real-time bot monitoring and management
- **📈 Backtesting Engine** - Historical strategy performance simulation
- **🌐 Web Dashboard** - Interactive interface for all management tasks
- **🔗 REST API** - Full API for integration with trading systems

## Quick Start

### Local Development

```bash
# Start development server with PM2
./dev-start.sh

# View logs
./dev-logs.sh

# Restart server
./dev-restart.sh

# Stop server
./dev-stop.sh
```

Access the application at: **http://localhost:3000**

### Production Deployment

```bash
# Deploy to production server
./deploy.sh [server_ip] [server_user]
```

## API Endpoints

### Bot Management
- `GET /api/bots` - List all registered bot instances
- `GET /api/bots?format=metrics` - Get dashboard metrics
- `POST /api/bots` - Register/update bot instance
- `PUT /api/bots/[id]` - Update specific bot
- `DELETE /api/bots/[id]` - Remove bot instance

### Strategy Validation
- `POST /api/strategies/validate` - Validate strategy configuration
- `POST /api/strategies/backtest` - Run strategy backtest

## Development

### Project Structure

```
src/
├── app/
│   ├── api/                 # API routes
│   │   ├── bots/           # Bot management endpoints
│   │   └── strategies/     # Strategy validation endpoints
│   ├── dashboard/          # Dashboard page
│   └── layout.tsx          # Root layout
├── components/             # React components
├── lib/                    # Utilities
└── types/                  # TypeScript definitions
```

### Technology Stack

- **Frontend**: Next.js 15, React 19, TailwindCSS
- **Backend**: Next.js API routes
- **Validation**: Zod schemas
- **Process Management**: PM2
- **Deployment**: Nginx reverse proxy

### Configuration

- **Local Dev**: Port 3000
- **Production**: Port 3002 (internal) → Port 8091 (public)

## Integration with Hive Trading Core

The Hivebot Manager integrates with the main Hive trading system:

1. **Strategy Validation** - Validates configs before sending to `hive_orchestrator.py`
2. **Bot Monitoring** - Tracks multiple Hive instances across servers
3. **Performance Analysis** - Provides backtesting before live deployment
4. **Centralized Management** - Single dashboard for all trading operations

## PM2 Management

### Local Development
```bash
pm2 status hivebot-manager-dev
pm2 logs hivebot-manager-dev
pm2 restart hivebot-manager-dev
pm2 monit
```

### Production
```bash
pm2 status hivebot-manager
pm2 logs hivebot-manager
pm2 restart hivebot-manager
```

## Environment Variables

- `NODE_ENV` - Environment (development/production)
- `PORT` - Application port (default: 3000 dev, 3002 prod)

## License

Part of the Hive Trading System - Internal Use Only
