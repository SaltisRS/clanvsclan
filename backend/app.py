from fastapi import FastAPI, HTTPException, status # Added status for clarity
from pymongo import AsyncMongoClient, MongoClient
from typing import Any, List, Dict, Optional
from loguru import logger
import os
from dotenv import load_dotenv
import wom
from wom import Metric
import asyncio
from contextlib import asynccontextmanager
from cachetools import LRUCache
import pandas as pd
import io


load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = "Frenzy"
COLLECTION_NAME_1 = "ironfoundry"
COLLECTION_NAME_2 = "ironclad"
COLLECTION_NAME_3 = "Templates"
ACTUAL_HEADERS = ["Rank", "Username", "Team", "Start", "End", "Gained", "Last Updated"]

leaderboards_cache = LRUCache(maxsize=1)
client = MongoClient(MONGO_URI, maxPoolSize=None, maxIdleTimeMS=60000 * 5, maxConnecting=10)
async_client = AsyncMongoClient(MONGO_URI, maxPoolSize=None, maxIdleTimeMS=60000 * 5, maxConnecting=10)
db = client[DATABASE_NAME]
if_coll = db[COLLECTION_NAME_1]
ic_coll = db[COLLECTION_NAME_2]
players = db["Players"]
async_db = async_client[DATABASE_NAME]
if_coll_async = async_db[COLLECTION_NAME_1]
ic_coll_async = async_db[COLLECTION_NAME_2]
players_coll_async = async_db["Players"]
foundry_link = "https://imgur.com/eVNvP9K.png"
clad_link = "https://i.imgur.com/a0DB45h.png"


async def refresh_leaderboards_cache(app: FastAPI):
    REFRESH_INTERVAL_SECONDS = 5 * 60 # 5 minutes

    while True:
        logger.info(f"Background task: Attempting to refresh leaderboard data.")
        try:
            combined_data = await _get_all_leaderboards_data()
            combined_leaderboards_dict = {"Data": combined_data}
            
            leaderboards_cache['combined_leaderboards'] = combined_leaderboards_dict
            logger.info(f"Background task: Leaderboard data updated in cache.")

        except Exception as e:
            logger.error(f"Background task: Failed to refresh leaderboard data: {e}", exc_info=True)

        await asyncio.sleep(REFRESH_INTERVAL_SECONDS)



@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("FastAPI application startup initiated.")
    try:
        app.state.wom_client = wom.Client(api_key=os.getenv("WOM_API"), user_agent="@saltis.")
        await app.state.wom_client.start()
        logger.info("WOM Client started successfully via Lifespan.")
        
        app.state.background_refresh_task = asyncio.create_task(refresh_leaderboards_cache(app))
        logger.info("Background leaderboard refresh task started.")

        app.state.initial_cache_populate_task = asyncio.create_task(
            _perform_initial_cache_population(app)
        )
        logger.info("Initial cache population task started in background.")

    except RuntimeError as e:
        logger.warning(f"WOM Client already started or encountered an issue during lifespan startup: {e}")
    except Exception as e:
        logger.error(f"Failed to start WOM Client or initial background tasks during lifespan startup: {e}")
        raise


    logger.info("FastAPI application is ready to serve. Yielding control.")
    yield

    logger.info("FastAPI application shutdown initiated.")
    
    if hasattr(app.state, 'background_refresh_task') and not app.state.background_refresh_task.done():
        app.state.background_refresh_task.cancel()
        logger.info("Background refresh task cancelled.")
        try:
            await app.state.background_refresh_task
        except asyncio.CancelledError:
            logger.info("Background refresh task successfully cancelled.")
    
    if hasattr(app.state, 'initial_cache_populate_task') and not app.state.initial_cache_populate_task.done():
        app.state.initial_cache_populate_task.cancel()
        logger.info("Initial cache population task cancelled.")
        try:
            await app.state.initial_cache_populate_task
        except asyncio.CancelledError:
            logger.info("Initial cache population task successfully cancelled.")

    if hasattr(app.state, 'wom_client') and app.state.wom_client:
        try:
            await app.state.wom_client.close()
            logger.info("WOM Client closed successfully via Lifespan.")
        except Exception as e:
            logger.error(f"Failed to close WOM Client during lifespan shutdown: {e}")
    
    if hasattr(app.state, 'initial_cache_populate_task') and not app.state.initial_cache_populate_task.done():
        app.state.initial_cache_populate_task.cancel()
        logger.info("Initial cache population task cancelled.")
        try:
            await app.state.initial_cache_populate_task
        except asyncio.CancelledError:
            logger.info("Initial cache population task successfully cancelled.")
            

