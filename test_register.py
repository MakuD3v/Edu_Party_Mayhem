import asyncio
import aiohttp
import sys
import json

async def test_register():
    url = "http://localhost:8000/api/auth/register"
    payload = {
        "username": "testuser_debug",
        "password": "password123"
    }
    
    print(f"Testing registration against {url}...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers={"Content-Type": "application/json"}) as response:
                print(f"Status: {response.status}")
                print(f"Headers: {response.headers}")
                text = await response.text()
                print(f"Body: {text}")
                
                if response.status == 200:
                    data = json.loads(text)
                    print("Success!", data)
                else:
                    print("Failed.")
    except Exception as e:
        print(f"Connection error: {e}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_register())
