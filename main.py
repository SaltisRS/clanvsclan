import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger
from client.discord_client import DiscordClient


client = DiscordClient()

async def logging_setup():
    load_dotenv()
    logger.remove()
    log_level = "DEBUG" if os.getenv("DEBUG_LOGS", "False").lower() == "true" else "INFO"
    logger.add(sink=sys.stdout, format="{level}:{message} - [{time:HH:mm:s - DD/MM/YYYY}]", level=log_level)
    logger.add(sink=Path(__file__).parent / "logs" / "{time:MMMM-YYYY}" / "{time:DD}.log", 
               format="{level}:{message} - [{time:HH:mm:s - DD/MM/YYYY}]", 
               level=log_level, 
               rotation="1 day")
    
    logger.info("Logging set to: {log_level}")


@logger.catch
async def main():
    await client.start(client.token)
    
    
if __name__ == "__main__":
    asyncio.run(main())