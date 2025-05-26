from fastapi import FastAPI
from pymongo import MongoClient
from typing import List, Dict
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
if_coll = db[COLLECTION_NAME_1]
ic_coll = db[COLLECTION_NAME_2]
players = db["Players"]


    

@app.get("/ironfoundry")
async def get_if_data() -> List[Dict]:
    logger.info("Retrieving data from the first collection")
    event_data = list(if_coll.find({}))
    player_data = list(players.find({"clan": "ironfoundry"}))
    if player_data:
        event_data[0]["players"] = player_data
    logger.info(f"Data retrieved.")
    return event_data

@app.get("/ironclad")
async def get_ic_data() -> List[Dict]:
    logger.info("Retrieving data from the second collection")
    event_data = list(ic_coll.find({}))
    player_data = players.find({"clan": "ironclad"})
    if player_data:
        event_data[0]["players"] = player_data
    logger.info(f"Data retrieved.")
    return event_data


@app.post("/milestones")
async def update_milestones(milestone_data: Dict):
    logger.info(milestone_data)

    return {"message": "Milestone data received and logged successfully."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