async def _perform_initial_cache_population(app: FastAPI):
    logger.info("Initial cache population: Starting data fetch.")
    try:
        combined_data = await _get_all_leaderboards_data()
        leaderboards_cache['combined_leaderboards'] = {"Data": combined_data}
        logger.info("Initial leaderboard cache populated successfully.")
    except Exception as e:
        logger.error(f"Failed to perform initial leaderboard cache population: {e}", exc_info=True)



app = FastAPI(lifespan=lifespan)

async def _get_total_gained_leaderboard_helper() -> List[Dict]:
    logger.info("Fetching Total Gained leaderboard data from MongoDB.")
    leaderboard_entries: List[Dict] = []
    try:
        cursor = players_coll_async.find({}).sort("total_gained", -1)
        player_docs = await cursor.to_list(length=None)

        rows: List[Dict] = []
        for i, doc in enumerate(player_docs):
            rsn = doc.get("rsn")
            value = doc.get("total_gained")
            
            clan = doc.get("clan")
            if not isinstance(rsn, str) or not isinstance(value, (int, float)):
                logger.warning(f"Skipping Total Gained entry due to non-standard RSN/Value type for doc: {doc.get('_id')}")
                continue

            profile_link = f"https://wiseoldman.net/players/{str(rsn).replace(' ', '%20')}"
            
            icon_link = ""
            if clan == "ironfoundry":
                icon_link = foundry_link
            elif clan == "ironclad":
                icon_link = clad_link

            rows.append({
                "index": i + 1,
                "rsn": rsn,
                "value": value,
                "profile_link": profile_link,
                "icon_link": icon_link,
            })
        
        if rows:
            leaderboard_entries.append({
                "title": "Total Gained (Points)",
                "metric_page": None,
                "data": rows
            })
        return leaderboard_entries
    except Exception as e:
        logger.error(f"Error fetching Total Gained leaderboard from MongoDB: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to fetch Total Gained leaderboard: {e}")

async def _get_wom_leaderboards_data_helper() -> List[Dict]:
    CSV_COLUMN_USERNAME = 'Username'
    CSV_COLUMN_TEAM = 'Team'
    CSV_COLUMN_GAINED = 'Gained'
    logger.info("Fetching Wiseoldman competition CSV data using wom_client and parsing with pandas.")
    competition_id = 90513
    
    metrics = [Metric.Overall.value, 
               Metric.Ehb.value, 
               Metric.Ehp.value, 
               Metric.ClueScrollsAll.value, 
               Metric.TombsOfAmascutExpert.value, 
               Metric.ChambersOfXeric.value, 
               Metric.TheatreOfBlood.value, 
               Metric.TheCorruptedGauntlet.value,
               Metric.Slayer.value,
               Metric.BarrowsChests.value,
               Metric.GiantMole.value,
               Metric.Yama.value,
               Metric.CollectionsLogged.value
               ]


    wom_leaderboards: List[Dict] = []

    try:
        current_wom_client: wom.Client = app.state.wom_client
        for metric in metrics:
            logger.info(f"Fetching data for metric: {metric} from WOM CSV endpoint.")
            
            response: wom.Result = await current_wom_client.competitions.get_details_csv(
                id=competition_id, metric=metric # type: ignore
            )

            if response.is_ok:
                csv_content: str = response.unwrap()
                df = pd.read_csv(io.StringIO(csv_content))
                
                if df.empty:
                    logger.warning(f"CSV data for metric {metric} is empty. Skipping leaderboard generation.")
                    continue
                    
                df[CSV_COLUMN_GAINED] = pd.to_numeric(df[CSV_COLUMN_GAINED], errors='coerce').fillna(0).astype(float)
                
                logger.info(f"Successfully parsed {len(df)} rows for {metric} from WOM CSV using pandas.")

                leaderboard_title = f"{metric.replace('_', ' ').title()}"
                
                leaderboard_rows = []
                sorted_df = df.sort_values(by=CSV_COLUMN_GAINED, ascending=False)

                for i, row in enumerate(sorted_df.itertuples(index=False)): 
                    rsn = getattr(row, CSV_COLUMN_USERNAME, 'N/A')
                    value = getattr(row, CSV_COLUMN_GAINED, 0.0)
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
                
                competition_page_url = f"https://wiseoldman.net/competitions/{competition_id}?preview={metric.lower().replace(" ", "_")}"
                
                wom_leaderboards.append({
                    "title": leaderboard_title,
                    "metric_page": competition_page_url,
                    "data": leaderboard_rows
                })
            else:
                logger.error(f"Failed to fetch {metric} competition details from WOM CSV (is_ok=False): {response.error_message}")
            
            await asyncio.sleep(5) 

        return wom_leaderboards

    except Exception as e:
        logger.error(f"An unexpected error occurred in _get_wom_leaderboards_data_helper (CSV): {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate leaderboard data from Wiseoldman CSV: {e}"
        )
        
