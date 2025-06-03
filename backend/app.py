from fastapi import FastAPI, HTTPException
from pymongo import AsyncMongoClient, MongoClient
from typing import Any, List, Dict, Optional
from loguru import logger
import os
from dotenv import load_dotenv
import wom
from wom import Metric
import asyncio
from contextlib import asynccontextmanager
from cachetools import TTLCache
import pandas as pd
import io




load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = "Frenzy"
COLLECTION_NAME_1 = "ironfoundry"
COLLECTION_NAME_2 = "ironclad"
COLLECTION_NAME_3 = "Templates"
ACTUAL_HEADERS = ["Rank", "Username", "Team", "Start", "End", "Gained", "Last Updated"]

leaderboards_cache = TTLCache(maxsize=1, ttl=300)
client = MongoClient(MONGO_URI, maxPoolSize=None, maxIdleTimeMS=60000 * 5, maxConnecting=10)
async_client = AsyncMongoClient(MONGO_URI, maxPoolSize=None, maxIdleTimeMS=60000 * 5, maxConnecting=10)
db = client[DATABASE_NAME]
if_coll = db[COLLECTION_NAME_1]
ic_coll = db[COLLECTION_NAME_2]
players = db["Players"]
foundry_link = "https://i.imgur.com/IQuSdoi.png"
clad_link = "https://i.imgur.com/a0DB45h.png"

def async_cached(cache):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            key = (args, frozenset(kwargs.items())) # Create a hashable key for caching
            
            # Check if value is in cache
            if key in cache:
                logger.info(f"Cache hit for {func.__name__}")
                return cache[key]
            
            # If not in cache, execute the coroutine and get its result
            logger.info(f"Cache miss for {func.__name__}. Executing...")
            # Schedule the coroutine as a task and await its result
            result = await func(*args, **kwargs)
            
            # Store the result in cache
            cache[key] = result
            logger.info(f"Result for {func.__name__} cached.")
            return result
        return wrapper
    return decorator

@asynccontextmanager
async def lifespan(app: FastAPI):

    logger.info("FastAPI application startup initiated.")
    try:
        app.state.wom_client = wom.Client(api_key=os.getenv("WOM_API"), user_agent="@saltis.") # Initialize WOM client
        await app.state.wom_client.start()
        logger.info("WOM Client started successfully via Lifespan.")
    except RuntimeError as e:
        logger.warning(f"WOM Client already started or encountered an issue during lifespan startup: {e}")
    except Exception as e:
        logger.error(f"Failed to start WOM Client during lifespan startup: {e}")
    yield

    logger.info("FastAPI application shutdown initiated.")
    if hasattr(app.state, 'wom_client') and app.state.wom_client:
        try:
            await app.state.wom_client.close()
            logger.info("WOM Client closed successfully via Lifespan.")
        except Exception as e:
            logger.error(f"Failed to close WOM Client during lifespan shutdown: {e}")
            
app = FastAPI(lifespan=lifespan)

