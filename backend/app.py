from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from typing import List, Dict
from loguru import logger
import os
from dotenv import load_dotenv
from starlette.status import HTTP_401_UNAUTHORIZED

load_dotenv()

app = FastAPI()

# MongoDB Configuration (replace with your actual connection details)
MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = "Frenzy"
COLLECTION_NAME_1 = "ironfoundry"
COLLECTION_NAME_2 = "ironclad"
COLLECTION_NAME_3 = "Templates"


client = MongoClient(MONGO_URI)
db = client[DATABASE_NAME]
if_coll = db[COLLECTION_NAME_1]
ic_coll = db[COLLECTION_NAME_2]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://www.ironfoundry.cc", "https://www.ironfoundry.cc"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
    allow_credentials=True,
)

@app.get("/ironfoundry")
async def get_if_data() -> List[Dict]:
    """
    Retrieves data from the first MongoDB collection.
    """
    logger.info("Retrieving data from the first collection")
    data = list(if_coll.find({}))  # Exclude _id
    logger.info(f"Data retrieved: {data}")
    return data

@app.get("/ironclad")
async def get_ic_data() -> List[Dict]:
    """
    Retrieves data from the second MongoDB collection.
    """
    logger.info("Retrieving data from the second collection")
    data = list(ic_coll.find({}))  # Exclude _id
    logger.info(f"Data retrieved: {data}")
    return data

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app)
