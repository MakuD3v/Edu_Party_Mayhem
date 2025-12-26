import asyncio
import websockets
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SESSION_CODE = "TEST01"
USER_ID = 1

async def test_game_flow():
    uri = f"ws://localhost:8000/ws/{SESSION_CODE}/{USER_ID}"
    logger.info(f"Connecting to {uri}")
    
    try:
        async with websockets.connect(uri) as websocket:
            logger.info("Connected!")
            
            # Send Start Game
            start_msg = {
                "type": "START_GAME"
            }
            logger.info(f"Sending: {start_msg}")
            await websocket.send(json.dumps(start_msg))
            
            # Wait for response
            while True:
                response = await websocket.recv()
                data = json.loads(response)
                logger.info(f"Received: {data}")
                
                if data.get("type") == "game_start":
                    logger.info("Game started successfully!")
                    break
                    
    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_game_flow())
