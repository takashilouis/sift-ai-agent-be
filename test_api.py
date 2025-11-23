"""
Test script for the E-Commerce Research Agent API

This script demonstrates how to use the research API endpoints.
"""

import httpx
import asyncio
import json


async def test_streaming_research():
    """Test the streaming research endpoint"""
    print("=" * 60)
    print("Testing Streaming Research Endpoint")
    print("=" * 60)
    
    url = "http://localhost:8000/api/research"
    payload = {
        "query": "research this product: Apple AirPods 4",
        "mode": "product-analysis"
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream("POST", url, json=payload) as response:
            print(f"\nStatus Code: {response.status_code}\n")
            
            async for line in response.aiter_lines():
                if line.strip():
                    try:
                        data = json.loads(line)
                        step = data.get("step", "unknown")
                        print(f"\n📍 Step: {step}")
                        print("-" * 40)
                        
                        # Pretty print the state
                        state = data.get("state", {})
                        for key, value in state.items():
                            if value is not None and key not in ["raw_html"]:
                                if isinstance(value, (dict, list)):
                                    print(f"{key}: {json.dumps(value, indent=2)[:200]}...")
                                else:
                                    print(f"{key}: {value}")
                    except json.JSONDecodeError:
                        print(f"Could not parse: {line}")


async def test_sync_research():
    """Test the synchronous research endpoint"""
    print("\n" + "=" * 60)
    print("Testing Synchronous Research Endpoint")
    print("=" * 60)
    
    url = "http://localhost:8000/api/research/sync"
    payload = {
        "query": "Samsung Galaxy Buds",
        "mode": "product-analysis"
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, json=payload)
        print(f"\nStatus Code: {response.status_code}\n")
        
        if response.status_code == 200:
            data = response.json()
            print("Final Research Report:")
            print("-" * 40)
            print(json.dumps(data, indent=2))


async def test_health_check():
    """Test the health check endpoint"""
    print("\n" + "=" * 60)
    print("Testing Health Check")
    print("=" * 60)
    
    url = "http://localhost:8000/api/research/health"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response: {response.json()}\n")


async def main():
    """Run all tests"""
    print("\n🚀 E-Commerce Research Agent API Tests\n")
    
    try:
        # Test health check first
        await test_health_check()
        
        # Test streaming endpoint
        await test_streaming_research()
        
        # Test sync endpoint
        await test_sync_research()
        
        print("\n" + "=" * 60)
        print("✅ All tests completed!")
        print("=" * 60 + "\n")
        
    except httpx.ConnectError:
        print("\n❌ Error: Could not connect to the API server.")
        print("Make sure the server is running on http://localhost:8000")
        print("Run: ./run.sh\n")
    except Exception as e:
        print(f"\n❌ Error: {e}\n")


if __name__ == "__main__":
    asyncio.run(main())
