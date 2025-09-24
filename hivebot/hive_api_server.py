#!/usr/bin/env python3

"""
Hive API Server - Main coordinator for modular API endpoints.
"""

import logging
from typing import Optional

from aiohttp import web
from aiohttp.web import middleware

from hive_api_strategies import HiveAPIStrategies
from hive_api_positions import HiveAPIPositions
from hive_api_status import HiveAPIStatus


@middleware
async def cors_handler(request, handler):
    """CORS middleware to handle cross-origin requests."""
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        response = web.Response()
    else:
        response = await handler(request)

    # Add CORS headers
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
    response.headers['Access-Control-Max-Age'] = '86400'  # 24 hours

    return response


class HiveAPIServer:
    """REST API server for dynamic strategy management."""

    def __init__(self, hive_core=None):
        """
        Initialize API server.

        Args:
            hive_core: Reference to the main HiveDynamicCore instance
        """
        self.hive_core = hive_core
        self._api_server: Optional[web.Application] = None
        self._api_runner: Optional[web.AppRunner] = None

        # Initialize module handlers
        self.strategies = HiveAPIStrategies(hive_core)
        self.positions = HiveAPIPositions(hive_core)
        self.status = HiveAPIStatus(hive_core)

    async def start_api_server(self, port: int):
        """Start the REST API server."""
        try:
            # Create web application
            self._api_server = web.Application(middlewares=[cors_handler])

            # Register strategy endpoints
            self._api_server.router.add_get('/api/strategies', self.strategies.api_list_strategies)
            self._api_server.router.add_post('/api/strategies', self.strategies.api_create_strategy)
            self._api_server.router.add_put('/api/strategies/{name}', self.strategies.api_update_strategy)
            self._api_server.router.add_delete('/api/strategies/{name}', self.strategies.api_delete_strategy)

            # Register position endpoints
            self._api_server.router.add_get('/api/positions', self.positions.api_get_positions)
            self._api_server.router.add_post('/api/positions/force-sync', self.positions.api_force_position_sync)
            self._api_server.router.add_post('/api/positions/force-close', self.positions.api_force_close_positions)
            self._api_server.router.add_get('/api/positions/debug', self.positions.api_debug_positions)

            # Register status endpoints
            self._api_server.router.add_get('/api/status', self.status.api_hive_status)
            self._api_server.router.add_post('/api/sync-from-postgres', self.status.api_sync_from_postgres)

            # Health check endpoint
            self._api_server.router.add_get('/health', self._health_check)

            # Start server
            self._api_runner = web.AppRunner(self._api_server)
            await self._api_runner.setup()

            site = web.TCPSite(self._api_runner, '0.0.0.0', port)
            await site.start()

            logging.info(f"🌐 Hive API server started on port {port}")
            return True

        except Exception as e:
            logging.error(f"Failed to start API server: {e}")
            return False

    async def stop_api_server(self):
        """Stop the REST API server."""
        try:
            if self._api_runner:
                await self._api_runner.cleanup()
                self._api_runner = None
                self._api_server = None
                logging.info("🌐 Hive API server stopped")
        except Exception as e:
            logging.error(f"Error stopping API server: {e}")

    async def _health_check(self, request):
        """Simple health check endpoint."""
        return web.json_response({
            "status": "healthy",
            "service": "hive-api",
            "hive_core_available": bool(self.hive_core),
            "modules": {
                "strategies": bool(self.strategies),
                "positions": bool(self.positions),
                "status": bool(self.status)
            }
        })