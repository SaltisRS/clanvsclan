from fastapi import FastAPI, HTTPException
from pymongo import AsyncMongoClient, MongoClient
from typing import Any, List, Dict, Optional
from loguru import logger
import os
from dotenv import load_dotenv
import wom
from wom import CompetitionDetail
import asyncio
from contextlib import asynccontextmanager
from cachetools import TTLCache, cached



load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = "Frenzy"
COLLECTION_NAME_1 = "ironfoundry"
COLLECTION_NAME_2 = "ironclad"
COLLECTION_NAME_3 = "Templates"

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
    Fetches competition data from Wiseoldman and formats it into
    the frontend's expected leaderboard structure.
    Uses response.unwrap() then converts objects to dicts using .to_dict().
    """
    logger.info("Fetching Wiseoldman competition data for leaderboards.")
    competition_id = 90513
    metrics = [wom.Metric.Overall, wom.Metric.Ehp, wom.Metric.Ehb]
    
    wom_leaderboards: List[Dict] = []

    try:
        current_wom_client: wom.Client = app.state.wom_client

        for metric in metrics:
            logger.info(f"Fetching data for metric: {metric.name} from WOM.")
            response: wom.Result = await current_wom_client.competitions.get_details(
                id=competition_id, metric=metric
            )

            if response.is_ok:
                # Get the CompetitionDetails object
                competition_details = response.unwrap() # No explicit type hint, let Python infer
                
                leaderboard_title = f"{metric.name.replace('_', ' ').title()} Gained"
                
                leaderboard_rows = []
                sorted_participants = sorted(
                    competition_details.participants,
                    key=lambda p: p.progress.gained,
                    reverse=True
                )

                for i, participant_obj in enumerate(sorted_participants):

                    participant_dict = participant_obj.to_dict() 
                    
                    player_data = participant_dict.get('player', {})
                    progress_data = participant_dict.get('progress', {})

                    rsn = player_data.get('display_name') or player_data.get('username', 'N/A')
                    
                    value_raw = progress_data.get('gained', 0)
                    try:
                        value = int(value_raw)
                    except (ValueError, TypeError):
                        logger.warning(f"Could not convert 'gained' value '{value_raw}' to int for player {rsn}.")
                        value = 0
                    
                    profile_username = player_data.get('username')
                    profile_link = f"https://wiseoldman.net/players/{profile_username}" if profile_username else "#"
                    
                    participant_team_name = participant_dict.get('team_name')
                    player_icon_link = ""
                    if participant_team_name == "Iron Foundry":
                        player_icon_link = foundry_link
                    elif participant_team_name == "Ironclad":
                        player_icon_link = clad_link

                    leaderboard_rows.append({
                        "index": i + 1,
                        "rsn": rsn,
                        "value": value,
                        "profile_link": profile_link,
                        "icon_link": player_icon_link
                    })
                
                competition_page_url = f"https://wiseoldman.net/competitions/{competition_id}?preview={metric.name.lower()}"
                
                wom_leaderboards.append({
                    "title": leaderboard_title,
                    "metric_page": competition_page_url,
                    "data": leaderboard_rows
                })
            else:
                logger.error(f"Failed to fetch {metric.name} competition details from WOM (is_ok=False): {response.error_message}")
            
            await asyncio.sleep(5)

        return wom_leaderboards

    except Exception as e:
        logger.error(f"Error in _get_wom_leaderboards_data_helper: {e}", exc_info=True)
        raise
            

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
