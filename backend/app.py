from fastapi import FastAPI, HTTPException
from pymongo import AsyncMongoClient, MongoClient
from typing import Any, List, Dict, Optional
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
async_client = AsyncMongoClient(MONGO_URI)
db = client[DATABASE_NAME]
if_coll = db[COLLECTION_NAME_1]
ic_coll = db[COLLECTION_NAME_2]
players = db["Players"]


def find_milestone_doc_sync(template_doc: Dict[str, Any], category: str, metric_name: str) -> Optional[Dict[str, Any]]:
    milestones_data = template_doc.get("milestones", {})
    category_list = milestones_data.get(category)
    if not category_list:
        return None

    for milestone in category_list:
        if milestone.get("name") == metric_name:
            return milestone
    return None

    

@app.get("/ironfoundry")
async def get_if_data() -> List[Dict]:
    logger.info("Retrieving data from the first collection")
    event_data = if_coll.find_one({})
    logger.info(f"Data retrieved.")
    return list(event_data) # type: ignore

@app.get("/ironclad")
async def get_ic_data() -> List[Dict]:
    logger.info("Retrieving data from the second collection")
    event_data = ic_coll.find_one({})
    logger.info(f"Data retrieved.")
    return list(event_data) # type: ignore


@app.post("/milestones")
async def update_milestones(milestone_data: Dict):
    logger.info(milestone_data)

    try:
        ironfoundry_data = milestone_data.get("ironfoundry")
        if ironfoundry_data:
            category = list(ironfoundry_data.keys())[0]
            metric_name = list(ironfoundry_data[category].keys())[0]
            updated_value = ironfoundry_data[category][metric_name]

            logger.info(f"Updating Iron Foundry: Category='{category}', Metric='{metric_name}', Value={updated_value}")

            ironfoundry_template = if_coll.find_one({}) # type: ignore
            if ironfoundry_template:
                update_result = if_coll.update_one(
                    {"_id": ironfoundry_template["_id"], f"milestones.{category}.name": metric_name},
                    {"$set": {f"milestones.{category}.$.current_value": updated_value}}
                ) # type: ignore
                logger.info(f"Iron Foundry update_one acknowledged: {update_result.acknowledged}, matched: {update_result.matched_count}, modified: {update_result.modified_count}")
            else:
                 logger.warning("Iron Foundry template document not found or missing _id for update.")

        ironclad_data = milestone_data.get("ironclad")
        if ironclad_data:
            category = list(ironclad_data.keys())[0]
            metric_name = list(ironclad_data[category].keys())[0]
            updated_value = ironclad_data[category][metric_name]

            logger.info(f"Updating Ironclad: Category='{category}', Metric='{metric_name}', Value={updated_value}")

            ironclad_template = ic_coll.find_one({}) # type: ignore
            if ironclad_template and '_id' in ironclad_template:
                 update_result = ic_coll.update_one(
                    {"_id": ironclad_template["_id"], f"milestones.{category}.name": metric_name},
                    {"$set": {f"milestones.{category}.$.current_value": updated_value}}
                ) # type: ignore
                 logger.info(f"Ironclad update_one acknowledged: {update_result.acknowledged}, matched: {update_result.matched_count}, modified: {update_result.modified_count}")
            else:
                 logger.warning("Ironclad template document not found or missing _id for update.")

        return {"message": "Milestone data processed for update."}

    except Exception as e:
        logger.error(f"An unhandled error occurred during milestone update processing: {e}", exc_info=True)
        return HTTPException(status_code=402, detail="Internal Server Error")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
