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
COLLECTION_NAME_4 = "BakTemp"

client = MongoClient(MONGO_URI)
db = client[DATABASE_NAME]
collection1 = db[COLLECTION_NAME_1]
collection2 = db[COLLECTION_NAME_2]
collection3 = db[COLLECTION_NAME_3]
collection4 = db[COLLECTION_NAME_4]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

async def check_passkey(passkey: str) -> bool:
    """
    Checks if the passkey is valid.
    """
    return passkey == os.getenv("PASSKEY")

def get_passkey_from_request(request: Request) -> str:
    """
    Extracts passkey from the Authorization header.
    """
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ")[1]
    raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid passkey")

@app.get("/api/data1")
async def get_data1() -> List[Dict]:
    """
    Retrieves data from the first MongoDB collection.
    """
    logger.info("Retrieving data from the first collection")
    data = list(collection1.find({}))  # Exclude _id
    logger.info(f"Data retrieved: {data}")
    return data

@app.get("/api/data2")
async def get_data2() -> List[Dict]:
    """
    Retrieves data from the second MongoDB collection.
    """
    logger.info("Retrieving data from the second collection")
    data = list(collection2.find({}))  # Exclude _id
    logger.info(f"Data retrieved: {data}")
    return data

@app.get("/api/template")
async def get_template() -> List[Dict]:
    """
    Retrieves the template for the form.
    """
    logger.info("Retrieving Template")
    data = list(collection3.find({}))
    logger.info(f"Template retrieved: {data}")
    return data

@app.post("/api/template")
async def post_template(data: dict, request: Request) -> dict:
    """
    Updates the template for the form.
    Validates the passkey before allowing updates.
    """
    passkey = get_passkey_from_request(request)
    
    if not await check_passkey(passkey):
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid passkey")

    # Assuming you want to update the template with the incoming data
    logger.info(f"Updating template with data: {data}")

    # Update the template in the collection
    try:
        result = collection4.update_one({}, {"$set": data}, upsert=True)
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Template not found to update")

        logger.info("Template updated successfully")
        return {"status": "success", "message": "Template updated successfully"}
    except Exception as e:
        logger.error(f"Error updating template: {e}")
        raise HTTPException(status_code=500, detail="Error updating template")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
