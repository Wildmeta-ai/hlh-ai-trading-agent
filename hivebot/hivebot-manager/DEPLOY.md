# Deployment Guide

Three deployment options for different scenarios:

## 🚀 Initial Setup
```bash
./deploy.sh
```
- Full server setup with nginx, PM2, dependencies
- Use this for first-time deployment or major changes

## ⚡ Quick Updates
```bash
./quick-deploy.sh
```
- Fast deployment for regular updates
- Intelligent dependency detection
- Skips unchanged files
- **Recommended for most updates**

## 🔥 Development Sync
```bash
./dev-deploy.sh
```
- Ultra-fast source code sync only
- Perfect for rapid development iterations
- Only syncs `src/` directory

## Current Status
- **Server**: 15.235.212.36:8091
- **Dashboard**: http://15.235.212.36:8091/dashboard
- **API**: http://15.235.212.36:8091/api/bots

## Server Commands
```bash
# Check status
ssh ubuntu@15.235.212.36 'pm2 status'

# View logs
ssh ubuntu@15.235.212.36 'pm2 logs hivebot-manager'

# Quick restart
ssh ubuntu@15.235.212.36 'pm2 reload hivebot-manager'
```
