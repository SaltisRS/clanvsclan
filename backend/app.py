from bson import ObjectId
from fastapi import FastAPI
from pydantic import BaseModel, RootModel, model_validator
from pymongo import MongoClient
from typing import List, Dict, Optional
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


class MetricValue(RootModel[Dict[str, int]]):
    pass


class CategoryData(BaseModel):
    cluescroll: Optional[MetricValue] = None
    experience: Optional[MetricValue] = None
    killcount: Optional[MetricValue] = None

    @model_validator(mode='before')
    @classmethod
    def check_exclusive_category(cls, values):
        if not isinstance(values, dict):
             return values

        categories = ['cluescroll', 'experience', 'killcount']
        present_categories = [cat for cat in categories if values.get(cat) is not None]
        if len(present_categories) != 1:
            raise ValueError("Exactly one category (cluescroll, experience, or killcount) must be provided.")
        return values


class MilestoneUpdate(BaseModel):
    ironfoundry: CategoryData
    ironclad: CategoryData
    
@app.post("/milestones")
async def update_milestones(milestone_data: MilestoneUpdate):
    logger.info(f"Received milestone update:")
    logger.info(milestone_data.model_dump())

    return {"message": "Milestone data received and logged successfully."}


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
