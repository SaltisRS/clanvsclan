from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from typing import List, Dict, Literal
from loguru import logger
import os
from dotenv import load_dotenv



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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
