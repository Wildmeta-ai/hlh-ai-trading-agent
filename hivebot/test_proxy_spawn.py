#!/usr/bin/env python3

"""
Test spawning a bot through the SOCKS proxy to bypass rate limiting
"""

import requests
import json

# Test spawning a bot with proxy configuration
def test_spawn_with_proxy():
    """Test the spawn-bot API"""

    spawn_data = {
        "userMainAddress": "0x8cf39b53bd5532566bc79588a2270d53176bd0ce",
        "agentPrivateKey": "0xa130dd7bd28c71a4c97ef4d1cc79908a8a09e76e0c4673b8019dd7f35a1914ee"
    }

    try:
        # Use SOCKS proxy for the spawn request too
        proxies = {
            'http': 'socks5://127.0.0.1:9999',
            'https': 'socks5://127.0.0.1:9999'
        }

        response = requests.post(
            'http://localhost:3000/api/spawn-bot',
            json=spawn_data,
            proxies=proxies,
            timeout=30
        )

        print(f"Spawn API Status: {response.status_code}")
        print(f"Response: {response.text}")

    except Exception as e:
        print(f"Error testing spawn API: {e}")

if __name__ == "__main__":
    test_spawn_with_proxy()