async def _get_items_obtained_leaderboard_helper() -> List[Dict]:
    logger.info("Fetching Items Obtained leaderboard data from MongoDB.")
    leaderboard_entries: List[Dict] = []
    try:
        cursor = players_coll_async.find({})
        player_docs = await cursor.to_list(length=None)

        processed_players_with_item_counts: List[Dict] = []
        for doc in player_docs:
            rsn = doc.get("rsn")
            clan = doc.get("clan")
            obtained_items = doc.get("obtained_items", {}) # Should be a dict
            
            if not isinstance(rsn, str):
                logger.warning(f"Skipping Items Obtained entry due to non-string RSN for doc: {doc.get('_id')}")
                continue

            total_items_obtained = sum(int(count) for count in obtained_items.values() if isinstance(count, (int, float)))
            
            processed_players_with_item_counts.append({
                "rsn": rsn,
                "total_items": total_items_obtained,
                "clan": clan,
                "profile_link_base": f"https://wiseoldman.net/players/{str(rsn).replace(' ', '%20')}"
            })
        
        sorted_players = sorted(processed_players_with_item_counts, key=lambda p: p.get("total_items", 0), reverse=True)

        rows: List[Dict] = []
        for i, player_data in enumerate(sorted_players):
            icon_link = ""
            if player_data.get("clan") == "ironfoundry":
                icon_link = foundry_link
            elif player_data.get("clan") == "ironclad":
                icon_link = clad_link
            
            rows.append({
                "index": i + 1,
                "rsn": player_data["rsn"],
                "value": player_data["total_items"],
                "profile_link": player_data["profile_link_base"],
                "icon_link": icon_link,
            })
        
        if rows:
            leaderboard_entries.append({
                "title": "Items Obtained (Total)",
                "metric_page": None,
                "data": rows
            })
        return leaderboard_entries
    except Exception as e:
        logger.error(f"Error fetching Items Obtained leaderboard from MongoDB: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to fetch Items Obtained leaderboard: {e}")


