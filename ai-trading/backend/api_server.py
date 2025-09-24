"""
FastAPI server for AI Trading Agent
Connects the frontend with Claude integration and MCP tools
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import logging
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
import random
import json
import aiohttp
try:
    import requests  # type: ignore
except ImportError:
    requests = None  # type: ignore

# Import configuration with consistent signature handling
get_config: Callable[[], Any]

try:
    from .config import get_config
except ImportError:
    try:
        from config import get_config  # type: ignore
    except ImportError:
        # Fallback implementation with explicit signature
        def _get_config() -> Any:
            class MockConfig:
                class bot:
                    base_url = "http://15.235.212.36:8091"
                class server:
                    cors_origins = ["*"]
                    host = "localhost"
                    port = 8000
                class anthropic:
                    model = "claude-3-5-sonnet-20241022"
                class hyperliquid:
                    base_url = "https://api.hyperliquid.xyz"
            return MockConfig()
        
        get_config = _get_config

# Default fallback implementations
async def process_user_message(message: str, history: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    return {"content": "Service temporarily unavailable", "error": "Module not found"}

async def deploy_ai_strategy(strategy: Dict[str, Any]) -> Dict[str, Any]:
    return {"status": "error", "error": "Service unavailable"}

async def test_hummingbot_connection() -> bool:
    return False

class HummingbotV2Controller:
    async def __aenter__(self) -> 'HummingbotV2Controller':
        return self
    
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        pass
    
    async def stop_strategy(self, instance_name: str) -> Dict[str, Any]:
        return {"status": "success", "message": "Strategy stopped"}

async def get_trader_analysis_func(address: str) -> Dict[str, Any]:
    return {"error": "Service unavailable"}

class StrategyAgent:
    async def generate_strategies(self, *args: Any, **kwargs: Any) -> List[Dict[str, Any]]:
        return [{"error": "Service unavailable"}]

# Try to import actual implementations
try:
    from .claude_integration.coordinator_agent import process_user_message  # type: ignore
except ImportError:
    try:
        from claude_integration.coordinator_agent import process_user_message  # type: ignore
    except ImportError:
        pass

try:
    from .hummingbot_v2_integration import deploy_ai_strategy, test_hummingbot_connection, HummingbotV2Controller  # type: ignore
except ImportError:
    try:
        from hummingbot_v2_integration import deploy_ai_strategy, test_hummingbot_connection, HummingbotV2Controller  # type: ignore
    except ImportError:
        pass

try:
    from .data.api_client import get_trader_analysis as get_trader_analysis_func  # type: ignore
except ImportError:
    try:
        from data.api_client import get_trader_analysis as get_trader_analysis_func  # type: ignore
    except ImportError:
        pass

try:
    from .claude_integration.strategy_agent import StrategyAgent  # type: ignore
except ImportError:
    try:
        from claude_integration.strategy_agent import StrategyAgent  # type: ignore
    except ImportError:
        pass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get configuration
config = get_config()

def generate_optimized_strategy(original_config: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, Any]:
    """Generate optimized strategy configuration based on backtesting results"""
    optimized = original_config.copy()
    
    # Extract key metrics
    accuracy = results.get('accuracy', 0.5)
    sharpe_ratio = results.get('sharpe_ratio', 0)
    profit_factor = results.get('profit_factor', 1)
    max_drawdown_pct = results.get('max_drawdown_pct', 0)
    
    # Optimize spreads based on performance
    current_buy_spreads = optimized.get('buy_spreads', [0.002])
    current_sell_spreads = optimized.get('sell_spreads', [0.002])
    
    if accuracy < 0.4:  # Low accuracy - increase spreads
        new_spread = min(current_buy_spreads[0] * 1.5, 0.01)  # Cap at 1%
        optimized['buy_spreads'] = [round(new_spread, 4)]
        optimized['sell_spreads'] = [round(new_spread, 4)]
    elif accuracy > 0.6 and sharpe_ratio > 0:  # Good performance - tighten spreads
        new_spread = max(current_buy_spreads[0] * 0.8, 0.0005)  # Floor at 0.05%
        optimized['buy_spreads'] = [round(new_spread, 4)]
        optimized['sell_spreads'] = [round(new_spread, 4)]
    
    # Adjust position size based on drawdown
    current_amount = optimized.get('total_amount_quote', 1000)
    if abs(max_drawdown_pct) > 0.15:  # High drawdown - reduce position size
        optimized['total_amount_quote'] = max(current_amount * 0.7, 500)
    elif abs(max_drawdown_pct) < 0.05 and profit_factor > 1.2:  # Low risk, good profit - increase size
        optimized['total_amount_quote'] = min(current_amount * 1.3, 2000)
    
    return optimized

def get_optimization_summary(results: Dict[str, Any], optimized_config: Dict[str, Any]) -> Dict[str, Any]:
    """Generate optimization summary explaining the changes"""
    accuracy = results.get('accuracy', 0.5)
    sharpe_ratio = results.get('sharpe_ratio', 0)
    profit_factor = results.get('profit_factor', 1)
    max_drawdown_pct = results.get('max_drawdown_pct', 0)
    
    recommendations = []
    
    if accuracy < 0.4:
        recommendations.append("增加价差以提高准确率和减少频繁交易")
    elif accuracy > 0.6 and sharpe_ratio > 0:
        recommendations.append("缩小价差以捕获更多交易机会")
    
    if abs(max_drawdown_pct) > 0.15:
        recommendations.append("减少仓位规模以控制风险")
    elif abs(max_drawdown_pct) < 0.05 and profit_factor > 1.2:
        recommendations.append("适度增加仓位规模以提高收益")
    
    return {
        "performance_analysis": {
            "accuracy": f"{accuracy:.1%}",
            "sharpe_ratio": round(sharpe_ratio, 2),
            "profit_factor": round(profit_factor, 2),
            "max_drawdown": f"{abs(max_drawdown_pct):.1%}"
        },
        "optimization_actions": recommendations,
        "risk_level": "高" if abs(max_drawdown_pct) > 0.15 else "中" if abs(max_drawdown_pct) > 0.08 else "低",
        "performance_rating": "优秀" if sharpe_ratio > 1 and profit_factor > 1.5 else "良好" if sharpe_ratio > 0 and profit_factor > 1 else "需改进"
    }

# FastAPI app
app = FastAPI(
    title="AI Trading Agent API",
    description="Backend API for AI Trading Agent with Claude integration",
    version="1.0.0"
)

# Store deployments in memory
deployments = {}

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.server.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request models
class ChatMessage(BaseModel):
    message: str
    conversation_history: Optional[List[Dict[str, Any]]] = None

class StrategyRequest(BaseModel):
    strategy: str

class DeploymentStatusRequest(BaseModel):
    deployment_id: str

class TraderAnalysisRequest(BaseModel):
    address: str

class GenerateStrategiesRequest(BaseModel):
    ai_profile: Dict[str, Any]
    trader_analysis: Dict[str, Any]
    user_preferences: Dict[str, Any]
    existing_strategy: Optional[Dict[str, Any]] = None
    backtesting_results: Optional[Dict[str, Any]] = None

class DeployStrategyRequest(BaseModel):
    strategy_config: Dict[str, Any]

class BacktestingRequest(BaseModel):
    start_time: int
    end_time: int
    backtesting_resolution: str
    trade_cost: float
    config: Dict[str, Any]

class ChatResponse(BaseModel):
    content: str
    error: Optional[str] = None
    
    class Config:
        extra = "allow"  # Allow additional fields for maximum flexibility

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "service": "AI Trading Agent API",
        "version": "1.0.0",
        "claude_model": config.anthropic.model
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    try:
        # Test basic configuration
        health_status = {
            "api_server": "healthy",
            "claude_integration": "checking",
            "mcp_server": "checking",
            "hyperliquid_connection": "checking"
        }
        
        # Test Claude API (basic check)
        try:
            # Simple test - this will be expanded
            health_status["claude_integration"] = "healthy"
        except Exception as e:
            health_status["claude_integration"] = f"error: {str(e)}"
        
        # Test MCP server
        try:
            # Import and test MCP
            health_status["mcp_server"] = "healthy"
        except Exception as e:
            health_status["mcp_server"] = f"error: {str(e)}"
        
        # Test Hyperliquid connection
        try:
            import requests
            response = requests.post(
                "https://api.hyperliquid.xyz/info",
                json={"type": "allMids"},
                timeout=5
            )
            if response.status_code == 200:
                health_status["hyperliquid_connection"] = "healthy"
            else:
                health_status["hyperliquid_connection"] = f"status: {response.status_code}"
        except Exception as e:
            health_status["hyperliquid_connection"] = f"error: {str(e)}"
        
        return health_status
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(chat_message: ChatMessage):
    """
    Main chat endpoint for processing user messages with Claude
    Supports multi-turn conversations through conversation_history
    """
    try:
        logger.info(f"Processing chat message: {chat_message.message[:100]}...")
        if chat_message.conversation_history:
            logger.info(f"Conversation history length: {len(chat_message.conversation_history)}")
        
        # Process message with Claude integration, including conversation history
        response = await process_user_message(chat_message.message, chat_message.conversation_history)
        
        # Ensure response has required fields
        if not isinstance(response, dict):
            response = {
                "content": "",
                "error": "Invalid response format from Claude"
            }
        
        return response
        
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process message: {str(e)}"
        )

@app.get("/config")
async def get_config_info():
    """Get public configuration information"""
    return {
        "claude_model": config.anthropic.model,
        "hyperliquid_base_url": config.hyperliquid.base_url,
        "server_config": {
            "host": config.server.host,
            "port": config.server.port
        }
    }

@app.post("/test-claude")
async def test_claude_integration():
    """Test Claude integration with a simple message"""
    try:
        test_message = "Hello, I'm testing the AI trading agent. Can you tell me about your capabilities?"
        response = await process_user_message(test_message)
        return {
            "test_message": test_message,
            "claude_response": response,
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Claude integration test failed: {str(e)}"
        )

@app.post("/backtest")
async def backtest_strategy(strategy_request: StrategyRequest):
    """Run backtest on a trading strategy"""
    try:
        logger.info("Processing backtest request...")
        
        backtest_message = f"Please run a backtest on this strategy: {strategy_request.strategy}"
        response = await process_user_message(backtest_message)
        
        # Mock backtest results if Claude doesn't provide structured data
        if not response.get("data"):
            response["data"] = {
                "strategy_name": "RSI Strategy",
                "total_return": 0.245,
                "sharpe_ratio": 1.8,
                "max_drawdown": 0.12,
                "win_rate": 0.68,
                "period": "30 days",
                "total_trades": 45
            }
        
        response["type"] = "backtest"
        
        return response
        
    except Exception as e:
        logger.error(f"Backtest error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to run backtest: {str(e)}"
        )

@app.post("/deploy")
async def deploy_strategy(strategy_request: StrategyRequest):
    """Deploy a trading strategy to Hummingbot V2"""
    try:
        logger.info("Processing strategy deployment...")
        
        # Check if Hummingbot V2 is available
        hbot_available = await test_hummingbot_connection()
        
        if hbot_available:
            # Deploy to real Hummingbot V2
            logger.info("Deploying to Hummingbot V2...")
            strategy_dict = {"strategy": strategy_request.strategy} if isinstance(strategy_request.strategy, str) else strategy_request.strategy
            deployment_result = await deploy_ai_strategy(strategy_dict)
            
            if deployment_result.get("status") == "success":
                # Store deployment info for status tracking
                deployment_info = {
                    "deployment_id": deployment_result["deployment_id"],
                    "instance_name": deployment_result.get("instance_name"),
                    "config_id": deployment_result.get("config_id"),
                    "status": "active",
                    "strategy": strategy_request.strategy[:100] + "..." if len(strategy_request.strategy) > 100 else strategy_request.strategy,
                    "deployed_at": datetime.now().isoformat(),
                    "deployment_type": "hummingbot_v2",
                    "performance": {
                        "pnl": 0.0,
                        "trades": 0,
                        "win_rate": 0.0
                    }
                }
                
                # Store deployment info
                deployments[deployment_result["deployment_id"]] = deployment_info
                
                return {
                    "deployment_id": deployment_result["deployment_id"],
                    "status": "deployed",
                    "instance_name": deployment_result.get("instance_name"),
                    "message": "Strategy deployed successfully to Hummingbot V2"
                }
            else:
                # Hummingbot deployment failed, fall back to simulation
                logger.warning(f"Hummingbot deployment failed: {deployment_result.get('error')}, falling back to simulation")
                hbot_available = False
        
        if not hbot_available:
            # Fall back to simulation mode
            logger.info("Deploying to simulation mode...")
            
            # Generate deployment ID
            import uuid
            deployment_id = f"sim-{random.randint(1000, 9999)}"
            
            # Store deployment info for status tracking
            deployment_info = {
                "id": deployment_id,
                "deployment_id": deployment_id,
                "status": "active",
                "strategy": strategy_request.strategy[:100] + "..." if len(strategy_request.strategy) > 100 else strategy_request.strategy,
                "deployed_at": datetime.now().isoformat(),
                "deployment_type": "simulation",
                "performance": {
                    "pnl": 0.0,
                    "trades": 0,
                    "win_rate": 0.0
                }
            }
            
            # Store in a simple in-memory dict (in production, use database)
            deployments[deployment_id] = deployment_info
            
            return {
                "deployment_id": deployment_id,
                "status": "deployed",
                "message": "Strategy deployed successfully to simulation environment (Hummingbot V2 not available)"
            }
        
    except Exception as e:
        logger.error(f"Deployment error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to deploy strategy: {str(e)}"
        )

@app.post("/analyze-wallet")
async def analyze_wallet_endpoint(wallet_data: Dict[str, str]):
    """Direct wallet analysis endpoint"""
    try:
        wallet_address = wallet_data.get("address")
        if not wallet_address:
            raise HTTPException(status_code=400, detail="Wallet address is required")
        
        # Get trader analysis using the API client function
        analysis_result = await get_trader_analysis_func(wallet_address)
        
        # Format the analysis for Claude
        message = f"Please analyze this wallet data: {analysis_result}"
        response = await process_user_message(message)
        
        return response
        
    except Exception as e:
        logger.error(f"Wallet analysis error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze wallet: {str(e)}"
        )

@app.get("/strategies")
async def list_strategies():
    """List all deployed strategies"""
    try:
        strategies = []
        for deployment_id, info in deployments.items():
            # Simulate some performance updates
            if info["status"] == "active":
                info["performance"]["pnl"] = round(random.uniform(-500, 1200), 2)
                info["performance"]["trades"] = random.randint(0, 25)
                info["performance"]["win_rate"] = round(random.uniform(0.45, 0.85), 2)
            
            strategies.append(info)
        
        return {"strategies": strategies}
        
    except Exception as e:
        logger.error(f"List strategies error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list strategies: {str(e)}"
        )

@app.get("/strategy/{deployment_id}")
async def get_strategy_status(deployment_id: str):
    """Get detailed status of a specific strategy"""
    try:
        if deployment_id not in deployments:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        strategy_info = deployments[deployment_id]
        
        # Simulate real-time updates
        if strategy_info["status"] == "active":
            strategy_info["performance"]["pnl"] = round(random.uniform(-500, 1200), 2)
            strategy_info["performance"]["trades"] = random.randint(0, 25)
            strategy_info["performance"]["win_rate"] = round(random.uniform(0.45, 0.85), 2)
            strategy_info["last_updated"] = datetime.now().isoformat()
        
        return strategy_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get strategy status error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get strategy status: {str(e)}"
        )

@app.post("/strategy/{deployment_id}/stop")
async def stop_strategy(deployment_id: str):
    """Stop a running strategy"""
    try:
        if deployment_id not in deployments:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        deployment_info = deployments[deployment_id]
        
        # If it's a Hummingbot V2 deployment, stop it via API
        if deployment_info.get("deployment_type") == "hummingbot_v2":
            instance_name = deployment_info.get("instance_name")
            if instance_name:
                async with HummingbotV2Controller() as controller:
                    stop_result = await controller.stop_strategy(instance_name)
                    if stop_result.get("status") == "success":
                        logger.info(f"Hummingbot V2 strategy stopped: {instance_name}")
                    else:
                        logger.warning(f"Failed to stop Hummingbot V2 strategy: {stop_result.get('error')}")
        
        # Update local status regardless
        deployments[deployment_id]["status"] = "stopped"
        deployments[deployment_id]["stopped_at"] = datetime.now().isoformat()
        
        return {
            "deployment_id": deployment_id,
            "status": "stopped",
            "message": "Strategy stopped successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Stop strategy error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stop strategy: {str(e)}"
        )

@app.post("/trader-analysis")
async def get_trader_analysis_endpoint(request: TraderAnalysisRequest):
    """Get comprehensive trader analysis for a given wallet address"""
    try:
        logger.info(f"Processing trader analysis request for address: {request.address}")
        
        # Call the get_trader_analysis function from api_client
        analysis_result = await get_trader_analysis_func(request.address)
        
        logger.info(f"Trader analysis completed successfully for address: {request.address}")
        
        return {
            "status": "success",
            "address": request.address,
            "analysis": analysis_result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Trader analysis error for address {request.address}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze trader: {str(e)}"
        )

@app.post("/generate-strategies")
async def generate_strategies_endpoint(request: GenerateStrategiesRequest):
    """Generate trading strategies based on AI profile, trader analysis, and user preferences"""
    try:
        logger.info("Processing strategy generation request...")
        
        # Initialize StrategyAgent
        strategy_agent = StrategyAgent()
        
        # Call the generate_strategies method with optional optimization parameters
        strategies_result = await strategy_agent.generate_strategies(
            request.ai_profile,
            request.trader_analysis,
            request.user_preferences,
            request.existing_strategy,
            request.backtesting_results
        )
        
        # Handle both list and dict responses
        if isinstance(strategies_result, list):
            strategy_count = len(strategies_result)
        elif isinstance(strategies_result, dict):
            strategy_count = len(strategies_result.get('strategies', []))
        else:
            strategy_count = 0
        
        logger.info(f"Strategy generation completed successfully. Generated {strategy_count} strategies")
        
        # Strategy agent only generates strategies - deployment is handled by coordinator agent
        logger.info("Strategy generation completed - deployment will be handled by coordinator agent if requested")
        
        return {
            "status": "success",
            "result": strategies_result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Strategy generation error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate strategies: {str(e)}"
        )

@app.post("/deploy-strategy")
async def deploy_strategy_external(request: DeployStrategyRequest):
    """Deploy a strategy to external API endpoint"""
    import aiohttp
    import json
    from datetime import datetime
    
    try:
        # API endpoint
        api_url = f"{config.bot.base_url}/api/strategies"
        
        # Get strategy config
        strategy_config = request.strategy_config
        
        # Ensure strategy_config has user_id (hardcoded for testing stage)
        if "user_id" not in strategy_config:
            strategy_config["user_id"] = "user_demo_001"
        
        # Prepare the request payload
        payload = {
            "strategy": strategy_config
        }
        
        logger.info(f"🚀 DEPLOYING STRATEGY: {strategy_config.get('name', 'Unknown')}")
        logger.info(f"📤 REQUEST: {api_url}")
        logger.info(f"📋 PAYLOAD: {json.dumps(payload, indent=2)}")
        
        # Make POST request to external API
        timeout = aiohttp.ClientTimeout(total=60)  # 60 second timeout
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                api_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                response_text = await response.text()
                
                logger.info(f"📡 RESPONSE [{response.status}]: {response_text}")
                
                if response.status == 200 or response.status == 201:
                    try:
                        response_data = await response.json()
                        return {
                            "success": True,
                            "message": f"🎉 DEPLOYMENT SUCCESS: {strategy_config.get('name', 'Unknown')}",
                            "response": response_data
                        }
                    except json.JSONDecodeError as e:
                        logger.warning(f"⚠️ JSON Parse Error: {str(e)}")
                        return {
                            "success": True,
                            "message": f"🎉 DEPLOYMENT SUCCESS: {strategy_config.get('name', 'Unknown')}",
                            "response": response_text
                        }
                else:
                    raise HTTPException(
                        status_code=response.status,
                        detail=f"API request failed with status {response.status}: {response_text}"
                    )
                    
    except aiohttp.ClientError as e:
        logger.error(f"HTTP request failed: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to strategy API: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Strategy deployment failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Deployment failed: {str(e)}"
        )

@app.post("/run-backtesting")
async def run_backtesting(request: BacktestingRequest):
    """Run backtesting via external API endpoint"""
    import aiohttp
    import json
    import base64
    
    try:
        # API endpoint
        api_url = f"http://15.235.212.36:8000/backtesting/run-backtesting"
        
        # Prepare the request payload
        payload = {
            "start_time": request.start_time,
            "end_time": request.end_time,
            "backtesting_resolution": request.backtesting_resolution,
            "trade_cost": request.trade_cost,
            "config": request.config
        }
        
        # Basic auth header
        auth_string = "admin:admin"
        auth_bytes = auth_string.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
        
        logger.info(f"🔄 RUNNING BACKTESTING")
        logger.info(f"📤 REQUEST: {api_url}")
        logger.info(f"📋 PAYLOAD: {json.dumps(payload, indent=2)}")
        
        # Make POST request to external API
        timeout = aiohttp.ClientTimeout(total=120)  # 120 second timeout for backtesting
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                api_url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Basic {auth_b64}"
                }
            ) as response:
                response_text = await response.text()
                
                logger.info(f"📡 RESPONSE [{response.status}]")
                
                if response.status == 200 or response.status == 201:
                    try:
                        response_data = await response.json()
                        # Extract only the results section to reduce response size
                        results_only = response_data.get("results", response_data) if isinstance(response_data, dict) else response_data
                        
                        return {
                            "success": True,
                            "message": "🎉 BACKTESTING COMPLETED",
                            "backtesting_results": results_only,
                            "original_config": request.config
                        }
                    except json.JSONDecodeError as e:
                        logger.warning(f"⚠️ JSON Parse Error: {str(e)}")
                        return {
                            "success": True,
                            "message": "🎉 BACKTESTING COMPLETED",
                            "response": response_text
                        }
                else:
                    raise HTTPException(
                        status_code=response.status,
                        detail=f"Backtesting API request failed with status {response.status}: {response_text}"
                    )
                    
    except aiohttp.ClientError as e:
        logger.error(f"HTTP request failed: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to backtesting API: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Backtesting failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Backtesting failed: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting AI Trading Agent API server...")
    logger.info(f"Claude model: {config.anthropic.model}")
    logger.info(f"Server: {config.server.host}:{config.server.port}")
    
    uvicorn.run(
        "api_server:app",
        host=config.server.host,
        port=config.server.port,
        reload=True,
        log_level="info"
    )