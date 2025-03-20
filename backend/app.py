from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from typing import List, Dict
from loguru import logger
import os
from dotenv import load_dotenv
from dataclasses import dataclass


load_dotenv()

@dataclass
class Image():
    url: str

@dataclass
class Gallery:
    collection: list[Image]

    def __iadd__(self, image: Image):
        self.collection.append(image)
        
    def __len__(self) -> int:
        return len(self.collection)
    
    def __contains__(self, image: Image) -> bool:
        return image in self.collection
    
    def __iter__(self):
        return iter(self.collection)

    def __add__(self, other: 'Gallery') -> 'Gallery':
        if not isinstance(other, Gallery):
            raise TypeError(f"Expected {type(self)} got {type(other)}")
        new_gallery = Gallery(self.collection + other.collection)
        return new_gallery
    
    def to_api(self) -> list[Dict]:
        gallery = []
        for image in self.collection:
            gallery.append({"image": image.url})
        return gallery
            
app = FastAPI()

# MongoDB Configuration (replace with your actual connection details)
MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = "Frenzy"
COLLECTION_NAME_1 = "ironfoundry"
COLLECTION_NAME_2 = "ironclad"
COLLECTION_NAME_3 = "Templates"
COLLECTION_NAME_4 = "Gallery"


client = MongoClient(MONGO_URI)
db = client[DATABASE_NAME]
if_coll = db[COLLECTION_NAME_1]
ic_coll = db[COLLECTION_NAME_2]
gallery_coll = db[COLLECTION_NAME_4]


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
    allow_credentials=True,
)

async def construct_gallery():
    images = []
    data = gallery_coll.find({})
    for img in data:
        images.append(Image(url=img["image"]))
    gallery = Gallery(images)
    return gallery.to_api()

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

@app.get("gallery")
async def get_gallery() -> List[Dict]:
    """
    Returns an array of image objects
    """
    response = await construct_gallery()
    return response



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
