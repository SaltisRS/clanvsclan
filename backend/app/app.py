from fastapi import FastAPI
from pymongo import MongoClient
from typing import List, Dict

import os
from dotenv import load_dotenv
load_dotenv()

app = FastAPI()

# MongoDB Configuration (replace with your actual connection details)
MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = "Frenzy"
COLLECTION_NAME_1 = "ironfoundry"
COLLECTION_NAME_2 = "ironclad"

client = MongoClient(MONGO_URI)
db = client[DATABASE_NAME]
collection1 = db[COLLECTION_NAME_1]
collection2 = db[COLLECTION_NAME_2]

@app.get("/api/data1")
async def get_data1() -> List[Dict]:
    """
    Retrieves data from the first MongoDB collection.
    """
    data = list(collection1.find({}))  # Exclude _id
    return data

@app.get("/api/data2")
async def get_data2() -> List[Dict]:
    """
    Retrieves data from the second MongoDB collection.
    """
    data = list(collection2.find({}))  # Exclude _id
    return data

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
