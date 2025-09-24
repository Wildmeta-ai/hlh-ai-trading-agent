# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## HIVE PROJECT STATUS

### Current Project: Hivebot
**Goal**: Transform Hummingbot from 1:1 (one container per strategy) to 1:N architecture (one container running N strategies)

### Project Progress
- **Phase 1**: ✅ Multi-strategy architecture with simulated data (COMPLETED)
- **Phase 2**: ✅ Real Hummingbot integration (COMPLETED)
  - ✅ Real HyperliquidPerpetualDerivative connector integrated
  - ✅ Real strategy instances (PureMarketMaking, Avellaneda, Cross-exchange)
  - ✅ Real order objects and event system integration
  - ✅ Universal strategy factory supporting all strategy parameters
  - ✅ Comprehensive risk management and portfolio monitoring
- **Phase 3**: ✅ Full strategy compatibility (COMPLETED)
  - ✅ Support for all relevant Hummingbot strategy types on Hyperliquid
  - ✅ Universal configuration schema with 30+ parameters
  - ✅ Enterprise-grade risk management and monitoring

### Main Business Entry Point ✅ CONSOLIDATED
**IMPORTANT**: We have ONE consolidated main entry point:
- **`hive_dynamic_core_modular.py`** - Main Hivebot system (orchestrator/entry script) with:
  - ✅ Task 1: Real HyperliquidExchange connector integrated
  - ✅ Task 2: Real PureMarketMakingStrategy instances integrated
  - ✅ Multi-strategy support (1:N architecture)
  - ✅ Database-driven strategy management (SQLite)
  - ✅ Hot-add/remove strategies while running
  - ✅ REST API for dynamic control (port 8080)
  - ✅ Real-time monitoring interface
  - ✅ Real market data: PURR-USDC from Hyperliquid testnet
  - ✅ Consolidated: All useful patterns from test scripts moved here

### CONSOLIDATION COMPLETE ✅
All test/verification scripts have been cleaned up. Useful patterns consolidated into main entry point:
- `RealStrategyInstance` class for real Hummingbot strategy management
- Real connector initialization and market data integration
- Performance metrics and active order tracking
- Database persistence and dynamic strategy management

### CRITICAL NOTE FOR AI
- ❌ Verification scripts working ≠ Task completion
- ✅ Only business entry point integration = Task completion
- ❌ Do NOT create multiple entry points or test scripts
- ✅ Use business entry point for testing real functionality
- ❌ Unit tests ≠ Integration complete
- ✅ Real business code working = Success
- ✅ Consolidation complete - all useful code moved to main entry point

## Development Commands

### Environment Setup
- `./install` - Install Hummingbot with conda environment setup (use `./install --dydx` for dYdX support)
- `source "${CONDA_BIN}/activate" hummingbot` - Activate the hummingbot conda environment

### Building and Compilation
- `./compile` - Compile Cython extensions (runs `python setup.py build_ext --inplace`)
- `make build` - Same as `./compile`
- `./clean` - Clean all compiled files and build artifacts
- `make clean` - Same as `./clean`

### Testing
- `make test` - Run test suite with coverage (excludes broken/problematic tests)
- `make run_coverage` - Run tests and generate coverage report
- `make report_coverage` - Generate coverage report from existing test run
- `make development-diff-cover` - Generate diff coverage report against development branch
- Tests require minimum 80% coverage for pull requests

### Docker
- `docker compose up -d` - Launch Hummingbot in Docker
- `docker attach hummingbot` - Attach to running Hummingbot Docker container
- `make docker` - Build Docker image

### V2 Strategy Development
- `make run-v2` - Quick start for V2 strategies using controllers framework

## Process Management with PM2

### PM2 Setup ✅ CONFIGURED
The main Hive entry script is managed using PM2 for better process control and monitoring:

**Configuration Files:**
- `ecosystem.config.js` - PM2 configuration for hive-orchestrator process
- Logs stored in `./logs/` directory

