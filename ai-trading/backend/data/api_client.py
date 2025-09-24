"""
Data layer for fetching trader analysis from APIs
"""
import aiohttp
import asyncio
from typing import Dict, Any, Optional
import json
import logging

logger = logging.getLogger(__name__)

class TraderAnalysisClient:
    """Client for fetching trader analysis data from the APIs"""
    
    def __init__(self, base_url: str = "https://test-dex-api.heima.network"):
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def fetch_trade_story(self, address: str) -> Dict[str, Any]:
        """
        Fetch trade story data for a given address
        Excludes tradeAction field to optimize token usage
        """
        url = f"{self.base_url}/ai-analyze/tradestory/{address}"
        
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    # Remove tradeAction field to reduce token usage
                    if isinstance(data, list):
                        for story in data:
                            if 'trade_action' in story:
                                del story['trade_action']
                    elif isinstance(data, dict) and 'trade_action' in data:
                        del data['trade_action']
                    return data
                else:
                    logger.error(f"Failed to fetch trade story: {response.status}")
                    return {}
        except Exception as e:
            logger.error(f"Error fetching trade story: {e}")
            return {}
    
    async def fetch_technical_metrics(self, address: str) -> Dict[str, Any]:
        """Fetch technical metrics for a given address"""
        url = f"{self.base_url}/ai-analyze/analyze/{address}"
        
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Failed to fetch technical metrics: {response.status}")
                    return {}
        except Exception as e:
            logger.error(f"Error fetching technical metrics: {e}")
            return {}
    
    async def fetch_ai_profile(self, address: str) -> Dict[str, Any]:
        """Fetch AI profile analysis for a given address"""
        url = f"{self.base_url}/ai-analyze/profile/{address}"
        
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Failed to fetch AI profile: {response.status}")
                    return {}
        except Exception as e:
            logger.error(f"Error fetching AI profile: {e}")
            return {}
    
    async def fetch_complete_analysis(self, address: str) -> Dict[str, Any]:
        """Fetch all analysis data for a given address"""
        tasks = [
            self.fetch_trade_story(address),
            self.fetch_technical_metrics(address),
            self.fetch_ai_profile(address)
        ]
        
        try:
            trade_story, technical_metrics, ai_profile = await asyncio.gather(*tasks)
            
            return {
                "address": address,
                "trade_story": trade_story,
                "technical_metrics": technical_metrics,
                "ai_profile": ai_profile
            }
        except Exception as e:
            logger.error(f"Error fetching complete analysis: {e}")
            return {
                "address": address,
                "trade_story": {},
                "technical_metrics": {},
                "ai_profile": {}
            }

# Standalone function for easy usage
async def get_trader_analysis(address: str) -> Dict[str, Any]:
    """Convenience function to get complete trader analysis"""
    async with TraderAnalysisClient() as client:
        return await client.fetch_complete_analysis(address)

# Test function
async def test_api():
    """Test the API client with the example address"""
    test_address = "0x37a45AdBb275d5d3F8100f4cF16977cd4B0f9Fb7"
    
    async with TraderAnalysisClient() as client:
        print("Testing API client...")
        
        # Test individual endpoints
        profile = await client.fetch_ai_profile(test_address)
        print(f"AI Profile: {json.dumps(profile, indent=2)}")
        
        metrics = await client.fetch_technical_metrics(test_address)
        print(f"Technical Metrics: {json.dumps(metrics, indent=2)}")
        
        # Test complete analysis
        complete = await client.fetch_complete_analysis(test_address)
        print(f"Complete Analysis: {json.dumps(complete, indent=2)}")

if __name__ == "__main__":
    asyncio.run(test_api())