async def _get_wom_leaderboards_data_helper() -> List[Dict]:
    """
    Fetches competition CSV data using wom_client.competitions.get_details_csv(),
    parses it with pandas, and formats it into the frontend's expected leaderboard structure.
    This version directly incorporates the working pandas script's pattern.
    """
    CSV_COLUMN_USERNAME = 'Username'
    CSV_COLUMN_TEAM = 'Team'
    CSV_COLUMN_GAINED = 'Gained'
    logger.info("Fetching Wiseoldman competition CSV data using wom_client and parsing with pandas.")
    competition_id = 90513
    
    metric_enum = Metric.Overall
    metric_value_str = metric_enum.value 

    wom_leaderboards: List[Dict] = []

    try:
        current_wom_client: wom.Client = app.state.wom_client

        logger.info(f"Fetching data for metric: {metric_value_str} from WOM CSV endpoint.")
        
        response: wom.Result = await current_wom_client.competitions.get_details_csv(
            id=competition_id, metric=metric_value_str # type: ignore
        )

        if response.is_ok:
            csv_content: str = response.unwrap() # Get the raw CSV string
            
            df = pd.read_csv(io.StringIO(csv_content))
            
            if df.empty:
                logger.warning("No data found in the CSV from WOM.")
                return wom_leaderboards

            # Ensure 'Gained' column is numeric (float is safe for 'number' in frontend)
            df[CSV_COLUMN_GAINED] = pd.to_numeric(df[CSV_COLUMN_GAINED], errors='coerce').fillna(0).astype(float)
            
            logger.info(f"Successfully parsed {len(df)} rows from WOM CSV using pandas.")

            leaderboard_title = f"WOM - {metric_enum.name.replace('_', ' ').title()} Gained (CSV)"
            
            leaderboard_rows = []
            
            # Sort the DataFrame directly by the 'Gained' column before iterating
            # This is more efficient than sorting a list of dicts later.
            sorted_df = df.sort_values(by=CSV_COLUMN_GAINED, ascending=False)

            # Iterate over rows and explicitly construct the dictionary for each
            for i, row in enumerate(sorted_df.itertuples(index=False)): # itertuples is generally faster than iterrows
                # Access data using attribute-like access (e.g., row.Username) or by name
                # We'll use get() to be safe if a column might be missing, or direct access if guaranteed
                # For `itertuples`, columns are accessed by attribute name, not dict key
                
                # Check for column existence and provide default if missing from the row object
                # Use .get() method on the namedtuple-like object if it supports it, or check hasattr
                rsn = getattr(row, CSV_COLUMN_USERNAME, 'N/A')
                value = getattr(row, CSV_COLUMN_GAINED, 0.0) # Will be float from pandas processing
                team_name = getattr(row, CSV_COLUMN_TEAM, None)
                
                profile_username_encoded = str(rsn).replace(' ', '%20')
                profile_link = f"https://wiseoldman.net/players/{profile_username_encoded}"
                
                player_icon_link = ""
                if team_name == "Iron Foundry":
                    player_icon_link = foundry_link
                elif team_name == "Ironclad":
                    player_icon_link = clad_link

                leaderboard_rows.append({
                    "index": i + 1,
                    "rsn": rsn,
                    "value": value,
                    "profile_link": profile_link,
                    "icon_link": player_icon_link
                })
            
            competition_page_url = f"https://wiseoldman.net/competitions/{competition_id}"
            
            wom_leaderboards.append({
                "title": leaderboard_title,
                "metric_page": competition_page_url,
                "data": leaderboard_rows
            })
        else:
            logger.error(f"Failed to fetch {metric_value_str} competition details from WOM CSV (is_ok=False): {response.error_message}")
        
        await asyncio.sleep(5)

        return wom_leaderboards

    except Exception as e:
        logger.error(f"An unexpected error occurred in _get_wom_leaderboards_data_helper (CSV): {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate leaderboard data from Wiseoldman CSV: {e}"
        )
            

def find_milestone_doc_sync(template_doc: Dict[str, Any], category: str, metric_name: str) -> Optional[Dict[str, Any]]:
    milestones_data = template_doc.get("milestones", {})
    category_list = milestones_data.get(category)
    if not category_list:
        return None

    for milestone in category_list:
        if milestone.get("name") == metric_name:
            return milestone
    return None

@app.get("/leaderboards")
@async_cached(leaderboards_cache)
async def get_combined_leaderboards():
    """
    Combines leaderboard data from various sources (e.g., Wiseoldman, MongoDB)
    and returns it in the format expected by the frontend.
    """
    logger.info("Starting to combine leaderboard data from multiple sources.")
    combined_leaderboards: List[Dict] = []

    try:
        wom_data = await _get_wom_leaderboards_data_helper()
        combined_leaderboards.extend(wom_data)
        logger.info(f"Finished combining leaderboards. Total: {len(combined_leaderboards)}.")
        return {"Data": combined_leaderboards}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred in get_combined_leaderboards: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to compile all leaderboard data: {e}"
        )
    
@app.get("/ironfoundry")
async def get_if_data() -> List[Dict]:
    logger.info("Retrieving data from the first collection")
    event_data = list(if_coll.find({}))
    logger.info(f"Data retrieved.")
    return event_data

@app.get("/ironclad")
async def get_ic_data() -> List[Dict]:
    logger.info("Retrieving data from the second collection")
    event_data = list(ic_coll.find({}))
    logger.info(f"Data retrieved.")
    return event_data # type: ignore


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