**PM2 Commands:**
```bash
# Process Control
pm2 start ecosystem.config.js    # Start hive orchestrator
pm2 restart hive-orchestrator     # Restart the orchestrator
pm2 stop hive-orchestrator        # Stop the orchestrator
pm2 delete hive-orchestrator      # Remove from PM2

# Monitoring
pm2 list                          # Show all PM2 processes
pm2 show hive-orchestrator        # Detailed process info
pm2 monit                         # Real-time monitoring dashboard

# Logs
pm2 logs hive-orchestrator        # Live tail logs
pm2 logs hive-orchestrator --lines 50  # Last 50 lines
pm2 flush                         # Clear all logs

# Persistence
pm2 save                          # Save current process list
pm2 resurrect                     # Restore saved processes
```

**Benefits:**
- Automatic restarts on crashes
- Structured logging with timestamps
- Memory usage monitoring and limits
- Easy process control for both user and AI assistant
- Proper conda environment activation

### Terminology Note
- **"Orchestrator"** = Main entry script (`hive_dynamic_core_modular.py`)
- **"Entry Script"** = Same thing, different naming preference
- Both terms refer to the central coordinator process that runs multiple strategies

## Code Architecture

### Core Structure
Hummingbot is organized into several key architectural layers:

**Client Layer (`hummingbot/client/`)**
- CLI interface with command handling and user interaction
- Configuration management and strategy initialization
- Application lifecycle and platform abstraction

**Strategy Layer (`hummingbot/strategy/` and `hummingbot/strategy_v2/`)**
- **V1 Strategies**: Traditional strategy framework with Cython-optimized components
- **V2 Strategies**: Modern framework using controllers, executors, and runnable components
- Controllers handle market making, directional trading, and generic strategies
- Executors manage order lifecycle and position management

**Connector Layer (`hummingbot/connector/`)**
- Exchange connectors for CEX (centralized) and DEX (decentralized) trading
- Gateway integration for AMM/DEX connectivity
- Derivative and spot market support
- Standardized REST/WebSocket API interfaces

**Core Infrastructure (`hummingbot/core/`)**
- Event system for component communication
- Clock and time management with real-time and backtesting support
- Data types for orders, trades, and market data
- Network handling and rate limiting

### Exchange Integration
Three main connector categories:
- **CLOB CEX**: Centralized exchanges (Binance, OKX, KuCoin, etc.)
- **CLOB DEX**: Decentralized order book exchanges (dYdX, Hyperliquid, Injective)
- **AMM DEX**: Automated market makers via Gateway (Uniswap, Curve, etc.)

### Strategy Development Patterns
- **V1**: Inherit from `StrategyBase` (Cython-optimized, complex setup)
- **V2**: Use controller-executor pattern with `RunnableBase` components
- Scripts: Simple Python files in `/scripts` for custom logic
- Controllers: Higher-level strategy coordination in `/controllers`

### Data Pipeline
- Market data flows through order book trackers and data feeds
- Events propagate through the event system to strategies and UI
- Configuration managed through Pydantic models and YAML files
- Database integration for trade history and performance tracking

## Development Guidelines

### File Organization
- Configuration files: `/conf` directory
- Strategy templates: `/hummingbot/templates`
- Custom strategies: `/strategies` or `/scripts` directories
- Controllers: `/controllers` directory

### Code Style and Testing
- Follow existing patterns in similar components
- Black formatting (120 character line length)
- isort for import organization
- Pre-commit hooks enforce code quality
- Minimum 80% test coverage required for PRs

### Branch and PR Workflow
- Create feature branches from `development` branch
- Use conventional commit prefixes: `(feat)`, `(fix)`, `(refactor)`, `(doc)`
- Rebase against upstream development before submitting PRs
- Enable "Allow edits by maintainers" on PRs

### Connector Development
- Follow standardized patterns in existing connectors
- Implement required abstract methods from base classes
- Add comprehensive test coverage
- Consider rate limits and WebSocket handling

### V2 Strategy Development
- Prefer V2 framework for new strategies
- Use controllers for high-level coordination
- Implement executors for specific trading actions
- Leverage the runnable component lifecycle

This codebase uses significant Cython optimization for performance-critical components, particularly in the core data structures and V1 strategy framework. The V2 architecture represents a more modern, Python-native approach that's easier to develop and maintain.
- remember: doing mock data or fake logic is strictly prohibited
