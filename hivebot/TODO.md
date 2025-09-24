# Hive Trading Core - TODO List

## 🚨 CRITICAL
- [x] **Strategy validation、routing& backtesting** - Parameter validation, basic backtesting
- [ ] **Move SQLite → PostgreSQL** - Simple direct connections (no pooling)

## ✅ CONFIRMED TODOS
- [ ] **Accounting system** - Commission tracking per strategy/trade
- [ ] **Real-time notifications** - Trade event webhooks (maybe)
- [ ] **Trading history & analytics** - Persistent trade data (maybe)
- [ ] **Monitoring & alerting** - System health, structured alerts
## ❌ NOT NEEDED
- User management (external system handles this)
- AI interface (external system handles this)
- Wallet management (strategies contain user info)
- Risk overrides (strategies define their own risk)
- Multi-exchange (Hyperliquid only is good)
- Compliance features
- Mobile APIs

---
*Focus: Build efficient trading execution engine, not SaaS platform*