async def _get_pets_obtained_leaderboard_helper() -> List[Dict]:
    logger.info("Fetching Pets Obtained leaderboard data from MongoDB.")
    leaderboard_entries: List[Dict] = []
    try:
        cursor = players_coll_async.find({})
        player_docs = await cursor.to_list(length=None)

        processed_players_with_pet_counts: List[Dict] = []
        for doc in player_docs:
            rsn = doc.get("rsn")
            clan = doc.get("clan")
            obtained_items = doc.get("obtained_items", {})
            
            if not isinstance(rsn, str):
                logger.warning(f"Skipping Pets Obtained entry due to non-string RSN for doc: {doc.get('_id')}")
                continue

            pet_count = 0
            for item_key, count in obtained_items.items():
                if isinstance(item_key, str) and item_key.startswith("Miscellaneous.Pets."):
                    pet_count += int(count) if isinstance(count, (int, float)) else 0
            
            if pet_count > 0:
                processed_players_with_pet_counts.append({
                    "rsn": rsn,
                    "total_pets": pet_count,
                    "clan": clan,
                    "profile_link_base": f"https://wiseoldman.net/players/{str(rsn).replace(' ', '%20')}"
                })
        
        sorted_players = sorted(processed_players_with_pet_counts, key=lambda p: p.get("total_pets", 0), reverse=True)

        rows: List[Dict] = []
        for i, player_data in enumerate(sorted_players):
            icon_link = ""
            if player_data.get("clan") == "ironfoundry":
                icon_link = foundry_link
            elif player_data.get("clan") == "ironclad":
                icon_link = clad_link
            
            rows.append({
                "index": i + 1,
                "rsn": player_data["rsn"],
                "value": player_data["total_pets"],
                "profile_link": player_data["profile_link_base"],
                "icon_link": icon_link,
            })
        
        if rows:
            leaderboard_entries.append({
                "title": "Pets Obtained",
                "metric_page": None,
                "data": rows
            })
        return leaderboard_entries
    except Exception as e:
        logger.error(f"Error fetching Pets Obtained leaderboard from MongoDB: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to fetch Pets Obtained leaderboard: {e}")


async def _get_all_leaderboards_data() -> List[Dict]:
    logger.info("Starting to compile all leaderboard data from various sources.")
    combined_leaderboards: List[Dict] = []

    try:
        # 1. Wise Old Man CSV Leaderboard
        wom_data = await _get_wom_leaderboards_data_helper()
        combined_leaderboards.extend(wom_data)
        logger.info(f"Added {len(wom_data)} leaderboards from Wiseoldman CSV.")
        
        # 2. MongoDB: Total Gained Leaderboard
        total_gained_data = await _get_total_gained_leaderboard_helper()
        combined_leaderboards.extend(total_gained_data)
        logger.info(f"Added {len(total_gained_data)} leaderboards for Total Gained from MongoDB.")

        # 3. MongoDB: Items Obtained Leaderboard
        items_obtained_data = await _get_items_obtained_leaderboard_helper()
        combined_leaderboards.extend(items_obtained_data)
        logger.info(f"Added {len(items_obtained_data)} leaderboards for Items Obtained from MongoDB.")

        # 4. MongoDB: Pets Obtained Leaderboard
        pets_obtained_data = await _get_pets_obtained_leaderboard_helper()
        combined_leaderboards.extend(pets_obtained_data)
        logger.info(f"Added {len(pets_obtained_data)} leaderboards for Pets Obtained from MongoDB.")

        logger.info(f"Finished combining all leaderboards. Total: {len(combined_leaderboards)}.")
        return combined_leaderboards

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred in _get_all_leaderboards_data: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compile all leaderboard data: {e}"
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
async def get_leaderboard():
    logger.info("Frontend requested leaderboards. Reading from cache.")
    if 'combined_leaderboards' in leaderboards_cache:
        cached_data = leaderboards_cache['combined_leaderboards']
        logger.info("Returning cached leaderboard data.")
        return cached_data
    else:
        logger.warning("Leaderboard data not yet available in cache. Initial fetch might be in progress or failed.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, # Use status constant
            detail="Leaderboard data not yet available. Please try again shortly. (Initial fetch might be in progress or failed.)"
        )
    
# --- Existing GET /ironfoundry endpoint (No change) ---
@app.get("/ironfoundry")
async def get_if_data() -> List[Dict]:
    logger.info("Retrieving data from the first collection")
    event_data = list(if_coll.find({}))
    logger.info(f"Data retrieved.")
    return event_data

# --- Existing GET /ironclad endpoint (No change) ---
@app.get("/ironclad")
async def get_ic_data() -> List[Dict]:
    logger.info("Retrieving data from the second collection")
    event_data = list(ic_coll.find({}))
    logger.info(f"Data retrieved.")
    return event_data # type: ignore

# --- Existing POST /milestones endpoint (No change) ---
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
        return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Server Error") # Use status constant


if __name__ == "__main__":
    import uvicorn
    import datetime # type: ignore
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=True)