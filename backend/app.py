from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from typing import List, Dict, Literal
from loguru import logger
import os
import httpx
from dotenv import load_dotenv
from uuid import uuid4
from pathlib import Path
from PIL import Image
from io import BytesIO


load_dotenv()
            
app = FastAPI()

MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = "Frenzy"
COLLECTION_NAME_1 = "ironfoundry"
COLLECTION_NAME_2 = "ironclad"
COLLECTION_NAME_3 = "Templates"


client = MongoClient(MONGO_URI)
db = client[DATABASE_NAME]
if_coll = db[COLLECTION_NAME_3]
ic_coll = db[COLLECTION_NAME_3]




@app.get("/ironfoundry")
async def get_if_data() -> List[Dict]:
    logger.info("Retrieving data from the first collection")
    data = list(if_coll.find({}))
    logger.info(f"Data retrieved: {data}")
    return data

@app.get("/ironclad")
async def get_ic_data() -> List[Dict]:
    logger.info("Retrieving data from the second collection")
    data = list(ic_coll.find({}))
    logger.info(f"Data retrieved: {data}")
    return data

@app.post("/saveimage")
async def save_image(image_url: str, clan: Literal["IF", "IC"]):
    with httpx.Client() as client:
        response = client.get(image_url)
        response.raise_for_status()
    
    image = Image.open(BytesIO(response.content))
    extension = image.format
    if extension:
        path = Path(".") / "gallery" / f"{str(uuid4())}_{clan}.{extension.lower()}"
        image.save(path)


@app.get("/leaderboard")
async def get_leaderboard() -> Dict[str, str | int]:
    """Fetches Competition from WOM and formats it."""
    competition_url = "https://wiseoldman.com/api/v2/competitions..."
    response = httpx.get(competition_url)
    if response.status_code == 200:
        return {}
    return {}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
